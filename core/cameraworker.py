
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, QMutex, QWaitCondition, QThread
from ultralytics import YOLO
from core.detect_thread_multiclass import DetectThread  # Certifique-se que este arquivo existe
import time

# -------------------- CONFIG (sem alterar lógica) --------------------
from config.config import CameraWorkerConfig
CFG = CameraWorkerConfig()

# Aplicar apenas os ajustes de ambiente que já eram feitos como literais
cv2.setNumThreads(CFG.cv2_num_threads)
cv2.ocl.setUseOpenCL(CFG.cv2_use_opencl)
# --------------------------------------------------------------------


class CaptureThread(QThread):
    def __init__(self, cam_id, buffer, mutex, condition, running_flag):
        super().__init__()
        self.cam_id = cam_id
        self.buffer = buffer
        self.mutex = mutex
        self.condition = condition
        self.running_flag = running_flag

    def run(self):
        # --- 1) Tenta abrir a câmera com fallback de backend (DSHOW -> MSMF -> ANY)
        backends = list(CFG.capture_backends)
        cap = None
        backend_usado = None
        for be in backends:
            c = cv2.VideoCapture(self.cam_id, be)
            if c.isOpened():
                cap = c
                backend_usado = be
                print(f"[🎥] Câmera {self.cam_id} aberta com backend: {be}")
                break
            else:
                c.release()

        if cap is None:
            print("[❌] Erro ao abrir a câmera (todos os backends).")
            return

        # --- 2) Set de propriedades: largura/altura antes do FPS; BUFFERSIZE só no DSHOW
        def _try_set(prop, val):
            ok = cap.set(prop, val)
            if not ok:
                print(f"[⚠] Backend {backend_usado} não aceitou prop {prop}={val}")
            return ok

        # Resolução “leve” (ajuste via config)
        _try_set(cv2.CAP_PROP_FRAME_WIDTH, CFG.frame_width)
        _try_set(cv2.CAP_PROP_FRAME_HEIGHT, CFG.frame_height)

        # Em MSMF o FPS costuma ser ignorado/recusado — só tenta se não for MSMF
        if backend_usado != cv2.CAP_MSMF:
            _try_set(cv2.CAP_PROP_FPS, CFG.fps_target)

        # BUFFERSIZE existe no DirectShow; no MSMF costuma dar erro
        if backend_usado == cv2.CAP_DSHOW:
            _try_set(cv2.CAP_PROP_BUFFERSIZE, CFG.dshow_buffersize)

        # Tenta MJPG (menos custo de decodificação na CPU)
        if CFG.try_mjpg:
            try:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass

        # BUFFERSIZE só no DSHOW; se falhar, ignora silenciosamente
        if backend_usado == cv2.CAP_DSHOW:
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, CFG.dshow_buffersize)
            except Exception:
                pass

        # Pequeno “aquecimento” para estabilizar a pipeline
        for _ in range(CFG.warmup_frames):
            cap.read()

        try:
            # --- 3) Loop de captura (sem waitKey; com tratamento de falha)
            while self.running_flag[0]:
                # descarta backlog: puxa N frames "na frente" e só então retrieve
                for _ in range(CFG.backlog_grabs):
                    cap.grab()
                ret, frame = cap.retrieve()

                if not ret:
                    time.sleep(CFG.fail_sleep_s)  # folga curta evita laço quente e alto uso de CPU
                    continue

                self.mutex.lock()
                self.buffer[0] = frame
                self.condition.wakeAll()
                self.mutex.unlock()

        finally:
            cap.release()
            print("[🔴] CaptureThread encerrada.")


class CameraWorker(QObject):
    frame_ready = Signal(np.ndarray)
    sensores_atualizados = Signal(dict)

    # Defaults agora vêm do arquivo de configuração (sem alterar lógica)
    DEFAULT_CAM_ID = CFG.cam_id
    DEFAULT_MODEL_PATH = CFG.model_path

    def __init__(self, cam_id=DEFAULT_CAM_ID, model_path=DEFAULT_MODEL_PATH):
        super().__init__()
        self.cam_id = cam_id
        self.model_path = model_path

        self.buffer = [None]
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.running_flag = [True]

        self.capture_thread = CaptureThread(cam_id, self.buffer, self.mutex, self.condition, self.running_flag)
        self.detect_thread = DetectThread(self.buffer, self.mutex, self.condition, self.running_flag, model_path)
        self.detect_thread.frame_ready.connect(self.frame_ready)
        self.detect_thread.sensores_atualizados.connect(self.sensores_atualizados)

    def enviar_dados_camera_para_dashboard(self):
        cap = cv2.VideoCapture(self.cam_id)
        if not cap.isOpened():
            print("[❌] Erro ao abrir a câmera para extrair dados.")
            return
        cap.release()

    def start(self):
        self.running_flag[0] = True
        self.capture_thread.start()
        self.detect_thread.start()

        # Espera até que o primeiro frame esteja disponível
        timeout = time.time() + CFG.start_wait_timeout_s
        while self.buffer[0] is None and time.time() < timeout:
            time.sleep(CFG.start_wait_poll_s)

        self.enviar_dados_camera_para_dashboard()

    def stop(self):
        self.running_flag[0] = False
        self.capture_thread.quit()
        self.capture_thread.wait()
        self.detect_thread.quit()
        self.detect_thread.wait()

    def shutdown(self):
        self.stop()
        try:
            self.capture_thread.deleteLater()
        except Exception:
            pass
        try:
            self.detect_thread.deleteLater()
        except Exception:
            pass

    def pause_detection(self):
        if self.detect_thread:
            print("[⏸️] Pausando detecção na thread.")
            self.detect_thread.pause()

    def resume_detection(self):
        if self.detect_thread:
            print("[▶️] Retomando detecção na thread.")
            self.detect_thread.resume()

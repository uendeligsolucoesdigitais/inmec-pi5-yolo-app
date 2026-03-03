# detect_thread_multiclass.py
from config.config import DetectThreadConfig as _CFGDetect
cfg = _CFGDetect()

import os
os.environ["OMP_NUM_THREADS"] = str(cfg.omp_num_threads)
os.environ["OPENBLAS_NUM_THREADS"] = str(cfg.openblas_num_threads)
os.environ["MKL_NUM_THREADS"] = str(cfg.mkl_num_threads)
os.environ["NUMEXPR_NUM_THREADS"] = str(cfg.numexpr_num_threads)

import cv2
cv2.setNumThreads(int(cfg.opencv_num_threads))
cv2.ocl.setUseOpenCL(bool(cfg.opencv_use_opencl))

import torch
torch.set_num_threads(int(cfg.torch_num_threads))
torch.set_num_interop_threads(int(cfg.torch_num_interop_threads))

import time
from datetime import datetime
from PySide6.QtCore import QThread, Signal, QMetaObject, Qt, Slot
from core.sensors import SensorManager

import numpy as np
from ultralytics import YOLO
from core.bdlmanager import BDLManager

from config.config import DetectionConfig
CFG = DetectionConfig()



class DetectThread(QThread):
    log_gerado = Signal(str)
    frame_ready = Signal(np.ndarray)
    contador_atualizado = Signal(int)
    contador_nao_conforme_atualizado = Signal(int)
    contador_total_atualizado = Signal(int)
    sensores_atualizados = Signal(dict)

    def __init__(self, buffer, mutex, condition, running_flag, model_path='datasets/yolov8n.pt'):
        super().__init__()
        self.buffer = buffer
        self.mutex = mutex
        self.condition = condition
        self.running_flag = running_flag
        self.model_path = model_path
        self.model = YOLO(self.model_path)

        self.tracked_ids = {}
        self.imagens_salvas = set()
        self.contador_conforme = 0
        self.contador_naoConforme = 0
        self.contador_total = 0
        self.linha_y = None
        self.sensor = SensorManager()
        self.pausado = False  # inicia despausado

        # Classe conforme / naoConforme vindas do BDL (mantida a lógica)
        config = BDLManager().get_config_data()
        self.conforme = config.get("Classes", "").strip()
        if not self.conforme:
            from PySide6.QtWidgets import QMessageBox, QApplication
            msg = QMessageBox()
            msg.setWindowTitle("Erro crítico")
            msg.setText("❌ Nenhuma classe configurada no banco de dados local. Configure a classe antes de iniciar o sistema.")
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            QApplication.quit()
            return
        self.naoConforme = f"{self.conforme}_nc"
        print(f"[⚙️] Classe conforme: '{self.conforme}' | naoConforme: '{self.naoConforme}'")

    def reset_tracking(self):
        self.tracked_ids.clear()
        self.imagens_salvas.clear()
        self.contador_conforme = 0
        self.contador_naoConforme = 0
        self.contador_total = 0
        self.linha_y = None
        print("[♻️] Rastreamento e contadores internos resetados.")

    @Slot()
    def emitir_sensores(self):
        dados = self.sensor.ler_todos()
        self.sensores_atualizados.emit(dados)

    def run(self):
        print("[🧠] DetectThread iniciada com YOLO + BoT-SORT")

        # Mantém a fluidez e derruba CPU via limite de frequência
        inference_min_interval = 0.18  # ~5-6 fps máx. de inferência
        last_inf_t = 0.0

        # Pular frames: processa 1 a cada 3 (vídeo segue fluido)
        skip_mod = 3
        frame_skip_ctr = 0

        # Cache visual de boxes para não "piscar" (TTL em segundos)
        box_ttl = 0.5
        last_boxes = []        # lista de dicts: {'xyxy':(x1,y1,x2,y2),'label':str,'color':(b,g,r)}
        last_boxes_time = 0.0  # timestamp do último update

        # Restringe classes apenas às necessárias (menos NMS)
        classes_idxs = []
        try:
            names = self.model.names  # pode ser dict {id: name} ou lista
            if isinstance(names, dict):
                for idx, name in names.items():
                    if name == self.conforme or name == self.naoConforme:
                        classes_idxs.append(int(idx))
            else:
                for idx, name in enumerate(names):
                    if name == self.conforme or name == self.naoConforme:
                        classes_idxs.append(int(idx))
        except Exception:
            classes_idxs = []  # fallback: sem filtro se algo der errado

        while self.running_flag[0]:
            if self.pausado:
                time.sleep(0.1)
                continue

            # obtém frame atual do buffer
            self.mutex.lock()
            self.condition.wait(self.mutex, 50)
            frame = self.buffer[0].copy() if self.buffer[0] is not None else None
            self.mutex.unlock()

            if frame is None:
                continue

            height, width = frame.shape[:2]
            if self.linha_y is None:
                self.linha_y = height // 2

            # define se haverá inferência neste frame
            frame_skip_ctr = (frame_skip_ctr + 1) % skip_mod
            do_infer = (frame_skip_ctr == 0)

            # desenha no próprio frame (evita cópia adicional)
            drawn_frame = frame
            cv2.line(drawn_frame, (0, self.linha_y), (width, self.linha_y), (197, 196, 86), 2)

            # Texto + seta (mantidos)
            texto = "Fluxo"
            fonte = cv2.FONT_HERSHEY_SIMPLEX
            escala = 0.6
            espessura = 1
            (tw, th), _ = cv2.getTextSize(texto, fonte, escala, espessura)
            pos_x_texto = width - tw - 20
            pos_y_texto = self.linha_y - 15
            cv2.putText(drawn_frame, texto, (pos_x_texto, pos_y_texto),
                        fonte, escala, (255, 255, 255), espessura, cv2.LINE_AA)
            inicio_seta_x = pos_x_texto + tw + 5
            inicio_seta_y = pos_y_texto - th // 2
            fim_seta_x = inicio_seta_x
            fim_seta_y = self.linha_y - 5
            cv2.arrowedLine(drawn_frame,
                            (inicio_seta_x, inicio_seta_y),
                            (fim_seta_x, fim_seta_y),
                            (255, 255, 255), 1, tipLength=0.3)

            now_global = time.time()

            # Frames sem inferência: redesenha boxes do cache (se ainda válidos) para não piscar
            if not do_infer:
                if last_boxes and (now_global - last_boxes_time) < box_ttl:
                    for b in last_boxes:
                        (x1, y1, x2, y2) = b['xyxy']
                        color = b['color']
                        label = b['label']
                        cv2.rectangle(drawn_frame, (x1, y1), (x2, y2), color, 1)
                        cv2.putText(drawn_frame, label, (x1, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
                self.frame_ready.emit(drawn_frame)
                continue

            # reduz a imagem para a rede (menos custo)
            small = cv2.resize(frame, (256, 192))
            ratio_x = width / 256.0
            ratio_y = height / 192.0

            try:
                # throttle temporal simples
                now = time.time()
                if now - last_inf_t < inference_min_interval:
                    time.sleep(0.005)
                    # mesmo em throttle, redesenha do cache para não piscar
                    if last_boxes and (now_global - last_boxes_time) < box_ttl:
                        for b in last_boxes:
                            (x1, y1, x2, y2) = b['xyxy']
                            color = b['color']
                            label = b['label']
                            cv2.rectangle(drawn_frame, (x1, y1), (x2, y2), color, 1)
                            cv2.putText(drawn_frame, label, (x1, y1 - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
                    self.frame_ready.emit(drawn_frame)
                    continue
                last_inf_t = now

                # inferência + tracking com classes filtradas e max_det reduzido
                with torch.inference_mode():
                    results = self.model.track(
                        small,
                        tracker='botsort.yaml',   # mantido
                        persist=True,
                        verbose=False,
                        conf=0.35,
                        iou=0.5,
                        imgsz=256,               # alinha com o resize acima
                        max_det=25,
                        classes=classes_idxs or None
                    )[0]

            except Exception as e:
                print(f"[❌] Erro durante inferência com tracking: {e}")
                # em caso de erro, tenta redesenhar cache
                if last_boxes and (now_global - last_boxes_time) < box_ttl:
                    for b in last_boxes:
                        (x1, y1, x2, y2) = b['xyxy']
                        color = b['color']
                        label = b['label']
                        cv2.rectangle(drawn_frame, (x1, y1), (x2, y2), color, 1)
                        cv2.putText(drawn_frame, label, (x1, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
                self.frame_ready.emit(drawn_frame)
                continue

            # Atualiza cache com os boxes do frame atual
            current_boxes = []

            # Lógica de contagem/tracking preservada
            if results.boxes is not None:
                for box in results.boxes:
                    if not hasattr(box, 'id') or box.id is None:
                        continue

                    track_id = int(box.id.item())
                    class_id = int(box.cls[0].item())
                    class_name = self.model.names[class_id]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = box.conf[0].item()

                    x1 = int(x1 * ratio_x)
                    x2 = int(x2 * ratio_x)
                    y1 = int(y1 * ratio_y)
                    y2 = int(y2 * ratio_y)
                    centro_y = (y1 + y2) // 2

                    if track_id not in self.tracked_ids:
                        self.tracked_ids[track_id] = {
                            'y_anterior': centro_y,
                            'contado': False,
                            'classe': class_name
                        }

                    dados = self.tracked_ids[track_id]

                    if class_name == self.conforme:
                        if not dados['contado'] and dados['y_anterior'] < self.linha_y <= centro_y:
                            self.contador_conforme += 1
                            self.contador_total += 1
                            self.tracked_ids[track_id]['contado'] = True

                            if track_id not in self.imagens_salvas:
                                # Se quiser salvar SEM overlays, use frame.copy()
                                self._processar_registro_async(frame, self.conforme, track_id, 'Sim')
                                self.imagens_salvas.add(track_id)

                            self.contador_atualizado.emit(self.contador_conforme)
                            self.contador_total_atualizado.emit(self.contador_total)
                            mensagem = f"[✅] Conforme ID {track_id} contado. Total: {self.contador_conforme}"
                            print(mensagem)
                            self.log_gerado.emit(mensagem)
                            QMetaObject.invokeMethod(self, "emitir_sensores", Qt.QueuedConnection)

                        self.tracked_ids[track_id]['y_anterior'] = centro_y
                        cor = (0, 255, 0) if dados['contado'] else (255, 255, 255)
                        label = f"Conforme ID {track_id}"

                    elif class_name == self.naoConforme:
                        if not dados['contado']:
                            self.contador_naoConforme += 1
                            self.contador_total += 1
                            self.tracked_ids[track_id]['contado'] = True

                            if track_id not in self.imagens_salvas:
                                # Se quiser salvar SEM overlays, use frame.copy()
                                self._processar_registro_async(frame, self.naoConforme, track_id, 'Não')
                                self.imagens_salvas.add(track_id)

                            self.contador_nao_conforme_atualizado.emit(self.contador_naoConforme)
                            self.contador_total_atualizado.emit(self.contador_total)
                            mensagem = f"[⚠️] NaoConforme ID {track_id} contado. Total: {self.contador_naoConforme}"
                            print(mensagem)
                            self.log_gerado.emit(mensagem)

                        cor = (0, 0, 255)
                        label = f"NaoConforme ID {track_id}"
                        if track_id not in self.imagens_salvas:
                            # Se quiser salvar SEM overlays, use frame.copy()
                            self._processar_registro_async(frame, self.naoConforme, track_id, 'Não')
                            self.imagens_salvas.add(track_id)

                    elif class_name not in [self.conforme, self.naoConforme]:
                        continue
                    else:
                        cor = (200, 200, 200)
                        label = f"{class_name} ID {track_id}"

                    # Desenho normal
                    cv2.rectangle(drawn_frame, (x1, y1), (x2, y2), cor, 1)
                    cv2.putText(drawn_frame, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)

                    # --- Atualiza cache com o que foi desenhado ---
                    current_boxes.append({
                        'xyxy': (x1, y1, x2, y2),
                        'label': label,
                        'color': cor
                    })

            # Atualiza cache (para frames pulados seguintes)
            last_boxes = current_boxes
            last_boxes_time = time.time()

            self.frame_ready.emit(drawn_frame)

    def _processar_registro_async(self, frame, classe, track_id, conformidade, manual=0):
        import threading
        from core.configmanager import ConfigManager
        from core.operationserial import OperationSerial
        from core.bdlmanager import LocalDatabaseActions

        def tarefa():
            config = ConfigManager()
            modulo_id = config.get("ModuloId")
            config_xml = config.get_tudo()
            operacao_id = OperationSerial.get_serial(modulo_id=modulo_id, configDataXml=config_xml)
            timestamp = datetime.now()
            data_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            nome_arquivo = f"{operacao_id}_{classe}_{track_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            pasta_base = os.path.join("deteccao", operacao_id)
            os.makedirs(pasta_base, exist_ok=True)
            caminho = os.path.join(pasta_base, nome_arquivo)
            cv2.imwrite(caminho, frame)
            print(f"[💾] Imagem salva: {caminho}")

            sensores = self.sensor.ler_todos()

            registro = {
                "Data": data_str,
                "Operacao": operacao_id,
                "Classe": classe,
                "Conformidade": conformidade,
                "Massa": 0,
                "Serial": config.get("Serial"),
                "Imagem": caminho,
                "Temperatura": sensores.get("temperatura", 0),
                "Umidade": sensores.get("umidade", 0),
                "Pressao": sensores.get("pressao", 0),
                "Luminosidade": sensores.get("luminosidade", 0),
                "Manual": manual,
            }

            try:
                bdl = LocalDatabaseActions(config_xml)
                bdl.insert_into_table("Registros", registro)
                bdl.close()
                print(f"[🗃️] Registro salvo com sucesso no banco de dados local: {registro}")
            except Exception as e:
                print(f"[❌] Erro ao salvar registro no banco local: {e}")

        threading.Thread(target=tarefa, daemon=True).start()

    @Slot()
    def incrementar_nao_conforme_manual(self):
        # 1) Incrementa contadores (mesma semântica já usada no botão)
        self.contador_naoConforme += 1
        self.contador_total += 1

        # 2) Atualiza a UI pelos sinais já existentes
        self.contador_nao_conforme_atualizado.emit(self.contador_naoConforme)
        self.contador_total_atualizado.emit(self.contador_total)
        QMetaObject.invokeMethod(self, "emitir_sensores", Qt.QueuedConnection)

        # 3) Insere na tabela Registros do BDL (frame preto 640x480)
        altura, largura = 480, 640
        frame_vazio = np.zeros((altura, largura, 3), dtype=np.uint8)
        classe_nc = self.naoConforme
        track_id_manual = 99999

        self._processar_registro_async(
            frame_vazio,
            classe_nc,
            track_id_manual,
            "Não",
            manual=1
        )

        # 4) Log
        self.log_gerado.emit("[🖐️] NaoConforme (manual) incrementado e registrado (tecla/pedal).")

    def pause(self):
        print("[⏸️] DetectThread pausada.")
        self.pausado = True

    def resume(self):
        print("[▶️] DetectThread retomada.")
        self.pausado = False

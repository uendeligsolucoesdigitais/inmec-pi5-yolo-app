# core/audio_player.py
# -*- coding: utf-8 -*-
"""
Classe utilitária para reprodução assíncrona de trechos MP3.
- Reproduz arquivos a partir da pasta /mp3.
- Executa a reprodução em thread separada para não travar a UI/vídeo.
- Se o arquivo não for encontrado, apenas notifica (terminal e rodapé) e segue.
- Em Raspberry Pi 5, prioriza reprodução via ALSA (mpg123), compatível com HAT WM8960.
- Tenta reprodução *somente Python* com pygame antes de qualquer executável externo.
"""

from __future__ import annotations

import os
import sys
import time
import threading
import subprocess
from typing import Callable, Optional
from shutil import which


class AudioPlayer:
    """
    AudioPlayer(mp3_dir='mp3', status_callback=None, status_duration_ms=3000, alsa_device='default')
      - mp3_dir: pasta onde ficam os arquivos MP3 (relativa ao cwd do app).
      - status_callback: callable opcional (mensagem:str, duracao_ms:int) -> None para exibir no rodapé.
      - status_duration_ms: duração padrão das mensagens de status (rodapé).
      - alsa_device: nome do device ALSA (se desejar direcionar; por padrão usa 'default').
    """

    # --- Controle global (classe) ---
    _volume: int = 70       # 0..100
    _muted: bool = False    # estado de mute global

    # ---- Mute ----
    @classmethod
    def is_muted(cls) -> bool:
        return bool(cls._muted)

    @classmethod
    def set_muted(cls, value: bool) -> None:
        cls._muted = bool(value)

    @classmethod
    def toggle_mute(cls) -> bool:
        cls._muted = not cls._muted
        return cls._muted

    # ---- Volume (0-100) ----
    @classmethod
    def get_volume(cls) -> int:
        return int(getattr(cls, "_volume", 70))

    @classmethod
    def set_volume(cls, value: int) -> int:
        v = max(0, min(100, int(value)))
        cls._volume = v
        # Aplica ao pygame, se ativo
        try:
            import pygame  # type: ignore
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(v / 100.0)
        except Exception:
            pass
        return cls._volume

    @classmethod
    def increase_volume(cls, step: int = 5) -> int:
        return cls.set_volume(cls.get_volume() + step)

    @classmethod
    def decrease_volume(cls, step: int = 5) -> int:
        return cls.set_volume(cls.get_volume() - step)

    # ---- Instância ----
    def __init__(
        self,
        mp3_dir: str = "mp3",
        status_callback: Optional[Callable[[str, int], None]] = None,
        status_duration_ms: int = 3000,
        alsa_device: str = "default",
    ) -> None:
        self.mp3_dir = mp3_dir
        self.status_callback = status_callback
        self.status_duration_ms = status_duration_ms
        self.alsa_device = alsa_device
        self._threads = set()        # rastreia threads iniciadas (opcional)
        self._lock = threading.Lock()

    # ------------------------- API pública -------------------------
    def playmp3(self, filename: str) -> None:
        """
        Inicia a reprodução de um arquivo MP3 em uma thread separada.
        'filename' deve ser o nome do arquivo (com ou sem extensão .mp3).
        Não bloqueia a aplicação.
        """
        if not filename:
            self._notify("⚠️ Nome de arquivo MP3 vazio.", self.status_duration_ms)
            return

        if not filename.lower().endswith(".mp3"):
            filename = f"{filename}.mp3"

        full_path = os.path.join(self.mp3_dir, filename)

        # Respeita mute global
        if AudioPlayer.is_muted():
            self._notify("🔇 Áudio mutado — ignorando reprodução.", self.status_duration_ms)
            return

        t = threading.Thread(target=self._worker_play, args=(full_path,), daemon=True)
        t.start()
        with self._lock:
            self._threads.add(t)

    # ------------------------- Internos ----------------------------
    def _play_with_pygame(self, full_path: str) -> bool:
        """
        Tenta reproduzir MP3 usando somente Python (pygame).
        Retorna True em caso de início de reprodução com sucesso.
        Não bloqueia a thread chamadora.
        """
        try:
            # Em Linux/RPi, usa ALSA (útil para HAT WM8960)
            if sys.platform.startswith("linux"):
                os.environ.setdefault("SDL_AUDIODRIVER", "alsa")
            import pygame  # type: ignore
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            # Aplica volume atual
            pygame.mixer.music.set_volume(AudioPlayer.get_volume() / 100.0)
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()
            return True
        except Exception:
            return False

    def _worker_play(self, full_path: str) -> None:
        if not os.path.isfile(full_path):
            self._notify(f"🔇 Arquivo MP3 não encontrado: {full_path}", self.status_duration_ms)
            return

        try:
            # 1) Python-only primeiro (pygame)
            if self._play_with_pygame(full_path):
                return

            # 2) Em Raspberry Pi 5, preferir mpg123 (ALSA), depois VLCs e python-vlc
            if self._is_raspberry_pi_5():
                if which("mpg123"):
                    cmd = ["mpg123", "-q", full_path]
                    subprocess.run(cmd, check=False)
                    return
                if which("cvlc"):
                    subprocess.run(["cvlc", "--quiet", "--play-and-exit", full_path], check=False)
                    return
                if which("vlc"):
                    subprocess.run(["vlc", "--intf", "dummy", "--play-and-exit", full_path], check=False)
                    return
                try:
                    import vlc  # type: ignore
                    player = vlc.MediaPlayer(full_path)
                    player.play()
                    time.sleep(0.1)
                    while True:
                        state = player.get_state()
                        if state in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
                            break
                        time.sleep(0.1)
                    return
                except Exception:
                    pass  # segue para fallback genérico

            # 3) Fallback genérico (não-RPi)
            if which("cvlc"):
                subprocess.run(["cvlc", "--quiet", "--play-and-exit", full_path], check=False)
                return
            if which("vlc"):
                subprocess.run(["vlc", "--intf", "dummy", "--play-and-exit", full_path], check=False)
                return
            try:
                import vlc  # type: ignore
                player = vlc.MediaPlayer(full_path)
                player.play()
                time.sleep(0.1)
                while True:
                    state = player.get_state()
                    if state in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
                        break
                    time.sleep(0.1)
                return
            except Exception:
                # Último fallback: informa e segue sem travar
                self._notify("🔇 Não há backend disponível para reproduzir MP3 (pygame/mpg123/cvlc/vlc/python-vlc).", self.status_duration_ms)

        except Exception as e:
            # Nunca travar a aplicação por erro de áudio
            self._notify(f"❌ Erro ao reproduzir áudio: {e}", self.status_duration_ms)

    # ------------------------- Verificações de dispositivo ------------------
    def check_audio_device(self):
        """
        Verifica a existência de dispositivo(s) de saída de áudio.
        Retorna (ok: bool, mensagem: str, is_rpi5: bool).
        - Detecta SO (Windows/macOS/Linux).
        - Em Raspberry Pi 5, tenta identificar o HAT WM8960 (via ALSA) e opcionalmente
          importar a biblioteca correspondente se disponível.
        """
        is_rpi5 = self._is_raspberry_pi_5()
        try:
            if sys.platform.startswith("linux"):
                # Verifica dispositivos ALSA via 'aplay -l'
                try:
                    proc = subprocess.run(["aplay", "-l"], capture_output=True, text=True, check=False)
                    out = (proc.stdout or "") + (proc.stderr or "")
                    has_card = "card " in out.lower()
                    has_wm8960 = "wm8960" in out.lower()
                    if is_rpi5 and has_wm8960:
                        try:
                            import wm8960  # type: ignore
                            lib_info = "biblioteca wm8960 importada"
                        except Exception:
                            lib_info = "biblioteca wm8960 ausente (ok, driver ALSA basta)"
                        return True, f"ALSA detectado. HAT WM8960 presente ({lib_info}).", True
                    if has_card:
                        return True, "Dispositivo(s) ALSA detectado(s).", is_rpi5
                    if which("cvlc") or which("vlc") or which("mpg123"):
                        return True, "Sem listagem ALSA, mas player instalado (cvlc/vlc/mpg123) disponível.", is_rpi5
                    return False, "Nenhum dispositivo ALSA encontrado (aplay -l vazio).", is_rpi5
                except Exception as e:
                    return False, f"Falha ao consultar ALSA (aplay): {e}", is_rpi5

            elif sys.platform.startswith("win"):
                # Windows: consulta WMI via PowerShell
                try:
                    ps = r"(Get-CimInstance Win32_SoundDevice | Where-Object { $_.Status -eq 'OK' } | Measure-Object).Count"
                    proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, check=False)
                    try:
                        count = int((proc.stdout or '0').strip())
                    except Exception:
                        count = 0
                    if count > 0:
                        return True, f"{count} dispositivo(s) de som OK via WMI.", is_rpi5
                    return False, "Nenhum dispositivo de som OK via WMI.", is_rpi5
                except Exception as e:
                    return False, f"Falha ao consultar WMI/PowerShell: {e}", is_rpi5

            elif sys.platform == "darwin":
                # macOS: usa system_profiler
                try:
                    proc = subprocess.run(["system_profiler", "SPAudioDataType", "-detailLevel", "mini"],
                                          capture_output=True, text=True, check=False)
                    out = (proc.stdout or "").lower()
                    if "output" in out or "device" in out:
                        return True, "Dispositivo(s) de áudio detectado(s) no macOS.", is_rpi5
                    return False, "Nenhum dispositivo de áudio detectado no macOS.", is_rpi5
                except Exception as e:
                    return False, f"Falha ao consultar system_profiler: {e}", is_rpi5

            else:
                return False, f"SO não reconhecido para teste: {sys.platform}", is_rpi5

        except Exception as e:
            return False, f"Erro inesperado no teste de áudio: {e}", is_rpi5

    # ------------------------- Utilidades --------------------------
    def _notify(self, message: str, duration_ms: int) -> None:
        # Terminal
        print(message)
        # Rodapé (se callback fornecido) — somente na thread principal (evita avisos do Qt)
        import threading as _threading
        if callable(self.status_callback) and _threading.current_thread() is _threading.main_thread():
            try:
                self.status_callback(message, duration_ms)
            except Exception:
                pass

    @staticmethod
    def _is_raspberry_pi_5() -> bool:
        """
        Heurística rápida para detectar Raspberry Pi 5.
        Pi 5 usa SoC BCM2712; também aceitamos presença da string 'Raspberry Pi'.
        """
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().lower()
            return ("raspberry pi" in text) or ("bcm2712" in text)
        except Exception:
            return False

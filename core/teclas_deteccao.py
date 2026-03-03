# core/teclas_deteccao.py
from PySide6.QtCore import QObject, Qt, QTimer, QEvent
from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter, QColor
from core.configmanager import ConfigManager
from core.audio_player import AudioPlayer

DETECCAO_SVG_PATH = "img/svg/teclado.svg"
PEDAL_SVG_PATH    = "img/svg/pedal.svg"

MIN_OVERLAY_MS = 300
MAX_OVERLAY_MS = 5000
STEP_OVERLAY_MS = 250


class TeclasDeteccaoToast(QObject):
    """
    Captura teclas no 'parent' (ContentWidget):
      - ESPAÇO: incrementa NC e exibe deteccao.svg (overlay vermelho, centralizado no vídeo)
      - P:       simula pedal: incrementa NC e exibe pedal.svg (overlay vermelho)
      - O:       alterna overlay on/off
      - [:       diminui duração do overlay (-250ms, mín. 300ms)
      - ]:       aumenta duração do overlay (+250ms, máx. 5000ms)

    O ícone é overlay (QLabel) sobre o video_widget (não desenha no frame).
    Preferências podem vir do config.xml:
      - DETECTION_OVERLAY_ENABLED (1/0/true/false)
      - DETECTION_OVERLAY_MS (inteiro em ms)
    """

    def __init__(self, parent: QWidget, dashboard_widget: QWidget, detect_thread_provider, video_widget: QWidget = None):
        super().__init__(parent)
        self.parent = parent
        self.dashboard_widget = dashboard_widget  # compat
        self.detect_thread_provider = detect_thread_provider
        self.video_widget = video_widget
        self._toast = None  # QLabel overlay

        # Preferências (com fallback)
        cfg = ConfigManager()
        # overlay enabled
        raw_en = str(cfg.get("DETECTION_OVERLAY_ENABLED") or "").strip().lower()
        if raw_en in ("1", "true", "yes", "on"):
            self.overlay_enabled = True
        elif raw_en in ("0", "false", "no", "off"):
            self.overlay_enabled = False
        else:
            self.overlay_enabled = True  # default

        # overlay duration
        try:
            self.overlay_ms = int(cfg.get("DETECTION_OVERLAY_MS") or 2000)
        except Exception:
            self.overlay_ms = 2000
        self.overlay_ms = max(MIN_OVERLAY_MS, min(MAX_OVERLAY_MS, self.overlay_ms))

    def instalar(self):
        # foco e filtros de evento
        self.parent.setFocusPolicy(Qt.StrongFocus)
        self.parent.setFocus()
        self.parent.installEventFilter(self)
        if self.video_widget is not None:
            self.video_widget.installEventFilter(self)

    # ---------- Event Filter ----------
    def eventFilter(self, obj, event):
        # teclas
        if obj is self.parent and event.type() == QEvent.KeyPress:
            key = event.key()

            if key == Qt.Key_Space:       # fluxo manual "deteccao"
                self._incrementar_nao_conforme()
                self._mostrar_icone_deteccao()
                return True

            if key == Qt.Key_P:           # simular pedal
                self._incrementar_nao_conforme()
                self._mostrar_icone_pedal()
                return True

            if key == Qt.Key_O:           # toggle overlay
                self.overlay_enabled = not self.overlay_enabled
                print(f"[🎛️] Overlay {'ON' if self.overlay_enabled else 'OFF'}")
                return True

            if key == Qt.Key_BracketLeft:  # diminuir duração
                before = self.overlay_ms
                self.overlay_ms = max(MIN_OVERLAY_MS, self.overlay_ms - STEP_OVERLAY_MS)
                if self.overlay_ms != before:
                    print(f"[⏱️] Overlay: {self.overlay_ms} ms")
                return True

            if key == Qt.Key_BracketRight:  # aumentar duração
                before = self.overlay_ms
                self.overlay_ms = min(MAX_OVERLAY_MS, self.overlay_ms + STEP_OVERLAY_MS)
                if self.overlay_ms != before:
                    print(f"[⏱️] Overlay: {self.overlay_ms} ms")
                return True
            # ----- Áudio: mute e volume -----
            if key == Qt.Key_M:
                muted = AudioPlayer.toggle_mute()
                if muted:
                    self._status_msg("🔇 Áudio em mute.", 3000)
                    try:
                        main_win = self.parent.window()
                        top = getattr(main_win, "top_bar", None)
                        if top and hasattr(top, "set_status_icon"):
                            top.set_status_icon("audio", "erro")  # vermelho
                        if top and hasattr(top, "set_custom_icon"):
                            top.set_custom_icon("audio", "img/svg/mute.svg")
                    except Exception:
                        pass
                else:
                    self._status_msg("🔊 Áudio habilitado.", 3000)
                    try:
                        main_win = self.parent.window()
                        top = getattr(main_win, "top_bar", None)
                        if top and hasattr(top, "set_status_icon"):
                            top.set_status_icon("audio", "ok")    # verde
                        if top and hasattr(top, "set_custom_icon"):
                            top.set_custom_icon("audio", "img/svg/audio.svg")
                    except Exception:
                        pass
                    try:
                        AudioPlayer(mp3_dir="mp3").playmp3("tom.mp3")
                    except Exception:
                        pass
                return True

            if key in (Qt.Key_Plus, Qt.Key_Equal):
                new_v = AudioPlayer.increase_volume(5)
                self._status_msg(f"🔊 Volume: {new_v}%", 2000)
                try:
                    AudioPlayer(mp3_dir="mp3").playmp3("tom.mp3")
                except Exception:
                    pass
                return True

            if key in (Qt.Key_Minus, Qt.Key_Underscore):
                new_v = AudioPlayer.decrease_volume(5)
                self._status_msg(f"🔉 Volume: {new_v}%", 2000)
                try:
                    AudioPlayer(mp3_dir="mp3").playmp3("tom.mp3")
                except Exception:
                    pass
                return True


        # manter centralizado no resize do vídeo
        if obj is self.video_widget and event.type() == QEvent.Resize:
            if self._toast and self._toast.isVisible():
                icon_w, icon_h = self._toast.width(), self._toast.height()
                x = (self.video_widget.width()  - icon_w) // 2
                y = (self.video_widget.height() - icon_h) // 2
                self._toast.move(x, y)
            return False

        return super().eventFilter(obj, event)


    def _status_msg(self, text: str, ms: int = 3000):
        """
        Mostra mensagem no rodapé (se disponível) e sempre no terminal.
        Executa na thread da UI (chamado a partir do eventFilter).
        """
        try:
            sb = getattr(self.parent, "status_bar", None)
            if sb is not None and hasattr(sb, "showMessage"):
                sb.showMessage(text, ms)
        except Exception:
            pass
        print(text)

    # ---------- Ações ----------
    def _incrementar_nao_conforme(self):
        try:
            thread = self.detect_thread_provider() if callable(self.detect_thread_provider) else None
            if thread is not None:
                # método público já trata contadores, DB, sensores e log
                thread.incrementar_nao_conforme_manual()
        except Exception as e:
            print(f"[⚠️] Falha ao incrementar 'Não Conforme' manualmente: {e}")

    def _mostrar_icone_deteccao(self):
        self._mostrar_icone_overlay(DETECCAO_SVG_PATH)

    def _mostrar_icone_pedal(self):
        self._mostrar_icone_overlay(PEDAL_SVG_PATH)

    def _mostrar_icone_overlay(self, svg_path: str):
        if not self.overlay_enabled:
            return
        try:
            overlay_parent = self.video_widget if self.video_widget is not None else self.parent

            # (Re)cria o QLabel se necessário / parent mudou
            if self._toast is None or self._toast.parent() is not overlay_parent:
                if self._toast is not None and self._toast.parent() is not overlay_parent:
                    self._toast.deleteLater()
                self._toast = QLabel(overlay_parent)
                self._toast.setAttribute(Qt.WA_TranslucentBackground)
                self._toast.setAttribute(Qt.WA_TransparentForMouseEvents)
                self._toast.setStyleSheet("background: transparent;")
                self._toast.setVisible(False)

            # render do SVG
            icon_w, icon_h = 72, 72
            base = QPixmap(icon_w, icon_h)
            base.fill(Qt.transparent)

            renderer = QSvgRenderer(svg_path)
            p = QPainter(base)
            renderer.render(p)
            p.end()

            # tint vermelho preservando alfa
            tinted = QPixmap(base.size())
            tinted.fill(Qt.transparent)
            p = QPainter(tinted)
            p.drawPixmap(0, 0, base)
            p.setCompositionMode(QPainter.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QColor(255, 0, 0))
            p.end()

            self._toast.setPixmap(tinted)
            self._toast.resize(icon_w, icon_h)

            # centraliza
            x = (overlay_parent.width()  - icon_w) // 2
            y = (overlay_parent.height() - icon_h) // 2
            self._toast.move(x, y)
            self._toast.raise_()
            self._toast.setVisible(True)

            QTimer.singleShot(self.overlay_ms, lambda: self._toast.setVisible(False))

        except Exception as e:
            print(f"[⚠️] Erro ao exibir ícone (overlay): {e}")

# core/pedal_input.py
from PySide6.QtCore import QObject, Qt, QTimer, QEvent
from PySide6.QtWidgets import QLabel, QWidget, QMessageBox, QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter, QColor
from core.configmanager import ConfigManager
import time

from config.config import PedalInputConfig
CFG = PedalInputConfig()
SVG_PATH = CFG.svg_path
MIN_OVERLAY_MS = CFG.min_overlay_ms
MAX_OVERLAY_MS = CFG.max_overlay_ms


class PedalWatcher(QObject):
    """
    Observa um pino GPIO (BCM) do Raspberry Pi 5 e, a cada transição 1->0 (queda):
      - incrementa 'Não Conforme' via detect_thread.incrementar_nao_conforme_manual()
      - exibe um overlay (pedal.svg) centralizado sobre o video_widget
    Debounce mínimo configurado no construtor (padrão 300ms).
    Overlay: controlado por DETECTION_OVERLAY_ENABLED e DETECTION_OVERLAY_MS no config.xml.
    """

    def __init__(self, parent: QWidget, dashboard_widget: QWidget, detect_thread_provider, video_widget: QWidget = None, debounce_ms: int = 300):
        super().__init__(parent)
        self.parent = parent
        self.dashboard_widget = dashboard_widget
        self.detect_thread_provider = detect_thread_provider
        self.video_widget = video_widget
        self.debounce_ms = debounce_ms

        self._toast = None
        self._btn = None
        self._active = False
        self._last_ts = 0.0
        self.pin_bcm = None
        self._chip = None
        self._line = None
        self._poll_timer = None
        self._last_gpio_value = 1  # repouso = nível alto

        # preferências de overlay (config)
        cfg = ConfigManager()
        raw_en = str(cfg.get("DETECTION_OVERLAY_ENABLED") or "").strip().lower()
        if raw_en in CFG.truthy_values:
            self.overlay_enabled = True
        elif raw_en in CFG.falsy_values:
            self.overlay_enabled = False
        else:
            self.overlay_enabled = True  # default

        try:
            self.overlay_ms = int(cfg.get("DETECTION_OVERLAY_MS") or CFG.overlay_ms_default)
        except Exception:
            self.overlay_ms = 2000
        self.overlay_ms = max(MIN_OVERLAY_MS, min(MAX_OVERLAY_MS, self.overlay_ms))

    def start(self):
        """Lê PIN do config.xml e inicializa o hardware do pedal."""
        cfg = ConfigManager()
        pin_str = str(cfg.get("PIN_PEDAL_BCM") or "").strip()

        if not pin_str.isdigit():
            msg = QMessageBox()
            msg.setWindowTitle(CFG.msg_cfg_title)
            msg.setText(CFG.msg_cfg_pin_missing)
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            QApplication.quit()
            return

        self.pin_bcm = int(pin_str)

        if self.video_widget is not None:
            self.video_widget.installEventFilter(self)

        # Inicializa GPIO via gpiod (mesma abordagem validada em monitor_gpio8.py)
        try:
            import gpiod
            self._chip = gpiod.Chip("/dev/gpiochip0")
            self._line = self._chip.get_line(self.pin_bcm)
            self._line.request(consumer="pedal-watcher", type=gpiod.LINE_REQ_DIR_IN)
            self._last_gpio_value = int(self._line.get_value())
            self._poll_timer = QTimer()
            self._poll_timer.timeout.connect(self._poll_gpio)
            self._poll_timer.start(100)
            self._active = True
            print(CFG.msg_active_ok.format(pin=self.pin_bcm, debounce=self.debounce_ms))
        except Exception as e:
            self._chip = None
            self._line = None
            self._active = False
            print(CFG.msg_disabled_info.format(e=e))

    def stop(self):
        """Libera recursos do hardware."""
        try:
            if self._poll_timer is not None:
                self._poll_timer.stop()
        except Exception:
            pass
        try:
            if self._line is not None:
                self._line.release()
        except Exception:
            pass
        try:
            if self._chip is not None:
                self._chip.close()
        except Exception:
            pass
        finally:
            self._poll_timer = None
            self._line = None
            self._chip = None
            self._active = False

    def _poll_gpio(self):
        """Detecta borda de descida (1->0) no pino do pedal."""
        try:
            value = int(self._line.get_value())
            if self._last_gpio_value == 1 and value == 0:
                self._on_falling_edge()
            self._last_gpio_value = value
        except Exception:
            pass

    # manter overlay centralizado no resize do vídeo
    def eventFilter(self, obj, event):
        if obj is self.video_widget and event.type() == QEvent.Resize:
            if self._toast and self._toast.isVisible():
                icon_w, icon_h = self._toast.width(), self._toast.height()
                x = (self.video_widget.width()  - icon_w) // 2
                y = (self.video_widget.height() - icon_h) // 2
                self._toast.move(x, y)
        return super().eventFilter(obj, event)

    # callback do pedal (1->0)
    def _on_falling_edge(self):
        now = time.monotonic()
        if (now - self._last_ts) * 1000.0 < self.debounce_ms:
            return  # respeita intervalo mínimo
        self._last_ts = now
        self._incrementar_nc()
        self._mostrar_toast()

    # ações
    def _incrementar_nc(self):
        try:
            thread = self.detect_thread_provider() if callable(self.detect_thread_provider) else None
            if thread is not None:
                thread.incrementar_nao_conforme_manual()
        except Exception as e:
            print(CFG.msg_fail_incrementar.format(e=e))

    def _mostrar_toast(self):
        if not self.overlay_enabled:
            return
        try:
            overlay_parent = self.video_widget if self.video_widget is not None else self.parent

            if self._toast is None or self._toast.parent() is not overlay_parent:
                if self._toast is not None and self._toast.parent() is not overlay_parent:
                    self._toast.deleteLater()
                self._toast = QLabel(overlay_parent)
                self._toast.setAttribute(Qt.WA_TranslucentBackground)
                self._toast.setAttribute(Qt.WA_TransparentForMouseEvents)
                self._toast.setStyleSheet(CFG.overlay_stylesheet)
                self._toast.setVisible(False)

            # render do SVG
            icon_w, icon_h = CFG.overlay_icon_w, CFG.overlay_icon_h
            base = QPixmap(icon_w, icon_h)
            base.fill(Qt.transparent)

            renderer = QSvgRenderer(SVG_PATH)
            p = QPainter(base)
            renderer.render(p)
            p.end()

            # tint vermelho
            tinted = QPixmap(base.size())
            tinted.fill(Qt.transparent)
            p = QPainter(tinted)
            p.drawPixmap(0, 0, base)
            p.setCompositionMode(QPainter.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QColor(CFG.overlay_tint_r, CFG.overlay_tint_g, CFG.overlay_tint_b))
            p.end()

            self._toast.setPixmap(tinted)
            self._toast.resize(icon_w, icon_h)

            x = (overlay_parent.width()  - icon_w) // 2
            y = (overlay_parent.height() - icon_h) // 2
            self._toast.move(x, y)
            self._toast.raise_()
            self._toast.setVisible(True)

            QTimer.singleShot(self.overlay_ms, lambda: self._toast.setVisible(False))

        except Exception as e:
            print(CFG.msg_fail_overlay.format(e=e))

import builtins
import sys

_ORIGINAL_PRINT = builtins.print


def install_statusbar_print_hook(status_bar, duration_ms: int = 5000):
    def hooked_print(*args, **kwargs):
        _ORIGINAL_PRINT(*args, **kwargs)
        try:
            target = kwargs.get("file", None)
            if target not in (None, sys.stdout, sys.stderr):
                return
            text = " ".join(str(a) for a in args)
            if status_bar and hasattr(status_bar, "showMessage"):
                try:
                    from PySide6.QtWidgets import QApplication
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                    app = QApplication.instance()
                    if app and app.thread() is not None and app.thread() != status_bar.thread():
                        QMetaObject.invokeMethod(
                            status_bar,
                            "showMessage",
                            Qt.QueuedConnection,
                            Q_ARG(str, text),
                            Q_ARG(int, duration_ms),
                        )
                    else:
                        status_bar.showMessage(text, duration_ms)
                except Exception:
                    status_bar.showMessage(text, duration_ms)
        except Exception:
            pass

    builtins.print = hooked_print


def restore_print():
    builtins.print = _ORIGINAL_PRINT

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
import sys

# ===== Bootstrap: permitir execução de dentro de ui/ e a partir da raiz =====
def _ensure_project_path_for_ui_import():
    try:
        here = os.path.abspath(os.path.dirname(__file__))
    except NameError:
        return
    parent = os.path.abspath(os.path.join(here, os.pardir))
    grandp = os.path.abspath(os.path.join(parent, os.pardir))
    for base in (parent, grandp):
        ui_dir = os.path.join(base, "ui")
        if os.path.isdir(ui_dir) and base not in sys.path:
            sys.path.insert(0, base)

_ensure_project_path_for_ui_import()

# ===== Imports tolerantes (ui.* primeiro; fallback local com sys.path do diretório) =====
try:
    from ui.report_viewer_shared import read_config_xml_for_sqlite  # noqa: F401
    from ui.report_viewer_ReportManager import ReportManager
    from ui.report_viewer_ReportWindow import ReportWindow
except Exception:
    # garante que a pasta onde este arquivo está (ui/) esteja no sys.path
    try:
        _here = os.path.abspath(os.path.dirname(__file__))
        if _here not in sys.path:
            sys.path.insert(0, _here)
    except Exception:
        pass
    from report_viewer_shared import read_config_xml_for_sqlite  # noqa: F401
    from report_viewer_ReportManager import ReportManager
    from report_viewer_ReportWindow import ReportWindow

from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)

    sqlite_env = os.environ.get("INMEC_SQLITE", None)
    manager = ReportManager(sqlite_path=sqlite_env)

    win = ReportWindow(manager=manager)
    win.showFullScreen()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

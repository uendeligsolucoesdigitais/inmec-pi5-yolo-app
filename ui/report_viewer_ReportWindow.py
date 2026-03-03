#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
import sys
import csv
import traceback
from typing import List, Any, Optional, Tuple, Set

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction, QKeySequence, QTextDocument, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QDateEdit, QPushButton, QTableView, QFileDialog,
    QMessageBox, QStatusBar, QDialog, QLineEdit, QToolButton, QMenu, QFrame, QHeaderView
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

# Imports tolerantes (pacote ui.* primeiro; fallback local)
try:
    from ui.report_viewer_shared import (
        carregar_svg_branco, resource_path, human_dt, parse_float, read_config_xml_for_sqlite
    )
    from ui.report_viewer_ReportManager import ReportManager
    from ui.report_viewer_StatChip import StatChip
    from ui.report_viewer_FancyProxy import FancyProxy
    from ui.report_viewer_SettingsDialog import SettingsDialog
    from ui.report_viewer_SqlEditorDialog import SqlEditorDialog  # pronto para uso futuro
except Exception:
    from report_viewer_shared import (
        carregar_svg_branco, resource_path, human_dt, parse_float, read_config_xml_for_sqlite
    )
    from report_viewer_ReportManager import ReportManager
    from report_viewer_StatChip import StatChip
    from report_viewer_FancyProxy import FancyProxy
    from report_viewer_SettingsDialog import SettingsDialog
    from report_viewer_SqlEditorDialog import SqlEditorDialog

class ReportWindow(QMainWindow):
    def __init__(self, manager: Optional[ReportManager] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Relatórios InMEC")
        self.resize(1280, 800)
        self.setStyleSheet("""
            QMainWindow { background:#2E4459; }
            QLabel { color: #e8f0f6; }
            QComboBox, QDateEdit, QLineEdit {
                background:#162635; color:#e8f0f6; border:1px solid #3f5a73; border-radius:8px; padding:6px;
            }
            QPushButton {
                background: transparent; color: #e8f0f6; border:1px solid #e8f0f6; border-radius:8px; padding:8px 14px;
                qproperty-iconSize: 18px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
            QTableView {
                background:#192b3b; color:#e8f0f6; gridline-color:#35526a; selection-background-color:#2f6ea5;
                alternate-background-color:#1e3345; border:1px solid #3f5a73; border-radius:10px;
            }
            QHeaderView::section {
                background:#27425a; color:#e8f0f6; padding:8px; border: none; border-right:1px solid #3f5a73;
            }
            QStatusBar { color:#cfe2f3; }
            QMenu { background:#162635; color:#e8f0f6; border:1px solid #3f5a73; }
            QMenu::item:selected { background:#27425a; }
        """)

        self.manager = manager or ReportManager(sqlite_path=None)
        if not self.manager.get_sqlite_path():
            auto = read_config_xml_for_sqlite("/config")
            if auto:
                self.manager.set_sqlite_path(auto)

        central = QWidget(self); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(16,16,16,16); root.setSpacing(12)
        self.status = QStatusBar(self); self.setStatusBar(self.status)

        # ----- Top bar -----
        self._build_topbar(root)

        # ----- Filtros + Busca -----
        self._build_filters(root)

        # ----- Métricas -----
        self._build_metrics(root)

        # ----- Tabela -----
        self._build_table(root)

        # ----- Rodapé (Exportar / Imprimir) -----
        self._build_footer(root)

        # Atalhos
        self._setup_shortcuts()

        self.status.showMessage("Relatórios prontos.")

    # -- Top bar --
    def _build_topbar(self, root_layout: QVBoxLayout):
        top = QHBoxLayout()
        left = QHBoxLayout()

        logo = QLabel()
        pm = QPixmap()
        logo_png = resource_path("img/logo.png")
        logo_svg = resource_path("img/svg/logo.svg")

        if os.path.isfile(logo_png):
            pm = QPixmap(logo_png).scaledToHeight(50, Qt.SmoothTransformation)
        elif os.path.isfile(logo_svg):
            icon = carregar_svg_branco(logo_svg, tamanho=50)
            pm = icon.pixmap(50, 50)

        if not pm.isNull():
            logo.setPixmap(pm)
            logo.setFixedSize(pm.size())
        else:
            logo.setText("📊")

        title = QLabel("Relatórios")
        title.setStyleSheet("font-size:18px; font-weight:700;")

        left.addWidget(logo)
        left.addSpacing(8)
        left.addWidget(title)

        right = QHBoxLayout()
        self.btn_voltar = QPushButton("Voltar")
        self.btn_sair   = QPushButton("Sair")
        self.btn_voltar.setIcon(carregar_svg_branco(resource_path("img/svg/voltar.svg"), tamanho=18))
        self.btn_sair.setIcon(carregar_svg_branco(resource_path("img/svg/sair.svg"), tamanho=18))
        for b in (self.btn_voltar, self.btn_sair):
            b.setMinimumHeight(36)

        right.addWidget(self.btn_voltar)
        right.addSpacing(8)
        right.addWidget(self.btn_sair)

        top.addLayout(left, 0)
        top.addStretch(1)
        top.addLayout(right, 0)
        root_layout.addLayout(top)

        self.btn_voltar.clicked.connect(self.on_voltar)
        self.btn_sair.clicked.connect(self.on_sair)

    # -- Filtros --
    def _build_filters(self, root_layout: QVBoxLayout):
        box = QFrame(); box.setObjectName("FilterBox")
        box.setStyleSheet("""
            QFrame#FilterBox { background:#314b61; border:1px solid #5f7a92; border-radius:12px; }
        """)
        gl = QGridLayout(box); gl.setContentsMargins(12,12,12,12); gl.setHorizontalSpacing(10); gl.setVerticalSpacing(8)

        lbl_type = QLabel("Tipo:")
        self.cb_type = QComboBox(); self.cb_type.addItems(["Producao","Sensores","Cameras"])
        try:
            self.cb_type.setItemIcon(0, carregar_svg_branco(resource_path("img/svg/producao.svg"), tamanho=18))
            self.cb_type.setItemIcon(1, carregar_svg_branco(resource_path("img/svg/sensores.svg"), tamanho=18))
            self.cb_type.setItemIcon(2, carregar_svg_branco(resource_path("img/svg/cameras.svg"), tamanho=18))
        except Exception:
            pass

        lbl_ini = QLabel("Início:")
        self.dt_ini = QDateEdit(); self.dt_ini.setDisplayFormat("yyyy-MM-dd"); self.dt_ini.setCalendarPopup(True); self.dt_ini.setDate(QDate.currentDate().addMonths(-1))

        lbl_fim = QLabel("Fim:")
        self.dt_fim = QDateEdit(); self.dt_fim.setDisplayFormat("yyyy-MM-dd"); self.dt_fim.setCalendarPopup(True); self.dt_fim.setDate(QDate.currentDate())

        self.btn_load  = QPushButton("Carregar")
        self.btn_clear = QPushButton("Limpar")
        self.btn_load.setIcon(carregar_svg_branco(resource_path("img/svg/carregar.svg"), tamanho=18))
        self.btn_clear.setIcon(carregar_svg_branco(resource_path("img/svg/limpar.svg"), tamanho=18))

        lbl_busca = QLabel("Buscar:")
        self.ed_busca = QLineEdit(); self.ed_busca.setPlaceholderText("Filtrar resultados...")
        try:
            self.ed_busca.addAction(carregar_svg_branco(resource_path("img/svg/buscar.svg"), tamanho=16), QLineEdit.LeadingPosition)
        except Exception:
            pass

        gl.addWidget(lbl_type, 0,0); gl.addWidget(self.cb_type, 0,1)
        gl.addWidget(lbl_ini,  0,2); gl.addWidget(self.dt_ini,  0,3)
        gl.addWidget(lbl_fim,  0,4); gl.addWidget(self.dt_fim,  0,5)
        gl.addWidget(self.btn_load, 0,6); gl.addWidget(self.btn_clear, 0,7)
        gl.addWidget(lbl_busca, 1,0); gl.addWidget(self.ed_busca, 1,1,1,7)

        root_layout.addWidget(box)

        self.btn_load.clicked.connect(self.on_load)
        self.btn_clear.clicked.connect(self.on_clear)
        self.ed_busca.textChanged.connect(self._on_search_changed)

    # -- Métricas --
    def _build_metrics(self, root_layout: QVBoxLayout):
        row = QHBoxLayout(); row.setSpacing(12)
        self.chip_total     = StatChip("Registros", "#3a556f")
        self.chip_info1     = StatChip("Métrica 1", "#3a556f")
        self.chip_info2     = StatChip("Métrica 2", "#3a556f")
        self.chip_info3     = StatChip("Métrica 3", "#3a556f")
        row.addWidget(self.chip_total)
        row.addWidget(self.chip_info1)
        row.addWidget(self.chip_info2)
        row.addWidget(self.chip_info3)
        root_layout.addLayout(row)

    # -- Tabela --
    def _build_table(self, root_layout: QVBoxLayout):
        self.model = QStandardItemModel(self)
        self.proxy = FancyProxy()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView(self)
        self.table.setModel(self.proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setMinimumHeight(400)
        root_layout.addWidget(self.table, 1)

    # -- Rodapé (Exportar / Imprimir) --
    def _build_footer(self, root_layout: QVBoxLayout):
        row = QHBoxLayout()
        row.addStretch(1)

        self.btn_exportar = QToolButton()
        self.btn_exportar.setText("Exportar")
        self.btn_exportar.setPopupMode(QToolButton.InstantPopup)
        self.btn_exportar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_exportar.setMinimumHeight(36)
        self.btn_exportar.setIcon(carregar_svg_branco(resource_path("img/svg/exportar.svg"), tamanho=18))

        menu = QMenu(self)
        act_xlsx = QAction("Excel (.xlsx)", self)
        act_csv  = QAction("CSV (.csv)", self)
        act_pdf  = QAction("PDF (.pdf)", self)
        act_imp  = QAction("Imprimir…", self)
        act_xlsx.setIcon(carregar_svg_branco(resource_path("img/svg/excel.svg"), tamanho=18))
        act_csv.setIcon(carregar_svg_branco(resource_path("img/svg/csv.svg"), tamanho=18))
        act_pdf.setIcon(carregar_svg_branco(resource_path("img/svg/pdf.svg"), tamanho=18))
        act_imp.setIcon(carregar_svg_branco(resource_path("img/svg/imprimir.svg"), tamanho=18))

        menu.addAction(act_xlsx); menu.addAction(act_csv)
        menu.addSeparator()
        menu.addAction(act_pdf)
        menu.addSeparator()
        menu.addAction(act_imp)
        self.btn_exportar.setMenu(menu)

        row.addWidget(self.btn_exportar)
        root_layout.addLayout(row)

        act_xlsx.triggered.connect(lambda: self._export_excel_or_csv(xlsx=True))
        act_csv.triggered.connect(lambda: self._export_excel_or_csv(xlsx=False))
        act_pdf.triggered.connect(self.on_export_pdf)
        act_imp.triggered.connect(self.on_print)

    # -- Atalhos --
    def _setup_shortcuts(self):
        self._shortcut_actions = []

        def add_action(text: str, seq: str, slot):
            act = QAction(text, self)
            act.setShortcut(QKeySequence(seq))
            act.triggered.connect(slot)
            self.addAction(act)
            self._shortcut_actions.append(act)
            return act

        add_action("Recarregar", "Ctrl+R", self.on_load)
        add_action("Excel",      "Ctrl+E", lambda: self._export_excel_or_csv(xlsx=True))
        add_action("Imprimir",   "Ctrl+P", self.on_print)
        add_action("Buscar",     "Ctrl+F", lambda: self.ed_busca.setFocus())
        add_action("Voltar",     "Alt+Left", self.on_voltar)
        add_action("Sair",       "Esc", self.on_sair)
        add_action("Configurações", "Ctrl+,", self.on_settings)  # atalho solicitado

    # ========= Navegação =========
    def on_voltar(self):
        try:
            self.close()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao voltar", str(e))

    def on_sair(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    # ========= Filtro de busca =========
    def _on_search_changed(self, text: str):
        self.proxy.set_query(text)

    # ========= Carregamento =========
    def _current_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        d0 = self.dt_ini.date(); d1 = self.dt_fim.date()
        start = f"{d0.toString('yyyy-MM-dd')} 00:00:00" if d0.isValid() else None
        end   = f"{d1.toString('yyyy-MM-dd')} 23:59:59" if d1.isValid() else None
        return start, end

    def on_clear(self):
        self.dt_ini.setDate(QDate.currentDate().addMonths(-1))
        self.dt_fim.setDate(QDate.currentDate())
        self.ed_busca.clear()
        self.model.clear()  # <-- corrigido: sem indentação extra
        self._update_chips([], [])
        self.status.showMessage("Filtros limpos.", 3000)

    def on_load(self):
        try:
            tipo = self.cb_type.currentText()
            start, end = self._current_date_range()
            headers, rows = self.manager.fetch(tipo, start, end)
            self._fill_table(headers, rows)
            self._update_chips(headers, rows)
            self.status.showMessage(f"{len(rows)} registro(s) carregado(s).", 5000)
        except Exception as e:
            details = traceback.format_exc()
            QMessageBox.critical(self, "Erro ao carregar", f"{e}\n\n{details}")
            self.status.showMessage("Falha ao carregar dados.", 5000)

    def _fill_table(self, headers: List[str], rows: List[List[Any]]):
        self.model.clear()
        if headers:
            self.model.setHorizontalHeaderLabels(headers)
        for row in rows:
            items = []
            for val in row:
                text = human_dt(val)
                it = QStandardItem(text); it.setEditable(False)
                items.append(it)
            self.model.appendRow(items)
        self.table.resizeColumnsToContents(); self.table.resizeRowsToContents()

    # ========= Métricas =========
    def _update_chips(self, headers: List[str], rows: List[List[Any]]):
        self.chip_total.set_value(str(len(rows)))
        self.chip_info1.set_value("--")
        self.chip_info2.set_value("--")
        self.chip_info3.set_value("--")

        tipo = self.cb_type.currentText()
        idx = {h: i for i, h in enumerate(headers)} if headers else {}

        if tipo == "Producao" and headers:
            c1 = sum(parse_float(rows[r][idx["conforme"]]) or 0 for r in range(len(rows)) if "conforme" in idx)
            c2 = sum(parse_float(rows[r][idx["naoConforme"]]) or 0 for r in range(len(rows)) if "naoConforme" in idx)
            c3 = sum(parse_float(rows[r][idx["total"]]) or 0 for r in range(len(rows)) if "total" in idx)
            self.chip_info1.lbl_titulo.setText("Conforme")
            self.chip_info2.lbl_titulo.setText("Não Conforme")
            self.chip_info3.lbl_titulo.setText("Total")
            self.chip_info1.set_value(str(int(c1)))
            self.chip_info2.set_value(str(int(c2)))
            self.chip_info3.set_value(str(int(c3)))
            return

        if tipo == "Sensores" and headers:
            def avg(col: str) -> Optional[float]:
                if col not in idx: return None
                vals = [parse_float(rows[r][idx[col]]) for r in range(len(rows))]
                vals = [v for v in vals if v is not None]
                return (sum(vals)/len(vals)) if vals else None
            t = avg("temperatura")
            u = avg("umidade")
            p = avg("pressao")
            self.chip_info1.lbl_titulo.setText("Temp média (°C)")
            self.chip_info2.lbl_titulo.setText("Umid média (%)")
            self.chip_info3.lbl_titulo.setText("Pressão média (hPa)")
            self.chip_info1.set_value(f"{t:.1f}" if t is not None else "--")
            self.chip_info2.set_value(f"{u:.1f}" if u is not None else "--")
            self.chip_info3.set_value(f"{p:.1f}" if p is not None else "--")
            return

        if tipo == "Cameras" and headers:
            fps = None
            br  = None
            if "fps" in idx:
                vals = [parse_float(rows[r][idx["fps"]]) for r in range(len(rows))]
                vals = [v for v in vals if v is not None]
                fps = (sum(vals)/len(vals)) if vals else None
            if "bitrate" in idx:
                vals = [parse_float(rows[r][idx["bitrate"]]) for r in range(len(rows))]
                vals = [v for v in vals if v is not None]
                br = (sum(vals)/len(vals)) if vals else None
            self.chip_info1.lbl_titulo.setText("FPS médio")
            self.chip_info2.lbl_titulo.setText("Bitrate médio")
            self.chip_info3.lbl_titulo.setText("Câmeras (dist.)")
            cams: Set[str] = set()
            if "camera_id" in idx:
                for r in rows:
                    cams.add(str(rows[r][idx["camera_id"]]) if isinstance(rows[r], list) else str(r[idx["camera_id"]]))
            self.chip_info1.set_value(f"{fps:.1f}" if fps is not None else "--")
            self.chip_info2.set_value(f"{br:.1f}" if br is not None else "--")
            self.chip_info3.set_value(str(len(cams)) if cams else "--")

    # ========= Exportar / Imprimir =========
    def _collect_table(self) -> Tuple[List[str], List[List[str]]]:
        headers = [self.model.headerData(c, Qt.Horizontal, Qt.DisplayRole) or "" for c in range(self.model.columnCount())]
        data: List[List[str]] = []
        for r in range(self.proxy.rowCount()):
            row = []
            for c in range(self.proxy.columnCount()):
                idx = self.proxy.index(r, c)
                src_idx = self.proxy.mapToSource(idx)
                val = self.model.data(src_idx, Qt.DisplayRole)
                row.append("" if val is None else str(val))
            data.append(row)
        return headers, data

    def _export_excel_or_csv(self, xlsx: bool):
        if self.model.columnCount() == 0:
            QMessageBox.warning(self, "Exportar", "Nenhum dado para exportar.")
            return

        if xlsx:
            path, _ = QFileDialog.getSaveFileName(self, "Salvar Excel", "relatorio.xlsx", "Excel (*.xlsx)")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", "relatorio.csv", "CSV (*.csv)")

        if not path:
            return

        headers, data = self._collect_table()
        try:
            if xlsx:
                try:
                    import pandas as pd  # type: ignore
                    df = pd.DataFrame(data, columns=headers)
                    df.to_excel(path, index=False)
                except Exception:
                    alt = os.path.splitext(path)[0] + ".csv"
                    with open(alt, "w", newline="", encoding="utf-8") as f:
                        import csv as _csv
                        writer = _csv.writer(f, delimiter=";")
                        writer.writerow(headers); writer.writerows(data)
                    path = alt
            else:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    import csv as _csv
                    writer = _csv.writer(f, delimiter=";")
                    writer.writerow(headers); writer.writerows(data)
            QMessageBox.information(self, "Exportar", f"Arquivo salvo em:\n{path}")
        except Exception as e:
            details = traceback.format_exc()
            QMessageBox.critical(self, "Erro ao exportar", f"{e}\n\n{details}")

    def _model_to_html(self, title: str) -> str:
        headers, data = self._collect_table()
        html = []
        html.append("<html><head><meta charset='utf-8'><style>")
        html.append("""
            body { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; }
            h1 { font-size: 16pt; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #aaa; padding: 6px; text-align: left; }
            th { background: #efefef; }
            tfoot td { font-weight: bold; }
        """)
        html.append("</style></head><body>")
        html.append(f"<h1>{title}</h1><table><thead><tr>")
        for h in headers: html.append(f"<th>{h}</th>")
        html.append("</tr></thead><tbody>")
        for row in data:
            html.append("<tr>")
            for val in row:
                html.append(f"<td>{val}</td>")
            html.append("</tr>")
        html.append("</tbody>")
        html.append(f"<tfoot><tr><td colspan='{len(headers)}'>Total de registros: {len(data)}</td></tr></tfoot>")
        html.append("</table></body></html>")
        return "".join(html)

    def on_export_pdf(self):
        if self.model.columnCount() == 0:
            QMessageBox.warning(self, "Exportar PDF", "Nenhum dado para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "relatorio.pdf", "PDF (*.pdf)")
        if not path: return
        try:
            html = self._model_to_html(f"Relatório – {self.cb_type.currentText()}")
            doc = QTextDocument(); doc.setHtml(html)
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            doc.print_(printer)
            QMessageBox.information(self, "Exportar", f"PDF gerado em:\n{path}")
        except Exception as e:
            details = traceback.format_exc()
            QMessageBox.critical(self, "Erro ao exportar PDF", f"{e}\n\n{details}")

    def on_print(self):
        if self.model.columnCount() == 0:
            QMessageBox.warning(self, "Imprimir", "Nenhum dado para imprimir.")
            return
        try:
            html = self._model_to_html(f"Relatório – {self.cb_type.currentText()}")
            doc = QTextDocument(); doc.setHtml(html)
            printer = QPrinter(QPrinter.HighResolution)
            dlg = QPrintDialog(printer, self)
            if dlg.exec() == QDialog.Accepted:
                doc.print_(printer)
        except Exception as e:
            details = traceback.format_exc()
            QMessageBox.critical(self, "Erro ao imprimir", f"{e}\n\n{details}")

    # ========= Config =========
    def on_settings(self):
        dlg = SettingsDialog(self, self.manager.get_sqlite_path())
        if dlg.exec() == QDialog.Accepted:
            vals = dlg.get_values()
            self.manager.set_sqlite_path(vals.get("sqlite_path"))
            self.status.showMessage(f"BDL: {self.manager.get_sqlite_path() or 'não definido'}", 5000)

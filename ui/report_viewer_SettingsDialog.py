#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QWidget, QHBoxLayout, QFileDialog

class SettingsDialog(QDialog):
    def __init__(self, parent, sqlite_path: Optional[str]):
        super().__init__(parent)
        self.setWindowTitle("Configurações do Relatório")
        self.resize(640, 180)
        form = QFormLayout(self)
        self.ed_sqlite = QLineEdit(self); self.ed_sqlite.setText(sqlite_path or "")
        self.ed_sqlite.setStyleSheet("background:#162635; color:#eee; border:1px solid #3f5a73; border-radius:6px; padding:6px;")
        bpick = QPushButton("Escolher arquivo…")
        row = QHBoxLayout(); row.addWidget(self.ed_sqlite, 1); row.addWidget(bpick, 0)
        w = QWidget(self); w.setLayout(row)
        form.addRow("SQLite (BDL):", w)
        h = QHBoxLayout(); bcancel = QPushButton("Cancelar"); bok = QPushButton("OK")
        for b in (bcancel, bok): b.setStyleSheet("padding:8px 16px;")
        h.addStretch(1); h.addWidget(bcancel); h.addWidget(bok); form.addRow(h)
        bpick.clicked.connect(self.on_pick); bcancel.clicked.connect(self.reject); bok.clicked.connect(self.accept)

    def on_pick(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecione o BDL (SQLite)", "", "SQLite (*.db *.sqlite *.sqlite3);;Todos (*.*)")
        if path: self.ed_sqlite.setText(path)

    def get_values(self) -> Dict[str, Any]:
        return {"sqlite_path": self.ed_sqlite.text().strip() or None}

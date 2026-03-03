#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton

class SqlEditorDialog(QDialog):
    def __init__(self, parent, current_type: str, sql_text: str):
        super().__init__(parent)
        self.setWindowTitle(f"Editar SQL – {current_type}")
        self.resize(900, 540)
        v = QVBoxLayout(self)
        self.t = QTextEdit(self); self.t.setPlainText(sql_text)
        self.t.setStyleSheet("background:#162635; color:#eee; border:1px solid #3f5a73; border-radius:8px;")
        v.addWidget(self.t)
        h = QHBoxLayout()
        bcancel = QPushButton("Cancelar"); bok = QPushButton("Salvar")
        for b in (bcancel, bok):
            b.setStyleSheet("padding:8px 16px;")
        h.addStretch(1); h.addWidget(bcancel); h.addWidget(bok); v.addLayout(h)
        bcancel.clicked.connect(self.reject); bok.clicked.connect(self.accept)

    def get_sql(self) -> str:
        return self.t.toPlainText().strip()

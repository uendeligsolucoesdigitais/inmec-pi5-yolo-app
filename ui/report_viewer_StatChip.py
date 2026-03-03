#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class StatChip(QFrame):
    """Card de métrica simples."""
    def __init__(self, titulo: str, cor_bg: str = "#3a556f"):
        super().__init__()
        self.setObjectName("StatChip")
        self.setStyleSheet(f"""
            QFrame#StatChip {{
                background-color: {cor_bg};
                border: 1px solid #5f7a92;
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        self.lbl_titulo = QLabel(titulo); self.lbl_titulo.setStyleSheet("color:#c9d5df; font-size:12px;")
        self.lbl_valor  = QLabel("--");   self.lbl_valor.setStyleSheet("color:white; font-size:20px; font-weight:700;")
        lay.addWidget(self.lbl_titulo); lay.addWidget(self.lbl_valor)

    def set_value(self, v: str):
        self.lbl_valor.setText(v)

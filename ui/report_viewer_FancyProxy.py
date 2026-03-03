#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from PySide6.QtCore import QSortFilterProxyModel, QRegularExpression, Qt

class FancyProxy(QSortFilterProxyModel):
    """Proxy de filtro (todas as colunas, case-insensitive)."""
    def __init__(self):
        super().__init__()
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(-1)

    def set_query(self, text: str):
        rx = QRegularExpression(text if text else "")
        rx.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
        self.setFilterRegularExpression(rx)

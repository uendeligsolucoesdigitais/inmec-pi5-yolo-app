#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

# Tenta pacote 'ui' primeiro, depois fallback local
try:
    from ui.report_viewer_shared import DEFAULT_SQL_TEMPLATES
except Exception:
    from report_viewer_shared import DEFAULT_SQL_TEMPLATES

class ReportManager:
    def __init__(self, sqlite_path: Optional[str] = None, sql_templates: Optional[Dict[str, str]] = None):
        self.sqlite_path = sqlite_path
        self.sql_templates = dict(DEFAULT_SQL_TEMPLATES)
        if sql_templates:
            self.sql_templates.update(sql_templates)

    def set_sqlite_path(self, path: Optional[str]):
        self.sqlite_path = path

    def get_sqlite_path(self) -> Optional[str]:
        return self.sqlite_path

    def _connect(self) -> sqlite3.Connection:
        if not self.sqlite_path:
            raise FileNotFoundError("Caminho do banco SQLite não definido.")
        if not os.path.isfile(self.sqlite_path):
            raise FileNotFoundError(f"Arquivo SQLite não encontrado: {self.sqlite_path}")
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_sql_template(self, t: str) -> str:
        if t not in self.sql_templates:
            raise KeyError(f"Tipo de relatório desconhecido: {t}")
        return self.sql_templates[t]

    def set_sql_template(self, t: str, sql: str):
        self.sql_templates[t] = sql

    def fetch(self, report_type: str, start: Optional[str], end: Optional[str]) -> Tuple[List[str], List[List[Any]]]:
        sql = self.get_sql_template(report_type)
        params = {"start": start, "end": end}
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            headers = [d[0] for d in cur.description] if cur.description else []
            data = [list(r) for r in rows]
            return headers, data

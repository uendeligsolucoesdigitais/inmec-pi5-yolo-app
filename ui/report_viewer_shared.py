#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple, Union

# Reexport do util do projeto (com fallback mínimo)
try:
    from ui.utils import carregar_svg_branco  # type: ignore
except Exception:
    from PySide6.QtGui import QIcon
    def carregar_svg_branco(path: str, tamanho: int = 18) -> QIcon:  # fallback
        return QIcon(path)

# ===== Resolver de caminhos =====
_APP_ROOT_CACHE: Optional[str] = None

def get_app_root() -> str:
    global _APP_ROOT_CACHE
    if _APP_ROOT_CACHE:
        return _APP_ROOT_CACHE

    env_root = os.environ.get("INMEC_APP_ROOT", "").strip()
    if env_root and os.path.isdir(env_root):
        _APP_ROOT_CACHE = env_root
        return _APP_ROOT_CACHE

    try:
        here = os.path.abspath(os.path.dirname(__file__))
    except NameError:
        here = os.getcwd()

    parent = os.path.abspath(os.path.join(here, os.pardir))
    grandp = os.path.abspath(os.path.join(parent, os.pardir))

    if os.path.isdir(os.path.join(parent, "ui")):
        _APP_ROOT_CACHE = parent
        return _APP_ROOT_CACHE
    if os.path.isdir(os.path.join(grandp, "ui")):
        _APP_ROOT_CACHE = grandp
        return _APP_ROOT_CACHE

    _APP_ROOT_CACHE = os.getcwd()
    return _APP_ROOT_CACHE

def resource_path(rel_path: str) -> str:
    candidates: List[str] = []
    app_root = get_app_root()
    candidates.append(os.path.join(app_root, rel_path))
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        candidates.append(os.path.join(here, rel_path))
    except NameError:
        pass
    candidates.append(os.path.join(os.getcwd(), rel_path))

    for p in candidates:
        if os.path.isfile(p) or os.path.isdir(p):
            return p
    return os.path.join(app_root, rel_path)

# ===== Utilidades =====
def human_dt(val: Union[datetime, date, str, None]) -> str:
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return "" if val is None else str(val)

def parse_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None

def read_config_xml_for_sqlite(base_dir: str = "/config") -> Optional[str]:
    import xml.etree.ElementTree as ET
    cfg_path = os.path.join(base_dir, "config.xml")
    if not os.path.isfile(cfg_path):
        return None
    try:
        tree = ET.parse(cfg_path)
        root = tree.getroot()
        path_node = root.find(".//db_path_local")
        name_node = root.find(".//db_name_local")
        if path_node is None or name_node is None:
            return None
        db_dir = (path_node.text or "").strip()
        db_name = (name_node.text or "").strip()
        if not db_name:
            return None
        full1 = os.path.join(db_dir or "", db_name)
        if os.path.isfile(full1):
            return full1
        full2 = os.path.join(base_dir, db_dir, db_name) if db_dir else os.path.join(base_dir, db_name)
        return full2 if os.path.isfile(full2) else None
    except Exception:
        return None

# ===== SQLs padrão =====
DEFAULT_SQL_TEMPLATES: Dict[str, str] = {
    "Producao": """
        SELECT
            DATE(timestamp) AS data,
            SUM(CASE WHEN class IN ('pessoa','person') THEN 1 ELSE 0 END) AS conforme,
            SUM(CASE WHEN class IN ('garrafa','bottle') THEN 1 ELSE 0 END) AS naoConforme,
            COUNT(*) AS total
        FROM detections
        WHERE (:start IS NULL OR timestamp >= :start)
          AND (:end   IS NULL OR timestamp <= :end)
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp);
    """,
    "Sensores": """
        SELECT
            timestamp AS datahora,
            temperature AS temperatura,
            humidity    AS umidade,
            pressure    AS pressao,
            luminosity  AS luminosidade
        FROM sensor_readings
        WHERE (:start IS NULL OR timestamp >= :start)
          AND (:end   IS NULL OR timestamp <= :end)
        ORDER BY timestamp;
    """,
    "Cameras": """
        SELECT
            timestamp AS datahora,
            camera_id,
            width,
            height,
            fps,
            bitrate
        FROM camera_stats
        WHERE (:start IS NULL OR timestamp >= :start)
          AND (:end   IS NULL OR timestamp <= :end)
        ORDER BY timestamp;
    """
}

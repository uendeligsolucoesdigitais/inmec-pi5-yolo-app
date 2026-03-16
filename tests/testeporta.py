#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List, Set


# =========================
# Configuração do projeto
# =========================

APP_TITLE = "Raspberry Pi 5 — Monitor GPIO (I/O) com exclusão automática de pinos (HATs)"
DEFAULT_REFRESH_MS = 800

# Pinos fixos por tipo de HAT (serão aplicados somente se o HAT for detectado)
WM8960_BCM_PINS = {2, 3, 18, 19, 20, 21}  # I2C1 + I2S/PCM
SENSORHAT_BCM_PINS = {2, 3}              # I2C1 (base)

# Heurísticas I2C
WM8960_I2C_ADDRS = {"0x1a", "0x1b"}  # endereços comuns do codec (dependendo do board/strap)

# Endereços típicos (não-exaustivo) de sensores comuns em HATs de sensores
# Usado como pista para “Sensor HAT / Sense HAT” quando overlay não deixa claro.
SENSORHAT_I2C_HINT_ADDRS = {
    "0x5c",  # HTS221 (humidade/temperatura) - Sense HAT
    "0x6a",  # LSM9DS1/IMU (varia) - Sense HAT
    "0x1d",  # acelerômetros comuns (varia)
    "0x76", "0x77",  # BMP/BME280
    "0x23",  # BH1750
    "0x29",  # VL53L0X
    "0x68",  # MPU6050/RTC
    "0x40",  # sensores diversos (INA219, etc.)
}


# Mapa físico (40 pinos) -> BCM (None = não é GPIO utilizável)
PHYS_TO_BCM = {
    1: None,  2: None,
    3: 2,     4: None,
    5: 3,     6: None,
    7: 4,     8: 14,
    9: None,  10: 15,
    11: 17,   12: 18,
    13: 27,   14: None,
    15: 22,   16: 23,
    17: None, 18: 24,
    19: 10,   20: None,
    21: 9,    22: 25,
    23: 11,   24: 8,
    25: None, 26: 7,
    27: 0,    28: 1,
    29: 5,    30: None,
    31: 6,    32: 12,
    33: 13,   34: None,
    35: 19,   36: 16,
    37: 26,   38: 20,
    39: None, 40: 21,
}

# Rótulos para pinos não GPIO
PHYS_LABEL = {
    1: "3V3", 2: "5V",
    4: "5V",
    6: "GND", 9: "GND", 14: "GND", 17: "3V3", 20: "GND", 25: "GND",
    30: "GND", 34: "GND", 39: "GND",
}


# =========================
# Bootstrap de dependências
# =========================

def ensure_python_deps(packages: List[str]) -> None:
    """
    Garante que dependências Python estejam instaladas.
    Tenta instalar via pip caso estejam ausentes.
    """
    missing = []
    for pkg in packages:
        try:
            __import__(pkg)
        except Exception:
            missing.append(pkg)

    if not missing:
        return

    for pkg in missing:
        print(f"[BOOT] Dependência ausente: {pkg}. Tentando instalar via pip...", flush=True)
        rc = install_with_pip(pkg)
        if rc != 0:
            print(
                f"[BOOT] Falha ao instalar {pkg}. "
                f"Verifique conectividade, permissões e pip. Código: {rc}",
                flush=True
            )

    for pkg in missing:
        try:
            __import__(pkg)
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível importar {pkg} após tentativa de instalação. Erro: {e}"
            ) from e


def install_with_pip(package: str) -> int:
    cmd = [sys.executable, "-m", "pip", "install", package]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        print(p.stdout, flush=True)
        return p.returncode
    except Exception as e:
        print(f"[BOOT] Erro executando pip para {package}: {e}", flush=True)
        return 1


# garante PyQt6 antes de importar
ensure_python_deps(["PyQt6"])

from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: E402


# =========================
# Utilitários
# =========================

def which(exe: str) -> bool:
    return shutil.which(exe) is not None


def run_cmd(cmd: List[str], timeout: float = 2.0) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError:
        return 127, "", "not found"
    except Exception as e:
        return 1, "", f"error: {e}"


def detect_raspberry_pi() -> Tuple[bool, str]:
    """
    Detecta Raspberry Pi usando sinais do sistema.
    Retorna (is_pi, reason).
    """
    model_paths = ["/proc/device-tree/model", "/sys/firmware/devicetree/base/model"]
    for pth in model_paths:
        try:
            if os.path.exists(pth):
                with open(pth, "rb") as f:
                    raw = f.read().replace(b"\x00", b"").strip()
                model = raw.decode("utf-8", errors="ignore").strip()
                if model:
                    if "Raspberry Pi" in model:
                        return True, f"Modelo detectado: {model}"
                    return False, f"Modelo não corresponde a Raspberry Pi: {model}"
        except Exception:
            pass

    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            if re.search(r"Raspberry Pi", txt, re.IGNORECASE):
                return True, "Detectado via /proc/cpuinfo (string Raspberry Pi)"
    except Exception:
        pass

    if os.path.isdir("/boot/firmware") or os.path.isdir("/boot"):
        return False, "Não foi possível confirmar Raspberry Pi via model/cpuinfo (ambiente parecido com Pi OS)."

    return False, "Não foi possível confirmar Raspberry Pi (model/cpuinfo ausentes ou não correspondem)."


def read_config_txt_overlays() -> List[str]:
    """
    Lê dtoverlay=... do config.txt (Pi OS) e retorna lista de nomes (normalizados).
    """
    paths = ["/boot/firmware/config.txt", "/boot/config.txt"]
    overlays: List[str] = []
    for pth in paths:
        if not os.path.exists(pth):
            continue
        try:
            with open(pth, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    # dtoverlay=wm8960-soundcard,foo=bar
                    if s.lower().startswith("dtoverlay="):
                        val = s.split("=", 1)[1].strip()
                        name = val.split(",", 1)[0].strip().lower()
                        if name:
                            overlays.append(name)
        except Exception:
            continue
    return overlays


def i2c_list_buses() -> List[str]:
    """
    Retorna números de buses i2c disponíveis (/dev/i2c-*)
    """
    buses = []
    try:
        for dev in sorted(glob_glob("/dev/i2c-*")):
            bn = dev.split("-")[-1]
            if bn.isdigit():
                buses.append(bn)
    except Exception:
        pass
    return buses


def glob_glob(pattern: str) -> List[str]:
    # evita importar glob no topo se não precisar
    import glob
    return glob.glob(pattern)


def i2c_scan_bus(busnum: str, timeout: float = 3.0) -> Set[str]:
    """
    Executa i2cdetect e retorna conjunto de endereços respondendo no formato '0x..'
    """
    if not which("i2cdetect"):
        return set()

    rc, out, err = run_cmd(["i2cdetect", "-y", "-r", str(busnum)], timeout=timeout)
    if rc != 0 or not out:
        return set()

    found = set()
    for token in re.findall(r"\b[0-9a-f]{2}\b", out.lower()):
        found.add("0x" + token)
    return found


def detect_hats_and_ignored_pins() -> Tuple[Set[int], List[str], Dict[str, str]]:
    """
    Retorna:
      - ignored_pins (BCM)
      - hats_detected (lista textual)
      - reasons_by_pin (pin -> razão)
    """
    ignored: Set[int] = set()
    hats: List[str] = []
    reasons: Dict[str, str] = {}

    overlays = read_config_txt_overlays()
    overlay_join = " ".join(overlays)

    wm_by_overlay = any("wm8960" in ov for ov in overlays) or ("wm8960" in overlay_join)
    sensor_by_overlay = any(("sense" in ov and "hat" in ov) or ("sensor" in ov and "hat" in ov) for ov in overlays)

    # Detecção por I2C
    wm_by_i2c = False
    sensor_by_i2c = False
    i2c_details = ""
    if which("i2cdetect"):
        buses = i2c_list_buses()
        all_addrs = set()
        per_bus = {}
        for b in buses:
            addrs = i2c_scan_bus(b)
            if addrs:
                per_bus[b] = addrs
                all_addrs |= addrs

        if all_addrs:
            wm_by_i2c = len(all_addrs & WM8960_I2C_ADDRS) > 0
            # heurística: se tiver “muitos” endereços típicos de sensor, assume sensor hat
            sensor_hits = len(all_addrs & SENSORHAT_I2C_HINT_ADDRS)
            sensor_by_i2c = sensor_hits >= 1

            # resumo curto
            try:
                parts = []
                for b in sorted(per_bus.keys(), key=lambda x: int(x)):
                    sample = sorted(list(per_bus[b]))[:12]
                    parts.append(f"bus {b}: {', '.join(sample)}")
                i2c_details = " | ".join(parts)
            except Exception:
                i2c_details = ""

    wm_detected = wm_by_overlay or wm_by_i2c
    sensor_detected = sensor_by_overlay or sensor_by_i2c

    if wm_detected:
        hats.append("WM8960 (áudio) detectado " + ("(overlay)" if wm_by_overlay else "(I2C)"))
        ignored |= WM8960_BCM_PINS
        for p in WM8960_BCM_PINS:
            reasons[str(p)] = "IGNORADO (WM8960: I2C1 + I2S/PCM)"

    if sensor_detected:
        hats.append("Sensor HAT detectado " + ("(overlay)" if sensor_by_overlay else "(I2C heurístico)"))
        ignored |= SENSORHAT_BCM_PINS
        for p in SENSORHAT_BCM_PINS:
            # se já tinha razão do WM8960, concatena
            if str(p) in reasons and "WM8960" in reasons[str(p)]:
                reasons[str(p)] = reasons[str(p)] + " + Sensor HAT (I2C1)"
            else:
                reasons[str(p)] = "IGNORADO (Sensor HAT: I2C1)"

    # Se não detectou nada, lista explicitamente para diagnóstico
    if not hats:
        hats.append("Nenhum HAT detectado automaticamente (sem exclusões aplicadas).")

    # adiciona detalhe I2C se existir (como “hats” extra, para aparecer no diagnóstico)
    if i2c_details:
        hats.append("I2C detectado: " + i2c_details)

    # se overlays existirem, mostre também (ajuda debug)
    if overlays:
        hats.append("Overlays lidos: " + ", ".join(overlays))

    return ignored, hats, reasons


# =========================
# Modelo de dados
# =========================

@dataclass
class PinStatus:
    phys: int
    bcm: Optional[int]
    label: str
    ignored: bool = False
    ignore_reason: str = ""
    mode: str = "-"
    pull: str = "-"
    level: str = "-"
    used: str = "-"
    consumer: str = "-"


# =========================
# Scanner GPIO
# =========================

class GpioScanner:
    """
    Combina pinctrl/raspi-gpio + gpioinfo para preencher status.
    A lista de pinos ignorados vem de detecção dinâmica.
    """

    def __init__(self, ignored_bcm_pins: Set[int], reasons_by_pin: Dict[str, str]):
        self.ignored_bcm_pins = set(ignored_bcm_pins)
        self.reasons_by_pin = dict(reasons_by_pin)

        self.has_pinctrl = which("pinctrl")
        self.has_raspi_gpio = which("raspi-gpio")
        self.has_gpioinfo = which("gpioinfo")

    def scan(self) -> Dict[int, PinStatus]:
        pins: Dict[int, PinStatus] = {}
        for phys in range(1, 41):
            bcm = PHYS_TO_BCM.get(phys)
            label = PHYS_LABEL.get(phys, f"GPIO{bcm}" if bcm is not None else "-")

            ignored = False
            ignore_reason = ""
            if bcm is not None and bcm in self.ignored_bcm_pins:
                ignored = True
                ignore_reason = self.reasons_by_pin.get(str(bcm), "IGNORADO (HAT)")

            pins[phys] = PinStatus(
                phys=phys,
                bcm=bcm,
                label=label,
                ignored=ignored,
                ignore_reason=ignore_reason
            )

        pinctrl_data = self._scan_pinctrl()
        for phys, st in pins.items():
            if st.bcm is None or st.ignored:
                continue
            if st.bcm in pinctrl_data:
                st.mode, st.pull, st.level = pinctrl_data[st.bcm]

        gpioinfo_data = self._scan_gpioinfo()
        for phys, st in pins.items():
            if st.bcm is None or st.ignored:
                continue
            if st.bcm in gpioinfo_data:
                st.used, st.consumer = gpioinfo_data[st.bcm]

        for phys, st in pins.items():
            if st.bcm is None:
                continue
            if st.ignored:
                st.mode = "IGNORADO"
                st.pull = "IGNORADO"
                st.level = "IGNORADO"
                st.used = "IGNORADO"
                st.consumer = st.ignore_reason

        return pins

    def _scan_pinctrl(self) -> Dict[int, Tuple[str, str, str]]:
        data: Dict[int, Tuple[str, str, str]] = {}

        bcm_list = sorted(set(
            v for v in PHYS_TO_BCM.values()
            if v is not None and v not in self.ignored_bcm_pins
        ))

        if self.has_pinctrl:
            for bcm in bcm_list:
                rc, out, err = run_cmd(["pinctrl", "get", str(bcm)], timeout=1.2)
                if rc != 0 or not out:
                    continue

                level = self._find_kv(out, "level") or "-"
                pull = self._find_kv(out, "pull") or "-"
                func = self._find_kv(out, "func") or "-"
                alt = self._find_kv(out, "alt")

                mode = func
                if "INPUT" in mode.upper():
                    mode = "IN"
                elif "OUTPUT" in mode.upper():
                    mode = "OUT"
                else:
                    if alt is not None:
                        mode = f"ALT{alt} ({func})" if func != "-" else f"ALT{alt}"

                data[bcm] = (mode, pull.upper(), str(level))
            return data

        if self.has_raspi_gpio:
            for bcm in bcm_list:
                rc, out, err = run_cmd(["raspi-gpio", "get", str(bcm)], timeout=1.2)
                if rc != 0 or not out:
                    continue

                level = self._find_kv(out, "level") or "-"
                pull = self._find_kv(out, "pull") or "-"
                func = self._find_kv(out, "func") or "-"
                alt = self._find_kv(out, "alt")

                mode = func
                if "INPUT" in mode.upper():
                    mode = "IN"
                elif "OUTPUT" in mode.upper():
                    mode = "OUT"
                else:
                    if alt is not None:
                        mode = f"ALT{alt} ({func})" if func != "-" else f"ALT{alt}"

                data[bcm] = (mode, pull.upper(), str(level))
            return data

        return data

    def _scan_gpioinfo(self) -> Dict[int, Tuple[str, str]]:
        data: Dict[int, Tuple[str, str]] = {}
        if not self.has_gpioinfo:
            return data

        rc, out, err = run_cmd(["gpioinfo"], timeout=2.8)
        if rc != 0 or not out:
            return data

        line_re = re.compile(
            r"^line\s+\d+:\s+\"([^\"]+)\"\s+\"([^\"]*)\".*?(?:\[(used|unused)\])?",
            re.IGNORECASE
        )

        for raw in out.splitlines():
            raw = raw.strip()
            m = line_re.match(raw)
            if not m:
                continue

            name = (m.group(1) or "").strip()
            consumer = (m.group(2) or "").strip() or "-"
            used_tag = (m.group(3) or "").lower()

            m_gpio = re.match(r"GPIO(\d+)", name, re.IGNORECASE)
            if not m_gpio:
                continue
            bcm = int(m_gpio.group(1))

            if bcm in self.ignored_bcm_pins:
                continue

            used = "SIM" if used_tag == "used" else "NÃO"
            if used_tag == "" and consumer not in ["-", ""]:
                used = "SIM"

            data[bcm] = (used, consumer)

        return data

    @staticmethod
    def _find_kv(text: str, key: str) -> Optional[str]:
        m = re.search(rf"\b{re.escape(key)}\s*=\s*([^\s]+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
        return None


# =========================
# Worker em thread
# =========================

class ScannerWorker(QtCore.QObject):
    data_ready = QtCore.pyqtSignal(dict)
    status = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, refresh_ms: int, ignored_bcm_pins: Set[int], reasons_by_pin: Dict[str, str]):
        super().__init__()
        self._refresh_ms = max(250, int(refresh_ms))
        self._running = False
        self._scanner = GpioScanner(ignored_bcm_pins, reasons_by_pin)

    @QtCore.pyqtSlot(int)
    def set_refresh(self, refresh_ms: int):
        self._refresh_ms = max(250, int(refresh_ms))

    @QtCore.pyqtSlot()
    def start(self):
        self._running = True
        self.status.emit("Monitoramento iniciado.")
        while self._running:
            pins = self._scanner.scan()
            self.data_ready.emit({"ts": time.time(), "pins": pins})
            time.sleep(self._refresh_ms / 1000.0)
        self.status.emit("Monitoramento finalizado.")
        self.finished.emit()

    @QtCore.pyqtSlot()
    def stop(self):
        self._running = False


# =========================
# UI
# =========================

class Banner(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("banner")
        self.setVisible(False)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        self._label = QtWidgets.QLabel("")
        self._label.setObjectName("bannerLabel")
        lay.addWidget(self._label, 1)

    def show_message(self, text: str):
        self._label.setText(text)
        self.setVisible(True)

    def hide_banner(self):
        self.setVisible(False)
        self._label.setText("")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1220, 780)

        self._is_pi, self._pi_reason = detect_raspberry_pi()
        self._ignored_bcm_pins, self._hat_diagnostics, self._reasons_by_pin = detect_hats_and_ignored_pins()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        self.banner = Banner()
        root.addWidget(self.banner)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(APP_TITLE)
        title.setObjectName("headerTitle")
        header.addWidget(title, 1)

        header.addWidget(QtWidgets.QLabel("Atualização:"))
        self.spin_refresh = QtWidgets.QSpinBox()
        self.spin_refresh.setRange(250, 5000)
        self.spin_refresh.setSingleStep(50)
        self.spin_refresh.setValue(DEFAULT_REFRESH_MS)
        self.spin_refresh.setSuffix(" ms")
        self.spin_refresh.setObjectName("refreshSpin")
        header.addWidget(self.spin_refresh)

        self.btn_start = QtWidgets.QPushButton("Iniciar")
        self.btn_stop = QtWidgets.QPushButton("Parar")
        self.btn_stop.setEnabled(False)
        header.addSpacing(8)
        header.addWidget(self.btn_start)
        header.addWidget(self.btn_stop)

        root.addLayout(header)

        info = QtWidgets.QLabel(
            "Monitor de I/O do header GPIO (40 pinos). "
            "Pinos reservados por HATs são ignorados automaticamente com base em overlays e/ou varredura I2C. "
            "Modo/Pull/Nível via pinctrl (ou raspi-gpio). Used/Consumer via gpioinfo (libgpiod)."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        root.addWidget(split, 1)

        # tabela principal
        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Pino (Físico)", "BCM", "Rótulo", "Modo", "Pull", "Nível", "Em uso / Consumer"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        split.addWidget(self.table)

        # painel diagnóstico
        diag_wrap = QtWidgets.QWidget()
        diag_lay = QtWidgets.QVBoxLayout(diag_wrap)
        diag_lay.setContentsMargins(0, 0, 0, 0)
        diag_lay.setSpacing(8)

        diag_title = QtWidgets.QLabel("Diagnóstico (detecção automática de HATs e pinos ignorados)")
        diag_title.setObjectName("diagTitle")
        diag_lay.addWidget(diag_title)

        self.diag_text = QtWidgets.QTextEdit()
        self.diag_text.setReadOnly(True)
        diag_lay.addWidget(self.diag_text, 1)

        split.addWidget(diag_wrap)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 2)

        self.err = QtWidgets.QLabel("")
        self.err.setStyleSheet("color: #fca5a5;")
        root.addWidget(self.err)

        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Pronto.")

        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[ScannerWorker] = None

        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.spin_refresh.valueChanged.connect(self.on_refresh_changed)

        self._apply_styles()
        self._populate_initial_rows()
        self._render_diagnostics()
        self._apply_device_state()

    def _render_diagnostics(self):
        ignored_sorted = sorted(list(self._ignored_bcm_pins))
        ignored_line = ", ".join(str(x) for x in ignored_sorted) if ignored_sorted else "(nenhum)"
        txt = []
        txt.extend(self._hat_diagnostics)
        txt.append("")
        txt.append("Pinos BCM ignorados: " + ignored_line)
        if self._reasons_by_pin:
            txt.append("")
            txt.append("Motivo por pino (BCM):")
            for k in sorted(self._reasons_by_pin.keys(), key=lambda x: int(x)):
                txt.append(f"  BCM {k}: {self._reasons_by_pin[k]}")
        self.diag_text.setPlainText("\n".join(txt))

    def _apply_device_state(self):
        if not self._is_pi:
            self.banner.show_message(
                "AVISO: Este dispositivo não foi identificado como um Raspberry Pi válido. "
                "A interface será carregada, mas o monitoramento ficará desabilitado. "
                f"Detalhe: {self._pi_reason}"
            )
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.spin_refresh.setEnabled(False)
        else:
            self.banner.hide_banner()
            self.btn_start.setEnabled(True)
            self.spin_refresh.setEnabled(True)
            self.statusbar.showMessage(self._pi_reason)

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget { font-family: "Segoe UI", "Inter", "Ubuntu", sans-serif; font-size: 12px; }
            QMainWindow { background: #0f172a; }
            QLabel#headerTitle { font-size: 18px; font-weight: 700; color: #e2e8f0; }
            QLabel { color: #cbd5e1; }

            QLabel#diagTitle { font-weight: 700; color: #e2e8f0; }

            QFrame#banner {
                background: #7f1d1d;
                border: 1px solid #fecaca;
                border-radius: 12px;
            }
            QLabel#bannerLabel {
                color: #fee2e2;
                font-weight: 700;
            }

            QPushButton {
                background: #1f2a44; border: 1px solid #2b3a57; color: #e2e8f0;
                padding: 8px 12px; border-radius: 10px;
            }
            QPushButton:hover { background: #243151; }
            QPushButton:disabled { color: #64748b; background: #141c2f; border-color: #1f2a44; }

            QSpinBox#refreshSpin {
                background: #0b1220; border: 1px solid #243042; color: #e2e8f0;
                padding: 6px 8px; border-radius: 10px;
            }

            QTableWidget, QTextEdit {
                background: #0b1220;
                border: 1px solid #243042;
                border-radius: 12px;
                gridline-color: #243042;
                color: #e2e8f0;
            }
            QHeaderView::section {
                background: #121c2f;
                color: #cbd5e1;
                border: 0px;
                padding: 8px;
                font-weight: 700;
            }
            QStatusBar { background: #0b1220; color: #cbd5e1; border-top: 1px solid #243042; }
            """
        )

    def _populate_initial_rows(self):
        self.table.setRowCount(40)
        for r in range(40):
            phys = r + 1
            bcm = PHYS_TO_BCM.get(phys)
            label = PHYS_LABEL.get(phys, f"GPIO{bcm}" if bcm is not None else "-")

            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(phys)))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem("-" if bcm is None else str(bcm)))
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(label))
            for c in range(3, 7):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem("-"))

            if bcm is None:
                for c in range(0, 7):
                    it = self.table.item(r, c)
                    it.setForeground(QtGui.QBrush(QtGui.QColor("#94a3b8")))

            if bcm is not None and bcm in self._ignored_bcm_pins:
                for c in range(0, 7):
                    it = self.table.item(r, c)
                    it.setForeground(QtGui.QBrush(QtGui.QColor("#9ca3af")))

        self.table.resizeColumnsToContents()

    def on_refresh_changed(self, value: int):
        if self._worker is not None:
            QtCore.QMetaObject.invokeMethod(
                self._worker, "set_refresh",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(int, value)
            )
        self.statusbar.showMessage(f"Atualização: {value} ms")

    def start_monitor(self):
        if not self._is_pi:
            self.statusbar.showMessage("Monitoramento desabilitado: dispositivo não é Raspberry Pi válido.")
            return

        if self._thread is not None:
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._thread = QtCore.QThread(self)
        self._worker = ScannerWorker(self.spin_refresh.value(), self._ignored_bcm_pins, self._reasons_by_pin)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start)
        self._worker.data_ready.connect(self.on_data)
        self._worker.status.connect(self.statusbar.showMessage)

        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)

        self._thread.start()

    def stop_monitor(self):
        if self._worker is not None:
            QtCore.QMetaObject.invokeMethod(self._worker, "stop", QtCore.Qt.ConnectionType.QueuedConnection)
        self.btn_stop.setEnabled(False)

    def _on_thread_finished(self):
        self._thread = None
        self._worker = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def on_data(self, payload: dict):
        pins: Dict[int, PinStatus] = payload.get("pins", {})
        if not pins:
            self.err.setText("Não foi possível ler os pinos (sem dados).")
            return

        missing = []
        if not (which("pinctrl") or which("raspi-gpio")):
            missing.append("pinctrl/raspi-gpio")
        if not which("gpioinfo"):
            missing.append("gpioinfo")
        if not which("i2cdetect"):
            # não é fatal, mas útil para deixar claro
            missing.append("i2cdetect (somente para auto-detecção de HAT via I2C)")
        self.err.setText("" if not missing else f"Ferramentas ausentes: {', '.join(missing)}")

        for phys in range(1, 41):
            st = pins.get(phys)
            if not st:
                continue
            r = phys - 1

            self._set_cell(r, 3, st.mode)
            self._set_cell(r, 4, st.pull)
            self._set_cell(r, 5, st.level)

            if st.bcm is None:
                use_text = "-"
            else:
                use_text = f"{st.used} / {st.consumer}"
            self._set_cell(r, 6, use_text)

            if st.bcm is not None:
                if st.ignored:
                    for c in range(0, 7):
                        it = self.table.item(r, c)
                        it.setForeground(QtGui.QBrush(QtGui.QColor("#9ca3af")))
                else:
                    it = self.table.item(r, 6)
                    if st.used == "SIM":
                        it.setForeground(QtGui.QBrush(QtGui.QColor("#86efac")))
                    elif st.used == "NÃO":
                        it.setForeground(QtGui.QBrush(QtGui.QColor("#94a3b8")))

        self.table.resizeColumnsToContents()

    def _set_cell(self, row: int, col: int, text: str):
        it = self.table.item(row, col)
        if it is None:
            it = QtWidgets.QTableWidgetItem(text)
            self.table.setItem(row, col, it)
        else:
            it.setText(text)

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self._worker is not None:
            try:
                QtCore.QMetaObject.invokeMethod(self._worker, "stop", QtCore.Qt.ConnectionType.QueuedConnection)
            except Exception:
                pass
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
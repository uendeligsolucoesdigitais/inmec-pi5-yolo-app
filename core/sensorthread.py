# core/sensorthread.py

from PySide6.QtCore import QObject, QThread, Signal
import time
from core.sensors import SensorManager
from core.bdlmanager import BDLManager

class SensorWorker(QObject):
    sensores_atualizados = Signal(dict)

    def __init__(self):
        super().__init__()
        self._running = True
        self.sensor = SensorManager()
        self.bdl = BDLManager()

    def run(self):
        while self._running:
            # Leitura imediata
            dados = self.sensor.ler_todos()
            self.sensores_atualizados.emit(dados)

            intervalo_total = self._pegar_intervalo_amostragem()
            intervalo_decorrido = 0
            passo = 0.5  # meio segundo

            while self._running and intervalo_decorrido < intervalo_total:
                time.sleep(passo)
                intervalo_decorrido += passo

    def _pegar_intervalo_amostragem(self):
        try:
            config = self.bdl.get_config_data()
            valor = config.get("AmostraSensores")
            return int(valor) if valor else 120
        except Exception:
            return 120

    def stop(self):
        self._running = False

# core/sensors.py

import platform
import random

class SensorManager:
    def __init__(self):
        self._pi_detected = self._is_raspberry_pi()
        self._sensor_disponivel = self._detectar_hat()

    def _is_raspberry_pi(self):
        """Detecta se estamos rodando num Raspberry Pi"""
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read().lower()
            return "raspberry pi" in cpuinfo or "bcm" in cpuinfo
        except Exception:
            return False

    def _detectar_hat(self):
        """Verifica se o módulo Sensor HAT está disponível"""
        if not self._pi_detected:
            return False

        try:
            import smbus2  # Bibliotecas como base para sensores I2C
            # Aqui podemos tentar acessar um endereço real (ex: 0x76 para BMP280)
            return True  # Supondo presente por enquanto
        except ImportError:
            return False

    def is_pi(self):
        """Retorna True se for Raspberry Pi"""
        return self._pi_detected

    def leitura_disponivel(self):
        """Retorna True se o Sensor HAT real estiver disponível"""
        return self._sensor_disponivel

    def ler_umidade(self):
        """Lê a umidade do ar"""
        if self._sensor_disponivel:
            # TODO: integrar leitura real do Sensor HAT
            return 55.2
        else:
            return self._valor_simulado(45.0, 65.0)

    def ler_temperatura(self):
        """Lê a temperatura"""
        if self._sensor_disponivel:
            # TODO: integrar leitura real do Sensor HAT
            return 26.4
        else:
            return self._valor_simulado(24.0, 30.0)

    def ler_pressao(self):
        """Lê a pressão barométrica"""
        if self._sensor_disponivel:
            # TODO: integrar leitura real do Sensor HAT
            return 1007.3
        else:
            return self._valor_simulado(1000.0, 1015.0)
        
    def ler_luminosidade(self):
        """Lê a luminosidade"""
        if self._sensor_disponivel:
            # TODO: integrar leitura real do Sensor HAT
            return 40.3
        else:
            return self._valor_simulado(40.0, 60.0)        

    def ler_todos(self):
        """
        Retorna um dicionário com todos os valores dos sensores:
        temperatura, umidade e pressão.
        """
        return {
            "temperatura": self.ler_temperatura(),
            "umidade": self.ler_umidade(),
            "pressao": self.ler_pressao(),
            "luminosidade": self.ler_luminosidade(),
            "simulado": not self._sensor_disponivel
        }

    def _valor_simulado(self, minimo, maximo):
        """Gera valor flutuante dentro de uma faixa para simulação"""
        return round(random.uniform(minimo, maximo), 1)

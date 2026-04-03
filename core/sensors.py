# core/sensors.py

import platform
import random
import time

# ----------- BH1750 (GY-30) -----------
try:
    from smbus2 import SMBus as _SMBus
except Exception:
    try:
        from smbus import SMBus as _SMBus
    except Exception:
        _SMBus = None

I2C_BUS         = 1
BH1750_ADDRS    = [0x23, 0x5C]   # tenta os dois endereços possíveis
CMD_POWER_ON    = 0x01
CMD_RESET       = 0x07

# ----------- Sense HAT -----------
try:
    from sense_hat import SenseHat as _SenseHat
    _SH_AVAILABLE = True
except Exception:
    _SenseHat     = None
    _SH_AVAILABLE = False


class SensorManager:
    def __init__(self):
        self._pi_detected        = self._is_raspberry_pi()
        self._bh_bus             = None
        self._bh_addr            = None
        self._sh                 = None
        self._sensor_disponivel  = False

        if self._pi_detected:
            self._inicializar_bh1750()
            self._inicializar_sense_hat()
            self._sensor_disponivel = (self._bh_bus is not None) or (self._sh is not None)

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------

    def _is_raspberry_pi(self):
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read().lower()
            return "raspberry pi" in cpuinfo or "bcm" in cpuinfo
        except Exception:
            return False

    def _inicializar_bh1750(self):
        if _SMBus is None:
            print("BH1750: SMBus indisponível (instale smbus2 ou python3-smbus).")
            return
        try:
            bus = _SMBus(I2C_BUS)
        except Exception as e:
            print(f"BH1750: não foi possível abrir I2C bus: {e}")
            return
        for addr in BH1750_ADDRS:
            try:
                bus.write_byte(addr, CMD_POWER_ON)
                time.sleep(0.01)
                self._bh_bus  = bus
                self._bh_addr = addr
                print(f"BH1750: OK em 0x{addr:02X}")
                return
            except Exception:
                continue
        print("BH1750: nenhum dispositivo encontrado em 0x23 ou 0x5C.")
        self._bh_bus = None

    def _inicializar_sense_hat(self):
        if not _SH_AVAILABLE:
            print("Sense HAT: biblioteca 'sense-hat' não encontrada.")
            return
        try:
            self._sh = _SenseHat()
            print("Sense HAT: OK")
        except Exception as e:
            print(f"Sense HAT: falha ao inicializar: {e}")
            self._sh = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def is_pi(self):
        return self._pi_detected

    def leitura_disponivel(self):
        return self._sensor_disponivel

    def ler_luminosidade(self):
        if self._bh_bus is not None and self._bh_addr is not None:
            try:
                addr = self._bh_addr
                # power on + reset
                self._bh_bus.write_byte(addr, CMD_POWER_ON)
                time.sleep(0.005)
                self._bh_bus.write_byte(addr, CMD_RESET)
                time.sleep(0.010)
                # MTreg padrão 69 — evita valor travado
                self._bh_bus.write_byte(addr, 0x40 | (69 >> 5))
                time.sleep(0.002)
                self._bh_bus.write_byte(addr, 0x60 | (69 & 0x1F))
                time.sleep(0.002)
                # one-time high-res (0x20) — reinicia a cada leitura
                self._bh_bus.write_byte(addr, 0x20)
                time.sleep(0.190)
                data = self._bh_bus.read_i2c_block_data(addr, 0x00, 2)
                raw  = (data[0] << 8) | data[1]
                return round(max(0.0, raw / 1.2), 1)
            except Exception as e:
                print(f"BH1750: erro de leitura: {e}")
            finally:
                try:
                    self._bh_bus.write_byte(self._bh_addr, 0x00)  # power down
                except Exception:
                    pass
        return self._valor_simulado(40.0, 60.0)

    def ler_temperatura(self):
        if self._sh is not None:
            try:
                return round(float(self._sh.get_temperature()), 1)
            except Exception as e:
                print(f"Sense HAT: erro ao ler temperatura: {e}")
        return self._valor_simulado(24.0, 30.0)

    def ler_umidade(self):
        if self._sh is not None:
            try:
                return round(float(self._sh.get_humidity()), 1)
            except Exception as e:
                print(f"Sense HAT: erro ao ler umidade: {e}")
        return self._valor_simulado(45.0, 65.0)

    def ler_pressao(self):
        if self._sh is not None:
            try:
                return round(float(self._sh.get_pressure()), 1)
            except Exception as e:
                print(f"Sense HAT: erro ao ler pressão: {e}")
        return self._valor_simulado(1000.0, 1015.0)

    def ler_todos(self):
        return {
            "temperatura":  self.ler_temperatura(),
            "umidade":      self.ler_umidade(),
            "pressao":      self.ler_pressao(),
            "luminosidade": self.ler_luminosidade(),
            "simulado":     not self._sensor_disponivel,
        }

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _valor_simulado(self, minimo, maximo):
        return round(random.uniform(minimo, maximo), 1)

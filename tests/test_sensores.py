#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Leitura continua: BH1750 (GY-30) + Sense HAT (temp/umid/press)
# Funciona no Raspberry Pi 5. Ctrl+C para sair.

import time
from datetime import datetime

# ----------- BH1750 (GY-30) -----------
try:
    from smbus2 import SMBus
except Exception:
    try:
        from smbus import SMBus
    except Exception:
        SMBus = None

I2C_BUS           = 1
BH1750_ADDR       = 0x5C        # visto no seu i2cdetect
CMD_POWER_ON      = 0x01
CMD_RESET         = 0x07
CMD_CONT_HIGH_RES = 0x10        # modo continuo, alta resolucao

def bh1750_read_lux(bus, addr=BH1750_ADDR):
    bus.write_byte(addr, CMD_POWER_ON)
    bus.write_byte(addr, CMD_RESET)
    bus.write_byte(addr, CMD_CONT_HIGH_RES)
    time.sleep(0.18)            # tempo tipico de conversao
    data = bus.read_i2c_block_data(addr, 0x00, 2)
    raw  = (data[0] << 8) | data[1]
    return max(0.0, raw / 1.2)

# ----------- Sense HAT -----------
try:
    from sense_hat import SenseHat
    SH_AVAILABLE = True
except Exception:
    SH_AVAILABLE = False
    SenseHat     = None

def read_sense(sh):
    # Observacao: temperatura pode estar acima do real por aquecimento interno.
    t = float(sh.get_temperature())
    h = float(sh.get_humidity())
    p = float(sh.get_pressure())
    return t, h, p

# ----------- Main -----------
def main():
    intervalo_s = 1.0

    # BH1750
    bh_bus = None
    if SMBus is not None:
        try:
            bh_bus = SMBus(I2C_BUS)
            # ping rapido para validar 0x5C
            bh_bus.write_byte(BH1750_ADDR, CMD_POWER_ON)
            print(f"BH1750: OK em 0x{BH1750_ADDR:02X}")
        except Exception as e:
            print("BH1750: nao foi possivel inicializar:", e)
            bh_bus = None
    else:
        print("BH1750: SMBus indisponivel (instale smbus2 ou python3-smbus).")

    # Sense HAT
    sh = None
    if SH_AVAILABLE:
        try:
            sh = SenseHat()
            print("Sense HAT: OK")
        except Exception as e:
            print("Sense HAT: falha ao inicializar:", e)
            sh = None
    else:
        print("Sense HAT: biblioteca 'sense-hat' nao encontrada.")

    if bh_bus is None and sh is None:
        print("Nenhum sensor disponivel. Verifique dependencias e conexoes.")
        return

    print("Lendo continuamente... (Ctrl+C para sair)")
    try:
        while True:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Lux
            lux = None
            if bh_bus is not None:
                try:
                    lux = bh1750_read_lux(bh_bus)
                except Exception as e:
                    print("BH1750: erro de leitura:", e)

            # Sense HAT
            t = h = p = None
            if sh is not None:
                try:
                    t, h, p = read_sense(sh)
                except Exception as e:
                    print("Sense HAT: erro de leitura:", e)

            # Saida
            parts = [ts]
            parts.append(f"Lux={lux:.2f}"    if lux is not None else "Lux=NA")
            parts.append(f"Temp={t:.2f}C"    if t   is not None else "Temp=NA")
            parts.append(f"Umid={h:.2f}%"    if h   is not None else "Umid=NA")
            parts.append(f"Press={p:.2f}hPa" if p   is not None else "Press=NA")
            print(" | ".join(parts))

            time.sleep(intervalo_s)

    except KeyboardInterrupt:
        print("\nEncerrado pelo usuario.")
    finally:
        # Desliga BH1750 e fecha o bus
        try:
            if bh_bus is not None:
                bh_bus.write_byte(BH1750_ADDR, 0x00)  # POWER DOWN
                bh_bus.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

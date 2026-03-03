# core/operationserial.py

import time
from core.bdlmanager import LocalDatabaseActions

class OperationSerial:
    _instance = None
    _serial_number = None

    def __init__(self, modulo_id, configDataXml, DEBUG=False):
        self.modulo_id = modulo_id
        self.configDataXml = configDataXml

        if OperationSerial._instance is not None:
            raise Exception("Use OperationSerial.get_serial(modulo_id, configDataXml) para acessar.")

        serial = self._gerar_serial_unico(DEBUG)

        OperationSerial._serial_number = serial
        OperationSerial._instance = self

        data = {
            "Data": int(time.time()),
            "ModuloId": self.modulo_id,
            "Operador": serial
        }

        try:
            db_local = LocalDatabaseActions(configDataXml, DEBUG)
            db_local.insert_into_table("Inicializacoes", data)
            db_local.close()
            if DEBUG:
                print(f"[OperationSerial] Serial salvo no banco local: {serial}")
        except Exception as e:
            print(f"[OperationSerial] ERRO ao salvar no banco local: {e}")

    def _gerar_serial_unico(self, DEBUG=False):
        tentativa = 0
        while True:
            timestamp = int(time.time())
            serial = f"OPR-{self.modulo_id}-{timestamp}"
            if not self._verifica_existencia(serial):
                if DEBUG:
                    print(f"[OperationSerial] Serial gerado: {serial}")
                return serial
            if DEBUG:
                print(f"[OperationSerial] Serial já existe: {serial}, tentando outro...")
            time.sleep(1)  # Evita gerar múltiplos com o mesmo timestamp
            tentativa += 1
            if tentativa > 5:
                raise RuntimeError("Falha ao gerar serial único para operação.")

    def _verifica_existencia(self, serial):
        try:
            db_local = LocalDatabaseActions(self.configDataXml)
            registros = db_local.select_from_table("Inicializacoes", f"Operador = '{serial}'")
            db_local.close()
            return len(registros) > 0
        except Exception as e:
            print(f"[OperationSerial] ERRO ao verificar existência no banco local: {e}")
            return False

    @staticmethod
    def get_serial(modulo_id=None, configDataXml=None, DEBUG=False):
        if OperationSerial._serial_number is None:
            if modulo_id is None or configDataXml is None:
                raise ValueError("ModuloId e configDataXml devem ser fornecidos na primeira chamada.")
            OperationSerial(modulo_id, configDataXml, DEBUG)
        return OperationSerial._serial_number
    
    @staticmethod
    def generate_new_serial(modulo_id, configDataXml, DEBUG=False):
        from core.bdlmanager import LocalDatabaseActions

        tentativa = 0
        while True:
            timestamp = int(time.time())
            serial = f"OPR-{modulo_id}-{timestamp}"

            try:
                db_local = LocalDatabaseActions(configDataXml, DEBUG)
                registros = db_local.select_from_table("Inicializacoes", f"Operador = '{serial}'")
                db_local.close()

                if len(registros) == 0:
                    data = {
                        "Data": int(time.time()),
                        "ModuloId": modulo_id,
                        "Operador": serial
                    }
                    db_local = LocalDatabaseActions(configDataXml, DEBUG)
                    db_local.insert_into_table("Inicializacoes", data)
                    db_local.close()
                    if DEBUG:
                        print(f"[generate_new_serial] Novo serial salvo: {serial}")
                    return serial
                else:
                    if DEBUG:
                        print(f"[generate_new_serial] Serial já existe: {serial}")
            except Exception as e:
                print(f"[generate_new_serial] ERRO ao verificar/inserir: {e}")
                return None

            time.sleep(1)
            tentativa += 1
            if tentativa > 5:
                raise RuntimeError("Falha ao gerar novo OperacaoID.")




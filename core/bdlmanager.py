import os
import sqlite3
from core.configmanager import ConfigManager
from typing import List, Dict
from config.config import BDLManagerConfig
CFG = BDLManagerConfig()

class BDLManager:
    def __init__(self):
        self.config = ConfigManager()
        path = self.config.get(CFG.key_db_path_local)
        name = self.config.get(CFG.key_db_name_local)
        self.db_path = os.path.join(path, name)

    def conectar(self):
        return sqlite3.connect(self.db_path)

    def read(self, tabela, filtro=CFG.read_default_filter):
        try:
            conn = self.conectar()
            cursor = conn.cursor()
            query = f"SELECT * FROM {tabela} WHERE {filtro}"
            cursor.execute(query)
            resultados = cursor.fetchall()
            colunas = [desc[0] for desc in cursor.description]
            conn.close()
            return [dict(zip(colunas, linha)) for linha in resultados]
        except Exception as e:
            print(f"Erro na leitura da tabela {tabela}: {e}")
            return []

    def write(self, tabela, comandos):
        try:
            conn = self.conectar()
            cursor = conn.cursor()
            for comando in comandos.split(CFG.write_cmd_delimiter):
                comando = comando.strip()
                if comando:
                    sql = f"UPDATE {tabela} SET {comando}"
                    cursor.execute(sql)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao escrever no banco: {e}")
            return False

    def get_config_data(self):
        modulo_id = self.config.get("ModuloId")
        resultado = self.read(CFG.table_config, f"{CFG.key_modulo_id} = '{modulo_id}'")
        return resultado[0] if resultado else None
    
    def update_where(self, tabela, dados: dict, filtro: str):
        try:
            conn = self.conectar()
            cursor = conn.cursor()
            set_sql = ", ".join([f"{col} = ?" for col in dados.keys()])
            valores = list(dados.values())
            sql = f"UPDATE {tabela} SET {set_sql} WHERE {filtro}"
            cursor.execute(sql, valores)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao atualizar com filtro no BDL: {e}")
            return False



# ---------------------------------------------
# Classe adicional para suporte ao OperationSerial
# ---------------------------------------------

class LocalDatabaseActions:
    def __init__(self, configDataXml, DEBUG=False):
        self.configDataXml = configDataXml
        self.DEBUG = DEBUG
        self.db_path = os.path.join(
            configDataXml[CFG.key_db_path_local],
            configDataXml[CFG.key_db_name_local]
        )
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def insert_into_table(self, tabela, data: dict):
        colunas = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        valores = list(data.values())
        sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})"
        if self.DEBUG:
            print(f"[LocalDB] INSERT: {sql} | VALORES: {valores}")
        self.cursor.execute(sql, valores)
        self.conn.commit()

    def select_from_table(self, tabela, filtro_sql: str) -> List[Dict]:
        sql = f"SELECT * FROM {tabela} WHERE {filtro_sql}"
        if self.DEBUG:
            print(f"[LocalDB] SELECT: {sql}")
        self.cursor.execute(sql)
        colunas = [desc[0] for desc in self.cursor.description]
        resultados = self.cursor.fetchall()
        return [dict(zip(colunas, row)) for row in resultados]

    def close(self):
        self.conn.close()

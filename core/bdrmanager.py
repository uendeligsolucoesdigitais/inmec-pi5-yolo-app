import mysql.connector
from core.configmanager import ConfigManager
import time  # certifique-se de ter este import no topo
from config.config import BDRManagerConfig
CFG = BDRManagerConfig()

def insert_into_table(self, tabela, data: dict):
    try:
        conn = self.conectar()
        cursor = conn.cursor()

        # Insere o unixtime atual na coluna DataUP
        data["DataUP"] = int(time.time())

        colunas = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        valores = list(data.values())
        sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})"
        cursor.execute(sql, valores)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao inserir no BDR: {e}")
        return False


class BDRManager:
    def __init__(self):
        self.config = ConfigManager()
        self.connection = None

    def conectar(self):
        self.connection = mysql.connector.connect(
            host=self.config.get(CFG.key_host_name),
            port=int(self.config.get(CFG.key_dbport)),
            user=self.config.get(CFG.key_user_name),
            password=self.config.get(CFG.key_user_password),
            database=self.config.get(CFG.key_db_name)
        )
        return self.connection

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
            print(f"Erro na leitura do BDR: {e}")
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
            print(f"Erro ao escrever no BDR: {e}")
            return False
        
    def insert_into_table(self, tabela, data: dict):
        try:
            import time
            conn = self.conectar()
            cursor = conn.cursor()

            colunas_tabela = self.get_colunas(tabela)

            # Adiciona DataUP automaticamente se necessário
            if "DataUP" in colunas_tabela and "DataUP" not in data:
                data["DataUP"] = int(time.time())

            colunas = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            valores = list(data.values())
            sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})"
            cursor.execute(sql, valores)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao inserir no BDR: {e}")
            return False
        
    def get_colunas(self, tabela):
        try:
            conn = self.conectar()
            cursor = conn.cursor()
            cursor.execute(f"SHOW COLUMNS FROM {tabela}")
            colunas = [col[0] for col in cursor.fetchall()]
            conn.close()
            return colunas
        except Exception as e:
            print(f"Erro ao obter colunas da tabela {tabela}: {e}")
            return []
        

    
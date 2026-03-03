import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QLabel
)
from PySide6.QtCore import Signal, QObject
from core.bdlmanager import BDLManager
from core.bdrmanager import BDRManager
import datetime

# Classe para emitir sinais de log
class Logger(QObject):
    log_signal = Signal(str)

logger = Logger()

# Funções de sincronismo (adaptadas do cron.py)
def registrar_log(mensagem):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.log_signal.emit(f"[{timestamp}] {mensagem}")

def sincronizar_config():
    registrar_log("Iniciando sincronização da tabela Config...")
    bdl = BDLManager()
    bdr = BDRManager()

    dados_bdr = bdr.read("Config")
    dados_bdl = bdl.read("Config")

    if not dados_bdr:
        registrar_log("Nenhum dado retornado do BDR.")
        return

    if not dados_bdl:
        registrar_log("Nenhum dado existente no BDL. Sincronização não realizada.")
        return

    colunas_bdr = set(dados_bdr[0].keys())
    colunas_bdl = set(dados_bdl[0].keys())

    colunas_faltando = colunas_bdr - colunas_bdl
    if colunas_faltando:
        registrar_log(f"ATENÇÃO: Colunas faltando no BDL: {', '.join(colunas_faltando)}")
        return

    for registro_bdr in dados_bdr:
        chave = registro_bdr.get("ModuloId")
        if not chave:
            continue
        sucesso = bdl.update_where("Config", registro_bdr, f"ModuloId = '{chave}'")
        if sucesso:
            registrar_log(f"Registro ModuloId={chave} atualizado com sucesso.")
        else:
            registrar_log(f"Erro ao atualizar registro ModuloId={chave}.")
    registrar_log("Sincronização da tabela Config concluída.")

def sincronizar_registros():
    registrar_log("Iniciando sincronização da tabela Registros...")
    bdl = BDLManager()
    bdr = BDRManager()
    dados_bdl = bdl.read("Registros")
    dados_bdr = bdr.read("Registros")

    if not dados_bdl:
        registrar_log("Nenhum dado encontrado no BDL para a tabela Registros.")
        return

    if not dados_bdr:
        dados_bdr = []

    colunas_bdl = set(dados_bdl[0].keys())
    colunas_bdr = set(dados_bdr[0].keys())

    if colunas_bdl != colunas_bdr:
        registrar_log("ERRO: As colunas da tabela Registros entre BDL e BDR são diferentes.")
        return

    colunas_comparacao = [col for col in colunas_bdl if col not in ("idRegistros", "DataUP")]
    pulados = 0
    inseridos = 0

    for reg_bdl in dados_bdl:
        duplicado = any(
            all(reg_bdl[col] == reg_bdr[col] for col in colunas_comparacao)
            for reg_bdr in dados_bdr
        )
        if duplicado:
            pulados += 1
            continue
        novo_reg = {k: v for k, v in reg_bdl.items() if k not in ("idRegistros", "DataUP")}
        sucesso = bdr.insert_into_table("Registros", novo_reg)
        if sucesso:
            inseridos += 1
        else:
            registrar_log(f"Erro ao inserir registro: {novo_reg}")
    registrar_log(f"Sincronização concluída. Pulados: {pulados} | Inseridos: {inseridos}")

def sincronizar_inicializacoes():
    registrar_log("Iniciando sincronização da tabela Inicializacoes...")
    bdl = BDLManager()
    bdr = BDRManager()
    dados_bdl = bdl.read("Inicializacoes")
    dados_bdr = bdr.read("Inicializacoes")

    if not dados_bdl:
        registrar_log("Nenhum dado encontrado no BDL para Inicializacoes.")
        return
    if not dados_bdr:
        dados_bdr = []

    colunas_bdl = set(dados_bdl[0].keys()) - {"id"}
    colunas_bdr = set(dados_bdr[0].keys()) - {"id"}

    if colunas_bdl != colunas_bdr:
        registrar_log("ERRO: Colunas diferentes em Inicializacoes entre BDL e BDR.")
        return

    operadores_bdr = {reg["Operador"] for reg in dados_bdr}
    inseridos = 0
    existentes = 0

    for reg in dados_bdl:
        operador = reg.get("Operador")
        if operador in operadores_bdr:
            existentes += 1
            continue
        novo_reg = {k: v for k, v in reg.items() if k != "id"}
        sucesso = bdr.insert_into_table("Inicializacoes", novo_reg)
        if sucesso:
            inseridos += 1
        else:
            registrar_log(f"Erro ao inserir: {novo_reg}")
    registrar_log(f"Inicializacoes sincronizadas. Existentes: {existentes} | Inseridos: {inseridos}")

# Interface gráfica
class CronGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sincronismo de Dados - InMEC")
        self.setMinimumSize(600, 400)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        self.btn_config = QPushButton("Sincronizar Config")
        self.btn_registros = QPushButton("Sincronizar Registros")
        self.btn_inicializacoes = QPushButton("Sincronizar Inicializacoes")
        self.btn_tudo = QPushButton("Sincronizar Tudo")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Log do Processo de Sincronismo:"))
        layout.addWidget(self.log_box)
        layout.addWidget(self.btn_config)
        layout.addWidget(self.btn_registros)
        layout.addWidget(self.btn_inicializacoes)
        layout.addWidget(self.btn_tudo)

        self.setLayout(layout)

        # Conexões
        logger.log_signal.connect(self.append_log)
        self.btn_config.clicked.connect(lambda: self.run_thread(sincronizar_config))
        self.btn_registros.clicked.connect(lambda: self.run_thread(sincronizar_registros))
        self.btn_inicializacoes.clicked.connect(lambda: self.run_thread(sincronizar_inicializacoes))
        self.btn_tudo.clicked.connect(lambda: self.run_thread(self.run_all))

    def append_log(self, msg):
        self.log_box.append(msg)

    def run_thread(self, func):
        t = threading.Thread(target=func)
        t.start()

    def run_all(self):
        sincronizar_config()
        sincronizar_registros()
        sincronizar_inicializacoes()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = CronGUI()
    gui.show()
    sys.exit(app.exec())

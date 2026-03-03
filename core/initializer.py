import os
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QCoreApplication
from core.configmanager import ConfigManager

class SystemInitializer:
    def __init__(self):
        config = ConfigManager()
        db_path = config.get("db_path_local") or "data"
        db_name = config.get("db_name_local") or "bdinMEC.db"

        self.required_files = [
            (db_name, db_path),
            ("bdl.svg", "img/svg"),
            ("bdr.svg", "img/svg"),
            ("best.pt", "datasets"),
            ("camera.svg", "img/svg"),
            ("cameraManager.py", "modules"),
            ("config.xml", "config"),
            ("delete.svg", "img/svg"),
            ("deteccao.svg", "img/svg"),
            ("erro.svg", "img/svg"),
            ("favicon.ico", "img"),
            ("favicon.png", "img"),
            ("ia.svg", "img/svg"),
            ("internet.svg", "img/svg"),
            ("janelaPrincipal.py", ""),
            ("licenca.svg", "img/svg"),
            ("logo.png", "img"),
            ("main.py", ""),
            ("manual.svg", "img/svg"),
            ("ok.svg", "img/svg"),
            ("operacao.png", "img"),
            ("problema.svg", "img/svg"),
            ("sair.svg", "img/svg"),
            ("selfTest.py", "core"),
            ("sensores.svg", "img/svg"),
            ("sincronizando.svg", "img/svg"),
            ("splash.png", "img"),
            ("topBar.py", "ui"),
            ("yolov8m-seg.pt", "datasets"),
            ("yolov8n-seg.pt", "datasets"),
        ]


    def verificar_arquivos_obrigatorios(self):
        """Verifica se todos os arquivos obrigatórios estão presentes."""
        arquivos_ausentes = []

        for nome_arquivo, pasta in self.required_files:
            caminho_completo = os.path.join(pasta, nome_arquivo)
            if not os.path.isfile(caminho_completo):
                arquivos_ausentes.append(caminho_completo)

        return arquivos_ausentes

    def mostrar_erro_arquivos(self, arquivos_ausentes):
        """Exibe uma mensagem de erro informando quais arquivos estão ausentes usando PySide6."""
        app = QApplication.instance() or QApplication(sys.argv)

        mensagem = "Os seguintes arquivos estão ausentes:\n\n"
        mensagem += "\n".join(arquivos_ausentes)
        mensagem += "\n\nO sistema não pode ser iniciado."

        QMessageBox.critical(None, "Erro de Arquivos", mensagem)
        QCoreApplication.quit()
        sys.exit(1)

    def iniciar_sistema(self):
        """Executa os procedimentos de verificação e inicialização."""
        print("Iniciando verificação de arquivos...")

        arquivos_faltando = self.verificar_arquivos_obrigatorios()

        if arquivos_faltando:
            self.mostrar_erro_arquivos(arquivos_faltando)

        print("Todos os arquivos obrigatórios foram encontrados.")
        print("Inicializando o sistema...")

        # Exemplo: chamada da interface principal
        # from core.interface import iniciar_interface
        # iniciar_interface()

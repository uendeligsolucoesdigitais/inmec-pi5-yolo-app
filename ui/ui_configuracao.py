import xml.etree.ElementTree as ET
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QFormLayout,
    QPushButton, QHBoxLayout, QMessageBox, QWidget, QTabWidget,
    QCheckBox, QComboBox, QSpinBox
)


class ConfiguracaoDialog(QDialog):
    def __init__(self, caminho_xml, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações do Sistema")
        self.setMinimumSize(600, 400)
        self.caminho_xml = caminho_xml
        self.campos = {}

        self.setStyleSheet("""
            QTabWidget::pane { border: 1px solid white; margin: 5px; }
            QTabBar::tab { background: #455A64; color: white; padding: 6px; border-radius: 4px; margin-right: 4px; }
            QTabBar::tab:selected { background: #1E88E5; }

            QLabel { color: white; font-weight: bold; padding: 3px; }

            QCheckBox { color: white; padding: 2px; }

            QPushButton {
                padding: 6px 12px;
                background-color: rgba(255,255,255,0.3) !important;
                color: white !important;
                border: 1px solid white;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.7) !important;
                color: black !important;
            }
            QPushButton:pressed {
                background-color: rgba(255,255,255,1.0) !important;
            }

            QWidget { background-color: #2E4459; }
        """)

        self._criar_tela_login()

    def _criar_tela_login(self):
        layout = QVBoxLayout(self)
        self.label_info = QLabel("<h2>Configuração do Sistema</h2>")
        self.label_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_info)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Login")
        self.login_input.setStyleSheet("background-color: white; color: black; padding: 3px; border-radius: 4px;")
        layout.addWidget(self.login_input)

        self.senha_input = QLineEdit()
        self.senha_input.setPlaceholderText("Senha")
        self.senha_input.setEchoMode(QLineEdit.Password)
        self.senha_input.setStyleSheet("background-color: white; color: black; padding: 3px; border-radius: 4px;")
        layout.addWidget(self.senha_input)

        btn_login = QPushButton("Acessar")
        btn_login.clicked.connect(self._verificar_login)
        layout.addWidget(btn_login)

    def _verificar_login(self):
        if self.login_input.text().strip() == "admin" and self.senha_input.text().strip() == "@Inmec#2025#":
            self._carregar_formulario()
        else:
            QMessageBox.warning(self, "Erro", "Login ou senha incorretos.")

    def _carregar_formulario(self):
        # Remove tela de login
        for i in reversed(range(self.layout().count())):
            widget = self.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not os.path.exists(self.caminho_xml):
            QMessageBox.critical(self, "Erro", "Arquivo de configuração XML não encontrado.")
            return

        tree = ET.parse(self.caminho_xml)
        root = tree.getroot()
        config_node = root.find("config")

        if config_node is None:
            QMessageBox.critical(self, "Erro", "Tag <config> não encontrada no XML.")
            return

        self.tabs = QTabWidget()
        tabs_data = {
            "Banco de Dados Local": ["db_name", "db_path_local", "db_name_local"],
            "Banco de Dados Remoto": ["host_name", "dbport", "user_name", "user_password"],
            "Identificação": ["Cliente", "Serial", "ModuloId", "CamId"],
            "Operação": ["Classes", "Model", "Videoteste"],
            "Parâmetros": [
                "MODO",
                "FAZER_TESTE",
                "verificar_dependencias",
                "bloqueio",
                "PIN_PEDAL_BCM"
            ]
        }

        label_personalizados = {
            "db_name": "Nome do DB Local",
            "db_path_local": "Caminho do DB Local",
            "db_name_local": "Nome Arquivo do DB Local",
            "host_name": "Hostname",
            "dbport": "Porta",
            "user_name": "Username",
            "user_password": "Password",
            "Cliente": "Cliente",
            "Serial": "Serial",
            "ModuloId": "ModuloID",
            "CamId": "CamID",
            "Classes": "Classes",
            "Model": "Modelo IA",
            "Videoteste": "Vídeo de Teste",
            "MODO": "Modo de Operação",
            "FAZER_TESTE": "Fazer Testes",
            "verificar_dependencias": "Verificar Dependências Linux",
            "bloqueio": "Número de bloqueios",
            "PIN_PEDAL_BCM": "Pino do Pedal (BCM)"
        }

        self.formularios = {}
        for tab in tabs_data:
            widget = QWidget()
            form = QFormLayout()
            widget.setLayout(form)
            self.tabs.addTab(widget, tab)
            self.formularios[tab] = form

        self.layout().addWidget(self.tabs)

        # Leitura dinâmica dos campos
        for elem in config_node:
            tag = elem.tag
            if tag in ["salt", "Versao", "senha_hash"]:
                continue

            valor = elem.text or ""
            campo = None

            if tag == "MODO":
                campo = QComboBox()
                campo.addItems(["no_rb", "rb"])
                idx = campo.findText(valor)
                if idx != -1:
                    campo.setCurrentIndex(idx)
                campo.setStyleSheet("background-color: white; color: black; padding: 3px; border-radius: 4px;")

            elif tag in ["FAZER_TESTE", "verificar_dependencias"]:
                campo = QCheckBox()
                campo.setChecked(valor.lower() == "true")

            elif tag == "user_password":
                campo = QLineEdit(valor)
                campo.setEchoMode(QLineEdit.Password)
                campo.setStyleSheet("background-color: white; color: black; padding: 3px; border-radius: 4px;")

            elif tag == "PIN_PEDAL_BCM":
                campo = QSpinBox()
                campo.setMinimum(0)
                campo.setMaximum(40)
                try:
                    campo.setValue(int(valor))
                except:
                    campo.setValue(0)
                campo.setStyleSheet("background-color: white; color: black; padding: 3px; border-radius: 4px;")

            else:
                campo = QLineEdit(valor)
                campo.setStyleSheet("background-color: white; color: black; padding: 3px; border-radius: 4px;")

            self.campos[tag] = campo
            label = QLabel(label_personalizados.get(tag, tag))

            for aba, campos in tabs_data.items():
                if tag in campos:
                    self.formularios[aba].addRow(label, campo)
                    break

        # Botões → agora com texto branco e hover preto
        botoes = QHBoxLayout()

        btn_salvar = QPushButton("Salvar")
        btn_salvar.setStyleSheet("""
            QPushButton { color: white !important; }
            QPushButton:hover { color: black !important; }
        """)
        btn_salvar.clicked.connect(self._salvar_config)

        btn_cancelar = QPushButton("Sair sem Salvar")
        btn_cancelar.setStyleSheet("""
            QPushButton { color: white !important; }
            QPushButton:hover { color: black !important; }
        """)
        btn_cancelar.clicked.connect(self.reject)

        botoes.addWidget(btn_salvar)
        botoes.addWidget(btn_cancelar)
        self.layout().addLayout(botoes)

    def _salvar_config(self):
        try:
            tree = ET.parse(self.caminho_xml)
            root = tree.getroot()
            config_node = root.find("config")

            for elem in config_node:
                tag = elem.tag
                if tag in self.campos:
                    campo = self.campos[tag]

                    if isinstance(campo, QCheckBox):
                        elem.text = "true" if campo.isChecked() else "false"
                    elif isinstance(campo, QComboBox):
                        elem.text = campo.currentText()
                    elif isinstance(campo, QSpinBox):
                        elem.text = str(campo.value())
                    else:
                        elem.text = campo.text().strip()

            tree.write(self.caminho_xml, encoding="utf-8", xml_declaration=True)
            QMessageBox.information(self, "Salvo", "Configurações salvas com sucesso.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {str(e)}")


# Exemplo para teste rápido
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<root>
    <config>
        <db_name>config_db</db_name>
        <db_path_local>/home/user/data</db_path_local>
        <db_name_local>database.db</db_name_local>
        <host_name>localhost</host_name>
        <dbport>5432</dbport>
        <user_name>admin</user_name>
        <user_password>12345</user_password>
        <Cliente>INMEC</Cliente>
        <Serial>12345</Serial>
        <ModuloId>1</ModuloId>
        <CamId>2</CamId>
        <Classes>Car,Bike</Classes>
        <Model>model_v1</Model>
        <Videoteste>video.mp4</Videoteste>
        <MODO>no_rb</MODO>
        <FAZER_TESTE>true</FAZER_TESTE>
        <verificar_dependencias>false</verificar_dependencias>
        <bloqueio>5</bloqueio>
        <PIN_PEDAL_BCM>17</PIN_PEDAL_BCM>
        <salt>xyz</salt>
        <Versao>1.0</Versao>
        <senha_hash>abc</senha_hash>
    </config>
</root>"""

    caminho_xml_temp = "config_temp.xml"
    with open(caminho_xml_temp, "w", encoding="utf-8") as f:
        f.write(xml_content)

    app = QApplication(sys.argv)
    dialog = ConfiguracaoDialog(caminho_xml_temp)
    dialog.exec()

    os.remove(caminho_xml_temp)
    sys.exit()

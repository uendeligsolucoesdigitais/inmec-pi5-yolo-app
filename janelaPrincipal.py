from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from ui.topBar import TopBarWidget
from ui.contentWidget import ContentWidget
from ui.statusBar import StatusBarManager
from core.configmanager import ConfigManager
from core.print_hook import install_statusbar_print_hook

class JanelaPrincipal(QMainWindow):
    def __init__(self, modulo_id="---", operacao_id="---"):
        super().__init__()

        self.setWindowTitle("InMEC Principal")
        #self.setMinimumSize(1024, 600)
        #self.setMaximumSize(1024,600)
        self.setFixedSize(1024,600)

        # Carrega configurações
        self.config_manager = ConfigManager()
        self.configDataXml = self.config_manager.get_tudo()
        self.configData = {
            "ModuloId": self.config_manager.get("ModuloId"),
            "Serial": self.config_manager.get("Serial"),
            "Cliente": self.config_manager.get("Cliente")
        }

        # Widget central e layout principal
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #2E4459;")
        self.setCentralWidget(central_widget)

        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(layout_principal)

        self.top_bar = TopBarWidget(modulo_id, operacao_id)

        self.top_bar.atualizar_modulo_operacao(self.configData["ModuloId"], operacao_id)
        layout_principal.addWidget(self.top_bar)

        self.status_bar_manager = StatusBarManager()
        self.setStatusBar(self.status_bar_manager)
        install_statusbar_print_hook(self.status_bar_manager)

        self.content_widget = ContentWidget(
            status_bar=self.status_bar_manager,
            configData=self.configData,
            configDataXml=self.configDataXml
        )
        layout_principal.addWidget(self.content_widget)

        #self.showFullScreen()

    def keyPressEvent(self, event):
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key_Escape:
            self.close()

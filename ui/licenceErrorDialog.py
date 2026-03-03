from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QCoreApplication

class LicenceErrorDialog(QDialog):
    def __init__(self, mensagem):
        super().__init__()
        self.setWindowTitle("Erro de Licenciamento")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet("background-color: #2E4459; color: white;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        label = QLabel(mensagem)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px;")
        layout.addWidget(label)

        btn_fechar = QPushButton("Fechar Aplicativo")
        btn_fechar.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 8px;")
        btn_fechar.clicked.connect(QCoreApplication.quit)
        layout.addWidget(btn_fechar)

        self.setLayout(layout)

import sys
import os
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QTimer, Qt
from janelaPrincipal import JanelaPrincipal
from core.configmanager import ConfigManager
from core.operationserial import OperationSerial
from core.audio_player import AudioPlayer


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: #2E4459;")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        splash_path = "img/splash.png"
        splash_label = QLabel()
        splash_label.setAlignment(Qt.AlignCenter)

        if os.path.exists(splash_path):
            pixmap = QPixmap(splash_path)
            splash_label.setPixmap(pixmap)  # mantém tamanho original
        else:
            splash_label.setText("Splash não encontrado")
            splash_label.setStyleSheet("color: white; font-size: 24px;")

        layout.addWidget(splash_label)
        self.setLayout(layout)


        # Reproduz o áudio de boas-vindas assim que o splash é exibido (thread separada)
        try:
            self._audio_player = AudioPlayer(mp3_dir="mp3")
            self._audio_player.playmp3("boas_vindas.mp3")
        except Exception as _e:
            print(f"[Áudio splash] Não foi possível iniciar o áudio: {_e}")
        QTimer.singleShot(3000, self.iniciar_principal)  # 3 segundos

    def iniciar_principal(self):
        config = ConfigManager()
        modulo_id = config.get("ModuloId")
        config_xml = config.get_tudo()
        operacao_serial = OperationSerial.get_serial(modulo_id=modulo_id, configDataXml=config_xml)

        self.close()
        self.janela = JanelaPrincipal(modulo_id=modulo_id, operacao_id=operacao_serial)
        self.janela.show()


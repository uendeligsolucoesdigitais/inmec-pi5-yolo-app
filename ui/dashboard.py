import os
import platform
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from core.bdlmanager import BDLManager

try:
    import ultralytics
    YOLO_VERSION = ultralytics.__version__
except ImportError:
    YOLO_VERSION = "Desconhecida"

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        painel_layout = QVBoxLayout()
        #painel_layout.setSpacing(10)
        painel_layout.setAlignment(Qt.AlignTop)
        painel_layout.setContentsMargins(0, 0, 0, 50)

        # Definir as variáveis de estilo
        paddingBot = '5px 5px 5px 5px'
        marginBot = 0
        fontsizeBot = 14
        label_height = 30

        # Criar uma string de estilo única para os QLabels
        estilo_label = f"color: white; font-size: {fontsizeBot}; padding: {paddingBot}px; margin: {marginBot}px; background:#162635; color:#e8f0f6; border:1px solid #3f5a73; border-radius:5px;"

        # Criar os QLabels
        self.label_sistema = QLabel(f"🖥️ Sistema: {self._detectar_sistema()}")
        self.label_stream = QLabel(f"📡 Stream: {self._detectar_stream()}")
        self.label_ver_ia = QLabel(f"🤖 YOLO: {YOLO_VERSION}")
        self.label_classe_conforme = QLabel("✅ Classe conforme: ---")
        self.label_classe_nc = QLabel("⚠️ Classe NC: ---")

        # Garantir modo mais rápido: PlainText (evita parser RichText/HTML)
        self.label_classe_conforme.setTextFormat(Qt.PlainText)
        self.label_classe_nc.setTextFormat(Qt.PlainText)

        """
        self.label_resolucao = QLabel("🎥 Resolução: ---")
        self.label_video_padrao = QLabel("🎞️ Vídeo: ---")
        self.label_proporcao = QLabel("📺 Proporção: ---")
        self.label_bitrate = QLabel("📶 Bitrate: ---")
        """
        labels_base = [
            self.label_sistema,
            self.label_stream,
            self.label_ver_ia,
        ]
        for label in labels_base:
            label.setStyleSheet(estilo_label)
            label.setFixedHeight(label_height)
            painel_layout.addWidget(label)


        for lbl in (self.label_classe_conforme, self.label_classe_nc):
            lbl.setStyleSheet(estilo_label)              # mantém seu estilo
            lbl.setWordWrap(True)                        # permite 2 linhas
            lbl.setTextFormat(Qt.PlainText)              # mais rápido
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop) # alinha topo-esquerda
            painel_layout.addWidget(lbl)
    


        # Finalizar o layout
        self.setLayout(painel_layout)
        self._carregar_classes()

        self.setStyleSheet(f"background-color: #3a556f; border-radius: 7px; padding: 0px 5px 0px 5px;")

    def _carregar_classes(self):
        """Lê a classe 'conforme' do BDL/Config e atualiza o painel."""
        try:
            config = BDLManager().get_config_data()
            conforme = (config.get("Classes") or "").strip()
            if conforme:
                self._set_classes(conforme, f"{conforme}_nc")
            else:
                self._set_classes("---", "---")
        except Exception as e:
            self._set_classes(f"Erro ao ler", f"{e}")

    def _set_classes(self, conforme: str, nao_conforme: str):
        # Método mais rápido: texto simples com quebra de linha via \n
        self.label_classe_conforme.setText(f"✅ Classe conforme:\n{conforme}")
        self.label_classe_nc.setText(f"⚠️ Classe NC:\n{nao_conforme}")


    def update_classes(self, conforme: str):
        """API pública para a tela atualizar depois de trocar a classe."""
        conforme = (conforme or "").strip()
        if not conforme:
            self._set_classes("---", "---")
        else:
            self._set_classes(conforme, f"{conforme}_nc")

    def _detectar_sistema(self):
        try:
            sistema = platform.system()
            arquitetura = platform.machine()

            if sistema == "Linux":
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpuinfo = f.read()
                        if "Raspberry Pi" in cpuinfo or "BCM" in cpuinfo:
                            return "Raspberry Pi (Linux)"
                except Exception:
                    pass
                return "Linux"
            elif sistema == "Windows":
                return "Windows"
            elif sistema == "Darwin":
                return "macOS"
            else:
                return f"{sistema} ({arquitetura})"
        except Exception as e:
            return f"Erro: {e}"

    def _detectar_stream(self):
        return "USB / MJPEG"

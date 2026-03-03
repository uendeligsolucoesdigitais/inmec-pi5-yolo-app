# topBar.py

import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt
from core.configmanager import ConfigManager
from core.operationserial import OperationSerial  # <- IMPORTADO

class TopBarWidget(QWidget):
    def __init__(self, modulo_id, operacao_id):

        super().__init__()

        self.setFixedHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background-color: #2E4459;")

        config = ConfigManager()
        modulo_id = config.get("ModuloId")
        config_xml = config.get_tudo()
        operacao_serial = OperationSerial.get_serial(modulo_id=modulo_id, configDataXml=config_xml)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(0)

        linha_superior = QHBoxLayout()
        linha_superior.setContentsMargins(15, 0, 15, 0)
        linha_superior.setSpacing(30)

        # LOGO
        logo_label = QLabel()
        logo_path = "img/logo.png"
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaledToHeight(50, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("-")
            logo_label.setStyleSheet("color: white; font-size: 24px;")
        logo_label.setFixedHeight(50)
        linha_superior.addWidget(logo_label, alignment=Qt.AlignLeft)

        # BLOCO DE TEXTO
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        modulo_layout = QHBoxLayout()
        modulo_layout.setSpacing(5)
        icon_modulo = self._carregar_svg("img/svg/ModuloID.svg", size=16, cor="white")
        self.label_modulo = QLabel(f"Módulo ID: {modulo_id}")
        self.label_modulo.setStyleSheet("color: white; font-size: 14px;")
        modulo_layout.addWidget(icon_modulo)
        modulo_layout.addWidget(self.label_modulo)

        operacao_layout = QHBoxLayout()
        operacao_layout.setSpacing(5)
        icon_operacao = self._carregar_svg("img/svg/OperacaoID.svg", size=16, cor="white")
        self.label_operacao = QLabel(f"Operação ID: {operacao_serial}")
        self.label_operacao.setStyleSheet("color: white; font-size: 14px;")
        operacao_layout.addWidget(icon_operacao)
        operacao_layout.addWidget(self.label_operacao)

        info_layout.addLayout(modulo_layout)
        info_layout.addLayout(operacao_layout)
        linha_superior.addLayout(info_layout)

        # ÍCONES DE STATUS
        self.icones_status = {}
        icones = ["licenca", "bdl", "bdr", "audio", "internet", "sensores", "ia"]
        icones_direita_layout = QHBoxLayout()
        icones_direita_layout.setSpacing(10)
        for nome in icones:
            widget_icon = self._carregar_svg(f"img/svg/{nome}.svg", cor="white")
            self.icones_status[nome] = widget_icon
            icones_direita_layout.addWidget(widget_icon)

        linha_superior.addStretch()
        linha_superior.addLayout(icones_direita_layout)
        layout.addLayout(linha_superior)

        linha_inferior = QFrame()
        linha_inferior.setFrameShape(QFrame.HLine)
        linha_inferior.setFixedHeight(1)
        linha_inferior.setStyleSheet("background-color: white;")
        layout.addWidget(linha_inferior)

    def _carregar_svg(self, caminho, size=50, cor="white"):
        label = QLabel()
        label.setFixedSize(size, size)
        label.setAlignment(Qt.AlignCenter)

        if not os.path.exists(caminho):
            label.setText("-")
            label.setStyleSheet(f"color: {cor}; font-size: 18px;")
            return label

        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        renderer = QSvgRenderer(caminho)
        painter = QPainter(image)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), QColor(cor))
        painter.end()

        label.setPixmap(QPixmap.fromImage(image))
        return label

    def atualizar_modulo_operacao(self, modulo_id: str, operacao_id: str):
        self.label_modulo.setText(f"Módulo ID: {modulo_id}")
        self.label_operacao.setText(f"Operação ID: {operacao_id}")

    def set_status_icon(self, nome, status):
        if nome not in self.icones_status:
            print(f"⚠️ Ícone '{nome}' não encontrado na topbar.")
            return

        cor = {
            "ok": "#73d673",
            "erro": "#73d673",
            "gray": "#9ab8d4"
        }.get(status, "transparent")

        widget_novo = self._carregar_svg(f"img/svg/{nome}.svg", cor=cor)
        self.icones_status[nome].setPixmap(widget_novo.pixmap())

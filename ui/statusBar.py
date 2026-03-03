import os
from PySide6.QtWidgets import QStatusBar, QLabel, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QColor, QPixmap
from PySide6.QtSvg import QSvgRenderer

class StatusBarManager(QStatusBar):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.setStyleSheet("background-color: #1F2F3D; color: white;")

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(20, 5, 0, 5)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.icon_label = self._load_icon("img/svg/terminal.svg", size=16, color="white")
        self.label_status = QLabel("Pronto")
        self.label_status.setStyleSheet("color: white; font-size: 12px;")
        self.label_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.label_status)

        self.addWidget(container)

    def atualizar_mensagem(self, mensagem: str):
        self.label_status.setText(mensagem)

    def _load_icon(self, path, size=16, color="white"):
        # Carrega um SVG com cor branca, ou retorna placeholder
        if not os.path.exists(path):
            label = QLabel("?")
            label.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: bold;")
            label.setFixedSize(size, size)
            label.setAlignment(Qt.AlignCenter)
            return label

        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        renderer = QSvgRenderer(path)
        painter = QPainter(image)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), QColor(color))
        painter.end()

        label = QLabel()
        label.setPixmap(QPixmap.fromImage(image))
        label.setFixedSize(size, size)
        return label

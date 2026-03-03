from PySide6.QtGui import QIcon, QImage, QPainter, QColor, QPixmap
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer


def carregar_svg_branco(caminho, tamanho=20):
    """Carrega um SVG e o renderiza em uma cor branca."""
    image = QImage(tamanho, tamanho, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    renderer = QSvgRenderer(caminho)
    painter = QPainter(image)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(image.rect(), QColor("white"))
    painter.end()
    return QIcon(QPixmap.fromImage(image))
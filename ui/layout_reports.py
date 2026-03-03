from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout, QScrollArea
from PySide6.QtCore import Qt
from ui.utils import carregar_svg_branco


def create_reports_layout(parent_widget):
    """Cria e retorna o layout da interface de relatórios."""
    grid = QGridLayout()
    grid.setSpacing(10)
    grid.setContentsMargins(20, 20, 20, 20)

    # Painel lateral
    painel_layout = QVBoxLayout()
    painel_titulo = QLabel("Painel de Controle")
    painel_titulo.setStyleSheet("color: white; font-size: 18px;")
    painel_layout.addWidget(painel_titulo)
    painel_layout.addStretch()

    btn_voltar = QPushButton(" Voltar à Operação")
    btn_voltar.setStyleSheet("background-color: orange; color: white; font-size: 14px; padding: 10px; border-radius: 6px;")
    btn_voltar.setIcon(carregar_svg_branco("img/svg/reiniciar.svg", tamanho=30))
    btn_voltar.clicked.connect(parent_widget._reiniciar_aplicacao)
    painel_layout.addWidget(btn_voltar)

    painel_widget = QWidget()
    painel_widget.setLayout(painel_layout)
    painel_widget.setMinimumWidth(200)
    painel_widget.setStyleSheet("background-color: #3a556f; border-radius: 10px;")
    grid.addWidget(painel_widget, 0, 0)

    # Área de relatórios
    layout_reports = QGridLayout()
    layout_reports.setSpacing(15)
    layout_reports.setContentsMargins(10, 10, 10, 10)

    for i in range(9):
        bloco = QLabel(f"Relatório {i+1}")
        bloco.setStyleSheet("background-color: white; color: black; padding: 30px; border-radius: 10px; font-size: 16px;")
        bloco.setAlignment(Qt.AlignCenter)
        layout_reports.addWidget(bloco, i // 3, i % 3)

    reports_widget = QWidget()
    reports_widget.setLayout(layout_reports)
    reports_widget.setStyleSheet("background-color: #2E4459;")

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(reports_widget)

    grid.addWidget(scroll, 0, 1)
    grid.setColumnStretch(0, 0)
    grid.setColumnStretch(1, 1)
    return grid
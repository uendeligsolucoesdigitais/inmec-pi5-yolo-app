from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QSizePolicy, QWidget, QPushButton
)
from PySide6.QtCore import Qt
from ui.utils import carregar_svg_branco
from ui.dashboard import DashboardWidget  # mantido para compatibilidade (retorno), mas não é exibido


def create_operational_layout(parent_widget, acoes):
    """Cria e retorna o layout operacional completo, incluindo botões, câmera e painéis."""
    grid = QGridLayout()
    grid.setSpacing(5)
    grid.setContentsMargins(5, 5, 5, 5)

    # =========================
    # Painel de Controle (coluna 0) — MANTIDO
    # =========================
    painel_layout = QVBoxLayout()
    painel_layout.setSpacing(8)
    painel_layout.setContentsMargins(6, 10, 6, 10)

    estilo_botao_icone = """
        QPushButton {
            background: transparent;
            border: 1px solid #e8f0f6;
            border-radius: 8px;
            padding: 6px;
            qproperty-iconSize: 22px;
        }
        QPushButton:hover { background: rgba(255,255,255,0.15); }
    """
    estilo_botao_icone_tooltip = estilo_botao_icone

    botoes = {}
    botoes_infos = [
        ("reiniciar_operacao", "Nova Operação"),
        ("configuracao", "Configuração"),
        ("adicionar_nc", "Adicionar NC"),
        ("acao_em_massa", "Ação em massa"),
        ("relatorios", "Relatórios"),
        ("pausar_deteccao", "Pausar Detecção"),
        ("atualizar_classe", "Atualizar classe")
    ]

    for nome, texto in botoes_infos:
        botao = QPushButton()
        botao.setIcon(carregar_svg_branco(f"img/svg/{nome}.svg", tamanho=22))
        botao.setToolTip(texto)
        botao.setStyleSheet(estilo_botao_icone_tooltip)
        botao.setFixedSize(50, 40)
        painel_layout.addWidget(botao, 0, Qt.AlignHCenter)
        botoes[nome] = botao

    painel_layout.addStretch()

    # Botão laranja "Reiniciar"
    botao_reiniciar_laranja = QPushButton()
    botao_reiniciar_laranja.setIcon(carregar_svg_branco("img/svg/reiniciar.svg", tamanho=22))
    botao_reiniciar_laranja.setToolTip("Reiniciar")
    botao_reiniciar_laranja.setStyleSheet("""
        QPushButton {
            background-color: #f19267;
            border: none;
            border-radius: 8px;
            padding: 8px;
            qproperty-iconSize: 22px;
        }
        QPushButton:hover { background-color: #e65b0f; }
    """)
    botao_reiniciar_laranja.setFixedSize(50, 40)
    botao_reiniciar_laranja.clicked.connect(parent_widget._reiniciar_aplicacao)
    painel_layout.addWidget(botao_reiniciar_laranja, 0, Qt.AlignHCenter)

    # Botão "Sair"
    botao_sair = QPushButton()
    botao_sair.setIcon(carregar_svg_branco("img/svg/sair.svg", tamanho=22))
    botao_sair.setToolTip("Sair")
    botao_sair.setStyleSheet("""
        QPushButton {
            background-color: #f74a5c;
            border: none;
            border-radius: 8px;
            padding: 8px;
            qproperty-iconSize: 22px;
        }
        QPushButton:hover { background-color: #f72e43; }
    """)
    botao_sair.setFixedSize(50, 40)
    painel_layout.addWidget(botao_sair, 0, Qt.AlignHCenter)

    painel_widget = QWidget()
    painel_widget.setLayout(painel_layout)
    painel_widget.setFixedWidth(70)
    painel_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    painel_widget.setStyleSheet("background-color: #3a556f; border-radius: 10px;")
    grid.addWidget(painel_widget, 0, 0)

    # =========================
    # Detectores (coluna 1) — MANTIDO
    # =========================
    detector_layout = QVBoxLayout()

    camera_label = QLabel()
    camera_label.setStyleSheet("background-color: #000;")
    camera_label.setAlignment(Qt.AlignCenter)
    camera_label.setMaximumHeight(420)
    camera_label.setScaledContents(True)

    camera_center_layout = QVBoxLayout()
    camera_center_layout.setContentsMargins(12, 10, 12, 10)  # ~5% de margem
    camera_center_layout.addStretch()
    camera_center_layout.addWidget(camera_label, alignment=Qt.AlignCenter)
    camera_center_layout.addStretch()

    camera_widget = QWidget()
    camera_widget.setLayout(camera_center_layout)
    camera_widget.setStyleSheet(
        "background-color: transparent; border: 2px solid #3a556f; border-radius: 10px;"
    )

    detector_layout.addWidget(camera_widget, stretch=1)

    detector_widget = QWidget()
    detector_widget.setLayout(detector_layout)
    detector_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    grid.addWidget(detector_widget, 0, 1)

    # =========================
    # Coluna da direita — APENAS CONTADORES + SENSORES
    # =========================
    coluna_direita_layout = QVBoxLayout()
    coluna_direita_layout.setSpacing(12)              # espaço entre blocos
    coluna_direita_layout.setContentsMargins(2, 2, 2, 2)

    # ---- (REMOVIDO) Dashboard: não será adicionado ao layout
    dashboard_widget = DashboardWidget(parent_widget)
    dashboard_widget.setVisible(False)  # mantém compatibilidade sem exibir

    # ---- CONTADORES
    contador_layout = QVBoxLayout()
    contador_layout.setSpacing(10)

    estilo_bloco = lambda cor: (
        f"background-color: {cor};"
        "color: black;"
        "font-weight: bold;"
        "padding: 6px 4px;"
        "border-radius: 10px;"
        "font-size: 13px;"
    )

    label_detectados = QLabel("DETECTADOS: 0")
    label_detectados.setAlignment(Qt.AlignCenter)
    label_detectados.setStyleSheet(estilo_bloco("#55c4c5"))
    label_detectados.setFixedHeight(50)
    contador_layout.addWidget(label_detectados)

    label_nao_conforme = QLabel("NÃO CONFORME: 0")
    label_nao_conforme.setAlignment(Qt.AlignCenter)
    label_nao_conforme.setStyleSheet(estilo_bloco("#f6918b"))
    label_nao_conforme.setFixedHeight(50)
    contador_layout.addWidget(label_nao_conforme)

    label_totais = QLabel("TOTAIS: 0")
    label_totais.setAlignment(Qt.AlignCenter)
    label_totais.setStyleSheet(estilo_bloco("#f7f4b1"))
    label_totais.setFixedHeight(50)
    contador_layout.addWidget(label_totais)

    contador_widget = QWidget()
    contador_widget.setLayout(contador_layout)
    coluna_direita_layout.addWidget(contador_widget)

    # ---- SENSORES
    painel_sensores = QVBoxLayout()
    painel_sensores.setSpacing(4)

    def _sensor_row(cor, texto):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background-color: {cor}; border-radius: 4px; min-width: 8px; max-width: 8px;"
        )
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: white; font-size: 12px;")
        row.addWidget(dot, 0, Qt.AlignVCenter)
        row.addWidget(lbl, 1)
        return row, lbl

    row_temp, label_temp = _sensor_row("#EF4444", "Temperatura: -- °C")
    row_umi,  label_umi  = _sensor_row("#22D3EE", "Umidade: -- %")
    row_pre,  label_pre  = _sensor_row("#10B981", "Pressão: -- hPa")
    row_lux,  label_lux  = _sensor_row("#F59E0B", "Luminosidade: -- lux")

    for row in (row_temp, row_umi, row_pre, row_lux):
        painel_sensores.addLayout(row)

    widget_sensores = QWidget()
    widget_sensores.setLayout(painel_sensores)
    widget_sensores.setStyleSheet("background-color: #3a556f; border-radius: 10px; padding: 8px;")
    coluna_direita_layout.addWidget(widget_sensores)

    coluna_direita_widget = QWidget()
    coluna_direita_widget.setLayout(coluna_direita_layout)
    coluna_direita_widget.setFixedWidth(220)
    coluna_direita_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    grid.addWidget(coluna_direita_widget, 0, 2)

    # =========================
    # Ajuste das colunas — MANTIDO
    # =========================
    grid.setColumnStretch(0, 0)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 0)

    # =========================
    # Conectando os sinais — MANTIDO
    # =========================
    botoes['reiniciar_operacao'].clicked.connect(acoes.reiniciar_operacao)
    botoes['configuracao'].clicked.connect(acoes.abrir_configuracao)
    botoes['adicionar_nc'].clicked.connect(acoes.adicionar_nc_manual)
    botoes['acao_em_massa'].clicked.connect(acoes.abrir_dialog_insercao_massa)
    botoes['relatorios'].clicked.connect(acoes.abrir_relatorios)
    botoes['pausar_deteccao'].clicked.connect(parent_widget._alternar_pausa_detectar)
    botoes['atualizar_classe'].clicked.connect(parent_widget._atualizar_classe)
    botao_sair.clicked.connect(parent_widget._encerrar_aplicacao)

    # Retorno (assinatura preservada — dashboard_widget oculto)
    return (
        grid, botoes, camera_label,
        label_detectados, label_nao_conforme, label_totais,
        label_temp, label_umi, label_pre, label_lux,
        dashboard_widget
    )

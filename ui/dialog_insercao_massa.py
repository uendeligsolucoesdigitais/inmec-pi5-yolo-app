
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt


from config.config import DialogInsercaoMassaConfig
CFG = DialogInsercaoMassaConfig()

class InsercaoMassaDialog(QDialog):
    def __init__(self, painel_acoes):
        super().__init__(painel_acoes.main_window)
        self.painel_acoes = painel_acoes
        self.setWindowTitle(CFG.window_title)
        self.setMinimumWidth(CFG.minimum_width)

        self.setStyleSheet(CFG.dialog_stylesheet)


        layout = QVBoxLayout(self)

        # Campo com botões + e -
        self.quantidade = QSpinBox()
        self.quantidade.setMinimum(0)
        self.quantidade.setMaximum(999)
        self.quantidade.setValue(CFG.spin_default)
        self.quantidade.setAlignment(Qt.AlignCenter)
        self.quantidade.setStyleSheet(CFG.spin_stylesheet)

        linha_input = QHBoxLayout()
        btn_menos = QPushButton("-")
        btn_menos.clicked.connect(lambda: self.quantidade.stepDown())
        btn_mais = QPushButton("+")
        btn_mais.clicked.connect(lambda: self.quantidade.stepUp())
        linha_input.addWidget(btn_menos)
        linha_input.addWidget(self.quantidade)
        linha_input.addWidget(btn_mais)

        # Botões inferiores
        linha_botoes = QHBoxLayout()
        btn_cancelar = QPushButton(CFG.btn_cancelar_text)
        btn_cancelar.clicked.connect(self.reject)
        btn_inserir = QPushButton(CFG.btn_inserir_text)
        btn_inserir.clicked.connect(self.inserir_ncs)
        linha_botoes.addWidget(btn_cancelar)
        linha_botoes.addWidget(btn_inserir)

        layout.addLayout(linha_input)
        layout.addSpacing(CFG.spacing_after_input)
        layout.addLayout(linha_botoes)

    def inserir_ncs(self):
        quantidade = self.quantidade.value()
        if quantidade <= 0:
            QMessageBox.warning(self, CFG.qmb_warning_title, CFG.qmb_warning_text)
            return

        try:
            import numpy as np

            detect_thread = self.painel_acoes.main_window.content_widget.camera_worker.detect_thread
            classe_nc = detect_thread.naoConforme
            frame_falso = np.zeros((CFG.frame_false_height, CFG.frame_false_width, CFG.frame_false_channels), dtype=np.uint8)

            for i in range(quantidade):
                track_id = 90000 + i
                detect_thread.contador_naoConforme += 1
                detect_thread.contador_total += 1
                detect_thread._processar_registro_async(
                    frame_falso,
                    classe_nc,
                    track_id,
                    "Não",
                    manual=1
                )

            detect_thread.contador_nao_conforme_atualizado.emit(detect_thread.contador_naoConforme)
            detect_thread.contador_total_atualizado.emit(detect_thread.contador_total)

            msg = CFG.msg_mass_success_template.format(quantidade=quantidade)
            print(msg)
            self.painel_acoes.main_window.status_bar.showMessage(msg, CFG.status_msg_duration_ms)
            QMessageBox.information(self, CFG.qmb_info_title, msg)
            self.accept()

        except Exception as e:
            erro = CFG.msg_error_prefix_template.format(e=e)
            print(erro)
            self.painel_acoes.main_window.status_bar.showMessage(erro, CFG.status_msg_duration_ms)
            QMessageBox.critical(self, CFG.qmb_error_title, str(e))
            self.reject()

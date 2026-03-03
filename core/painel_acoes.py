from ui.dialog_insercao_massa import InsercaoMassaDialog

from PySide6.QtCore import QTimer
import time
from core.operationserial import OperationSerial
from PySide6.QtWidgets import QDialog
from config.config import PainelAcoesConfig
CFG = PainelAcoesConfig()


class PainelAcoes:
    def __init__(self, main_window):
        self.main_window = main_window

    def reiniciar_operacao(self):
        print("[🔄] Reiniciando operação...")

        # 1. Parar detecção
        if hasattr(self.main_window.content_widget, 'camera_worker'):
            self.main_window.content_widget.camera_worker.stop()
            print("[🛑] Detecção parada.")

        # 2. Gerar novo OperacaoID
        config_xml = self.main_window.configDataXml
        modulo_id = self.main_window.configData.get("ModuloId")
        novo_operacao_id = OperationSerial.generate_new_serial(modulo_id, config_xml)
        


        self.main_window.configData["OperacaoId"] = novo_operacao_id
        self.main_window.window().top_bar.atualizar_modulo_operacao(modulo_id, novo_operacao_id)
        print(f"[🆕] Novo OperacaoID: {novo_operacao_id}")


        # 3. Zerar contadores
        self.main_window.content_widget.atualizar_contador_detectados(0)
        self.main_window.content_widget.atualizar_contador_nao_conforme(0)
        self.main_window.content_widget.atualizar_contador_totais(0)
        print("[0️⃣] Contadores zerados.")

        # 4. Esperar 2 segundos e reiniciar detecção
        QTimer.singleShot(CFG.reiniciar_operacao_delay_ms, self.iniciar_novamente)

    def iniciar_novamente(self):
        if hasattr(self.main_window.content_widget, 'camera_worker'):
            self.main_window.content_widget.camera_worker.start()
            print("[▶️] Detecção reiniciada.")

    def abrir_configuracao(self):
        print("[⚙️] Acessando configurações...")

        # 1. Parar detecção e câmera
        if hasattr(self.main_window.camera_worker, 'stop'):
            self.main_window.camera_worker.stop()
            print("[🛑] Detecção e câmera paradas.")

        # 2. Zerar contadores
        self.main_window.atualizar_contador_detectados(0)
        self.main_window.atualizar_contador_nao_conforme(0)
        self.main_window.atualizar_contador_totais(0)

        # 3. Resetar rastreamento
        if hasattr(self.main_window.camera_worker, "detect_thread"):
            self.main_window.camera_worker.detect_thread.reset_tracking()
            print("[♻️] IDs de rastreamento zerados.")

        # 4. Gerar novo OperacaoID
        from core.operationserial import OperationSerial
        modulo_id = self.main_window.configData.get("ModuloId")
        config_xml = self.main_window.configDataXml
        novo_operacao_id = OperationSerial.generate_new_serial(modulo_id, config_xml)
        self.main_window.configData["OperacaoId"] = novo_operacao_id
        self.main_window.window().top_bar.atualizar_modulo_operacao(modulo_id, novo_operacao_id)
        print(f"[🆕] Novo OperacaoID: {novo_operacao_id}")

        # 5. Abrir janela de configuração
        from ui.ui_configuracao import ConfiguracaoDialog
        caminho = CFG.config_xml_path
        dialog = ConfiguracaoDialog(caminho)
        resultado = dialog.exec()

        if resultado == QDialog.Accepted:
            print("[✅] Configurações salvas. Reiniciando sistema...")
            from PySide6.QtWidgets import QApplication
            import sys, os
            QApplication.instance().quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            print("[↩️] Configuração cancelada. Reativando detecção...")
            self.main_window.camera_worker.start()

    def adicionar_nc_manual(self):
        print("[🟠] Detecção manual de NC realizada pelo usuário.")
        self.main_window.status_bar.showMessage("NC manual adicionado com sucesso.", CFG.status_msg_duration_ms)

        try:
            detect_thread = self.main_window.content_widget.camera_worker.detect_thread

            import numpy as np
            altura = CFG.manual_nc_frame_height
            largura = CFG.manual_nc_frame_width
            frame_vazio = np.zeros((altura, largura, 3), dtype=np.uint8)

            classe_nc = detect_thread.naoConforme
            track_id_manual = CFG.manual_nc_track_id  # ID fictício

            detect_thread.contador_naoConforme += 1
            detect_thread.contador_total += 1
            detect_thread.contador_nao_conforme_atualizado.emit(detect_thread.contador_naoConforme)
            detect_thread.contador_total_atualizado.emit(detect_thread.contador_total)

            detect_thread._processar_registro_async(
                frame_vazio,
                classe_nc,
                track_id_manual,
                "Não",
                manual=CFG.processar_registro_manual_flag
            )

        except Exception as e:
            print(f"[❌] Erro ao adicionar NC manualmente: {e}")


    def abrir_dialog_insercao_massa(self):
        dialog = InsercaoMassaDialog(self)
        dialog.exec()

    def pausar_detectar(self):
        if hasattr(self.main_window.content_widget, '_alternar_pausa_detectar'):
            self.main_window.content_widget._alternar_pausa_detectar()

    def abrir_relatorios(self):
        """
        Suspende tudo e abre a janela de relatórios em tela cheia.
        """
        cw = getattr(self.main_window, "content_widget", None)
        if cw and hasattr(cw, "abrir_report_viewer"):
            cw.abrir_report_viewer()
        elif cw and hasattr(cw, "mostrar_relatorios"):
            # fallback se você ainda mantiver o alias
            cw.mostrar_relatorios()

        

    def reiniciar_operacao(self):
        if hasattr(self.main_window.content_widget, "_reiniciar_aplicacao"):
            self.main_window.content_widget._reiniciar_aplicacao()


        
        

    

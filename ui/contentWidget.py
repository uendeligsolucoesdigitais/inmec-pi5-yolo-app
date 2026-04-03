from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QSizePolicy, QApplication, QDialog, QPushButton, QHBoxLayout, QStyle
from PySide6.QtCore import Qt, QTimer, QThread
from core.licence import LicenceVerifier
from core.bdlmanager import BDLManager
from ui.licenceErrorDialog import LicenceErrorDialog
from core.infratest import InfraTestManager
from PySide6.QtGui import QImage, QPixmap
from core.sensorthread import SensorWorker
from core.cameraworker import CameraWorker
from core.painel_acoes import PainelAcoes
import cv2
import os

# Importando as novas funções e classes modularizadas
from ui.layout_operational import create_operational_layout
from ui.utils import carregar_svg_branco
from core.teclas_deteccao import TeclasDeteccaoToast
from core.pedal_input import PedalWatcher
from ui.report_viewer import ReportWindow







class ContentWidget(QWidget):
    def __init__(self, status_bar, configData, configDataXml, parent=None):
        super().__init__(parent)
        self.status_bar = status_bar
        self.configData = configData
        self.configDataXml = configDataXml
        self.tester = InfraTestManager(configData, configDataXml)
        self.camera_label = None
        self.acoes = PainelAcoes(self)
        self.window().content_widget = self
        self.setStyleSheet("background-color: #2E4459;")
        self.etapas = [
            ("licenca", "Verificando licença...", self.testar_licenca),
            ("bdl", "Testando banco de dados local...", self.testar_banco_local),
            ("internet", "Testando conexão com a internet...", self.testar_internet),
            ("bdr", "Testando banco de dados remoto...", self.testar_banco_remoto),
            ("audio", "Testando dispositivo de áudio...", self.testar_audio),
            ("sensores", "Verificando sensores...", self.testar_sensores),
            ("ia", "Inicializando IA...", self.testar_ia)
        ]
        self.etapa_atual = 0
        self.layout_principal = QVBoxLayout()
        self.layout_principal.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout_principal)
        self.label_progresso = QLabel("Iniciando...")
        self.label_progresso.setStyleSheet("color: white; font-size: 16px;")
        self.label_progresso.setAlignment(Qt.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1F2F3D;
                color: white;
                border: 1px solid white;
                height: 24px;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #5dc6ca;
                width: 20px;
            }
        """)

        self._ui_last_ms = 0
        self._ui_interval_ms = 40  # ~25 fps para a UI; mude para 33 se quiser ~30 fps


        self.layout_principal.addWidget(self.label_progresso)
        self.layout_principal.addWidget(self.progress_bar, alignment=Qt.AlignCenter)
        self.deteccao_pausada = False
        if not self._verificar_status_modulo_inativo():
            QTimer.singleShot(100, self.executar_proxima_etapa)

    def resizeEvent(self, event):
        self.progress_bar.setFixedWidth(int(self.width() * 0.6))

    def executar_proxima_etapa(self):
        if self.etapa_atual < len(self.etapas):
            chave, nome, funcao = self.etapas[self.etapa_atual]
            self.label_progresso.setText(nome)
            self.status_bar.atualizar_mensagem(nome)
            resultado = funcao()
            if resultado is True:
                self._atualizar_icone_topbar(chave, "ok")
            elif resultado is False:
                self._atualizar_icone_topbar(chave, "erro")
            elif resultado is None:
                self._atualizar_icone_topbar(chave, "gray")
            progresso = int(((self.etapa_atual + 1) / len(self.etapas)) * 100)
            self.progress_bar.setValue(progresso)
            self.etapa_atual += 1
            QTimer.singleShot(500, self.executar_proxima_etapa)
        else:
            self._ativar_layout_operacional()

    def _verificar_status_modulo_inativo(self) -> bool:
        status_val = ""
        try:
            status_val = (self.configDataXml.get("Status") or "").strip().lower()
        except Exception:
            status_val = ""
        if status_val == "i":
            self._mostrar_dialog_modulo_inativo()
            return True
        return False

    def _mostrar_dialog_modulo_inativo(self):
        if getattr(self, "_dialog_inativo", None):
            return

        self._fechando_por_inatividade = False
        parent_win = self.window()
        dialog = QDialog(parent_win)
        dialog.setWindowTitle("Módulo Inativo")
        dialog.setModal(True)
        dialog.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowStaysOnTopHint
        )

        layout = QVBoxLayout()
        header = QHBoxLayout()

        icon = QLabel()
        warning_icon = dialog.style().standardIcon(QStyle.SP_MessageBoxWarning)
        icon.setPixmap(warning_icon.pixmap(48, 48))
        icon.setFixedSize(48, 48)

        texto = QLabel("Módulo inativo.\nProcure ajuda com os administradores do sistema.")
        texto.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        texto.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        header.addWidget(icon)
        header.addWidget(texto, 1)
        layout.addLayout(header)

        botao_fechar = QPushButton("Fechar")
        botao_fechar.setFixedWidth(140)
        botao_fechar.clicked.connect(self._fechar_aplicacao_inativo)

        layout.addWidget(botao_fechar, alignment=Qt.AlignCenter)
        dialog.setLayout(layout)

        dialog.setStyleSheet("""
            QDialog {
                background-color: #C62828;
                border: 4px solid #FBC02D;
            }
            QPushButton {
                background-color: #FBC02D;
                color: #000000;
                border: 2px solid #FBC02D;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFD54F;
            }
            QPushButton:pressed {
                background-color: #F9A825;
            }
        """)

        QTimer.singleShot(10000, self._fechar_aplicacao_inativo)

        self._dialog_inativo = dialog
        QTimer.singleShot(0, dialog.open)

    def _fechar_aplicacao_inativo(self):
        if getattr(self, "_fechando_por_inatividade", False):
            return
        self._fechando_por_inatividade = True
        try:
            if getattr(self, "_dialog_inativo", None):
                self._dialog_inativo.close()
        except Exception:
            pass
        try:
            self.window().close()
        except Exception:
            pass
        QApplication.quit()

    def _atualizar_icone_topbar(self, nome, status):
        main_window = self.window()
        if hasattr(main_window, "top_bar"):
            main_window.top_bar.set_status_icon(nome, status)

    def testar_licenca(self):
        return self.tester.testar_licenca()

    def testar_banco_local(self):
        return self.tester.testar_banco_local()

    def testar_internet(self):
        return self.tester.testar_internet()

    def testar_banco_remoto(self):
        return self.tester.testar_banco_remoto()


    def testar_audio(self):

        return self.tester.testar_audio()

    def testar_sensores(self):
        return self.tester.testar_sensores()

    def testar_ia(self):
        return self.tester.testar_ia()

    def _atualizar_camera(self, frame_bgr):
        from PySide6.QtCore import QTime
        now = QTime.currentTime().msecsSinceStartOfDay()
        if now - self._ui_last_ms < self._ui_interval_ms:
            return
        self._ui_last_ms = now

        if not self.camera_label or frame_bgr is None:
            return

        # ---- BGR -> QImage sem cvtColor (mais leve)
        h, w, ch = frame_bgr.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_bgr.data, w, h, bytes_per_line, QImage.Format_BGR888)

        target_w = self.camera_label.width()
        target_h = self.camera_label.height()

        # Nenhuma operação de redimensionamento aqui.
        self.camera_label.setPixmap(QPixmap.fromImage(qimg))





    def _atualizar_valores_sensores(self, dados):
        self.label_temp.setText(f"Temperatura: {dados['temperatura']} °C")
        self.label_umi.setText(f"Umidade: {dados['umidade']} %")
        self.label_pre.setText(f"Pressão: {dados['pressao']} hPa")
        self.label_lux.setText(f"Luminosidade: {dados['luminosidade']} lux")

    def closeEvent(self, event):
        if hasattr(self, 'sensor_worker') and self.sensor_worker:
            self.sensor_worker.stop()
            self.sensor_thread.quit()
            self.sensor_thread.wait()
            self.sensor_worker = None
            self.sensor_thread = None
        super().closeEvent(event)

    def _encerrar_camera_thread(self):
        if self.camera_thread and self.camera_thread.isRunning():
            print("[🧵] Finalizando thread da câmera com segurança...")
            self.camera_thread.quit()
            self.camera_thread.wait()
            print("[✅] Thread da câmera finalizada.")
        self.camera_thread = None
        self.camera_worker = None
        self.deteccao_pausada = False
        self.close()

    def finalizar_camera(self):
        if self.camera_worker:
            print("[🛑] Encerrando câmera...")
            self.camera_worker.stop()
        if self.camera_label:
            self.camera_label.clear()
            self.camera_label.setText("Desligando a câmera. Aguarde!")
            self.camera_label.setStyleSheet(
                "color: white; font-size: 16px; background-color: black; border: 2px solid white;"
            )

    def _encerrar_aplicacao(self):
        print("[⛔] Encerrando sistema...")
        self.encerrar_todos_os_threads()

    def encerrar_todos_os_threads(self):
        if hasattr(self, 'sensor_worker') and self.sensor_worker:
            self.sensor_worker.stop()
            self.sensor_thread.quit()
            self.sensor_thread.wait()
            self.sensor_worker = None
            self.sensor_thread = None

        # parar pedal (se ativo)
        if hasattr(self, "_pedal") and self._pedal:
            try:
                self._pedal.stop()
            except Exception:
                pass
            self._pedal = None

        self.finalizar_camera()
        QTimer.singleShot(300, self._encerrar_camera_thread_final)

    def suspender_todos_os_threads(self):
        """
        Suspende (para) todas as threads e libera recursos,
        sem finalizar/fechar a aplicação.
        """
        # Sensores
        if hasattr(self, 'sensor_worker') and self.sensor_worker:
            try:
                self.sensor_worker.stop()
            except Exception:
                pass
            if hasattr(self, 'sensor_thread') and self.sensor_thread:
                self.sensor_thread.quit()
                self.sensor_thread.wait()
            self.sensor_worker = None
            self.sensor_thread = None

        # Pedal
        if hasattr(self, "_pedal") and self._pedal:
            try:
                self._pedal.stop()
            except Exception:
                pass
            self._pedal = None

        # Câmera / YOLO
        if hasattr(self, 'camera_worker') and self.camera_worker:
            try:
                self.camera_worker.stop()
            except Exception:
                pass
            self.camera_worker = None

        self.deteccao_pausada = False
    

    def atualizar_contador_detectados(self, total):
        self.label_detectados.setText(f"DETECTADOS: {total}")

    def atualizar_contador_nao_conforme(self, total):
        self.label_nao_conforme.setText(f"NÃO CONFORME: {total}")

    def atualizar_contador_totais(self, total):
        self.label_totais.setText(f"TOTAIS: {total}")

    def _encerrar_camera_thread_final(self):
        print("[🧵] Finalizando threads internas da câmera com segurança...")
        if self.camera_worker:
            self.camera_worker.shutdown()
            self.camera_worker = None
            self.deteccao_pausada = False
        self.close()
        QApplication.quit()

    def _ativar_layout_operacional(self):
            while self.layout_principal.count():
                item = self.layout_principal.takeAt(0)
                if item:
                    if item.widget():
                        item.widget().deleteLater()
                    elif item.layout():
                        while item.layout().count():
                            subitem = item.layout().takeAt(0)
                            if subitem.widget():
                                subitem.widget().deleteLater()
                        item.layout().deleteLater()

            grid, self.botoes, self.camera_label, self.label_detectados, self.label_nao_conforme, self.label_totais, self.label_temp, self.label_umi, self.label_pre, self.label_lux, self.dashboard_widget  = create_operational_layout(self, self.acoes)
            self.layout_principal.addLayout(grid)
            self.status_bar.atualizar_mensagem("Sistema pronto.")

            _model_path = self._resolver_model_path()
            if not _model_path:
                return
            self.camera_worker = CameraWorker(model_path=_model_path)
            self.camera_worker.frame_ready.connect(self._atualizar_camera)
            self.camera_worker.detect_thread.log_gerado.connect(self.atualizar_status_bar)
            self.camera_worker.detect_thread.contador_atualizado.connect(self.atualizar_contador_detectados)
            self.camera_worker.detect_thread.contador_nao_conforme_atualizado.connect(self.atualizar_contador_nao_conforme)
            self.camera_worker.detect_thread.contador_total_atualizado.connect(self.atualizar_contador_totais)
            self.camera_worker.sensores_atualizados.connect(self._atualizar_valores_sensores)
            self.camera_worker.start()

            self.sensor_worker = SensorWorker()
            self.sensor_thread = QThread()
            self.sensor_worker.moveToThread(self.sensor_thread)
            self.sensor_worker.sensores_atualizados.connect(self._atualizar_valores_sensores)

            # Captura da tecla ESPAÇO + toast SVG (módulo externo no core)
            self._teclas_helper = TeclasDeteccaoToast(
                parent=self,
                dashboard_widget=self.dashboard_widget,
                detect_thread_provider=lambda: self.camera_worker.detect_thread if self.camera_worker else None,
                video_widget=self.camera_label  # <<< NOVO: sobrepor no vídeo
            )
            self._teclas_helper.instalar()


            self.sensor_thread.started.connect(self.sensor_worker.run)
            self.sensor_thread.start()

            # Pedal (GPIO) :
            self._pedal = PedalWatcher(
                parent=self,
                dashboard_widget=self.dashboard_widget,
                detect_thread_provider=lambda: self.camera_worker.detect_thread if self.camera_worker else None,
                video_widget=self.camera_label,
                debounce_ms=300
            )
            self._pedal.start()





    def _alternar_pausa_detectar(self):
        if not self.camera_worker:
            print("[⚠️] Nenhuma câmera ativa.")
            return
        if self.deteccao_pausada:
            self.camera_worker.resume_detection()
            self.deteccao_pausada = False
            self.status_bar.showMessage("🧠 Detecção retomada.")
            self._atualizar_botao_pausa("Pausar Detecção")
        else:
            self.camera_worker.pause_detection()
            self.deteccao_pausada = True
            self.status_bar.showMessage("⏸️ Detecção pausada.")
            self._atualizar_botao_pausa("Voltar a Detectar")

    def _atualizar_botao_pausa(self, texto):
        botao = self.botoes.get("pausar_deteccao")
        if botao:
            botao.setText(f"{texto}")
            if "Voltar" in texto:
                icone = carregar_svg_branco("img/svg/play.svg", tamanho=40)
            else:
                icone = carregar_svg_branco("img/svg/pausar_deteccao.svg", tamanho=40)
            botao.setIcon(icone)
            botao.repaint()

    def atualizar_status_bar(self, mensagem):
        self.status_bar.showMessage(mensagem, 10000)

    def _atualizar_luminosidade(self, valor):
        if hasattr(self, 'label_lux'):
            self.label_lux.setText(f"🔆 Luminosidade: {valor:.2f} %")

    def mostrar_relatorios(self):
        """
        Wrapper público para abrir a janela de relatórios em tela cheia.
        Mantém compatibilidade com chamadas existentes.
        """
        self.abrir_report_viewer()

    def abrir_report_viewer(self):
        print("[📊] Abrindo Report Viewer em tela cheia...")
        self.suspender_todos_os_threads()

        # usa a classe já importada no topo
        app = QApplication.instance()
        self._report_win = ReportWindow()
        self._report_win.showFullScreen()

        main_win = self.window()
        if main_win:
            main_win.close()
        app.setProperty("report_window", self._report_win)



    def _reiniciar_aplicacao(self):
        import os, sys
        from PySide6.QtWidgets import QApplication
        print("[🔁] Reiniciando aplicação...")
        
        # 1. Chamar a função que encerra todos os threads e libera recursos
        self.encerrar_todos_os_threads()

        # 2. Fechar a janela e reiniciar o aplicativo
        self.window().close()
        QApplication.quit()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def _resolver_model_path(self):
        """Resolve o caminho do modelo seguindo a ordem BDR → BDL → config XML."""
        import os
        from core.bdlmanager import BDLManager
        from core.bdrmanager import BDRManager
        from core.configmanager import ConfigManager

        model = None

        # 1) BDR
        try:
            cfg = ConfigManager()
            modulo_id = cfg.get("ModuloId")
            dados_bdr = BDRManager().read("Config", f"ModuloId='{modulo_id}'")
            if dados_bdr:
                model = (dados_bdr[0].get("Model") or "").strip() or None
        except Exception:
            pass

        # 2) BDL
        if not model:
            try:
                config = BDLManager().get_config_data()
                model = (config.get("Model") or "").strip() or None if config else None
            except Exception:
                pass

        # 3) config XML
        if not model:
            try:
                model = (ConfigManager().get("Model") or "").strip() or None
            except Exception:
                pass

        if model:
            path = os.path.join("datasets", model) if not os.path.sep in model else model
            if os.path.exists(path):
                print(f"[🤖] Modelo carregado: {path}")
                return path
            self._erro_modelo(path)
            return None

        self._erro_modelo(None)
        return None

    def _erro_modelo(self, path):
        from PySide6.QtWidgets import QMessageBox, QApplication
        if path:
            msg = f"O arquivo de modelo não foi encontrado:\n{path}\n\nO sistema não pode ser iniciado."
        else:
            msg = "Nenhum modelo (.pt) está configurado no BDR, BDL ou config.xml.\n\nO sistema não pode ser iniciado."
        print(f"[❌] {msg}")
        box = QMessageBox()
        box.setWindowTitle("Erro de Modelo")
        box.setText(msg)
        box.setIcon(QMessageBox.Critical)
        box.exec()
        QApplication.quit()

    def _atualizar_classe(self):
        print("[🔁] Atualizando classe de detecção...")
        if self.camera_worker:
            self.camera_worker.pause_detection()
        self.atualizar_contador_detectados(0)
        self.atualizar_contador_nao_conforme(0)
        self.atualizar_contador_totais(0)
        if self.camera_worker:
            self.camera_worker.stop()
            self.camera_worker = None
        from core.bdlmanager import BDLManager
        from core.bdrmanager import BDRManager
        from core.operationserial import OperationSerial
        from core.configmanager import ConfigManager
        classe = None

        # 1) tenta BDR
        try:
            cfg = ConfigManager()
            modulo_id = cfg.get("ModuloId")
            dados_bdr = BDRManager().read("Config", f"ModuloId='{modulo_id}'")
            if dados_bdr:
                classe_bdr = (dados_bdr[0].get("Classes") or "").strip()
                if classe_bdr:
                    classe = classe_bdr
                    cfg.set("Classes", classe_bdr)
                    self._update_bdl_classes(modulo_id, classe_bdr, cfg)
            else:
                self.status_bar.showMessage("BDR indisponível. Continuando com BDL/XML.", 7000)
        except Exception:
            self.status_bar.showMessage("BDR indisponível. Continuando com BDL/XML.", 7000)
            pass

        # 2) fallback BDL
        if not classe:
            try:
                config = BDLManager().get_config_data()
                classe_bdl = (config.get("Classes") or "").strip() if config else ""
                if classe_bdl:
                    classe = classe_bdl
            except Exception:
                classe = None

        # 3) fallback XML
        if not classe:
            try:
                classe_xml = (ConfigManager().get("Classes") or "").strip()
                if classe_xml:
                    classe = classe_xml
            except Exception:
                classe = None

        self.conforme = (classe or "").strip()
        if not self.conforme:
            from PySide6.QtWidgets import QMessageBox, QApplication
            msg = QMessageBox()
            msg.setWindowTitle("Erro crítico")
            msg.setText("❌ Nenhuma classe configurada no banco de dados local. Configure a classe antes de iniciar o sistema.")
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            QApplication.quit()
            return
        # 2) Atualiza BDL e XML com a classe escolhida
        try:
            cfg = ConfigManager()
            cfg.set("Classes", self.conforme)
            modulo_id = cfg.get("ModuloId")
            if modulo_id:
                self._update_bdl_classes(modulo_id, self.conforme, cfg)
        except Exception:
            pass
        self.naoConforme = f"{self.conforme}_nc"
        print(f"[⚙️] Classe conforme: '{self.conforme}' | naoConforme: '{self.naoConforme}'")

        # Avisar e reiniciar com seguranÃ§a (apÃ³s confirmaÃ§Ã£o)
        self.status_bar.showMessage("Aplicação será reiniciada com segurança.", 5000)
        try:
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Reinício necessário")
            msg.setText(f"A aplicação será reiniciada para carregar a classe: {self.conforme}")
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #FFFFFF;
                    color: #000000;
                    border: 1px solid #CCCCCC;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #F2F2F2;
                }
                QPushButton:pressed {
                    background-color: #E6E6E6;
                }
            """)
            msg.exec()
        except Exception:
            pass

        # 3) Desativar cÃ¢meras / YOLO com seguranÃ§a
        try:
            if self.camera_worker:
                self.camera_worker.shutdown()
        except Exception:
            pass

        # 4) Reiniciar a aplicaÃ§Ã£o
        self._reiniciar_aplicacao()
        return
        
    def _update_bdl_classes(self, modulo_id: str, classe: str, cfg):
        import os
        import sqlite3
        try:
            db_path = os.path.join(
                str(cfg.get("db_path_local") or ""),
                str(cfg.get("db_name_local") or ""),
            )
            if not db_path:
                return
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            cur.execute("PRAGMA table_info(Config)")
            existing = {row[1] for row in cur.fetchall()}
            if "Classes" not in existing:
                cur.execute("ALTER TABLE Config ADD COLUMN Classes TEXT")

            cur.execute("SELECT 1 FROM Config WHERE ModuloId = ? LIMIT 1", (modulo_id,))
            exists = cur.fetchone() is not None
            if exists:
                cur.execute("UPDATE Config SET Classes = ? WHERE ModuloId = ?", (classe, modulo_id))
            else:
                cur.execute("INSERT INTO Config (ModuloId, Classes) VALUES (?, ?)", (modulo_id, classe))

            conn.commit()
            conn.close()
        except Exception:
            pass


    

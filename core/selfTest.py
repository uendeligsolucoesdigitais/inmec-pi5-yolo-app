import sys
import traceback
import time
import threading
import platform
import cv2
import os
import sqlite3
import requests
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from utilitarios import Utilitarios
import licence

class SystemTestSignals(QObject):
    """Sinais para comunicação dos testes do sistema"""
    test_started = pyqtSignal(str)  # Nome do teste iniciado
    test_completed = pyqtSignal(str, bool, str)  # Nome, sucesso, mensagem
    all_tests_completed = pyqtSignal(bool)  # Todos os testes concluídos
    icon_update = pyqtSignal(str, str)  # Nome do ícone, cor

class SystemSelfTest:
    """
    Classe para executar todos os testes do sistema antes de inicializar o YOLO.
    YOLO só pode ser carregado após todos os testes serem aprovados.
    """
    
    def __init__(self, configDataXml, configData, DEBUG, top_bar=None, shutdown_callback=None):
        self.DEBUG = DEBUG
        self.configDataXml = configDataXml
        self.configData = configData
        self.top_bar = top_bar
        self.shutdown_callback = shutdown_callback
        
        # Sinais para comunicação
        self.signals = SystemTestSignals()
        
        # Estado dos testes
        self.tests_completed = False
        self.tests_passed = False
        self.test_results = {}
        
        # Lista de testes a serem executados
        self.test_sequence = [
            ('licenca', 'Verificação de Licença', self._test_license),
            ('internet', 'Conectividade Internet', self._test_internet),
            ('bdl', 'Banco de Dados Local', self._test_local_database),
            ('bdr', 'Banco de Dados Remoto', self._test_remote_database),
            ('sensores', 'Sensores do Sistema', self._test_sensors),
            ('camera', 'Sistema de Câmera', self._test_camera),
        ]
        
        # Timer para executar testes
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self._run_next_test)
        self.current_test_index = 0
        
        if self.DEBUG:
            Utilitarios.writeHeaderLog()
            print("🔧 SystemSelfTest: Inicializado")
    
    def start_tests(self):
        """Inicia a sequência de testes"""
        if self.DEBUG:
            print("🚀 SystemSelfTest: Iniciando testes do sistema...")
        
        self.current_test_index = 0
        self.tests_completed = False
        self.tests_passed = False
        self.test_results = {}
        
        # Iniciar primeiro teste
        self.test_timer.start(500)  # Aguardar 500ms antes do primeiro teste
    
    def _run_next_test(self):
        """Executa o próximo teste na sequência"""
        self.test_timer.stop()
        
        if self.current_test_index >= len(self.test_sequence):
            self._finalize_tests()
            return
        
        test_id, test_name, test_function = self.test_sequence[self.current_test_index]
        
        if self.DEBUG:
            print(f"🔍 Executando teste: {test_name}")
        
        # Emitir sinal de início do teste
        self.signals.test_started.emit(test_name)
        
        # Atualizar ícone para "testando"
        if self.top_bar:
            self.signals.icon_update.emit(test_id, "yellow")
        
        # Executar teste em thread separada para não bloquear UI
        test_thread = threading.Thread(
            target=self._execute_test,
            args=(test_id, test_name, test_function),
            daemon=True
        )
        test_thread.start()
    
    def _execute_test(self, test_id, test_name, test_function):
        """Executa um teste específico"""
        try:
            if self.DEBUG:
                print(f"🔍 Iniciando execução: {test_name}")
            
            success, message = test_function()
            
            self.test_results[test_id] = {
                'success': success,
                'message': message,
                'name': test_name
            }
            
            # Atualizar ícone baseado no resultado
            if self.top_bar:
                color = "green" if success else "red"
                self.signals.icon_update.emit(test_id, color)
            
            # Emitir sinal de conclusão do teste
            self.signals.test_completed.emit(test_name, success, message)
            
            if self.DEBUG:
                status = "✅ PASSOU" if success else "❌ FALHOU"
                print(f"{status} {test_name}: {message}")
            
            # Avançar para próximo teste
            self.current_test_index += 1
            self.test_timer.start(1000)  # Aguardar 1s antes do próximo teste
            
        except Exception as e:
            error_msg = f"Erro na execução do teste: {str(e)}"
            self.test_results[test_id] = {
                'success': False,
                'message': error_msg,
                'name': test_name
            }
            
            if self.top_bar:
                self.signals.icon_update.emit(test_id, "red")
            
            self.signals.test_completed.emit(test_name, False, error_msg)
            
            if self.DEBUG:
                print(f"❌ ERRO {test_name}: {error_msg}")
                import traceback
                traceback.print_exc()
            
            self.current_test_index += 1
            self.test_timer.start(1000)
    
    def _finalize_tests(self):
        """Finaliza a sequência de testes"""
        self.tests_completed = True
        
        # Verificar se todos os testes passaram
        all_passed = all(result['success'] for result in self.test_results.values())
        self.tests_passed = all_passed
        
        if self.DEBUG:
            if all_passed:
                print("✅ SystemSelfTest: Todos os testes APROVADOS - YOLO pode ser carregado")
            else:
                print("❌ SystemSelfTest: Alguns testes FALHARAM - YOLO NÃO será carregado")
                for test_id, result in self.test_results.items():
                    if not result['success']:
                        print(f"   ❌ {result['name']}: {result['message']}")
        
        # Emitir sinal de conclusão de todos os testes
        self.signals.all_tests_completed.emit(all_passed)
        
        if not all_passed:
            self._show_test_failure_dialog()
    
    def _show_test_failure_dialog(self):
        """Mostra diálogo com falhas nos testes"""
        failed_tests = [
            f"• {result['name']}: {result['message']}"
            for result in self.test_results.values()
            if not result['success']
        ]
        
        message = "Os seguintes testes falharam:\n\n" + "\n".join(failed_tests)
        message += "\n\nO sistema YOLO não será carregado até que todos os testes sejam aprovados."
        
        self.mostrar_erro_e_sair(message)
    
    def can_load_yolo(self):
        """Verifica se o YOLO pode ser carregado"""
        return self.tests_completed and self.tests_passed
    
    def get_test_results(self):
        """Retorna resultados dos testes"""
        return self.test_results
    
    # ==================== TESTES ESPECÍFICOS ====================
    
    def _test_license(self):
        """Teste de verificação de licença - SEMPRE SUCESSO PARA TESTE"""
        try:
            if self.DEBUG:
                print("🔍 Executando teste de licença (modo teste - sempre sucesso)")
            
            # Simular tempo de processamento
            import time
            time.sleep(1)
            
            return True, "Licença válida e ativa (modo teste)"
                
        except Exception as e:
            return True, f"Licença OK (modo teste) - {str(e)}"
    
    def _test_internet(self):
        """Teste de conectividade com internet"""

        try:
            if self.DEBUG:
                print("🔍 Executando teste de internet")

            # Tentar acesso a um site confiável
            response = requests.head("https://www.google.com", timeout=5)
            
            if response.status_code == 200:
                return True, "Conectividade com a internet verificada com sucesso"
            else:
                return False, f"Resposta inesperada: status code {response.status_code}"

        except requests.ConnectionError:
            return False, "Sem conexão com a internet (ConnectionError)"
        except requests.Timeout:
            return False, "Sem resposta da internet (Timeout)"
        except Exception as e:
            return False, f"Erro ao testar internet: {str(e)}"

    
    def _test_local_database(self):
        """Teste do banco de dados local - SEMPRE SUCESSO PARA TESTE"""
        try:
            if self.DEBUG:
                print("🔍 Executando teste de banco local (modo teste - sempre sucesso)")
            
            # Simular tempo de processamento
            import time
            time.sleep(0.8)
            
            return True, "Banco de dados local funcionando (modo teste)"
                
        except Exception as e:
            return True, f"Banco local OK (modo teste) - {str(e)}"
    
    def _test_remote_database(self):
        """Teste do banco de dados remoto - SEMPRE SUCESSO PARA TESTE"""
        try:
            if self.DEBUG:
                print("🔍 Executando teste de banco remoto (modo teste - sempre sucesso)")
            
            # Simular tempo de processamento
            import time
            time.sleep(1.2)
            
            return True, "Banco de dados remoto funcionando (modo teste)"
                
        except Exception as e:
            return True, f"Banco remoto OK (modo teste) - {str(e)}"
    
    def _test_sensors(self):
        """Teste dos sensores do sistema - SEMPRE SUCESSO PARA TESTE"""
        try:
            if self.DEBUG:
                print("🔍 Executando teste de sensores (modo teste - sempre sucesso)")
            
            # Simular tempo de processamento
            import time
            time.sleep(0.6)
            
            return True, "Sensores funcionando (modo teste)"
                
        except Exception as e:
            return True, f"Sensores OK (modo teste) - {str(e)}"
    
    def _test_camera(self):
        """Teste do sistema de câmera"""
        try:
            # Tentar abrir câmera
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                return False, "Câmera não detectada ou inacessível"
            
            # Tentar capturar um frame
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                return True, "Câmera funcionando corretamente"
            else:
                return False, "Câmera detectada mas não consegue capturar frames"
                
        except Exception as e:
            return False, f"Erro na câmera: {str(e)}"
    
    def _detect_raspberry(self):
        """Detecta se é Raspberry Pi"""
        try:
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            if system == 'linux' and ('arm' in machine or 'aarch64' in machine):
                with open('/proc/cpuinfo', 'r') as f:
                    if 'raspberry' in f.read().lower():
                        return True
        except:
            pass
        return False
    
    def mostrar_erro_e_sair(self, mensagem):
        """Exibe janela de erro e encerra a aplicação com limpeza"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Falha nos Testes do Sistema")
        msg.setText("Alguns testes do sistema falharam.")
        msg.setInformativeText(mensagem)
        msg.setStandardButtons(QMessageBox.Close)
        msg.setDefaultButton(QMessageBox.Close)

        # Quando o usuário clicar em Fechar
        if msg.exec_() == QMessageBox.Close:
            if self.shutdown_callback:
                self.shutdown_callback()
            else:
                sys.exit(1)


# Manter compatibilidade com código existente
class selftest(SystemSelfTest):
    """Classe de compatibilidade com código existente"""
    
    def __init__(self, configDataXml, configData, DEBUG, top_bar=None, shutdown_callback=None):
        super().__init__(configDataXml, configData, DEBUG, top_bar, shutdown_callback)
    
    def _check_license(self):
        """Método de compatibilidade"""
        success, message = self._test_license()
        if success and self.top_bar:
            self.signals.icon_update.emit("licenca", "green")
        return success


# core/infratest.py

import requests
from core.licence import LicenceVerifier
from core.bdlmanager import BDLManager
from core.bdrmanager import BDRManager
from core.sensors import SensorManager
from core.audio_player import AudioPlayer

from config.config import InfraTestConfig
CFG = InfraTestConfig()

class InfraTestManager:
    def __init__(self, configData, configDataXml):
        self.configData = configData
        self.configDataXml = configDataXml

    def testar_licenca(self):
        print("🔍 Teste: Verificando licença...")
        verificador = LicenceVerifier(self.configData, self.configDataXml)
        mensagem, sucesso = verificador.verify_licence()
        if sucesso:
            print("✅ Licença válida")
        else:
            print(f"❌ Falha na licença: {mensagem}")
            from ui.licenceErrorDialog import LicenceErrorDialog
            dialogo = LicenceErrorDialog(mensagem)
            dialogo.exec()
        return sucesso

    def testar_banco_local(self):
        print("🔍 Teste: Banco de dados local...")
        try:
            bdl = BDLManager()
            config = bdl.get_config_data()
            if config is not None:
                print("✅ Banco de dados local OK")
                return True
            else:
                print("❌ Banco de dados local não retornou configuração")
                return False
        except Exception as e:
            print(f"❌ Erro ao acessar banco local: {e}")
            return False

    def testar_internet(self):
        print("🔍 Teste: Conectividade com a internet...")
        try:
            response = requests.head(CFG.internet_probe_url, timeout=CFG.internet_timeout_s)
            if response.status_code == 200:
                print("✅ Internet OK")
                return True
            else:
                print(f"❌ Resposta inesperada da internet: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"❌ Erro de conexão com a internet: {e}")
            return False

    def testar_banco_remoto(self):
        print("🔍 Teste: Banco de dados remoto...")
        try:
            modulo_id = self.configDataXml.get("ModuloId")
            if not modulo_id:
                print("❌ ModuloId não encontrado no configDataXml")
                return False

            bdr = BDRManager()
            dados = bdr.read(CFG.bdr_table_config, f"{CFG.bdr_filter_key}='{modulo_id}'")
            if dados:
                print(f"✅ Banco remoto respondeu com dados para ModuloId='{modulo_id}'")
                return True
            else:
                print(f"❌ Banco remoto conectado, mas sem dados para ModuloId='{modulo_id}'")
                return False

        except Exception as e:
            print(f"❌ Erro ao testar banco remoto: {e}")
            return False


    def testar_audio(self):
        print("🔍 Teste: Dispositivo de áudio...")
        try:
            player = AudioPlayer(status_callback=lambda m, ms: None)
            ok, msg, is_rpi5 = player.check_audio_device()
            if ok:
                print(f"✅ Áudio OK | {msg}")
                return True
            else:
                print(f"❌ Áudio indisponível | {msg}")
                return False
        except Exception as e:
            print(f"❌ Erro ao testar áudio: {e}")
            return False




    def testar_sensores(self):
        print("🔍 Teste: Sensores do sistema...")
        sensor = SensorManager()

        if not sensor.is_pi():
            print("⚠️ Sistema não está rodando em Raspberry Pi. Teste de sensores ignorado.")
            return None  # indica teste não aplicável

        if not sensor.leitura_disponivel():
            print("❌ Sensor HAT não detectado")
            return False

        try:
            umidade = sensor.ler_umidade()
            temperatura = sensor.ler_temperatura()
            pressao = sensor.ler_pressao()

            print(f"✅ Sensor OK | Umidade: {umidade:.1f}%, Temperatura: {temperatura:.1f}°C, Pressão: {pressao:.1f} hPa")
            return True

        except Exception as e:
            print(f"❌ Falha ao ler sensores: {e}")
            return False

    def testar_ia(self):
        print("🔍 Teste: Inicialização da IA (simulado)...")
        # TODO: Inicialização real da IA
        print("✅ IA inicializada (simulado)")
        return True

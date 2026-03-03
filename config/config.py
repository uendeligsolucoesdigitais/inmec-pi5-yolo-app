
"""
config/config.py

Arquivo único com TODAS as configurações do projeto, organizadas por classes.
⚠️ Somente valores/literais. Nenhuma lógica de negócio aqui.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple


# ======================================================
# Configurações específicas de detect_thread_multiclass
# ======================================================
@dataclass
class DetectThreadConfig:
    # Limites de threads para bibliotecas numéricas
    omp_num_threads: int = 1
    openblas_num_threads: int = 1
    mkl_num_threads: int = 1
    numexpr_num_threads: int = 1

    # OpenCV
    opencv_num_threads: int = 1
    opencv_use_opencl: bool = False

    # PyTorch
    torch_num_threads: int = 1
    torch_num_interop_threads: int = 1

    # Espaço para parâmetros futuros específicos da detecção
    extras: Dict[str, Any] = field(default_factory=dict)


# Mantemos alias para compatibilidade de imports antigos
class DetectionConfig(DetectThreadConfig):
    """Alias compatível para `from config.config import DetectionConfig`."""
    pass


# ======================================================
# Configurações específicas de cameraworker.py
# ======================================================
@dataclass
class CameraWorkerConfig:
    # Parâmetros de alto nível
    cam_id: int = 0
    model_path: str = "datasets/yolov8n.pt"

    # OpenCV - performance
    cv2_num_threads: int = 1
    cv2_use_opencl: bool = False

    # Backends de captura (preenchidos no __post_init__ com constantes do cv2)
    capture_backends: Tuple[int, ...] = field(default_factory=tuple)

    # Propriedades de captura
    frame_width: int = 640
    frame_height: int = 480
    fps_target: int = 15
    dshow_buffersize: int = 1
    try_mjpg: bool = True

    # Fluxo de captura
    warmup_frames: int = 3
    backlog_grabs: int = 2
    fail_sleep_s: float = 0.005

    # Startup: aguardar primeiro frame
    start_wait_timeout_s: float = 5.0
    start_wait_poll_s: float = 0.1

    def __post_init__(self):
        # Apenas definição de dados com fallback seguro.
        try:
            import cv2
            object.__setattr__(self, "capture_backends", (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY))
        except Exception:
            object.__setattr__(self, "capture_backends", (0,))


# Placeholder genérico para módulos futuros
@dataclass
class FutureModuleConfig:
    extras: Dict[str, Any] = field(default_factory=dict)




# ======================================================
# Configurações específicas de painel_acoes.py
# ======================================================
@dataclass
class PainelAcoesConfig:
    # Atraso antes de reiniciar a detecção (ms)
    reiniciar_operacao_delay_ms: int = 2000

    # Caminho do XML de configuração
    config_xml_path: str = "./config/config.xml"

    # Duração padrão das mensagens em status bar (ms)
    status_msg_duration_ms: int = 5000

    # Parâmetros do quadro sintético para NC manual
    manual_nc_frame_height: int = 480
    manual_nc_frame_width: int = 640

    # Track ID fictício para eventos manuais
    manual_nc_track_id: int = 99999

    # Flag "manual" para registro
    processar_registro_manual_flag: int = 1



# ======================================================
# Configurações específicas de bdlmanager.py
# ======================================================
@dataclass
class BDLManagerConfig:
    # Chaves usadas pelo ConfigManager
    key_db_path_local: str = "db_path_local"
    key_db_name_local: str = "db_name_local"
    key_modulo_id: str = "ModuloId"

    # Nome da tabela de configuração no BDL
    table_config: str = "Config"

    # Leitura
    read_default_filter: str = "1=1"

    # Escrita
    write_cmd_delimiter: str = ";"

    # LocalDatabaseActions
    localdb_debug_default: bool = False



# ======================================================
# Configurações específicas de bdrmanager.py
# ======================================================
@dataclass
class BDRManagerConfig:
    # Chaves lidas do ConfigManager
    key_host_name: str = "host_name"
    key_dbport: str = "dbport"
    key_user_name: str = "user_name"
    key_user_password: str = "user_password"
    key_db_name: str = "db_name"

    # Padrões de leitura/escrita
    read_default_filter: str = "1=1"
    write_cmd_delimiter: str = ";"



# ======================================================
# Configurações específicas de configmanager.py
# ======================================================
@dataclass
class ConfigManagerConfig:
    # Caminho padrão do XML
    default_xml_path: str = "config/config.xml"

    # Tag raiz onde moram as chaves de configuração
    xml_root_tag: str = "config"

    # Codificação usada ao salvar o XML
    xml_encoding: str = "utf-8"

    # Padrões a garantir no XML (valores default)
    default_overlay: dict = field(default_factory=lambda: {
        "DETECTION_OVERLAY_ENABLED": "1",
        "DETECTION_OVERLAY_MS": "2000",
    })

    # Chaves que devem ser sincronizadas com BDR/BDL
    sync_keys: tuple = (
        "SetTeste",
        "SetDebug",
        "BaseLDR",
        "BaseHR",
        "BaseUmidade",
        "BaseTemperatura",
        "BaseGyro",
        "BaseIluminacao",
        "BaseCameras",
        "Versao",
        "LinePosition",
        "FAZER_TESTE",
        "MODO",
        "verificar_dependencias",
        "db_path_local",
        "db_name_local",
        "Classes",
        "Status",
    )

    # Controle de tentativas de acesso ao BDR
    tentativas_key: str = "TentativasDeAcessoInternet"
    bdr_retry_count: int = 3
    bdr_retry_delay_s: float = 1.0

# ======================================================
# Configurações específicas para core/infratest.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class InfraTestConfig:
    # Teste de internet
    internet_probe_url: str = "https://www.google.com"
    internet_timeout_s: int = 5  # segundos

    # Banco de Dados Remoto (BDR)
    bdr_table_config: str = "Config"
    bdr_filter_key: str = "ModuloId"

__all__ = [
    "DetectThreadConfig",
    "DetectionConfig",      # alias de compatibilidade
    "CameraWorkerConfig",
    "FutureModuleConfig",
 "PainelAcoesConfig", "BDLManagerConfig", "BDRManagerConfig", "ConfigManagerConfig",
        "InfraTestConfig",
]

# ======================================================
# Configurações para initializer.py (SystemInitializer)
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass(frozen=True)
class InitializerConfig:
    required_files: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("bdinMEC.db", "data"),
("bdl.svg", "img/svg"),
("bdr.svg", "img/svg"),
("best.pt", "datasets"),
("camera.svg", "img/svg"),
("cameraManager.py", "modules"),
("config.xml", "config"),
("db", "data"),
("delete.svg", "img/svg"),
("deteccao.svg", "img/svg"),
("erro.svg", "img/svg"),
("favicon.ico", "img"),
("favicon.png", "img"),
("ia.svg", "img/svg"),
("internet.svg", "img/svg"),
("janelaPrincipal.py", ""),
("licenca.svg", "img/svg"),
("logo.png", "img"),
("main.py", ""),
("manual.svg", "img/svg"),
("ok.svg", "img/svg"),
("operacao.png", "img"),
("problema.svg", "img/svg"),
("sair.svg", "img/svg"),
("selfTest.py", "core"),
("sensores.svg", "img/svg"),
("sincronizando.svg", "img/svg"),
("splash.png", "img"),
("topBar.py", "ui"),
("yolov8m-seg.pt", "datasets"),
("yolov8n-seg.pt", "datasets"),
    ])

    # Textos de UI (iguais aos usados hoje)
    error_title: str = "Erro de Arquivos"
    error_header: str = "Os seguintes arquivos estão ausentes:\n\n"
    error_footer: str = "\n\nO sistema não pode ser iniciado."

# ======================================================
# Configurações para licence.py (LicenceVerifier)
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class LicenceConfig:
    lic_file: str = 'lic.xml'
    key_file: str = 'key.key'
    conf_file: str = 'config.xml'
    debug_default: bool = True

    max_offline_attempts: int = 3

    internet_probe_url: str = "http://www.google.com"
    internet_timeout_s: int = 5

    db_table_config: str = "Config"

    xml_tag_root: str = "licence"
    xml_tag_moduloid: str = "ModuloId"
    xml_tag_serial: str = "licence"
    xml_tag_offline_attempts: str = "offline_attempts"

    tk_error_title: str = "Erro de Licenciamento"
    tk_warning_title: str = "Aviso de Licenciamento"
    terminal_error_header: str = "ERRO DE LICENCIAMENTO:"

# ======================================================
# Configurações específicas de core/operationserial.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class OperationSerialConfig:
    # Prefixo e formatação do serial (ex: "OPR-<ModuloId>-<timestamp>")
    serial_prefix: str = "OPR-"
    serial_delimiter: str = "-"

    # Tabela e colunas no Banco de Dados Local (BDL)
    table_inicializacoes: str = "Inicializacoes"
    col_data: str = "Data"
    col_modulo_id: str = "ModuloId"
    col_operador: str = "Operador"

    # Parâmetros de tentativa/espera ao gerar serial único
    sleep_between_attempts_seconds: int = 1
    max_attempts: int = 5

    # Mensagens de interface/log
    msg_instance_use_get: str = "Use OperationSerial.get_serial(modulo_id, configDataXml) para acessar."
    msg_saved_ok: str = "[OperationSerial] Serial salvo no banco local: {serial}"
    msg_error_save: str = "[OperationSerial] ERRO ao salvar no banco local: {e}"
    msg_serial_generated: str = "[OperationSerial] Serial gerado: {serial}"
    msg_serial_exists_trying: str = "[OperationSerial] Serial já existe: {serial}, tentando outro..."
    err_serial_unique_fail: str = "Falha ao gerar serial único para operação."
    msg_error_check_exist: str = "[OperationSerial] ERRO ao verificar existência no banco local: {e}"
    err_first_call_missing_args: str = "ModuloId e configDataXml devem ser fornecidos na primeira chamada."
    msg_new_saved_ok: str = "[generate_new_serial] Novo serial salvo: {serial}"
    msg_new_serial_exists: str = "[generate_new_serial] Serial já existe: {serial}"
    msg_new_error_verify_insert: str = "[generate_new_serial] ERRO ao verificar/inserir: {e}"
    err_new_serial_fail: str = "Falha ao gerar novo OperacaoID."

# ======================================================
# Configurações específicas de core/pedal_input.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class PedalInputConfig:
    # Arquivo do ícone (SVG) exibido no overlay
    svg_path: str = "img/svg/pedal.svg"

    # Limites do tempo de overlay (ms)
    min_overlay_ms: int = 300
    max_overlay_ms: int = 5000

    # Padrões de comportamento
    default_debounce_ms: int = 300          # debounce padrão do pedal (ms)
    overlay_enabled_default: bool = True    # se DETECTION_OVERLAY_ENABLED não estiver definido
    overlay_ms_default: int = 2000          # fallback para DETECTION_OVERLAY_MS (ms)

    # Interpretadores de boolean string vindos do config.xml
    truthy_values: tuple = ("1", "true", "yes", "on")
    falsy_values: tuple = ("0", "false", "no", "off")

    # Mensagens de UI/Log
    msg_cfg_title: str = "Erro de configuração"
    msg_cfg_pin_missing: str = "❌ PIN_PEDAL_BCM não configurado no config.xml.\nConfigure o pino corretamente e reinicie o aplicativo."
    msg_active_ok: str = "[🦶] PedalWatcher ativo no BCM {pin} (debounce={debounce}ms)."
    msg_disabled_info: str = "[ℹ️] PedalWatcher desativado (GPIO indisponível?): {e}"
    msg_fail_incrementar: str = "[⚠️] Falha ao incrementar NC (pedal): {e}"
    msg_fail_overlay: str = "[⚠️] Erro ao exibir ícone do pedal: {e}"

    # Aparência do overlay
    overlay_icon_w: int = 72
    overlay_icon_h: int = 72
    overlay_tint_r: int = 255
    overlay_tint_g: int = 0
    overlay_tint_b: int = 0
    overlay_stylesheet: str = "background: transparent;"

# ======================================================
# Configurações específicas de selfTest.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class SelfTestConfig:
    # Temporizações (ms)
    first_test_delay_ms: int = 500
    between_tests_delay_ms: int = 1000

    # Mensagens de debug/log
    msg_initialized: str = "🔧 SystemSelfTest: Inicializado"
    msg_starting: str = "🚀 SystemSelfTest: Iniciando testes do sistema..."
    msg_running: str = "🔍 Executando teste: {test_name}"
    msg_exec_start: str = "🔍 Iniciando execução: {test_name}"
    msg_pass_all: str = "✅ SystemSelfTest: Todos os testes APROVADOS - YOLO pode ser carregado"
    msg_fail_some: str = "❌ SystemSelfTest: Alguns testes FALHARAM - YOLO NÃO será carregado"
    msg_fail_item: str = "   ❌ {test_name}: {message}"
    status_pass: str = "✅ PASSOU"
    status_fail: str = "❌ FALHOU"
    err_exec_test: str = "Erro na execução do teste: {error}"

    # Cores dos ícones na TopBar
    color_testing: str = "yellow"
    color_pass: str = "green"
    color_fail: str = "red"

    # Identificadores e nomes de testes
    test_ids: tuple = ("licenca", "internet", "bdl", "bdr", "sensores", "camera")
    test_names: tuple = (
        "Verificação de Licença",
        "Conectividade Internet",
        "Banco de Dados Local",
        "Banco de Dados Remoto",
        "Sensores do Sistema",
        "Sistema de Câmera",
    )

    # Teste de Internet
    internet_url: str = "https://www.google.com"
    internet_timeout_s: int = 5
    internet_ok_status: int = 200
    err_internet_connection: str = "Sem conexão com a internet (ConnectionError)"
    err_internet_timeout: str = "Sem resposta da internet (Timeout)"
    err_internet_generic: str = "Erro ao testar internet: {error}"
    msg_internet_ok: str = "Conectividade com a internet verificada com sucesso"
    msg_internet_unexpected: str = "Resposta inesperada: status code {status_code}"

    # Delays (s) simulados nos testes de modo teste
    sleep_license_s: float = 1.0
    sleep_local_db_s: float = 0.8
    sleep_remote_db_s: float = 1.2
    sleep_sensors_s: float = 0.6

    # Mensagens de sucesso de testes simulados
    msg_license_ok: str = "Licença válida e ativa (modo teste)"
    msg_local_db_ok: str = "Banco de dados local funcionando (modo teste)"
    msg_remote_db_ok: str = "Banco de dados remoto funcionando (modo teste)"
    msg_sensors_ok: str = "Sensores funcionando (modo teste)"

    # Teste de câmera
    msg_camera_not_detected: str = "Câmera não detectada ou inacessível"
    msg_camera_ok: str = "Câmera funcionando corretamente"
    msg_camera_detected_no_frames: str = "Câmera detectada mas não consegue capturar frames"
    err_camera: str = "Erro na câmera: {error}"

    # Diálogo de falha
    dlg_fail_title: str = "Falha nos Testes do Sistema"
    dlg_fail_header: str = "Alguns testes do sistema falharam."
    dlg_fail_prefix: str = "Os seguintes testes falharam:\n\n"
    dlg_fail_suffix: str = "\n\nO sistema YOLO não será carregado até que todos os testes sejam aprovados."

    # Detecção de Raspberry
    cpuinfo_path: str = "/proc/cpuinfo"

# ======================================================
# Configurações específicas de sensors.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class SensorsConfig:
    # Detecção de Raspberry Pi
    cpuinfo_path: str = "/proc/cpuinfo"
    cpuinfo_keywords_rpi: tuple = ("raspberry pi", "bcm")

    # Biblioteca base para I2C
    i2c_base_module: str = "smbus2"

    # Valores "reais" (placeholders) quando o HAT estiver disponível
    real_umidade: float = 55.2
    real_temperatura: float = 26.4
    real_pressao: float = 1007.3
    real_luminosidade: float = 40.3

    # Faixas de simulação quando o HAT não estiver disponível
    sim_umidade_min: float = 45.0
    sim_umidade_max: float = 65.0

    sim_temperatura_min: float = 24.0
    sim_temperatura_max: float = 30.0

    sim_pressao_min: float = 1000.0
    sim_pressao_max: float = 1015.0

    sim_luminosidade_min: float = 40.0
    sim_luminosidade_max: float = 60.0

    # Precisão do arredondamento da simulação
    sim_round_decimals: int = 1

# ======================================================
# Configurações específicas de sensorthread.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class SensorThreadConfig:
    sample_step_seconds: float = 0.5
    default_sample_interval_seconds: int = 120
    amostra_sensores_field: str = "AmostraSensores"

# ======================================================
# Configurações específicas de teclas_deteccao.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class TeclasDeteccaoConfig:
    # Caminhos dos ícones SVG
    deteccao_svg_path: str = "img/svg/teclado.svg"
    pedal_svg_path: str = "img/svg/pedal.svg"

    # Durações e passo do overlay (ms)
    min_overlay_ms: int = 300
    max_overlay_ms: int = 5000
    step_overlay_ms: int = 250
    overlay_ms_default: int = 2000  # fallback quando DETECTION_OVERLAY_MS não estiver definido/for inválido

    # Preferências booleanas vindas do config.xml
    config_key_overlay_enabled: str = "DETECTION_OVERLAY_ENABLED"
    config_key_overlay_ms: str = "DETECTION_OVERLAY_MS"
    truthy_values: tuple = ("1", "true", "yes", "on")
    falsy_values: tuple = ("0", "false", "no", "off")
    default_overlay_enabled: bool = True  # valor padrão quando não definido/no parse

    # Aparência do overlay
    overlay_icon_w: int = 72
    overlay_icon_h: int = 72
    overlay_stylesheet: str = "background: transparent;"
    overlay_tint_r: int = 255
    overlay_tint_g: int = 0
    overlay_tint_b: int = 0

    # Mensagens de UI/Log
    msg_overlay_toggle: str = "[🎛️] Overlay {state}"
    msg_overlay_ms: str = "[⏱️] Overlay: {ms} ms"
    msg_fail_incrementar_nc: str = "[⚠️] Falha ao incrementar 'Não Conforme' manualmente: {e}"
    msg_fail_overlay: str = "[⚠️] Erro ao exibir ícone (overlay): {e}"

# ======================================================
# Configurações específicas de contentWidget.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class ContentWidgetConfig:
    # Cores/estilos gerais
    bg_color: str = "#2E4459"
    label_status_style: str = "color: white; font-size: 16px;"
    progressbar_stylesheet: str = (
        "QProgressBar {"
        "    background-color: #1F2F3D;"
        "    color: white;"
        "    border: 1px solid white;"
        "    height: 24px;"
        "    border-radius: 5px;"
        "    text-align: center;"
        "}"
        "QProgressBar::chunk {"
        "    background-color: #5dc6ca;"
        "    width: 20px;"
        "}"
    )
    progress_min: int = 0
    progress_max: int = 100
    progress_width_ratio: float = 0.6

    # Mensagens iniciais e tempos
    init_label_text: str = "Iniciando..."
    ui_interval_ms: int = 40            # ~25fps (33 -> ~30fps)
    first_step_delay_ms: int = 100      # QTimer.singleShot inicial
    between_steps_delay_ms: int = 500   # intervalo entre etapas

    # Etapas (chave, mensagem)
    etapas_keys: tuple = ("licenca", "bdl", "internet", "bdr", "sensores", "ia")
    etapas_msgs: tuple = (
        "Verificando licença...",
        "Testando banco de dados local...",
        "Testando conexão com a internet...",
        "Testando banco de dados remoto...",
        "Verificando sensores...",
        "Inicializando IA...",
    )

    # Mensagens e estilos diversos
    msg_finalizando_camera_thread: str = "[🧵] Finalizando thread da câmera com segurança..."
    msg_camera_thread_finalizada: str = "[✅] Thread da câmera finalizada."
    msg_encerrando_camera: str = "[🛑] Encerrando câmera..."
    camera_shutdown_text: str = "Desligando a câmera. Aguarde!"
    camera_shutdown_style: str = "color: white; font-size: 16px; background-color: black; border: 2px solid white;"
    msg_encerrando_sistema: str = "[⛔] Encerrando sistema..."
    encerrar_threads_delay_ms: int = 300
    status_ready_msg: str = "Sistema pronto."

    # Contadores (prefixos)
    label_detectados_prefix: str = "DETECTADOS: "
    label_nao_conforme_prefix: str = "NÃO CONFORME: "
    label_totais_prefix: str = "TOTAIS: "

    # Mensagens de pausa/retomar e botões
    msg_deteccao_retomada: str = "🧠 Detecção retomada."
    msg_deteccao_pausada: str = "⏸️ Detecção pausada."
    btn_text_pausar: str = "Pausar Detecção"
    btn_text_voltar: str = "Voltar a Detectar"
    icon_play_path: str = "img/svg/play.svg"
    icon_pause_path: str = "img/svg/pausar_deteccao.svg"
    icon_btn_size: int = 40

    # Report Viewer / Reinício
    msg_abrindo_report: str = "[📊] Abrindo Report Viewer em tela cheia..."
    msg_reiniciando_app: str = "[🔁] Reiniciando aplicação..."

    # Status bar
    status_msg_duration_ms: int = 10000

    # Mensagens de atualização de classe
    dlg_erro_critico_title: str = "Erro crítico"
    dlg_erro_critico_text: str = "❌ Nenhuma classe configurada no banco de dados local. Configure a classe antes de iniciar o sistema."
    dlg_classe_ok_title: str = "Classe Atualizada"
    dlg_classe_ok_text_template: str = "A nova classe de detecção é:🧠 {classe}. Esta janela se fechará em 5 segundos."
    dlg_classe_ok_autoclose_ms: int = 5000
    dlg_classe_ok_stylesheet: str = (
        "QMessageBox {"
        "    background-color: #2E4459;"
        "}"
        "QLabel {"
        "    color: white;"
        "}"
        "QPushButton {"
        "    border: 1px solid white;"
        "    color: white;"
        "    background-color: transparent;"
        "    padding: 5px 15px;"
        "    border-radius: 4px;"
        "}"
        "QPushButton:hover {"
        "    background-color: rgba(255, 255, 255, 0.7);"
        "    color: black;"
        "}"
    )
    # Pedal debounce default (usado na criação do PedalWatcher)
    default_pedal_debounce_ms: int = 300

# ======================================================
# Configurações específicas de layout_operational.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class LayoutOperationalConfig:
    # Grid geral
    grid_spacing: int = 5
    grid_margin_left: int = 5
    grid_margin_top: int = 5
    grid_margin_right: int = 5
    grid_margin_bottom: int = 5

    # Painel de Controle (coluna 0)
    painel_titulo_text: str = "Painel de Controle"
    painel_titulo_style: str = "color: white; font-size: 18px;"
    estilo_botao_topo: str = (
        "QPushButton {"
        "    background: transparent;"
        "    color: #e8f0f6;"
        "    border: 1px solid #e8f0f6;"
        "    border-radius: 8px;"
        "    padding: 8px 14px;"
        "    qproperty-iconSize: 18px;"
        "}"
        "QPushButton:hover { background: rgba(255,255,255,0.15); }"
    )
    botoes_infos: tuple = (
        ("reiniciar_operacao", "Reiniciar Operação"),
        ("configuracao", "Configuração"),
        ("adicionar_nc", "Adicionar NC"),
        ("acao_em_massa", "Ação em massa"),
        ("relatorios", "Relatórios"),
        ("pausar_deteccao", "Pausar Detecção"),
        ("atualizar_classe", "Atualizar classe"),
    )
    botao_icon_path_template: str = "img/svg/{nome}.svg"
    botao_icon_size: int = 40

    painel_margins_left: int = 10
    painel_margins_top: int = 10
    painel_margins_right: int = 10
    painel_margins_bottom: int = 20
    painel_min_width: int = 160
    painel_widget_style: str = "background-color: #3a556f; border-radius: 10px;"

    # Botão laranja "Reiniciar"
    botao_reiniciar_text: str = " Reiniciar"
    botao_reiniciar_icon: str = "img/svg/reiniciar.svg"
    botao_reiniciar_style: str = (
        "QPushButton {"
        "    background-color: #f19267;"
        "    color: black;"
        "    border: 1px solid white;"
        "    padding: 10px 20px;"
        "    border-radius: 8px;"
        "    font-size: 14px;"
        "}"
        "QPushButton:hover { background-color: #e65b0f; }"
    )

    # Botão "Sair"
    botao_sair_text: str = " Sair"
    botao_sair_icon: str = "img/svg/sair.svg"
    botao_sair_style: str = (
        "QPushButton {"
        "    background-color: #f74a5c;"
        "    color: white;"
        "    border: 1px solid white;"
        "    padding: 10px 20px;"
        "    border-radius: 8px;"
        "    font-size: 14px;"
        "}"
        "QPushButton:hover { background-color: #f72e43; }"
    )

    # Detectores (coluna 1)
    camera_label_bg: str = "#000"
    camera_label_max_height: int = 420
    camera_widget_style: str = "background-color: transparent; border: 2px solid #3a556f; border-radius: 10px;"

    # Coluna direita (contadores + sensores)
    coluna_direita_spacing: int = 12
    coluna_direita_margin_left: int = 2
    coluna_direita_margin_top: int = 2
    coluna_direita_margin_right: int = 2
    coluna_direita_margin_bottom: int = 2
    coluna_direita_min_width: int = 200

    # Contadores
    estilo_bloco_template: str = (
        "background-color: {cor};"
        "color: black;"
        "font-weight: bold;"
        "padding: 10px;"
        "border-radius: 10px;"
        "font-size: 14px;"
    )
    contador_label_height: int = 50
    contador_detectados_text: str = "DETECTADOS: 0"
    contador_nao_conforme_text: str = "NÃO CONFORME: 0"
    contador_totais_text: str = "TOTAIS: 0"
    contador_detectados_cor: str = "#55c4c5"
    contador_nao_conforme_cor: str = "#f6918b"
    contador_totais_cor: str = "#f7f4b1"

    # Sensores
    sensores_label_temp_text: str = "🌡️ Temperatura: -- °C"
    sensores_label_umi_text: str = "💧 Umidade: -- %"
    sensores_label_pre_text: str = "🌪️ Pressão: -- hPa"
    sensores_label_lux_text: str = "🔆 Luminosidade: -- lux"
    sensores_labels_style: str = "color: white; font-size: 14px; padding: 2px 0;"
    sensores_widget_style: str = "background-color: #3a556f; border-radius: 10px; padding: 10px;"
    sensores_widget_max_height: int = 130

    # Grid colunas (ratios)
    grid_col_stretch_left: int = 0
    grid_col_stretch_center: int = 1
    grid_col_stretch_right: int = 0

# ======================================================
# Configurações específicas de dialog_insercao_massa.py
# (Apenas literais. Nenhuma lógica aqui.)
# ======================================================
from dataclasses import dataclass

@dataclass(frozen=True)
class DialogInsercaoMassaConfig:
    # Janela
    window_title: str = "Inserção em Massa de NC"
    minimum_width: int = 300

    # Estilo da janela (stylesheet)
    dialog_stylesheet: str = (
        "QLabel { color: white; font-weight: bold; padding: 3px; }"
        "QPushButton {"
        "    padding: 6px 12px;"
        "    background-color: rgba(255,255,255,0.3) !important;"
        "    color: white !important;"
        "    border: 1px solid white;"
        "    border-radius: 6px;"
        "}"
        "QPushButton:hover {"
        "    background-color: rgba(255,255,255,0.7) !important;"
        "    color: black !important;"
        "}"
        "QPushButton:pressed {"
        "    background-color: rgba(255,255,255,1.0) !important;"
        "    color: black !important;"
        "}"
        "QWidget { background-color: #2E4459; }"
        "QSpinBox::up-button, QSpinBox::down-button {"
        "    width: 0px;"
        "    height: 0px;"
        "    border: none;"
        "}"
    )

    # Campo quantidade (QSpinBox)
    spin_min: int = 0
    spin_max: int = 999
    spin_default: int = 1
    spin_stylesheet: str = "background-color: white; color: black; font-size: 18px; padding: 3px; border-radius: 4px;"

    # Botões e textos
    btn_menos_text: str = "-"
    btn_mais_text: str = "+"
    btn_cancelar_text: str = "Sair sem inserir"
    btn_inserir_text: str = "Inserir"

    # Layout
    spacing_after_input: int = 20

    # Geração do registro manual
    frame_false_height: int = 480
    frame_false_width: int = 640
    frame_false_channels: int = 3
    frame_false_dtype_name: str = "uint8"
    track_id_base: int = 90000
    nao_conforme_label: str = "Não"
    manual_flag_value: int = 1

    # Mensagens e tempos
    msg_mass_success_template: str = "[📦] Inserção em massa de {quantidade} NC realizada."
    msg_error_prefix_template: str = "[❌] Erro na inserção em massa: {e}"
    status_msg_duration_ms: int = 7000
    qmb_warning_title: str = "Aviso"
    qmb_warning_text: str = "Informe uma quantidade maior que zero."
    qmb_info_title: str = "Sucesso"
    qmb_error_title: str = "Erro"

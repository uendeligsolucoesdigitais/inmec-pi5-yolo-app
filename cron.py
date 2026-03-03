# cron.py

import os
import sys
import datetime

# Adiciona a raiz ao sys.path para permitir imports dos módulos
sys.path.append(os.path.abspath("."))

from core.bdlmanager import BDLManager
from core.bdrmanager import BDRManager

# Flag global de debug
DEBUG = True

# Diretório e arquivo de log
LOG_DIR = os.path.join("logs")
LOG_FILE = os.path.join(LOG_DIR, "sync_config.log")

def registrar_log(mensagem):
    """Registra a mensagem no log e imprime no terminal se DEBUG estiver ativado."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {mensagem}"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")
    
    if DEBUG:
        print(log_message)

def sincronizar_config():
    registrar_log("Iniciando sincronização da tabela Config...")

    bdl = BDLManager()
    bdr = BDRManager()

    dados_bdr = bdr.read("Config")
    dados_bdl = bdl.read("Config")

    if not dados_bdr:
        registrar_log("Nenhum dado retornado do BDR.")
        return

    if not dados_bdl:
        registrar_log("Nenhum dado existente no BDL. Sincronização não realizada.")
        return

    colunas_bdr = set(dados_bdr[0].keys())
    colunas_bdl = set(dados_bdl[0].keys())

    colunas_faltando = colunas_bdr - colunas_bdl
    if colunas_faltando:
        registrar_log(f"ATENÇÃO: Colunas faltando no BDL: {', '.join(colunas_faltando)}")
        return

    for registro_bdr in dados_bdr:
        chave = registro_bdr.get("ModuloId")
        if not chave:
            continue

        sucesso = bdl.update_where("Config", registro_bdr, f"ModuloId = '{chave}'")

        if sucesso:
            registrar_log(f"Registro ModuloId={chave} atualizado com sucesso.")
        else:
            registrar_log(f"Erro ao atualizar registro ModuloId={chave}.")


    registrar_log("Sincronização da tabela Config concluída.")

def sincronizar_registros():
    registrar_log("Iniciando sincronização da tabela Registros...")

    bdl = BDLManager()
    bdr = BDRManager()

    dados_bdl = bdl.read("Registros")
    dados_bdr = bdr.read("Registros")

    if not dados_bdl:
        registrar_log("Nenhum dado encontrado no BDL para a tabela Registros.")
        return

    if not dados_bdr:
        dados_bdr = []

    # Verificação de colunas
    colunas_bdl = set(dados_bdl[0].keys())
    colunas_bdr = set(dados_bdr[0].keys())

    if colunas_bdl != colunas_bdr:
        registrar_log("ERRO: As colunas da tabela Registros entre BDL e BDR são diferentes.")
        registrar_log(f"BDL: {sorted(colunas_bdl)}")
        registrar_log(f"BDR: {sorted(colunas_bdr)}")
        return

    pulados = 0
    inseridos = 0

    # Ignorar colunas que não devem ser comparadas
    colunas_comparacao = [col for col in colunas_bdl if col not in ("idRegistros", "DataUP")]

    for reg_bdl in dados_bdl:
        duplicado = False
        for reg_bdr in dados_bdr:
            if all(reg_bdl[col] == reg_bdr[col] for col in colunas_comparacao):
                duplicado = True
                break

        if duplicado:
            pulados += 1
            continue

        # Remove idRegistros e DataUP antes de inserir
        novo_reg = {k: v for k, v in reg_bdl.items() if k not in ("idRegistros", "DataUP")}
        sucesso = bdr.insert_into_table("Registros", novo_reg)

        if sucesso:
            inseridos += 1
        else:
            registrar_log(f"Erro ao inserir registro: {novo_reg}")

    registrar_log(f"Sincronização da tabela Registros concluída.")
    registrar_log(f"Total de registros pulados (já existentes): {pulados}")
    registrar_log(f"Total de registros inseridos: {inseridos}")


def sincronizar_inicializacoes():
    registrar_log("Iniciando sincronização da tabela Inicializacoes...")

    bdl = BDLManager()
    bdr = BDRManager()

    dados_bdl = bdl.read("Inicializacoes")
    dados_bdr = bdr.read("Inicializacoes")

    if not dados_bdl:
        registrar_log("Nenhum dado encontrado no BDL para a tabela Inicializacoes.")
        return

    if not dados_bdr:
        dados_bdr = []

    # Verificar colunas (ignorando 'id' do BDR porque é auto_increment)
    colunas_bdl = set(dados_bdl[0].keys()) - {"id"}
    colunas_bdr = set(dados_bdr[0].keys()) - {"id"}

    if colunas_bdl != colunas_bdr:
        registrar_log("ERRO: As colunas da tabela Inicializacoes entre BDL e BDR são diferentes.")
        registrar_log(f"BDL: {sorted(colunas_bdl)}")
        registrar_log(f"BDR: {sorted(colunas_bdr)}")
        return

    operadores_bdr = {reg["Operador"] for reg in dados_bdr}
    inseridos = 0
    existentes = 0

    for reg in dados_bdl:
        operador = reg.get("Operador")
        if operador in operadores_bdr:
            existentes += 1
            continue

        novo_reg = {
            "Data": reg.get("Data"),
            "ModuloId": reg.get("ModuloId"),
            "Operador": reg.get("Operador")
        }

        sucesso = bdr.insert_into_table("Inicializacoes", novo_reg)
        if sucesso:
            inseridos += 1
        else:
            registrar_log(f"Erro ao inserir operação: {novo_reg}")

    registrar_log(f"Sincronização da tabela Inicializacoes concluída.")
    registrar_log(f"Operações já existentes no BDR: {existentes}")
    registrar_log(f"Novas operações inseridas no BDR: {inseridos}")



if __name__ == "__main__":
    sincronizar_config()
    sincronizar_registros()
    sincronizar_inicializacoes()

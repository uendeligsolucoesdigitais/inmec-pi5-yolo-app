# DOCUMENTAÇÃO PENDENTE #
import os
import xml.etree.ElementTree as ET
from cryptography.fernet import Fernet
import mysql.connector
import tkinter as tk
from tkinter import messagebox
import requests

#import getConfig

# Classe responsável pela verificação da licença do sistema.
class LicenceVerifier:
    

    # O método __init__ é chamado na inicialização da classe e carrega as configurações iniciais.
    def __init__(self,configData, configDataXml, lic_file='lic.xml', key_file='key.key', conf_file='config.xml', DEBUG=True):
        # Recebe o objeto config_data e carrega os dados de configuração do arquivo config.xml usando getConfig.
        self.config_data = configData
        self.DEBUG = DEBUG
        self.configDataXml = configDataXml
         #print(config_data)
        self.lic_file = lic_file  # Nome do arquivo de licença criptografado
        self.key_file = key_file  # Nome do arquivo de chave criptográfica
        self.key = self.load_or_generate_key()  # Carrega ou gera a chave criptográfica
        self.lic_data = self.load_licence_data()  # Carrega os dados de licença
        self.max_offline_attempts = 3  # Número máximo de acessos offline permitidos

    # Função para carregar ou gerar a chave criptográfica usada na encriptação e decriptação dos dados da licença.
    def load_or_generate_key(self):
        if os.path.exists(self.key_file):  # Verifica se o arquivo de chave já existe
            with open(self.key_file, 'rb') as keyfile:
                key = keyfile.read()  # Se existe, carrega a chave
        else:
            key = Fernet.generate_key()  # Se não existe, gera uma nova chave
            with open(self.key_file, 'wb') as keyfile:
                keyfile.write(key)  # Salva a nova chave gerada
        return key

    # Função para descriptografar os dados usando a chave carregada.
    def decrypt_data(self, encrypted_data):
        fernet = Fernet(self.key)  # Inicializa o Fernet com a chave
        decrypted = fernet.decrypt(encrypted_data).decode()  # Descriptografa os dados e decodifica em string
        return decrypted

    # Função para criptografar os dados antes de salvar o arquivo lic.xml.
    def encrypt_data(self, data):
        fernet = Fernet(self.key)  # Inicializa o Fernet com a chave
        encrypted = fernet.encrypt(data.encode())  # Criptografa os dados
        return encrypted

    # Função que carrega e descriptografa o arquivo lic.xml, contendo a licença.
    def load_licence_data(self):
        if os.path.exists(self.lic_file):  # Verifica se o arquivo lic.xml existe
            try:
                with open(self.lic_file, 'rb') as file:
                    encrypted_data = file.read()  # Lê o conteúdo criptografado do arquivo
                decrypted_data = self.decrypt_data(encrypted_data)  # Descriptografa o conteúdo
                root = ET.fromstring(decrypted_data)  # Interpreta o XML descrito

                # Extrai o ModuloId, Serial e Contagem de acessos offline (se existir).
                modulo_id = root.find('ModuloId').text
                serial = root.find('licence').text
                offline_attempts = root.find('offline_attempts')
                if offline_attempts is None:
                    offline_attempts = 0  # Se não existir, inicia com 0
                else:
                    offline_attempts = int(offline_attempts.text)  # Converte para inteiro o valor de tentativas offline

                return {'ModuloId': modulo_id, 'Serial': serial, 'offline_attempts': offline_attempts}  # Retorna os dados
            except Exception as e:
                erro_msg = f"Erro ao carregar o arquivo de licença: {e}"
                print("\n" + "="*80)
                print("ERRO DE LICENCIAMENTO:")
                print(erro_msg)
                print("="*80 + "\n")
                return None
        else:
            erro_msg = f"Arquivo {self.lic_file} não encontrado."
            print("\n" + "="*80)
            print("ERRO DE LICENCIAMENTO:")
            print(erro_msg)
            print("="*80 + "\n")
            return None

    # Função que salva os dados atualizados da licença, incluindo a contagem de tentativas offline.
    def save_licence_data(self):
        root = ET.Element('licence')  # Cria o XML base
        ET.SubElement(root, 'ModuloId').text = self.lic_data['ModuloId']
        ET.SubElement(root, 'licence').text = self.lic_data['Serial']
        ET.SubElement(root, 'offline_attempts').text = str(self.lic_data['offline_attempts'])

        # Converte o XML para string e criptografa os dados antes de salvar.
        xml_data = ET.tostring(root, encoding='unicode')
        encrypted_data = self.encrypt_data(xml_data)

        # Escreve os dados criptografados no arquivo lic.xml
        with open(self.lic_file, 'wb') as file:
            file.write(encrypted_data)

    # Função principal que verifica a validade da licença.
    def verify_licence(self):
        if not self.lic_data:  # Verifica se os dados da licença estão carregados corretamente
            erro = 'Arquivo de licença não encontrado ou inválido.'
            self.show_error_message(erro)
            self.print_error_to_terminal(erro)
            return erro, False
            
        self.moduloID = self.config_data['ModuloId']
        # Verifica se o ModuloId e Serial no lic.xml são iguais aos passados no config_data.
        if self.lic_data['ModuloId'] != self.moduloID or self.lic_data['Serial'] != self.config_data['Serial']:
            erro = f"Erro de licença: ModuloId ou Serial inválido. Esperado ModuloId={self.moduloID}, Serial={self.config_data['Serial']}. Encontrado ModuloId={self.lic_data['ModuloId']}, Serial={self.lic_data['Serial']}."
            self.show_error_message(erro)
            self.print_error_to_terminal(erro)
            return erro, False

        # Tenta acessar a internet para validar a licença no banco de dados remoto.
        if not self.check_internet_access():
            return self.handle_offline_access()  # Se não houver internet, lida com o acesso offline

        # Verifica o serial no banco de dados se houver conexão com a internet.
        db_result, db_error = self.verify_serial_in_db()
        if not db_result:
            erro = f"Erro de licença: Serial não encontrado no banco de dados. Detalhes: {db_error}"
            self.show_error_message(erro)
            self.print_error_to_terminal(erro)
            return erro, False

        # Se tudo estiver correto, zera as tentativas offline e salva os dados atualizados.
        self.lic_data['offline_attempts'] = 0
        self.save_licence_data()
        if self.DEBUG: print("Licença verificada com sucesso!")
        return "Licença válida", True

    # Função que verifica a conexão com a internet.
    def check_internet_access(self):
        try:
            response = requests.get("http://www.google.com", timeout=5)  # Tenta acessar o Google como teste
            return response.status_code == 200  # Retorna True se o status for 200 (sucesso)
        except requests.ConnectionError:
            if self.DEBUG: print("Sem conexão com a internet para verificar licença.")
            return False  # Retorna False se não houver conexão

    # Função que gerencia o acesso quando não há internet (acesso offline).
    def handle_offline_access(self):
        self.lic_data['offline_attempts'] += 1  # Incrementa a contagem de acessos offline

        # Verifica se o número de acessos offline ultrapassou o limite.
        if self.lic_data['offline_attempts'] > self.max_offline_attempts:
            erro = f"O número de acessos sem conexão com a internet foi excedido. Limite: {self.max_offline_attempts}, Atual: {self.lic_data['offline_attempts']}"
            self.show_error_message(erro)
            self.print_error_to_terminal(erro)
            return erro, False
        else:
            # Mostra um aviso de que o acesso offline é permitido e informa quantas tentativas restam.
            warning = f"Acesso offline permitido. Restam {self.max_offline_attempts - self.lic_data['offline_attempts']} tentativas."
            self.show_warning_message(warning)
            if self.DEBUG: print(warning)
            self.save_licence_data()  # Salva os dados atualizados
            return warning, True

    # Função que verifica o serial no banco de dados remoto usando os dados de configuração.
    def verify_serial_in_db(self):
        try:
            # Conecta ao banco de dados usando as informações do self.config_data
            conn = mysql.connector.connect(
                host=self.configDataXml['host_name'],
                user=self.configDataXml['user_name'],
                password=self.configDataXml['user_password'],
                database=self.configDataXml['db_name']
            )
            cursor = conn.cursor()

            # Executa a consulta SQL para verificar o ModuloId e Serial no banco de dados.
            query = """
                SELECT COUNT(*) 
                FROM Config 
                WHERE ModuloId = %s AND Serial = %s AND Cliente = %s
            """
            cursor.execute(query, (self.config_data['ModuloId'], self.config_data['Serial'], self.config_data['Cliente']))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result[0] > 0:
                return True, None  # Retorna True se houver correspondência no banco
            else:
                error_msg = f"Nenhum registro encontrado para ModuloId={self.config_data['ModuloId']}, Serial={self.config_data['Serial']}, Cliente={self.config_data['Cliente']}"
                return False, error_msg
        except mysql.connector.Error as err:
            error_msg = f"Erro de banco de dados: {err}"
            if self.DEBUG: print(error_msg)
            return False, error_msg

    # Função para exibir uma mensagem de erro na tela usando Tkinter.
    def show_error_message(self, message):
        root = tk.Tk()
        root.withdraw()  # Esconde a janela principal do Tkinter
        messagebox.showerror("Erro de Licenciamento", message)  # Exibe uma mensagem de erro
        root.destroy()  # Fecha a janela

    # Função para exibir uma mensagem de aviso (ex: número de tentativas offline restantes).
    def show_warning_message(self, message):
        root = tk.Tk()
        root.withdraw()  # Esconde a janela principal do Tkinter
        messagebox.showwarning("Aviso de Licenciamento", message)  # Exibe uma mensagem de aviso
        root.destroy()  # Fecha a janela
        
    # Função para exibir o erro de licenciamento no terminal de forma destacada
    def print_error_to_terminal(self, message):
        print("\n" + "="*80)
        print("ERRO DE LICENCIAMENTO:")
        print(message)
        print("="*80 + "\n")

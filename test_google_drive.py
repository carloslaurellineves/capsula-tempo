#!/usr/bin/env python3
"""
Script de Teste e Diagnóstico para Google Drive API
===================================================

Este script testa todos os aspectos da integração com Google Drive:
1. Validação das variáveis de ambiente
2. Autenticação com a Service Account
3. Acesso à pasta do Google Drive
4. Teste de upload de arquivo

Autor: Assistente AI
Data: 2025-09-08
"""

import os
import json
import tempfile
import traceback
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io


def print_header(title):
    """Imprime um cabeçalho formatado"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_step(step_num, description):
    """Imprime o número e descrição do passo"""
    print(f"\n[PASSO {step_num}] {description}")
    print("-" * 50)


def print_success(message):
    """Imprime mensagem de sucesso"""
    print(f"✅ SUCESSO: {message}")


def print_error(message):
    """Imprime mensagem de erro"""
    print(f"❌ ERRO: {message}")


def print_warning(message):
    """Imprime mensagem de aviso"""
    print(f"⚠️  AVISO: {message}")


def print_info(message):
    """Imprime mensagem informativa"""
    print(f"ℹ️  INFO: {message}")


def test_env_variables():
    """Testa e valida as variáveis de ambiente"""
    print_step(1, "Verificando variáveis de ambiente (.env)")
    
    # Carregar o arquivo .env
    load_dotenv()
    
    # Verificar FOLDER_ID
    folder_id = os.getenv("FOLDER_ID")
    print(f"FOLDER_ID encontrado: {folder_id}")
    
    if not folder_id:
        print_error("FOLDER_ID não está definido no arquivo .env")
        return False, None, None
    
    # Validar formato do FOLDER_ID
    if "?usp=" in folder_id or "https://" in folder_id:
        print_error("FOLDER_ID contém parâmetros de URL inválidos")
        print_info("Remova tudo após '?' e mantenha apenas o ID da pasta")
        # Tentar extrair apenas o ID
        if "?usp=" in folder_id:
            clean_folder_id = folder_id.split("?")[0]
            if clean_folder_id.startswith("'") and clean_folder_id.endswith("'"):
                clean_folder_id = clean_folder_id[1:-1]
            print_info(f"ID limpo sugerido: {clean_folder_id}")
            folder_id = clean_folder_id
        else:
            return False, None, None
    
    # Remover aspas se presentes
    if folder_id.startswith("'") and folder_id.endswith("'"):
        folder_id = folder_id[1:-1]
        print_info(f"Removendo aspas do FOLDER_ID: {folder_id}")
    
    print_success(f"FOLDER_ID válido: {folder_id}")
    
    # Verificar MAX_MB
    max_mb = os.getenv("MAX_MB", "500")
    print_success(f"MAX_MB: {max_mb}MB")
    
    # Verificar credenciais JSON
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        # Verificar se existe arquivo service_account.json
        if os.path.exists("service_account.json"):
            print_success("Arquivo service_account.json encontrado")
            return True, folder_id, "file"
        else:
            print_error("Nem GOOGLE_SERVICE_ACCOUNT_JSON nem service_account.json foram encontrados")
            return False, None, None
    
    # Tentar fazer parse do JSON
    try:
        # Limpar espaços e quebras de linha desnecessárias
        service_account_json = service_account_json.strip()
        service_account_info = json.loads(service_account_json)
        
        # Verificar campos obrigatórios
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in service_account_info:
                print_error(f"Campo obrigatório '{field}' não encontrado no JSON")
                return False, None, None
        
        print_success("JSON das credenciais é válido")
        print_info(f"Service Account Email: {service_account_info.get('client_email')}")
        print_info(f"Project ID: {service_account_info.get('project_id')}")
        
        return True, folder_id, service_account_info
        
    except json.JSONDecodeError as e:
        print_error(f"JSON das credenciais inválido: {e}")
        print_info("Verifique se o JSON está em uma única linha e bem formatado")
        return False, None, None


def test_google_auth(service_account_info):
    """Testa a autenticação com Google"""
    print_step(2, "Testando autenticação com Google Drive API")
    
    try:
        scopes = ["https://www.googleapis.com/auth/drive"]
        
        if service_account_info == "file":
            # Usar arquivo local
            creds = service_account.Credentials.from_service_account_file(
                "service_account.json", scopes=scopes
            )
            print_info("Usando arquivo service_account.json")
        else:
            # Usar JSON da variável de ambiente
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=scopes
            )
            print_info("Usando variável de ambiente GOOGLE_SERVICE_ACCOUNT_JSON")
        
        # Testar conexão
        service = build("drive", "v3", credentials=creds)
        
        # Fazer uma chamada simples para testar
        about = service.about().get(fields="user").execute()
        print_success("Autenticação com Google Drive API realizada com sucesso!")
        print_info(f"Usuário autenticado: {about.get('user', {}).get('emailAddress', 'N/A')}")
        
        return True, service
        
    except Exception as e:
        print_error(f"Falha na autenticação: {e}")
        traceback.print_exc()
        return False, None


def test_folder_access(service, folder_id):
    """Testa o acesso à pasta do Google Drive"""
    print_step(3, "Verificando acesso à pasta do Google Drive")
    
    try:
        # Tentar acessar informações da pasta (com suporte a Shared Drives)
        folder_info = service.files().get(
            fileId=folder_id,
            supportsAllDrives=True,
            fields="id,name,mimeType,createdTime,driveId"
        ).execute()
        
        print_success(f"Pasta encontrada: {folder_info.get('name')}")
        print_info(f"ID da pasta: {folder_info.get('id')}")
        print_info(f"Tipo: {folder_info.get('mimeType')}")
        print_info(f"Criada em: {folder_info.get('createdTime')}")
        
        # Verificar se está em Shared Drive
        drive_id = folder_info.get('driveId')
        if drive_id:
            print_success("✅ PASTA ESTÁ EM SHARED DRIVE!")
            print_info(f"Drive ID: {drive_id}")
            try:
                drive_info = service.drives().get(driveId=drive_id).execute()
                print_info(f"Nome do Shared Drive: {drive_info.get('name')}")
            except:
                pass
        else:
            print_warning("⚠️  PASTA NÃO ESTÁ EM SHARED DRIVE")
            print_info("Esta pasta está no Drive pessoal - pode haver limitações de quota")
        
        # Verificar se é realmente uma pasta
        if folder_info.get('mimeType') != 'application/vnd.google-apps.folder':
            print_warning("O ID fornecido não corresponde a uma pasta")
            return False
        
        # Verificar permissões listando arquivos da pasta
        try:
            files_result = service.files().list(
                q=f"'{folder_id}' in parents",
                pageSize=1,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = files_result.get('files', [])
            print_success(f"Permissões de leitura OK. {len(files)} arquivo(s) na pasta")
            
        except HttpError as e:
            if e.resp.status == 403:
                print_error("Sem permissão para listar arquivos na pasta")
                print_info("Verifique se a service account tem acesso de 'Editor' à pasta")
                return False
            else:
                raise
        
        return True
        
    except HttpError as e:
        if e.resp.status == 404:
            print_error("Pasta não encontrada")
            print_info("Verifique se o FOLDER_ID está correto")
        elif e.resp.status == 403:
            print_error("Sem permissão para acessar a pasta")
            print_info("Verifique se a pasta foi compartilhada com a service account")
            print_info("Email da service account: capsula-service@personal-471220.iam.gserviceaccount.com")
        else:
            print_error(f"Erro HTTP {e.resp.status}: {e}")
        
        return False
        
    except Exception as e:
        print_error(f"Erro inesperado ao acessar pasta: {e}")
        traceback.print_exc()
        return False


def test_file_upload(service, folder_id):
    """Testa o upload de um arquivo de teste"""
    print_step(4, "Testando upload de arquivo")
    
    try:
        # Criar arquivo de teste em memória
        test_content = f"""
Teste de Upload - Cápsula do Tempo
==================================

Este é um arquivo de teste criado automaticamente para verificar
se o upload para o Google Drive está funcionando corretamente.

Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Service Account: capsula-service@personal-471220.iam.gserviceaccount.com
Pasta ID: {folder_id}

Se você está vendo este arquivo na pasta do Google Drive,
significa que o sistema está funcionando perfeitamente! 🎉

Você pode deletar este arquivo com segurança.
        """.strip()
        
        # Nome do arquivo de teste
        test_filename = f"TESTE_CAPSULA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Metadados do arquivo
        file_metadata = {
            'name': test_filename,
            'parents': [folder_id],
            'description': 'Arquivo de teste gerado automaticamente pelo script de diagnóstico'
        }
        
        print_info(f"Criando arquivo de teste: {test_filename}")
        
        # Upload do arquivo
        media = MediaIoBaseUpload(
            io.BytesIO(test_content.encode('utf-8')), 
            mimetype='text/plain',
            resumable=True
        )
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields='id,name,webViewLink'
        ).execute()
        
        print_success("Upload realizado com sucesso!")
        print_info(f"ID do arquivo: {uploaded_file.get('id')}")
        print_info(f"Nome: {uploaded_file.get('name')}")
        
        web_link = uploaded_file.get('webViewLink')
        if web_link:
            print_info(f"Link: {web_link}")
        
        # Tentar definir permissões para visualização pública (opcional)
        try:
            service.permissions().create(
                fileId=uploaded_file['id'],
                body={'role': 'reader', 'type': 'anyone'},
                supportsAllDrives=True
            ).execute()
            print_info("Arquivo configurado para visualização pública")
        except:
            print_warning("Não foi possível configurar visualização pública (não é crítico)")
        
        return True, uploaded_file
        
    except HttpError as e:
        if e.resp.status == 403:
            print_error("Sem permissão para fazer upload na pasta")
            print_info("Verifique se a service account tem acesso de 'Editor' à pasta")
        elif e.resp.status == 404:
            print_error("Pasta não encontrada durante upload")
        else:
            print_error(f"Erro HTTP {e.resp.status}: {e}")
        
        return False, None
        
    except Exception as e:
        print_error(f"Erro inesperado durante upload: {e}")
        traceback.print_exc()
        return False, None


def main():
    """Função principal que executa todos os testes"""
    print_header("DIAGNÓSTICO COMPLETO - GOOGLE DRIVE API")
    print("Este script irá testar todos os aspectos da configuração do Google Drive.")
    print("Resultados detalhados serão exibidos para cada etapa.")
    
    # Contadores de sucesso
    tests_passed = 0
    total_tests = 4
    
    # Teste 1: Variáveis de ambiente
    env_ok, folder_id, service_account_info = test_env_variables()
    if env_ok:
        tests_passed += 1
    else:
        print_error("Não é possível continuar sem variáveis de ambiente válidas")
        print_info("Corrija o arquivo .env e execute novamente")
        return
    
    # Teste 2: Autenticação
    auth_ok, service = test_google_auth(service_account_info)
    if auth_ok:
        tests_passed += 1
    else:
        print_error("Não é possível continuar sem autenticação válida")
        return
    
    # Teste 3: Acesso à pasta
    folder_ok = test_folder_access(service, folder_id)
    if folder_ok:
        tests_passed += 1
    else:
        print_error("Não é possível testar upload sem acesso à pasta")
        # Continuar mesmo assim para ver o erro específico
    
    # Teste 4: Upload de arquivo
    if folder_ok:
        upload_ok, uploaded_file = test_file_upload(service, folder_id)
        if upload_ok:
            tests_passed += 1
    else:
        print_info("Pulando teste de upload devido a falha no acesso à pasta")
    
    # Resultado final
    print_header("RESULTADO FINAL")
    
    if tests_passed == total_tests:
        print_success(f"TODOS OS TESTES PASSARAM! ({tests_passed}/{total_tests})")
        print("🎉 Sua configuração está perfeita!")
        print("O sistema deve funcionar corretamente para upload de imagens.")
    else:
        print_error(f"ALGUNS TESTES FALHARAM: {tests_passed}/{total_tests} passaram")
        print("\n📋 AÇÕES NECESSÁRIAS:")
        
        if not env_ok:
            print("- Corrigir arquivo .env (FOLDER_ID e credenciais JSON)")
        if not auth_ok:
            print("- Verificar credenciais da service account")
        if not folder_ok:
            print("- Compartilhar pasta com a service account (capsula-service@personal-471220.iam.gserviceaccount.com)")
            print("- Dar permissão de 'Editor' à service account")
        
        print("\nApós as correções, execute este script novamente para verificar.")
    
    print(f"\nScript executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

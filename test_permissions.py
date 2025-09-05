#!/usr/bin/env python3
"""
Script para testar permissões da pasta do Google Drive com retry
"""
import os
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

def test_permissions_with_retry(max_attempts=5, wait_seconds=30):
    """Testa permissões com várias tentativas"""
    print("🔍 Testando permissões da pasta do Google Drive...")
    
    # Carregar variáveis do .env
    load_dotenv()
    FOLDER_ID = os.getenv("FOLDER_ID")
    
    if not FOLDER_ID:
        print("❌ FOLDER_ID não encontrado no .env")
        return False
    
    print(f"📂 Pasta ID: {FOLDER_ID}")
    
    # Configurar credenciais
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    
    try:
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        if service_account_json:
            service_account_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            service_email = service_account_info.get('client_email')
        else:
            credentials = service_account.Credentials.from_service_account_file(
                "service_account.json", scopes=SCOPES
            )
            with open("service_account.json", "r") as f:
                service_info = json.load(f)
                service_email = service_info.get('client_email')
        
        print(f"📧 Service Account: {service_email}")
        
        # Conectar com a API
        service = build("drive", "v3", credentials=credentials)
        
        for attempt in range(1, max_attempts + 1):
            print(f"\n🔄 Tentativa {attempt}/{max_attempts}...")
            
            try:
                # Testar acesso básico à pasta
                folder_info = service.files().get(
                    fileId=FOLDER_ID, 
                    fields='id,name,owners,capabilities'
                ).execute()
                
                print(f"✅ Pasta acessível: {folder_info['name']}")
                
                # Verificar permissões
                capabilities = folder_info.get('capabilities', {})
                can_add_children = capabilities.get('canAddChildren', False)
                can_edit = capabilities.get('canEdit', False)
                
                print(f"   📁 Pode adicionar arquivos: {'✅ SIM' if can_add_children else '❌ NÃO'}")
                print(f"   ✏️  Pode editar: {'✅ SIM' if can_edit else '❌ NÃO'}")
                
                if can_add_children:
                    print("🎉 SUCESSO! A service account tem permissões adequadas!")
                    
                    # Fazer um teste prático criando um arquivo de teste
                    print("🧪 Testando upload real...")
                    test_file_metadata = {
                        'name': f'teste_permissao_{int(time.time())}.txt',
                        'parents': [FOLDER_ID]
                    }
                    
                    from googleapiclient.http import MediaIoBaseUpload
                    import io
                    
                    test_content = "Teste de permissão - pode ser deletado"
                    media = MediaIoBaseUpload(
                        io.BytesIO(test_content.encode()), 
                        mimetype='text/plain'
                    )
                    
                    test_file = service.files().create(
                        body=test_file_metadata,
                        media_body=media,
                        fields='id,name'
                    ).execute()
                    
                    print(f"✅ Arquivo de teste criado: {test_file['name']}")
                    print(f"   ID: {test_file['id']}")
                    
                    # Deletar o arquivo de teste
                    service.files().delete(fileId=test_file['id']).execute()
                    print("🗑️  Arquivo de teste removido")
                    
                    print("\n🎉 TESTE COMPLETO BEM-SUCEDIDO!")
                    print("Sua aplicação deve funcionar normalmente agora!")
                    return True
                else:
                    print(f"⏳ Ainda sem permissão para adicionar arquivos...")
                    if attempt < max_attempts:
                        print(f"   Aguardando {wait_seconds} segundos antes da próxima tentativa...")
                        time.sleep(wait_seconds)
                    else:
                        print("❌ Permissões não foram propagadas ainda.")
                        print("\n💡 VERIFIQUE SE VOCÊ:")
                        print(f"   1. Compartilhou a pasta com: {service_email}")
                        print("   2. Deu permissão de 'Editor' (não apenas 'Visualizador')")
                        print("   3. Aguarde mais alguns minutos e tente novamente")
                        return False
                    
            except HttpError as e:
                if e.resp.status == 404:
                    print("❌ Pasta não encontrada ou ainda sem acesso")
                elif e.resp.status == 403:
                    print("❌ Ainda sem permissão para acessar")
                else:
                    print(f"❌ Erro HTTP {e.resp.status}: {e}")
                
                if attempt < max_attempts:
                    print(f"   Aguardando {wait_seconds} segundos antes da próxima tentativa...")
                    time.sleep(wait_seconds)
                else:
                    print("\n💡 SOLUÇÕES:")
                    print(f"   1. Confirme que compartilhou a pasta com: {service_email}")
                    print("   2. Certifique-se de ter dado permissão de 'Editor'")
                    print("   3. Aguarde mais tempo - a propagação pode demorar até 15 minutos")
                    return False
        
        return False
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    print("🕐 Testando permissões do Google Drive...")
    print("💡 Isso pode levar alguns minutos devido ao delay de propagação das permissões.")
    
    success = test_permissions_with_retry()
    
    if success:
        print("\n✨ PRONTO! Reinicie sua aplicação e teste o upload!")
    else:
        print("\n🔧 Ainda há problemas de permissão. Aguarde mais um pouco e tente novamente.")
    
    exit(0 if success else 1)

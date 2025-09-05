#!/usr/bin/env python3
"""
Teste rápido de status da pasta
"""
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

def quick_test():
    load_dotenv()
    FOLDER_ID = os.getenv("FOLDER_ID")
    
    print(f"🔍 Testando pasta: {FOLDER_ID}")
    
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
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
    
    service = build("drive", "v3", credentials=credentials)
    
    try:
        folder_info = service.files().get(
            fileId=FOLDER_ID, 
            fields='id,name,capabilities,permissions'
        ).execute()
        
        print(f"✅ SUCESSO! Pasta encontrada: {folder_info['name']}")
        
        capabilities = folder_info.get('capabilities', {})
        can_add = capabilities.get('canAddChildren', False)
        
        print(f"📁 Pode adicionar arquivos: {'✅ SIM' if can_add else '❌ NÃO'}")
        
        if can_add:
            print("🎉 PRONTO PARA USAR!")
            return True
        else:
            print("⏳ Ainda aguardando permissões...")
            return False
            
    except HttpError as e:
        print(f"❌ Erro: {e.resp.status}")
        if e.resp.status == 404:
            print("   Pasta não encontrada - verifique o compartilhamento")
        elif e.resp.status == 403:
            print("   Sem permissão - aguarde a propagação")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    quick_test()

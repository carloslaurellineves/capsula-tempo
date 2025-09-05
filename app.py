import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io
import tempfile

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
FOLDER_ID = os.getenv("FOLDER_ID")
MAX_MB = int(os.getenv("MAX_MB", "500"))  # limite por arquivo

if not FOLDER_ID:
    raise RuntimeError("Defina FOLDER_ID no .env")

# Configuração das credenciais da Service Account
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Prioridade: variável de ambiente (Railway) > arquivo local
service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if service_account_json:
    # Usando variável de ambiente (Railway)
    try:
        service_account_info = json.loads(service_account_json)
        CREDS = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        print("✅ Credenciais carregadas da variável de ambiente")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Erro ao decodificar GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
else:
    # Usando arquivo local (desenvolvimento)
    try:
        CREDS = service_account.Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
        print("✅ Credenciais carregadas do arquivo service_account.json")
    except FileNotFoundError:
        raise RuntimeError(
            "Credenciais não encontradas. Configure GOOGLE_SERVICE_ACCOUNT_JSON ou coloque service_account.json na raiz"
        )

app = FastAPI(title="Capsula do Tempo – Upload")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # redireciona direto para a página de upload
    return RedirectResponse(url="/upload", status_code=302)

@app.get("/upload", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "max_mb": MAX_MB
    })

@app.post("/upload")
async def handle_upload(
    request: Request,
    file: UploadFile = File(...),
    nome: str = Form("Convidado(a)"),
    mensagem: str = Form(""),
    consentimento: bool = Form(False),
):
    logger.info(f"Iniciando upload para usuário: {nome}, arquivo: {file.filename}")
    
    try:
        # Checagens básicas
        size_hdr = request.headers.get("content-length")
        if size_hdr:
            total_mb = int(size_hdr) / (1024 * 1024)
            if total_mb > (MAX_MB + 5):  # margem
                logger.warning(f"Arquivo muito grande: {total_mb:.2f}MB")
                raise HTTPException(status_code=413, detail="Arquivo muito grande.")

        if not consentimento:
            logger.warning("Upload rejeitado: consentimento não aceito")
            raise HTTPException(status_code=400, detail="É necessário aceitar o consentimento.")

        # Lê em memória (para produção, considere stream/chunk)
        content = await file.read()
        if len(content) == 0:
            logger.warning("Arquivo vazio enviado")
            raise HTTPException(status_code=400, detail="Arquivo vazio.")
        
        logger.info(f"Arquivo lido com sucesso: {len(content)} bytes")

        # Monta nome de arquivo no Drive
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_guest = "".join(c for c in nome if c.isalnum() or c in " -_").strip()[:60] or "Convidado"
        drive_filename = f"{ts}__{safe_guest}__{file.filename}"
        logger.info(f"Nome do arquivo no Drive: {drive_filename}")

        # Metadata + upload
        logger.info("Iniciando conexão com Google Drive API...")
        service = build("drive", "v3", credentials=CREDS)
        
        # Primeiro, verificar se a pasta existe
        try:
            folder_info = service.files().get(fileId=FOLDER_ID).execute()
            logger.info(f"Pasta encontrada: {folder_info['name']}")
        except HttpError as e:
            if e.resp.status == 404:
                logger.error(f"Pasta não encontrada! FOLDER_ID: {FOLDER_ID}")
                raise HTTPException(
                    status_code=500, 
                    detail="Erro de configuração: pasta do Google Drive não encontrada ou sem permissão de acesso."
                )
            else:
                logger.error(f"Erro ao acessar pasta: {e}")
                raise HTTPException(status_code=500, detail=f"Erro ao acessar pasta do Google Drive: {e}")
        
        file_metadata = {
            "name": drive_filename,
            "parents": [FOLDER_ID],
            "description": f"Upload da cápsula do tempo\nConvidado: {nome}\nMensagem: {mensagem}",
        }
        
        logger.info("Iniciando upload para o Google Drive...")
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=file.content_type, resumable=True)
        uploaded = service.files().create(body=file_metadata, media_body=media, fields="id,name,webViewLink").execute()
        
        logger.info(f"Upload concluído com sucesso! ID: {uploaded['id']}")

        # (Opcional) tornar o arquivo visível por link (só leitura)
        # service.permissions().create(fileId=uploaded["id"], body={"role":"reader","type":"anyone"}).execute()

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "ok": True,
                "uploaded_name": uploaded["name"],
                "webViewLink": uploaded.get("webViewLink"),
                "max_mb": MAX_MB,
            },
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions as they are already handled
        raise
    except HttpError as e:
        logger.error(f"Erro da API do Google Drive: {e}")
        if e.resp.status == 403:
            error_msg = "Erro de permissão: a service account não tem acesso à pasta do Google Drive."
        elif e.resp.status == 404:
            error_msg = "Pasta do Google Drive não encontrada. Verifique o FOLDER_ID."
        elif e.resp.status == 401:
            error_msg = "Erro de autenticação: credenciais inválidas ou expiradas."
        else:
            error_msg = f"Erro da API do Google Drive: {e}"
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        logger.error(f"Erro inesperado durante upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

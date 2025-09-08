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
SCOPES = ["https://www.googleapis.com/auth/drive"]

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
    files: list[UploadFile] = File(...),
    nome: str = Form("Convidado(a)"),
    mensagem: str = Form(""),
    consentimento: bool = Form(False),
):
    # Configurações para múltiplos arquivos
    MAX_FILES_PER_UPLOAD = 10  # máximo 10 arquivos por vez
    
    logger.info(f"Iniciando upload para usuário: {nome}, {len(files)} arquivo(s)")
    
    try:
        # Validações básicas para múltiplos arquivos
        if len(files) == 0:
            logger.warning("Nenhum arquivo enviado")
            raise HTTPException(status_code=400, detail="Nenhum arquivo foi selecionado.")
        
        if len(files) > MAX_FILES_PER_UPLOAD:
            logger.warning(f"Muitos arquivos: {len(files)} (máx: {MAX_FILES_PER_UPLOAD})")
            raise HTTPException(status_code=413, detail=f"Máximo {MAX_FILES_PER_UPLOAD} arquivos por upload.")

        if not consentimento:
            logger.warning("Upload rejeitado: consentimento não aceito")
            raise HTTPException(status_code=400, detail="É necessário aceitar o consentimento.")

        # Processar e validar todos os arquivos primeiro
        file_data_list = []
        total_size_bytes = 0
        
        for i, file in enumerate(files, 1):
            logger.info(f"Processando arquivo {i}/{len(files)}: {file.filename}")
            
            # Ler conteúdo do arquivo
            content = await file.read()
            if len(content) == 0:
                logger.warning(f"Arquivo vazio: {file.filename}")
                raise HTTPException(status_code=400, detail=f"Arquivo vazio: {file.filename}")
            
            # Verificar tamanho individual
            file_size_mb = len(content) / (1024 * 1024)
            if file_size_mb > MAX_MB:
                logger.warning(f"Arquivo muito grande: {file.filename} ({file_size_mb:.2f}MB)")
                raise HTTPException(status_code=413, detail=f"Arquivo '{file.filename}' excede {MAX_MB}MB")
            
            total_size_bytes += len(content)
            
            # Validar tipos de arquivo permitidos
            allowed_types = {
                'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp',
                'video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/quicktime',
                'application/pdf', 'text/plain', 'application/zip'
            }
            
            if file.content_type and file.content_type not in allowed_types:
                logger.warning(f"Tipo de arquivo não permitido: {file.filename} ({file.content_type})")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Tipo de arquivo não permitido: {file.filename}"
                )
            
            # Preparar dados para upload
            ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            safe_guest = "".join(c for c in nome if c.isalnum() or c in " -_").strip()[:60] or "Convidado"
            drive_filename = f"{ts}__{safe_guest}__{i:02d}__{file.filename}"
            
            file_data_list.append({
                'content': content,
                'filename': drive_filename,
                'original_filename': file.filename,
                'content_type': file.content_type,
                'size_bytes': len(content)
            })
        
        # Verificar tamanho total do lote
        total_size_mb = total_size_bytes / (1024 * 1024)
        max_total_mb = MAX_MB * len(files)  # Limite flexível baseado no número de arquivos
        
        if total_size_mb > max_total_mb:
            logger.warning(f"Lote muito grande: {total_size_mb:.2f}MB (máx: {max_total_mb:.2f}MB)")
            raise HTTPException(
                status_code=413, 
                detail=f"Tamanho total do lote ({total_size_mb:.1f}MB) excede o limite ({max_total_mb:.0f}MB)"
            )
        
        logger.info(f"Todos os arquivos validados. Tamanho total: {total_size_mb:.2f}MB")

        # Conectar ao Google Drive API
        logger.info("Iniciando conexão com Google Drive API...")
        service = build("drive", "v3", credentials=CREDS)
        
        # Verificar se a pasta existe (com suporte a Shared Drives)
        try:
            folder_info = service.files().get(
                fileId=FOLDER_ID, 
                supportsAllDrives=True
            ).execute()
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
        
        # Upload em lote com controle de erro
        uploaded_files = []
        failed_files = []
        
        logger.info(f"Iniciando upload de {len(file_data_list)} arquivo(s) para o Google Drive...")
        
        for i, file_data in enumerate(file_data_list, 1):
            try:
                logger.info(f"Fazendo upload {i}/{len(file_data_list)}: {file_data['original_filename']}")
                
                file_metadata = {
                    "name": file_data['filename'],
                    "parents": [FOLDER_ID],
                    "description": f"Upload da cápsula do tempo\nConvidado: {nome}\nMensagem: {mensagem}\nArquivo {i} de {len(file_data_list)}",
                }
                
                media = MediaIoBaseUpload(
                    io.BytesIO(file_data['content']), 
                    mimetype=file_data['content_type'], 
                    resumable=True
                )
                
                uploaded = service.files().create(
                    body=file_metadata, 
                    media_body=media, 
                    supportsAllDrives=True,
                    fields="id,name,webViewLink"
                ).execute()
                
                uploaded_files.append({
                    'id': uploaded['id'],
                    'name': uploaded['name'],
                    'original_filename': file_data['original_filename'],
                    'webViewLink': uploaded.get('webViewLink'),
                    'size_mb': file_data['size_bytes'] / (1024 * 1024)
                })
                
                logger.info(f"Upload {i} concluído com sucesso! ID: {uploaded['id']}")
                
            except Exception as upload_error:
                error_msg = f"Erro no upload de '{file_data['original_filename']}': {str(upload_error)}"
                logger.error(error_msg)
                failed_files.append({
                    'filename': file_data['original_filename'],
                    'error': str(upload_error)
                })
        
        # Verificar resultado do lote
        if len(uploaded_files) == 0:
            logger.error("Nenhum arquivo foi enviado com sucesso")
            raise HTTPException(status_code=500, detail="Falha no upload de todos os arquivos")
        
        success_count = len(uploaded_files)
        total_count = len(file_data_list)
        
        if len(failed_files) > 0:
            logger.warning(f"Upload parcial: {success_count}/{total_count} arquivos enviados")
        else:
            logger.info(f"Upload completo: {success_count}/{total_count} arquivos enviados com sucesso!")

        # Preparar dados para o template
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "ok": True,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "success_count": success_count,
                "total_count": total_count,
                "total_size_mb": round(total_size_mb, 2),
                "max_mb": MAX_MB,
                "multiple_files": True,
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

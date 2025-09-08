# 💍 Cápsula do Tempo do Casamento

> **Uma forma especial e moderna de preservar memórias do seu grande dia!**

Este projeto permite que os convidados do casamento, ao escanear um **QR Code**, sejam redirecionados para uma página web onde podem enviar **múltiplos arquivos** (fotos, vídeos, etc.) de uma só vez diretamente para uma pasta compartilhada no Google Drive. É uma maneira única de criar uma cápsula digital com todas as memórias do evento.

## 🎯 Como Funciona

1. **QR Code** → Os convidados escaneiam o código na festa
2. **Upload Web** → Acessam uma página simples e amigável  
3. **Google Drive** → Arquivos são salvos automaticamente na pasta dos noivos
4. **Memórias Eternas** → Tudo fica organizado para ser revisitado no futuro

![Fluxo do Sistema](https://img.shields.io/badge/QR%20Code-→-blue) ![Upload](https://img.shields.io/badge/Upload-→-green) ![Google Drive](https://img.shields.io/badge/Google%20Drive-→-red) ![Memórias](https://img.shields.io/badge/Memórias-💖-pink)

## 🛠️ Pré-requisitos

Antes de começar, você precisará de:

- **Python 3.10+** instalado
- **Conta no Google Cloud** com Drive API ativada
- **Service Account** configurada com chave JSON
- **Pasta no Google Drive** compartilhada com a service account
- **Conta no Railway** (ou outra plataforma PaaS)

## ⚙️ Configuração do Google Cloud

### 1. Criar Service Account

1. Acesse o [Google Cloud Console](https://console.cloud.google.com)
2. Vá em **APIs & Services** > **Credentials**
3. Clique em **Create Credentials** > **Service Account**
4. Preencha os dados e clique em **Create**
5. Na aba **Keys**, clique em **Add Key** > **Create New Key** > **JSON**
6. Faça download do arquivo JSON

### 2. Ativar Drive API

1. No Google Cloud Console, vá em **APIs & Services** > **Library**
2. Busque por "Google Drive API"
3. Clique em **Enable**

### 3. Configurar Pasta no Drive

⚠️ **IMPORTANTE:** Para service accounts funcionarem corretamente, você precisa usar um **Shared Drive**.

1. No Google Drive, clique em **"Novo" > "Shared drive"**
2. Dê um nome ao Shared Drive (ex: "Cápsula do Tempo")
3. Adicione a service account como membro com permissão de **"Manager"**
4. Crie uma pasta dentro do Shared Drive
5. Copie o **ID da pasta** da URL (a parte após `/folders/`)

## 🚀 Instalação e Configuração

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/capsula-tempo-casamento.git
cd capsula-tempo-casamento
```

### 2. Instale as Dependências

Este projeto usa **uv** como package manager:

```bash
# Se você não tem o uv instalado:
pip install uv

# Instalar dependências:
uv sync
```

Ou use pip tradicional:
```bash
pip install -r requirements.txt
```

### 3. Configure as Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# ID da pasta no Google Drive (obrigatório)
FOLDER_ID=sua_pasta_id_aqui

# Limite de upload por arquivo em MB (opcional, padrão: 500MB)
MAX_MB=500

# Para Railway: conteúdo completo do JSON da service account
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
```

### 4. Adicione o Arquivo da Service Account

- **Para desenvolvimento local**: Coloque o arquivo JSON como `service_account.json` na raiz
- **Para Railway**: Use a variável de ambiente `GOOGLE_SERVICE_ACCOUNT_JSON`

## 💻 Execução Local

Com uv:
```bash
uv run app.py
```

Ou tradicionalmente:
```bash
uvicorn app:app --reload --port 8000
```

Acesse: `http://localhost:8000/upload`

## 🧪 Teste da Configuração

Antes de usar em produção, teste se tudo está funcionando:

```bash
uv run test_google_drive.py
```

Este script testa:
- ✅ Variáveis de ambiente
- ✅ Autenticação com Google Drive
- ✅ Acesso à pasta (incluindo Shared Drives)
- ✅ Upload de arquivo de teste

### 🖼️ Teste de Múltiplos Arquivos

Para testar especificamente a funcionalidade de múltiplos arquivos:

```bash
# Primeiro, inicie o servidor em um terminal
uv run app.py

# Em outro terminal, execute o teste
uv run test_multiple_files.py
```

Este teste:
- 📁 Cria 3 arquivos de teste
- 🚀 Testa upload múltiplo via HTTP
- ✅ Valida resposta do servidor
- 🧩 Limpa arquivos de teste automaticamente

## 🚄 Deploy no Railway

### 1. Prepare os Arquivos

Certifique-se de ter os arquivos:

**requirements.txt**
```txt
fastapi==0.104.1
python-multipart==0.0.6
jinja2==3.1.2
python-dotenv==1.0.0
google-auth==2.23.4
google-api-python-client==2.108.0
uvicorn==0.24.0
```

**Procfile**
```txt
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

### 2. Conectar ao Railway

1. Acesse [railway.app](https://railway.app) e faça login
2. Clique em **New Project** > **Deploy from GitHub repo**
3. Selecione seu repositório
4. Railway detectará automaticamente que é um projeto Python

### 3. Configurar Variáveis de Ambiente

No painel do Railway, vá em **Variables** e adicione:

- `FOLDER_ID`: ID da sua pasta no Google Drive
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Conteúdo completo do JSON da service account
- `MAX_MB`: Limite de upload (opcional, padrão: 500)

### 4. Deploy Automático

O Railway fará o deploy automaticamente e fornecerá uma **URL pública** como:
```
https://seu-projeto.up.railway.app
```

Esta URL será usada no seu QR Code! 📱

## 🔒 Segurança e Boas Práticas

### ✅ Recursos de Segurança Incluídos

- **Consentimento obrigatório** no formulário
- **Limite de tamanho** de arquivo configurável
- **Validação de tipos** de arquivo aceitos
- **Sanitização** do nome do convidado
- **Verificação** de arquivos vazios

### 🚀 Funcionalidades do Upload Múltiplo

- **Até 10 arquivos** por upload
- **Preview em tempo real** dos arquivos selecionados
- **Validação individual** de tamanho e tipo
- **Upload em lote** com controle de erro robusto
- **Relatório detalhado** de sucessos e falhas
- **Compatibilidade total** com uploads únicos antigos
- **Nomeação sequencial** automática dos arquivos

### 🛡️ Melhorias Opcionais

```python
# Para adicionar rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/upload")
@limiter.limit("5/minute")  # 5 uploads por minuto
async def handle_upload(...):
    # seu código aqui
```

## 🎨 Personalização

### Interface Visual

Edite o arquivo `templates/upload.html` para:

- Alterar cores e estilo
- Personalizar mensagens para os convidados
- Adicionar fotos do casal
- Mudar o título e textos

### Exemplo de Personalização

```html
<h1>🌟 João & Maria - Nossa Cápsula do Tempo 🌟</h1>
<p>Queridos amigos e familiares, compartilhem conosco um momento especial deste dia inesquecível! 📸✨</p>
```

### Domínio Personalizado

1. No Railway, vá em **Settings** > **Domains**
2. Clique em **Custom Domain**
3. Adicione seu domínio (ex: `memorias.joaoeMaria.com.br`)
4. Configure o DNS conforme instruído

## 📱 Gerando o QR Code

Use qualquer gerador de QR Code online com sua URL do Railway:

- [QR Code Generator](https://www.qr-code-generator.com/)
- [QR Tiger](https://www.qrcode-tiger.com/)

**Dica**: Teste o QR Code antes do evento! 🧪

## 📋 Estrutura do Projeto

```
capsula-tempo/
│
├── app.py                    # Aplicação FastAPI principal ✨
├── test_google_drive.py      # Script de teste completo 🧪
├── test_multiple_files.py    # Teste de múltiplos arquivos 🖼️
├── templates/
│   └── upload.html           # Interface web com suporte múltiplo
├── pyproject.toml            # Configuração uv
├── requirements.txt          # Dependências Python
├── Procfile                 # Configuração Railway
├── .env                     # Variáveis de ambiente (local)
├── .env.example             # Exemplo de configuração
├── service_account.json     # Credenciais Google (local apenas)
└── README.md               # Este arquivo
```

## 🔧 Próximos Passos e Melhorias

### 📦 Pós-Evento

- **Backup automático**: Configure scripts para baixar todos os arquivos
- **Organização**: Crie pastas por tipo de arquivo (fotos, vídeos, mensagens)
- **Compartilhamento**: Gere um álbum digital para os convidados

### 🚀 Funcionalidades Avançadas

- **Preview de imagens** antes do upload
- **Compressão automática** de vídeos grandes  
- **Integração com Google Photos** para álbuns automáticos
- **Notificações** por email a cada novo upload
- **Dashboard** para acompanhar uploads em tempo real

### 💡 Ideias Criativas

- **Mensagens em vídeo**: Permitir gravação direta no browser
- **Timeline interativa**: Mostrar uploads em tempo real na festa
- **Filtros especiais**: Adicionar molduras temáticas do casamento

## 🆘 Solução de Problemas

### 🧪 Execute o teste primeiro!
Antes de tudo, execute o diagnóstico completo:
```bash
uv run test_google_drive.py
```

### Erro "storageQuotaExceeded"
⚠️ **Service accounts não têm quota de armazenamento!**
- **Solução:** Use um Shared Drive (conforme instruções acima)
- Mova sua pasta para dentro de um Shared Drive
- Adicione a service account como membro do Shared Drive

### Erro "FOLDER_ID não definido"
- Verifique se a variável `FOLDER_ID` está configurada corretamente
- Confirme se o ID foi copiado corretamente da URL do Drive
- Não inclua parâmetros da URL (?usp=... etc)

### Erro de permissões no Google Drive
- Verifique se a pasta foi compartilhada com o email da service account
- Confirme se a Drive API está ativada no projeto
- Para Shared Drives: adicione a service account como **Manager**

### Upload falha no Railway
- Verifique se `GOOGLE_SERVICE_ACCOUNT_JSON` está configurado
- Confirme se o JSON está em uma única linha (sem quebras)
- Use uma pasta dentro de um Shared Drive

### QR Code não funciona
- Teste a URL diretamente no navegador
- Verifique se o deploy no Railway foi bem-sucedido
- Confirme se não há erros nos logs

## 🤝 Contribuições

Contribuições são sempre bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 💝 Agradecimentos

Este projeto foi criado com muito amor para tornar momentos especiais ainda mais memoráveis. 

**Que sua cápsula do tempo seja repleta de momentos únicos e inesquecíveis! 💕**

---

<div align="center">

**Feito com ❤️ para casais apaixonados por tecnologia**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google Cloud](https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)](https://cloud.google.com/)
[![Railway](https://img.shields.io/badge/Railway-131415?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app/)

</div>

# 🚀 Dumont Cloud

Sistema de gerenciamento de GPU cloud com auto-hibernação inteligente e provisionamento ultra-rápido.

## 🎯 Quick Start

O jeito mais rápido de rodar o projeto é usar o script `dev.sh`:

```bash
./dev.sh
```

Isso irá:
- ✅ Verificar e instalar dependências
- ✅ Iniciar PostgreSQL no Docker (se necessário)
- ✅ Criar/atualizar arquivo `.env`
- ✅ Instalar dependências Python e Node
- ✅ Executar migrations do banco
- ✅ Iniciar backend (FastAPI) e frontend (Vite + React)

### Portas

- **Frontend**: `http://localhost:3200` (ou próxima livre entre 3200-3300)
- **Backend**: `http://localhost:8767`
- **API Docs**: `http://localhost:8767/docs`
- **PostgreSQL**: `localhost:5432`

## 📦 Pré-requisitos

- [Bun](https://bun.sh) - Runtime JavaScript ultra-rápido
- [Docker](https://docker.com) - Para o PostgreSQL
- Python 3.9+ - Backend FastAPI

### Instalando Bun

```bash
curl -fsSL https://bun.sh/install | bash
```

## 🗄️ Database (PostgreSQL)

### Opção 1: Via dev.sh (Recomendado)

O script `dev.sh` já cuida de tudo automaticamente.

### Opção 2: Via Docker Compose

```bash
docker-compose up -d
```

### Opção 3: Manualmente

```bash
docker run -d \
  --name dumont-cloud-db \
  -e POSTGRES_USER=dumont \
  -e POSTGRES_PASSWORD=dumont123 \
  -e POSTGRES_DB=dumontcloud \
  -p 5432:5432 \
  -v dumont-cloud-postgres-data:/var/lib/postgresql/data \
  postgres:16-alpine
```

## ⚙️ Configuração

### 1. Arquivo .env

O script `dev.sh` cria automaticamente um `.env` com valores padrão. Configure suas credenciais:

```bash
# Database (já configurado automaticamente)
DATABASE_URL=postgresql://dumont:dumont123@localhost:5432/dumontcloud

# VAST.ai API (obtenha em https://cloud.vast.ai/api/)
VAST_API_KEY=your_vast_api_key_here

# Cloudflare R2 (para backups)
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your_bucket_name

# JWT (gerado automaticamente)
SECRET_KEY=<auto-gerado>
```

### 2. Credenciais VAST.ai

1. Acesse https://cloud.vast.ai/api/
2. Copie sua API key
3. Cole no `.env` na variável `VAST_API_KEY`

## 🛠️ Desenvolvimento Manual

Se preferir rodar sem o script `dev.sh`:

### Backend (FastAPI)

```bash
# 1. Criar virtualenv
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar servidor
uvicorn src.main:app --reload --port 8767
```

### Frontend (Vite + React)

```bash
cd web

# 1. Instalar dependências
bun install

# 2. Rodar servidor
bun run dev --port 3200
```

## 🧪 Testes

```bash
# Backend
pytest

# Frontend
cd web
bun test
```

## 📂 Estrutura do Projeto

```
dumont-cloud/
├── src/                    # Backend Python (FastAPI)
│   ├── api/               # Endpoints da API
│   ├── domain/            # Lógica de negócio
│   ├── infrastructure/    # Providers (VAST, GCP, etc)
│   └── main.py           # Entry point
├── web/                   # Frontend React + Vite
│   ├── src/
│   │   ├── components/   # Componentes React
│   │   ├── pages/        # Páginas
│   │   └── context/      # Context API
│   └── package.json
├── alembic/              # Migrations do banco
├── dev.sh                # Script de desenvolvimento
├── docker-compose.yml    # PostgreSQL
└── requirements.txt      # Dependências Python
```

## 🐛 Troubleshooting

### Porta em uso

O script `dev.sh` automaticamente encontra uma porta livre entre 3200-3300 para o frontend.

### PostgreSQL não conecta

```bash
# Verificar se está rodando
docker ps | grep dumont-cloud-db

# Ver logs
docker logs dumont-cloud-db

# Reiniciar
docker restart dumont-cloud-db
```

### Backend não inicia

```bash
# Ver logs
tail -f /tmp/dumont-backend.log

# Verificar dependências
./venv/bin/pip list
```

### Limpar tudo e recomeçar

```bash
# Parar containers
docker-compose down

# Remover volumes (CUIDADO: apaga dados do banco!)
docker volume rm dumont-cloud-postgres-data

# Rodar novamente
./dev.sh
```

## 📚 Documentação

- **API Docs**: http://localhost:8767/docs (Swagger UI)
- **ReDoc**: http://localhost:8767/redoc

## 🚢 Deploy

TODO: Adicionar instruções de deploy para produção

## 📝 Licença

Proprietário - Dumont Cloud

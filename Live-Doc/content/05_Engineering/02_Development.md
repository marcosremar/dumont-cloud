# Guia de Desenvolvimento

## Setup Local

### Requisitos

- Python 3.9+
- Node.js 18+
- PostgreSQL 16
- Docker (opcional)

### Backend

```bash
# Clone
git clone https://github.com/dumontcloud/dumontcloud.git
cd dumontcloud

# Virtual env
python -m venv venv
source venv/bin/activate

# Dependencias
pip install -r requirements.txt

# Variaveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# Database
createdb dumontcloud
alembic upgrade head

# Iniciar
python -m src.main
# API em http://localhost:8767
```

### Frontend

```bash
cd web

# Dependencias
npm install

# Iniciar
npm run dev
# UI em http://localhost:3200
```

---

## Variaveis de Ambiente

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dumontcloud

# VAST.ai
VAST_API_KEY=your_key

# Cloudflare R2
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_ENDPOINT=xxx
R2_BUCKET=xxx

# GCP (CPU Standby)
GCP_CREDENTIALS={"type": "service_account"...}
GCP_ZONE=us-central1-a
GCP_MACHINE_TYPE=e2-standard-4

# LLM (AI Wizard)
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx

# Auth
SECRET_KEY=random_secret
JWT_SECRET=jwt_secret

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=xxx
MAIL_PASSWORD=xxx
```

---

## Testes

### Backend

```bash
# Todos os testes
pytest

# Com coverage
pytest --cov=src

# Apenas unit tests
pytest tests/unit/

# Apenas integration
pytest tests/integration/
```

### Frontend

```bash
cd web

# Unit tests
npm run test

# E2E com Playwright
npm run test:e2e
```

---

## Migrations

### Criar migration

```bash
alembic revision --autogenerate -m "add new table"
```

### Aplicar

```bash
alembic upgrade head
```

### Rollback

```bash
alembic downgrade -1
```

---

## Estrutura de Codigo

### API Endpoint

```python
# src/api/v1/instances.py
from fastapi import APIRouter, Depends
from src.domain.services import InstanceService

router = APIRouter(prefix="/instances", tags=["instances"])

@router.get("/")
async def list_instances(
    service: InstanceService = Depends()
):
    return await service.list_all()
```

### Domain Service

```python
# src/domain/services/instance_service.py
class InstanceService:
    def __init__(self, repo: InstanceRepository):
        self.repo = repo

    async def list_all(self) -> List[Instance]:
        return await self.repo.find_all()
```

### Repository

```python
# src/domain/repositories/instance_repository.py
class InstanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(self) -> List[Instance]:
        result = await self.session.execute(
            select(InstanceModel)
        )
        return result.scalars().all()
```

---

## Convencoes

### Commits

```
feat: add new feature
fix: bug fix
docs: documentation
refactor: code refactor
test: add tests
chore: maintenance
```

### Branches

```
main - producao
develop - desenvolvimento
feature/xxx - nova feature
fix/xxx - bug fix
```

### Code Style

- Python: Black + isort
- TypeScript: ESLint + Prettier
- Max line length: 100

---

## Docker

### Build

```bash
docker build -t dumontcloud .
```

### Run

```bash
docker-compose up -d
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8767:8767"
    environment:
      - DATABASE_URL=postgresql://...
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## Debugging

### Logs

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Processing instance", extra={"instance_id": id})
```

### API Docs

- Swagger: http://localhost:8767/docs
- ReDoc: http://localhost:8767/redoc

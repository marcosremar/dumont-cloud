# Dumont Cloud - Multi-stage Dockerfile
# Frontend (React/Vite) + Backend (FastAPI)

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

# Copiar arquivos de dependências
COPY web/package*.json ./
COPY web/bun.lock* ./

# Instalar dependências
RUN npm ci --legacy-peer-deps

# Copiar código fonte
COPY web/ ./

# Build do frontend
RUN npm run build

# ============================================
# Stage 2: Python Backend + Frontend estático
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte do backend
COPY src/ ./src/

# Copiar frontend buildado
COPY --from=frontend-builder /app/web/build ./web/build

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

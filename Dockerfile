# Dumont Cloud - Multi-stage Dockerfile
# Frontend (React/Vite) + Backend (FastAPI) + VS Code Server

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
# Stage 2: Python Backend + Frontend estático + VS Code Server
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema + code-server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    openssh-client \
    procps \
    && curl -fsSL https://code-server.dev/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Configurar code-server com senha
RUN mkdir -p /root/.config/code-server && \
    echo 'bind-addr: 0.0.0.0:8080' > /root/.config/code-server/config.yaml && \
    echo 'auth: password' >> /root/.config/code-server/config.yaml && \
    echo 'password: marcos123' >> /root/.config/code-server/config.yaml && \
    echo 'cert: false' >> /root/.config/code-server/config.yaml

# Copiar requirements e instalar dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte do backend
COPY src/ ./src/

# Copiar frontend buildado
COPY --from=frontend-builder /app/web/build ./web/build

# Criar diretório para dados persistentes
RUN mkdir -p /app/data && chmod 777 /app/data

# Volume para persistência
VOLUME /app/data

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000
ENV CONFIG_FILE=/app/data/config.json

# Expor portas (8000=API, 8080=VS Code Server)
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Script de entrada para rodar ambos serviços
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Comando para iniciar ambos serviços
CMD ["/bin/bash", "/app/start.sh"]

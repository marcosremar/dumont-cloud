# Dumont Cloud - Multi-stage Dockerfile
# Frontend (React/Vite) + Backend (FastAPI) + VS Code Server

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

COPY web/package*.json ./
COPY web/bun.lock* ./
RUN npm ci --legacy-peer-deps

COPY web/ ./
RUN npm run build

# ============================================
# Stage 2: Python Backend + Frontend + VS Code Server
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema + code-server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    procps \
    sudo \
    && curl -fsSL https://code-server.dev/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar code-server
RUN mkdir -p /root/.config/code-server && \
    printf 'bind-addr: 0.0.0.0:8080\nauth: password\npassword: Marcos+123\ncert: false\n' > /root/.config/code-server/config.yaml

# Copiar requirements e instalar dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte do backend
COPY src/ ./src/

# Copiar script de inicialização
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

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

# Expor portas
EXPOSE 8000 8080

# Health check (só verifica o backend principal)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Usar script para iniciar ambos serviços
CMD ["/app/start.sh"]

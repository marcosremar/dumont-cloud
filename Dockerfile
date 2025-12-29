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

# Instalar dependências do sistema + code-server + Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    procps \
    sudo \
    ca-certificates \
    gnupg \
    && curl -fsSL https://code-server.dev/install.sh | sh \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário ubuntu com privilégios de administrador
RUN useradd -m -s /bin/bash ubuntu \
    && echo "ubuntu:ubuntu" | chpasswd \
    && usermod -aG sudo ubuntu \
    && echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Instalar Claude Code para root
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && ln -sf /root/.claude/local/bin/claude /usr/local/bin/claude

# Instalar Claude Code para ubuntu também
RUN su - ubuntu -c 'curl -fsSL https://claude.ai/install.sh | bash'

# Configurar variáveis de ambiente GLOBAIS para todos os usuários
RUN echo 'export PATH="/usr/local/bin:/root/.claude/local/bin:$HOME/.claude/local/bin:$PATH"' > /etc/profile.d/claude.sh \
    && chmod +x /etc/profile.d/claude.sh \
    && echo 'PATH="/usr/local/bin:/root/.claude/local/bin:/home/ubuntu/.claude/local/bin:$PATH"' >> /etc/environment

# Adicionar ao .bashrc de root e ubuntu
RUN echo 'export PATH="/root/.claude/local/bin:$PATH"' >> /root/.bashrc \
    && echo 'export PATH="$HOME/.claude/local/bin:$PATH"' >> /home/ubuntu/.bashrc

# Configurar code-server para ambos usuários
RUN mkdir -p /root/.config/code-server && \
    printf 'bind-addr: 0.0.0.0:8080\nauth: password\npassword: Marcos+123\ncert: false\n' > /root/.config/code-server/config.yaml && \
    mkdir -p /home/ubuntu/.config/code-server && \
    printf 'bind-addr: 0.0.0.0:8080\nauth: password\npassword: Marcos+123\ncert: false\n' > /home/ubuntu/.config/code-server/config.yaml && \
    chown -R ubuntu:ubuntu /home/ubuntu

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

# Dar permissões ao usuário ubuntu no diretório /app
RUN chown -R ubuntu:ubuntu /app

# Volume para persistência
VOLUME /app/data

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000
ENV CONFIG_FILE=/app/data/config.json
ENV PATH="/root/.claude/local/bin:/home/ubuntu/.claude/local/bin:${PATH}"

# Expor portas
EXPOSE 8000 8080

# Health check (só verifica o backend principal)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Usar script para iniciar ambos serviços
CMD ["/app/start.sh"]

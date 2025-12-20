# 🌐 Configuração do Nginx para Dumont Cloud

## Status Atual

O arquivo `nginx_update.conf` está configurado corretamente com:
- ✅ Porta 8767 (FastAPI)
- ✅ Domínio `dumontcloud-local.orb.local` adicionado
- ✅ Rotas para `/admin/doc/live`, `/api/menu`, `/api/content/`

## Aplicar Configuração no Servidor

### Se o Nginx está rodando em outro servidor (produção):

1. **Copie o arquivo** `nginx_update.conf` para o servidor:
```bash
scp nginx_update.conf user@server:/tmp/
```

2. **No servidor**, execute:
```bash
# Copiar para sites-available
sudo cp /tmp/nginx_update.conf /etc/nginx/sites-available/dumontcloud

# Criar link simbólico (se não existir)
sudo ln -sf /etc/nginx/sites-available/dumontcloud /etc/nginx/sites-enabled/dumontcloud

# Testar configuração
sudo nginx -t

# Se OK, recarregar
sudo systemctl reload nginx
```

### Se quiser testar localmente (desenvolvimento):

O Vite já está configurado para fazer proxy de `/admin` e `/api` para `http://localhost:8767`.

**Acesse diretamente:**
- `http://localhost:5173/admin/doc/live` (via Vite dev server)
- `http://localhost:8767/admin/doc/live` (direto no FastAPI)

## Configuração Atual do nginx_update.conf

```nginx
server {
    server_name 28864630.dumontcloud.com dumontcloud.com dumontcloud-local.orb.local;

    # Marketing Live Docs (Proxy para aplicacao principal)
    location /admin/doc/live {
        proxy_pass http://127.0.0.1:8767/admin/doc/live;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Live Docs API endpoints
    location /api/menu {
        proxy_pass http://127.0.0.1:8767/api/menu;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/content/ {
        proxy_pass http://127.0.0.1:8767/api/content/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # ... resto da configuração ...
}
```

## URLs Disponíveis

### Durante Desenvolvimento:
- **Frontend (Vite)**: `http://localhost:5173`
- **Backend (FastAPI)**: `http://localhost:8767`
- **Live Doc**: `http://localhost:5173/admin/doc/live` ou `http://localhost:8767/admin/doc/live`
- **API Docs**: `http://localhost:8767/docs`

### Via Nginx (Produção):
- **Live Doc**: `http://dumontcloud-local.orb.local/admin/doc/live`
- **Live Doc**: `https://dumontcloud.com/admin/doc/live`

## Notas Importantes

⚠️ **O Nginx não está instalado localmente**. Este é um ambiente de desenvolvimento local. Para acessar o Live Doc:

1. Use `http://localhost:5173/admin/doc/live` (via Vite proxy)
2. Ou use `http://localhost:8767/admin/doc/live` (direto no FastAPI)

Para aplicar a configuração do Nginx, você precisa estar no servidor onde o Nginx está rodando (provavelmente o servidor de produção com IP `79.112.1.66` ou similar).

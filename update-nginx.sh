#!/bin/bash
# Script para atualizar configuração do Nginx com as configurações do Dumont Cloud

echo "🔄 Atualizando configuração do Nginx..."
echo ""

NGINX_CONF="/home/marcos/dumontcloud/nginx_update.conf"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available/dumontcloud"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled/dumontcloud"

# Verificar se o arquivo de configuração existe
if [ ! -f "$NGINX_CONF" ]; then
    echo "❌ Arquivo de configuração não encontrado: $NGINX_CONF"
    exit 1
fi

echo "📋 Arquivo de configuração encontrado: $NGINX_CONF"
echo ""

# Copiar configuração para sites-available
echo "📝 Copiando configuração para $NGINX_SITES_AVAILABLE..."
sudo cp "$NGINX_CONF" "$NGINX_SITES_AVAILABLE"

# Criar link simbólico em sites-enabled se não existir
if [ ! -L "$NGINX_SITES_ENABLED" ]; then
    echo "🔗 Criando link simbólico em sites-enabled..."
    sudo ln -s "$NGINX_SITES_AVAILABLE" "$NGINX_SITES_ENABLED"
else
    echo "✓ Link simbólico já existe"
fi

# Testar configuração do Nginx
echo ""
echo "🧪 Testando configuração do Nginx..."
if sudo nginx -t; then
    echo ""
    echo "✅ Configuração válida!"
    echo ""
    echo "🔄 Recarregando Nginx..."
    sudo systemctl reload nginx
    echo ""
    echo "✅ Nginx recarregado com sucesso!"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Você pode acessar o Live Doc em:"
    echo "  • http://dumontcloud-local.orb.local/admin/doc/live"
    echo "  • https://dumontcloud.com/admin/doc/live"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
else
    echo ""
    echo "❌ Erro na configuração do Nginx!"
    echo "   Revise o arquivo e tente novamente."
    exit 1
fi

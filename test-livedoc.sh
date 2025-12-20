#!/bin/bash
# Test Dumont Cloud Live-Doc via Nginx

echo "🧪 Testando Live-Doc via Nginx na porta 80..."
echo ""

# Test localhost
echo "📍 Teste 1: http://localhost/admin/doc/live"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/doc/live)
if [ "$STATUS" = "200" ]; then
    echo "   ✅ Funcionando (HTTP $STATUS)"
else
    echo "   ❌ Falhou (HTTP $STATUS)"
fi
echo ""

# Test API menu
echo "📍 Teste 2: http://localhost/api/menu"
MENU=$(curl -s http://localhost/api/menu | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['menu'][0]['name'] if data.get('menu') else 'ERROR')" 2>/dev/null)
if [ -n "$MENU" ] && [ "$MENU" != "ERROR" ]; then
    echo "   ✅ API funcionando - Primeiro item: $MENU"
else
    echo "   ❌ API com erro"
fi
echo ""

# Test domain resolution
echo "📍 Teste 3: Resolução do domínio dumontcloud-local.orb.local"
HOST_RESULT=$(getent hosts dumontcloud-local.orb.local 2>/dev/null)
if [ -n "$HOST_RESULT" ]; then
    echo "   ✅ Domínio resolve para: $HOST_RESULT"
else
    echo "   ❌ Domínio não resolve"
fi
echo ""

# Check services
echo "📊 Status dos Serviços:"
echo ""
echo "  Nginx:   $(systemctl is-active nginx)"
echo "  FastAPI: $(if pgrep -f 'uvicorn.*8767' > /dev/null; then echo 'active'; else echo 'inactive'; fi)"
echo "  Vite:    $(if pgrep -f 'vite.*5173' > /dev/null; then echo 'active'; else echo 'inactive'; fi)"
echo "  LiveDoc: $(if pgrep -f 'server.py.*8081' > /dev/null; then echo 'active'; else echo 'inactive'; fi)"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ URLs disponíveis:"
echo ""
echo "  • http://localhost/admin/doc/live"
echo "  • http://dumontcloud-local.orb.local/admin/doc/live"
echo "  • http://localhost/ (Frontend React)"
echo ""
echo "════════════════════════════════════════════════════════════════"

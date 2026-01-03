# Chat Arena - Comandos Úteis

## Gerenciamento de Instâncias VAST.ai

### Verificar status dos modelos deployados
```bash
python3 scripts/test_chat_arena.py
```

### Testar conexão SSH com os modelos
```bash
# Llama 3.2 3B (RTX 3080)
ssh -p 19056 root@ssh9.vast.ai "curl -s http://localhost:11434/api/tags"

# Qwen 2.5 3B (RTX 3060)
ssh -p 19112 root@ssh7.vast.ai "curl -s http://localhost:11434/api/tags"
```

### Fazer query diretamente no modelo
```bash
# Llama 3.2 3B
ssh -p 19056 root@ssh9.vast.ai "ollama run llama3.2:3b 'Hello, how are you?'"

# Qwen 2.5 3B
ssh -p 19112 root@ssh7.vast.ai "ollama run qwen2.5:3b 'Hello, how are you?'"
```

### Destruir as instâncias (PARAR BILLING)
```bash
python3 scripts/deploy_chat_arena_models.py --cleanup
```

## Criar SSH Tunnels para Testes Locais

### Criar tunnels
```bash
# Tunnel para Llama (porta local 11434)
ssh -f -N -L 11434:localhost:11434 -p 19056 root@ssh9.vast.ai

# Tunnel para Qwen (porta local 11435)
ssh -f -N -L 11435:localhost:11434 -p 19112 root@ssh7.vast.ai
```

### Testar tunnels
```bash
# Testar Llama
curl http://localhost:11434/api/tags

# Testar Qwen
curl http://localhost:11435/api/tags
```

### Fechar tunnels
```bash
# Matar processos nas portas
lsof -ti:11434 | xargs kill -9
lsof -ti:11435 | xargs kill -9
```

## Testes E2E com Playwright

### Rodar teste demo (com mocks)
```bash
npx playwright test tests/chat-arena-interactive.spec.js --headed
```

### Rodar teste REAL (com SSH tunnels)
```bash
# Primeiro, criar os SSH tunnels (ver comandos acima)

# Depois rodar o teste
npx playwright test tests/chat-arena-real-direct.spec.js --headed
```

### Ver relatórios dos testes
```bash
# Abrir relatório HTML do Playwright
npx playwright show-report

# Ver relatório JSON
cat tests/CHAT_ARENA_TEST_REPORT.json | jq '.'
```

## Verificar Custos

### Ver deployment info
```bash
cat chat_arena_deployment.json | jq '.total_cost_per_hour, .instances[].model_name'
```

### Calcular custo estimado
```bash
# Para X horas
echo "scale=4; 0.0874 * X" | bc

# Para 24h (1 dia)
echo "scale=4; 0.0874 * 24" | bc

# Para 30 dias
echo "scale=4; 0.0874 * 24 * 30" | bc
```

## API Endpoints (Backend)

### Listar modelos disponíveis
```bash
# Com autenticação
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/chat/models
```

### Testar Ollama diretamente
```bash
# Via SSH tunnel local
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

## Logs e Debug

### Ver logs do Ollama nas instâncias
```bash
# Llama
ssh -p 19056 root@ssh9.vast.ai "docker logs ollama"

# Qwen
ssh -p 19112 root@ssh7.vast.ai "docker logs ollama"
```

### Verificar recursos (GPU, RAM, etc.)
```bash
# Llama
ssh -p 19056 root@ssh9.vast.ai "nvidia-smi"

# Qwen
ssh -p 19112 root@ssh7.vast.ai "nvidia-smi"
```

## Manutenção

### Atualizar modelo Ollama
```bash
ssh -p PORT root@HOST "ollama pull MODEL_NAME:TAG"

# Exemplo - Llama
ssh -p 19056 root@ssh9.vast.ai "ollama pull llama3.2:3b"
```

### Listar modelos instalados
```bash
ssh -p 19056 root@ssh9.vast.ai "ollama list"
```

### Remover modelo
```bash
ssh -p 19056 root@ssh9.vast.ai "ollama rm MODEL_NAME"
```

## Troubleshooting

### Problema: "Connection refused" ao acessar Ollama
```bash
# Verificar se Ollama está rodando
ssh -p PORT root@HOST "ps aux | grep ollama"

# Verificar porta
ssh -p PORT root@HOST "netstat -tlnp | grep 11434"

# Reiniciar Ollama
ssh -p PORT root@HOST "systemctl restart ollama"
```

### Problema: "Model not found"
```bash
# Baixar modelo novamente
ssh -p PORT root@HOST "ollama pull MODEL_NAME"
```

### Problema: SSH timeout
```bash
# Verificar se instância está online no VAST.ai
curl -s -H "Authorization: Bearer VAST_API_KEY" \
  https://console.vast.ai/api/v0/instances/ | jq '.instances[] | {id, status}'
```

## Arquivos de Configuração

- `chat_arena_deployment.json` - Info do deployment atual
- `scripts/deploy_chat_arena_models.py` - Script de deploy
- `scripts/test_chat_arena.py` - Script de teste
- `tests/chat-arena-*.spec.js` - Testes E2E Playwright
- `.env` - Credenciais (VAST_API_KEY)

## Links Úteis

- VAST.ai Console: https://cloud.vast.ai/
- Ollama Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
- Chat Arena UI: http://localhost:4894/app/chat-arena

## Notas Importantes

- As instâncias VAST.ai cobram por HORA, mesmo quando idle
- Sempre destrua instâncias com `--cleanup` quando terminar os testes
- SSH keys são gerenciadas automaticamente pelo script de deploy
- Porta 11434 é a porta padrão do Ollama
- Modelos 3B cabem confortavelmente em GPUs com 8GB+ VRAM

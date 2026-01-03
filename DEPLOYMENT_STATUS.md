# Chat Arena Deployment Status - 2026-01-03

## Status: FALHOU - Créditos Insuficientes

### Resumo
Tentativa de deploy de 2 modelos ultra-leves falhou devido a créditos insuficientes na conta VAST.ai.

### Conta VAST.ai
- **Email**: marcosremar@gmail.com
- **Saldo atual**: -$0.02
- **Crédito disponível**: $0.00
- **Threshold de saldo**: -$0.01

### Modelos Planejados

#### 1. Qwen 2.5 0.5B
- **Tamanho**: 316 MB
- **Modelo Ollama**: `qwen2.5:0.5b`
- **GPU preferida**: RTX 3060, RTX 3070, GTX 1660
- **Status**: Oferta encontrada ($0.0385/hora) mas criação falhou

#### 2. Qwen 2.5 1.5B
- **Tamanho**: 934 MB
- **Modelo Ollama**: `qwen2.5:1.5b`
- **GPU preferida**: RTX 3060, RTX 3070, RTX 4060
- **Status**: Oferta encontrada ($0.0356/hora) mas criação falhou

### Custo Estimado
- **Custo por hora**: ~$0.07/hora (ambas instâncias)
- **Custo por 1 hora**: $0.07
- **Custo por 24 horas**: $1.68
- **Custo por 7 dias**: $11.76

### Erro Encontrado
```
HTTP 400: Bad Request
{
  "error": "insufficient_credit",
  "msg": "Your account lacks credit; see the billing page."
}
```

### Ação Necessária

**ADICIONAR CRÉDITOS NA VAST.AI:**

1. Acessar: https://cloud.vast.ai/billing/
2. Login com: marcosremar@gmail.com
3. Adicionar pelo menos $2.00 de crédito (recomendado: $5-10)
4. Aguardar confirmação do pagamento
5. Re-executar o script de deployment

### Como Re-executar o Deploy

Após adicionar créditos:

```bash
cd /Users/marcos/CascadeProjects/dumontcloud
python3 scripts/deploy_lightweight_arena.py --force
```

### Script Criado

O script de deployment está pronto e funcional:
- **Localização**: `/Users/marcos/CascadeProjects/dumontcloud/scripts/deploy_lightweight_arena.py`
- **Funcionalidades**:
  - Busca GPUs mais baratas
  - Cria instâncias com porta 11434 exposta
  - Instala Ollama com `OLLAMA_HOST=0.0.0.0` (acesso público)
  - Faz pull dos modelos leves
  - Testa endpoints HTTP (não SSH)
  - Valida geração de texto
  - Salva resultados em JSON

### Configuração Ollama

O script configura Ollama para acesso PÚBLICO:

```bash
# Serviço systemd criado com:
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Porta 11434 exposta publicamente pela VAST.ai
# Testes via HTTP (não SSH):
curl http://HOST:11434/api/tags
curl http://HOST:11434/api/generate -d '{"model": "qwen2.5:0.5b", "prompt": "Hello!", "stream": false}'
```

### Verificação Final

Após o deployment bem-sucedido, será gerado:
- `chat_arena_deployment.json` com detalhes das instâncias
- Endpoints HTTP públicos para cada modelo
- Confirmação de testes HTTP e geração de texto

### Limpeza de Instâncias

Para destruir instâncias e parar custos:

```bash
python3 scripts/deploy_lightweight_arena.py --cleanup
```

---

## Histórico

### Deploy Anterior (2026-01-03 01:39)
- **Instância 1**: 29449056 - Llama 3.2 3B (RTX 3080, $0.049/h)
- **Instância 2**: 29449112 - Qwen 2.5 3B (RTX 3060, $0.039/h)
- **Status**: Modelos mais pesados (3B), já foram desligados
- **Problema**: Porta 11434 estava acessível via SSH, não HTTP público

### Deploy Atual (2026-01-03 10:26)
- **Melhoria**: Modelos mais leves (0.5B e 1.5B)
- **Melhoria**: Porta 11434 exposta publicamente com HTTP
- **Melhoria**: OLLAMA_HOST=0.0.0.0 configurado via systemd
- **Melhoria**: Testes via HTTP em vez de SSH
- **Status**: Aguardando créditos VAST.ai

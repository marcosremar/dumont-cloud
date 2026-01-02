# Quick Start: Testes de Failover REAIS

**Tempo de leitura:** 2 minutos  
**Tempo de execução:** 15-20 minutos  
**Custo:** ~$0.03-0.05

---

## ⚡ Execução Rápida

### 1. Configurar ambiente (1 vez apenas)

```bash
cd /Users/marcos/CascadeProjects/dumontcloud

# Configurar variáveis
export VAST_API_KEY="your_vast_api_key_here"
export B2_ENDPOINT="https://s3.us-west-004.backblazeb2.com"
export B2_BUCKET="dumoncloud-snapshot"

# Iniciar backend (em outro terminal)
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8766
```

### 2. Executar testes

```bash
# Testes COMPLETOS (cria GPUs reais - CUSTA $$$)
./run_failover_tests.sh

# Ou apenas dry-run (mostra o que seria feito)
./run_failover_tests.sh --dry-run
```

### 3. Ver resultados

Os testes exibem progresso em tempo real e geram relatório ao final.

---

## 📝 O que os testes fazem

1. ✅ Provisiona GPU real ($0.32/hr)
2. ✅ Cria 3 arquivos de teste
3. ✅ Calcula MD5 de cada arquivo
4. ✅ Cria snapshot em B2
5. ✅ Provisiona NOVA GPU (failover)
6. ✅ Restaura snapshot
7. ✅ Valida MD5 de todos arquivos
8. ✅ Deleta GPUs automaticamente

**Validação:** Se todos MD5 baterem, dados foram transferidos com sucesso!

---

## 🎯 Exemplo de Saída

```
======================================================================
  DUMONT CLOUD - BATERIA DE TESTES DE FAILOVER REAIS
======================================================================

[1/7] Verificando pré-requisitos...
✓ Variáveis de ambiente OK
  VAST_API_KEY: abc123...
  B2_ENDPOINT: https://s3.us-west-004.backblazeb2.com

[2/7] Verificando backend...
✓ Backend acessível

[3/7] Ativando ambiente virtual...
✓ Ambiente virtual ativado

[4/7] Verificando dependências...
✓ Dependências instaladas

[5/7] Verificando saldo VAST.ai...
✓ Saldo disponível: $5.23

[6/7] Executando testes de failover...

ATENÇÃO: Testes COMPLETOS - VAI CRIAR GPUS REAIS!

Estimativa de custo: ~$0.10 - $0.50
Tempo estimado: 15-30 minutos

Continuar? (yes/no): yes

... (testes executam) ...

✓ Testes concluídos com sucesso!
  Tempo total: 176s

[7/7] Gerando relatório...
✓ Métricas salvas em: cli/tests/failover_test_metrics.json

Resumo das métricas:
  Teste: real_time_sync_failover
  Sucesso: True
  Arquivos validados: 3/3
  Tempo total: 176.4s
  Custo estimado: $0.0314

======================================================================
  TESTES CONCLUÍDOS
======================================================================
```

---

## 🛠️ Troubleshooting Rápido

### Erro: "Backend não está rodando"

```bash
# Terminal 1: Iniciar backend
cd /Users/marcos/CascadeProjects/dumontcloud
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8766

# Terminal 2: Executar testes
./run_failover_tests.sh
```

### Erro: "VAST_API_KEY não configurado"

```bash
export VAST_API_KEY="your_key_here"
./run_failover_tests.sh
```

### Erro: "No GPU offers available"

- Verificar saldo: `curl -H "Authorization: Bearer $VAST_API_KEY" https://cloud.vast.ai/api/v0/users/current/`
- Tentar novamente em 5 minutos (alta demanda)

---

## 📚 Documentação Completa

- **Guia completo:** `FAILOVER_TESTING_GUIDE.md`
- **Sumário:** `FAILOVER_TESTS_SUMMARY.md`
- **Sistema de failover:** `docs/FAILOVER_SYSTEM.md`

---

## ✅ Checklist Rápido

Antes de executar:

- [ ] VAST_API_KEY configurado
- [ ] Backend rodando (`curl http://localhost:8766/health`)
- [ ] Saldo VAST.ai > $1.00
- [ ] B2 credentials configurados (se usar snapshots)

---

**Pronto!** Execute `./run_failover_tests.sh` e aguarde os resultados.

**Tempo:** ~15-20 minutos  
**Custo:** ~$0.03-0.05  
**Validação:** 100% automática

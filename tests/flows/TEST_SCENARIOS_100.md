# 100 Cenários de Teste E2E - Dumont Cloud GPU Platform

> Todos os testes usam GPUs REAIS no VAST.ai. Custo estimado: ~$5-10 para rodar todos.

---

## CATEGORIA 1: Ciclo de Vida de Instâncias (15 testes)

### Básicos
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 1 | Criar instância RTX 4090 | Sim | Provisionar RTX 4090, verificar SSH, destruir |
| 2 | Criar instância RTX 3080 barata | Sim | Buscar oferta mais barata, criar, verificar |
| 3 | Criar instância com imagem custom | Sim | Usar pytorch/pytorch, verificar CUDA |
| 4 | Criar instância multi-GPU | Sim | Provisionar 2x RTX 3090, verificar ambas GPUs |
| 5 | Criar instância em região específica | Sim | Forçar região EU, verificar geolocalização |

### Pause/Resume
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 6 | Pause e resume simples | Sim | Criar, pausar, verificar stopped, resumir, verificar running |
| 7 | Pause com verificação de dados | Sim | Criar arquivo, pausar, resumir, verificar arquivo existe |
| 8 | Resume após 5 minutos paused | Sim | Pausar, esperar 5min, resumir, medir tempo cold start |
| 9 | Múltiplos pause/resume | Sim | Ciclo de 3 pause/resume, verificar estabilidade |
| 10 | Pause durante execução de processo | Sim | Rodar script, pausar durante, resumir, verificar estado |

### Destruição e Limpeza
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 11 | Destruir instância running | Sim | Criar, verificar running, destruir imediatamente |
| 12 | Destruir instância paused | Sim | Criar, pausar, destruir enquanto paused |
| 13 | Destruir com cleanup de volumes | Sim | Criar com disco grande, destruir, verificar sem custos residuais |
| 14 | Criar mesma oferta após destruir | Sim | Criar, destruir, recriar mesma oferta |
| 15 | Destruição em lote | Sim | Criar 3 instâncias, destruir todas em paralelo |

---

## CATEGORIA 2: Serverless GPU (12 testes)

### Ativação e Configuração
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 16 | Ativar modo serverless | Sim | Criar instância, ativar serverless, verificar config |
| 17 | Serverless modo FAST | Sim | Ativar com CPU standby, verificar sync ativo |
| 18 | Serverless modo ECONOMIC | Sim | Ativar sem standby, verificar pause nativo |
| 19 | Configurar threshold de idle | Sim | Setar idle_threshold=30s, verificar aplicado |
| 20 | Desativar serverless | Sim | Ativar, desativar, verificar instância continua running |

### Auto-Pause
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 21 | Auto-pause após idle | Sim | Deixar GPU idle 60s, verificar auto-pause |
| 22 | Manter ativo com uso GPU | Sim | Rodar stress test, verificar não pausa |
| 23 | Auto-pause com grace period | Sim | Nova instância, verificar grace period respeitado |
| 24 | Métricas de economia | Sim | Usar serverless 10min, verificar savings calculado |

### Cold Start
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 25 | Medir cold start FAST mode | Sim | Pausar, medir tempo até SSH disponível |
| 26 | Medir cold start ECONOMIC | Sim | Pausar nativo, medir tempo de resume |
| 27 | Cold start com modelo carregado | Sim | Instalar Ollama, pausar, resumir, verificar modelo |

---

## CATEGORIA 3: Failover e Alta Disponibilidade (15 testes)

### CPU Standby
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 28 | Criar CPU standby automático | Sim | Criar GPU, verificar standby GCP criado |
| 29 | Sync inicial para standby | Sim | Criar arquivos na GPU, verificar sync no standby |
| 30 | Failover para CPU standby | Sim | Simular falha GPU, verificar failover funciona |
| 31 | Tempo de failover < 5s | Sim | Medir tempo desde detecção até standby ativo |
| 32 | Failback para GPU | Sim | Após failover, reprovisionar GPU, sync reverso |

### Warm Pool
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 33 | Provisionar warm pool | Sim | Criar volume regional para warm pool |
| 34 | Failover via warm pool | Sim | Simular falha, failover para warm pool GPU |
| 35 | Health check warm pool | Sim | Verificar saúde do warm pool ativo |
| 36 | Multi-região warm pool | Sim | Criar warm pool em EU e US |
| 37 | Deprovision warm pool | Sim | Remover warm pool, verificar cleanup |

### Recuperação
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 38 | Recovery cold start | Sim | Sem standby, simular falha, medir recovery |
| 39 | Validação pós-failover | Sim | Após failover, rodar inference test |
| 40 | Failover durante treinamento | Sim | Iniciar job, forçar failover, verificar checkpoint |
| 41 | Múltiplos failovers sequenciais | Sim | 3 failovers em 10 minutos |
| 42 | Failover com dados grandes | Sim | 10GB de dados, verificar sync completo |

---

## CATEGORIA 4: Snapshots e Backups (10 testes)

### Criação
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 43 | Snapshot full | Sim | Criar instância com dados, snapshot full |
| 44 | Snapshot incremental | Sim | Modificar arquivos, snapshot incremental |
| 45 | Snapshot de instância paused | Sim | Pausar, criar snapshot, verificar sucesso |
| 46 | Múltiplos snapshots | Sim | Criar 3 snapshots sequenciais |

### Restore
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 47 | Restore para nova instância | Sim | Snapshot, destruir, restore em nova GPU |
| 48 | Restore parcial | Sim | Restore apenas diretório específico |
| 49 | Restore para GPU diferente | Sim | Snapshot RTX 3080, restore em RTX 4090 |
| 50 | Verificar integridade após restore | Sim | MD5 de arquivos antes/depois |

### Gerenciamento
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 51 | Listar snapshots | Sim | Verificar listagem correta |
| 52 | Prune snapshots antigos | Sim | Criar vários, prune, verificar retenção |

---

## CATEGORIA 5: Jobs e Execução (12 testes)

### Criação e Execução
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 53 | Job simples - comando bash | Sim | Executar `nvidia-smi`, capturar output |
| 54 | Job Python com GPU | Sim | Script PyTorch usando CUDA |
| 55 | Job com timeout | Sim | Job de 5min com timeout 2min |
| 56 | Job com output para storage | Sim | Salvar resultados em B2 |
| 57 | Job spot instance | Sim | Executar em spot, verificar economia |

### Gerenciamento
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 58 | Cancelar job em execução | Sim | Iniciar job longo, cancelar após 30s |
| 59 | Obter logs de job | Sim | Job com prints, verificar logs completos |
| 60 | Job com dependências | Sim | Instalar pip packages, executar |
| 61 | Job multi-GPU | Sim | Distributed training em 2 GPUs |

### Cleanup
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 62 | Auto-destroy após job | Sim | Job termina, GPU destruída automaticamente |
| 63 | Cleanup após falha | Sim | Job com erro, verificar cleanup correto |
| 64 | Job retry após falha | Sim | Job falha, retry automático |

---

## CATEGORIA 6: Deploy de Modelos (12 testes)

### LLM
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 65 | Deploy Llama 3.2 1B | Sim | Deploy modelo pequeno, testar inference |
| 66 | Deploy com quantização INT4 | Sim | Modelo quantizado, verificar funcionamento |
| 67 | Deploy vLLM | Sim | Usar vLLM backend, medir throughput |
| 68 | Chat completion API | Sim | Testar endpoint /v1/chat/completions |

### Whisper
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 69 | Deploy Whisper base | Sim | Deploy, transcrever áudio de teste |
| 70 | Deploy Whisper large | Sim | Modelo grande, verificar VRAM |
| 71 | Transcrição em lote | Sim | 10 áudios sequenciais |

### Outros Modelos
| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 72 | Deploy Stable Diffusion | Sim | Gerar imagem de teste |
| 73 | Deploy embeddings | Sim | Sentence-transformers, testar embedding |
| 74 | Deploy modelo custom HuggingFace | Sim | Modelo do Hub, deploy automático |
| 75 | Scale up modelo | Sim | Aumentar réplicas, verificar load balancing |
| 76 | Health check de modelo | Sim | Verificar endpoint /health |

---

## CATEGORIA 7: Fine-Tuning (8 testes)

| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 77 | Fine-tune Llama com Unsloth | Sim | Dataset pequeno, 100 steps |
| 78 | Upload dataset JSONL | Sim | Upload, validar formato |
| 79 | Fine-tune com checkpoints | Sim | Salvar checkpoint a cada 50 steps |
| 80 | Cancelar fine-tune | Sim | Iniciar, cancelar, verificar cleanup |
| 81 | Obter logs de treinamento | Sim | Loss, métricas em tempo real |
| 82 | Export modelo fine-tuned | Sim | Salvar para B2 |
| 83 | Fine-tune multi-GPU | Sim | Distributed em 2 GPUs |
| 84 | Resumir fine-tune de checkpoint | Sim | Parar, resumir de checkpoint |

---

## CATEGORIA 8: Market e Preços (6 testes)

| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 85 | Buscar ofertas por preço | Não* | Filtrar < $0.20/hr |
| 86 | Comparar preços entre regiões | Não* | US vs EU vs Asia |
| 87 | Previsão de preço | Não* | ML prediction próximas 24h |
| 88 | Ranking de reliability | Não* | Top 10 hosts mais confiáveis |
| 89 | Spot vs On-demand | Sim | Criar ambos, comparar custo real |
| 90 | Monitorar preço em tempo real | Não* | WebSocket de preços |

*Não requer GPU para o teste em si, mas valida dados de GPUs reais

---

## CATEGORIA 9: Migração e Otimização (5 testes)

| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 91 | Migrar para GPU mais barata | Sim | Detectar oferta melhor, migrar |
| 92 | Migrar para região diferente | Sim | US -> EU com dados |
| 93 | Migrar preservando IP | Sim | Migrar mantendo mesmo SSH host |
| 94 | Estimativa de migração | Sim | Calcular tempo/custo antes |
| 95 | Migração com modelo carregado | Sim | Ollama rodando, migrar sem perder |

---

## CATEGORIA 10: Cenários de Erro e Edge Cases (5 testes)

| # | Cenário | GPU Real | Descrição |
|---|---------|----------|-----------|
| 96 | Retry após oferta expirada | Sim | Tentar oferta antiga, retry automático |
| 97 | Blacklist de host problemático | Sim | Falhar em host, verificar blacklist |
| 98 | Recuperar de disk full | Sim | Encher disco, limpar, recuperar |
| 99 | Timeout de criação | Sim | Oferta lenta, verificar timeout handling |
| 100 | Concurrent creates | Sim | 3 creates simultâneos, sem conflito |

---

## Resumo de Custos

| Categoria | Testes | GPU-Minutos | Custo Est. |
|-----------|--------|-------------|------------|
| Instâncias | 15 | 45 | $0.75 |
| Serverless | 12 | 60 | $1.00 |
| Failover | 15 | 90 | $1.50 |
| Snapshots | 10 | 30 | $0.50 |
| Jobs | 12 | 36 | $0.60 |
| Models | 12 | 60 | $1.00 |
| Fine-tune | 8 | 80 | $1.35 |
| Market | 6 | 10 | $0.15 |
| Migração | 5 | 25 | $0.40 |
| Edge Cases | 5 | 25 | $0.40 |
| **TOTAL** | **100** | **461 min** | **~$7.65** |

---

## Implementação

Cada teste deve:
1. Criar recursos necessários
2. Executar cenário
3. Verificar resultado esperado
4. **DESTRUIR todos os recursos criados**
5. Verificar cleanup completo

### Marcadores pytest:
- `@pytest.mark.real_gpu` - Requer GPU real
- `@pytest.mark.slow` - > 2 minutos
- `@pytest.mark.cost_high` - > $0.10 por execução
- `@pytest.mark.failover` - Testes de failover
- `@pytest.mark.model` - Deploy de modelos

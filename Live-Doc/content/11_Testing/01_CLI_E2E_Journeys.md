# CLI E2E Journey Tests

Documentacao completa dos testes de jornada end-to-end para o Dumont CLI. Estes testes validam fluxos completos de usuario, desde autenticacao ate operacoes complexas de infraestrutura GPU.

---

## Visao Geral

Os testes E2E do CLI cobrem **10 jornadas principais** que representam os casos de uso mais comuns da plataforma Dumont Cloud.

| # | Journey | Descricao | Criticidade |
|---|---------|-----------|-------------|
| 1 | Autenticacao | Login, sessao, logout | Alta |
| 2 | Ciclo de Vida GPU | Criar, gerenciar, destruir | Alta |
| 3 | Backup e Restore | Snapshots e recuperacao | Alta |
| 4 | CPU Standby | Failover e resiliencia | Media |
| 5 | Fine-Tuning | Treinar modelos LLM | Media |
| 6 | Analise Spot | Previsao e monitoramento | Baixa |
| 7 | Tracking Economia | ROI e savings | Baixa |
| 8 | Deploy com IA | Wizard inteligente | Media |
| 9 | Migracao | GPU para CPU e vice-versa | Media |
| 10 | Health Check | Monitoramento do sistema | Alta |

---

## Journey 1: Autenticacao Completa

**Objetivo:** Validar ciclo completo de autenticacao JWT.

**Pre-requisitos:**
- Backend rodando em `localhost:8767`
- Usuario registrado no sistema

### Comandos

```bash
# 1. Login com credenciais
dumont auth login user@email.com password
# Esperado: Token salvo em ~/.dumont_token

# 2. Verificar sessao ativa
dumont auth me
# Esperado: JSON com dados do usuario autenticado

# 3. Acessar recurso protegido
dumont setting list
# Esperado: Lista de configuracoes do usuario

# 4. Logout
dumont auth logout
# Esperado: Token removido

# 5. Tentar acessar sem autenticacao
dumont auth me
# Esperado: Erro 401 Unauthorized
```

### Validacoes

| Step | Comando | Status Esperado | Validacao |
|------|---------|-----------------|-----------|
| 1 | auth login | 200 | Token salvo |
| 2 | auth me | 200 | email presente |
| 3 | setting list | 200 | settings presentes |
| 4 | auth logout | 200 | Token removido |
| 5 | auth me | 401 | Unauthorized |

---

## Journey 2: Ciclo de Vida de Instancia GPU

**Objetivo:** Validar fluxo completo de criacao, gerenciamento e destruicao de GPU.

**Pre-requisitos:**
- Usuario autenticado
- API key Vast.ai configurada
- Saldo disponivel

### Comandos

```bash
# 1. Pesquisar GPUs disponiveis
dumont instance offers
# Esperado: Lista de ofertas com precos

# 2. Filtrar por GPU especifica
dumont instance offers gpu_name=rtx4090 max_price=0.50
# Esperado: Ofertas filtradas

# 3. Criar instancia
dumont instance create offer_id=<ID> label=test-gpu disk_size=100
# Esperado: Instancia criada com ID

# 4. Listar instancias
dumont instance list
# Esperado: Nova instancia na lista

# 5. Obter detalhes
dumont instance get <instance_id>
# Esperado: Detalhes completos da instancia

# 6. Pausar instancia
dumont instance pause <instance_id>
# Esperado: Status "paused"

# 7. Retomar instancia
dumont instance resume <instance_id>
# Esperado: Status "running"

# 8. Destruir instancia
dumont instance delete <instance_id>
# Esperado: Instancia removida

# 9. Confirmar destruicao
dumont instance list
# Esperado: Instancia nao aparece mais
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 1 | offers | 200 | count > 0 |
| 2 | offers filtrado | 200 | gpu_name match |
| 3 | create | 201 | id retornado |
| 4 | list | 200 | instancia presente |
| 5 | get | 200 | todos campos |
| 6 | pause | 200 | success: true |
| 7 | resume | 200 | success: true |
| 8 | delete | 200 | success: true |
| 9 | list | 200 | instancia ausente |

---

## Journey 3: Backup e Restore

**Objetivo:** Validar persistencia de dados com snapshots.

**Pre-requisitos:**
- Instancia GPU ativa
- Storage configurado (R2/Restic)

### Comandos

```bash
# 1. Criar instancia para teste
dumont instance create offer_id=<ID> label=backup-test

# 2. Sincronizar dados (apos trabalhar na instancia)
dumont instance sync <instance_id>
# Esperado: Snapshot incremental criado

# 3. Criar snapshot nomeado
dumont snapshot create backup-v1 <instance_id>
# Esperado: Snapshot com ID unico

# 4. Listar snapshots
dumont snapshot list
# Esperado: backup-v1 na lista

# 5. Destruir instancia original
dumont instance delete <instance_id>

# 6. Restaurar em nova GPU
dumont snapshot restore <snapshot_id> gpu_name=rtx4090
# Esperado: Nova instancia com dados restaurados

# 7. Verificar restauracao
dumont instance list
# Esperado: Nova instancia ativa

# 8. Limpar snapshot
dumont snapshot delete <snapshot_id>
# Esperado: Snapshot removido
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 2 | sync | 200 | snapshot_id presente |
| 3 | snapshot create | 201 | id retornado |
| 4 | snapshot list | 200 | backup-v1 presente |
| 6 | restore | 200 | new_instance_id |
| 8 | delete | 200 | success: true |

---

## Journey 4: CPU Standby e Failover

**Objetivo:** Validar resiliencia com CPU standby automatico.

**Pre-requisitos:**
- Credenciais GCP configuradas
- Auto-standby habilitado

### Comandos

```bash
# 1. Verificar status inicial
dumont standby status
# Esperado: configured: false ou true

# 2. Configurar auto-standby
dumont standby configure enabled=true gcp_zone=europe-west1-b
# Esperado: Auto-standby ativado

# 3. Criar GPU (auto-cria CPU standby)
dumont instance create offer_id=<ID> label=resilient-gpu

# 4. Verificar associacoes
dumont standby associations
# Esperado: Par GPU <-> CPU criado

# 5. Iniciar sincronizacao
dumont standby sync-start <gpu_instance_id>
# Esperado: Sync iniciado

# 6. Simular falha GPU (destroy com reason)
dumont instance delete <gpu_id> reason=gpu_failure destroy_standby=false
# Esperado: GPU destruida, CPU mantida

# 7. Verificar CPU standby ativo
dumont standby status
# Esperado: CPU standby disponivel para restore
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 2 | configure | 200 | enabled: true |
| 4 | associations | 200 | count > 0 |
| 5 | sync-start | 200 | sync iniciado |
| 6 | delete | 200 | CPU mantida |
| 7 | status | 200 | orphan CPU presente |

---

## Journey 5: Fine-Tuning LLM

**Objetivo:** Validar workflow de treinamento de modelos.

**Pre-requisitos:**
- GPU com VRAM suficiente
- Dataset preparado

### Comandos

```bash
# 1. Listar modelos base suportados
dumont finetune models
# Esperado: Lista de modelos Unsloth

# 2. Obter recomendacao de GPU
dumont advisor recommend task="Train Llama 3 8B with LoRA"
# Esperado: Sugestao de GPU adequada

# 3. Criar GPU para treino
dumont instance create offer_id=<ID> label=finetune-job

# 4. Iniciar job de fine-tuning
dumont finetune create job_name=my-lora model_id=unsloth/llama-3-8b-bnb-4bit
# Esperado: Job criado com ID

# 5. Listar jobs
dumont finetune jobs
# Esperado: my-lora na lista

# 6. Monitorar logs
dumont finetune logs <job_id>
# Esperado: Logs de treinamento

# 7. Cancelar job (se necessario)
dumont finetune cancel <job_id>
# Esperado: Job cancelado
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 1 | models | 200 | models.length > 0 |
| 2 | recommend | 200 | gpu_recommendation |
| 4 | create | 201 | job_id retornado |
| 5 | jobs | 200 | job presente |
| 6 | logs | 200 | log content |
| 7 | cancel | 200 | status: cancelled |

---

## Journey 6: Analise de Mercado Spot

**Objetivo:** Validar ferramentas de analise de precos e disponibilidade.

**Pre-requisitos:**
- Usuario autenticado

### Comandos

```bash
# 1. Previsao de precos 24h
dumont spot prediction rtx4090
# Esperado: Array de previsoes por hora

# 2. Monitor de precos atual
dumont spot monitor
# Esperado: Precos atuais por GPU

# 3. Score de confiabilidade
dumont spot reliability
# Esperado: Rankings de providers

# 4. Ranking GPUs para LLM
dumont spot llm-gpus
# Esperado: GPUs otimizadas para inference

# 5. Janelas seguras de uso
dumont spot safe-windows rtx4090
# Esperado: Horarios com menor interrupcao

# 6. Disponibilidade instantanea
dumont spot availability
# Esperado: GPUs disponiveis agora

# 7. Custo de treinamento
dumont spot training-cost model=llama-3-8b
# Esperado: Estimativa de custo
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 1 | prediction | 200 | predictions_24h array |
| 2 | monitor | 200 | items array |
| 3 | reliability | 200 | scores presentes |
| 4 | llm-gpus | 200 | rankings |
| 5 | safe-windows | 200 | windows array |
| 6 | availability | 200 | gpus disponiveis |
| 7 | training-cost | 200 | estimated_cost |

---

## Journey 7: Tracking de Economia

**Objetivo:** Validar metricas de economia e ROI.

**Pre-requisitos:**
- Historico de uso (alguns dias)

### Comandos

```bash
# 1. Economia real em USD
dumont metrics savings
# Esperado: total_savings_usd

# 2. Resumo consolidado
dumont saving summary
# Esperado: Economia total vs clouds

# 3. Breakdown por GPU
dumont saving breakdown
# Esperado: Economia por tipo de GPU

# 4. Historico mensal
dumont saving history
# Esperado: Economia por mes

# 5. Economia com hibernacao
dumont hibernation stats
# Esperado: Horas/USD economizados

# 6. Comparacao com clouds
dumont saving comparison
# Esperado: vs AWS, GCP, Azure
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 1 | savings | 200 | summary presente |
| 2 | summary | 200 | total_savings |
| 3 | breakdown | 200 | gpu_breakdown |
| 4 | history | 200 | monthly_data |
| 5 | hibernation | 200 | stats |
| 6 | comparison | 200 | cloud_comparison |

---

## Journey 8: Deploy Assistido por IA

**Objetivo:** Validar wizard inteligente de deploy.

**Pre-requisitos:**
- Projeto com requirements.txt ou Dockerfile

### Comandos

```bash
# 1. Analisar projeto atual
dumont ai-wizard analyze
# Esperado: Analise de requisitos

# 2. Obter recomendacao
dumont advisor recommend task="Run inference with Flux.1"
# Esperado: GPU e config recomendadas

# 3. Deploy com wizard
dumont instance create wizard gpu_name=rtx4090
# Esperado: Deploy otimizado automatico

# 4. Verificar instancia
dumont instance list
# Esperado: Instancia criada com config otimizada
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 1 | analyze | 200 | analysis result |
| 2 | recommend | 200 | recommendation |
| 3 | create wizard | 201 | optimized instance |
| 4 | list | 200 | instance presente |

---

## Journey 9: Migracao GPU para CPU

**Objetivo:** Validar migracao de workload entre tipos de instancia.

**Pre-requisitos:**
- Instancia GPU ativa
- Dados sincronizados

### Comandos

```bash
# 1. Criar GPU inicial
dumont instance create offer_id=<ID> label=migrate-test

# 2. Trabalhar e sincronizar
dumont instance sync <instance_id>

# 3. Estimar migracao
dumont instance migrate <instance_id> estimate target_type=cpu
# Esperado: Custo e tempo estimado

# 4. Migrar para CPU
dumont instance migrate <instance_id> target_type=cpu
# Esperado: Nova instancia CPU

# 5. Verificar migracao
dumont instance list
# Esperado: Instancia CPU ativa

# 6. Migrar de volta para GPU
dumont instance migrate <cpu_id> target_type=gpu gpu_name=rtx4090
# Esperado: Nova instancia GPU

# 7. Confirmar
dumont instance list
# Esperado: GPU ativa com dados restaurados
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 3 | estimate | 200 | estimated_time |
| 4 | migrate cpu | 200 | new_instance_id |
| 6 | migrate gpu | 200 | new_instance_id |
| 7 | list | 200 | GPU com dados |

---

## Journey 10: Health Check e Monitoramento

**Objetivo:** Validar saude do sistema e monitoramento.

### Comandos

```bash
# 1. Health check do backend
dumont health list
# Esperado: status: healthy

# 2. Listar instancias ativas
dumont instance list
# Esperado: Lista ou vazio

# 3. Verificar mercado
dumont metrics market
# Esperado: Dados de mercado

# 4. Rankings de eficiencia
dumont metrics efficiency
# Esperado: GPU efficiency scores

# 5. Rankings de providers
dumont metrics providers
# Esperado: Provider rankings

# 6. Status dos agentes
dumont agent status
# Esperado: Agents health
```

### Validacoes

| Step | Comando | Status | Validacao |
|------|---------|--------|-----------|
| 1 | health | 200 | status: healthy |
| 2 | list | 200 | resposta valida |
| 3 | market | 200 | data presente |
| 4 | efficiency | 200 | rankings |
| 5 | providers | 200 | rankings |
| 6 | agent status | 200 | agents health |

---

## Execucao dos Testes

### Estrutura de Arquivos

```
tests/cli/
├── journeys/
│   ├── 01_auth_journey.sh
│   ├── 02_instance_lifecycle.sh
│   ├── 03_backup_restore.sh
│   ├── 04_standby_failover.sh
│   ├── 05_finetune_workflow.sh
│   ├── 06_spot_analysis.sh
│   ├── 07_savings_tracking.sh
│   ├── 08_ai_deploy.sh
│   ├── 09_migration.sh
│   └── 10_health_check.sh
├── utils/
│   ├── setup.sh
│   ├── teardown.sh
│   └── assertions.sh
├── config/
│   └── test_credentials.env
└── run_all.sh
```

### Comando para Executar

```bash
# Executar todos os testes
./tests/cli/run_all.sh

# Executar journey especifico
./tests/cli/journeys/01_auth_journey.sh

# Executar com verbose
DEBUG=1 ./tests/cli/run_all.sh
```

### Variaveis de Ambiente

```bash
export DUMONT_TEST_EMAIL="test@example.com"
export DUMONT_TEST_PASSWORD="testpass123"
export DUMONT_BASE_URL="http://localhost:8767"
export DUMONT_SKIP_DESTRUCTIVE=true  # Pular testes que criam/destroem
```

---

## Metricas de Cobertura

| Journey | Comandos | Endpoints | Cobertura |
|---------|----------|-----------|-----------|
| Auth | 5 | 4 | 100% |
| Instance | 9 | 8 | 100% |
| Backup | 8 | 6 | 100% |
| Standby | 7 | 5 | 100% |
| Finetune | 7 | 5 | 100% |
| Spot | 7 | 7 | 100% |
| Savings | 6 | 6 | 100% |
| AI Deploy | 4 | 3 | 100% |
| Migration | 7 | 4 | 100% |
| Health | 6 | 6 | 100% |
| **Total** | **66** | **54** | **100%** |

---

## Proximos Passos

1. Implementar scripts shell para cada journey
2. Adicionar CI/CD pipeline para testes automaticos
3. Criar dashboard de resultados
4. Integrar com alertas de falha

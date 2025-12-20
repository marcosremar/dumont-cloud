# 📟 Dumont CLI: Comando de Voz do Arquiteto

O Dumont Cloud CLI (`dumont`) é uma ferramenta de linha de comando automática e integrada ao sistema, projetada para oferecer controle total sobre a infraestrutura de GPU sem a necessidade de uma interface gráfica.

Assim como o `claude` do Claude Code, o `dumont` é inteligente, descobre APIs automaticamente e gerencia sua autenticação de forma transparente.

---

## 🚀 Instalação e Configuração

Para instalar o CLI em seu sistema e habilitar atalhos globais:

```bash
cd /home/marcos/dumontcloud
./install-cli.sh
./setup-cli-shortcuts.sh
source ~/.bashrc
```

Após a instalação, você pode usar `dumont` (ou o alias `dm`) de **qualquer diretório** do seu terminal.

---

## 🔐 Autenticação (Authentication)

O CLI gerencia tokens JWT automaticamente após o primeiro login.

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `auth login` | Realiza login e salva o token | `dumont auth login user@email.com pass` |
| `auth me` | Verifica o status da sessão atual | `dumont auth me` |
| `auth logout` | Remove o token salvo localmente | `dumont auth logout` |
| `auth register` | Cria uma nova conta | `dumont auth register user@email.com pass` |

---

## 💻 Gestão de Instâncias (Instances)

O coração da orquestração Dumont.

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `instance list` | Lista todas as suas instâncias | `dumont instance list` |
| `instance create` | Cria uma nova instância GPU | `dumont instance create rtx4090` |
| `instance create wizard` | Deploy assistido por IA | `dumont instance create wizard rtx4090` |
| `instance get` | Detalhes de uma instância | `dumont instance get 123456` |
| `instance pause` | Pausa a instância (Stop) | `dumont instance pause 123456` |
| `instance resume` | Retoma uma instância pausada | `dumont instance resume 123456` |
| `instance wake` | Acorda uma instância em hibernação | `dumont instance wake 123456` |
| `instance delete` | Destrói a instância permanentemente | `dumont instance delete 123456` |
| `instance offers` | Pesquisa GPUs disponíveis no mercado | `dumont instance offers 'rtx 4090'` |

> **Dica:** Use `num_gpus=2` ou outros parâmetros no formato `key=value` após o comando create.

---

## 💾 Snapshots e Backup

Gerenciamento de persistência de dados ultra-rápida.

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `snapshot list` | Lista todos os snapshots criados | `dumont snapshot list` |
| `snapshot create` | Cria um snapshot de uma instância | `dumont snapshot create backup-v1 123456` |
| `snapshot restore` | Restaura dados para uma instância | `dumont snapshot restore snap_abc 123456` |
| `snapshot delete` | Remove um snapshot do storage | `dumont snapshot delete snap_abc` |

---

## 🛡️ CPU Standby (GCP Resilience)

Comandos para gerenciar a camada de resiliência em Google Cloud.

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `standby status` | Status geral do sistema de standby | `dumont standby status` |
| `standby configure` | Habilita/Desabilita auto-standby | `dumont standby configure enabled=true` |
| `standby associations`| Lista pares GPU ↔ CPU Standby | `dumont standby associations` |
| `standby sync-start` | Força início da sincronização | `dumont standby sync-start 123456` |
| `standby sync-stop` | Para a sincronização atual | `dumont standby sync-stop 123456` |

---

## 🧬 Fine-Tuning (LLM)

Controle de jobs de treinamento via Unsloth/SkyPilot.

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `finetune models` | Lista modelos base suportados | `dumont finetune models` |
| `finetune jobs` | Lista todos os seus jobs de treino | `dumont finetune jobs` |
| `finetune create` | Inicia um novo job de Fine-Tuning | `dumont finetune create my-lora llama-3` |
| `finetune logs` | Visualiza logs do treinamento | `dumont finetune logs job_abc123` |
| `finetune cancel` | Cancela um job em execução | `dumont finetune cancel job_abc123` |

---

## 📊 Métricas e Economia

Visualize seu ROI e saúde do sistema.

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `metric dashboard` | Resumo de métricas do sistema | `dumont metric dashboard` |
| `metric savings` | Histórico de economia real (USD) | `dumont metric savings` |
| `hibernation stats`| Estatísticas de hibernação automática | `dumont hibernation stats` |
| `saving summary` | Relatório consolidado de custos | `dumont saving summary` |

---

## 🧠 Inteligência Artificial

| Comando | Descrição | Exemplo |
|:--- |:--- |:--- |
| `ai-wizard analyze` | Análise de arquitetura de projeto | `dumont ai-wizard analyze` |
| `advisor recommend`| Recomendação de GPU por tarefa | `dumont advisor recommend "Train Flux.1"` |
| `spot prediction` | Previsão de preços para as próximas 24h | `dumont spot prediction rtx4090` |

---

## ⚡ Atalhos Rápidos (Aliases)

Se você executou o `setup-cli-shortcuts.sh`, estes atalhos estão ativos:

*   `dm` -> `dumont`
*   `dmls` -> `dumont instance list`
*   `dmme` -> `dumont auth me`
*   `dmcreate` -> `dumont instance create`
*   `dmrm` -> `dumont instance delete`
*   `dmsnap` -> `dumont snapshot list`

---

## 🛠️ Auto-Discovery Mechanism

O Dumont CLI utiliza o mecanismo de **OpenAPI Reflection**. Isso significa que se você adicionar um novo endpoint ao backend FastAPI, ele aparecerá automaticamente no CLI sem necessidade de atualização do código do cliente.

Para ver todos os comandos disponíveis no seu sistema no momento:
```bash
dumont help
```

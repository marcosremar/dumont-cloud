# Machines - Gerenciamento de Instancias

## Visao Geral

A pagina Machines e onde voce gerencia todas as suas instancias GPU. Crie, monitore, e destrua maquinas conforme necessario.

---

## Criar Nova Maquina

### Via UI

1. Clique em **"Nova Maquina"**
2. Escolha:
   - **GPU**: RTX 4090, A100, H100, etc
   - **Regiao**: US, EU, Asia
   - **Imagem**: PyTorch, TensorFlow, Custom
3. Configure:
   - **Disk**: 50GB - 1TB
   - **Failover**: Habilitado/Desabilitado
4. Clique em **"Lancar"**

### Via AI Wizard

1. Clique em **"AI Wizard"**
2. Descreva seu caso de uso
3. Aceite a recomendacao
4. Maquina criada automaticamente

---

## Estados da Maquina

| Estado | Descricao | Acao |
|--------|-----------|------|
| `running` | Ativa e cobrando | SSH disponivel |
| `starting` | Inicializando | Aguarde ~30s |
| `stopping` | Parando | Aguarde |
| `stopped` | Parada | Nao cobra |
| `hibernating` | Auto-pause | Resume sob demanda |
| `failed` | Erro/Interrupcao | Failover automatico |

---

## Acoes Disponiveis

### Start/Stop
- **Stop**: Para cobranca, mantem dados
- **Start**: Retoma de onde parou

### Reboot
- Reinicia a maquina
- Mantem IP e configuracoes

### Destroy
- Remove permanentemente
- Dados perdidos (a menos que tenha snapshot)

### Snapshot
- Cria backup manual
- Armazenado no R2

### SSH
- Abre terminal no browser
- Ou copie comando SSH

---

## Metricas

### GPU
- Utilizacao (%)
- Memoria usada/total
- Temperatura
- Power usage

### Sistema
- CPU usage
- RAM usage
- Disk I/O
- Network I/O

### Custos
- Custo acumulado
- Estimativa mensal
- Comparativo spot vs on-demand

---

## Configuracoes

### Failover
- Habilitar/desabilitar
- Escolher estrategia (Warm Pool / CPU Standby)
- Prioridade de regiao

### Snapshots Automaticos
- Frequencia (1h, 6h, 24h)
- Retencao (7, 30, 90 dias)
- Notificacoes

### Hibernation (Serverless)
- Tempo de idle (5-60 min)
- Horarios ativos
- Excecoes

---

## Troubleshooting

### Maquina nao inicia
1. Verifique saldo
2. Tente outra regiao
3. Contate suporte

### SSH nao conecta
1. Verifique se esta `running`
2. Confirme IP correto
3. Verifique firewall local

### GPU nao aparece
1. Verifique drivers: `nvidia-smi`
2. Reinicie a maquina
3. Contate suporte

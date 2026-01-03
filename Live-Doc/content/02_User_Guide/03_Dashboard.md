# Dashboard

## Visao Geral

O Dashboard e sua central de comando. Veja metricas, custos, e status de todas as suas instancias em um so lugar.

---

## Cards Principais

### Saldo Atual
- Creditos disponiveis
- Estimativa de duracao
- Link para adicionar mais

### Maquinas Ativas
- Contagem de instancias rodando
- Custo/hora atual
- Status geral (all green / alertas)

### Economia Total
- Quanto voce economizou vs AWS/GCP
- Grafico historico
- Detalhamento por GPU

### Failovers
- Failovers nas ultimas 24h
- Taxa de sucesso
- Tempo medio de recuperacao

---

## Graficos

### Uso de GPU
- Utilizacao ao longo do tempo
- Por maquina ou agregado
- Periodo: 1h, 24h, 7d, 30d

### Custos
- Gastos diarios/semanais/mensais
- Por GPU, regiao, ou projeto
- Projecao para o mes

### Latencia de Failover
- Tempo de cada failover
- Comparativo Warm Pool vs CPU Standby
- Tendencia

---

## Acoes Rapidas

### Nova Maquina
Botao para criar maquina rapidamente

### AI Wizard
Acesso ao assistente de IA

### Relatorios
Gerar relatorios customizados

### Settings
Acesso rapido a configuracoes

---

## Alertas

### Tipos de Alerta

| Tipo | Descricao | Acao |
|------|-----------|------|
| `warning` | Saldo baixo | Adicionar creditos |
| `error` | Maquina falhou | Verificar failover |
| `info` | Failover concluido | Nenhuma |
| `success` | Snapshot criado | Nenhuma |

### Configurar Alertas

1. **Settings** > **Notifications**
2. Escolha eventos
3. Defina canais (email, webhook, Slack)

---

## Widgets

### Personalizacao
- Arrastar e soltar widgets
- Mostrar/ocultar metricas
- Salvar layout

### Widgets Disponiveis
- Resumo de custos
- Status de maquinas
- Graficos de uso
- Lista de alertas
- Failovers recentes
- Top GPUs por uso

---

## Atalhos de Teclado

| Atalho | Acao |
|--------|------|
| `N` | Nova maquina |
| `W` | AI Wizard |
| `M` | Ir para Machines |
| `B` | Ir para Billing |
| `?` | Ajuda |

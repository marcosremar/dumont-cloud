# Sistema de Monitoramento de Preços de GPUs

Sistema automático de monitoramento de preços de GPUs na Vast.ai com análise de tendências e alertas.

## 📋 Características

- ✅ **Agentes auto-inicializáveis**: Iniciam automaticamente quando o servidor sobe
- ✅ **Auto-restart**: Se um agente falhar, ele reinicia automaticamente
- ✅ **Monitoramento periódico**: A cada 30 minutos (configurável)
- ✅ **GPUs monitoradas**: RTX 4090 e RTX 4050 (expansível)
- ✅ **Banco de dados PostgreSQL**: Armazena histórico completo de preços
- ✅ **Análise de tendências**: Detecta mudanças significativas de preço (±10%)
- ✅ **Alertas automáticos**: Notifica quando há quedas ou picos de preço
- ✅ **Relatórios completos**: APIs para análise de preços, melhores horários, comparações

## 🗄️ Banco de Dados

### Configuração

O sistema usa PostgreSQL para armazenar o histórico de preços.

**Credenciais:**
- Host: localhost
- Porta: 5432
- Database: dumont_cloud
- Usuário: dumont
- Senha: dumont123

### Tabelas

#### price_history
Armazena snapshots periódicos de preços:

```sql
- id: identificador único
- gpu_name: nome da GPU (ex: "RTX 4090")
- timestamp: data/hora da coleta
- min_price: preço mínimo encontrado ($/hora)
- max_price: preço máximo encontrado ($/hora)
- avg_price: preço médio ($/hora)
- median_price: mediana dos preços ($/hora)
- total_offers: quantidade de ofertas disponíveis
- available_gpus: total de GPUs disponíveis
- region_stats: estatísticas por região (JSON)
```

#### price_alerts
Armazena alertas de mudanças significativas:

```sql
- id: identificador único
- gpu_name: nome da GPU
- timestamp: data/hora do alerta
- alert_type: tipo ('price_drop', 'price_spike', 'high_availability')
- previous_value: valor anterior
- current_value: valor atual
- change_percent: variação percentual
- message: mensagem descritiva do alerta
```

## 🚀 Inicialização

### Inicializar o banco de dados

```bash
python3 init_db.py
```

### Iniciar o servidor

O agente de monitoramento inicia automaticamente quando você sobe o servidor Flask:

```bash
python3 app.py
```

**Saída esperada:**
```
Inicializando agentes automaticos...
✓ Agente de monitoramento de precos iniciado (RTX 4090, RTX 4050)
 * Running on http://0.0.0.0:8766
```

## 📊 APIs Disponíveis

### 1. Status do Agente

**GET** `/api/price-monitor/status`

Retorna status do agente de monitoramento.

**Resposta:**
```json
{
  "success": true,
  "agent": {
    "name": "PriceMonitor",
    "running": true,
    "class": "PriceMonitorAgent",
    "interval_minutes": 30,
    "gpus_monitored": ["RTX 4090", "RTX 4050"],
    "last_prices": {
      "RTX 4090": 0.3456,
      "RTX 4050": 0.1234
    }
  }
}
```

### 2. Histórico de Preços

**GET** `/api/price-monitor/history?gpu_name=RTX 4090&hours=24&limit=100`

Retorna histórico de preços.

**Parâmetros:**
- `gpu_name` (opcional): Filtrar por GPU específica
- `hours` (padrão: 24): Quantas horas de histórico
- `limit` (padrão: 100): Limite de registros

**Resposta:**
```json
{
  "success": true,
  "count": 48,
  "history": [
    {
      "id": 123,
      "gpu_name": "RTX 4090",
      "timestamp": "2025-12-16T19:30:00",
      "min_price": 0.29,
      "max_price": 0.45,
      "avg_price": 0.35,
      "median_price": 0.34,
      "total_offers": 87,
      "available_gpus": 142
    }
  ]
}
```

### 3. Resumo de Preços Atual

**GET** `/api/price-monitor/summary?gpu_name=RTX 4090`

Resumo de preços atuais e tendências 24h.

**Resposta:**
```json
{
  "success": true,
  "summary": [
    {
      "gpu_name": "RTX 4090",
      "current": {
        "min_price": 0.29,
        "avg_price": 0.35,
        "max_price": 0.45,
        "median_price": 0.34,
        "total_offers": 87,
        "available_gpus": 142,
        "timestamp": "2025-12-16T19:30:00"
      },
      "trend_24h": {
        "direction": "down",
        "change_percent": -5.2,
        "lowest_avg": 0.32,
        "highest_avg": 0.38,
        "period_avg": 0.35
      }
    }
  ]
}
```

### 4. Alertas de Preço

**GET** `/api/price-monitor/alerts?gpu_name=RTX 4090&hours=24`

Lista alertas de mudanças significativas.

**Resposta:**
```json
{
  "success": true,
  "count": 3,
  "alerts": [
    {
      "id": 45,
      "gpu_name": "RTX 4090",
      "timestamp": "2025-12-16T15:00:00",
      "alert_type": "price_drop",
      "previous_value": 0.38,
      "current_value": 0.32,
      "change_percent": -15.8,
      "message": "RTX 4090: Preço caiu 15.8% ($0.3800 -> $0.3200)"
    }
  ]
}
```

### 5. Melhores Horários para Alugar

**GET** `/api/price-monitor/best-times?gpu_name=RTX 4090&days=7`

Analisa quando os preços costumam ser mais baixos.

**Resposta:**
```json
{
  "success": true,
  "gpu_name": "RTX 4090",
  "analysis_period_days": 7,
  "best_hours": [
    {
      "hour": 3,
      "avg_price": 0.31,
      "time_range": "03:00-03:59"
    },
    {
      "hour": 4,
      "avg_price": 0.32,
      "time_range": "04:00-04:59"
    }
  ],
  "best_days": [
    {
      "day": "Tuesday",
      "avg_price": 0.33
    },
    {
      "day": "Wednesday",
      "avg_price": 0.34
    }
  ],
  "hourly_average": {
    "00:00": 0.35,
    "01:00": 0.34,
    ...
  }
}
```

### 6. Comparar GPUs

**GET** `/api/price-monitor/compare?gpus=RTX 4090,RTX 4050`

Compara preços entre diferentes GPUs.

**Resposta:**
```json
{
  "success": true,
  "comparison": [
    {
      "gpu_name": "RTX 4050",
      "avg_price": 0.12,
      "min_price": 0.09,
      "max_price": 0.15,
      "total_offers": 234,
      "available_gpus": 456,
      "last_update": "2025-12-16T19:30:00"
    },
    {
      "gpu_name": "RTX 4090",
      "avg_price": 0.35,
      "min_price": 0.29,
      "max_price": 0.45,
      "total_offers": 87,
      "available_gpus": 142,
      "last_update": "2025-12-16T19:30:00"
    }
  ],
  "cheapest": {
    "gpu_name": "RTX 4050",
    "avg_price": 0.12
  }
}
```

## ⚙️ Configuração

### Alterar GPUs Monitoradas

Edite `app.py` na função `init_agents()`:

```python
agent_manager.register_agent(
    PriceMonitorAgent,
    vast_api_key=vast_api_key,
    interval_minutes=30,  # Alterar intervalo aqui
    gpus_to_monitor=['RTX 4090', 'RTX 4050', 'A100']  # Adicionar GPUs aqui
)
```

### Alterar Intervalo de Monitoramento

O intervalo padrão é 30 minutos. Para alterar, modifique o parâmetro `interval_minutes` acima.

**Exemplos:**
- 15 minutos: `interval_minutes=15`
- 1 hora: `interval_minutes=60`
- 6 horas: `interval_minutes=360`

### GPUs Suportadas

Qualquer GPU disponível na Vast.ai pode ser monitorada:

```
RTX 5090, RTX 4090, RTX 4080, RTX 4050, RTX 3090, RTX 3080,
RTX A6000, RTX A5000, RTX A4000, A100, H100, L40S
```

## 🔍 Consultas Úteis SQL

### Ver últimos 10 registros de preços

```sql
SELECT gpu_name, timestamp, avg_price, total_offers
FROM price_history
ORDER BY timestamp DESC
LIMIT 10;
```

### Ver média de preço das últimas 24h

```sql
SELECT
    gpu_name,
    AVG(avg_price) as media_24h,
    MIN(min_price) as menor_preco,
    MAX(max_price) as maior_preco
FROM price_history
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY gpu_name;
```

### Ver todos os alertas de queda de preço

```sql
SELECT *
FROM price_alerts
WHERE alert_type = 'price_drop'
ORDER BY timestamp DESC;
```

### Ver horários com menores preços (última semana)

```sql
SELECT
    gpu_name,
    EXTRACT(HOUR FROM timestamp) as hora,
    AVG(avg_price) as preco_medio
FROM price_history
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY gpu_name, hora
ORDER BY gpu_name, preco_medio;
```

## 🛠️ Troubleshooting

### Agente não está iniciando

Verifique se há uma API key configurada:

```bash
curl http://localhost:8766/api/settings
```

Se não houver API key, configure via:

```bash
curl -X PUT http://localhost:8766/api/settings \
  -H "Content-Type: application/json" \
  -d '{"vast_api_key": "SUA_API_KEY"}'
```

### Verificar status do agente

```bash
curl http://localhost:8766/api/price-monitor/status
```

### Ver logs do servidor

```bash
# Se rodando via systemd
sudo journalctl -u dumont-cloud -f

# Se rodando diretamente
# Os logs aparecem no terminal
```

### Banco de dados não conecta

Verifique se o PostgreSQL está rodando:

```bash
sudo systemctl status postgresql
```

Se não estiver, inicie:

```bash
sudo systemctl start postgresql
```

### Reiniciar agente manualmente

O sistema de agentes não expõe API de restart ainda, mas você pode reiniciar o servidor:

```bash
# Se usando systemd
sudo systemctl restart dumont-cloud

# Se rodando diretamente
# Ctrl+C e depois python3 app.py
```

## 📈 Casos de Uso

### 1. Encontrar Melhor Momento para Alugar

```bash
# Ver melhores horários da última semana
curl "http://localhost:8766/api/price-monitor/best-times?gpu_name=RTX 4090&days=7"
```

### 2. Ser Alertado Quando Preço Cai

```bash
# Verificar alertas recentes
curl "http://localhost:8766/api/price-monitor/alerts?hours=24"
```

### 3. Comparar Custo-Benefício entre GPUs

```bash
# Comparar preços
curl "http://localhost:8766/api/price-monitor/compare?gpus=RTX 4090,RTX 4050,A100"
```

### 4. Monitorar Tendência de Longo Prazo

```bash
# Histórico de 7 dias
curl "http://localhost:8766/api/price-monitor/history?gpu_name=RTX 4090&hours=168&limit=500"
```

## 🔐 Variáveis de Ambiente (Opcionais)

Você pode configurar o banco via variáveis de ambiente:

```bash
export DB_USER=dumont
export DB_PASSWORD=dumont123
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=dumont_cloud
```

## 🚦 Status do Sistema

- ✅ Sistema de agentes com auto-restart
- ✅ PostgreSQL configurado
- ✅ Monitoramento de RTX 4090 e RTX 4050
- ✅ APIs de relatórios completas
- ✅ Detecção de mudanças de preço
- ✅ Análise de melhores horários
- ✅ Comparação entre GPUs

## 📝 Próximos Passos (Futuras Melhorias)

- [ ] Dashboard web para visualizar gráficos
- [ ] Notificações por email/webhook quando preço cai
- [ ] Exportar relatórios em PDF/CSV
- [ ] Análise de correlação preço x disponibilidade
- [ ] Previsão de preços usando ML
- [ ] API pública com rate limiting
- [ ] Alertas customizáveis por usuário

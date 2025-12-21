# Balance API

Endpoint para consultar saldo de crédito da conta Vast.ai.

## Endpoint

### GET /balance

Retorna o saldo atual de crédito na conta Vast.ai configurada.

**Response:**
```json
{
  "balance": 125.50,
  "currency": "USD",
  "last_updated": "2024-12-20T15:30:00Z",
  "estimated_hours_remaining": 298.8,
  "active_instances": 2,
  "hourly_cost": 0.42,
  "alerts": {
    "low_balance_threshold": 50.00,
    "low_balance_alert": false
  }
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| balance | float | Saldo atual em USD |
| currency | string | Moeda (sempre USD) |
| last_updated | string | Última atualização |
| estimated_hours_remaining | float | Horas estimadas restantes |
| active_instances | int | Instâncias ativas |
| hourly_cost | float | Custo por hora atual |
| alerts.low_balance_threshold | float | Limite para alerta |
| alerts.low_balance_alert | bool | Se alerta está ativo |

**Exemplo curl:**
```bash
curl https://api.dumontcloud.com/api/v1/balance \
  -H "Authorization: Bearer $API_KEY"
```

---

## Cálculo de Tempo Restante

```
estimated_hours_remaining = balance / hourly_cost
```

O `hourly_cost` é a soma dos custos de todas as instâncias ativas.

---

## Alertas de Saldo Baixo

Configure alertas em `/settings`:

```json
{
  "low_balance_threshold": 50.00,
  "notify_on_low_balance": true,
  "notify_channels": ["email", "slack"]
}
```

---

## Adicionar Créditos

Para adicionar créditos, acesse:
- [vast.ai/billing](https://vast.ai/billing) - Para créditos Vast.ai
- [dumontcloud.com/billing](https://dumontcloud.com/billing) - Via Dumont Cloud

---

## Integração com CLI

```bash
# Ver saldo
dumont balance

# Saída:
# 💰 Balance: $125.50 USD
# ⏱️  Estimated: 298.8 hours remaining
# 📊 Active instances: 2 ($0.42/hr)
```

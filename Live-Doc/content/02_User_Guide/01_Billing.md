# Billing

## Visao Geral

O Dumont Cloud usa um sistema de creditos pre-pagos. Voce adiciona creditos e eles sao consumidos por segundo de uso.

---

## Adicionar Creditos

### Via Dashboard

1. Acesse **Dashboard** > **Billing**
2. Clique em **"Adicionar Creditos"**
3. Escolha o valor
4. Selecione o metodo de pagamento
5. Confirme

### Valores Disponiveis

| Creditos | Bonus | Total |
|----------|-------|-------|
| $10 | - | $10 |
| $50 | +$5 | $55 |
| $100 | +$15 | $115 |
| $500 | +$100 | $600 |

---

## Metodos de Pagamento

### Cartao de Credito
- Visa, Mastercard, Amex
- Processamento instantaneo
- Recorrencia disponivel

### PIX (Brasil)
- QR Code ou copia-e-cola
- Creditos em ate 5 minutos
- Sem taxas adicionais

### Boleto (Brasil)
- Prazo de 3 dias uteis
- Creditos apos compensacao

### Wire Transfer (Empresas)
- Para valores acima de $1.000
- Dados bancarios enviados por email
- Prazo de 2-5 dias uteis

---

## Consumo

### Como e calculado?

```
Custo = tempo_uso (segundos) x preco_hora / 3600
```

### Exemplo

RTX 4090 a $0.40/hora:
- 1 hora = $0.40
- 30 min = $0.20
- 10 min = $0.067

### Ver Consumo

1. **Dashboard** > **Billing** > **Usage**
2. Filtrar por periodo, maquina, ou GPU
3. Exportar para CSV

---

## Alertas de Saldo

### Configurar Alertas

1. **Settings** > **Notifications**
2. Defina limite minimo (ex: $10)
3. Escolha canal (email, webhook, Slack)

### Alertas Automaticos
- Saldo baixo (configuravel)
- Creditos esgotando (24h estimadas)
- Pagamento recebido

---

## Fatura e NF

### Nota Fiscal (Brasil)
- Emitida automaticamente
- Enviada por email
- Disponivel no dashboard

### Invoice (Internacional)
- PDF disponivel no dashboard
- Dados fiscais configuraveis
- Suporta VAT ID (Europa)

---

## Reembolso

### Politica
- Creditos nao utilizados: reembolso em 30 dias
- Creditos bonus: nao reembolsaveis
- Solicitar via suporte

### Como Solicitar
1. Email para billing@dumontcloud.com
2. Informe motivo e valor
3. Reembolso em 5-10 dias uteis

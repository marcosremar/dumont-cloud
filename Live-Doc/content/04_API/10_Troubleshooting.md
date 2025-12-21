# API Troubleshooting

Guia de diagnóstico e resolução de problemas comuns da API.

## Códigos de Erro HTTP

| Código | Significado | Ação |
|--------|-------------|------|
| 400 | Bad Request | Verifique parâmetros da requisição |
| 401 | Unauthorized | Token inválido ou expirado |
| 403 | Forbidden | Sem permissão para o recurso |
| 404 | Not Found | Recurso não existe |
| 409 | Conflict | Operação conflitante em andamento |
| 422 | Unprocessable Entity | Validação falhou |
| 429 | Too Many Requests | Rate limit excedido |
| 500 | Internal Server Error | Erro no servidor |
| 502 | Bad Gateway | Serviço upstream indisponível |
| 503 | Service Unavailable | Manutenção ou sobrecarga |

---

## Problemas de Autenticação

### "401 Unauthorized"

**Causas:**
- Token expirado
- Token inválido
- Header Authorization ausente

**Solução:**
```bash
# Verificar token
curl https://api.dumontcloud.com/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Re-autenticar se necessário
curl -X POST https://api.dumontcloud.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@email.com", "password": "senha"}'
```

### Token expira rapidamente

- Tokens padrão expiram em 24 horas
- Use refresh token para renovar
- Configure `remember_me: true` no login para token de 7 dias

---

## Problemas de Instâncias

### "Instance not found"

**Causas:**
- ID incorreto
- Instância foi destruída
- Instância pertence a outro usuário

**Diagnóstico:**
```bash
# Listar suas instâncias
curl https://api.dumontcloud.com/api/v1/instances \
  -H "Authorization: Bearer $TOKEN"
```

### "Cannot start instance"

**Causas:**
- Saldo insuficiente
- GPU não disponível
- Host offline

**Solução:**
1. Verifique saldo: `GET /balance`
2. Verifique disponibilidade: `GET /instances/offers`
3. Tente outra GPU ou região

### Instância não responde

```bash
# Verificar status
curl https://api.dumontcloud.com/api/v1/instances/123 \
  -H "Authorization: Bearer $TOKEN"

# Verificar agente
curl https://api.dumontcloud.com/api/v1/agent/instances/123 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Problemas de Failover

### "Warm pool not ready"

**Causas:**
- Host não tem GPUs suficientes
- Standby não foi provisionado
- Volume não foi criado

**Solução:**
```bash
# Verificar status do warm pool
curl https://api.dumontcloud.com/api/v1/warmpool/status/123 \
  -H "Authorization: Bearer $TOKEN"

# Provisionar se necessário
curl -X POST https://api.dumontcloud.com/api/v1/warmpool/provision \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"machine_id": 123, "host_machine_id": 88888}'
```

### "CPU standby not configured"

```bash
# Verificar configuração
curl https://api.dumontcloud.com/api/v1/failover/settings/machines/123 \
  -H "Authorization: Bearer $TOKEN"

# Habilitar CPU standby
curl -X POST https://api.dumontcloud.com/api/v1/failover/settings/machines/123/enable-cpu-standby \
  -H "Authorization: Bearer $TOKEN"
```

### Failover lento (>2 minutos)

1. Verifique estratégia ativa (warm_pool é mais rápido)
2. Verifique tamanho do snapshot
3. Verifique velocidade da rede
4. Considere usar region mais próxima

---

## Problemas de Snapshots

### "Snapshot failed"

**Causas:**
- Espaço em disco insuficiente
- Cloud storage não configurado
- Credenciais inválidas

**Solução:**
```bash
# Testar cloud storage
curl -X POST https://api.dumontcloud.com/api/v1/settings/cloud-storage/test \
  -H "Authorization: Bearer $TOKEN"
```

### Snapshots muito lentos

1. Verifique tamanho do workspace
2. Use exclusões para dados temporários
3. Considere provider mais próximo

---

## Rate Limiting

### "429 Too Many Requests"

**Limites padrão:**
| Plano | Requests/min | Requests/hora |
|-------|--------------|---------------|
| Free | 30 | 500 |
| Pro | 100 | 2000 |
| Enterprise | 500 | 10000 |

**Headers de resposta:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1703084400
```

**Solução:**
- Aguarde `X-RateLimit-Reset`
- Implemente backoff exponencial
- Considere upgrade de plano

---

## Problemas de Conexão

### Timeout

**Causas:**
- Rede lenta
- Servidor sobrecarregado
- Request muito grande

**Solução:**
- Aumente timeout do cliente
- Use paginação para listas grandes
- Tente novamente com backoff

### "Connection refused"

**Verificar:**
1. URL correta (`https://api.dumontcloud.com`)
2. DNS resolvendo corretamente
3. Firewall não bloqueando

---

## Logs e Debugging

### Habilitar logs detalhados (CLI)

```bash
# Modo verbose
dumont --verbose instance list

# Debug completo
DUMONT_DEBUG=1 dumont instance list
```

### Verificar health da API

```bash
curl https://api.dumontcloud.com/health

# Response esperado:
# {"status": "healthy", "version": "1.2.0"}
```

---

## Contato e Suporte

Se o problema persistir:

1. **Documentação:** [docs.dumontcloud.com](https://docs.dumontcloud.com)
2. **Status:** [status.dumontcloud.com](https://status.dumontcloud.com)
3. **Discord:** [discord.gg/dumontcloud](https://discord.gg/dumontcloud)
4. **Email:** support@dumontcloud.com

Ao reportar, inclua:
- Request ID (header `X-Request-ID`)
- Timestamp
- Código de erro
- Corpo da requisição (sem senhas)

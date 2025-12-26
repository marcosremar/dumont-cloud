# Next Steps - Dumont Cloud
> Ações recomendadas baseadas nos testes de QA

## 🔴 Prioridade CRÍTICA (Fix antes de produção)

Nenhuma issue crítica encontrada. Sistema está operacional.

## 🟡 Prioridade ALTA (Fix em 1-2 dias)

### 1. Corrigir CLI Default Base URL
**Problema**: CLI requer `--base-url` explícito, senão falha ao carregar schema
**Impacto**: UX ruim para usuários do CLI
**Solução**:
```python
# Adicionar em cli.py
DEFAULT_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
```

**Teste**:
```bash
export DUMONT_API_URL=http://localhost:8000
dumont instance list  # Deve funcionar sem --base-url
```

### 2. Fix endpoint /api/advisor/recommend
**Problema**: Retorna 404 Not Found
**Impacto**: Feature de AI Advisor inacessível
**Ação**:
- Verificar se rota está registrada no router
- Verificar se é GET ou POST
- Adicionar testes

**Arquivo**: `src/api/v1/endpoints/advisor.py`

### 3. Melhorar error handling /api/chat/models
**Problema**: Retorna 400 sem mensagem clara
**Impacto**: Usuários não sabem que precisam configurar LLM provider
**Solução**:
```python
if not llm_provider_configured:
    raise HTTPException(
        status_code=400,
        detail="LLM provider not configured. Please set FIREWORKS_API_KEY or OPENAI_API_KEY in environment."
    )
```

### 4. Fix /api/spot/pricing query params
**Problema**: Retorna 400, provavelmente faltam params default
**Ação**:
- Adicionar query params com valores default
- Documentar params no OpenAPI schema

## 🟢 Prioridade MÉDIA (1 semana)

### 5. Adicionar Health Check para Agents
**Benefício**: Monitorar status de background agents
**Implementação**:
```python
@router.get("/health/agents")
def agents_health():
    return {
        "standby_manager": get_standby_manager().is_running(),
        "market_monitor": get_market_agent().is_running(),
        "auto_hibernation": get_auto_hibernation_manager().is_running(),
        "periodic_snapshot": get_periodic_snapshot_service().is_running(),
    }
```

### 6. Adicionar Integration Tests
**Objetivo**: Testar criação real de recursos com budget limitado
**Plano**:
```bash
# Criar GPU mais barata possível (< $0.02/hr)
pytest tests/integration/test_real_gpu_deploy.py --max-cost=0.02

# Testar snapshot real (< 1GB)
pytest tests/integration/test_real_snapshot.py --max-size=1GB

# Testar failover real (com timeout)
pytest tests/integration/test_real_failover.py --timeout=300
```

### 7. Melhorar OpenAPI Schema
**Ação**:
- Adicionar exemplos de request/response para todos endpoints
- Documentar query parameters obrigatórios
- Adicionar descriptions melhores

### 8. Rate Limiting
**Problema**: API não tem proteção contra abuse
**Solução**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/instances")
@limiter.limit("10/minute")
async def list_instances():
    ...
```

## 🔵 Prioridade BAIXA (1 mês)

### 9. Monitoring & Observability
**Implementar**:
- Prometheus metrics endpoint
- Grafana dashboards
- Log aggregation (ELK stack ou similar)
- Error tracking (Sentry)

### 10. CI/CD Pipeline
**Setup**:
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest tests/ -v
```

### 11. Performance Optimization
**Áreas**:
- Cache de queries frequentes (Redis)
- Database query optimization (EXPLAIN ANALYZE)
- Frontend code splitting
- API response compression

### 12. Security Hardening
**Checklist**:
- [ ] Implementar API key rotation
- [ ] Adicionar CSRF protection
- [ ] Setup HTTPS em produção
- [ ] Audit de dependências (pip-audit)
- [ ] Secrets scanning no CI

## 📊 Testes Adicionais Recomendados

### Testes de Carga
```bash
# Instalar ferramenta
pip install locust

# Criar locustfile.py
# Testar com 100 usuários simultâneos
locust -f tests/load/locustfile.py --users 100 --spawn-rate 10
```

### Testes de Segurança
```bash
# OWASP ZAP scan
docker run -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:8000

# SQL Injection scan
sqlmap -u "http://localhost:8000/api/instances?id=1" --batch

# XSS scan
python3 -m pip install xsstrike
xsstrike --url http://localhost:8000
```

### Testes de Failover Real
```bash
# Teste 1: CPU Standby failover
# 1. Deploy GPU instance
# 2. Enable CPU Standby
# 3. Simulate GPU failure
# 4. Verify CPU takes over
# 5. Recover GPU
# 6. Verify traffic moves back

# Teste 2: Warm Pool failover
# 1. Deploy GPU instance
# 2. Enable Warm Pool
# 3. Simulate GPU interruption
# 4. Verify Warm Pool instance takes over
# 5. Measure failover time (should be < 60s)
```

## 🎯 Roadmap de Features

### Q1 2025
- [ ] Multi-region support
- [ ] Auto-scaling based on load
- [ ] Advanced cost optimizer
- [ ] Mobile app (React Native)

### Q2 2025
- [ ] Kubernetes integration
- [ ] Terraform provider
- [ ] Webhooks para eventos
- [ ] SSO integration (Google, GitHub)

### Q3 2025
- [ ] Multi-cloud support (AWS, Azure, GCP)
- [ ] Advanced analytics dashboard
- [ ] ML-based price prediction
- [ ] Auto-negotiation com providers

## 📝 Documentação Necessária

### Para Usuários
- [ ] Quick Start Guide
- [ ] Tutoriais em vídeo
- [ ] FAQs expandido
- [ ] Troubleshooting guide
- [ ] Best practices

### Para Desenvolvedores
- [ ] Architecture deep dive
- [ ] API Reference completa
- [ ] Contributing guide
- [ ] Code style guide
- [ ] Testing guide

### Para Operações
- [ ] Deployment guide
- [ ] Monitoring setup
- [ ] Backup & recovery
- [ ] Incident response playbook
- [ ] Scaling guide

## 💡 Ideias de Melhorias

### UX
- Dashboard customizável (drag & drop widgets)
- Dark mode
- Notifications in-app
- Command palette (Cmd+K)
- Atalhos de teclado

### Performance
- GraphQL API (além de REST)
- WebSocket para updates real-time
- Edge caching (Cloudflare)
- Database read replicas

### Features
- Budget alerts
- Cost forecasting
- GPU comparisons side-by-side
- Saved searches/filters
- Export to CSV/JSON

## 📞 Suporte

Para questões sobre os testes ou próximos passos:
- Ler relatórios: `TESTE_REPORT.md` e `TESTE_SUMMARY.md`
- Executar testes: `./TEST_COMMANDS.sh`
- Abrir issue no repositório

---

**Última atualização**: 2025-12-26
**Próxima revisão**: Após implementar fixes de prioridade ALTA

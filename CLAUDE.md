# Dumont Cloud - Instruções para Claude

## Testes

### Regra Principal: Sempre Testes REAIS

**NUNCA usar mocks para testes de infraestrutura.** Todos os testes devem ser executados em máquinas reais da VAST.ai.

### Seleção de GPUs para Testes

Ao provisionar GPUs para testes, seguir estas prioridades:

1. **Custo**: Escolher GPUs mais baratas (< $0.10/hr quando possível)
2. **Localização**: Evitar máquinas na China/Ásia - preferir:
   - Estados Unidos (US)
   - Europa (EU)
   - América do Sul (ideal para baixa latência)
3. **Confiabilidade**: Preferir máquinas com `reliability >= 0.90`
4. **Velocidade de boot**: GPUs menores iniciam mais rápido (GTX 1080, RTX 2080, Quadro P2000)

### Exemplo de Query para GPUs de Teste

```python
# Buscar GPUs baratas e próximas
query = {
    "rentable": {"eq": True},
    "dph_total": {"lte": 0.10},  # Max $0.10/hr
    "geolocation": {"in": ["US", "EU", "BR", "CA"]},  # Evitar Ásia
    "reliability2": {"gte": 0.90},
    "order": [["dph_total", "asc"]]
}
```

### GPUs Recomendadas para Testes

| GPU | Preço Típico | Boot Time | Uso Recomendado |
|-----|-------------|-----------|-----------------|
| Quadro P2000 | $0.01-0.03/hr | ~30s | Testes rápidos, widget |
| GTX 1080 | $0.03-0.05/hr | ~30s | Testes de code-server |
| GTX 1080 Ti | $0.03-0.06/hr | ~45s | Fine-tuning leve |
| RTX 2080 | $0.05-0.08/hr | ~45s | Testes de inferência |
| RTX 3090 | $0.08-0.15/hr | ~60s | Fine-tuning completo |

### Não Usar para Testes

- A100, H100 (caros e demoram para iniciar)
- Máquinas na China (alta latência)
- Máquinas com reliability < 0.85

## Arquitetura

### Failover GPU → CPU

```
┌─────────────────┐         ┌─────────────────┐
│  GPU Vast.ai    │  rsync  │  GCP CPU        │
│  (principal)    │ ──────► │  (standby)      │
└─────────────────┘  30s    └─────────────────┘
```

- CPU Standby é **obrigatório** para fine-tuning
- Checkpoints sincronizados a cada 30 segundos
- Failover automático quando GPU falha

### Widget de Failover (VS Code)

O widget no code-server mostra:
- Status atual (GPU verde / CPU azul)
- Botão de migração manual
- Configurações de auto-migração (padrão: 10 min inativo)

## API Keys

- VAST.ai: Armazenada em `.env` como `VAST_API_KEY`
- GCP: Service account em `~/.config/gcloud/`

## Comandos Úteis

```bash
# Verificar saldo VAST.ai
python3 -c "
import requests
with open('.env') as f:
    for line in f:
        if 'VAST_API_KEY' in line:
            key = line.split('=')[1].strip()
r = requests.get('https://console.vast.ai/api/v0/users/current/',
                 headers={'Authorization': f'Bearer {key}'})
print(f'Saldo: \${r.json().get(\"credit\", 0):.2f}')
"

# Listar instâncias ativas
python3 -c "
import requests
with open('.env') as f:
    for line in f:
        if 'VAST_API_KEY' in line:
            key = line.split('=')[1].strip()
r = requests.get('https://console.vast.ai/api/v0/instances/',
                 headers={'Authorization': f'Bearer {key}'})
for i in r.json().get('instances', []):
    print(f'{i[\"id\"]}: {i[\"gpu_name\"]} - {i[\"actual_status\"]}')
"
```

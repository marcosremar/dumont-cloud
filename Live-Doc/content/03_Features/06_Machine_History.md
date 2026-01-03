# Machine History & Reliability

## Visao Geral

O sistema de Machine History rastreia o historico de confiabilidade de cada host GPU. Use essas informacoes para escolher maquinas mais estaveis e evitar hosts problematicos.

---

## Metricas Rastreadas

### Por Host

| Metrica | Descricao |
|---------|-----------|
| Uptime | % de tempo online |
| Interrupcoes | Numero de falhas |
| MTBF | Tempo medio entre falhas |
| MTTR | Tempo medio para recuperar |
| Rating | Score de 1-5 estrelas |

### Por GPU

| Metrica | Descricao |
|---------|-----------|
| Performance | Benchmark relativo |
| Temperatura | Media e picos |
| Throttling | Frequencia de throttle |
| Erros | Erros de memoria/CUDA |

---

## Reliability Score

### Calculo

```
Score = (uptime * 0.4) + (mtbf * 0.3) + (rating * 0.3)
```

### Classificacao

| Score | Classificacao | Recomendacao |
|-------|--------------|--------------|
| 4.5+ | Excelente | Producao |
| 4.0-4.5 | Bom | Staging |
| 3.5-4.0 | Regular | Dev com failover |
| < 3.5 | Ruim | Evitar |

---

## Dashboard

### Visualizar Historico

1. **Market** > **Machine History**
2. Filtre por:
   - GPU type
   - Regiao
   - Score minimo
3. Veja detalhes de cada host

### Informacoes Disponiveis

- Grafico de uptime (30 dias)
- Lista de interrupcoes
- Reviews de usuarios
- Comparativo com media

---

## Blacklist

### Bloquear Host

Se um host te causou problemas:

1. **Machines** > Sua instancia
2. **Actions** > **Report Host**
3. Descreva o problema
4. Host adicionado a sua blacklist

### Via API

```bash
curl -X POST /api/v1/hosts/blacklist \
  -d '{"host_id": "host123", "reason": "Frequent disconnections"}'
```

### Gerenciar Blacklist

```bash
# Listar
curl /api/v1/hosts/blacklist

# Remover
curl -X DELETE /api/v1/hosts/blacklist/{host_id}
```

---

## Preferencias

### Configurar Preferencias

1. **Settings** > **Instance Preferences**
2. Configure:
   - Score minimo (ex: 4.0)
   - Blacklist global
   - Preferir hosts conhecidos

### Via API

```bash
curl -X PUT /api/v1/users/me/preferences \
  -d '{
    "min_reliability_score": 4.0,
    "prefer_known_hosts": true,
    "auto_blacklist_threshold": 3
  }'
```

---

## Contribuindo com Reviews

### Avaliar Host

Apos usar uma maquina:

1. **Machines** > Instancia finalizada
2. Clique em **"Rate Host"**
3. De uma nota (1-5 estrelas)
4. Adicione comentario (opcional)

### Impacto

- Reviews afetam o score do host
- Ajuda outros usuarios
- Hosts ruins sao removidos automaticamente

---

## API

### Consultar Historico

```bash
curl /api/v1/hosts/{host_id}/history
```

### Resposta

```json
{
  "host_id": "host123",
  "gpu_type": "RTX_4090",
  "reliability_score": 4.2,
  "uptime_30d": 98.5,
  "interruptions_30d": 3,
  "mtbf_hours": 168,
  "avg_rating": 4.1,
  "total_reviews": 47
}
```

### Buscar Melhores Hosts

```bash
curl /api/v1/hosts/top?gpu_type=RTX_4090&min_score=4.0&limit=10
```

---

## Melhores Praticas

1. **Defina score minimo** - 4.0+ para producao
2. **Use blacklist** - Evite hosts problematicos
3. **Avalie hosts** - Ajude a comunidade
4. **Monitore MTBF** - Prefira hosts com alto MTBF
5. **Combine com Warm Pool** - Protecao extra

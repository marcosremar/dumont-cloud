# Dumont Cloud - Chat Arena Deployment Report

**Data:** 2026-01-03
**Status:** ✅ DEPLOYED & TESTED

---

## Executive Summary

Dois modelos leves foram deployados com sucesso na VAST.ai para demonstração do Chat Arena:

- **Llama 3.2 3B** - RTX 3080 (Noruega)
- **Qwen 2.5 3B** - RTX 3060 (Carolina do Norte, EUA)

**Custo total:** $0.0874/hora ($2.10/dia se mantidos 24h)

---

## Deployment Details

### Instance 1: Llama 3.2 3B

```yaml
Instance ID: 29449056
Model: llama3.2:3b (2.0 GB)
GPU: RTX 3080 (10GB VRAM)
Location: Norway, NO
Cost: $0.0489/hora
SSH: ssh9.vast.ai:19056
Ollama: http://ssh9.vast.ai:11434
Deploy Time: 169.2s
  - Create: 0.8s
  - Ready: 62.5s
  - Install: 105.9s
Status: ✅ ONLINE & TESTED
```

### Instance 2: Qwen 2.5 3B

```yaml
Instance ID: 29449112
Model: qwen2.5:3b (1.9 GB)
GPU: RTX 3060 (12GB VRAM)
Location: North Carolina, US
Cost: $0.0385/hora
SSH: ssh7.vast.ai:19112
Ollama: http://ssh7.vast.ai:11434
Deploy Time: 122.8s
  - Create: 0.5s
  - Ready: 31.3s
  - Install: 91.0s
Status: ✅ ONLINE & TESTED
```

---

## Performance Metrics

### Deploy Performance

| Metric | Llama 3.2 3B | Qwen 2.5 3B |
|--------|--------------|-------------|
| Instance Creation | 0.8s | 0.5s |
| Ready Time | 62.5s | 31.3s |
| Model Install | 105.9s | 91.0s |
| **Total** | **169.2s** | **122.8s** |

### GPU Utilization (at idle)

- **Llama 3.2 3B:** 2929 MB / 10240 MB (28% VRAM)
- **Qwen 2.5 3B:** 2457 MB / 12288 MB (20% VRAM)

---

## Chat Arena Test Results

Ambos os modelos foram testados com 5 perguntas variadas:

### Question 1: Capital of France
- **Llama 3.2:** "The capital of France is Paris."
- **Qwen 2.5:** "The capital of France is Paris."
- **Winner:** Tie (both correct)

### Question 2: Haiku about Coding
- **Llama 3.2:**
  ```
  Lines of code descend
  Logic's gentle, guiding hand
  Beauty in the screen
  ```
- **Qwen 2.5:**
  ```
  Syntax dances light,
  Code whispers secrets soft,
  Programs dance to code.
  ```
- **Winner:** Subjective (both creative)

### Question 3: Quantum Computing Explanation
- **Llama 3.2:** Long explanation (45 words) - clear but exceeded 2 sentence limit
- **Qwen 2.5:** Concise (29 words) - followed instructions better
- **Winner:** Qwen 2.5 (better instruction following)

### Question 5: Name 3 Programming Languages
- **Llama 3.2:** Simple list (Python, Java, C++)
- **Qwen 2.5:** Detailed explanations with use cases
- **Winner:** Depends on use case (Llama for brevity, Qwen for detail)

---

## Cost Analysis

### Hourly Costs
- Llama 3.2 3B: $0.0489/hora
- Qwen 2.5 3B: $0.0385/hora
- **Total:** $0.0874/hora

### Daily Projections (24h)
- Llama 3.2 3B: $1.17/dia
- Qwen 2.5 3B: $0.92/dia
- **Total:** $2.10/dia

### 5-Minute Test Cost
- **Total:** $0.0073

---

## Access Instructions

### SSH Access

```bash
# Llama 3.2 3B
ssh -p 19056 root@ssh9.vast.ai

# Qwen 2.5 3B
ssh -p 19112 root@ssh7.vast.ai
```

### Test Models Interactively

```bash
# On Llama instance
ollama run llama3.2:3b

# On Qwen instance
ollama run qwen2.5:3b
```

### API Access (if needed)

```bash
# Llama 3.2 3B
curl http://ssh9.vast.ai:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Why is the sky blue?"
}'

# Qwen 2.5 3B
curl http://ssh7.vast.ai:11434/api/generate -d '{
  "model": "qwen2.5:3b",
  "prompt": "Why is the sky blue?"
}'
```

---

## Cleanup Instructions

### Option 1: Automated Cleanup

```bash
cd /Users/marcos/CascadeProjects/dumontcloud
python3 scripts/deploy_chat_arena_models.py --cleanup
```

### Option 2: Manual Cleanup

```bash
# Via VAST.ai CLI
vast destroy instance 29449056
vast destroy instance 29449112

# Or via Python
python3 -c "
from src.services.gpu.vast import VastService
import os
vast = VastService(os.getenv('VAST_API_KEY'))
vast.destroy_instance(29449056)
vast.destroy_instance(29449112)
print('Instances destroyed')
"
```

---

## Files Generated

1. **chat_arena_deployment.json** - Deployment metadata
2. **scripts/deploy_chat_arena_models.py** - Deployment script
3. **scripts/test_chat_arena.py** - Test script
4. **CHAT_ARENA_DEPLOYMENT_REPORT.md** - This report

---

## Recommendations

### For Production Use

1. **Load Balancing:** Use Nginx/HAProxy to distribute requests
2. **Monitoring:** Add Prometheus/Grafana for metrics
3. **Auto-scaling:** Add more instances during peak hours
4. **Backup Strategy:** Regular snapshots via Restic/B2
5. **Cost Optimization:**
   - Use spot instances (already done)
   - Auto-pause during low traffic
   - Implement serverless mode for idle periods

### Model Selection for Different Use Cases

- **Llama 3.2 3B:** Better for factual Q&A, concise responses
- **Qwen 2.5 3B:** Better for detailed explanations, creative tasks

### Next Steps

1. ✅ Deploy 2 models (DONE)
2. ✅ Test inference (DONE)
3. ⏳ Integrate with Chat Arena UI
4. ⏳ Add model comparison voting
5. ⏳ Implement load balancing
6. ⏳ Add monitoring dashboards

---

## Technical Validation

### ✅ Checks Passed

- [x] Both instances created successfully
- [x] SSH access working
- [x] Ollama installed and running
- [x] Models pulled and loaded
- [x] Inference tested successfully
- [x] GPU memory within limits
- [x] Network connectivity verified
- [x] Cost tracking accurate

### ⚠️ Known Issues

1. **Webhook Database Error:** Non-critical warning about missing `webhook_configs` table
   - Does not affect deployment
   - Only impacts webhook notifications

2. **Question 4 Parse Error:** Shell quoting issue with apostrophes in prompts
   - Workaround: Escape quotes properly in production
   - Not affecting other questions

---

## Budget Tracking

### VAST.ai Account Status
- Starting Balance: $8.25
- Deployment Cost: ~$0.01 (provisioning + 5 min test)
- **Remaining Balance:** ~$8.24

### Burn Rate
- **Current:** $0.0874/hora
- **If left running 24h:** -$2.10/dia
- **Days until balance exhausted:** ~3.9 days

**ACTION REQUIRED:** Remember to cleanup instances when testing is complete!

---

## Conclusion

✅ **Deployment Successful!**

Dois modelos leves estão rodando em GPUs diferentes, prontos para demonstração do Chat Arena. O sistema está funcional, com custos controlados e performance adequada para modelos de 3B parâmetros.

**Total deployment time:** ~15 minutos
**Total cost:** $0.0073 (5-minute test)
**Success rate:** 100% (2/2 models deployed)

---

**Generated:** 2026-01-03T01:45:00
**Script:** /Users/marcos/CascadeProjects/dumontcloud/scripts/deploy_chat_arena_models.py

# Dumont Cloud SDK

SDK Python completo para gerenciamento de GPUs cloud com inferência LLM e failover automático.

## Funcionalidades

- **Gerenciamento de Instâncias** - Listar, criar, pausar, resumir, destruir GPUs
- **Snapshots** - Backup e restore ultra-rápido
- **Wizard Deploy** - Deploy multi-start (batches de máquinas em paralelo)
- **Modelos LLM** - Instalação de Ollama e modelos via SSH
- **Inferência com Failover** - GPU → OpenRouter automático

## Instalação

```bash
pip install dumont-sdk
```

## Uso Rápido

```python
import asyncio
from dumont_sdk import DumontClient

async def main():
    async with DumontClient(api_key="dumont_sk_...") as client:
        # Listar instâncias
        instances = await client.instances.list()
        for inst in instances:
            print(f"{inst.id}: {inst.gpu_name} - {inst.status}")

        # Deploy rápido
        result = await client.wizard.deploy(
            gpu_name="RTX 4090",
            max_price=1.5
        )
        print(f"SSH: {result.ssh_command}")

        # Instalar modelo
        await client.models.install(result.instance_id, "llama3.2")

        # Inferência com failover
        response = await client.llm.complete("Olá!")
        print(response)

asyncio.run(main())
```

## Módulos

### Instâncias (`client.instances`)

```python
# Listar todas as instâncias
instances = await client.instances.list()

# Buscar ofertas de GPU
offers = await client.instances.search_offers(
    gpu_name="RTX 4090",
    max_price=2.0,
    region="EU"
)

# Criar instância
instance = await client.instances.create(
    offer_id=offers[0].id,
    disk_size=100,
    label="minha-gpu"
)

# Pausar/Resumir
await client.instances.pause(instance.id)
await client.instances.resume(instance.id)

# Destruir
await client.instances.destroy(instance.id)

# Sync de dados
await client.instances.sync(instance.id, source_path="/workspace")
```

### Snapshots (`client.snapshots`)

```python
# Listar snapshots
snapshots = await client.snapshots.list()

# Criar snapshot
snapshot = await client.snapshots.create(
    instance_id=12345,
    label="antes-do-deploy"
)

# Restaurar
await client.snapshots.restore(
    snapshot_id=snapshot.id,
    instance_id=12345
)

# Snapshot mais recente
latest = await client.snapshots.latest(instance_id=12345)
```

### Wizard Deploy (`client.wizard`)

Deploy multi-start: cria várias máquinas em paralelo, a primeira que ficar pronta ganha.

```python
# Deploy com callback de progresso
def on_progress(status, data):
    print(f"[{status}] {data}")

client.wizard.on_progress(on_progress)

result = await client.wizard.deploy(
    gpu_name="RTX 4090",
    max_price=1.5,
    region="EU",
    speed="fast",          # fast, balanced, cheap
    batch_size=5,          # Máquinas por batch
    max_batches=3,         # Máximo de batches
    timeout_per_batch=90,  # Segundos por batch
)

if result.success:
    print(f"Instance: {result.instance_id}")
    print(f"SSH: {result.ssh_command}")
    print(f"Ready in: {result.ready_time:.1f}s")
```

### Modelos LLM (`client.models`)

```python
# Instalar Ollama + modelo
result = await client.models.install(
    instance_id=12345,
    model="llama3.2"
)
print(f"Ollama URL: {result.ollama_url}")

# Listar modelos instalados
models = await client.models.list(instance_id=12345)

# Executar prompt
response = await client.models.run(
    instance_id=12345,
    model="llama3.2",
    prompt="Hello!"
)

# Remover modelo
await client.models.remove(instance_id=12345, model="llama3.2")
```

### Inferência com Failover (`client.llm`)

O tráfego pesado vai DIRETO para GPU ou OpenRouter, sem sobrecarregar o servidor Dumont.

```python
# Inferência simples
response = await client.llm.complete("Olá!")
print(client.llm.get_content(response))

# Com system prompt
response = await client.llm.complete(
    prompt="Explique ML em 2 frases",
    system="Você é um assistente técnico."
)

# Chat com histórico
messages = [
    {"role": "system", "content": "Você é um assistente."},
    {"role": "user", "content": "Olá!"},
]
response = await client.llm.chat(messages)

# Streaming
async for chunk in client.llm.stream("Conte uma história"):
    print(chunk, end="", flush=True)

# Verificar fonte (GPU ou fallback)
print(response.get("_source"))  # "gpu" ou "fallback"
```

## Autenticação

```python
# Login
await client.login("user@email.com", "password")

# Verificar usuário
user = await client.me()

# Logout
await client.logout()
```

## Variáveis de Ambiente

```bash
export DUMONT_API_KEY=dumont_sk_...
export DUMONT_SERVER=https://api.dumontcloud.com
export OPENROUTER_API_KEY=sk-or-...
```

## Arquitetura de Failover LLM

```
┌─────────────────────────────────────────────────────────────┐
│                     Sua Aplicação                           │
│                          │                                  │
│                    Dumont SDK                               │
│                          │                                  │
│         ┌────────────────┴────────────────┐                 │
│         ▼                                 ▼                 │
│   ┌───────────┐                    ┌─────────────┐          │
│   │ Sua GPU   │ ─── Se falhar ───► │ OpenRouter  │          │
│   │ (direto)  │                    │  (direto)   │          │
│   └───────────┘                    └─────────────┘          │
└─────────────────────────────────────────────────────────────┘

                            │
                            ▼
               ┌─────────────────────────┐
               │  Dumont Cloud Server    │
               │  (só config, 1 request) │
               └─────────────────────────┘
```

## Comparação CLI vs SDK

| Funcionalidade | CLI | SDK |
|----------------|-----|-----|
| Instâncias | `dumont instance list` | `await client.instances.list()` |
| Wizard Deploy | `dumont wizard deploy` | `await client.wizard.deploy()` |
| Instalar Modelo | `dumont model install` | `await client.models.install()` |
| Snapshots | `dumont snapshot list` | `await client.snapshots.list()` |
| LLM Failover | - | `await client.llm.complete()` |

## License

MIT

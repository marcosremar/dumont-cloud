"""
Exemplo básico de uso do Dumont SDK.

Este exemplo mostra como usar o SDK para fazer inferência LLM
com failover automático GPU → OpenRouter.
"""
import asyncio
import os
from dumont_sdk import DumontLLM, DumontConfig, GPUConfig, FallbackModel


async def exemplo_basico():
    """Uso mais simples - SDK busca config do servidor."""

    # Opção 1: Usando API key do Dumont Cloud
    # O SDK busca automaticamente a config do servidor
    client = DumontLLM(api_key=os.getenv("DUMONT_API_KEY"))

    response = await client.complete(
        prompt="Explique o que é machine learning em 2 frases.",
        system="Você é um assistente técnico conciso."
    )

    print("Resposta:", client.get_content(response))
    print("Fonte:", response.get("_source"))  # "gpu" ou "fallback"

    await client.close()


async def exemplo_config_manual():
    """Configuração manual - sem precisar do servidor Dumont."""

    # Configura GPU diretamente
    config = DumontConfig(
        gpu=GPUConfig(
            url="http://192.168.1.100:8000",  # IP da sua GPU
            model="llama-3.1-70b",
            timeout=60.0,
        ),
        fallback_models=[
            FallbackModel(provider="openrouter", model="openai/gpt-4o-mini", priority=0),
            FallbackModel(provider="openrouter", model="anthropic/claude-3.5-sonnet", priority=1),
        ],
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        auto_failover=True,
    )

    async with DumontLLM(config=config) as client:
        response = await client.complete("Olá, quem é você?")
        print("Resposta:", client.get_content(response))


async def exemplo_chat():
    """Exemplo de chat com múltiplas mensagens."""

    client = DumontLLM(api_key=os.getenv("DUMONT_API_KEY"))

    messages = [
        {"role": "system", "content": "Você é um assistente de programação Python."},
        {"role": "user", "content": "Como faço um list comprehension?"},
    ]

    response = await client.chat(messages, temperature=0.7)
    print("Resposta:", client.get_content(response))

    # Continua a conversa
    messages.append({"role": "assistant", "content": client.get_content(response)})
    messages.append({"role": "user", "content": "Agora com filter e map juntos."})

    response = await client.chat(messages)
    print("Resposta:", client.get_content(response))

    await client.close()


async def exemplo_streaming():
    """Exemplo com streaming de resposta."""

    client = DumontLLM(api_key=os.getenv("DUMONT_API_KEY"))

    print("Resposta: ", end="", flush=True)
    async for chunk in client.stream("Conte uma história curta sobre um robô."):
        print(chunk, end="", flush=True)
    print()  # Nova linha no final

    await client.close()


async def exemplo_failover_forcado():
    """Exemplo forçando failover (GPU fake para testar)."""

    config = DumontConfig(
        gpu=GPUConfig(
            url="http://192.168.255.255:8000",  # GPU inexistente
            timeout=5.0,  # Timeout curto
        ),
        fallback_models=[
            FallbackModel(provider="openrouter", model="openai/gpt-4o-mini", priority=0),
        ],
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        auto_failover=True,
        retry_gpu_count=1,  # Só 1 tentativa antes de failover
    )

    async with DumontLLM(config=config) as client:
        response = await client.complete("Olá!")

        print("Resposta:", client.get_content(response))
        print("Fonte:", response.get("_source"))  # Deve ser "fallback"
        print("Modelo usado:", response.get("_fallback_model"))


async def exemplo_env_vars():
    """Exemplo usando variáveis de ambiente."""

    # Configure as seguintes variáveis:
    # DUMONT_API_KEY=dumont_sk_...
    # DUMONT_GPU_URL=http://gpu-ip:8000  (opcional)
    # OPENROUTER_API_KEY=sk-or-...
    # DUMONT_FALLBACK_MODELS=openrouter/openai/gpt-4o-mini,openrouter/anthropic/claude-3.5-sonnet

    # O SDK carrega automaticamente do ambiente
    config = DumontConfig.from_env()

    async with DumontLLM(config=config) as client:
        response = await client.complete("Teste de config via env vars")
        print("Resposta:", client.get_content(response))


if __name__ == "__main__":
    print("=== Exemplo Básico ===")
    asyncio.run(exemplo_basico())

    print("\n=== Exemplo Config Manual ===")
    asyncio.run(exemplo_config_manual())

    print("\n=== Exemplo Streaming ===")
    asyncio.run(exemplo_streaming())

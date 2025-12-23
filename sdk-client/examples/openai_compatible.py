"""
Exemplo usando OpenAI SDK apontando para Dumont Proxy.

Se você prefere usar o SDK oficial da OpenAI, pode apontar
para o proxy do Dumont Cloud que cuida do failover.

NOTA: Este método passa tráfego pelo servidor Dumont.
Para evitar isso, use o dumont_sdk diretamente.
"""
import os
from openai import OpenAI


def exemplo_openai_sdk():
    """
    Usa o SDK oficial da OpenAI apontando para o proxy Dumont.

    O proxy Dumont:
    1. Tenta rotear para sua GPU
    2. Se falhar, redireciona para OpenRouter

    Vantagem: Não precisa mudar código existente.
    Desvantagem: Tráfego passa pelo servidor Dumont.
    """
    client = OpenAI(
        base_url="https://api.dumontcloud.com/v1",
        api_key=os.getenv("DUMONT_API_KEY"),
    )

    response = client.chat.completions.create(
        model="gpu:default",  # Usa GPU, fallback automático
        messages=[
            {"role": "system", "content": "Você é um assistente."},
            {"role": "user", "content": "Olá!"},
        ],
    )

    print("Resposta:", response.choices[0].message.content)


def exemplo_modelo_especifico():
    """Força um modelo específico."""
    client = OpenAI(
        base_url="https://api.dumontcloud.com/v1",
        api_key=os.getenv("DUMONT_API_KEY"),
    )

    # Força usar OpenRouter diretamente (ignora GPU)
    response = client.chat.completions.create(
        model="openrouter/openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Teste"}],
    )

    print("Resposta:", response.choices[0].message.content)


def exemplo_streaming():
    """Streaming com OpenAI SDK."""
    client = OpenAI(
        base_url="https://api.dumontcloud.com/v1",
        api_key=os.getenv("DUMONT_API_KEY"),
    )

    stream = client.chat.completions.create(
        model="gpu:llama-70b",
        messages=[{"role": "user", "content": "Conte uma história curta."}],
        stream=True,
    )

    print("Resposta: ", end="")
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


if __name__ == "__main__":
    print("=== OpenAI SDK com Dumont Proxy ===")
    exemplo_openai_sdk()

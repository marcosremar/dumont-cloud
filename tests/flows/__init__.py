"""
Testes de Fluxo - Dumont Cloud

Testes REAIS contra a API, sem mocks.
Organizados por fluxo de usuário.

Fluxos:
    1. Deploy de Modelos (LLM, Whisper, Embeddings)
    2. Job GPU (Execute & Destroy)
    3. Desenvolvimento Interativo + Serverless
    4. API Inferência Serverless
    5. Alta Disponibilidade (CPU Standby + Failover)
    6. Warm Pool
    7. Monitoramento e Métricas
    8. Autenticação e Configurações

Uso:
    # Rodar todos os testes de fluxo (sem GPU real)
    pytest tests/flows/ -v -m "not real_gpu"

    # Rodar testes de um fluxo específico
    pytest tests/flows/ -v -m flow1

    # Rodar TODOS os testes (incluindo GPU real - CUSTA $$$)
    pytest tests/flows/ -v

Markers:
    flow1-flow8: Testes por fluxo
    real_gpu: Requer GPU real (custa dinheiro)
    slow: Testes lentos (>1 min)
    destructive: Pode destruir recursos
"""

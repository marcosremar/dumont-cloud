#!/usr/bin/env python3
"""Script de teste para o agente de monitoramento de preços."""

import sys
import os
import time

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.agent_manager import agent_manager
from src.services.price_monitor_agent import PriceMonitorAgent
from src.config.database import SessionLocal
from src.models.price_history import PriceHistory
import json

def load_config():
    """Carrega configuração do usuário."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def test_agent():
    """Testa o agente de monitoramento."""
    print("=" * 60)
    print("TESTE DO AGENTE DE MONITORAMENTO DE PREÇOS")
    print("=" * 60)

    # Carregar API key
    config = load_config()
    vast_api_key = None
    for user_data in config.get('users', {}).values():
        vast_api_key = user_data.get('vast_api_key')
        if vast_api_key:
            break

    if not vast_api_key:
        print("❌ Erro: Nenhuma API key encontrada no config.json")
        print("Configure via: /api/settings")
        return

    print(f"✓ API key encontrada: {vast_api_key[:10]}...")

    # Criar agente
    print("\n1. Criando agente de monitoramento...")
    agent = PriceMonitorAgent(
        vast_api_key=vast_api_key,
        interval_minutes=1,  # 1 minuto para teste
        gpus_to_monitor=['RTX 4090', 'RTX 4080']
    )
    print(f"✓ Agente criado: {agent.name}")

    # Executar um ciclo de monitoramento manualmente
    print("\n2. Executando ciclo de monitoramento...")
    try:
        agent._monitor_cycle()
        print("✓ Ciclo de monitoramento concluído")
    except Exception as e:
        print(f"❌ Erro no ciclo de monitoramento: {e}")
        import traceback
        traceback.print_exc()
        return

    # Verificar dados no banco
    print("\n3. Verificando dados no banco de dados...")
    db = SessionLocal()
    try:
        records = db.query(PriceHistory).order_by(PriceHistory.timestamp.desc()).limit(5).all()

        if records:
            print(f"✓ Encontrados {len(records)} registros no banco:")
            for record in records:
                print(f"  - {record.gpu_name}: avg=${record.avg_price:.4f}/h, "
                      f"ofertas={record.total_offers}, "
                      f"timestamp={record.timestamp}")
        else:
            print("⚠️  Nenhum registro encontrado no banco")
    finally:
        db.close()

    # Testar estatísticas do agente
    print("\n4. Estatísticas do agente:")
    stats = agent.get_stats()
    print(f"  - Nome: {stats['name']}")
    print(f"  - Rodando: {stats['running']}")
    print(f"  - Intervalo: {stats['interval_minutes']} minutos")
    print(f"  - GPUs: {', '.join(stats['gpus_monitored'])}")
    print(f"  - Últimos preços: {stats['last_prices']}")

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO COM SUCESSO! ✓")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Inicie o servidor: python3 app.py")
    print("2. Acesse: http://localhost:8766/api/price-monitor/status")
    print("3. Veja o histórico: http://localhost:8766/api/price-monitor/history")

if __name__ == "__main__":
    test_agent()

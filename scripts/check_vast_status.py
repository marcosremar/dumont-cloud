#!/usr/bin/env python3
"""
Script rápido para verificar status da conta VAST.ai
- Saldo atual
- Instâncias ativas
- Custo por hora de instâncias ativas
"""
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.gpu.vast import VastService
from dotenv import load_dotenv

load_dotenv()

VAST_API_KEY = os.getenv("VAST_API_KEY")
if not VAST_API_KEY:
    print("❌ VAST_API_KEY não encontrado no .env")
    sys.exit(1)


def main():
    vast = VastService(VAST_API_KEY)

    print("="*60)
    print("🔍 VAST.AI STATUS CHECK")
    print("="*60)
    print(f"Data: {datetime.now().isoformat()}")
    print()

    # 1. Verificar saldo
    print("💰 SALDO DA CONTA")
    print("-"*60)
    balance = vast.get_balance()
    credit = balance.get("credit", 0)
    balance_value = balance.get("balance", 0)
    email = balance.get("email", "N/A")

    print(f"Email: {email}")
    print(f"Crédito disponível: ${credit:.4f}")
    print(f"Saldo: ${balance_value:.4f}")

    if credit < 0.10:
        print("⚠️  ATENÇÃO: Crédito muito baixo!")
        print("   Adicione créditos em: https://cloud.vast.ai/billing/")
    elif credit < 1.00:
        print("⚠️  Crédito baixo. Recomendado adicionar mais.")
    else:
        print("✅ Crédito suficiente para testes")

    # 2. Listar instâncias ativas
    print("\n📋 INSTÂNCIAS ATIVAS")
    print("-"*60)
    instances = vast.list_instances()

    if not instances:
        print("✅ Nenhuma instância ativa (sem custos)")
    else:
        total_cost = 0
        print(f"Total: {len(instances)} instância(s)")
        print()

        for inst in instances:
            inst_id = inst.get("id")
            status = inst.get("actual_status", "unknown")
            gpu_name = inst.get("gpu_name", "N/A")
            dph = inst.get("dph_total", 0)
            label = inst.get("label", "N/A")

            total_cost += dph

            print(f"ID: {inst_id}")
            print(f"  Status: {status}")
            print(f"  GPU: {gpu_name}")
            print(f"  Label: {label}")
            print(f"  Custo: ${dph:.4f}/hora")
            print()

        print(f"💰 Custo total: ${total_cost:.4f}/hora")
        print(f"   Estimado (24h): ${total_cost * 24:.2f}")
        print(f"   Estimado (7d): ${total_cost * 24 * 7:.2f}")

        print("\n⚠️  Para desligar instâncias:")
        for inst in instances:
            inst_id = inst.get("id")
            print(f"   vast destroy instance {inst_id}")

    # 3. Verificar deployment anterior
    print("\n📄 DEPLOYMENT ANTERIOR")
    print("-"*60)
    deployment_file = "chat_arena_deployment.json"
    if os.path.exists(deployment_file):
        with open(deployment_file) as f:
            data = json.load(f)

        timestamp = data.get("timestamp")
        cost_per_hour = data.get("total_cost_per_hour", 0)
        deployed_instances = data.get("instances", [])

        print(f"Arquivo: {deployment_file}")
        print(f"Data: {timestamp}")
        print(f"Custo registrado: ${cost_per_hour:.4f}/hora")
        print(f"Instâncias deployadas: {len(deployed_instances)}")
        print()

        for inst in deployed_instances:
            inst_id = inst.get("instance_id")
            model_name = inst.get("model_name")
            endpoint = inst.get("ollama_endpoint")
            print(f"  - {model_name} (ID: {inst_id})")
            print(f"    Endpoint: {endpoint}")
    else:
        print("Nenhum deployment anterior encontrado")

    print()
    print("="*60)


if __name__ == "__main__":
    main()

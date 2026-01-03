#!/usr/bin/env python3
"""
Test Chat Arena - Compara respostas dos dois modelos deployados

Este script testa os modelos deployados com perguntas variadas e
compara suas respostas.
"""
import json
import subprocess
import sys
from typing import Dict, List, Tuple


def load_deployment() -> Dict:
    """Carrega configuração do deployment"""
    with open("chat_arena_deployment.json") as f:
        return json.load(f)


def query_model(ssh_host: str, ssh_port: int, model_name: str, prompt: str, timeout: int = 30) -> Tuple[bool, str]:
    """Executa query em um modelo via SSH"""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-p", str(ssh_port),
                f"root@{ssh_host}",
                f"ollama run {model_name} '{prompt}'"
            ],
            capture_output=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            return True, result.stdout.decode().strip()
        else:
            return False, result.stderr.decode().strip()

    except subprocess.TimeoutExpired:
        return False, f"Timeout ({timeout}s)"
    except Exception as e:
        return False, str(e)


def test_arena():
    """Testa Chat Arena com múltiplas perguntas"""
    deployment = load_deployment()
    instances = deployment["instances"]

    if len(instances) < 2:
        print("Erro: Necessário pelo menos 2 instâncias deployadas")
        sys.exit(1)

    model1 = instances[0]
    model2 = instances[1]

    print("="*80)
    print("DUMONT CLOUD - CHAT ARENA TEST")
    print("="*80)
    print(f"\nModel 1: {model1['model_name']} ({model1['gpu_name']})")
    print(f"Model 2: {model2['model_name']} ({model2['gpu_name']})")
    print(f"\nCusto total: ${deployment['total_cost_per_hour']:.4f}/hora")

    # Perguntas de teste
    questions = [
        "What is the capital of France? Answer in one sentence.",
        "Write a haiku about coding.",
        "Explain quantum computing in simple terms (2 sentences max).",
        "What's 15 * 23? Show your work.",
        "Name 3 programming languages.",
    ]

    print("\n" + "="*80)
    print("ARENA BATTLE - Side by Side Comparison")
    print("="*80)

    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"Question {i}: {question}")
        print(f"{'='*80}")

        # Query modelo 1
        print(f"\n[{model1['model_name']}] Thinking...")
        success1, response1 = query_model(
            model1['ssh_host'],
            model1['ssh_port'],
            model1['ollama_model'],
            question
        )

        # Query modelo 2
        print(f"[{model2['model_name']}] Thinking...")
        success2, response2 = query_model(
            model2['ssh_host'],
            model2['ssh_port'],
            model2['ollama_model'],
            question
        )

        # Mostrar respostas
        print(f"\n┌─ {model1['model_name']} ─────────────────────────────────────────────")
        if success1:
            print(f"│ {response1}")
        else:
            print(f"│ ERROR: {response1}")
        print("└" + "─"*79)

        print(f"\n┌─ {model2['model_name']} ──────────────────────────────────────────────")
        if success2:
            print(f"│ {response2}")
        else:
            print(f"│ ERROR: {response2}")
        print("└" + "─"*79)

    print("\n" + "="*80)
    print("ARENA TEST COMPLETE")
    print("="*80)
    print(f"\nTotal cost incurred (assuming ~5 min test): ${deployment['total_cost_per_hour'] * 0.083:.4f}")
    print("\nTo cleanup and stop billing:")
    print("python scripts/deploy_chat_arena_models.py --cleanup")


if __name__ == "__main__":
    test_arena()

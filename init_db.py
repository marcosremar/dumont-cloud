#!/usr/bin/env python3
"""Script para inicializar o banco de dados."""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.database import init_db, engine
from src.models import PriceHistory, PriceAlert

def main():
    """Cria todas as tabelas no banco de dados."""
    print("Inicializando banco de dados...")
    print(f"Conectando em: {engine.url}")

    try:
        init_db()
        print("✓ Tabelas criadas com sucesso!")
        print("  - price_history")
        print("  - price_alerts")
    except Exception as e:
        print(f"✗ Erro ao criar tabelas: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

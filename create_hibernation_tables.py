#!/usr/bin/env python3
"""
Script para criar tabelas de hibernação no banco de dados PostgreSQL.
"""
import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.database import Base, engine
from src.models.instance_status import InstanceStatus, HibernationEvent

def create_tables():
    """Cria todas as tabelas no banco de dados."""
    print("Criando tabelas de hibernação...")

    # Criar apenas as tabelas de hibernação
    InstanceStatus.__table__.create(bind=engine, checkfirst=True)
    HibernationEvent.__table__.create(bind=engine, checkfirst=True)

    print("✓ Tabelas criadas com sucesso!")
    print("  - instance_status")
    print("  - hibernation_events")

if __name__ == "__main__":
    create_tables()

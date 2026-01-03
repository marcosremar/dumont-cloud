#!/usr/bin/env python3
"""
Cria usuário de teste para os testes de deployment
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt
from datetime import datetime
import json

# Configuração
DB_URL = "postgresql://dumont:dumont123@localhost:5432/dumont_cloud"

def create_test_user():
    """Criar usuário de teste"""
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Verificar se usuário já existe
        result = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "test@test.com"}
        )
        existing = result.fetchone()

        if existing:
            print("Usuário test@test.com já existe")
            session.close()
            return

        # Hash da senha usando bcrypt diretamente
        password = "test123"
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        # Inserir usuário
        now = datetime.utcnow()
        session.execute(
            text("""
                INSERT INTO users (
                    email, hashed_password, is_verified,
                    is_trial, trial_gpu_seconds_remaining,
                    created_at, updated_at
                ) VALUES (
                    :email, :hashed_password, :is_verified,
                    :is_trial, :trial_gpu_seconds_remaining,
                    :created_at, :updated_at
                )
            """),
            {
                "email": "test@test.com",
                "hashed_password": hashed_password,
                "is_verified": True,
                "is_trial": True,
                "trial_gpu_seconds_remaining": 7200,
                "created_at": now,
                "updated_at": now,
            }
        )
        session.commit()
        print("Usuário test@test.com criado com sucesso!")
        print("  Email: test@test.com")
        print("  Senha: test123")

    except Exception as e:
        print(f"Erro ao criar usuário: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    create_test_user()

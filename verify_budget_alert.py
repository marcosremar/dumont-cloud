#!/usr/bin/env python3
"""Verify BudgetAlert model import."""
from src.models.metrics import BudgetAlert
print("BudgetAlert" in dir())
print(f"Table name: {BudgetAlert.__tablename__}")
print("Verification passed!")

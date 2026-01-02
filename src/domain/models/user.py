"""
Domain model for users - Re-exports from src/models/user.py to avoid duplication.
"""

# Re-export User from the main models module to avoid SQLAlchemy table conflicts
from src.models.user import User

__all__ = ['User']

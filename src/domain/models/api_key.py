"""
Domain model for API Keys.

API keys permitem autenticação programática sem senha.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import secrets


def generate_api_key() -> str:
    """Gera uma API key segura no formato dumont_sk_xxx."""
    random_part = secrets.token_urlsafe(32)
    return f"dumont_sk_{random_part}"


@dataclass
class APIKey:
    """Representa uma API key do usuário."""
    id: str
    user_email: str
    key_hash: str  # Hash da key (nunca armazenamos a key real)
    key_prefix: str  # Primeiros 8 chars para identificação (dumont_sk_xxx...)
    name: str  # Nome descritivo (ex: "SDK Dev", "Production")
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True

    # Permissões
    scopes: list = field(default_factory=lambda: ["all"])  # ["instances", "snapshots", "llm"]

    @property
    def is_expired(self) -> bool:
        """Verifica se a key expirou."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Verifica se a key é válida (ativa e não expirada)."""
        return self.is_active and not self.is_expired

    def to_dict(self) -> dict:
        """Converte para dicionário (sem o hash)."""
        return {
            "id": self.id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "scopes": self.scopes,
        }


@dataclass
class APIKeyCreate:
    """Resultado da criação de API key (inclui a key real uma única vez)."""
    api_key: APIKey
    key: str  # A key real - só retornada na criação

    def to_dict(self) -> dict:
        """Converte para resposta da API."""
        result = self.api_key.to_dict()
        result["key"] = self.key  # Só na criação
        return result

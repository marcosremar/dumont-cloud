"""
API Key Service - Gerencia criação e validação de API keys.
"""
import logging
import hashlib
import uuid
from typing import Optional, List
from datetime import datetime, timedelta

from ..models.api_key import APIKey, APIKeyCreate, generate_api_key
from ..repositories import IUserRepository

logger = logging.getLogger(__name__)


class APIKeyService:
    """
    Serviço para gerenciamento de API keys.

    API keys são armazenadas como hash no settings do usuário.
    A key real só é retornada uma vez na criação.
    """

    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def _hash_key(self, key: str) -> str:
        """Gera hash SHA-256 da API key."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_user_api_keys(self, user_email: str) -> List[dict]:
        """Obtém lista de API keys do usuário."""
        settings = self.user_repository.get_settings(user_email)
        return settings.get("api_keys", [])

    def _save_user_api_keys(self, user_email: str, api_keys: List[dict]):
        """Salva lista de API keys do usuário."""
        settings = self.user_repository.get_settings(user_email)
        settings["api_keys"] = api_keys
        self.user_repository.update_settings(user_email, settings)

    def create_api_key(
        self,
        user_email: str,
        name: str = "Default",
        scopes: List[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> APIKeyCreate:
        """
        Cria uma nova API key para o usuário.

        Args:
            user_email: Email do usuário
            name: Nome descritivo da key
            scopes: Permissões (default: ["all"])
            expires_in_days: Dias até expirar (None = nunca)

        Returns:
            APIKeyCreate com a key real (só retornada uma vez)
        """
        # Gerar key
        key = generate_api_key()
        key_hash = self._hash_key(key)
        key_prefix = key[:16] + "..."  # dumont_sk_xxxx...

        # Calcular expiração
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Criar objeto
        api_key = APIKey(
            id=str(uuid.uuid4()),
            user_email=user_email,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=scopes or ["all"],
            expires_at=expires_at,
        )

        # Salvar no settings do usuário
        api_keys = self._get_user_api_keys(user_email)
        api_keys.append({
            "id": api_key.id,
            "key_hash": api_key.key_hash,
            "key_prefix": api_key.key_prefix,
            "name": api_key.name,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "is_active": api_key.is_active,
            "scopes": api_key.scopes,
        })
        self._save_user_api_keys(user_email, api_keys)

        logger.info(f"API key created for {user_email}: {key_prefix}")

        return APIKeyCreate(api_key=api_key, key=key)

    def validate_api_key(self, key: str) -> Optional[str]:
        """
        Valida uma API key e retorna o email do usuário.

        Args:
            key: API key no formato dumont_sk_xxx

        Returns:
            Email do usuário se válida, None se inválida
        """
        if not key or not key.startswith("dumont_sk_"):
            return None

        key_hash = self._hash_key(key)

        # Buscar em todos os usuários (em produção, usar índice)
        # Por enquanto, vamos iterar pelos usuários conhecidos
        # TODO: Criar índice de api_key_hash -> user_email

        # Buscar usuário pelo hash da key
        user_email = self._find_user_by_key_hash(key_hash)
        if not user_email:
            return None

        # Verificar se key está ativa e não expirada
        api_keys = self._get_user_api_keys(user_email)
        for ak in api_keys:
            if ak["key_hash"] == key_hash:
                if not ak.get("is_active", True):
                    logger.warning(f"Inactive API key used: {ak['key_prefix']}")
                    return None

                expires_at = ak.get("expires_at")
                if expires_at:
                    if datetime.fromisoformat(expires_at) < datetime.utcnow():
                        logger.warning(f"Expired API key used: {ak['key_prefix']}")
                        return None

                # Atualizar last_used_at
                ak["last_used_at"] = datetime.utcnow().isoformat()
                self._save_user_api_keys(user_email, api_keys)

                return user_email

        return None

    def _find_user_by_key_hash(self, key_hash: str) -> Optional[str]:
        """
        Busca usuário pelo hash da API key.

        TODO: Em produção, usar índice invertido para performance.
        """
        # Por enquanto, verificamos se existe um índice global
        # Se não, retornamos None (será preciso implementar busca)

        # Tentar buscar do índice global no settings
        try:
            # Este é um workaround - idealmente teríamos uma tabela separada
            all_users = self.user_repository.list_all_users()
            for user in all_users:
                api_keys = user.settings.get("api_keys", [])
                for ak in api_keys:
                    if ak.get("key_hash") == key_hash:
                        return user.email
        except Exception as e:
            logger.error(f"Error finding user by key hash: {e}")

        return None

    def list_api_keys(self, user_email: str) -> List[APIKey]:
        """Lista todas as API keys do usuário."""
        api_keys = self._get_user_api_keys(user_email)

        return [
            APIKey(
                id=ak["id"],
                user_email=user_email,
                key_hash=ak["key_hash"],
                key_prefix=ak["key_prefix"],
                name=ak["name"],
                created_at=datetime.fromisoformat(ak["created_at"]),
                last_used_at=datetime.fromisoformat(ak["last_used_at"]) if ak.get("last_used_at") else None,
                expires_at=datetime.fromisoformat(ak["expires_at"]) if ak.get("expires_at") else None,
                is_active=ak.get("is_active", True),
                scopes=ak.get("scopes", ["all"]),
            )
            for ak in api_keys
        ]

    def revoke_api_key(self, user_email: str, key_id: str) -> bool:
        """
        Revoga uma API key.

        Args:
            user_email: Email do usuário
            key_id: ID da key a revogar

        Returns:
            True se revogada com sucesso
        """
        api_keys = self._get_user_api_keys(user_email)

        for ak in api_keys:
            if ak["id"] == key_id:
                ak["is_active"] = False
                self._save_user_api_keys(user_email, api_keys)
                logger.info(f"API key revoked: {ak['key_prefix']}")
                return True

        return False

    def delete_api_key(self, user_email: str, key_id: str) -> bool:
        """
        Deleta uma API key permanentemente.

        Args:
            user_email: Email do usuário
            key_id: ID da key a deletar

        Returns:
            True se deletada com sucesso
        """
        api_keys = self._get_user_api_keys(user_email)
        original_len = len(api_keys)

        api_keys = [ak for ak in api_keys if ak["id"] != key_id]

        if len(api_keys) < original_len:
            self._save_user_api_keys(user_email, api_keys)
            logger.info(f"API key deleted for {user_email}")
            return True

        return False

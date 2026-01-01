"""
Database-based SSO Repository Implementation
Implements ISSORepository interface using PostgreSQL with SQLAlchemy ORM
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ...core.exceptions import NotFoundException, ValidationException
from ...domain.repositories.sso_repository import ISSORepository
from ...models.sso_config import SSOConfig, SSOUserMapping
from ...config.db_session import get_db_session

logger = logging.getLogger(__name__)


class DatabaseSSORepository(ISSORepository):
    """
    Database-based implementation of ISSORepository.
    Stores SSO configurations and user mappings in PostgreSQL using SQLAlchemy ORM.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize database SSO repository.

        Args:
            session: Optional SQLAlchemy session. If not provided,
                     sessions are created per-operation using context manager.
        """
        self._session = session

    # ==================== SSO Config Operations ====================

    def get_sso_config(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get SSO configuration for an organization."""
        if self._session:
            config = self._session.query(SSOConfig).filter(
                SSOConfig.organization_id == organization_id
            ).first()
            return config.to_dict() if config else None

        with get_db_session() as session:
            config = session.query(SSOConfig).filter(
                SSOConfig.organization_id == organization_id
            ).first()
            return config.to_dict() if config else None

    def get_sso_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get SSO configuration by its ID."""
        if self._session:
            config = self._session.query(SSOConfig).filter(
                SSOConfig.id == config_id
            ).first()
            return config.to_dict() if config else None

        with get_db_session() as session:
            config = session.query(SSOConfig).filter(
                SSOConfig.id == config_id
            ).first()
            return config.to_dict() if config else None

    def create_sso_config(
        self,
        organization_id: str,
        provider_type: str,
        provider_name: str,
        config_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new SSO configuration for an organization."""
        if provider_type not in ('oidc', 'saml'):
            raise ValidationException(f"Invalid provider_type: {provider_type}")

        config = SSOConfig(
            organization_id=organization_id,
            provider_type=provider_type,
            provider_name=provider_name,
            enabled=False,  # Disabled by default until configured
        )

        # Apply OIDC-specific fields
        if provider_type == 'oidc':
            config.client_id = config_data.get('client_id')
            config.client_secret_encrypted = config_data.get('client_secret_encrypted')
            config.discovery_url = config_data.get('discovery_url')
            config.issuer_url = config_data.get('issuer_url')
            if 'scopes' in config_data:
                config.scopes = ' '.join(config_data['scopes']) if isinstance(
                    config_data['scopes'], list
                ) else config_data['scopes']

        # Apply SAML-specific fields
        elif provider_type == 'saml':
            config.idp_entity_id = config_data.get('idp_entity_id')
            config.idp_sso_url = config_data.get('idp_sso_url')
            config.idp_slo_url = config_data.get('idp_slo_url')
            config.idp_certificate = config_data.get('idp_certificate')
            config.sp_entity_id = config_data.get('sp_entity_id')
            config.assertion_consumer_service_url = config_data.get(
                'assertion_consumer_service_url'
            )

        # Apply common fields
        if 'role_mappings' in config_data:
            config.role_mappings = json.dumps(config_data['role_mappings'])
        if 'default_role' in config_data:
            config.default_role = config_data['default_role']
        if 'group_attribute' in config_data:
            config.group_attribute = config_data['group_attribute']
        if 'allowed_domains' in config_data:
            config.allowed_domains = ','.join(config_data['allowed_domains']) if isinstance(
                config_data['allowed_domains'], list
            ) else config_data['allowed_domains']
        if 'idp_metadata' in config_data:
            config.idp_metadata = json.dumps(config_data['idp_metadata'])
        if 'clock_skew_seconds' in config_data:
            config.clock_skew_seconds = config_data['clock_skew_seconds']
        if 'session_timeout_minutes' in config_data:
            config.session_timeout_minutes = config_data['session_timeout_minutes']

        if self._session:
            return self._create_config_in_session(self._session, config)

        with get_db_session() as session:
            return self._create_config_in_session(session, config)

    def _create_config_in_session(
        self, session: Session, config: SSOConfig
    ) -> Dict[str, Any]:
        """Create config within a session context."""
        try:
            session.add(config)
            session.flush()
            logger.info(
                f"SSO config created for org={config.organization_id}, "
                f"provider={config.provider_name}"
            )
            return config.to_dict()
        except IntegrityError:
            session.rollback()
            raise ValidationException(
                f"SSO config already exists for organization {config.organization_id}"
            )

    def update_sso_config(
        self,
        organization_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update SSO configuration for an organization."""
        if self._session:
            return self._update_config_in_session(self._session, organization_id, updates)

        with get_db_session() as session:
            return self._update_config_in_session(session, organization_id, updates)

    def _update_config_in_session(
        self, session: Session, organization_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update config within a session context."""
        config = session.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id
        ).first()

        if not config:
            raise NotFoundException(
                f"SSO config not found for organization {organization_id}"
            )

        # Update allowed fields
        field_mappings = {
            'enabled': 'enabled',
            'client_id': 'client_id',
            'client_secret_encrypted': 'client_secret_encrypted',
            'discovery_url': 'discovery_url',
            'issuer_url': 'issuer_url',
            'scopes': 'scopes',
            'idp_entity_id': 'idp_entity_id',
            'idp_sso_url': 'idp_sso_url',
            'idp_slo_url': 'idp_slo_url',
            'idp_certificate': 'idp_certificate',
            'sp_entity_id': 'sp_entity_id',
            'assertion_consumer_service_url': 'assertion_consumer_service_url',
            'default_role': 'default_role',
            'group_attribute': 'group_attribute',
            'sso_enforced': 'sso_enforced',
            'allow_password_fallback': 'allow_password_fallback',
            'clock_skew_seconds': 'clock_skew_seconds',
            'session_timeout_minutes': 'session_timeout_minutes',
        }

        for key, attr in field_mappings.items():
            if key in updates:
                setattr(config, attr, updates[key])

        # Handle complex fields
        if 'role_mappings' in updates:
            config.role_mappings = json.dumps(updates['role_mappings'])

        if 'allowed_domains' in updates:
            domains = updates['allowed_domains']
            config.allowed_domains = ','.join(domains) if isinstance(
                domains, list
            ) else domains

        if 'idp_metadata' in updates:
            config.idp_metadata = json.dumps(updates['idp_metadata'])

        if 'scopes' in updates and isinstance(updates['scopes'], list):
            config.scopes = ' '.join(updates['scopes'])

        session.flush()
        logger.info(f"SSO config updated for org={organization_id}")
        return config.to_dict()

    def delete_sso_config(self, organization_id: str) -> bool:
        """Delete SSO configuration for an organization."""
        if self._session:
            return self._delete_config_in_session(self._session, organization_id)

        with get_db_session() as session:
            return self._delete_config_in_session(session, organization_id)

    def _delete_config_in_session(
        self, session: Session, organization_id: str
    ) -> bool:
        """Delete config within a session context."""
        config = session.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id
        ).first()

        if not config:
            return False

        session.delete(config)
        session.flush()
        logger.info(f"SSO config deleted for org={organization_id}")
        return True

    def enable_sso(self, organization_id: str) -> Dict[str, Any]:
        """Enable SSO for an organization."""
        if self._session:
            return self._enable_sso_in_session(self._session, organization_id)

        with get_db_session() as session:
            return self._enable_sso_in_session(session, organization_id)

    def _enable_sso_in_session(
        self, session: Session, organization_id: str
    ) -> Dict[str, Any]:
        """Enable SSO within a session context."""
        config = session.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id
        ).first()

        if not config:
            raise NotFoundException(
                f"SSO config not found for organization {organization_id}"
            )

        # Validate configuration is complete
        if not config.is_active():
            if config.is_oidc():
                raise ValidationException(
                    "OIDC configuration incomplete: client_id and discovery_url required"
                )
            elif config.is_saml():
                raise ValidationException(
                    "SAML configuration incomplete: idp_entity_id, idp_sso_url, "
                    "and idp_certificate required"
                )

        config.enabled = True
        session.flush()
        logger.info(f"SSO enabled for org={organization_id}")
        return config.to_dict()

    def disable_sso(self, organization_id: str) -> Dict[str, Any]:
        """Disable SSO for an organization."""
        return self.update_sso_config(organization_id, {'enabled': False})

    def set_sso_enforcement(
        self,
        organization_id: str,
        enforced: bool,
        allow_fallback: bool = True,
    ) -> Dict[str, Any]:
        """Set SSO enforcement policy for an organization."""
        return self.update_sso_config(organization_id, {
            'sso_enforced': enforced,
            'allow_password_fallback': allow_fallback,
        })

    def list_sso_configs(
        self,
        enabled_only: bool = False,
        provider_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all SSO configurations."""
        if self._session:
            return self._list_configs_in_session(
                self._session, enabled_only, provider_type
            )

        with get_db_session() as session:
            return self._list_configs_in_session(session, enabled_only, provider_type)

    def _list_configs_in_session(
        self,
        session: Session,
        enabled_only: bool,
        provider_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        """List configs within a session context."""
        query = session.query(SSOConfig)

        if enabled_only:
            query = query.filter(SSOConfig.enabled == True)

        if provider_type:
            query = query.filter(SSOConfig.provider_type == provider_type)

        configs = query.all()
        return [config.to_dict() for config in configs]

    def get_sso_config_by_domain(self, email_domain: str) -> Optional[Dict[str, Any]]:
        """Get SSO configuration by email domain."""
        if self._session:
            return self._get_config_by_domain_in_session(self._session, email_domain)

        with get_db_session() as session:
            return self._get_config_by_domain_in_session(session, email_domain)

    def _get_config_by_domain_in_session(
        self, session: Session, email_domain: str
    ) -> Optional[Dict[str, Any]]:
        """Get config by domain within a session context."""
        # Search for configs where the domain is in allowed_domains
        configs = session.query(SSOConfig).filter(
            SSOConfig.enabled == True
        ).all()

        for config in configs:
            if config.allowed_domains:
                domains = [d.strip().lower() for d in config.allowed_domains.split(',')]
                if email_domain.lower() in domains:
                    return config.to_dict()

        return None

    # ==================== SSO User Mapping Operations ====================

    def get_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get SSO user mapping for a user in an organization."""
        if self._session:
            mapping = self._session.query(SSOUserMapping).filter(
                SSOUserMapping.user_id == user_id,
                SSOUserMapping.organization_id == organization_id,
            ).first()
            return mapping.to_dict() if mapping else None

        with get_db_session() as session:
            mapping = session.query(SSOUserMapping).filter(
                SSOUserMapping.user_id == user_id,
                SSOUserMapping.organization_id == organization_id,
            ).first()
            return mapping.to_dict() if mapping else None

    def get_sso_user_mapping_by_external_id(
        self,
        provider: str,
        external_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get SSO user mapping by external SSO identity."""
        if self._session:
            mapping = self._session.query(SSOUserMapping).filter(
                SSOUserMapping.sso_provider == provider,
                SSOUserMapping.sso_external_id == external_id,
            ).first()
            return mapping.to_dict() if mapping else None

        with get_db_session() as session:
            mapping = session.query(SSOUserMapping).filter(
                SSOUserMapping.sso_provider == provider,
                SSOUserMapping.sso_external_id == external_id,
            ).first()
            return mapping.to_dict() if mapping else None

    def create_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
        provider: str,
        external_id: str,
        mapping_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new SSO user mapping."""
        mapping = SSOUserMapping(
            user_id=user_id,
            organization_id=organization_id,
            sso_provider=provider,
            sso_external_id=external_id,
            sso_email=mapping_data.get('email'),
            sso_name=mapping_data.get('name'),
            is_active=True,
            provisioned_at=datetime.utcnow(),
        )

        # Handle groups
        if 'groups' in mapping_data:
            mapping.set_groups(mapping_data['groups'])

        if self._session:
            return self._create_mapping_in_session(self._session, mapping)

        with get_db_session() as session:
            return self._create_mapping_in_session(session, mapping)

    def _create_mapping_in_session(
        self, session: Session, mapping: SSOUserMapping
    ) -> Dict[str, Any]:
        """Create mapping within a session context."""
        try:
            session.add(mapping)
            session.flush()
            logger.info(
                f"SSO user mapping created: user={mapping.user_id}, "
                f"provider={mapping.sso_provider}"
            )
            return mapping.to_dict()
        except IntegrityError:
            session.rollback()
            raise ValidationException(
                f"SSO user mapping already exists for user {mapping.user_id}"
            )

    def update_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update SSO user mapping."""
        if self._session:
            return self._update_mapping_in_session(
                self._session, user_id, organization_id, updates
            )

        with get_db_session() as session:
            return self._update_mapping_in_session(
                session, user_id, organization_id, updates
            )

    def _update_mapping_in_session(
        self,
        session: Session,
        user_id: str,
        organization_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update mapping within a session context."""
        mapping = session.query(SSOUserMapping).filter(
            SSOUserMapping.user_id == user_id,
            SSOUserMapping.organization_id == organization_id,
        ).first()

        if not mapping:
            raise NotFoundException(
                f"SSO user mapping not found for user {user_id}"
            )

        # Update allowed fields
        field_mappings = {
            'sso_email': 'sso_email',
            'sso_name': 'sso_name',
            'is_active': 'is_active',
            'current_session_id': 'current_session_id',
        }

        for key, attr in field_mappings.items():
            if key in updates:
                setattr(mapping, attr, updates[key])

        # Handle groups
        if 'groups' in updates:
            mapping.set_groups(updates['groups'])

        # Handle sync timestamp
        if 'last_sync_at' in updates:
            mapping.last_sync_at = updates['last_sync_at']

        session.flush()
        logger.info(f"SSO user mapping updated: user={user_id}")
        return mapping.to_dict()

    def delete_sso_user_mapping(
        self,
        user_id: str,
        organization_id: str,
    ) -> bool:
        """Delete SSO user mapping."""
        if self._session:
            return self._delete_mapping_in_session(
                self._session, user_id, organization_id
            )

        with get_db_session() as session:
            return self._delete_mapping_in_session(session, user_id, organization_id)

    def _delete_mapping_in_session(
        self,
        session: Session,
        user_id: str,
        organization_id: str,
    ) -> bool:
        """Delete mapping within a session context."""
        mapping = session.query(SSOUserMapping).filter(
            SSOUserMapping.user_id == user_id,
            SSOUserMapping.organization_id == organization_id,
        ).first()

        if not mapping:
            return False

        session.delete(mapping)
        session.flush()
        logger.info(f"SSO user mapping deleted: user={user_id}")
        return True

    def list_sso_user_mappings(
        self,
        organization_id: str,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """List all SSO user mappings for an organization."""
        if self._session:
            return self._list_mappings_in_session(
                self._session, organization_id, active_only
            )

        with get_db_session() as session:
            return self._list_mappings_in_session(session, organization_id, active_only)

    def _list_mappings_in_session(
        self,
        session: Session,
        organization_id: str,
        active_only: bool,
    ) -> List[Dict[str, Any]]:
        """List mappings within a session context."""
        query = session.query(SSOUserMapping).filter(
            SSOUserMapping.organization_id == organization_id
        )

        if active_only:
            query = query.filter(SSOUserMapping.is_active == True)

        mappings = query.all()
        return [mapping.to_dict() for mapping in mappings]

    # ==================== Audit & Statistics ====================

    def record_sso_login(
        self,
        organization_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> None:
        """Record a successful SSO login for audit purposes."""
        if self._session:
            self._record_login_in_session(
                self._session, organization_id, user_id, session_id
            )
            return

        with get_db_session() as session:
            self._record_login_in_session(
                session, organization_id, user_id, session_id
            )

    def _record_login_in_session(
        self,
        session: Session,
        organization_id: str,
        user_id: str,
        session_id: Optional[str],
    ) -> None:
        """Record login within a session context."""
        now = datetime.utcnow()

        # Update config audit fields
        config = session.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id
        ).first()

        if config:
            config.last_login_at = now
            config.login_count = (config.login_count or 0) + 1

        # Update user mapping
        mapping = session.query(SSOUserMapping).filter(
            SSOUserMapping.user_id == user_id,
            SSOUserMapping.organization_id == organization_id,
        ).first()

        if mapping:
            mapping.last_login_at = now
            mapping.login_count = (mapping.login_count or 0) + 1
            if session_id:
                mapping.current_session_id = session_id

        session.flush()
        logger.info(f"SSO login recorded: org={organization_id}, user={user_id}")

    def record_sso_error(
        self,
        organization_id: str,
        error_message: str,
    ) -> None:
        """Record an SSO error for debugging purposes."""
        if self._session:
            self._record_error_in_session(
                self._session, organization_id, error_message
            )
            return

        with get_db_session() as session:
            self._record_error_in_session(session, organization_id, error_message)

    def _record_error_in_session(
        self,
        session: Session,
        organization_id: str,
        error_message: str,
    ) -> None:
        """Record error within a session context."""
        config = session.query(SSOConfig).filter(
            SSOConfig.organization_id == organization_id
        ).first()

        if config:
            config.last_error = error_message[:500]  # Truncate to column size
            config.last_error_at = datetime.utcnow()
            session.flush()
            logger.warning(
                f"SSO error recorded: org={organization_id}, error={error_message}"
            )

    def sync_user_from_idp(
        self,
        user_id: str,
        organization_id: str,
        idp_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Sync user data from IdP (groups, status, etc.)."""
        updates = {
            'last_sync_at': datetime.utcnow(),
        }

        if 'email' in idp_data:
            updates['sso_email'] = idp_data['email']
        if 'name' in idp_data:
            updates['sso_name'] = idp_data['name']
        if 'groups' in idp_data:
            updates['groups'] = idp_data['groups']
        if 'is_active' in idp_data:
            updates['is_active'] = idp_data['is_active']

        return self.update_sso_user_mapping(user_id, organization_id, updates)

    def deprovision_user(
        self,
        user_id: str,
        organization_id: str,
    ) -> Dict[str, Any]:
        """Mark a user as deprovisioned (removed from IdP)."""
        if self._session:
            return self._deprovision_in_session(
                self._session, user_id, organization_id
            )

        with get_db_session() as session:
            return self._deprovision_in_session(session, user_id, organization_id)

    def _deprovision_in_session(
        self,
        session: Session,
        user_id: str,
        organization_id: str,
    ) -> Dict[str, Any]:
        """Deprovision user within a session context."""
        mapping = session.query(SSOUserMapping).filter(
            SSOUserMapping.user_id == user_id,
            SSOUserMapping.organization_id == organization_id,
        ).first()

        if not mapping:
            raise NotFoundException(
                f"SSO user mapping not found for user {user_id}"
            )

        mapping.is_active = False
        mapping.deprovisioned_at = datetime.utcnow()
        mapping.current_session_id = None  # Clear active session

        session.flush()
        logger.info(f"User deprovisioned: user={user_id}, org={organization_id}")
        return mapping.to_dict()

    # ==================== Role Mapping ====================

    def update_role_mappings(
        self,
        organization_id: str,
        role_mappings: Dict[str, str],
        default_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update IdP group to app role mappings."""
        updates = {
            'role_mappings': role_mappings,
        }

        if default_role is not None:
            updates['default_role'] = default_role

        return self.update_sso_config(organization_id, updates)

    def get_role_mappings(
        self,
        organization_id: str,
    ) -> Dict[str, Any]:
        """Get IdP group to app role mappings."""
        config = self.get_sso_config(organization_id)

        if not config:
            raise NotFoundException(
                f"SSO config not found for organization {organization_id}"
            )

        return config.get('role_mapping', {
            'mappings': {},
            'default_role': 'user',
            'group_attribute': 'groups',
        })


# Singleton factory function for convenience
_sso_repository: Optional[DatabaseSSORepository] = None


def get_sso_repository() -> DatabaseSSORepository:
    """
    Get the singleton SSO repository instance.

    Returns:
        DatabaseSSORepository instance
    """
    global _sso_repository
    if _sso_repository is None:
        _sso_repository = DatabaseSSORepository()
    return _sso_repository

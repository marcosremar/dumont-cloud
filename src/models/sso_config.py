"""
Modelos de banco de dados para configuração de SSO (Single Sign-On) enterprise.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, Text
from datetime import datetime
from src.config.database import Base


class SSOConfig(Base):
    """Tabela para armazenar configuração de SSO por organização."""

    __tablename__ = "sso_configs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String(100), unique=True, nullable=False, index=True)

    # Provider info
    provider_type = Column(String(20), nullable=False)  # 'oidc' or 'saml'
    provider_name = Column(String(50), nullable=False)  # 'okta', 'azure', 'google'
    enabled = Column(Boolean, default=False, nullable=False)

    # OIDC Configuration
    client_id = Column(String(500), nullable=True)
    client_secret_encrypted = Column(Text, nullable=True)  # Encrypted secret
    discovery_url = Column(String(500), nullable=True)  # OIDC discovery endpoint
    issuer_url = Column(String(500), nullable=True)  # Token issuer URL
    scopes = Column(String(500), default="openid email profile")  # Space-separated scopes

    # SAML Configuration
    idp_entity_id = Column(String(500), nullable=True)  # IdP entity ID
    idp_sso_url = Column(String(500), nullable=True)  # IdP SSO service URL
    idp_slo_url = Column(String(500), nullable=True)  # IdP Single Logout URL (optional)
    idp_certificate = Column(Text, nullable=True)  # IdP X.509 certificate (PEM format)
    sp_entity_id = Column(String(500), nullable=True)  # Service Provider entity ID
    assertion_consumer_service_url = Column(String(500), nullable=True)  # ACS URL

    # Role Mapping Configuration
    role_mappings = Column(Text, nullable=True)  # JSON: {"idp_group": "app_role", ...}
    default_role = Column(String(50), default="user")  # Default role if no group matches
    group_attribute = Column(String(100), default="groups")  # OIDC claim or SAML attribute for groups

    # SSO Enforcement
    sso_enforced = Column(Boolean, default=False)  # Block password login when enabled
    allow_password_fallback = Column(Boolean, default=True)  # Allow password login if SSO fails

    # Domain restrictions
    allowed_domains = Column(String(500), nullable=True)  # Comma-separated allowed email domains
    domain_verification = Column(String(500), nullable=True)  # TXT record for domain verification

    # Metadata and Advanced Config
    idp_metadata = Column(Text, nullable=True)  # JSON: IdP-specific configuration
    clock_skew_seconds = Column(Integer, default=60)  # Tolerance for timestamp validation (SAML)
    session_timeout_minutes = Column(Integer, default=480)  # SSO session timeout (8 hours default)

    # Audit fields
    last_login_at = Column(DateTime, nullable=True)  # Last successful SSO login
    login_count = Column(Integer, default=0)  # Total SSO logins
    last_error = Column(String(500), nullable=True)  # Last SSO error message
    last_error_at = Column(DateTime, nullable=True)  # When the last error occurred

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes
    __table_args__ = (
        Index('idx_sso_provider', 'provider_type', 'provider_name'),
        Index('idx_sso_enabled', 'enabled', 'sso_enforced'),
    )

    def __repr__(self):
        return f"<SSOConfig(org={self.organization_id}, provider={self.provider_name}, enabled={self.enabled})>"

    def to_dict(self, include_secrets: bool = False):
        """Converte para dicionário para API responses."""
        import json

        # Parse role mappings JSON
        role_mappings_dict = {}
        if self.role_mappings:
            try:
                role_mappings_dict = json.loads(self.role_mappings)
            except json.JSONDecodeError:
                pass

        # Parse metadata JSON
        metadata_dict = {}
        if self.idp_metadata:
            try:
                metadata_dict = json.loads(self.idp_metadata)
            except json.JSONDecodeError:
                pass

        # Parse allowed domains
        allowed_domains_list = []
        if self.allowed_domains:
            allowed_domains_list = [d.strip() for d in self.allowed_domains.split(',') if d.strip()]

        result = {
            'id': self.id,
            'organization_id': self.organization_id,
            'provider': {
                'type': self.provider_type,
                'name': self.provider_name,
            },
            'enabled': self.enabled,
            'oidc_config': {
                'client_id': self.client_id,
                'discovery_url': self.discovery_url,
                'issuer_url': self.issuer_url,
                'scopes': self.scopes.split() if self.scopes else [],
            } if self.provider_type == 'oidc' else None,
            'saml_config': {
                'idp_entity_id': self.idp_entity_id,
                'idp_sso_url': self.idp_sso_url,
                'idp_slo_url': self.idp_slo_url,
                'sp_entity_id': self.sp_entity_id,
                'assertion_consumer_service_url': self.assertion_consumer_service_url,
                'has_certificate': bool(self.idp_certificate),
            } if self.provider_type == 'saml' else None,
            'role_mapping': {
                'mappings': role_mappings_dict,
                'default_role': self.default_role,
                'group_attribute': self.group_attribute,
            },
            'enforcement': {
                'sso_enforced': self.sso_enforced,
                'allow_password_fallback': self.allow_password_fallback,
            },
            'domain_config': {
                'allowed_domains': allowed_domains_list,
                'domain_verified': bool(self.domain_verification),
            },
            'settings': {
                'clock_skew_seconds': self.clock_skew_seconds,
                'session_timeout_minutes': self.session_timeout_minutes,
            },
            'audit': {
                'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
                'login_count': self.login_count,
                'last_error': self.last_error,
                'last_error_at': self.last_error_at.isoformat() if self.last_error_at else None,
            },
            'idp_metadata': metadata_dict,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

        # Include secrets only if explicitly requested (for admin operations)
        if include_secrets:
            result['oidc_config']['client_secret_encrypted'] = self.client_secret_encrypted
            if self.provider_type == 'saml':
                result['saml_config']['idp_certificate'] = self.idp_certificate

        return result

    def is_oidc(self) -> bool:
        """Check if this is an OIDC provider."""
        return self.provider_type == 'oidc'

    def is_saml(self) -> bool:
        """Check if this is a SAML provider."""
        return self.provider_type == 'saml'

    def is_active(self) -> bool:
        """Check if SSO is enabled and properly configured."""
        if not self.enabled:
            return False

        if self.is_oidc():
            return bool(self.client_id and self.discovery_url)
        elif self.is_saml():
            return bool(self.idp_entity_id and self.idp_sso_url and self.idp_certificate)

        return False


class SSOUserMapping(Base):
    """Tabela para mapear usuários a identidades SSO externas."""

    __tablename__ = "sso_user_mappings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)  # Local user ID
    organization_id = Column(String(100), nullable=False, index=True)

    # SSO identity
    sso_provider = Column(String(50), nullable=False)  # 'okta', 'azure', 'google'
    sso_external_id = Column(String(500), nullable=False)  # External user ID (sub claim)
    sso_email = Column(String(255), nullable=True)  # Email from IdP
    sso_name = Column(String(255), nullable=True)  # Name from IdP

    # Groups from IdP
    sso_groups = Column(Text, nullable=True)  # JSON array of group memberships

    # Sync status
    is_active = Column(Boolean, default=True)  # User status from IdP
    last_sync_at = Column(DateTime, nullable=True)  # Last sync with IdP
    provisioned_at = Column(DateTime, nullable=True)  # When user was auto-provisioned
    deprovisioned_at = Column(DateTime, nullable=True)  # When user was deactivated

    # Session info
    last_login_at = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    current_session_id = Column(String(100), nullable=True)  # Current SSO session

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes
    __table_args__ = (
        Index('idx_sso_user_provider', 'sso_provider', 'sso_external_id'),
        Index('idx_sso_user_org', 'organization_id', 'user_id'),
        Index('idx_sso_user_email', 'sso_email'),
    )

    def __repr__(self):
        return f"<SSOUserMapping(user={self.user_id}, provider={self.sso_provider}, external_id={self.sso_external_id})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        import json

        # Parse groups JSON
        groups_list = []
        if self.sso_groups:
            try:
                groups_list = json.loads(self.sso_groups)
            except json.JSONDecodeError:
                pass

        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'sso_identity': {
                'provider': self.sso_provider,
                'external_id': self.sso_external_id,
                'email': self.sso_email,
                'name': self.sso_name,
                'groups': groups_list,
            },
            'status': {
                'is_active': self.is_active,
                'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
                'provisioned_at': self.provisioned_at.isoformat() if self.provisioned_at else None,
                'deprovisioned_at': self.deprovisioned_at.isoformat() if self.deprovisioned_at else None,
            },
            'session': {
                'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
                'login_count': self.login_count,
                'has_active_session': bool(self.current_session_id),
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def get_groups(self) -> list:
        """Get the list of SSO groups for this user."""
        import json
        if self.sso_groups:
            try:
                return json.loads(self.sso_groups)
            except json.JSONDecodeError:
                return []
        return []

    def set_groups(self, groups: list):
        """Set the list of SSO groups for this user."""
        import json
        self.sso_groups = json.dumps(groups)

"""
Database model for User with SSO support.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, JSON
from datetime import datetime
from src.config.database import Base


class User(Base):
    """User table with SSO authentication support."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for SSO-only users
    name = Column(String(255), nullable=True)

    # Vast.ai integration
    vast_api_key = Column(String(255), nullable=True)

    # User settings (JSON)
    settings = Column(JSON, nullable=True, default=dict)

    # SSO fields
    sso_provider = Column(String(50), nullable=True, index=True)  # 'okta', 'azure', 'google'
    sso_external_id = Column(String(255), nullable=True)  # External ID from identity provider
    sso_enforced = Column(Boolean, default=False)  # If True, password login is disabled
    last_sso_login = Column(DateTime, nullable=True)  # Last SSO authentication timestamp

    # Account status
    is_active = Column(Boolean, default=True)  # Can be used for deprovisioning
    is_verified = Column(Boolean, default=False)  # Email verification status

    # Organization (for enterprise features)
    organization_id = Column(Integer, nullable=True, index=True)

    # Roles (comma-separated or JSON array for simplicity)
    roles = Column(String(500), nullable=True, default="user")  # e.g., "user,admin"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes for SSO lookups
    __table_args__ = (
        Index('ix_users_sso_lookup', 'sso_provider', 'sso_external_id'),
        Index('ix_users_org_active', 'organization_id', 'is_active'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, sso_provider={self.sso_provider})>"

    def to_dict(self):
        """Convert to dictionary for API responses (excludes sensitive data)."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'vast_api_key': self.vast_api_key,
            'settings': self.settings or {},
            'sso': {
                'provider': self.sso_provider,
                'external_id': self.sso_external_id,
                'enforced': self.sso_enforced,
                'last_login': self.last_sso_login.isoformat() if self.last_sso_login else None,
            } if self.sso_provider else None,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'organization_id': self.organization_id,
            'roles': self.roles.split(',') if self.roles else ['user'],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        if not self.roles:
            return False
        return role in self.roles.split(',')

    def is_sso_user(self) -> bool:
        """Check if user authenticates via SSO."""
        return self.sso_provider is not None and self.sso_external_id is not None

    def can_use_password_login(self) -> bool:
        """Check if user can login with password."""
        # SSO enforced users cannot use password login
        if self.sso_enforced:
            return False
        # Users without password hash cannot use password login
        if not self.password_hash:
            return False
        return True

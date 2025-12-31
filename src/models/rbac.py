"""
Modelos de banco de dados para RBAC (Role-Based Access Control) e Teams.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, ForeignKey, Text, Float, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from src.config.database import Base


# Association table for Role-Permission many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
)


class Team(Base):
    """Tabela para armazenar times/organizações."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(String(500), nullable=True)

    # Owner (first admin)
    owner_user_id = Column(String(100), nullable=False, index=True)

    # Team settings
    is_active = Column(Boolean, default=True, nullable=False)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    invitations = relationship("TeamInvitation", back_populates="team", cascade="all, delete-orphan")
    custom_roles = relationship("Role", back_populates="team", foreign_keys="Role.team_id")

    # Indices
    __table_args__ = (
        Index('idx_team_owner', 'owner_user_id'),
        Index('idx_team_active', 'is_active', 'deleted_at'),
    )

    def __repr__(self):
        return f"<Team(id={self.id}, name={self.name}, slug={self.slug})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'owner_user_id': self.owner_user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Permission(Base):
    """Tabela para armazenar permissões granulares do sistema."""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "gpu.provision"
    display_name = Column(String(100), nullable=False)  # e.g., "Provision GPU"
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=False, index=True)  # e.g., "gpu", "cost", "team", "settings", "audit"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    # Indices
    __table_args__ = (
        Index('idx_permission_category', 'category'),
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
        }


class Role(Base):
    """Tabela para armazenar roles (funções) do sistema."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # e.g., "Admin", "Developer", "Viewer"
    display_name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # System roles cannot be modified or deleted
    is_system = Column(Boolean, default=False, nullable=False)

    # Custom roles belong to a specific team (NULL for system roles)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    team = relationship("Team", back_populates="custom_roles", foreign_keys=[team_id])

    # Indices
    __table_args__ = (
        Index('idx_role_system', 'is_system'),
        Index('idx_role_team', 'team_id'),
    )

    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name}, is_system={self.is_system})>"

    def to_dict(self, include_permissions=False):
        """Converte para dicionário para API responses."""
        result = {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'is_system': self.is_system,
            'team_id': self.team_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_permissions:
            result['permissions'] = [p.to_dict() for p in self.permissions]
        return result


class TeamMember(Base):
    """Tabela de associação para membros de times (usuários que já aceitaram convite)."""

    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)  # References user's ID
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False, index=True)

    # Invitation metadata
    invited_by_user_id = Column(String(100), nullable=True)  # NULL for team creator
    invited_at = Column(DateTime, nullable=True)

    # Membership timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Soft delete for audit trail
    removed_at = Column(DateTime, nullable=True)
    removed_by_user_id = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", back_populates="members")
    role = relationship("Role")

    # Indices
    __table_args__ = (
        Index('idx_team_member_user', 'user_id', 'team_id'),
        Index('idx_team_member_active', 'team_id', 'is_active'),
        Index('idx_team_member_role', 'role_id'),
    )

    def __repr__(self):
        return f"<TeamMember(id={self.id}, user_id={self.user_id}, team_id={self.team_id}, role_id={self.role_id})>"

    def to_dict(self, include_role=False):
        """Converte para dicionário para API responses."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'team_id': self.team_id,
            'role_id': self.role_id,
            'invited_by_user_id': self.invited_by_user_id,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'removed_at': self.removed_at.isoformat() if self.removed_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_role and self.role:
            result['role'] = self.role.to_dict()
        return result


class TeamInvitation(Base):
    """Tabela para convites pendentes de membros para times."""

    __tablename__ = "team_invitations"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)  # Email do convidado
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False, index=True)

    # Invitation token
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Who invited
    invited_by_user_id = Column(String(100), nullable=False)

    # Expiration
    expires_at = Column(DateTime, nullable=False)

    # Status: 'pending', 'accepted', 'expired', 'revoked'
    status = Column(String(50), default='pending', nullable=False, index=True)

    # If accepted, link to the created TeamMember
    accepted_at = Column(DateTime, nullable=True)
    accepted_by_user_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", back_populates="invitations")
    role = relationship("Role")

    # Indices
    __table_args__ = (
        Index('idx_invitation_team_email', 'team_id', 'email'),
        Index('idx_invitation_status', 'status', 'expires_at'),
        Index('idx_invitation_token', 'token'),
    )

    def __repr__(self):
        return f"<TeamInvitation(id={self.id}, email={self.email}, team_id={self.team_id}, status={self.status})>"

    def to_dict(self, include_role=False):
        """Converte para dicionário para API responses."""
        result = {
            'id': self.id,
            'team_id': self.team_id,
            'email': self.email,
            'role_id': self.role_id,
            'invited_by_user_id': self.invited_by_user_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'accepted_by_user_id': self.accepted_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_role and self.role:
            result['role'] = self.role.to_dict()
        return result


# Constants for predefined system roles
SYSTEM_ROLES = {
    'admin': {
        'name': 'admin',
        'display_name': 'Admin',
        'description': 'Full control over team resources and settings',
    },
    'developer': {
        'name': 'developer',
        'display_name': 'Developer',
        'description': 'Can provision and manage GPU instances',
    },
    'viewer': {
        'name': 'viewer',
        'display_name': 'Viewer',
        'description': 'Read-only access to resources',
    },
}

# Constants for all available permissions
PERMISSIONS = {
    # GPU permissions
    'gpu.provision': {
        'display_name': 'Provision GPU',
        'description': 'Create and provision new GPU instances',
        'category': 'gpu',
    },
    'gpu.delete': {
        'display_name': 'Delete GPU',
        'description': 'Delete and terminate GPU instances',
        'category': 'gpu',
    },
    'gpu.view': {
        'display_name': 'View GPU',
        'description': 'View GPU instance details and status',
        'category': 'gpu',
    },
    # Cost permissions
    'cost.view': {
        'display_name': 'View All Costs',
        'description': 'View cost reports for the entire team',
        'category': 'cost',
    },
    'cost.view_own': {
        'display_name': 'View Own Costs',
        'description': 'View own cost and usage reports',
        'category': 'cost',
    },
    'cost.export': {
        'display_name': 'Export Costs',
        'description': 'Export cost reports and invoices',
        'category': 'cost',
    },
    # Team permissions
    'team.invite': {
        'display_name': 'Invite Members',
        'description': 'Invite new members to the team',
        'category': 'team',
    },
    'team.remove': {
        'display_name': 'Remove Members',
        'description': 'Remove members from the team',
        'category': 'team',
    },
    'team.manage': {
        'display_name': 'Manage Team',
        'description': 'Full team management including roles and settings',
        'category': 'team',
    },
    # Settings permissions
    'settings.view': {
        'display_name': 'View Settings',
        'description': 'View team settings and configuration',
        'category': 'settings',
    },
    'settings.manage': {
        'display_name': 'Manage Settings',
        'description': 'Modify team settings and configuration',
        'category': 'settings',
    },
    # Audit permissions
    'audit.view': {
        'display_name': 'View Audit Logs',
        'description': 'View team audit logs and activity history',
        'category': 'audit',
    },
}

# Role-Permission mapping for system roles
ROLE_PERMISSIONS = {
    'admin': [
        'gpu.provision', 'gpu.delete', 'gpu.view',
        'cost.view', 'cost.view_own', 'cost.export',
        'team.invite', 'team.remove', 'team.manage',
        'settings.view', 'settings.manage',
        'audit.view',
    ],
    'developer': [
        'gpu.provision', 'gpu.view',
        'cost.view_own',
    ],
    'viewer': [
        'gpu.view',
        'cost.view_own',
    ],
}


class AuditLog(Base):
    """Tabela para armazenar logs de auditoria de ações no sistema."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action
    user_id = Column(String(100), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='SET NULL'), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # e.g., "member.added", "role.changed", "gpu.provisioned"
    resource_type = Column(String(100), nullable=False, index=True)  # e.g., "team_member", "role", "gpu_instance"
    resource_id = Column(String(100), nullable=True, index=True)  # ID of the affected resource

    # Action metadata
    details = Column(Text, nullable=True)  # JSON string with additional action details
    old_value = Column(Text, nullable=True)  # JSON string with previous state (for updates)
    new_value = Column(Text, nullable=True)  # JSON string with new state (for updates)

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(String(500), nullable=True)  # Browser/client user agent

    # Result
    status = Column(String(50), default='success', nullable=False, index=True)  # 'success', 'failure', 'denied'
    error_message = Column(String(500), nullable=True)  # Error message if status is 'failure' or 'denied'

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indices
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_team_action', 'team_id', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_timestamp', 'created_at'),
        Index('idx_audit_team_timestamp', 'team_id', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, resource={self.resource_type})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'team_id': self.team_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TeamQuota(Base):
    """Tabela para armazenar quotas e limites de recursos por time."""

    __tablename__ = "team_quotas"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)

    # GPU quotas
    max_gpu_hours_per_month = Column(Float, nullable=True)  # NULL means unlimited
    max_concurrent_instances = Column(Integer, nullable=True)  # NULL means unlimited

    # Budget quotas
    max_monthly_budget_usd = Column(Float, nullable=True)  # NULL means unlimited

    # Current usage tracking
    current_gpu_hours_used = Column(Float, default=0.0, nullable=False)
    current_concurrent_instances = Column(Integer, default=0, nullable=False)
    current_monthly_spend_usd = Column(Float, default=0.0, nullable=False)

    # Usage period
    usage_period_start = Column(DateTime, nullable=True)  # Start of current billing period
    usage_period_end = Column(DateTime, nullable=True)  # End of current billing period

    # Soft limits (warnings before hard limits)
    warn_at_gpu_hours_percent = Column(Float, default=80.0, nullable=False)  # Warn at 80% of limit
    warn_at_budget_percent = Column(Float, default=80.0, nullable=False)  # Warn at 80% of budget

    # Notification settings
    notify_on_warning = Column(Boolean, default=True, nullable=False)
    notify_on_limit_reached = Column(Boolean, default=True, nullable=False)
    last_warning_sent_at = Column(DateTime, nullable=True)
    last_limit_reached_sent_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team")

    # Indices
    __table_args__ = (
        Index('idx_quota_team', 'team_id'),
        Index('idx_quota_usage_period', 'usage_period_start', 'usage_period_end'),
    )

    def __repr__(self):
        return f"<TeamQuota(id={self.id}, team_id={self.team_id}, gpu_hours={self.current_gpu_hours_used}/{self.max_gpu_hours_per_month})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'limits': {
                'max_gpu_hours_per_month': self.max_gpu_hours_per_month,
                'max_concurrent_instances': self.max_concurrent_instances,
                'max_monthly_budget_usd': self.max_monthly_budget_usd,
            },
            'usage': {
                'gpu_hours_used': self.current_gpu_hours_used,
                'concurrent_instances': self.current_concurrent_instances,
                'monthly_spend_usd': self.current_monthly_spend_usd,
            },
            'usage_period': {
                'start': self.usage_period_start.isoformat() if self.usage_period_start else None,
                'end': self.usage_period_end.isoformat() if self.usage_period_end else None,
            },
            'warnings': {
                'warn_at_gpu_hours_percent': self.warn_at_gpu_hours_percent,
                'warn_at_budget_percent': self.warn_at_budget_percent,
            },
            'notifications': {
                'notify_on_warning': self.notify_on_warning,
                'notify_on_limit_reached': self.notify_on_limit_reached,
                'last_warning_sent_at': self.last_warning_sent_at.isoformat() if self.last_warning_sent_at else None,
                'last_limit_reached_sent_at': self.last_limit_reached_sent_at.isoformat() if self.last_limit_reached_sent_at else None,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_gpu_hours_exceeded(self):
        """Verifica se o limite de horas de GPU foi excedido."""
        if self.max_gpu_hours_per_month is None:
            return False
        return self.current_gpu_hours_used >= self.max_gpu_hours_per_month

    def is_concurrent_instances_exceeded(self):
        """Verifica se o limite de instâncias concorrentes foi excedido."""
        if self.max_concurrent_instances is None:
            return False
        return self.current_concurrent_instances >= self.max_concurrent_instances

    def is_budget_exceeded(self):
        """Verifica se o orçamento mensal foi excedido."""
        if self.max_monthly_budget_usd is None:
            return False
        return self.current_monthly_spend_usd >= self.max_monthly_budget_usd

    def is_any_quota_exceeded(self):
        """Verifica se algum limite foi excedido."""
        return (
            self.is_gpu_hours_exceeded() or
            self.is_concurrent_instances_exceeded() or
            self.is_budget_exceeded()
        )

    def get_gpu_hours_percent_used(self):
        """Retorna a porcentagem de horas de GPU utilizadas."""
        if self.max_gpu_hours_per_month is None or self.max_gpu_hours_per_month == 0:
            return 0.0
        return (self.current_gpu_hours_used / self.max_gpu_hours_per_month) * 100

    def get_budget_percent_used(self):
        """Retorna a porcentagem do orçamento utilizado."""
        if self.max_monthly_budget_usd is None or self.max_monthly_budget_usd == 0:
            return 0.0
        return (self.current_monthly_spend_usd / self.max_monthly_budget_usd) * 100

    def should_warn_gpu_hours(self):
        """Verifica se deve enviar aviso sobre horas de GPU."""
        return self.get_gpu_hours_percent_used() >= self.warn_at_gpu_hours_percent

    def should_warn_budget(self):
        """Verifica se deve enviar aviso sobre orçamento."""
        return self.get_budget_percent_used() >= self.warn_at_budget_percent


# Audit log action constants
AUDIT_ACTIONS = {
    # Member actions
    'member.added': 'Member added to team',
    'member.removed': 'Member removed from team',
    'member.role_changed': 'Member role changed',
    # Role actions
    'role.created': 'Custom role created',
    'role.updated': 'Role updated',
    'role.deleted': 'Role deleted',
    # GPU actions
    'gpu.provisioned': 'GPU instance provisioned',
    'gpu.deleted': 'GPU instance deleted',
    'gpu.hibernated': 'GPU instance hibernated',
    'gpu.woke': 'GPU instance woke from hibernation',
    # Settings actions
    'settings.updated': 'Team settings updated',
    # Quota actions
    'quota.updated': 'Team quota updated',
    'quota.exceeded': 'Team quota exceeded',
    # Team actions
    'team.created': 'Team created',
    'team.updated': 'Team updated',
    'team.deleted': 'Team deleted',
    # Invitation actions
    'invitation.sent': 'Invitation sent',
    'invitation.accepted': 'Invitation accepted',
    'invitation.revoked': 'Invitation revoked',
    'invitation.expired': 'Invitation expired',
}

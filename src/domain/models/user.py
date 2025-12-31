"""
Domain model for users - SQLAlchemy ORM model.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, DateTime, Text
from src.config.database import Base


class User(Base):
    """Represents a user in the system."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    vast_api_key = Column(String(255), nullable=True)

    # Settings stored as JSON string
    settings_json = Column(Text, nullable=True, default="{}")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

    @property
    def settings(self) -> Dict[str, Any]:
        """Get settings as a dictionary."""
        if not self.settings_json:
            return {}
        try:
            return json.loads(self.settings_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @settings.setter
    def settings(self, value: Dict[str, Any]) -> None:
        """Set settings from a dictionary."""
        self.settings_json = json.dumps(value) if value else "{}"

    def to_dict(self) -> dict:
        """Convert to dictionary (excludes password_hash for security)."""
        return {
            'id': self.id,
            'email': self.email,
            'vast_api_key': self.vast_api_key,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def restic_repo(self) -> Optional[str]:
        """Get restic repository from settings."""
        return self.settings.get('restic_repo')

    @property
    def restic_password(self) -> Optional[str]:
        """Get restic password from settings."""
        return self.settings.get('restic_password')

    @property
    def r2_access_key(self) -> Optional[str]:
        """Get R2 access key from settings."""
        return self.settings.get('r2_access_key')

    @property
    def r2_secret_key(self) -> Optional[str]:
        """Get R2 secret key from settings."""
        return self.settings.get('r2_secret_key')

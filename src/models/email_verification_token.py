"""
SQLAlchemy model for email verification tokens.

Tokens are used for email verification during user registration.
Each token is associated with a user and expires after 24 hours.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from src.config.database import Base


# Default token expiration: 24 hours
TOKEN_EXPIRATION_HOURS = 24


class EmailVerificationToken(Base):
    """
    Email verification token model.

    Tokens are generated during user registration and sent via email.
    Users must click the verification link to activate their trial account.
    Tokens expire after 24 hours for security.
    """

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationship to User model
    user = relationship("User", backref="verification_tokens")

    # Composite index for efficient token lookup with expiration check
    __table_args__ = (
        Index('idx_token_expiration', 'token', 'expires_at'),
    )

    def __repr__(self):
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"

    @classmethod
    def create_token(cls, user_id: int, token: str, expiration_hours: int = TOKEN_EXPIRATION_HOURS) -> "EmailVerificationToken":
        """
        Factory method to create a new verification token.

        Args:
            user_id: The ID of the user this token is for
            token: The secure random token string
            expiration_hours: Hours until token expires (default: 24)

        Returns:
            New EmailVerificationToken instance
        """
        return cls(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=expiration_hours)
        )

    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the token is still valid (not expired)."""
        return not self.is_expired()

    def time_remaining(self) -> timedelta:
        """
        Get the time remaining until token expiration.

        Returns:
            timedelta of remaining time, or zero if expired
        """
        remaining = self.expires_at - datetime.utcnow()
        return max(timedelta(0), remaining)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token': self.token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired(),
        }

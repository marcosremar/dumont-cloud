"""
SQLAlchemy model for users with trial support.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, Text
from datetime import datetime
from src.config.database import Base


class User(Base):
    """
    User model with trial management fields.

    Trial users receive 2 hours (7200 seconds) of GPU time upon registration.
    Notification flags track which usage threshold emails have been sent.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Email verification
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True, index=True)
    verification_token_expires_at = Column(DateTime, nullable=True)

    # Trial management
    is_trial = Column(Boolean, default=True, nullable=False, index=True)
    trial_gpu_seconds_remaining = Column(Integer, default=7200, nullable=False)  # 2 hours
    trial_started_at = Column(DateTime, nullable=True)

    # Trial notification flags (prevent duplicate emails)
    trial_notified_75 = Column(Boolean, default=False, nullable=False)
    trial_notified_90 = Column(Boolean, default=False, nullable=False)
    trial_notified_100 = Column(Boolean, default=False, nullable=False)

    # VAST.ai integration
    vast_api_key = Column(String(255), nullable=True)

    # User settings (JSON stored as Text)
    settings = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_user_trial_status', 'is_trial', 'is_verified'),
        Index('idx_user_verification', 'verification_token', 'verification_token_expires_at'),
    )

    # Alias for compatibility with db_user_repository
    @property
    def password_hash(self):
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value):
        self.hashed_password = value

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_trial={self.is_trial}, verified={self.is_verified})>"

    def to_dict(self):
        """Convert to dictionary for API responses (excludes sensitive data)."""
        return {
            'id': self.id,
            'email': self.email,
            'is_verified': self.is_verified,
            'is_trial': self.is_trial,
            'trial_gpu_seconds_remaining': self.trial_gpu_seconds_remaining,
            'trial_started_at': self.trial_started_at.isoformat() if self.trial_started_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_trial_usage_percent(self) -> float:
        """Calculate the percentage of trial GPU time used."""
        total_seconds = 7200  # 2 hours
        used_seconds = total_seconds - self.trial_gpu_seconds_remaining
        return min(100.0, max(0.0, (used_seconds / total_seconds) * 100))

    def has_trial_time_remaining(self) -> bool:
        """Check if user has any trial GPU time left."""
        return self.trial_gpu_seconds_remaining > 0

    def deduct_trial_time(self, seconds: int) -> int:
        """
        Deduct GPU seconds from trial balance.

        Args:
            seconds: Number of seconds to deduct

        Returns:
            Actual seconds deducted (may be less if balance is insufficient)
        """
        if self.trial_gpu_seconds_remaining <= 0:
            return 0

        actual_deduction = min(seconds, self.trial_gpu_seconds_remaining)
        self.trial_gpu_seconds_remaining -= actual_deduction
        return actual_deduction

    def should_notify_threshold(self, threshold_percent: int) -> bool:
        """
        Check if notification should be sent for a usage threshold.

        Args:
            threshold_percent: The threshold to check (75, 90, or 100)

        Returns:
            True if notification should be sent, False otherwise
        """
        usage_percent = self.get_trial_usage_percent()

        if threshold_percent == 75:
            return usage_percent >= 75 and not self.trial_notified_75
        elif threshold_percent == 90:
            return usage_percent >= 90 and not self.trial_notified_90
        elif threshold_percent == 100:
            return usage_percent >= 100 and not self.trial_notified_100

        return False

    def mark_threshold_notified(self, threshold_percent: int) -> None:
        """
        Mark a threshold as having been notified.

        Args:
            threshold_percent: The threshold to mark (75, 90, or 100)
        """
        if threshold_percent == 75:
            self.trial_notified_75 = True
        elif threshold_percent == 90:
            self.trial_notified_90 = True
        elif threshold_percent == 100:
            self.trial_notified_100 = True

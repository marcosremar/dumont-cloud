"""
Trial Management Repository Implementation
Handles trial status, GPU time tracking, and notification management
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ...core.exceptions import NotFoundException
from ...models.user import User as DBUser
from ...config.database import SessionLocal

logger = logging.getLogger(__name__)

# Default trial allocation: 2 hours in seconds
DEFAULT_TRIAL_SECONDS = 7200


@dataclass
class TrialStatus:
    """Data class representing a user's trial status."""
    email: str
    is_trial: bool
    gpu_seconds_remaining: int
    gpu_seconds_total: int
    trial_started_at: Optional[datetime]
    percentage_used: float
    notified_75: bool
    notified_90: bool
    notified_100: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'email': self.email,
            'is_trial': self.is_trial,
            'gpu_seconds_remaining': self.gpu_seconds_remaining,
            'gpu_seconds_total': self.gpu_seconds_total,
            'trial_started_at': self.trial_started_at.isoformat() if self.trial_started_at else None,
            'percentage_used': round(self.percentage_used, 2),
            'hours_remaining': round(self.gpu_seconds_remaining / 3600, 2),
            'minutes_remaining': round(self.gpu_seconds_remaining / 60, 1),
        }


class TrialRepository:
    """
    Repository for managing trial user data.
    Handles GPU time tracking and notification state.
    Uses database transactions to prevent race conditions.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize trial repository.

        Args:
            session: Optional SQLAlchemy session. If not provided, creates new sessions per operation.
        """
        self._session = session

    def _get_session(self) -> Session:
        """Get or create a database session."""
        if self._session:
            return self._session
        return SessionLocal()

    def _close_session(self, session: Session):
        """Close session if it was created by this method."""
        if not self._session:
            session.close()

    def get_trial_status(self, email: str) -> Optional[TrialStatus]:
        """
        Get trial status for a user.

        Args:
            email: User email address

        Returns:
            TrialStatus if user exists, None otherwise
        """
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                return None

            percentage_used = db_user.get_trial_usage_percent()

            return TrialStatus(
                email=db_user.email,
                is_trial=db_user.is_trial,
                gpu_seconds_remaining=db_user.trial_gpu_seconds_remaining,
                gpu_seconds_total=DEFAULT_TRIAL_SECONDS,
                trial_started_at=db_user.trial_started_at,
                percentage_used=percentage_used,
                notified_75=db_user.trial_notified_75,
                notified_90=db_user.trial_notified_90,
                notified_100=db_user.trial_notified_100,
            )
        finally:
            self._close_session(session)

    def decrement_gpu_seconds(self, email: str, seconds: int) -> int:
        """
        Decrement GPU seconds from trial balance using database transaction.

        Uses SELECT FOR UPDATE to prevent race conditions on concurrent updates.

        Args:
            email: User email address
            seconds: Number of seconds to deduct

        Returns:
            Actual seconds deducted (may be less if balance is insufficient)

        Raises:
            NotFoundException: If user not found
        """
        session = self._get_session()
        try:
            # Use with_for_update() to lock the row for concurrent access
            db_user = (
                session.query(DBUser)
                .filter(DBUser.email == email)
                .with_for_update()
                .first()
            )

            if not db_user:
                raise NotFoundException(f"User {email} not found")

            if not db_user.is_trial:
                logger.info(f"User {email} is not a trial user, skipping GPU time deduction")
                return 0

            # Use the model's deduct method
            actual_deducted = db_user.deduct_trial_time(seconds)

            # Start trial timer on first usage
            if actual_deducted > 0 and db_user.trial_started_at is None:
                db_user.trial_started_at = datetime.utcnow()
                logger.info(f"Trial started for user {email}")

            session.commit()

            logger.info(
                f"Deducted {actual_deducted}s from user {email}, "
                f"remaining: {db_user.trial_gpu_seconds_remaining}s"
            )

            return actual_deducted
        except NotFoundException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error decrementing GPU seconds for {email}: {e}")
            raise
        finally:
            self._close_session(session)

    def check_and_mark_notification(self, email: str, percentage: int) -> bool:
        """
        Check if notification should be sent and mark it as sent.

        Uses database transaction to prevent duplicate notifications.

        Args:
            email: User email address
            percentage: Threshold percentage to check (75, 90, or 100)

        Returns:
            True if notification should be sent (was unmarked), False otherwise

        Raises:
            NotFoundException: If user not found
            ValueError: If invalid percentage threshold
        """
        if percentage not in (75, 90, 100):
            raise ValueError(f"Invalid threshold percentage: {percentage}. Must be 75, 90, or 100")

        session = self._get_session()
        try:
            # Lock the row for update
            db_user = (
                session.query(DBUser)
                .filter(DBUser.email == email)
                .with_for_update()
                .first()
            )

            if not db_user:
                raise NotFoundException(f"User {email} not found")

            if not db_user.is_trial:
                return False

            # Check if notification should be sent
            should_notify = db_user.should_notify_threshold(percentage)

            if should_notify:
                # Mark as notified
                db_user.mark_threshold_notified(percentage)
                session.commit()
                logger.info(f"Marked {percentage}% notification as sent for user {email}")

            return should_notify
        except (NotFoundException, ValueError):
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error checking/marking notification for {email}: {e}")
            raise
        finally:
            self._close_session(session)

    def get_pending_notifications(self, email: str) -> list[int]:
        """
        Get list of pending notification thresholds for a user.

        Args:
            email: User email address

        Returns:
            List of pending threshold percentages (75, 90, 100)

        Raises:
            NotFoundException: If user not found
        """
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()

            if not db_user:
                raise NotFoundException(f"User {email} not found")

            if not db_user.is_trial:
                return []

            pending = []
            for threshold in [75, 90, 100]:
                if db_user.should_notify_threshold(threshold):
                    pending.append(threshold)

            return pending
        except NotFoundException:
            raise
        finally:
            self._close_session(session)

    def has_sufficient_balance(self, email: str, required_seconds: int) -> bool:
        """
        Check if user has sufficient trial balance for an operation.

        Args:
            email: User email address
            required_seconds: Seconds required for the operation

        Returns:
            True if balance is sufficient, False otherwise
        """
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()

            if not db_user:
                return False

            # Non-trial users always have sufficient balance (unlimited)
            if not db_user.is_trial:
                return True

            return db_user.trial_gpu_seconds_remaining >= required_seconds
        finally:
            self._close_session(session)

    def reset_trial(self, email: str) -> bool:
        """
        Reset trial allocation for a user (admin operation).

        Args:
            email: User email address

        Returns:
            True if reset successful, False if user not found

        Raises:
            NotFoundException: If user not found
        """
        session = self._get_session()
        try:
            db_user = (
                session.query(DBUser)
                .filter(DBUser.email == email)
                .with_for_update()
                .first()
            )

            if not db_user:
                raise NotFoundException(f"User {email} not found")

            db_user.trial_gpu_seconds_remaining = DEFAULT_TRIAL_SECONDS
            db_user.trial_started_at = None
            db_user.trial_notified_75 = False
            db_user.trial_notified_90 = False
            db_user.trial_notified_100 = False

            session.commit()
            logger.info(f"Trial reset for user {email}")

            return True
        except NotFoundException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting trial for {email}: {e}")
            raise
        finally:
            self._close_session(session)

    def upgrade_from_trial(self, email: str) -> bool:
        """
        Upgrade user from trial to paid status.

        Args:
            email: User email address

        Returns:
            True if upgrade successful

        Raises:
            NotFoundException: If user not found
        """
        session = self._get_session()
        try:
            db_user = (
                session.query(DBUser)
                .filter(DBUser.email == email)
                .with_for_update()
                .first()
            )

            if not db_user:
                raise NotFoundException(f"User {email} not found")

            db_user.is_trial = False
            session.commit()
            logger.info(f"User {email} upgraded from trial to paid")

            return True
        except NotFoundException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error upgrading user {email}: {e}")
            raise
        finally:
            self._close_session(session)

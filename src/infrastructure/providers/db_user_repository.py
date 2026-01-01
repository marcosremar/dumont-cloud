"""
Database-based User Repository Implementation
Implements IUserRepository interface using SQLAlchemy and PostgreSQL
"""
import json
import logging
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ...core.exceptions import NotFoundException, ValidationException
from ...domain.repositories import IUserRepository
from ...domain.models import User as DomainUser
from ...models.user import User as DBUser
from ...config.database import SessionLocal

logger = logging.getLogger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DBUserRepository(IUserRepository):
    """
    Database implementation of IUserRepository.
    Stores users in PostgreSQL using SQLAlchemy.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize database user repository.

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

    def _db_to_domain(self, db_user: DBUser) -> DomainUser:
        """Convert SQLAlchemy model to domain model."""
        settings = {}
        if db_user.settings:
            try:
                settings = json.loads(db_user.settings)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON settings for user {db_user.email}")
                settings = {}

        return DomainUser(
            email=db_user.email,
            password_hash=db_user.hashed_password,
            vast_api_key=db_user.vast_api_key,
            settings=settings,
        )

    def get_user(self, email: str) -> Optional[DomainUser]:
        """Get user by email."""
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                return None
            return self._db_to_domain(db_user)
        finally:
            self._close_session(session)

    def create_user(self, email: str, password: str) -> DomainUser:
        """Create a new user."""
        if not email or not password:
            raise ValidationException("Email and password are required")

        session = self._get_session()
        try:
            # Check if user already exists
            existing = session.query(DBUser).filter(DBUser.email == email).first()
            if existing:
                raise ValidationException(f"User {email} already exists")

            password_hash = self._hash_password(password)

            db_user = DBUser(
                email=email,
                hashed_password=password_hash,
                vast_api_key=None,
                settings=json.dumps({}),
            )

            session.add(db_user)
            session.commit()
            session.refresh(db_user)

            logger.info(f"User {email} created")

            return DomainUser(
                email=email,
                password_hash=password_hash,
                vast_api_key=None,
                settings={},
            )
        except ValidationException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user {email}: {e}")
            raise
        finally:
            self._close_session(session)

    def update_user(self, email: str, updates: Dict[str, Any]) -> DomainUser:
        """Update user information."""
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                raise NotFoundException(f"User {email} not found")

            # Update allowed fields
            if "vast_api_key" in updates:
                db_user.vast_api_key = updates["vast_api_key"]

            if "settings" in updates:
                db_user.settings = json.dumps(updates["settings"])

            if "password" in updates:
                db_user.hashed_password = self._hash_password(updates["password"])

            session.commit()
            session.refresh(db_user)

            logger.info(f"User {email} updated")

            return self._db_to_domain(db_user)
        except NotFoundException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user {email}: {e}")
            raise
        finally:
            self._close_session(session)

    def delete_user(self, email: str) -> bool:
        """Delete a user."""
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                return False

            session.delete(db_user)
            session.commit()
            logger.info(f"User {email} deleted")

            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting user {email}: {e}")
            raise
        finally:
            self._close_session(session)

    def verify_password(self, email: str, password: str) -> bool:
        """Verify user password using bcrypt."""
        session = self._get_session()
        try:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                return False

            return pwd_context.verify(password, db_user.hashed_password)
        finally:
            self._close_session(session)

    def update_settings(self, email: str, settings: Dict[str, Any]) -> DomainUser:
        """Update user settings."""
        return self.update_user(email, {"settings": settings})

    def get_settings(self, email: str) -> Dict[str, Any]:
        """Get user settings."""
        user = self.get_user(email)
        if not user:
            raise NotFoundException(f"User {email} not found")
        return user.settings

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

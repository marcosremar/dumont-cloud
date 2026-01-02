"""
Database-based User Repository Implementation
Implements IUserRepository interface using SQLAlchemy and PostgreSQL
"""
import bcrypt
import json
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ...core.exceptions import NotFoundException, ValidationException
from ...domain.repositories import IUserRepository
from ...domain.models import User as DomainUser
from ...models.user import User as DBUser
from ...config.database import SessionLocal

logger = logging.getLogger(__name__)


class DBUserRepository(IUserRepository):
    """
    Database implementation of IUserRepository.
    Stores users in PostgreSQL using SQLAlchemy.
from ...models.db_user import User as DBUser
from ...config.db_session import get_db_session

logger = logging.getLogger(__name__)


class DatabaseUserRepository(IUserRepository):
    """
    Database-based implementation of IUserRepository.
    Stores users in PostgreSQL using SQLAlchemy ORM.
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
            session: Optional SQLAlchemy session. If not provided,
                     sessions are created per-operation using context manager.
        """
        self._session = session

    def _get_session(self):
        """Get the current session or create a new one."""
        if self._session:
            return self._session
        return None

    def get_user(self, email: str) -> Optional[DomainUser]:
        """Get user by email"""
        if self._session:
            db_user = self._session.query(DBUser).filter(DBUser.email == email).first()
            return self._to_domain(db_user) if db_user else None

        with get_db_session() as session:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            return self._to_domain(db_user) if db_user else None

    def get_user_by_id(self, user_id: int) -> Optional[DomainUser]:
        """Get user by ID"""
        if self._session:
            db_user = self._session.query(DBUser).filter(DBUser.id == user_id).first()
            return self._to_domain(db_user) if db_user else None

        with get_db_session() as session:
            db_user = session.query(DBUser).filter(DBUser.id == user_id).first()
            return self._to_domain(db_user) if db_user else None

    def get_user_by_sso(self, provider: str, external_id: str) -> Optional[DomainUser]:
        """Get user by SSO provider and external ID"""
        if self._session:
            db_user = self._session.query(DBUser).filter(
                DBUser.sso_provider == provider,
                DBUser.sso_external_id == external_id
            ).first()
            return self._to_domain(db_user) if db_user else None

        with get_db_session() as session:
            db_user = session.query(DBUser).filter(
                DBUser.sso_provider == provider,
                DBUser.sso_external_id == external_id
            ).first()
            return self._to_domain(db_user) if db_user else None

    def create_user(self, email: str, password: str) -> DomainUser:
        """Create a new user"""
        if not email or not password:
            raise ValidationException("Email and password are required")

        password_hash = self._hash_password(password)

        db_user = DBUser(
            email=email,
            password_hash=password_hash,
            vast_api_key=None,
            settings={},
        )

        if self._session:
            try:
                self._session.add(db_user)
                self._session.flush()
                logger.info(f"User {email} created")
                return self._to_domain(db_user)
            except IntegrityError:
                self._session.rollback()
                raise ValidationException(f"User {email} already exists")

        with get_db_session() as session:
            try:
                session.add(db_user)
                session.flush()
                logger.info(f"User {email} created")
                return self._to_domain(db_user)
            except IntegrityError:
                session.rollback()
                raise ValidationException(f"User {email} already exists")

    def create_sso_user(
        self,
        email: str,
        provider: str,
        external_id: str,
        name: Optional[str] = None,
        roles: Optional[str] = None,
    ) -> DomainUser:
        """Create a new SSO-authenticated user (no password)"""
        if not email:
            raise ValidationException("Email is required")
        if not provider or not external_id:
            raise ValidationException("SSO provider and external_id are required")

        db_user = DBUser(
            email=email,
            password_hash=None,  # SSO users don't have passwords
            name=name,
            sso_provider=provider,
            sso_external_id=external_id,
            sso_enforced=True,
            vast_api_key=None,
            settings={},
            roles=roles or "user",
        )

        if self._session:
            try:
                self._session.add(db_user)
                self._session.flush()
                logger.info(f"SSO user {email} created (provider: {provider})")
                return self._to_domain(db_user)
            except IntegrityError:
                self._session.rollback()
                raise ValidationException(f"User {email} already exists")

        with get_db_session() as session:
            try:
                session.add(db_user)
                session.flush()
                logger.info(f"SSO user {email} created (provider: {provider})")
                return self._to_domain(db_user)
            except IntegrityError:
                session.rollback()
                raise ValidationException(f"User {email} already exists")

    def update_user(self, email: str, updates: Dict[str, Any]) -> DomainUser:
        """Update user information"""
        if self._session:
            return self._update_user_in_session(self._session, email, updates)

        with get_db_session() as session:
            return self._update_user_in_session(session, email, updates)

    def _update_user_in_session(
        self, session: Session, email: str, updates: Dict[str, Any]
    ) -> DomainUser:
        """Update user within a session context"""
        db_user = session.query(DBUser).filter(DBUser.email == email).first()
        if not db_user:
            raise NotFoundException(f"User {email} not found")

        # Update allowed fields
        if "vast_api_key" in updates:
            db_user.vast_api_key = updates["vast_api_key"]

        if "settings" in updates:
            db_user.settings = updates["settings"]

        if "password" in updates:
            db_user.password_hash = self._hash_password(updates["password"])

        if "name" in updates:
            db_user.name = updates["name"]

        if "sso_provider" in updates:
            db_user.sso_provider = updates["sso_provider"]

        if "sso_external_id" in updates:
            db_user.sso_external_id = updates["sso_external_id"]

        if "sso_enforced" in updates:
            db_user.sso_enforced = updates["sso_enforced"]

        if "last_sso_login" in updates:
            db_user.last_sso_login = updates["last_sso_login"]

        if "is_active" in updates:
            db_user.is_active = updates["is_active"]

        if "organization_id" in updates:
            db_user.organization_id = updates["organization_id"]

        if "roles" in updates:
            db_user.roles = updates["roles"]

        session.flush()
        logger.info(f"User {email} updated")

        return self._to_domain(db_user)

    def delete_user(self, email: str) -> bool:
        """Delete a user"""
        if self._session:
            db_user = self._session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                return False
            self._session.delete(db_user)
            self._session.flush()
            logger.info(f"User {email} deleted")
            return True

        with get_db_session() as session:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user:
                return False
            session.delete(db_user)
            session.flush()
            logger.info(f"User {email} deleted")
            return True

    def verify_password(self, email: str, password: str) -> bool:
        """Verify user password using bcrypt"""
        if self._session:
            db_user = self._session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user or not db_user.password_hash:
                return False
            return bcrypt.checkpw(password.encode(), db_user.password_hash.encode())

        with get_db_session() as session:
            db_user = session.query(DBUser).filter(DBUser.email == email).first()
            if not db_user or not db_user.password_hash:
                return False
            return bcrypt.checkpw(password.encode(), db_user.password_hash.encode())

    def update_settings(self, email: str, settings: Dict[str, Any]) -> DomainUser:
        """Update user settings"""
        return self.update_user(email, {"settings": settings})

    def get_settings(self, email: str) -> Dict[str, Any]:
        """Get user settings"""
        user = self.get_user(email)
        if not user:
            raise NotFoundException(f"User {email} not found")
        return user.settings

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    def update_last_sso_login(self, email: str) -> DomainUser:
        """Update last SSO login timestamp"""
        from datetime import datetime
        return self.update_user(email, {"last_sso_login": datetime.utcnow()})

    def link_sso(
        self, email: str, provider: str, external_id: str, enforce: bool = False
    ) -> DomainUser:
        """Link an existing user to an SSO provider"""
        return self.update_user(email, {
            "sso_provider": provider,
            "sso_external_id": external_id,
            "sso_enforced": enforce,
        })

    def unlink_sso(self, email: str) -> DomainUser:
        """Unlink a user from SSO (requires password to be set first)"""
        user = self.get_user(email)
        if not user:
            raise NotFoundException(f"User {email} not found")
        if not user.password_hash:
            raise ValidationException("Cannot unlink SSO without a password set")
        return self.update_user(email, {
            "sso_provider": None,
            "sso_external_id": None,
            "sso_enforced": False,
        })

    # Helper methods

    def _to_domain(self, db_user: DBUser) -> DomainUser:
        """Convert database user to domain user"""
        return DomainUser(
            email=db_user.email,
            password_hash=db_user.password_hash or "",
            vast_api_key=db_user.vast_api_key,
            settings=db_user.settings or {},
        )

    def _hash_password(self, password: str) -> str:
        """Hash a password (simple SHA-256 for now)"""
        # NOTE: In production, use bcrypt or argon2
        return hashlib.sha256(password.encode()).hexdigest()

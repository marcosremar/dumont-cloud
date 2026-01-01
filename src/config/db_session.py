"""
Utilities for database session management.

Provides context managers and helpers for managing database sessions
with proper transaction handling and cleanup.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

from src.config.database import SessionLocal, engine


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.

    Usage:
        with get_db_session() as db:
            db.query(User).all()

    Automatically handles:
        - Session creation
        - Rollback on exception
        - Session close on exit
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db_session_no_commit() -> Generator[Session, None, None]:
    """
    Context manager for database sessions without auto-commit.

    Useful for read-only operations or when you want manual
    control over transaction commits.

    Usage:
        with get_db_session_no_commit() as db:
            users = db.query(User).all()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def transaction(session: Session) -> Generator[Session, None, None]:
    """
    Context manager for explicit transaction boundaries.

    Usage:
        with get_db_session_no_commit() as db:
            with transaction(db):
                db.add(user)
                db.add(sso_config)
                # Commits on successful exit
    """
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def create_session() -> Session:
    """
    Create a new database session.

    Caller is responsible for:
        - Committing/rolling back transactions
        - Closing the session

    Prefer using get_db_session() context manager when possible.
    """
    return SessionLocal()


def check_connection() -> bool:
    """
    Check if database connection is available.

    Returns:
        True if connection succeeds, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def get_pool_status() -> dict:
    """
    Get current connection pool status.

    Returns:
        Dictionary with pool statistics:
            - size: configured pool size
            - checked_in: available connections
            - checked_out: connections in use
            - overflow: current overflow count
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }

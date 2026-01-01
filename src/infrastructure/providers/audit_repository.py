"""
SQLAlchemy Audit Repository Implementation
Implements IAuditRepository interface (Dependency Inversion Principle)
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ...core.exceptions import NotFoundException
from ...domain.repositories import IAuditRepository
from ...models.rbac import AuditLog

logger = logging.getLogger(__name__)


class SQLAlchemyAuditRepository(IAuditRepository):
    """
    SQLAlchemy implementation of IAuditRepository.
    Stores audit logs in PostgreSQL.
    """

    def __init__(self, session: Session):
        """
        Initialize SQLAlchemy audit repository

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create_log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        team_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = 'success',
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Create a new audit log entry"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            team_id=team_id,
            details=json.dumps(details) if details else None,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )

        self.session.add(log)
        self.session.flush()
        logger.debug(f"Audit log created: {action} on {resource_type} by {user_id}")

        return log

    def get_log(self, log_id: int) -> Optional[AuditLog]:
        """Get a specific audit log entry by ID"""
        return self.session.query(AuditLog).filter(AuditLog.id == log_id).first()

    def _apply_filters(
        self,
        query,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        team_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ):
        """Apply common filters to a query"""
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if team_id:
            query = query.filter(AuditLog.team_id == team_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        if status:
            query = query.filter(AuditLog.status == status)

        return query

    def get_logs_for_team(
        self,
        team_id: int,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[AuditLog]:
        """Get audit logs for a team with filtering and pagination"""
        query = self.session.query(AuditLog).filter(AuditLog.team_id == team_id)

        query = self._apply_filters(
            query,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            status=status
        )

        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    def get_logs_for_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        team_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[AuditLog]:
        """Get audit logs for a user with filtering and pagination"""
        query = self.session.query(AuditLog).filter(AuditLog.user_id == user_id)

        query = self._apply_filters(
            query,
            action=action,
            resource_type=resource_type,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            status=status
        )

        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    def get_logs_for_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Get audit logs for a specific resource"""
        query = self.session.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )

        if action:
            query = query.filter(AuditLog.action == action)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    def get_logs_by_action(
        self,
        action: str,
        limit: int = 50,
        offset: int = 0,
        team_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Get audit logs by action type"""
        query = self.session.query(AuditLog).filter(AuditLog.action == action)

        if team_id:
            query = query.filter(AuditLog.team_id == team_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    def count_logs_for_team(
        self,
        team_id: int,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> int:
        """Count audit logs for a team (for pagination)"""
        query = self.session.query(AuditLog).filter(AuditLog.team_id == team_id)

        query = self._apply_filters(
            query,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            status=status
        )

        return query.count()

    def count_logs_for_user(
        self,
        user_id: str,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        team_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> int:
        """Count audit logs for a user (for pagination)"""
        query = self.session.query(AuditLog).filter(AuditLog.user_id == user_id)

        query = self._apply_filters(
            query,
            action=action,
            resource_type=resource_type,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            status=status
        )

        return query.count()

    def get_recent_activity(
        self,
        team_id: int,
        limit: int = 10
    ) -> List[AuditLog]:
        """Get recent activity for a team dashboard"""
        return self.session.query(AuditLog).filter(
            AuditLog.team_id == team_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()

    def get_failed_actions(
        self,
        team_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Get failed or denied actions for security monitoring"""
        query = self.session.query(AuditLog).filter(
            or_(
                AuditLog.status == 'failure',
                AuditLog.status == 'denied'
            )
        )

        if team_id:
            query = query.filter(AuditLog.team_id == team_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()

    def delete_old_logs(
        self,
        older_than: datetime,
        batch_size: int = 1000
    ) -> int:
        """Delete logs older than specified date (for retention policy)"""
        total_deleted = 0

        while True:
            # Delete in batches to avoid locking the table for too long
            subquery = self.session.query(AuditLog.id).filter(
                AuditLog.created_at < older_than
            ).limit(batch_size).subquery()

            result = self.session.query(AuditLog).filter(
                AuditLog.id.in_(subquery)
            ).delete(synchronize_session='fetch')

            self.session.flush()
            total_deleted += result

            if result < batch_size:
                break

        if total_deleted > 0:
            logger.info(f"Deleted {total_deleted} old audit logs")

        return total_deleted

    def export_logs(
        self,
        team_id: int,
        start_date: datetime,
        end_date: datetime,
        format: str = 'json'
    ) -> Any:
        """Export audit logs for compliance/reporting"""
        logs = self.session.query(AuditLog).filter(
            AuditLog.team_id == team_id,
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date
        ).order_by(AuditLog.created_at).all()

        if format == 'json':
            return [log.to_dict() for log in logs]
        elif format == 'csv':
            # Return data in a format suitable for CSV conversion
            return {
                'headers': [
                    'id', 'user_id', 'team_id', 'action', 'resource_type',
                    'resource_id', 'status', 'ip_address', 'created_at'
                ],
                'rows': [
                    [
                        log.id, log.user_id, log.team_id, log.action,
                        log.resource_type, log.resource_id, log.status,
                        log.ip_address, log.created_at.isoformat() if log.created_at else None
                    ]
                    for log in logs
                ]
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")

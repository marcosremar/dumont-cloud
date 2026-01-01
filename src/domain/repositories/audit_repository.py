"""
Abstract interface for audit log storage (Dependency Inversion Principle)
Allows swapping between different storage implementations
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class IAuditRepository(ABC):
    """Abstract interface for audit log storage"""

    @abstractmethod
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
    ) -> Any:
        """Create a new audit log entry"""
        pass

    @abstractmethod
    def get_log(self, log_id: int) -> Optional[Any]:
        """Get a specific audit log entry by ID"""
        pass

    @abstractmethod
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
    ) -> List[Any]:
        """Get audit logs for a team with filtering and pagination"""
        pass

    @abstractmethod
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
    ) -> List[Any]:
        """Get audit logs for a user with filtering and pagination"""
        pass

    @abstractmethod
    def get_logs_for_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Any]:
        """Get audit logs for a specific resource"""
        pass

    @abstractmethod
    def get_logs_by_action(
        self,
        action: str,
        limit: int = 50,
        offset: int = 0,
        team_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Any]:
        """Get audit logs by action type"""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_recent_activity(
        self,
        team_id: int,
        limit: int = 10
    ) -> List[Any]:
        """Get recent activity for a team dashboard"""
        pass

    @abstractmethod
    def get_failed_actions(
        self,
        team_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Any]:
        """Get failed or denied actions for security monitoring"""
        pass

    @abstractmethod
    def delete_old_logs(
        self,
        older_than: datetime,
        batch_size: int = 1000
    ) -> int:
        """Delete logs older than specified date (for retention policy)"""
        pass

    @abstractmethod
    def export_logs(
        self,
        team_id: int,
        start_date: datetime,
        end_date: datetime,
        format: str = 'json'
    ) -> Any:
        """Export audit logs for compliance/reporting"""
        pass

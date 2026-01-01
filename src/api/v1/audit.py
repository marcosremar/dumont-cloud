"""
Audit Log API endpoints

Provides access to team audit logs with filtering and pagination.
Requires audit.view permission to access.
"""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .dependencies import (
    get_current_user_email,
    require_permission,
)
from ...config.database import get_db
from ...core.permissions import AUDIT_VIEW
from ...infrastructure.providers import SQLAlchemyTeamRepository, SQLAlchemyAuditRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["Audit Logs"])


# Request/Response models

class AuditLogResponse(BaseModel):
    """Audit log entry response"""
    id: int
    user_id: str
    team_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response"""
    logs: List[AuditLogResponse]
    count: int
    total: int
    limit: int
    offset: int


class RecentActivityResponse(BaseModel):
    """Recent activity response for dashboard"""
    logs: List[AuditLogResponse]
    count: int


# Helper functions

def get_team_repository(db: Session = Depends(get_db)) -> SQLAlchemyTeamRepository:
    """Get team repository instance"""
    return SQLAlchemyTeamRepository(session=db)


def get_audit_repository(db: Session = Depends(get_db)) -> SQLAlchemyAuditRepository:
    """Get audit repository instance"""
    return SQLAlchemyAuditRepository(session=db)


# Audit Log Endpoints

@router.get("/{team_id}/audit-logs", response_model=AuditLogListResponse)
async def get_team_audit_logs(
    team_id: int,
    user_email: str = Depends(require_permission(AUDIT_VIEW)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    audit_repo: SQLAlchemyAuditRepository = Depends(get_audit_repository),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    action: Optional[str] = Query(None, description="Filter by action type (e.g., 'member.added', 'gpu.provisioned')"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (e.g., 'team_member', 'gpu_instance')"),
    user_id: Optional[str] = Query(None, description="Filter by user who performed the action"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: success, failure, denied"),
    start_date: Optional[datetime] = Query(None, description="Filter logs from this date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter logs until this date (ISO format)"),
):
    """
    Get audit logs for a team

    Returns paginated audit logs with optional filtering. Requires audit.view permission.
    Logs are sorted by creation time (newest first).
    """
    # Check if user is a member of the team
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    # Get audit logs with filters
    logs = audit_repo.get_logs_for_team(
        team_id=team_id,
        limit=limit,
        offset=offset,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
    )

    # Get total count for pagination
    total_count = audit_repo.count_logs_for_team(
        team_id=team_id,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
    )

    # Convert to response models
    log_responses = []
    for log in logs:
        log_responses.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            team_id=log.team_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at,
        ))

    return AuditLogListResponse(
        logs=log_responses,
        count=len(log_responses),
        total=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/{team_id}/audit-logs/recent", response_model=RecentActivityResponse)
async def get_recent_activity(
    team_id: int,
    user_email: str = Depends(require_permission(AUDIT_VIEW)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    audit_repo: SQLAlchemyAuditRepository = Depends(get_audit_repository),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of recent activities to return"),
):
    """
    Get recent activity for a team

    Returns the most recent audit log entries for the team dashboard.
    Requires audit.view permission.
    """
    # Check if user is a member of the team
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    # Get recent activity
    logs = audit_repo.get_recent_activity(
        team_id=team_id,
        limit=limit,
    )

    # Convert to response models
    log_responses = []
    for log in logs:
        log_responses.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            team_id=log.team_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at,
        ))

    return RecentActivityResponse(
        logs=log_responses,
        count=len(log_responses),
    )


@router.get("/{team_id}/audit-logs/failed", response_model=AuditLogListResponse)
async def get_failed_actions(
    team_id: int,
    user_email: str = Depends(require_permission(AUDIT_VIEW)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    audit_repo: SQLAlchemyAuditRepository = Depends(get_audit_repository),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    start_date: Optional[datetime] = Query(None, description="Filter logs from this date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter logs until this date (ISO format)"),
):
    """
    Get failed or denied actions for security monitoring

    Returns audit logs where the status is 'failure' or 'denied'.
    Useful for security monitoring and troubleshooting.
    Requires audit.view permission.
    """
    # Check if user is a member of the team
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    # Get failed actions
    logs = audit_repo.get_failed_actions(
        team_id=team_id,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )

    # Get total count
    # Note: We count failure and denied separately and sum them
    total_count = (
        audit_repo.count_logs_for_team(team_id=team_id, status='failure', start_date=start_date, end_date=end_date) +
        audit_repo.count_logs_for_team(team_id=team_id, status='denied', start_date=start_date, end_date=end_date)
    )

    # Convert to response models
    log_responses = []
    for log in logs:
        log_responses.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            team_id=log.team_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            status=log.status,
            error_message=log.error_message,
            created_at=log.created_at,
        ))

    return AuditLogListResponse(
        logs=log_responses,
        count=len(log_responses),
        total=total_count,
        limit=limit,
        offset=offset,
    )


@router.get("/{team_id}/audit-logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    team_id: int,
    log_id: int,
    user_email: str = Depends(require_permission(AUDIT_VIEW)),
    team_repo: SQLAlchemyTeamRepository = Depends(get_team_repository),
    audit_repo: SQLAlchemyAuditRepository = Depends(get_audit_repository),
):
    """
    Get a specific audit log entry

    Returns detailed information about a single audit log entry.
    Requires audit.view permission.
    """
    # Check if user is a member of the team
    member = team_repo.get_member(team_id, user_email)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    # Get the audit log
    log = audit_repo.get_log(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {log_id} not found",
        )

    # Verify the log belongs to this team
    if log.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {log_id} not found in this team",
        )

    return AuditLogResponse(
        id=log.id,
        user_id=log.user_id,
        team_id=log.team_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        details=log.details,
        old_value=log.old_value,
        new_value=log.new_value,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        status=log.status,
        error_message=log.error_message,
        created_at=log.created_at,
    )

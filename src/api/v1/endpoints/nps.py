"""
NPS (Net Promoter Score) API endpoints
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..schemas.nps import (
    NPSSubmissionRequest,
    NPSSubmissionResponse,
    NPSDismissRequest,
    NPSShouldShowResponse,
    NPSTrendsResponse,
    NPSDetractorsResponse,
    NPSFollowupUpdateRequest,
    NPSFollowupUpdateResponse,
    NPSConfigListResponse,
    NPSConfigItem,
)
from ....domain.services.nps_service import NPSService
from ....core.exceptions import ValidationException, NotFoundException
from ....config.database import get_db
from ..dependencies import get_current_user_email, get_current_user_email_optional

router = APIRouter(prefix="/nps", tags=["NPS"])


def get_nps_service() -> NPSService:
    """Get NPS service instance"""
    return NPSService()


@router.get("/should-show", response_model=NPSShouldShowResponse)
async def should_show_survey(
    trigger_type: str = Query(..., description="Survey trigger type (first_deployment, monthly, issue_resolution)"),
    user_email: Optional[str] = Depends(get_current_user_email_optional),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Check if NPS survey should be shown to user

    Returns whether the survey should be displayed based on:
    - Trigger type configuration (enabled/disabled)
    - Rate limiting (user hasn't submitted/dismissed within frequency window)
    """
    # If user is not authenticated, don't show survey
    if not user_email:
        return NPSShouldShowResponse(
            should_show=False,
            reason="User is not authenticated",
            trigger_type=None,
            survey_config=None,
        )

    try:
        result = nps_service.should_show_survey(
            user_id=user_email,
            trigger_type=trigger_type,
            session=db,
        )
        return NPSShouldShowResponse(**result)
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/submit", response_model=NPSSubmissionResponse)
async def submit_nps(
    request: NPSSubmissionRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Submit NPS survey response

    Stores the user's NPS score (0-10) and optional comment.
    Automatically categorizes as detractor (0-6), passive (7-8), or promoter (9-10).
    Records submission for rate limiting.
    """
    try:
        result = nps_service.submit_response(
            user_id=user_email,
            score=request.score,
            trigger_type=request.trigger_type,
            comment=request.comment,
            session=db,
        )
        return NPSSubmissionResponse(
            success=result['success'],
            id=result['id'],
            category=result['category'],
            message=result['message'],
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/dismiss", response_model=dict)
async def dismiss_survey(
    request: NPSDismissRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Record NPS survey dismissal

    Tracks when a user dismisses the survey for rate limiting purposes.
    Survey won't be shown again until the frequency window expires.
    """
    try:
        result = nps_service.record_dismissal(
            user_id=user_email,
            trigger_type=request.trigger_type,
            reason=request.reason,
            session=db,
        )
        return result
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/trends", response_model=NPSTrendsResponse)
async def get_trends(
    start_date: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Get NPS trends for admin dashboard

    Returns:
    - NPS score data points over time
    - Category breakdown (detractors, passives, promoters)
    - Current overall NPS score
    - Average score and total responses
    """
    # Parse dates if provided
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format: YYYY-MM-DD",
            )

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format: YYYY-MM-DD",
            )

    result = nps_service.get_trends(
        start_date=start_dt,
        end_date=end_dt,
        session=db,
    )

    return NPSTrendsResponse(**result)


@router.get("/detractors", response_model=NPSDetractorsResponse)
async def get_detractors(
    pending_only: bool = Query(False, description="Only return detractors needing follow-up"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Results offset for pagination"),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Get list of detractor responses for follow-up

    Returns detractor responses (scores 0-6) with their comments.
    Can filter to show only those needing follow-up.
    """
    result = nps_service.get_detractors(
        pending_only=pending_only,
        limit=limit,
        offset=offset,
        session=db,
    )

    return NPSDetractorsResponse(**result)


@router.put("/responses/{response_id}/followup", response_model=NPSFollowupUpdateResponse)
async def update_followup(
    response_id: int,
    request: NPSFollowupUpdateRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Update follow-up status for a detractor response

    Mark a detractor response as followed up and add notes.
    """
    try:
        result = nps_service.update_followup(
            response_id=response_id,
            followup_completed=request.followup_completed,
            followup_notes=request.followup_notes,
            session=db,
        )
        return NPSFollowupUpdateResponse(
            success=result['success'],
            id=result['id'],
            message=result['message'],
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/config", response_model=NPSConfigListResponse)
async def get_survey_configs(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Get all NPS survey configurations

    Returns configuration for all trigger types (first_deployment, monthly, issue_resolution).
    """
    configs = nps_service.get_survey_configs(session=db)

    return NPSConfigListResponse(
        configs=[NPSConfigItem(**c) for c in configs],
        count=len(configs),
    )


@router.put("/config/{trigger_type}", response_model=NPSConfigItem)
async def update_survey_config(
    trigger_type: str,
    enabled: Optional[bool] = Query(None, description="Whether to enable this trigger"),
    frequency_days: Optional[int] = Query(None, ge=1, le=365, description="Minimum days between surveys"),
    title: Optional[str] = Query(None, max_length=200, description="Custom survey title"),
    description: Optional[str] = Query(None, max_length=500, description="Custom survey description"),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
    nps_service: NPSService = Depends(get_nps_service),
):
    """
    Update NPS survey configuration for a trigger type

    Allows enabling/disabling triggers and customizing survey appearance.
    """
    try:
        result = nps_service.update_survey_config(
            trigger_type=trigger_type,
            enabled=enabled,
            frequency_days=frequency_days,
            title=title,
            description=description,
            session=db,
        )
        return NPSConfigItem(**result)
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

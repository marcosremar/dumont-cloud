"""
GPU Reservation API endpoints

CRUD operations for GPU reservations with availability checking,
pricing estimates, and credit management.
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..schemas.request import (
    ReservationCreateRequest,
    CheckAvailabilityRequest,
    CancelReservationRequest,
    PurchaseCreditsRequest,
)
from ..schemas.response import (
    ReservationResponse,
    ListReservationsResponse,
    AvailabilityResponse,
    PricingEstimateResponse,
    CancelReservationResponse,
    CreditBalanceResponse,
    ReservationCreditResponse,
    ListCreditsResponse,
    SuccessResponse,
)
from ..dependencies import require_auth, get_current_user_email
from ....config.database import get_db
from ....services.reservation_service import (
    ReservationService,
    ReservationConflictException,
    InsufficientCreditsException,
)
from ....models.reservation import ReservationStatus
from ....models.reservation_credit import (
    ReservationCredit,
    CreditStatus,
    CreditTransactionType,
)
from ....core.exceptions import (
    NotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"],
    dependencies=[Depends(require_auth)]
)


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    """Get reservation service with database session."""
    return ReservationService(db)


# =============================================================================
# RESERVATION CRUD ENDPOINTS
# =============================================================================

@router.get("", response_model=ListReservationsResponse)
async def list_reservations(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: pending, active, completed, cancelled, failed"
    ),
    include_past: bool = Query(
        False,
        description="Include completed and cancelled reservations"
    ),
    user_email: str = Depends(get_current_user_email),
    service: ReservationService = Depends(get_reservation_service),
):
    """
    List all GPU reservations for the current user.

    Returns a list of reservations with optional filtering by status.
    By default, only pending and active reservations are returned.
    """
    # Parse status filter
    reservation_status = None
    if status_filter:
        try:
            reservation_status = ReservationStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Valid values: pending, active, completed, cancelled, failed"
            )

    reservations = service.get_user_reservations(
        user_id=user_email,
        status=reservation_status,
        include_past=include_past
    )

    reservation_responses = [
        ReservationResponse.from_model(r) for r in reservations
    ]

    return ListReservationsResponse(
        reservations=reservation_responses,
        count=len(reservation_responses)
    )


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    request: ReservationCreateRequest,
    user_email: str = Depends(get_current_user_email),
    service: ReservationService = Depends(get_reservation_service),
):
    """
    Create a new GPU reservation.

    Reserves GPU capacity for a specified time period with 10-20% discount
    off spot pricing. Credits are deducted upfront.

    Validates:
    - Time range (future start, end after start, min 1h, max 30 days)
    - GPU availability for requested time slot
    - User has sufficient credits
    """
    try:
        # Parse datetime strings
        try:
            start_time = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
            # Remove timezone info for consistency with database
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime format: {e}. Use ISO 8601 format (e.g., 2024-02-01T10:00:00Z)"
            )

        reservation = service.create_reservation(
            user_id=user_email,
            gpu_type=request.gpu_type,
            start_time=start_time,
            end_time=end_time,
            gpu_count=request.gpu_count,
        )

        return ReservationResponse.from_model(reservation)

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ReservationConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except InsufficientCreditsException as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: int,
    user_email: str = Depends(get_current_user_email),
    service: ReservationService = Depends(get_reservation_service),
):
    """
    Get a specific reservation by ID.

    Returns detailed information about a reservation including
    pricing, status, and credit information.
    """
    try:
        reservation = service.get_reservation(reservation_id)

        # Verify ownership
        if reservation.user_id != user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this reservation"
            )

        return ReservationResponse.from_model(reservation)

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{reservation_id}", response_model=CancelReservationResponse)
async def cancel_reservation(
    reservation_id: int,
    request: Optional[CancelReservationRequest] = None,
    user_email: str = Depends(get_current_user_email),
    service: ReservationService = Depends(get_reservation_service),
):
    """
    Cancel a reservation and refund unused credits.

    For pending reservations: Full refund
    For active reservations: Partial refund based on unused time
    For completed/cancelled: Cannot be cancelled

    Returns the refund amount and percentage.
    """
    try:
        reservation = service.get_reservation(reservation_id)

        # Verify ownership
        if reservation.user_id != user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this reservation"
            )

        reason = request.reason if request else None
        updated_reservation, refund_credit = service.cancel_reservation(
            reservation_id=reservation_id,
            reason=reason
        )

        credits_refunded = refund_credit.amount if refund_credit else 0.0
        refund_percentage = (
            (credits_refunded / reservation.credits_used * 100)
            if reservation.credits_used > 0 else 0.0
        )

        return CancelReservationResponse(
            success=True,
            reservation_id=reservation_id,
            message=f"Reservation {reservation_id} cancelled successfully",
            credits_refunded=credits_refunded,
            refund_percentage=round(refund_percentage, 2)
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =============================================================================
# AVAILABILITY & PRICING ENDPOINTS
# =============================================================================

@router.get("/availability", response_model=AvailabilityResponse)
async def check_availability(
    gpu_type: str = Query(..., description="GPU type (e.g., 'A100', 'H100')"),
    start: str = Query(..., alias="start", description="Start time (ISO 8601 format, UTC)"),
    end: str = Query(..., alias="end", description="End time (ISO 8601 format, UTC)"),
    gpu_count: int = Query(1, ge=1, le=8, description="Number of GPUs"),
    service: ReservationService = Depends(get_reservation_service),
):
    """
    Check GPU availability for a specific time slot.

    Returns whether the requested GPU capacity is available
    and the number of conflicting reservations.
    """
    try:
        start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}. Use ISO 8601 format"
        )

    availability = service.get_availability_details(
        gpu_type=gpu_type,
        start_time=start_time,
        end_time=end_time
    )

    return AvailabilityResponse(
        available=availability["available"],
        gpu_type=gpu_type,
        gpu_count=gpu_count,
        start_time=start,
        end_time=end,
        capacity=1 if availability["available"] else 0,
        conflicting_reservations=availability["conflicting_reservations"],
        message="GPU available for reservation" if availability["available"] else "GPU not available for requested time slot"
    )


@router.get("/pricing", response_model=PricingEstimateResponse)
async def get_pricing_estimate(
    gpu_type: str = Query(..., description="GPU type (e.g., 'A100', 'H100')"),
    start: str = Query(..., alias="start", description="Start time (ISO 8601 format, UTC)"),
    end: str = Query(..., alias="end", description="End time (ISO 8601 format, UTC)"),
    gpu_count: int = Query(1, ge=1, le=8, description="Number of GPUs"),
    service: ReservationService = Depends(get_reservation_service),
):
    """
    Get pricing estimate for a reservation.

    Returns the spot price, discounted reservation price,
    total cost, and savings amount.
    """
    try:
        start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {e}. Use ISO 8601 format"
        )

    pricing = service.calculate_pricing(
        gpu_type=gpu_type,
        start_time=start_time,
        end_time=end_time,
        gpu_count=gpu_count
    )

    return PricingEstimateResponse(
        gpu_type=gpu_type,
        gpu_count=gpu_count,
        duration_hours=pricing["duration_hours"],
        spot_price_per_hour=pricing["spot_price_per_hour"],
        discount_rate=pricing["discount_rate"],
        reserved_price_per_hour=pricing["reserved_price_per_hour"],
        total_spot_cost=pricing["spot_total"],
        total_reserved_cost=pricing["reserved_total"],
        savings=pricing["savings"],
        credits_required=pricing["credits_required"]
    )


# =============================================================================
# CREDIT MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/credits", response_model=CreditBalanceResponse)
async def get_credit_balance(
    user_email: str = Depends(get_current_user_email),
    service: ReservationService = Depends(get_reservation_service),
    db: Session = Depends(get_db),
):
    """
    Get user's reservation credit balance.

    Returns available credits, locked credits (in active reservations),
    and credits expiring within 7 days.
    """
    from sqlalchemy import func
    from datetime import timedelta

    available_credits = service.get_user_credit_balance(user_email)

    # Get locked credits
    now = datetime.utcnow()
    locked_total = db.query(func.sum(ReservationCredit.original_amount)).filter(
        ReservationCredit.user_id == user_email,
        ReservationCredit.status == CreditStatus.LOCKED
    ).scalar() or 0.0

    # Get credits expiring within 7 days
    seven_days = now + timedelta(days=7)
    expiring_soon = db.query(func.sum(ReservationCredit.amount)).filter(
        ReservationCredit.user_id == user_email,
        ReservationCredit.status == CreditStatus.AVAILABLE,
        ReservationCredit.expires_at <= seven_days,
        ReservationCredit.expires_at > now,
        ReservationCredit.amount > 0
    ).scalar() or 0.0

    # Get all credit details
    credits = db.query(ReservationCredit).filter(
        ReservationCredit.user_id == user_email,
        ReservationCredit.amount > 0
    ).order_by(ReservationCredit.expires_at.asc()).all()

    credit_responses = [
        ReservationCreditResponse.from_model(c) for c in credits
    ]

    return CreditBalanceResponse(
        user_id=user_email,
        available_credits=float(available_credits),
        locked_credits=float(locked_total),
        total_credits=float(available_credits) + float(locked_total),
        expiring_soon=float(expiring_soon),
        credits=credit_responses
    )


@router.post("/credits/purchase", response_model=ReservationCreditResponse)
async def purchase_credits(
    request: PurchaseCreditsRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Purchase reservation credits.

    Creates a new credit record for the user.
    Credits expire after 30 days if not used.

    Note: This is a mock implementation. In production,
    integrate with payment gateway.
    """
    credit = ReservationCredit.create_purchase(
        user_id=user_email,
        amount=request.amount,
        description=request.description or f"Credit purchase: {request.amount} credits"
    )

    db.add(credit)
    db.commit()
    db.refresh(credit)

    logger.info(f"User {user_email} purchased {request.amount} credits")

    return ReservationCreditResponse.from_model(credit)


@router.get("/credits/history", response_model=ListCreditsResponse)
async def get_credit_history(
    limit: int = Query(50, le=100, description="Maximum results"),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Get credit transaction history for the current user.

    Returns all credit records including purchases, deductions,
    refunds, and expired credits.
    """
    credits = db.query(ReservationCredit).filter(
        ReservationCredit.user_id == user_email
    ).order_by(
        ReservationCredit.created_at.desc()
    ).limit(limit).all()

    credit_responses = [
        ReservationCreditResponse.from_model(c) for c in credits
    ]

    return ListCreditsResponse(
        credits=credit_responses,
        count=len(credit_responses)
    )

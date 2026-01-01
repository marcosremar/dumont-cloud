"""
Reservation Service - Business Logic for GPU Reservations

Gerencia reservas de GPU com validacao de disponibilidade,
calculo de precos com desconto e gerenciamento de creditos.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.models.reservation import Reservation, ReservationStatus
from src.models.reservation_credit import (
    ReservationCredit, CreditStatus, CreditTransactionType, CREDIT_EXPIRY_DAYS
)
from src.models.usage import GPUPricingReference
from src.core.exceptions import (
    ValidationException,
    NotFoundException,
    InsufficientBalanceException,
    DumontCloudException,
)

logger = logging.getLogger(__name__)


# Configuration from environment variables
DISCOUNT_MIN = int(os.environ.get("RESERVATION_DISCOUNT_MIN", "10"))
DISCOUNT_MAX = int(os.environ.get("RESERVATION_DISCOUNT_MAX", "20"))


class ReservationConflictException(DumontCloudException):
    """Raised when a reservation conflicts with existing bookings."""
    def __init__(self, gpu_type: str, start_time: datetime, end_time: datetime):
        self.gpu_type = gpu_type
        self.start_time = start_time
        self.end_time = end_time
        message = f"GPU {gpu_type} not available from {start_time} to {end_time}"
        super().__init__(message, {
            "gpu_type": gpu_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        })


class InsufficientCreditsException(DumontCloudException):
    """Raised when user doesn't have enough credits for reservation."""
    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        message = f"Insufficient credits. Required: {required:.2f}, Available: {available:.2f}"
        super().__init__(message, {"required": required, "available": available})


class ReservationService:
    """
    Service for managing GPU reservations.

    Handles availability checking, pricing calculation with discounts,
    credit management, and reservation lifecycle.
    """

    def __init__(self, db: Session):
        """
        Initialize reservation service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def check_availability(
        self,
        gpu_type: str,
        start_time: datetime,
        end_time: datetime,
        gpu_count: int = 1,
        exclude_reservation_id: Optional[int] = None
    ) -> bool:
        """
        Check if GPU capacity is available for the requested time slot.

        Uses SQL query to detect overlapping reservations:
        WHERE gpu_type = X AND NOT (end_time <= new_start OR start_time >= new_end)

        Args:
            gpu_type: GPU model (e.g., "A100", "H100")
            start_time: Reservation start time (UTC)
            end_time: Reservation end time (UTC)
            gpu_count: Number of GPUs requested
            exclude_reservation_id: Reservation ID to exclude (for updates)

        Returns:
            True if capacity is available, False otherwise
        """
        logger.info(f"Checking availability for {gpu_type} from {start_time} to {end_time}")

        # Build query for overlapping reservations
        # Overlap condition: NOT (end_time <= start OR start_time >= end)
        # Equivalent to: end_time > start AND start_time < end
        query = self.db.query(func.count(Reservation.id)).filter(
            Reservation.gpu_type == gpu_type,
            Reservation.status.in_([
                ReservationStatus.PENDING,
                ReservationStatus.ACTIVE
            ]),
            Reservation.end_time > start_time,
            Reservation.start_time < end_time
        )

        if exclude_reservation_id:
            query = query.filter(Reservation.id != exclude_reservation_id)

        conflicting_count = query.scalar() or 0

        # For now, assume 1 GPU per type available
        # This can be extended with capacity management
        available = conflicting_count == 0

        logger.info(
            f"Availability check result: {available} "
            f"(found {conflicting_count} conflicting reservations)"
        )

        return available

    def get_availability_details(
        self,
        gpu_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get detailed availability information for a time slot.

        Args:
            gpu_type: GPU model
            start_time: Reservation start time (UTC)
            end_time: Reservation end time (UTC)

        Returns:
            Dictionary with availability details
        """
        # Get conflicting reservations
        conflicting = self.db.query(Reservation).filter(
            Reservation.gpu_type == gpu_type,
            Reservation.status.in_([
                ReservationStatus.PENDING,
                ReservationStatus.ACTIVE
            ]),
            Reservation.end_time > start_time,
            Reservation.start_time < end_time
        ).all()

        available = len(conflicting) == 0

        return {
            "available": available,
            "gpu_type": gpu_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "conflicting_reservations": len(conflicting),
            "conflicts": [
                {
                    "id": r.id,
                    "start_time": r.start_time.isoformat() if r.start_time else None,
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                }
                for r in conflicting
            ] if not available else []
        }

    def validate_reservation(
        self,
        user_id: str,
        gpu_type: str,
        start_time: datetime,
        end_time: datetime,
        gpu_count: int = 1
    ) -> Dict[str, Any]:
        """
        Validate a reservation request before creation.

        Performs all necessary validations:
        - Time range validation (start < end, not in past)
        - GPU type validation
        - Availability checking
        - Credit balance verification

        Args:
            user_id: User making the reservation
            gpu_type: GPU model requested
            start_time: Reservation start time (UTC)
            end_time: Reservation end time (UTC)
            gpu_count: Number of GPUs requested

        Returns:
            Dictionary with validation results

        Raises:
            ValidationException: If validation fails
        """
        errors = []
        warnings = []

        # Validate time range
        now = datetime.utcnow()
        if start_time <= now:
            errors.append("Reservation start time must be in the future")

        if end_time <= start_time:
            errors.append("Reservation end time must be after start time")

        # Minimum reservation duration: 1 hour
        if (end_time - start_time).total_seconds() < 3600:
            errors.append("Minimum reservation duration is 1 hour")

        # Maximum reservation duration: 30 days
        if (end_time - start_time).days > 30:
            errors.append("Maximum reservation duration is 30 days")

        # Validate GPU count
        if gpu_count < 1:
            errors.append("GPU count must be at least 1")

        # Check GPU type exists
        gpu_pricing = self.db.query(GPUPricingReference).filter(
            GPUPricingReference.gpu_type == gpu_type
        ).first()

        if not gpu_pricing:
            # Allow reservation even without pricing reference (use default)
            warnings.append(f"No pricing reference found for {gpu_type}, using default rates")

        # Check availability
        if not errors:  # Only check availability if no time errors
            if not self.check_availability(gpu_type, start_time, end_time, gpu_count):
                errors.append(f"GPU {gpu_type} not available for requested time slot")

        # Calculate pricing
        pricing = self.calculate_pricing(
            gpu_type=gpu_type,
            start_time=start_time,
            end_time=end_time,
            gpu_count=gpu_count
        )

        # Check credit balance
        available_credits = self.get_user_credit_balance(user_id)
        if available_credits < pricing["credits_required"]:
            errors.append(
                f"Insufficient credits. Required: {pricing['credits_required']:.2f}, "
                f"Available: {available_credits:.2f}"
            )

        is_valid = len(errors) == 0

        result = {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "pricing": pricing,
            "available_credits": available_credits,
        }

        if not is_valid:
            logger.warning(f"Reservation validation failed for user {user_id}: {errors}")

        return result

    def calculate_pricing(
        self,
        gpu_type: str,
        start_time: datetime,
        end_time: datetime,
        gpu_count: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate reservation pricing with discount.

        Discount is calculated based on reservation duration:
        - 1-24 hours: DISCOUNT_MIN (10%)
        - 24-168 hours (1 week): Linear interpolation
        - 168+ hours: DISCOUNT_MAX (20%)

        Args:
            gpu_type: GPU model
            start_time: Reservation start time
            end_time: Reservation end time
            gpu_count: Number of GPUs

        Returns:
            Dictionary with pricing details
        """
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600

        # Get spot price from reference table
        gpu_pricing = self.db.query(GPUPricingReference).filter(
            GPUPricingReference.gpu_type == gpu_type
        ).first()

        if gpu_pricing:
            spot_price_per_hour = gpu_pricing.dumont_hourly
        else:
            # Default fallback pricing
            spot_price_per_hour = 1.0

        # Calculate discount based on duration
        discount_rate = self._calculate_discount_rate(duration_hours)

        # Calculate prices
        spot_total = spot_price_per_hour * duration_hours * gpu_count
        discount_amount = spot_total * (discount_rate / 100)
        reserved_total = spot_total - discount_amount
        reserved_price_per_hour = spot_price_per_hour * (1 - discount_rate / 100)

        return {
            "gpu_type": gpu_type,
            "gpu_count": gpu_count,
            "duration_hours": round(duration_hours, 2),
            "spot_price_per_hour": round(spot_price_per_hour, 4),
            "reserved_price_per_hour": round(reserved_price_per_hour, 4),
            "discount_rate": discount_rate,
            "spot_total": round(spot_total, 2),
            "discount_amount": round(discount_amount, 2),
            "reserved_total": round(reserved_total, 2),
            "credits_required": round(reserved_total, 2),
            "savings": round(discount_amount, 2),
        }

    def _calculate_discount_rate(self, duration_hours: float) -> int:
        """
        Calculate discount rate based on reservation duration.

        Args:
            duration_hours: Reservation duration in hours

        Returns:
            Discount percentage (10-20)
        """
        min_duration = 1  # 1 hour
        max_duration = 168  # 1 week

        if duration_hours <= min_duration:
            return DISCOUNT_MIN
        elif duration_hours >= max_duration:
            return DISCOUNT_MAX
        else:
            # Linear interpolation
            ratio = (duration_hours - min_duration) / (max_duration - min_duration)
            return int(DISCOUNT_MIN + ratio * (DISCOUNT_MAX - DISCOUNT_MIN))

    def get_user_credit_balance(self, user_id: str) -> float:
        """
        Get total available credit balance for a user.

        Only counts credits that are:
        - Status = AVAILABLE
        - Not expired
        - Amount > 0

        Args:
            user_id: User ID

        Returns:
            Total available credits
        """
        now = datetime.utcnow()

        total = self.db.query(func.sum(ReservationCredit.amount)).filter(
            ReservationCredit.user_id == user_id,
            ReservationCredit.status == CreditStatus.AVAILABLE,
            ReservationCredit.expires_at > now,
            ReservationCredit.amount > 0
        ).scalar()

        return float(total) if total else 0.0

    def has_sufficient_credits(
        self,
        user_id: str,
        required_credits: float
    ) -> bool:
        """
        Check if user has sufficient credits for a reservation.

        Args:
            user_id: User ID
            required_credits: Credits needed

        Returns:
            True if sufficient credits available
        """
        available = self.get_user_credit_balance(user_id)
        return available >= required_credits

    def deduct_credits(
        self,
        user_id: str,
        amount: float,
        reservation_id: int
    ) -> List[ReservationCredit]:
        """
        Deduct credits from user balance for a reservation.

        Uses FIFO (First In, First Out) based on expiration date.
        Credits are locked to the reservation (won't expire until reservation completes).

        Args:
            user_id: User ID
            amount: Amount to deduct
            reservation_id: Reservation ID to link credits to

        Returns:
            List of credit records that were modified

        Raises:
            InsufficientCreditsException: If not enough credits available
        """
        available = self.get_user_credit_balance(user_id)
        if available < amount:
            raise InsufficientCreditsException(required=amount, available=available)

        now = datetime.utcnow()
        remaining = amount
        modified_credits = []

        # Get available credits ordered by expiration (FIFO)
        credits = self.db.query(ReservationCredit).filter(
            ReservationCredit.user_id == user_id,
            ReservationCredit.status == CreditStatus.AVAILABLE,
            ReservationCredit.expires_at > now,
            ReservationCredit.amount > 0
        ).order_by(ReservationCredit.expires_at.asc()).all()

        for credit in credits:
            if remaining <= 0:
                break

            if credit.amount <= remaining:
                # Use entire credit
                deducted = credit.amount
                credit.amount = 0
                credit.lock_for_reservation(reservation_id)
            else:
                # Partial deduction - split the credit
                deducted = remaining
                credit.amount -= deducted

                # Create new credit record for the locked portion
                locked_credit = ReservationCredit(
                    user_id=user_id,
                    amount=0,
                    original_amount=deducted,
                    created_at=credit.created_at,
                    expires_at=credit.expires_at,
                    status=CreditStatus.LOCKED,
                    reservation_id=reservation_id,
                    transaction_type=CreditTransactionType.DEDUCTION,
                    parent_credit_id=credit.id,
                    description=f"Deduction for reservation {reservation_id}"
                )
                self.db.add(locked_credit)
                modified_credits.append(locked_credit)

            remaining -= deducted
            modified_credits.append(credit)
            credit.updated_at = now

        self.db.commit()

        logger.info(
            f"Deducted {amount:.2f} credits from user {user_id} "
            f"for reservation {reservation_id}"
        )

        return modified_credits

    def refund_credits(
        self,
        reservation: Reservation,
        partial: bool = False
    ) -> Optional[ReservationCredit]:
        """
        Refund credits for a cancelled or failed reservation.

        Args:
            reservation: Reservation to refund
            partial: If True, calculate partial refund based on usage

        Returns:
            New credit record for the refund, or None if no refund applicable
        """
        if partial and reservation.started_at:
            # Calculate partial refund based on unused time
            now = datetime.utcnow()
            scheduled_end = reservation.end_time.replace(tzinfo=None) if reservation.end_time else now
            actual_start = reservation.started_at.replace(tzinfo=None) if reservation.started_at else now

            total_duration = (scheduled_end - actual_start).total_seconds()
            used_duration = (now - actual_start).total_seconds()

            if total_duration > 0 and used_duration < total_duration:
                unused_ratio = (total_duration - used_duration) / total_duration
                refund_amount = reservation.credits_used * unused_ratio
            else:
                refund_amount = 0
        else:
            # Full refund
            refund_amount = reservation.credits_used

        if refund_amount <= 0:
            return None

        # Create refund credit
        refund_credit = ReservationCredit.create_refund(
            user_id=reservation.user_id,
            amount=refund_amount,
            reservation_id=reservation.id
        )

        reservation.credits_refunded = refund_amount

        self.db.add(refund_credit)
        self.db.commit()

        logger.info(
            f"Refunded {refund_amount:.2f} credits to user {reservation.user_id} "
            f"for reservation {reservation.id}"
        )

        return refund_credit

    def create_reservation(
        self,
        user_id: str,
        gpu_type: str,
        start_time: datetime,
        end_time: datetime,
        gpu_count: int = 1
    ) -> Reservation:
        """
        Create a new GPU reservation.

        Args:
            user_id: User making the reservation
            gpu_type: GPU model to reserve
            start_time: Reservation start time (UTC)
            end_time: Reservation end time (UTC)
            gpu_count: Number of GPUs to reserve

        Returns:
            Created reservation

        Raises:
            ValidationException: If validation fails
            ReservationConflictException: If time slot not available
            InsufficientCreditsException: If not enough credits
        """
        logger.info(f"Creating reservation for user {user_id}: {gpu_type} from {start_time} to {end_time}")

        # Validate reservation
        validation = self.validate_reservation(
            user_id=user_id,
            gpu_type=gpu_type,
            start_time=start_time,
            end_time=end_time,
            gpu_count=gpu_count
        )

        if not validation["valid"]:
            raise ValidationException(
                message="Reservation validation failed",
                details={"errors": validation["errors"]}
            )

        pricing = validation["pricing"]

        # Create reservation record
        reservation = Reservation(
            user_id=user_id,
            gpu_type=gpu_type,
            gpu_count=gpu_count,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.PENDING,
            credits_used=pricing["credits_required"],
            discount_rate=pricing["discount_rate"],
            spot_price_per_hour=pricing["spot_price_per_hour"],
            reserved_price_per_hour=pricing["reserved_price_per_hour"],
        )

        self.db.add(reservation)
        self.db.flush()  # Get reservation ID before deducting credits

        # Deduct credits
        self.deduct_credits(
            user_id=user_id,
            amount=pricing["credits_required"],
            reservation_id=reservation.id
        )

        self.db.commit()

        logger.info(f"Created reservation {reservation.id} for user {user_id}")

        return reservation

    def get_reservation(self, reservation_id: int) -> Reservation:
        """
        Get a reservation by ID.

        Args:
            reservation_id: Reservation ID

        Returns:
            Reservation record

        Raises:
            NotFoundException: If reservation not found
        """
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise NotFoundException(f"Reservation {reservation_id} not found")

        return reservation

    def get_user_reservations(
        self,
        user_id: str,
        status: Optional[ReservationStatus] = None,
        include_past: bool = False
    ) -> List[Reservation]:
        """
        Get all reservations for a user.

        Args:
            user_id: User ID
            status: Filter by status (optional)
            include_past: Include completed/cancelled reservations

        Returns:
            List of reservations
        """
        query = self.db.query(Reservation).filter(
            Reservation.user_id == user_id
        )

        if status:
            query = query.filter(Reservation.status == status)
        elif not include_past:
            query = query.filter(
                Reservation.status.in_([
                    ReservationStatus.PENDING,
                    ReservationStatus.ACTIVE
                ])
            )

        return query.order_by(Reservation.start_time.asc()).all()

    def cancel_reservation(
        self,
        reservation_id: int,
        reason: Optional[str] = None
    ) -> Tuple[Reservation, Optional[ReservationCredit]]:
        """
        Cancel a reservation and refund unused credits.

        Args:
            reservation_id: Reservation ID
            reason: Cancellation reason (optional)

        Returns:
            Tuple of (updated reservation, refund credit if applicable)

        Raises:
            NotFoundException: If reservation not found
            ValidationException: If reservation cannot be cancelled
        """
        reservation = self.get_reservation(reservation_id)

        if not reservation.is_cancellable:
            raise ValidationException(
                message=f"Reservation {reservation_id} cannot be cancelled",
                details={"status": reservation.status.value if reservation.status else None}
            )

        # Determine if partial or full refund
        is_partial = reservation.status == ReservationStatus.ACTIVE

        # Process refund
        refund_credit = self.refund_credits(reservation, partial=is_partial)

        # Update reservation status
        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelled_at = datetime.utcnow()
        reservation.cancellation_reason = reason

        # Release any locked credits back to available
        locked_credits = self.db.query(ReservationCredit).filter(
            ReservationCredit.reservation_id == reservation_id,
            ReservationCredit.status == CreditStatus.LOCKED
        ).all()

        for credit in locked_credits:
            credit.status = CreditStatus.REFUNDED
            credit.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info(f"Cancelled reservation {reservation_id}")

        return reservation, refund_credit

    def activate_reservation(self, reservation_id: int, instance_id: str, provider: str) -> Reservation:
        """
        Activate a pending reservation (when GPU is allocated).

        Args:
            reservation_id: Reservation ID
            instance_id: Allocated instance ID
            provider: GPU provider (vast, tensordock, etc)

        Returns:
            Updated reservation

        Raises:
            NotFoundException: If reservation not found
            ValidationException: If reservation cannot be activated
        """
        reservation = self.get_reservation(reservation_id)

        if reservation.status != ReservationStatus.PENDING:
            raise ValidationException(
                message=f"Reservation {reservation_id} cannot be activated",
                details={"status": reservation.status.value if reservation.status else None}
            )

        reservation.status = ReservationStatus.ACTIVE
        reservation.instance_id = instance_id
        reservation.provider = provider
        reservation.started_at = datetime.utcnow()

        # Mark locked credits as used
        locked_credits = self.db.query(ReservationCredit).filter(
            ReservationCredit.reservation_id == reservation_id,
            ReservationCredit.status == CreditStatus.LOCKED
        ).all()

        for credit in locked_credits:
            credit.mark_as_used()

        self.db.commit()

        logger.info(
            f"Activated reservation {reservation_id} with instance {instance_id}"
        )

        return reservation

    def complete_reservation(self, reservation_id: int) -> Reservation:
        """
        Mark a reservation as completed.

        Args:
            reservation_id: Reservation ID

        Returns:
            Updated reservation
        """
        reservation = self.get_reservation(reservation_id)

        if reservation.status != ReservationStatus.ACTIVE:
            raise ValidationException(
                message=f"Reservation {reservation_id} is not active",
                details={"status": reservation.status.value if reservation.status else None}
            )

        reservation.status = ReservationStatus.COMPLETED
        reservation.completed_at = datetime.utcnow()

        self.db.commit()

        logger.info(f"Completed reservation {reservation_id}")

        return reservation

    def fail_reservation(
        self,
        reservation_id: int,
        reason: str
    ) -> Tuple[Reservation, Optional[ReservationCredit]]:
        """
        Mark a reservation as failed and issue full refund.

        Args:
            reservation_id: Reservation ID
            reason: Failure reason

        Returns:
            Tuple of (updated reservation, refund credit)
        """
        reservation = self.get_reservation(reservation_id)

        # Issue full refund
        refund_credit = self.refund_credits(reservation, partial=False)

        reservation.status = ReservationStatus.FAILED
        reservation.failure_reason = reason

        # Release locked credits
        locked_credits = self.db.query(ReservationCredit).filter(
            ReservationCredit.reservation_id == reservation_id,
            ReservationCredit.status == CreditStatus.LOCKED
        ).all()

        for credit in locked_credits:
            credit.status = CreditStatus.REFUNDED
            credit.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info(f"Failed reservation {reservation_id}: {reason}")

        return reservation, refund_credit

    def get_upcoming_reservations(
        self,
        minutes_ahead: int = 15
    ) -> List[Reservation]:
        """
        Get reservations that should start soon.

        Used by scheduler to allocate GPUs before reservation start time.

        Args:
            minutes_ahead: How many minutes ahead to look

        Returns:
            List of pending reservations starting soon
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(minutes=minutes_ahead)

        return self.db.query(Reservation).filter(
            Reservation.status == ReservationStatus.PENDING,
            Reservation.start_time <= cutoff,
            Reservation.start_time > now
        ).order_by(Reservation.start_time.asc()).all()

    def expire_credits(self) -> int:
        """
        Expire credits that have passed their expiration date.

        Only expires credits with status AVAILABLE.
        Locked credits (linked to active reservations) are not expired.

        Returns:
            Number of credits expired
        """
        now = datetime.utcnow()

        # Find expired credits
        expired_credits = self.db.query(ReservationCredit).filter(
            ReservationCredit.status == CreditStatus.AVAILABLE,
            ReservationCredit.expires_at <= now,
            ReservationCredit.amount > 0
        ).all()

        count = 0
        for credit in expired_credits:
            credit.mark_as_expired()
            count += 1

        if count > 0:
            self.db.commit()
            logger.info(f"Expired {count} credit records")

        return count

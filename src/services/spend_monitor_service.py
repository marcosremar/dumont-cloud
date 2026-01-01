"""
Spend Threshold Monitoring Service

Monitors user spending to trigger referrer rewards when referred users
reach the $50 spend threshold. The referrer receives $25 credit.

This service:
- Tracks spending for referred users
- Detects when $50 threshold is crossed
- Grants $25 reward to referrer (idempotent)
- Handles race conditions with database locks
- Can run as a background monitoring agent
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
from sqlalchemy.exc import OperationalError

from src.models.referral import (
    Referral, ReferralCode, CreditTransaction,
    ReferralStatus, TransactionType
)
from src.services.credit_service import CreditService

logger = logging.getLogger(__name__)


# Configuration constants (can be moved to config)
SPEND_THRESHOLD = 50.0  # $50 spend threshold to trigger referrer reward
REFERRER_REWARD = 25.0  # $25 reward for referrer


class SpendMonitorService:
    """
    Service to monitor user spending and trigger referrer rewards.

    Tracks spending for referred users and automatically grants
    the $25 referrer reward when the $50 threshold is reached.
    """

    def __init__(self, db: Session):
        """
        Initialize the spend monitor service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.credit_service = CreditService(db)

    def record_spend(
        self,
        user_id: str,
        amount: float,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None
    ) -> Dict:
        """
        Record a spend event for a user and check if threshold is reached.

        This method:
        1. Updates the referred user's total spend
        2. Checks if the $50 threshold is crossed
        3. Grants $25 reward to referrer if threshold reached (idempotent)

        Args:
            user_id: ID of the user who spent money
            amount: Amount spent (must be positive)
            reference_id: Optional external reference ID (e.g., billing_id)
            reference_type: Optional reference type (e.g., "billing", "usage")

        Returns:
            Dict with status and details:
            - is_referred: True if user was referred
            - previous_spend: Total spend before this transaction
            - new_spend: Total spend after this transaction
            - threshold_reached: True if threshold was just crossed
            - referrer_rewarded: True if referrer was rewarded
            - reward_transaction_id: ID of reward transaction (if rewarded)
        """
        if amount <= 0:
            logger.warning(f"Invalid spend amount for user {user_id}: {amount}")
            return {
                "success": False,
                "error": "Amount must be positive",
                "is_referred": False
            }

        # Find active referral for this user
        referral = self._get_active_referral(user_id)

        if not referral:
            # User was not referred, nothing to track
            return {
                "success": True,
                "is_referred": False,
                "previous_spend": 0.0,
                "new_spend": 0.0,
                "threshold_reached": False,
                "referrer_rewarded": False
            }

        # Check if reward was already granted (idempotency check)
        if referral.reward_granted:
            return {
                "success": True,
                "is_referred": True,
                "previous_spend": referral.referred_total_spend,
                "new_spend": referral.referred_total_spend,
                "threshold_reached": True,
                "referrer_rewarded": False,
                "message": "Reward already granted for this referral"
            }

        # Use database lock to prevent race conditions
        try:
            result = self._update_spend_with_lock(referral, amount)
            return result
        except OperationalError as e:
            logger.error(f"Database lock error for user {user_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": "Concurrent update detected, please retry",
                "is_referred": True
            }

    def _get_active_referral(self, user_id: str) -> Optional[Referral]:
        """
        Get active referral for a user (if any).

        Args:
            user_id: ID of the referred user

        Returns:
            Referral object or None
        """
        return self.db.query(Referral).filter(
            Referral.referred_id == user_id,
            Referral.status.in_([
                ReferralStatus.PENDING.value,
                ReferralStatus.ACTIVE.value
            ])
        ).first()

    def _update_spend_with_lock(self, referral: Referral, amount: float) -> Dict:
        """
        Update spend with database lock to prevent race conditions.

        Uses SELECT FOR UPDATE to lock the referral row during update.

        Args:
            referral: Referral object to update
            amount: Amount to add to total spend

        Returns:
            Dict with update result
        """
        # Lock the referral row for update (prevents concurrent modifications)
        locked_referral = self.db.query(Referral).filter(
            Referral.id == referral.id
        ).with_for_update().first()

        if not locked_referral:
            return {
                "success": False,
                "error": "Referral not found",
                "is_referred": True
            }

        # Re-check if reward was granted (in case of race condition)
        if locked_referral.reward_granted:
            return {
                "success": True,
                "is_referred": True,
                "previous_spend": locked_referral.referred_total_spend,
                "new_spend": locked_referral.referred_total_spend,
                "threshold_reached": True,
                "referrer_rewarded": False,
                "message": "Reward already granted for this referral"
            }

        # Calculate new spend
        previous_spend = locked_referral.referred_total_spend
        new_spend = round(previous_spend + amount, 2)
        was_below_threshold = previous_spend < locked_referral.spend_threshold
        is_now_above_threshold = new_spend >= locked_referral.spend_threshold

        # Update spend
        locked_referral.referred_total_spend = new_spend
        locked_referral.updated_at = datetime.utcnow()

        # Check if threshold was just crossed
        threshold_just_crossed = was_below_threshold and is_now_above_threshold

        result = {
            "success": True,
            "is_referred": True,
            "previous_spend": previous_spend,
            "new_spend": new_spend,
            "threshold": locked_referral.spend_threshold,
            "threshold_reached": is_now_above_threshold,
            "threshold_just_crossed": threshold_just_crossed,
            "referrer_rewarded": False,
            "referrer_id": locked_referral.referrer_id,
            "referred_id": locked_referral.referred_id
        }

        # Grant reward if threshold just crossed
        if threshold_just_crossed:
            reward_result = self._grant_referrer_reward(locked_referral)
            result["referrer_rewarded"] = reward_result.get("success", False)
            result["reward_transaction_id"] = reward_result.get("transaction_id")
            if reward_result.get("error"):
                result["reward_error"] = reward_result["error"]

            logger.info(
                f"Threshold crossed for referral {locked_referral.id}: "
                f"user {locked_referral.referred_id} spent ${new_spend}, "
                f"referrer {locked_referral.referrer_id} rewarded: {result['referrer_rewarded']}"
            )

        self.db.commit()
        return result

    def _grant_referrer_reward(self, referral: Referral) -> Dict:
        """
        Grant $25 reward to referrer.

        This method is idempotent - if reward was already granted,
        it returns success without creating duplicate transaction.

        Args:
            referral: Referral object

        Returns:
            Dict with result: success, transaction_id, or error
        """
        # Double-check reward hasn't been granted
        if referral.reward_granted:
            return {
                "success": True,
                "message": "Reward already granted"
            }

        # Check for fraud/suspicious activity
        if referral.is_suspicious or referral.status == ReferralStatus.FRAUD.value:
            logger.warning(
                f"Blocked reward for suspicious referral {referral.id}: "
                f"{referral.fraud_reason or 'marked suspicious'}"
            )
            return {
                "success": False,
                "error": "Referral blocked due to suspicious activity"
            }

        try:
            # Grant the reward using CreditService
            transaction = self.credit_service.grant_referrer_reward(referral)

            if transaction:
                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "amount": transaction.amount
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create reward transaction"
                }

        except Exception as e:
            logger.error(f"Error granting referrer reward: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def check_threshold_for_user(self, user_id: str) -> Dict:
        """
        Check if a referred user has reached the spend threshold.

        This does NOT update spend - only checks current status.

        Args:
            user_id: ID of the user to check

        Returns:
            Dict with threshold status
        """
        referral = self._get_active_referral(user_id)

        if not referral:
            # Check if there's a completed referral
            completed_referral = self.db.query(Referral).filter(
                Referral.referred_id == user_id,
                Referral.status == ReferralStatus.COMPLETED.value
            ).first()

            if completed_referral:
                return {
                    "is_referred": True,
                    "status": "completed",
                    "total_spend": completed_referral.referred_total_spend,
                    "threshold": completed_referral.spend_threshold,
                    "threshold_reached": True,
                    "reward_granted": completed_referral.reward_granted,
                    "reward_granted_at": (
                        completed_referral.reward_granted_at.isoformat()
                        if completed_referral.reward_granted_at else None
                    )
                }

            return {
                "is_referred": False,
                "status": None
            }

        return {
            "is_referred": True,
            "status": referral.status,
            "total_spend": referral.referred_total_spend,
            "threshold": referral.spend_threshold,
            "progress": referral.spend_progress,
            "threshold_reached": referral.is_threshold_reached,
            "reward_granted": referral.reward_granted,
            "amount_remaining": max(0, referral.spend_threshold - referral.referred_total_spend)
        }

    def get_pending_rewards(self, limit: int = 100) -> List[Dict]:
        """
        Get all referrals that have reached threshold but haven't been rewarded.

        This is useful for background processing or manual review.

        Args:
            limit: Maximum number of results

        Returns:
            List of pending reward details
        """
        pending = self.db.query(Referral).filter(
            Referral.referred_total_spend >= Referral.spend_threshold,
            Referral.reward_granted == False,
            Referral.is_suspicious == False,
            Referral.status.in_([
                ReferralStatus.PENDING.value,
                ReferralStatus.ACTIVE.value
            ])
        ).limit(limit).all()

        return [
            {
                "referral_id": r.id,
                "referrer_id": r.referrer_id,
                "referred_id": r.referred_id,
                "total_spend": r.referred_total_spend,
                "threshold": r.spend_threshold,
                "reward_amount": r.referrer_reward_amount,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in pending
        ]

    def process_pending_rewards(self) -> Dict:
        """
        Process all pending rewards that should have been granted.

        This is a recovery mechanism for any rewards that weren't
        granted due to errors or timing issues.

        Returns:
            Dict with processing results
        """
        pending = self.get_pending_rewards()

        processed = 0
        failed = 0
        errors = []

        for item in pending:
            referral = self.db.query(Referral).filter(
                Referral.id == item["referral_id"]
            ).with_for_update().first()

            if not referral or referral.reward_granted:
                continue

            result = self._grant_referrer_reward(referral)

            if result.get("success"):
                processed += 1
                self.db.commit()
            else:
                failed += 1
                errors.append({
                    "referral_id": item["referral_id"],
                    "error": result.get("error")
                })
                self.db.rollback()

        return {
            "processed": processed,
            "failed": failed,
            "errors": errors if errors else None
        }

    def get_referrer_stats(self, referrer_id: str) -> Dict:
        """
        Get spend monitoring statistics for a referrer.

        Args:
            referrer_id: ID of the referrer

        Returns:
            Dict with referrer statistics
        """
        # Get all referrals for this referrer
        referrals = self.db.query(Referral).filter(
            Referral.referrer_id == referrer_id
        ).all()

        if not referrals:
            return {
                "total_referrals": 0,
                "active_referrals": 0,
                "completed_referrals": 0,
                "total_referred_spend": 0.0,
                "rewards_granted": 0,
                "total_rewards": 0.0,
                "pending_rewards": 0,
                "potential_rewards": 0.0
            }

        active = [r for r in referrals if r.status in [
            ReferralStatus.PENDING.value, ReferralStatus.ACTIVE.value
        ]]
        completed = [r for r in referrals if r.status == ReferralStatus.COMPLETED.value]
        pending_reward = [r for r in active if r.is_threshold_reached and not r.reward_granted]

        return {
            "total_referrals": len(referrals),
            "active_referrals": len(active),
            "completed_referrals": len(completed),
            "total_referred_spend": sum(r.referred_total_spend for r in referrals),
            "rewards_granted": len([r for r in referrals if r.reward_granted]),
            "total_rewards": sum(
                r.referrer_reward_amount for r in referrals if r.reward_granted
            ),
            "pending_rewards": len(pending_reward),
            "potential_rewards": sum(
                r.referrer_reward_amount for r in active if not r.reward_granted
            ),
            "referrals": [
                {
                    "referred_id": r.referred_id,
                    "status": r.status,
                    "total_spend": r.referred_total_spend,
                    "progress": r.spend_progress,
                    "reward_granted": r.reward_granted
                }
                for r in referrals
            ]
        }

    def get_spend_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Get top referred users by spend amount (not yet converted).

        Useful for identifying users close to reaching threshold.

        Args:
            limit: Maximum number of results

        Returns:
            List of top spenders
        """
        top_spenders = self.db.query(Referral).filter(
            Referral.reward_granted == False,
            Referral.is_suspicious == False,
            Referral.status.in_([
                ReferralStatus.PENDING.value,
                ReferralStatus.ACTIVE.value
            ])
        ).order_by(Referral.referred_total_spend.desc()).limit(limit).all()

        return [
            {
                "referral_id": r.id,
                "referred_id": r.referred_id,
                "referrer_id": r.referrer_id,
                "total_spend": r.referred_total_spend,
                "threshold": r.spend_threshold,
                "progress": r.spend_progress,
                "amount_remaining": max(0, r.spend_threshold - r.referred_total_spend)
            }
            for r in top_spenders
        ]

    def get_recent_conversions(self, limit: int = 10) -> List[Dict]:
        """
        Get recent threshold crossings (conversions).

        Args:
            limit: Maximum number of results

        Returns:
            List of recent conversions
        """
        recent = self.db.query(Referral).filter(
            Referral.threshold_reached_at.isnot(None),
            Referral.reward_granted == True
        ).order_by(Referral.threshold_reached_at.desc()).limit(limit).all()

        return [
            {
                "referral_id": r.id,
                "referred_id": r.referred_id,
                "referrer_id": r.referrer_id,
                "total_spend": r.referred_total_spend,
                "reward_amount": r.referrer_reward_amount,
                "threshold_reached_at": (
                    r.threshold_reached_at.isoformat() if r.threshold_reached_at else None
                ),
                "reward_granted_at": (
                    r.reward_granted_at.isoformat() if r.reward_granted_at else None
                )
            }
            for r in recent
        ]


class SpendMonitorAgent:
    """
    Background agent for monitoring spend thresholds.

    This agent periodically checks for pending rewards and processes them.
    Can be run as a background task or scheduled job.

    Follows pattern from PriceMonitorAgent.
    """

    def __init__(self, interval_minutes: int = 5):
        """
        Initialize the spend monitor agent.

        Args:
            interval_minutes: Interval between monitoring cycles
        """
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.last_run = None
        self.stats = {
            "cycles": 0,
            "rewards_processed": 0,
            "errors": 0
        }

    def start(self):
        """Start the monitoring agent."""
        self.running = True
        logger.info(f"Starting SpendMonitorAgent with {self.interval_seconds / 60} minute interval")

    def stop(self):
        """Stop the monitoring agent."""
        self.running = False
        logger.info("Stopping SpendMonitorAgent")

    def run_cycle(self, db: Session) -> Dict:
        """
        Run a single monitoring cycle.

        Args:
            db: Database session

        Returns:
            Dict with cycle results
        """
        logger.info(f"Running spend monitor cycle at {datetime.utcnow()}")
        self.stats["cycles"] += 1

        service = SpendMonitorService(db)

        # Process any pending rewards
        result = service.process_pending_rewards()

        self.stats["rewards_processed"] += result["processed"]
        if result["failed"] > 0:
            self.stats["errors"] += result["failed"]

        self.last_run = datetime.utcnow()

        logger.info(
            f"Spend monitor cycle complete: "
            f"processed={result['processed']}, failed={result['failed']}"
        )

        return result

    def get_stats(self) -> Dict:
        """Get agent statistics."""
        return {
            "running": self.running,
            "interval_minutes": self.interval_seconds / 60,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "total_cycles": self.stats["cycles"],
            "total_rewards_processed": self.stats["rewards_processed"],
            "total_errors": self.stats["errors"]
        }

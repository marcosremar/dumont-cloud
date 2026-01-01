"""
NPS Service - Domain Service (Business Logic)
Handles NPS survey triggers, rate limiting, and response management
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from ...models.nps import NPSResponse, NPSSurveyConfig, NPSUserInteraction
from ...core.exceptions import ValidationException, NotFoundException

logger = logging.getLogger(__name__)

# Valid trigger types
VALID_TRIGGER_TYPES = ['first_deployment', 'monthly', 'issue_resolution']

# Default rate limit in days (if no config found)
DEFAULT_FREQUENCY_DAYS = 30


class NPSService:
    """
    Domain service for NPS survey management.
    Handles survey triggers, rate limiting, and response collection (Single Responsibility Principle).
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize NPS service

        Args:
            session: SQLAlchemy database session (optional, can be injected per-method)
        """
        self._session = session

    def _get_session(self, session: Optional[Session] = None) -> Session:
        """Get the session to use, preferring the passed one over the instance one."""
        if session is not None:
            return session
        if self._session is not None:
            return self._session
        raise ValidationException("Database session is required")

    def should_show_survey(
        self,
        user_id: str,
        trigger_type: str,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Check if NPS survey should be shown to a user

        Rate limiting logic:
        - Check if trigger type is enabled
        - Check if user has submitted/dismissed within frequency window
        - Check if user is currently in a critical operation

        Args:
            user_id: User identifier
            trigger_type: Type of trigger (first_deployment, monthly, issue_resolution)
            session: Database session

        Returns:
            Dict with:
                - should_show: bool
                - reason: str
                - trigger_type: str (if should_show is True)
                - survey_config: dict (if available)

        Raises:
            ValidationException: If trigger_type is invalid
        """
        db = self._get_session(session)

        if trigger_type not in VALID_TRIGGER_TYPES:
            raise ValidationException(f"Invalid trigger_type: {trigger_type}")

        # Get survey config for this trigger type
        config = db.query(NPSSurveyConfig).filter(
            NPSSurveyConfig.trigger_type == trigger_type
        ).first()

        # Check if trigger is enabled
        if config and not config.enabled:
            logger.debug(f"Survey trigger '{trigger_type}' is disabled")
            return {
                'should_show': False,
                'reason': 'Survey trigger is disabled',
                'trigger_type': None,
                'survey_config': None
            }

        # Get frequency from config or use default
        frequency_days = config.frequency_days if config else DEFAULT_FREQUENCY_DAYS
        cutoff_date = datetime.utcnow() - timedelta(days=frequency_days)

        # Check for recent interactions (submitted or dismissed)
        recent_interaction = db.query(NPSUserInteraction).filter(
            and_(
                NPSUserInteraction.user_id == user_id,
                NPSUserInteraction.interaction_type.in_(['submitted', 'dismissed']),
                NPSUserInteraction.created_at >= cutoff_date
            )
        ).first()

        if recent_interaction:
            days_until_eligible = (
                recent_interaction.created_at + timedelta(days=frequency_days) - datetime.utcnow()
            ).days
            logger.debug(
                f"User {user_id} has recent interaction ({recent_interaction.interaction_type}), "
                f"eligible again in {days_until_eligible} days"
            )
            return {
                'should_show': False,
                'reason': f'User has recent {recent_interaction.interaction_type}. Eligible again in {max(1, days_until_eligible)} days',
                'trigger_type': None,
                'survey_config': None
            }

        logger.info(f"Survey should be shown to user {user_id} for trigger '{trigger_type}'")
        return {
            'should_show': True,
            'reason': 'User is eligible for survey',
            'trigger_type': trigger_type,
            'survey_config': config.to_dict() if config else None
        }

    def submit_response(
        self,
        user_id: str,
        score: int,
        trigger_type: str,
        comment: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Submit an NPS response

        Args:
            user_id: User identifier
            score: NPS score (0-10)
            trigger_type: Type of trigger
            comment: Optional feedback comment
            session: Database session

        Returns:
            Dict with:
                - id: int (response ID)
                - category: str (detractor/passive/promoter)
                - success: bool
                - message: str

        Raises:
            ValidationException: If input is invalid
        """
        db = self._get_session(session)

        # Validate score
        if not isinstance(score, int) or score < 0 or score > 10:
            raise ValidationException("Score must be an integer between 0 and 10")

        # Validate trigger type
        if trigger_type not in VALID_TRIGGER_TYPES:
            raise ValidationException(f"Invalid trigger_type: {trigger_type}")

        # Calculate category
        category = NPSResponse.get_category(score)
        needs_followup = category == 'detractor'

        # Create response
        nps_response = NPSResponse(
            user_id=user_id,
            score=score,
            comment=comment,
            trigger_type=trigger_type,
            category=category,
            needs_followup=needs_followup,
            followup_completed=False,
            created_at=datetime.utcnow()
        )
        db.add(nps_response)

        # Record interaction for rate limiting
        interaction = NPSUserInteraction(
            user_id=user_id,
            interaction_type='submitted',
            trigger_type=trigger_type,
            response_id=None,  # Will update after flush
            created_at=datetime.utcnow()
        )
        db.add(interaction)

        # Flush to get the response ID
        db.flush()

        # Update interaction with response_id
        interaction.response_id = nps_response.id

        db.commit()

        logger.info(
            f"NPS response submitted: user={user_id}, score={score}, "
            f"category={category}, trigger={trigger_type}"
        )

        return {
            'id': nps_response.id,
            'category': category,
            'success': True,
            'message': 'Thank you for your feedback!'
        }

    def record_dismissal(
        self,
        user_id: str,
        trigger_type: str,
        reason: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Record a survey dismissal for rate limiting

        Args:
            user_id: User identifier
            trigger_type: Type of trigger
            reason: Optional dismissal reason
            session: Database session

        Returns:
            Dict with success status

        Raises:
            ValidationException: If trigger_type is invalid
        """
        db = self._get_session(session)

        if trigger_type not in VALID_TRIGGER_TYPES:
            raise ValidationException(f"Invalid trigger_type: {trigger_type}")

        # Record dismissal interaction
        interaction = NPSUserInteraction(
            user_id=user_id,
            interaction_type='dismissed',
            trigger_type=trigger_type,
            interaction_metadata=reason,
            created_at=datetime.utcnow()
        )
        db.add(interaction)
        db.commit()

        logger.info(f"NPS survey dismissed: user={user_id}, trigger={trigger_type}")

        return {
            'success': True,
            'message': 'Dismissal recorded'
        }

    def get_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get NPS trends for admin dashboard

        Args:
            start_date: Start date for trends (default: 30 days ago)
            end_date: End date for trends (default: now)
            session: Database session

        Returns:
            Dict with:
                - scores: List of data points over time
                - categories: Category breakdown
                - current_nps: Current NPS score (-100 to 100)
                - total_responses: Total response count
                - average_score: Average score (0-10)
        """
        db = self._get_session(session)

        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Get all responses in date range
        responses = db.query(NPSResponse).filter(
            and_(
                NPSResponse.created_at >= start_date,
                NPSResponse.created_at <= end_date
            )
        ).order_by(NPSResponse.created_at).all()

        # Calculate category breakdown
        detractors = sum(1 for r in responses if r.category == 'detractor')
        passives = sum(1 for r in responses if r.category == 'passive')
        promoters = sum(1 for r in responses if r.category == 'promoter')
        total = len(responses)

        # Calculate percentages
        if total > 0:
            detractors_pct = (detractors / total) * 100
            passives_pct = (passives / total) * 100
            promoters_pct = (promoters / total) * 100
            # NPS = % Promoters - % Detractors
            current_nps = promoters_pct - detractors_pct
            average_score = sum(r.score for r in responses) / total
        else:
            detractors_pct = passives_pct = promoters_pct = 0
            current_nps = 0
            average_score = 0

        # Group by date for trend chart
        daily_data: Dict[str, Dict[str, Any]] = {}
        for response in responses:
            date_key = response.created_at.strftime('%Y-%m-%d')
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'scores': [],
                    'detractors': 0,
                    'passives': 0,
                    'promoters': 0
                }
            daily_data[date_key]['scores'].append(response.score)
            daily_data[date_key][response.category + 's'] += 1

        # Convert to list of data points
        scores = []
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            day_total = data['detractors'] + data['passives'] + data['promoters']
            day_promoters_pct = (data['promoters'] / day_total) * 100 if day_total > 0 else 0
            day_detractors_pct = (data['detractors'] / day_total) * 100 if day_total > 0 else 0

            scores.append({
                'date': date_str,
                'nps_score': day_promoters_pct - day_detractors_pct,
                'total_responses': day_total,
                'detractors': data['detractors'],
                'passives': data['passives'],
                'promoters': data['promoters']
            })

        return {
            'scores': scores,
            'categories': {
                'detractors': detractors,
                'passives': passives,
                'promoters': promoters,
                'detractors_percentage': round(detractors_pct, 2),
                'passives_percentage': round(passives_pct, 2),
                'promoters_percentage': round(promoters_pct, 2)
            },
            'current_nps': round(current_nps, 2),
            'total_responses': total,
            'average_score': round(average_score, 2),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }

    def get_detractors(
        self,
        pending_only: bool = False,
        limit: int = 100,
        offset: int = 0,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get list of detractor responses for follow-up

        Args:
            pending_only: Only return detractors needing follow-up
            limit: Maximum number of results
            offset: Results offset for pagination
            session: Database session

        Returns:
            Dict with:
                - detractors: List of detractor responses
                - count: Total count
                - pending_followup: Count needing follow-up
        """
        db = self._get_session(session)

        # Base query for detractors
        query = db.query(NPSResponse).filter(
            NPSResponse.category == 'detractor'
        )

        if pending_only:
            query = query.filter(
                and_(
                    NPSResponse.needs_followup == True,
                    NPSResponse.followup_completed == False
                )
            )

        # Get total count
        total_count = query.count()

        # Get pending count
        pending_count = db.query(NPSResponse).filter(
            and_(
                NPSResponse.category == 'detractor',
                NPSResponse.needs_followup == True,
                NPSResponse.followup_completed == False
            )
        ).count()

        # Get paginated results
        detractors = query.order_by(
            desc(NPSResponse.created_at)
        ).offset(offset).limit(limit).all()

        return {
            'detractors': [d.to_dict() for d in detractors],
            'count': total_count,
            'pending_followup': pending_count
        }

    def update_followup(
        self,
        response_id: int,
        followup_completed: bool,
        followup_notes: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Update follow-up status for a detractor response

        Args:
            response_id: NPS response ID
            followup_completed: Whether follow-up is completed
            followup_notes: Notes from the follow-up
            session: Database session

        Returns:
            Dict with success status

        Raises:
            NotFoundException: If response not found
        """
        db = self._get_session(session)

        response = db.query(NPSResponse).filter(
            NPSResponse.id == response_id
        ).first()

        if not response:
            raise NotFoundException(f"NPS response {response_id} not found")

        response.followup_completed = followup_completed
        if followup_notes:
            response.followup_notes = followup_notes

        db.commit()

        logger.info(
            f"Follow-up updated for response {response_id}: "
            f"completed={followup_completed}"
        )

        return {
            'success': True,
            'id': response_id,
            'message': 'Follow-up status updated'
        }

    def get_survey_configs(
        self,
        session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all survey configurations

        Args:
            session: Database session

        Returns:
            List of survey config dictionaries
        """
        db = self._get_session(session)

        configs = db.query(NPSSurveyConfig).order_by(
            NPSSurveyConfig.trigger_type
        ).all()

        return [c.to_dict() for c in configs]

    def update_survey_config(
        self,
        trigger_type: str,
        enabled: Optional[bool] = None,
        frequency_days: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Update survey configuration for a trigger type

        Args:
            trigger_type: Type of trigger to update
            enabled: Whether to enable this trigger
            frequency_days: Minimum days between surveys
            title: Custom survey title
            description: Custom survey description
            session: Database session

        Returns:
            Updated config dict

        Raises:
            ValidationException: If trigger_type is invalid
            NotFoundException: If config not found
        """
        db = self._get_session(session)

        if trigger_type not in VALID_TRIGGER_TYPES:
            raise ValidationException(f"Invalid trigger_type: {trigger_type}")

        config = db.query(NPSSurveyConfig).filter(
            NPSSurveyConfig.trigger_type == trigger_type
        ).first()

        if not config:
            # Create new config
            config = NPSSurveyConfig(
                trigger_type=trigger_type,
                enabled=enabled if enabled is not None else True,
                frequency_days=frequency_days if frequency_days is not None else DEFAULT_FREQUENCY_DAYS,
                title=title,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(config)
        else:
            # Update existing config
            if enabled is not None:
                config.enabled = enabled
            if frequency_days is not None:
                config.frequency_days = frequency_days
            if title is not None:
                config.title = title
            if description is not None:
                config.description = description
            config.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Survey config updated for trigger '{trigger_type}'")

        return config.to_dict()

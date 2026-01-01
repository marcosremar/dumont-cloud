"""
Email Preferences Flask Blueprint

Flask blueprint for managing user email preferences (weekly/monthly reports).
Provides endpoints for getting, updating, and managing email subscriptions.
"""
import logging
from flask import Blueprint, jsonify, request, g, session
from functools import wraps

logger = logging.getLogger(__name__)

email_preferences_bp = Blueprint('email_preferences', __name__, url_prefix='/api/email-preferences')


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated


def get_db_session():
    """Get a database session"""
    from src.config.database import SessionLocal
    return SessionLocal()


@email_preferences_bp.route('', methods=['GET'])
@login_required
def get_email_preferences():
    """
    Get current user's email preferences

    Returns the user's email preference settings including frequency,
    unsubscribe status, and timezone configuration.
    """
    from src.models.email_preferences import EmailPreference

    user_email = session.get('user')
    db = get_db_session()

    try:
        # Find existing preferences for user
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create default preferences if none exist
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency="weekly",
                timezone="UTC",
                unsubscribed=False,
            )
            db.add(preference)
            db.commit()
            db.refresh(preference)
            logger.info(f"Created default email preferences for user: {user_email}")

        return jsonify({
            'id': preference.id,
            'user_id': preference.user_id,
            'email': preference.email,
            'frequency': preference.frequency,
            'unsubscribed': preference.unsubscribed,
            'timezone': preference.timezone,
            'created_at': preference.created_at.isoformat() if preference.created_at else None,
            'updated_at': preference.updated_at.isoformat() if preference.updated_at else None,
        })

    except Exception as e:
        logger.error(f"Error fetching email preferences for {user_email}: {e}")
        return jsonify({'error': f'Failed to fetch email preferences: {str(e)}'}), 500
    finally:
        db.close()


@email_preferences_bp.route('', methods=['PUT'])
@login_required
def update_email_preferences():
    """
    Update user's email preferences

    Allows updating email frequency (weekly/monthly/none) and timezone settings.
    Setting frequency to 'none' effectively disables email reports.
    """
    from src.models.email_preferences import EmailPreference

    user_email = session.get('user')
    data = request.get_json() or {}
    db = get_db_session()

    try:
        # Validate frequency if provided
        frequency = data.get('frequency')
        if frequency and frequency not in ['weekly', 'monthly', 'none']:
            return jsonify({'error': 'Invalid frequency. Must be weekly, monthly, or none'}), 400

        # Find existing preferences
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create new preferences with provided values
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency=frequency or "weekly",
                timezone=data.get('timezone', 'UTC'),
                unsubscribed=False,
            )
            db.add(preference)
            logger.info(f"Created email preferences for user: {user_email}")
        else:
            # Update existing preferences
            if frequency is not None:
                preference.frequency = frequency
                # If user explicitly sets frequency to something other than 'none',
                # clear the unsubscribed flag
                if frequency != "none":
                    preference.unsubscribed = False

            if 'timezone' in data and data['timezone'] is not None:
                preference.timezone = data['timezone']

            logger.info(f"Updated email preferences for user: {user_email}")

        db.commit()
        db.refresh(preference)

        return jsonify({
            'id': preference.id,
            'user_id': preference.user_id,
            'email': preference.email,
            'frequency': preference.frequency,
            'unsubscribed': preference.unsubscribed,
            'timezone': preference.timezone,
            'created_at': preference.created_at.isoformat() if preference.created_at else None,
            'updated_at': preference.updated_at.isoformat() if preference.updated_at else None,
        })

    except Exception as e:
        logger.error(f"Error updating email preferences for {user_email}: {e}")
        db.rollback()
        return jsonify({'error': f'Failed to update email preferences: {str(e)}'}), 500
    finally:
        db.close()


@email_preferences_bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe_to_emails():
    """
    Re-subscribe to email reports

    If user was previously unsubscribed, this reactivates their email subscription.
    Sets frequency to 'weekly' by default if it was 'none'.
    """
    from src.models.email_preferences import EmailPreference

    user_email = session.get('user')
    db = get_db_session()

    try:
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create new preferences with weekly frequency
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency="weekly",
                timezone="UTC",
                unsubscribed=False,
            )
            db.add(preference)
            message = "Successfully subscribed to weekly email reports"
        else:
            # Reactivate subscription
            preference.unsubscribed = False
            if preference.frequency == "none":
                preference.frequency = "weekly"
            message = "Successfully re-subscribed to email reports"

        db.commit()
        logger.info(f"User {user_email} subscribed to email reports")

        return jsonify({'success': True, 'message': message})

    except Exception as e:
        logger.error(f"Error subscribing {user_email} to emails: {e}")
        db.rollback()
        return jsonify({'error': f'Failed to subscribe: {str(e)}'}), 500
    finally:
        db.close()


@email_preferences_bp.route('/test-email', methods=['POST'])
@login_required
def send_test_email():
    """
    Send a test email report

    Triggers sending of a test weekly report email to the authenticated user.
    Useful for previewing email content and verifying email delivery works.
    """
    from src.models.email_preferences import EmailPreference
    from datetime import datetime, timedelta

    user_email = session.get('user')
    db = get_db_session()

    try:
        from src.services.email_sender import send_weekly_report
        from src.services.email_analytics_aggregator import EmailAnalyticsAggregator
        from src.services.email_recommendations import generate_recommendations
        from src.services.email_composer import compose_weekly_report

        # Get user preferences
        preference = db.query(EmailPreference).filter(
            EmailPreference.user_id == user_email
        ).first()

        if not preference:
            # Create default preferences
            preference = EmailPreference(
                user_id=user_email,
                email=user_email,
                frequency="weekly",
                timezone="UTC",
                unsubscribed=False,
            )
            db.add(preference)
            db.commit()
            db.refresh(preference)

        # Aggregate usage data
        aggregator = EmailAnalyticsAggregator()
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=7)
        week_end = today - timedelta(days=1)

        metrics = aggregator.aggregate_user_usage(user_email, week_start, week_end, db)
        comparison = aggregator.calculate_week_over_week(user_email, week_start, db)

        # Generate recommendations
        recommendations = generate_recommendations(metrics)

        # Compose email
        email_content = compose_weekly_report(
            user_email=user_email,
            metrics=metrics,
            comparison=comparison,
            recommendations=recommendations,
            week_start=week_start,
            week_end=week_end,
        )

        # Send email
        result = send_weekly_report(
            to_email=user_email,
            subject=email_content.subject,
            html_body=email_content.html_body,
            user_id=user_email,
            week_start=week_start,
            week_end=week_end,
            db=db,
        )

        if result.success:
            return jsonify({
                'success': True,
                'message': f'Test email sent to {user_email}',
                'email_id': result.email_id,
            })
        else:
            return jsonify({'error': f'Failed to send test email: {result.error}'}), 500

    except ImportError as e:
        logger.warning(f"Email services not available: {e}")
        return jsonify({'error': 'Email service not configured. Please ensure RESEND_API_KEY is set.'}), 503
    except Exception as e:
        logger.error(f"Error sending test email for {user_email}: {e}")
        return jsonify({'error': f'Failed to send test email: {str(e)}'}), 500
    finally:
        db.close()

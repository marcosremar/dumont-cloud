#!/usr/bin/env python3
"""
Manual Test Script: Send Test Email

This script allows manual testing of the weekly email report system.
It can be run from the command line or imported into a Python console.

Usage:
    # From command line:
    python scripts/test_email_send.py --email user@example.com

    # From Python console:
    from scripts.test_email_send import send_test_email_to_user
    result = send_test_email_to_user("user@example.com")

    # Preview email without sending:
    from scripts.test_email_send import preview_email
    preview_email("user@example.com")

Environment Variables Required:
    - RESEND_API_KEY: API key for Resend email service
    - DATABASE_URL: PostgreSQL connection string

Verification Steps:
1. Trigger manual email send (this script)
2. Verify email received with all sections
3. Verify EmailDeliveryLog entry created
4. Check email rendering in Gmail/Outlook
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_mock_analytics_data(user_id: str) -> Dict:
    """
    Generate mock analytics data for testing.
    In production, this would come from aggregate_user_usage().
    """
    now = datetime.utcnow()
    return {
        'user_id': user_id,
        'current_week': {
            'week_start': now.replace(hour=0, minute=0, second=0).isoformat(),
            'week_end': now.isoformat(),
            'week_start_formatted': 'December 25',
            'week_end_formatted': 'December 31, 2024',
            'total_hours': 32.5,
            'total_cost_dumont': 65.00,
            'total_cost_aws': 142.50,
            'total_cost_gcp': 128.00,
            'total_cost_azure': 135.00,
            'savings_vs_aws': 77.50,
            'savings_vs_gcp': 63.00,
            'savings_vs_azure': 70.00,
            'savings_percentage_aws': 54.4,
            'auto_hibernate_savings': 18.75,
            'total_sessions': 8,
            'unique_gpus_used': 3,
            'is_first_week': False,
            'has_usage': True,
        },
        'previous_week': {
            'has_usage': True,
            'total_hours': 28.0,
            'total_cost_dumont': 52.00,
            'savings_vs_aws': 65.00,
        },
        'week_over_week': {
            'hours_change_percent': 16.1,
            'cost_change_percent': 25.0,
            'savings_change_percent': 19.2,
            'hours_trend': 'up',
            'cost_trend': 'up',
            'savings_trend': 'up',
            'hours_diff': 4.5,
            'cost_diff': 13.00,
            'savings_diff': 12.50,
            'has_previous_week': True,
        },
        'gpu_breakdown': [
            {
                'gpu_type': 'RTX 4090',
                'hours': 18.5,
                'cost_dumont': 42.00,
                'cost_aws': 92.50,
                'savings': 50.50,
                'sessions': 4,
            },
            {
                'gpu_type': 'RTX 4080',
                'hours': 10.0,
                'cost_dumont': 18.00,
                'cost_aws': 40.00,
                'savings': 22.00,
                'sessions': 3,
            },
            {
                'gpu_type': 'RTX 3080',
                'hours': 4.0,
                'cost_dumont': 5.00,
                'cost_aws': 10.00,
                'savings': 5.00,
                'sessions': 1,
            },
        ],
        'generated_at': now.isoformat(),
    }


def preview_email(
    user_email: str,
    user_name: Optional[str] = None,
    output_file: Optional[str] = None,
) -> Dict:
    """
    Generate and preview email without sending.

    Args:
        user_email: Email address to use for preview
        user_name: Optional display name
        output_file: Optional file path to save HTML preview

    Returns:
        Dict with email content details
    """
    from src.services.email_composer import compose_weekly_report
    from src.services.email_recommendations import generate_recommendations

    logger.info(f"Generating email preview for {user_email}")

    # Get mock analytics
    analytics_data = get_mock_analytics_data(user_email)

    # Generate recommendations
    recommendations = generate_recommendations(
        current_week=analytics_data.get('current_week', {}),
        previous_week=analytics_data.get('previous_week', {}),
        week_over_week=analytics_data.get('week_over_week', {}),
        gpu_breakdown=analytics_data.get('gpu_breakdown', [])
    )

    logger.info(f"Generated {len(recommendations)} recommendations")

    # Compose email
    email_content = compose_weekly_report(
        user_id=user_email,
        user_email=user_email,
        user_name=user_name,
        analytics_data=analytics_data,
        recommendations=recommendations,
    )

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write(email_content.html_body)
        logger.info(f"Email HTML saved to: {output_file}")

    result = {
        'success': True,
        'subject': email_content.subject,
        'html_length': len(email_content.html_body),
        'has_usage': email_content.has_usage,
        'is_first_week': email_content.is_first_week,
        'week_start': email_content.week_start.isoformat(),
        'week_end': email_content.week_end.isoformat(),
        'recommendations_count': len(recommendations),
    }

    logger.info(f"Preview generated: {result}")
    return result


def send_test_email_to_user(
    user_email: str,
    user_name: Optional[str] = None,
    use_real_data: bool = False,
) -> Dict:
    """
    Send a test email to the specified user.

    Args:
        user_email: Email address to send to
        user_name: Optional display name
        use_real_data: If True, tries to use real usage data from database

    Returns:
        Dict with send result details
    """
    from src.services.email_sender import send_email
    from src.services.email_composer import compose_weekly_report
    from src.services.email_recommendations import generate_recommendations

    logger.info(f"Preparing test email for {user_email}")

    # Check if Resend is configured
    if not os.getenv('RESEND_API_KEY'):
        logger.error("RESEND_API_KEY not set!")
        return {
            'success': False,
            'error': 'RESEND_API_KEY environment variable not configured',
        }

    # Get analytics data
    if use_real_data:
        try:
            from src.config.database import SessionLocal
            from src.services.email_analytics_aggregator import aggregate_user_usage

            db = SessionLocal()
            try:
                analytics_data = aggregate_user_usage(db, user_email)
                logger.info("Using real analytics data from database")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to get real data: {e}, using mock data")
            analytics_data = get_mock_analytics_data(user_email)
    else:
        analytics_data = get_mock_analytics_data(user_email)
        logger.info("Using mock analytics data")

    # Generate recommendations
    recommendations = generate_recommendations(
        current_week=analytics_data.get('current_week', {}),
        previous_week=analytics_data.get('previous_week', {}),
        week_over_week=analytics_data.get('week_over_week', {}),
        gpu_breakdown=analytics_data.get('gpu_breakdown', [])
    )

    logger.info(f"Generated {len(recommendations)} recommendations")

    # Compose email
    email_content = compose_weekly_report(
        user_id=user_email,
        user_email=user_email,
        user_name=user_name,
        analytics_data=analytics_data,
        recommendations=recommendations,
    )

    logger.info(f"Email composed with subject: {email_content.subject}")

    # Send email
    result = send_email(
        to=user_email,
        subject=email_content.subject,
        html=email_content.html_body,
    )

    if result.success:
        logger.info(f"Email sent successfully! ID: {result.email_id}")
        return {
            'success': True,
            'email_id': result.email_id,
            'recipient': user_email,
            'subject': email_content.subject,
            'attempts': result.attempts,
        }
    else:
        logger.error(f"Failed to send email: {result.error}")
        return {
            'success': False,
            'error': result.error,
            'attempts': result.attempts,
        }


def verify_delivery_log(user_email: str) -> Dict:
    """
    Verify EmailDeliveryLog entries for a user.

    Args:
        user_email: User email to check logs for

    Returns:
        Dict with delivery log information
    """
    try:
        from src.config.database import SessionLocal
        from src.models.email_delivery_log import EmailDeliveryLog

        db = SessionLocal()
        try:
            logs = db.query(EmailDeliveryLog).filter(
                EmailDeliveryLog.user_id == user_email
            ).order_by(EmailDeliveryLog.sent_at.desc()).limit(10).all()

            result = {
                'total_logs': len(logs),
                'logs': [log.to_dict() for log in logs],
            }

            logger.info(f"Found {len(logs)} delivery log entries for {user_email}")
            for log in logs:
                logger.info(f"  - {log.sent_at}: {log.status} (ID: {log.email_id})")

            return result

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to check delivery logs: {e}")
        return {
            'error': str(e),
            'total_logs': 0,
            'logs': [],
        }


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Test email sending for weekly GPU reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--email', '-e',
        required=True,
        help='Email address to send test email to'
    )

    parser.add_argument(
        '--name', '-n',
        help='Optional display name for the recipient'
    )

    parser.add_argument(
        '--preview-only', '-p',
        action='store_true',
        help='Only preview email, do not send'
    )

    parser.add_argument(
        '--output', '-o',
        help='Save HTML preview to file'
    )

    parser.add_argument(
        '--real-data', '-r',
        action='store_true',
        help='Use real data from database (requires database connection)'
    )

    parser.add_argument(
        '--verify-logs', '-v',
        action='store_true',
        help='Verify delivery logs after sending'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Weekly Email Report - Manual Test")
    print("=" * 60)

    if args.preview_only:
        print(f"\nGenerating preview for: {args.email}")
        result = preview_email(
            user_email=args.email,
            user_name=args.name,
            output_file=args.output,
        )
        print(f"\nPreview Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        if args.output:
            print(f"\nOpen {args.output} in a browser to view the email")

    else:
        print(f"\nSending test email to: {args.email}")
        result = send_test_email_to_user(
            user_email=args.email,
            user_name=args.name,
            use_real_data=args.real_data,
        )

        print(f"\nSend Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")

        if result.get('success') and args.verify_logs:
            print("\n" + "-" * 40)
            print("Verifying delivery logs...")
            logs = verify_delivery_log(args.email)
            print(f"Found {logs['total_logs']} log entries")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()

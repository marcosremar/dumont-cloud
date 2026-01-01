#!/usr/bin/env python3
"""Quick verification that the scheduler module imports correctly."""

import sys
sys.path.insert(0, '.')

try:
    from src.services.email_report_scheduler import (
        EmailReportScheduler,
        init_email_scheduler,
        shutdown_email_scheduler,
        _execute_weekly_reports_job,
    )
    print("OK - All scheduler functions import successfully")

    # Quick instantiation test
    scheduler = EmailReportScheduler(use_jobstore=False)
    print(f"OK - Scheduler instantiated: send_day={scheduler.send_day}, send_hour={scheduler.send_hour}")

except Exception as e:
    print(f"FAIL - Import error: {e}")
    sys.exit(1)

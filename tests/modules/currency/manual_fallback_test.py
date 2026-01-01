#!/usr/bin/env python3
"""
Manual Test Script: Exchange Rate Fallback

This script verifies the graceful fallback behavior when the exchange rate API fails.
Run this in a development environment with the full stack running.

Requirements:
- PostgreSQL database running with currency tables created
- Some cached exchange rates in the database (from previous successful fetches)

Steps to run:
1. Ensure database has some cached rates (run normal scheduler first)
2. Set an invalid API key to simulate API failure
3. Run this script
4. Observe fallback behavior in logs

Usage:
    # Normal mode (uses .env settings)
    python tests/modules/currency/manual_fallback_test.py

    # Force invalid API key
    python tests/modules/currency/manual_fallback_test.py --force-invalid-key
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def test_fallback_behavior(force_invalid_key: bool = False):
    """
    Test the exchange rate fallback behavior.

    Steps:
    1. Check if we have cached rates in the database
    2. Optionally set invalid API key to force API failure
    3. Attempt to fetch rates (should fallback to cache if API fails)
    4. Verify prices can still be displayed
    5. Report results
    """
    try:
        from src.config.database import SessionLocal
        from src.services.exchange_rate import ExchangeRateService, ExchangeRateCacheError
        from src.models.currency import ExchangeRate

        print("\n" + "="*60)
        print("MANUAL FALLBACK TEST: Exchange Rate API Failure Handling")
        print("="*60)

        # Create database session
        db = SessionLocal()

        # Step 1: Check cached rates
        print("\n[Step 1] Checking for cached exchange rates...")
        cached_count = db.query(ExchangeRate).count()
        print(f"  Found {cached_count} cached exchange rate records")

        if cached_count == 0:
            print("  WARNING: No cached rates found! Fallback will fail.")
            print("  Please run the scheduler first to populate cache.")

        # Get most recent rates
        from sqlalchemy import desc
        recent_rates = db.query(ExchangeRate).order_by(desc(ExchangeRate.fetched_at)).limit(3).all()
        if recent_rates:
            print("  Most recent cached rates:")
            for rate in recent_rates:
                age_hours = (datetime.utcnow() - rate.fetched_at).total_seconds() / 3600
                stale_indicator = " [STALE]" if age_hours > 48 else ""
                print(f"    {rate.from_currency}/{rate.to_currency}: {float(rate.rate):.6f} "
                      f"(age: {age_hours:.1f}h){stale_indicator}")

        # Step 2: Create service with potentially invalid API key
        print("\n[Step 2] Creating ExchangeRateService...")
        service = ExchangeRateService(db)

        original_api_key = service._api_key
        original_api_url = service._api_url

        if force_invalid_key:
            print("  Forcing invalid API key to simulate API failure...")
            service._api_key = "INVALID_API_KEY_FOR_TESTING"
            service._api_url = "https://invalid-api-url.example.com/rates"

        print(f"  API URL: {service._api_url}")
        print(f"  API Key: {'<set>' if service._api_key else '<not set>'}")

        # Step 3: Attempt to fetch rates
        print("\n[Step 3] Attempting to fetch exchange rates...")
        try:
            rates = await service.fetch_latest_rates()
            print(f"  SUCCESS: Fetched rates: {rates}")

            if force_invalid_key:
                print("  NOTE: Rates came from cache (API was invalid)")
            else:
                print("  NOTE: Rates came from API")

        except ExchangeRateCacheError as e:
            print(f"  FAILURE: {e}")
            print("  This is expected if no cached rates exist and API fails")

        # Step 4: Verify price display still works
        print("\n[Step 4] Testing price conversion with cached rates...")

        # Get fresh rates from get_all_rates
        all_rates = service.get_all_rates()
        print(f"  Base currency: {all_rates['base_currency']}")
        print(f"  Is stale: {all_rates['is_stale']}")
        print(f"  Stale warning: {all_rates['stale_warning']}")

        # Test conversions
        test_amounts = [(100, "USD", "EUR"), (50, "USD", "GBP"), (200, "USD", "BRL")]
        for amount, from_cur, to_cur in test_amounts:
            result = service.convert_amount(amount, from_cur, to_cur)
            if result:
                print(f"  {amount} {from_cur} = {result['converted_amount']} {to_cur} "
                      f"(rate: {result['rate']:.4f})")
            else:
                print(f"  Could not convert {amount} {from_cur} to {to_cur}")

        # Step 5: Health check
        print("\n[Step 5] Running health check...")
        health = service.check_rates_health()
        print(f"  Status: {health['status']}")
        if health['issues']:
            print("  Issues:")
            for issue in health['issues']:
                print(f"    - {issue}")

        # Restore original settings
        if force_invalid_key:
            service._api_key = original_api_key
            service._api_url = original_api_url

        # Cleanup
        db.close()

        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)

        # Summary
        print("\nSUMMARY:")
        if cached_count > 0:
            print("  [OK] Cached rates are available for fallback")
        else:
            print("  [WARN] No cached rates - fallback would fail")

        if all_rates.get('is_stale'):
            print("  [WARN] Rates are stale (>48 hours old)")
        elif all_rates.get('stale_warning'):
            print("  [WARN] Rates are getting old (>24 hours)")
        else:
            print("  [OK] Rates are fresh")

        print("\n")

    except ImportError as e:
        print(f"\nERROR: Cannot import required modules: {e}")
        print("Make sure you're running from the project root with proper environment")
        sys.exit(1)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    force_invalid = "--force-invalid-key" in sys.argv

    if force_invalid:
        print("Running with forced invalid API key...")

    asyncio.run(test_fallback_behavior(force_invalid))


if __name__ == "__main__":
    main()

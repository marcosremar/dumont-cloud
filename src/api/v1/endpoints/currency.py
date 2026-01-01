"""
Currency API endpoints for multi-currency pricing system

Provides endpoints for:
- Exchange rate retrieval
- User currency preference management
- Price conversion
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..schemas.currency import (
    CurrencyCode,
    CurrencyPreferenceRequest,
    CurrencyConversionRequest,
    ExchangeRatesResponse,
    CurrencyPreferenceResponse,
    CurrencyConversionResponse,
    SUPPORTED_CURRENCIES,
)
from ..dependencies import get_current_user_email, get_current_user_email_optional
from ....config.database import get_db
from ....services.exchange_rate import (
    ExchangeRateService,
    get_exchange_rate_service,
    ExchangeRateCacheError,
)
from ....models.currency import UserCurrencyPreference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["Currency"])


# ============================================================================
# Exchange Rate Endpoints
# ============================================================================

@router.get("/rates", response_model=ExchangeRatesResponse)
async def get_exchange_rates(
    db: Session = Depends(get_db),
):
    """
    Get current exchange rates

    Returns all supported exchange rates with USD as base currency.
    Includes staleness indicator if rates are older than 48 hours.
    """
    try:
        service = get_exchange_rate_service(db)
        rates_data = service.get_all_rates()

        return ExchangeRatesResponse(
            base_currency=rates_data['base_currency'],
            rates=rates_data['rates'],
            updated_at=rates_data['updated_at'],
            is_stale=rates_data['is_stale'],
            supported_currencies=SUPPORTED_CURRENCIES,
        )
    except Exception as e:
        logger.error(f"Failed to get exchange rates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve exchange rates: {str(e)}",
        )


@router.post("/refresh", response_model=ExchangeRatesResponse)
async def refresh_exchange_rates(
    db: Session = Depends(get_db),
    user_email: str = Depends(get_current_user_email),
):
    """
    Manually refresh exchange rates from external API

    Requires authentication. Fetches latest rates from external API
    and updates the cache.
    """
    try:
        service = get_exchange_rate_service(db)
        rates = await service.fetch_latest_rates()

        # Get full rates data including metadata
        rates_data = service.get_all_rates()

        logger.info(f"Exchange rates refreshed by {user_email}")

        return ExchangeRatesResponse(
            base_currency=rates_data['base_currency'],
            rates=rates_data['rates'],
            updated_at=rates_data['updated_at'],
            is_stale=rates_data['is_stale'],
            supported_currencies=SUPPORTED_CURRENCIES,
        )
    except ExchangeRateCacheError as e:
        logger.error(f"No exchange rates available: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exchange rate service unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to refresh exchange rates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh exchange rates: {str(e)}",
        )


@router.post("/convert", response_model=CurrencyConversionResponse)
async def convert_currency(
    request: CurrencyConversionRequest,
    db: Session = Depends(get_db),
):
    """
    Convert amount between currencies

    Converts a given amount from one currency to another using
    current exchange rates. Uses banker's rounding for precision.
    """
    try:
        service = get_exchange_rate_service(db)

        result = service.convert_amount(
            amount=request.amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
        )

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to convert from {request.from_currency} to {request.to_currency}. Check that both currencies are supported.",
            )

        # Check if rate is stale
        rate_record = None
        if request.from_currency == "USD":
            rate_record = db.query(UserCurrencyPreference).first()  # Just to get the session working

        # Get staleness from the service
        rates_data = service.get_all_rates()

        return CurrencyConversionResponse(
            original_amount=result['original_amount'],
            original_currency=result['from_currency'],
            converted_amount=result['converted_amount'],
            target_currency=result['to_currency'],
            rate=result['rate'],
            rate_updated_at=result['rate_updated_at'],
            is_rate_stale=rates_data['is_stale'],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to convert currency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert currency: {str(e)}",
        )


# ============================================================================
# User Currency Preference Endpoints
# ============================================================================

@router.get("/preference", response_model=CurrencyPreferenceResponse)
async def get_user_currency_preference(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Get user's currency preference

    Returns the user's stored currency preference.
    Defaults to USD if no preference is set.
    """
    try:
        preference = db.query(UserCurrencyPreference).filter(
            UserCurrencyPreference.user_email == user_email
        ).first()

        currency = preference.currency_code if preference else "USD"

        # Validate currency code
        if currency not in SUPPORTED_CURRENCIES:
            logger.warning(f"Invalid stored currency {currency} for user {user_email}, defaulting to USD")
            currency = "USD"

        return CurrencyPreferenceResponse(
            success=True,
            currency=currency,
            message=None,
        )
    except Exception as e:
        logger.error(f"Failed to get currency preference for {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get currency preference: {str(e)}",
        )


@router.post("/preference", response_model=CurrencyPreferenceResponse)
async def set_user_currency_preference(
    request: CurrencyPreferenceRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Set user's currency preference

    Stores the user's preferred display currency.
    Only accepts valid currency codes: USD, EUR, GBP, BRL.
    """
    try:
        currency_code = request.currency

        # Validate currency code
        if currency_code not in SUPPORTED_CURRENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid currency code. Supported currencies: {', '.join(SUPPORTED_CURRENCIES)}",
            )

        # Find or create preference
        preference = db.query(UserCurrencyPreference).filter(
            UserCurrencyPreference.user_email == user_email
        ).first()

        if preference:
            preference.currency_code = currency_code
        else:
            preference = UserCurrencyPreference(
                user_email=user_email,
                currency_code=currency_code,
            )
            db.add(preference)

        db.commit()
        db.refresh(preference)

        logger.info(f"Currency preference set to {currency_code} for user {user_email}")

        return CurrencyPreferenceResponse(
            success=True,
            currency=preference.currency_code,
            message=f"Currency preference updated to {preference.currency_code}",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to set currency preference for {user_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set currency preference: {str(e)}",
        )


# ============================================================================
# Health/Status Endpoints
# ============================================================================

@router.get("/health")
async def check_currency_health(
    db: Session = Depends(get_db),
):
    """
    Check health of currency service

    Returns detailed health status including rate freshness
    for each supported currency.
    """
    try:
        service = get_exchange_rate_service(db)
        health = service.check_rates_health()

        status_code = (
            status.HTTP_200_OK
            if health['status'] == 'healthy'
            else status.HTTP_503_SERVICE_UNAVAILABLE
            if health['status'] == 'unhealthy'
            else status.HTTP_200_OK  # degraded is still OK
        )

        return {
            "service": "currency",
            "status": health['status'],
            "currencies": health['currencies'],
            "issues": health['issues'],
            "supported_currencies": SUPPORTED_CURRENCIES,
        }
    except Exception as e:
        logger.error(f"Failed to check currency health: {e}")
        return {
            "service": "currency",
            "status": "unhealthy",
            "error": str(e),
            "supported_currencies": SUPPORTED_CURRENCIES,
        }

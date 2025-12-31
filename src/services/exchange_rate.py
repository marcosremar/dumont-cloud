"""
Exchange Rate Service for Multi-Currency Pricing

Fetches exchange rates from external API, caches them in Redis/database,
and provides currency conversion functionality.

Supports: USD, EUR, GBP, BRL
Base currency: USD (all rates stored relative to USD)
"""
import os
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

import httpx

from src.models.currency import ExchangeRate, SUPPORTED_CURRENCIES
from src.config.database import get_db

logger = logging.getLogger(__name__)


# Configuration
EXCHANGE_RATE_CONFIG = {
    # API timeout in seconds
    "api_timeout": 10.0,

    # Target currencies to fetch (excluding base currency USD)
    "target_currencies": ["EUR", "GBP", "BRL"],

    # Stale rate warning threshold (hours)
    "stale_warning_hours": 24,

    # Critical stale threshold - rates older than this are considered unreliable
    "stale_critical_hours": 48,

    # Redis cache TTL in seconds (24 hours)
    "redis_cache_ttl": 86400,

    # Maximum retries for API calls
    "max_retries": 3,

    # Retry delay in seconds (exponential backoff)
    "retry_delay": 1.0,
}


class ExchangeRateError(Exception):
    """Base exception for exchange rate errors."""
    pass


class ExchangeRateAPIError(ExchangeRateError):
    """Raised when API call fails."""
    pass


class ExchangeRateCacheError(ExchangeRateError):
    """Raised when both API and cache fail."""
    pass


class ExchangeRateService:
    """
    Service for fetching and managing exchange rates.

    Features:
    - Fetches rates from external API (exchangerate-api.io or similar)
    - Caches rates in database for fallback
    - Provides currency conversion with high precision
    - Graceful fallback to cached rates on API failure

    Usage:
        service = ExchangeRateService(db)
        rates = await service.fetch_latest_rates()
        converted = service.convert_amount(100.0, "USD", "EUR")
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the exchange rate service.

        Args:
            db: SQLAlchemy database session. If None, will be obtained via get_db()
        """
        self._db = db
        self._config = EXCHANGE_RATE_CONFIG.copy()
        self._api_url = os.getenv("EXCHANGE_RATE_API_URL", "https://api.exchangerate-api.com/v4/latest/USD")
        self._api_key = os.getenv("EXCHANGE_RATE_API_KEY", "")

    @property
    def db(self) -> Session:
        """Get database session."""
        if self._db is None:
            self._db = next(get_db())
        return self._db

    # ==================== PUBLIC API ====================

    async def fetch_latest_rates(self) -> Dict[str, float]:
        """
        Fetch latest exchange rates from external API.

        Attempts to fetch from API first, falls back to cached rates on failure.
        Successfully fetched rates are stored in the database.

        Returns:
            Dict mapping currency codes to rates (e.g., {'EUR': 0.92, 'GBP': 0.79, 'BRL': 5.42})

        Raises:
            ExchangeRateCacheError: If both API and cache fail
        """
        try:
            rates = await self._fetch_from_api()

            # Store successful rates in database
            self._store_rates(rates)

            logger.info(f"Successfully fetched exchange rates: {rates}")
            return rates

        except ExchangeRateAPIError as e:
            logger.warning(f"Exchange rate API failed: {e}. Falling back to cached rates.")

            # Fallback to cached rates from database
            cached_rates = self._get_cached_rates()

            if not cached_rates:
                raise ExchangeRateCacheError(
                    "No cached exchange rates available and API failed"
                )

            return cached_rates

    def get_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Get exchange rate between two currencies.

        Uses cached database rates. For fresh rates, call fetch_latest_rates() first.

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR')

        Returns:
            Exchange rate as float, or None if not found
        """
        # Validate currencies
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
            logger.warning(f"Invalid currency pair: {from_currency}/{to_currency}")
            return None

        # Same currency = 1:1
        if from_currency == to_currency:
            return 1.0

        # Direct lookup: from USD to target
        if from_currency == "USD":
            rate_record = self._get_latest_rate("USD", to_currency)
            if rate_record:
                return float(rate_record.rate)
            return None

        # Reverse lookup: from target to USD
        if to_currency == "USD":
            rate_record = self._get_latest_rate("USD", from_currency)
            if rate_record:
                # Invert the rate
                return 1.0 / float(rate_record.rate)
            return None

        # Cross-currency: from currency A to B via USD
        # A -> USD -> B
        rate_a_to_usd = self._get_latest_rate("USD", from_currency)
        rate_usd_to_b = self._get_latest_rate("USD", to_currency)

        if rate_a_to_usd and rate_usd_to_b:
            # Convert: A -> USD (invert) -> B
            return float(rate_usd_to_b.rate) / float(rate_a_to_usd.rate)

        return None

    def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        precision: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Convert an amount from one currency to another.

        Uses banker's rounding (round half to even) to minimize cumulative errors.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            precision: Decimal places for result (default 2)

        Returns:
            Dict with conversion details:
            {
                'original_amount': float,
                'converted_amount': float,
                'rate': float,
                'from_currency': str,
                'to_currency': str,
                'rate_updated_at': str (ISO format)
            }
            Or None if conversion fails
        """
        # Validate currencies
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
            logger.warning(f"Invalid currency for conversion: {from_currency}/{to_currency}")
            return None

        # Handle edge cases
        if amount <= 0:
            logger.warning(f"Invalid amount for conversion: {amount}")
            return None

        # Same currency = no conversion needed
        if from_currency == to_currency:
            return {
                'original_amount': amount,
                'converted_amount': amount,
                'rate': 1.0,
                'from_currency': from_currency,
                'to_currency': to_currency,
                'rate_updated_at': datetime.utcnow().isoformat()
            }

        # Get exchange rate
        rate = self.get_rate(from_currency, to_currency)
        if rate is None:
            logger.error(f"No exchange rate available for {from_currency}/{to_currency}")
            return None

        # Convert with high precision, then round
        converted = Decimal(str(amount)) * Decimal(str(rate))
        rounded = converted.quantize(
            Decimal(10) ** -precision,
            rounding=ROUND_HALF_EVEN  # Banker's rounding
        )

        # Validate result
        if rounded <= 0:
            logger.error(f"Conversion resulted in non-positive amount: {rounded}")
            return None

        # Get rate timestamp
        rate_record = self._get_latest_rate("USD", to_currency if from_currency == "USD" else from_currency)
        rate_updated_at = rate_record.fetched_at.isoformat() if rate_record else datetime.utcnow().isoformat()

        return {
            'original_amount': amount,
            'converted_amount': float(rounded),
            'rate': rate,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate_updated_at': rate_updated_at
        }

    def get_all_rates(self) -> Dict[str, Any]:
        """
        Get all current exchange rates.

        Returns:
            Dict with rates and metadata:
            {
                'base_currency': 'USD',
                'rates': {'EUR': 0.92, 'GBP': 0.79, 'BRL': 5.42, 'USD': 1.0},
                'updated_at': str (ISO format),
                'is_stale': bool,
                'stale_warning': bool
            }
        """
        rates = {'USD': 1.0}
        oldest_rate = None

        for currency in self._config["target_currencies"]:
            rate_record = self._get_latest_rate("USD", currency)
            if rate_record:
                rates[currency] = float(rate_record.rate)
                if oldest_rate is None or rate_record.fetched_at < oldest_rate:
                    oldest_rate = rate_record.fetched_at

        # Determine staleness
        is_stale = False
        stale_warning = False

        if oldest_rate:
            age_hours = (datetime.utcnow() - oldest_rate).total_seconds() / 3600
            stale_warning = age_hours > self._config["stale_warning_hours"]
            is_stale = age_hours > self._config["stale_critical_hours"]
        else:
            is_stale = True
            stale_warning = True

        return {
            'base_currency': 'USD',
            'rates': rates,
            'updated_at': oldest_rate.isoformat() if oldest_rate else None,
            'is_stale': is_stale,
            'stale_warning': stale_warning
        }

    def check_rates_health(self) -> Dict[str, Any]:
        """
        Check health of exchange rate data.

        Returns:
            Dict with health status for each currency
        """
        health = {
            'status': 'healthy',
            'currencies': {},
            'issues': []
        }

        for currency in self._config["target_currencies"]:
            rate_record = self._get_latest_rate("USD", currency)

            if rate_record:
                currency_status = {
                    'rate': float(rate_record.rate),
                    'fetched_at': rate_record.fetched_at.isoformat(),
                    'age_hours': rate_record.age_hours,
                    'is_stale': rate_record.is_stale
                }

                if rate_record.is_stale:
                    health['status'] = 'degraded'
                    health['issues'].append(f"Stale rate for {currency}: {rate_record.age_hours:.1f} hours old")
            else:
                currency_status = {
                    'rate': None,
                    'fetched_at': None,
                    'age_hours': None,
                    'is_stale': True
                }
                health['status'] = 'unhealthy'
                health['issues'].append(f"No exchange rate data for {currency}")

            health['currencies'][currency] = currency_status

        return health

    # ==================== PRIVATE METHODS ====================

    async def _fetch_from_api(self) -> Dict[str, float]:
        """
        Fetch exchange rates from external API.

        Returns:
            Dict mapping currency codes to rates

        Raises:
            ExchangeRateAPIError: If API call fails
        """
        headers = {}
        params = {}

        # Add API key if configured
        if self._api_key:
            # Support different API authentication methods
            params['apikey'] = self._api_key

        for attempt in range(self._config["max_retries"]):
            try:
                async with httpx.AsyncClient(timeout=self._config["api_timeout"]) as client:
                    response = await client.get(
                        self._api_url,
                        headers=headers,
                        params=params if params else None
                    )
                    response.raise_for_status()
                    data = response.json()

                # Parse response - support common API response formats
                # Format 1: {"rates": {"EUR": 0.92, ...}}
                # Format 2: {"conversion_rates": {"EUR": 0.92, ...}}
                rates_data = data.get('rates') or data.get('conversion_rates') or {}

                # Extract only supported currencies
                rates = {}
                for currency in self._config["target_currencies"]:
                    if currency in rates_data:
                        rates[currency] = float(rates_data[currency])
                    else:
                        logger.warning(f"Currency {currency} not found in API response")

                if not rates:
                    raise ExchangeRateAPIError("No valid rates found in API response")

                return rates

            except httpx.TimeoutException:
                logger.warning(f"API timeout (attempt {attempt + 1}/{self._config['max_retries']})")
                if attempt < self._config["max_retries"] - 1:
                    import asyncio
                    await asyncio.sleep(self._config["retry_delay"] * (2 ** attempt))

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"API rate limited (attempt {attempt + 1}/{self._config['max_retries']})")
                    if attempt < self._config["max_retries"] - 1:
                        import asyncio
                        await asyncio.sleep(self._config["retry_delay"] * (2 ** attempt))
                else:
                    raise ExchangeRateAPIError(f"API HTTP error: {e.response.status_code}")

            except httpx.RequestError as e:
                raise ExchangeRateAPIError(f"API request error: {str(e)}")

            except (KeyError, ValueError, TypeError) as e:
                raise ExchangeRateAPIError(f"API response parse error: {str(e)}")

        raise ExchangeRateAPIError(f"API failed after {self._config['max_retries']} retries")

    def _store_rates(self, rates: Dict[str, float]) -> None:
        """
        Store exchange rates in database.

        Args:
            rates: Dict mapping currency codes to rates
        """
        now = datetime.utcnow()

        for currency, rate in rates.items():
            exchange_rate = ExchangeRate(
                from_currency='USD',
                to_currency=currency,
                rate=rate,
                fetched_at=now
            )
            self.db.add(exchange_rate)

        try:
            self.db.commit()
            logger.info(f"Stored {len(rates)} exchange rates in database")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store exchange rates: {e}")
            raise

    def _get_cached_rates(self) -> Dict[str, float]:
        """
        Get cached exchange rates from database.

        Returns:
            Dict mapping currency codes to rates
        """
        rates = {}

        for currency in self._config["target_currencies"]:
            rate_record = self._get_latest_rate("USD", currency)

            if rate_record:
                rates[currency] = float(rate_record.rate)

                # Log warning for stale rates
                if rate_record.is_stale:
                    logger.error(
                        f"Stale exchange rate for {currency}: "
                        f"fetched at {rate_record.fetched_at.isoformat()}"
                    )
                elif rate_record.age_hours > self._config["stale_warning_hours"]:
                    logger.warning(
                        f"Exchange rate for {currency} is {rate_record.age_hours:.1f} hours old"
                    )

        return rates

    def _get_latest_rate(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """
        Get the most recent exchange rate record for a currency pair.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            ExchangeRate record or None
        """
        return self.db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency
        ).order_by(ExchangeRate.fetched_at.desc()).first()


# Singleton instance
_service_instance: Optional[ExchangeRateService] = None


def get_exchange_rate_service(db: Optional[Session] = None) -> ExchangeRateService:
    """
    Get exchange rate service instance.

    Usage:
        service = get_exchange_rate_service()
        rate = service.get_rate("USD", "EUR")
    """
    global _service_instance

    if _service_instance is None or db is not None:
        _service_instance = ExchangeRateService(db)

    return _service_instance

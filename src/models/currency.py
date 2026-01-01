"""
Currency Models for Multi-Currency Pricing System

Stores exchange rates and user currency preferences for international pricing.
Supports USD, EUR, GBP, and BRL currencies.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Index, Numeric
)

from src.config.database import Base


# Supported currencies (ISO 4217 codes)
SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'BRL']


class ExchangeRate(Base):
    """
    Stores exchange rates between currencies.

    Rates are fetched daily from external API and stored for:
    - Current price conversions
    - Fallback when API is unavailable
    - Historical rate tracking

    All rates are stored relative to USD as the base currency.
    """
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)

    # Currency pair (ISO 4217 codes)
    from_currency = Column(String(3), nullable=False, index=True)  # Base currency (usually USD)
    to_currency = Column(String(3), nullable=False, index=True)  # Target currency (EUR, GBP, BRL)

    # Exchange rate with high precision to avoid rounding errors
    # Numeric(18, 6) allows for rates like 0.923456 or 5.123456
    rate = Column(Numeric(precision=18, scale=6), nullable=False)

    # Timestamp when rate was fetched from API
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        # Index for looking up latest rate for a currency pair
        Index('idx_latest_rate', 'from_currency', 'to_currency', 'fetched_at'),
        # Index for finding all rates from a specific fetch time
        Index('idx_exchange_rate_fetched', 'fetched_at'),
    )

    @property
    def is_stale(self) -> bool:
        """Check if rate is older than 48 hours."""
        if not self.fetched_at:
            return True
        age_hours = (datetime.utcnow() - self.fetched_at).total_seconds() / 3600
        return age_hours > 48

    @property
    def age_hours(self) -> float:
        """Get age of rate in hours."""
        if not self.fetched_at:
            return float('inf')
        return (datetime.utcnow() - self.fetched_at).total_seconds() / 3600

    def to_dict(self):
        return {
            "id": self.id,
            "from_currency": self.from_currency,
            "to_currency": self.to_currency,
            "rate": float(self.rate) if self.rate else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "is_stale": self.is_stale,
            "age_hours": round(self.age_hours, 2),
        }

    def __repr__(self):
        rate_str = f"{float(self.rate):.6f}" if self.rate else "N/A"
        return f"<ExchangeRate {self.from_currency}/{self.to_currency} = {rate_str}>"


class UserCurrencyPreference(Base):
    """
    Stores user's preferred display currency.

    Each user can select their preferred currency for price display.
    Preference is synced between frontend localStorage and backend database.
    """
    __tablename__ = "user_currency_preferences"

    id = Column(Integer, primary_key=True, index=True)

    # User identifier (email address)
    user_email = Column(String(255), nullable=False, unique=True, index=True)

    # Preferred currency (ISO 4217 code)
    currency_code = Column(String(3), nullable=False, default="USD")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Index for looking up user preference
        Index('idx_user_currency_email', 'user_email'),
    )

    @property
    def is_valid_currency(self) -> bool:
        """Check if currency code is in supported list."""
        return self.currency_code in SUPPORTED_CURRENCIES

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "currency_code": self.currency_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<UserCurrencyPreference {self.user_email}: {self.currency_code}>"

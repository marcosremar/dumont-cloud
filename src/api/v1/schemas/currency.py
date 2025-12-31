"""
Currency API Schemas (Pydantic models for request/response validation)

Schemas for multi-currency pricing system:
- Exchange rate retrieval
- Currency preference management
- Price conversion
"""
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


# Supported currencies (ISO 4217 codes)
class CurrencyCode(str, Enum):
    """Supported currency codes"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    BRL = "BRL"


SUPPORTED_CURRENCIES = [c.value for c in CurrencyCode]


# ============================================================================
# Request Schemas
# ============================================================================

class CurrencyPreferenceRequest(BaseModel):
    """Request to set user's currency preference"""
    currency: CurrencyCode = Field(
        ...,
        description="Preferred currency code (USD, EUR, GBP, BRL)"
    )

    class Config:
        use_enum_values = True


class CurrencyConversionRequest(BaseModel):
    """Request for price conversion between currencies"""
    amount: float = Field(
        ...,
        gt=0,
        description="Amount to convert (must be positive)"
    )
    from_currency: CurrencyCode = Field(
        default=CurrencyCode.USD,
        description="Source currency code"
    )
    to_currency: CurrencyCode = Field(
        ...,
        description="Target currency code"
    )

    class Config:
        use_enum_values = True

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Ensure amount is a valid positive number"""
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > 999999999:  # Reasonable upper limit
            raise ValueError('Amount exceeds maximum allowed value')
        return round(v, 2)  # Round to 2 decimal places for monetary amounts


# ============================================================================
# Response Schemas
# ============================================================================

class ExchangeRateItem(BaseModel):
    """Individual exchange rate data"""
    from_currency: str = Field(..., description="Base currency code")
    to_currency: str = Field(..., description="Target currency code")
    rate: float = Field(..., description="Exchange rate value")
    is_stale: bool = Field(False, description="True if rate is older than 48 hours")


class ExchangeRatesResponse(BaseModel):
    """Response containing current exchange rates"""
    base_currency: str = Field("USD", description="Base currency for all rates")
    rates: Dict[str, float] = Field(
        ...,
        description="Exchange rates keyed by currency code (e.g., {'EUR': 0.92, 'GBP': 0.79, 'BRL': 5.42})"
    )
    updated_at: Optional[str] = Field(
        None,
        description="ISO timestamp of when rates were last updated"
    )
    is_stale: bool = Field(
        False,
        description="True if any rate is older than 48 hours"
    )
    supported_currencies: List[str] = Field(
        default_factory=lambda: SUPPORTED_CURRENCIES,
        description="List of all supported currency codes"
    )


class CurrencyPreferenceResponse(BaseModel):
    """Response for user's currency preference"""
    success: bool = Field(True, description="Operation success status")
    currency: str = Field(..., description="User's preferred currency code")
    message: Optional[str] = Field(None, description="Optional message")


class CurrencyConversionResponse(BaseModel):
    """Response for price conversion"""
    original_amount: float = Field(..., description="Original amount before conversion")
    original_currency: str = Field(..., description="Original currency code")
    converted_amount: float = Field(..., description="Converted amount")
    target_currency: str = Field(..., description="Target currency code")
    rate: float = Field(..., description="Exchange rate used for conversion")
    rate_updated_at: Optional[str] = Field(
        None,
        description="ISO timestamp of when the rate was last updated"
    )
    is_rate_stale: bool = Field(
        False,
        description="True if rate is older than 48 hours"
    )


class SchedulerStatusResponse(BaseModel):
    """Response for scheduler status"""
    running: bool = Field(..., description="Whether the scheduler is running")
    jobs: List[Dict] = Field(
        default_factory=list,
        description="List of scheduled jobs"
    )
    last_rate_update: Optional[str] = Field(
        None,
        description="ISO timestamp of last rate update"
    )
    next_scheduled_update: Optional[str] = Field(
        None,
        description="ISO timestamp of next scheduled update"
    )

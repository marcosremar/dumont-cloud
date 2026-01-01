"""
Endpoints para Relatórios de Economia Compartilháveis.

Privacy Filtering:
- Public endpoints only return aggregate savings data
- Sensitive fields (user_email, api_keys, instance_ids, etc.) are filtered out
- Uses whitelist-based filtering for maximum security

Rate Limiting:
- Report generation limited to 10 reports/hour per user
- Uses in-memory sliding window counter
- Returns 429 Too Many Requests with Retry-After header when exceeded
"""

import secrets
import time
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Dict, Any, Optional, Set, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.api.v1.dependencies import get_current_user_email
from src.services.savings_calculator import SavingsCalculator
from src.models.shareable_report import ShareableReport
from src.api.v1.schemas.reports import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportDataResponse,
)

router = APIRouter()

# =============================================================================
# RATE LIMITING - In-memory sliding window counter
# =============================================================================

# Rate limit configuration
RATE_LIMIT_MAX_REQUESTS = 10  # Maximum reports per window
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour window


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Tracks request timestamps per user and enforces a maximum number
    of requests within a rolling time window.

    Thread-safe implementation using a lock for concurrent access.
    """

    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS,
                 window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def _cleanup_expired(self, user_id: str, current_time: float) -> None:
        """Remove expired request timestamps for a user."""
        cutoff = current_time - self.window_seconds
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > cutoff
        ]

    def is_allowed(self, user_id: str) -> Tuple[bool, int]:
        """
        Check if a request is allowed for the user.

        Returns:
            Tuple of (is_allowed, seconds_until_reset)
            - is_allowed: True if request is within rate limit
            - seconds_until_reset: Seconds until oldest request expires (for Retry-After)
        """
        current_time = time.time()

        with self._lock:
            # Clean up expired timestamps
            self._cleanup_expired(user_id, current_time)

            request_count = len(self._requests[user_id])

            if request_count >= self.max_requests:
                # Calculate when the oldest request will expire
                oldest_request = min(self._requests[user_id])
                seconds_until_reset = int(
                    (oldest_request + self.window_seconds) - current_time
                ) + 1  # Add 1 second buffer
                return False, max(1, seconds_until_reset)

            # Request is allowed, record the timestamp
            self._requests[user_id].append(current_time)
            return True, 0

    def get_remaining(self, user_id: str) -> int:
        """Get remaining requests in the current window."""
        current_time = time.time()

        with self._lock:
            self._cleanup_expired(user_id, current_time)
            return max(0, self.max_requests - len(self._requests[user_id]))


# Global rate limiter instance
report_rate_limiter = RateLimiter()

# =============================================================================
# PRIVACY FILTERING - Whitelisted fields for public endpoints
# =============================================================================

# Fields allowed in savings_data (aggregate data only, no user-identifying info)
ALLOWED_SAVINGS_DATA_FIELDS: Set[str] = {
    # Aggregate savings amounts
    "total_savings_vs_aws",
    "total_savings_vs_gcp",
    "total_savings_vs_azure",
    # Percentage metrics
    "savings_percentage_avg",
    "savings_percentage",
    # Time metrics (no user-identifying info)
    "total_hours",
    "period",
    # Monthly/annual aggregates
    "monthly_savings",
    "annual_savings",
}

# Fields allowed in config (only display preferences, no sensitive settings)
ALLOWED_CONFIG_FIELDS: Set[str] = {
    # Display toggles
    "monthly_savings",
    "annual_savings",
    "percentage_saved",
    "provider_comparison",
    # Format preferences
    "format",
    "theme",
}

# Fields that must NEVER appear in public responses (defensive blacklist)
SENSITIVE_FIELDS: Set[str] = {
    # User identification
    "user_id",
    "user_email",
    "email",
    "account_id",
    "customer_id",
    # API credentials
    "api_key",
    "api_keys",
    "api_secret",
    "access_token",
    "refresh_token",
    "secret_key",
    "password",
    "credentials",
    # Instance-specific data
    "instance_id",
    "instance_ids",
    "instance_name",
    "ssh_key",
    "ip_address",
    "private_ip",
    # Internal data
    "internal_id",
    "database_id",
}


def filter_dict_by_whitelist(
    data: Optional[Dict[str, Any]],
    allowed_fields: Set[str],
    sensitive_fields: Set[str] = SENSITIVE_FIELDS
) -> Optional[Dict[str, Any]]:
    """
    Filter a dictionary to only include whitelisted fields.

    Uses dual approach:
    1. Whitelist: Only include fields in allowed_fields
    2. Blacklist: Double-check to exclude any sensitive fields

    This ensures maximum privacy protection.
    """
    if data is None:
        return None

    if not isinstance(data, dict):
        return None

    filtered = {}
    for key, value in data.items():
        # First check: field must be in whitelist
        if key not in allowed_fields:
            continue

        # Second check: field must NOT be in sensitive blacklist
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_fields):
            continue

        # Handle nested dicts recursively (but only allow simple values in public data)
        if isinstance(value, dict):
            # For nested dicts, we don't recurse - just skip them for safety
            # Public reports should only contain flat, aggregate data
            continue

        # Handle lists - filter out any that might contain sensitive data
        if isinstance(value, list):
            # Only allow lists of primitive values (numbers, strings, bools)
            if all(isinstance(item, (int, float, str, bool, type(None))) for item in value):
                filtered[key] = value
            continue

        # Allow primitive values
        filtered[key] = value

    return filtered if filtered else None


def sanitize_savings_data(savings_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Sanitize savings_data for public consumption.

    Only returns aggregate financial metrics, no user-identifying information.
    """
    return filter_dict_by_whitelist(savings_data, ALLOWED_SAVINGS_DATA_FIELDS)


def sanitize_config(config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Sanitize config for public consumption.

    Only returns display preferences, no sensitive settings.
    """
    return filter_dict_by_whitelist(config, ALLOWED_CONFIG_FIELDS)


def generate_shareable_id(length: int = 10) -> str:
    """
    Gera um ID único, URL-safe para relatórios compartilháveis.
    Usa secrets.token_urlsafe para gerar IDs seguros e não-sequenciais.
    """
    # token_urlsafe retorna ~1.3x o número de bytes, então ajustamos
    return secrets.token_urlsafe(length)[:length]


@router.post("/generate", response_model=GenerateReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: GenerateReportRequest,
    response: Response,
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Gera um novo relatório de economia compartilhável.

    - Requer autenticação
    - Aceita configuração de formato (twitter/linkedin/generic) e métricas
    - Retorna shareable_id para URL pública e image_url (após processamento)
    - Rate limited: max 10 reports/hour per user

    Rate Limit Headers:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests in current window
    - X-RateLimit-Reset: Seconds until window reset (when limit exceeded)
    """
    # Check rate limit
    is_allowed, retry_after = report_rate_limiter.is_allowed(user_id)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} reports per hour. Try again in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(retry_after)
            }
        )

    # Add rate limit headers to successful response
    remaining = report_rate_limiter.get_remaining(user_id)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    # Gerar ID único para o relatório
    shareable_id = generate_shareable_id()

    # Verificar se ID já existe (muito improvável, mas por segurança)
    existing = db.query(ShareableReport).filter(
        ShareableReport.shareable_id == shareable_id
    ).first()
    if existing:
        # Tentar novamente com novo ID
        shareable_id = generate_shareable_id(12)

    # Obter dados de economia atuais do usuário
    calculator = SavingsCalculator(db)
    savings_summary = calculator.calculate_user_savings(user_id, period="year")

    # Preparar configuração de métricas como dict
    config_dict = request.metrics.model_dump()

    # Preparar dados de economia para armazenamento (snapshot)
    savings_data = {
        "total_savings_vs_aws": savings_summary.get("savings_vs_aws", 0),
        "total_savings_vs_gcp": savings_summary.get("savings_vs_gcp", 0),
        "total_savings_vs_azure": savings_summary.get("savings_vs_azure", 0),
        "savings_percentage_avg": savings_summary.get("savings_percentage_avg", 0),
        "total_hours": savings_summary.get("total_hours", 0),
        "period": "year",
    }

    # Criar registro no banco de dados
    report = ShareableReport(
        user_id=user_id,
        shareable_id=shareable_id,
        config=config_dict,
        format=request.format.value,
        savings_data=savings_data,
        created_at=datetime.utcnow(),
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return GenerateReportResponse(
        shareable_id=report.shareable_id,
        image_url=report.image_url,  # Será None inicialmente, preenchido após geração da imagem
        format=report.format,
        config=report.config,
        created_at=report.created_at,
    )


@router.get("/{shareable_id}", response_model=ReportDataResponse)
async def get_report(
    shareable_id: str,
    db: Session = Depends(get_db)
):
    """
    Recupera dados públicos de um relatório compartilhável.

    - Endpoint público (não requer autenticação)
    - Retorna apenas dados agregados de economia (sem informações sensíveis)
    - Privacy filtering: excludes user_email, api_keys, instance_ids, and other sensitive data
    """
    report = db.query(ShareableReport).filter(
        ShareableReport.shareable_id == shareable_id
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Apply privacy filtering to savings_data
    # This removes any sensitive fields that might have been stored accidentally
    filtered_savings_data = sanitize_savings_data(report.savings_data)

    # Retornar apenas dados públicos (privacy filtering applied)
    # Include image_url for social media og:image meta tag
    return ReportDataResponse(
        shareable_id=report.shareable_id,
        format=report.format,
        savings_data=filtered_savings_data,
        image_url=report.image_url,
        created_at=report.created_at,
    )

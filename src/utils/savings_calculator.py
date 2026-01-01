"""
Savings calculator utility for real-time and historical cost calculations.

This module provides standalone functions for calculating cost savings when using
Dumont Cloud compared to major cloud providers (AWS, GCP, Azure).

Functions:
    calculate_savings: Calculate savings for a specific GPU usage period
    calculate_session_savings: Calculate real-time savings for active sessions
    calculate_lifetime_savings: Calculate total historical savings
    calculate_projections: Project future savings based on usage patterns
    calculate_hourly_comparison: Get hourly rate comparison across providers
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging

from src.services.pricing_service import get_pricing_service, PricingService

logger = logging.getLogger(__name__)


def _round_currency(value: float, precision: int = 2) -> float:
    """Round a value to specified decimal places using banker's rounding."""
    return float(Decimal(str(value)).quantize(
        Decimal(10) ** -precision,
        rounding=ROUND_HALF_UP
    ))


def calculate_savings(
    gpu_type: str,
    hours: float,
    provider: str = 'AWS',
    dumont_cost: Optional[float] = None,
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Calculate cost savings for using Dumont Cloud vs a cloud provider.

    This is the primary function for calculating savings for any GPU usage period.
    Supports both real-time (using calculated costs) and historical (using actual costs).

    Args:
        gpu_type: GPU model name (e.g., 'RTX 4090', 'A100')
        hours: Number of hours of usage
        provider: Cloud provider for comparison ('AWS', 'GCP', 'Azure')
        dumont_cost: Optional actual Dumont cost if different from calculated
        pricing_service: Optional PricingService instance (uses singleton if not provided)

    Returns:
        Dictionary containing:
            - gpu_type: The GPU model used
            - hours: Hours of usage
            - provider: Comparison provider
            - dumont_hourly: Dumont hourly rate
            - provider_hourly: Provider hourly rate
            - dumont_cost: Total Dumont cost
            - provider_cost: Total provider cost
            - savings: Dollar amount saved
            - savings_percentage: Percentage saved
            - currency: Currency code (USD)

    Example:
        >>> result = calculate_savings('RTX 4090', hours=10, provider='AWS')
        >>> print(f"Saved ${result['savings']:.2f}")
        Saved $33.60
    """
    if hours < 0:
        raise ValueError("Hours cannot be negative")

    service = pricing_service or get_pricing_service()
    provider = provider.upper()

    if provider not in ['AWS', 'GCP', 'AZURE']:
        logger.warning(f"Unknown provider '{provider}', defaulting to AWS")
        provider = 'AWS'

    provider_hourly = service.get_provider_price(provider, gpu_type)
    dumont_hourly = service.get_dumont_price(gpu_type)

    provider_cost = provider_hourly * hours
    actual_dumont_cost = dumont_cost if dumont_cost is not None else (dumont_hourly * hours)

    savings = provider_cost - actual_dumont_cost
    savings_pct = (savings / provider_cost * 100) if provider_cost > 0 else 0

    return {
        'gpu_type': gpu_type,
        'hours': _round_currency(hours, 2),
        'provider': provider,
        'dumont_hourly': _round_currency(dumont_hourly, 2),
        'provider_hourly': _round_currency(provider_hourly, 2),
        'dumont_cost': _round_currency(actual_dumont_cost, 2),
        'provider_cost': _round_currency(provider_cost, 2),
        'savings': _round_currency(savings, 2),
        'savings_percentage': _round_currency(savings_pct, 1),
        'currency': 'USD',
    }


def calculate_session_savings(
    instances: List[Dict[str, Any]],
    provider: str = 'AWS',
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Calculate real-time savings for active GPU sessions.

    Calculates cumulative savings across multiple active instances,
    suitable for live dashboard updates.

    Args:
        instances: List of instance dictionaries, each containing:
            - gpu_type: GPU model name
            - start_time: Session start datetime (or ISO string)
            - hours: Optional pre-calculated hours (uses start_time if not provided)
            - dumont_cost: Optional actual cost incurred so far
        provider: Cloud provider for comparison
        pricing_service: Optional PricingService instance

    Returns:
        Dictionary containing:
            - total_savings: Combined savings across all instances
            - total_dumont_cost: Combined Dumont cost
            - total_provider_cost: What providers would have charged
            - instance_count: Number of active instances
            - instances: Per-instance breakdown
            - calculated_at: Calculation timestamp
            - provider: Comparison provider
            - currency: Currency code

    Example:
        >>> instances = [
        ...     {'gpu_type': 'RTX 4090', 'start_time': datetime.now() - timedelta(hours=2)},
        ...     {'gpu_type': 'A100', 'hours': 1.5}
        ... ]
        >>> result = calculate_session_savings(instances, provider='AWS')
        >>> print(f"Total session savings: ${result['total_savings']:.2f}")
    """
    service = pricing_service or get_pricing_service()
    provider = provider.upper()
    now = datetime.utcnow()

    total_savings = 0.0
    total_dumont_cost = 0.0
    total_provider_cost = 0.0
    instance_details = []

    for instance in instances:
        gpu_type = instance.get('gpu_type', 'default')

        # Calculate hours from start_time or use provided hours
        if 'hours' in instance:
            hours = float(instance['hours'])
        elif 'start_time' in instance:
            start_time = instance['start_time']
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            hours = (now - start_time).total_seconds() / 3600
        else:
            hours = 0.0

        dumont_cost = instance.get('dumont_cost')

        savings_data = calculate_savings(
            gpu_type=gpu_type,
            hours=hours,
            provider=provider,
            dumont_cost=dumont_cost,
            pricing_service=service
        )

        total_savings += savings_data['savings']
        total_dumont_cost += savings_data['dumont_cost']
        total_provider_cost += savings_data['provider_cost']

        instance_details.append({
            'gpu_type': gpu_type,
            'hours': savings_data['hours'],
            'savings': savings_data['savings'],
            'dumont_cost': savings_data['dumont_cost'],
            'provider_cost': savings_data['provider_cost'],
        })

    return {
        'total_savings': _round_currency(total_savings, 2),
        'total_dumont_cost': _round_currency(total_dumont_cost, 2),
        'total_provider_cost': _round_currency(total_provider_cost, 2),
        'instance_count': len(instances),
        'instances': instance_details,
        'calculated_at': now.isoformat() + 'Z',
        'provider': provider,
        'currency': 'USD',
    }


def calculate_lifetime_savings(
    usage_records: List[Dict[str, Any]],
    provider: str = 'AWS',
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Calculate total historical savings from usage records.

    Aggregates savings across all historical usage to show lifetime value.

    Args:
        usage_records: List of usage record dictionaries, each containing:
            - gpu_type: GPU model name
            - hours: Hours used in this period
            - dumont_cost: Optional actual cost (calculated if not provided)
            - created_at: Optional timestamp for the usage period
        provider: Cloud provider for comparison
        pricing_service: Optional PricingService instance

    Returns:
        Dictionary containing:
            - lifetime_savings: Total savings since account creation
            - total_hours: Total GPU hours used
            - total_dumont_cost: Total spent on Dumont Cloud
            - total_provider_cost: What providers would have charged
            - savings_percentage: Overall percentage saved
            - gpu_breakdown: Savings breakdown by GPU type
            - record_count: Number of usage records processed
            - currency: Currency code

    Example:
        >>> records = [
        ...     {'gpu_type': 'RTX 4090', 'hours': 100, 'dumont_cost': 74.00},
        ...     {'gpu_type': 'A100', 'hours': 50, 'dumont_cost': 125.00}
        ... ]
        >>> result = calculate_lifetime_savings(records, provider='AWS')
        >>> print(f"Lifetime savings: ${result['lifetime_savings']:.2f}")
    """
    service = pricing_service or get_pricing_service()
    provider = provider.upper()

    total_savings = 0.0
    total_hours = 0.0
    total_dumont_cost = 0.0
    total_provider_cost = 0.0
    gpu_breakdown: Dict[str, Dict[str, float]] = {}

    for record in usage_records:
        gpu_type = record.get('gpu_type', 'default')
        hours = float(record.get('hours', 0))
        dumont_cost = record.get('dumont_cost')

        savings_data = calculate_savings(
            gpu_type=gpu_type,
            hours=hours,
            provider=provider,
            dumont_cost=dumont_cost,
            pricing_service=service
        )

        total_savings += savings_data['savings']
        total_hours += hours
        total_dumont_cost += savings_data['dumont_cost']
        total_provider_cost += savings_data['provider_cost']

        # Aggregate by GPU type
        if gpu_type not in gpu_breakdown:
            gpu_breakdown[gpu_type] = {
                'hours': 0.0,
                'savings': 0.0,
                'dumont_cost': 0.0,
                'provider_cost': 0.0,
            }
        gpu_breakdown[gpu_type]['hours'] += hours
        gpu_breakdown[gpu_type]['savings'] += savings_data['savings']
        gpu_breakdown[gpu_type]['dumont_cost'] += savings_data['dumont_cost']
        gpu_breakdown[gpu_type]['provider_cost'] += savings_data['provider_cost']

    # Round GPU breakdown values
    for gpu_data in gpu_breakdown.values():
        gpu_data['hours'] = _round_currency(gpu_data['hours'], 2)
        gpu_data['savings'] = _round_currency(gpu_data['savings'], 2)
        gpu_data['dumont_cost'] = _round_currency(gpu_data['dumont_cost'], 2)
        gpu_data['provider_cost'] = _round_currency(gpu_data['provider_cost'], 2)

    savings_pct = (total_savings / total_provider_cost * 100) if total_provider_cost > 0 else 0

    return {
        'lifetime_savings': _round_currency(total_savings, 2),
        'total_hours': _round_currency(total_hours, 2),
        'total_dumont_cost': _round_currency(total_dumont_cost, 2),
        'total_provider_cost': _round_currency(total_provider_cost, 2),
        'savings_percentage': _round_currency(savings_pct, 1),
        'gpu_breakdown': gpu_breakdown,
        'record_count': len(usage_records),
        'provider': provider,
        'currency': 'USD',
    }


def calculate_projections(
    gpu_type: str,
    daily_hours: float = 8.0,
    provider: str = 'AWS',
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Project future savings based on usage patterns.

    Estimates potential savings over daily, weekly, monthly, and yearly periods.

    Args:
        gpu_type: GPU model name
        daily_hours: Average hours used per day
        provider: Cloud provider for comparison
        pricing_service: Optional PricingService instance

    Returns:
        Dictionary containing:
            - gpu_type: GPU model used for projection
            - daily_hours: Usage assumption
            - hourly_savings: Savings per hour
            - projections: Breakdown by time period (daily, weekly, monthly, yearly)
            - provider: Comparison provider
            - assumptions: Calculation assumptions
            - currency: Currency code

    Example:
        >>> result = calculate_projections('RTX 4090', daily_hours=12, provider='AWS')
        >>> print(f"Yearly projection: ${result['projections']['yearly']:.2f}")
    """
    if daily_hours < 0:
        raise ValueError("Daily hours cannot be negative")
    if daily_hours > 24:
        raise ValueError("Daily hours cannot exceed 24")

    service = pricing_service or get_pricing_service()
    provider = provider.upper()

    provider_hourly = service.get_provider_price(provider, gpu_type)
    dumont_hourly = service.get_dumont_price(gpu_type)
    hourly_savings = provider_hourly - dumont_hourly

    daily_savings = hourly_savings * daily_hours
    weekly_savings = daily_savings * 7
    monthly_savings = daily_savings * 30
    yearly_savings = daily_savings * 365

    return {
        'gpu_type': gpu_type,
        'daily_hours': daily_hours,
        'hourly_savings': _round_currency(hourly_savings, 2),
        'projections': {
            'daily': _round_currency(daily_savings, 2),
            'weekly': _round_currency(weekly_savings, 2),
            'monthly': _round_currency(monthly_savings, 2),
            'yearly': _round_currency(yearly_savings, 2),
        },
        'provider': provider,
        'assumptions': {
            'days_per_week': 7,
            'days_per_month': 30,
            'days_per_year': 365,
        },
        'currency': 'USD',
    }


def calculate_hourly_comparison(
    gpu_type: str,
    providers: Optional[List[str]] = None,
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Get hourly rate comparison for a GPU across all providers.

    Useful for displaying price comparison charts in the dashboard.

    Args:
        gpu_type: GPU model name
        providers: Optional list of providers to compare (default: all)
        pricing_service: Optional PricingService instance

    Returns:
        Dictionary containing:
            - gpu_type: GPU model compared
            - dumont_hourly: Dumont Cloud hourly rate
            - providers: Rate for each cloud provider
            - savings_vs: Savings compared to each provider
            - best_alternative: Provider with lowest rate (excluding Dumont)
            - max_savings_provider: Provider with highest savings potential
            - currency: Currency code

    Example:
        >>> result = calculate_hourly_comparison('RTX 4090')
        >>> for provider, rate in result['providers'].items():
        ...     print(f"{provider}: ${rate}/hr")
    """
    service = pricing_service or get_pricing_service()
    providers = providers or service.get_supported_providers()

    dumont_hourly = service.get_dumont_price(gpu_type)
    provider_rates: Dict[str, float] = {}
    savings_vs: Dict[str, Dict[str, Any]] = {}

    for provider in providers:
        provider = provider.upper()
        provider_hourly = service.get_provider_price(provider, gpu_type)
        provider_rates[provider] = _round_currency(provider_hourly, 2)

        savings = provider_hourly - dumont_hourly
        savings_pct = (savings / provider_hourly * 100) if provider_hourly > 0 else 0

        savings_vs[provider] = {
            'amount': _round_currency(savings, 2),
            'percentage': _round_currency(savings_pct, 1),
        }

    # Find best alternative and max savings
    best_alternative = min(provider_rates.items(), key=lambda x: x[1])[0] if provider_rates else None
    max_savings_provider = max(savings_vs.items(), key=lambda x: x[1]['amount'])[0] if savings_vs else None

    return {
        'gpu_type': gpu_type,
        'dumont_hourly': _round_currency(dumont_hourly, 2),
        'providers': provider_rates,
        'savings_vs': savings_vs,
        'best_alternative': best_alternative,
        'max_savings_provider': max_savings_provider,
        'currency': 'USD',
    }


def calculate_savings_rate(
    gpu_type: str,
    provider: str = 'AWS',
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Calculate the real-time savings rate (per second/minute/hour).

    Useful for live-updating savings counters in the dashboard.

    Args:
        gpu_type: GPU model name
        provider: Cloud provider for comparison
        pricing_service: Optional PricingService instance

    Returns:
        Dictionary containing:
            - gpu_type: GPU model
            - provider: Comparison provider
            - savings_per_second: Savings accumulating per second
            - savings_per_minute: Savings accumulating per minute
            - savings_per_hour: Savings per hour
            - dumont_cost_per_hour: Dumont hourly rate
            - provider_cost_per_hour: Provider hourly rate
            - currency: Currency code

    Example:
        >>> rate = calculate_savings_rate('RTX 4090', 'AWS')
        >>> print(f"Saving ${rate['savings_per_second']:.4f}/second")
    """
    service = pricing_service or get_pricing_service()
    provider = provider.upper()

    provider_hourly = service.get_provider_price(provider, gpu_type)
    dumont_hourly = service.get_dumont_price(gpu_type)
    savings_per_hour = provider_hourly - dumont_hourly

    return {
        'gpu_type': gpu_type,
        'provider': provider,
        'savings_per_second': _round_currency(savings_per_hour / 3600, 6),
        'savings_per_minute': _round_currency(savings_per_hour / 60, 4),
        'savings_per_hour': _round_currency(savings_per_hour, 2),
        'dumont_cost_per_hour': _round_currency(dumont_hourly, 2),
        'provider_cost_per_hour': _round_currency(provider_hourly, 2),
        'currency': 'USD',
    }


def get_savings_summary(
    lifetime_records: List[Dict[str, Any]],
    active_instances: List[Dict[str, Any]],
    provider: str = 'AWS',
    daily_hours: float = 8.0,
    pricing_service: Optional[PricingService] = None
) -> Dict[str, Any]:
    """
    Get a comprehensive savings summary for the dashboard widget.

    Combines lifetime, current session, and projections into one response.

    Args:
        lifetime_records: Historical usage records
        active_instances: Currently running GPU instances
        provider: Cloud provider for comparison
        daily_hours: Assumed daily usage for projections
        pricing_service: Optional PricingService instance

    Returns:
        Dictionary containing:
            - lifetime: Lifetime savings data
            - current_session: Active session savings
            - projections: Future savings projections (if active instances exist)
            - provider: Comparison provider
            - calculated_at: Timestamp
            - has_active_session: Whether there are running instances
            - currency: Currency code

    Example:
        >>> summary = get_savings_summary(
        ...     lifetime_records=[{'gpu_type': 'RTX 4090', 'hours': 100}],
        ...     active_instances=[{'gpu_type': 'RTX 4090', 'hours': 2.5}],
        ...     provider='AWS'
        ... )
    """
    service = pricing_service or get_pricing_service()
    provider = provider.upper()
    now = datetime.utcnow()

    # Calculate lifetime savings
    lifetime = calculate_lifetime_savings(
        usage_records=lifetime_records,
        provider=provider,
        pricing_service=service
    )

    # Calculate current session savings
    session = calculate_session_savings(
        instances=active_instances,
        provider=provider,
        pricing_service=service
    )

    # Calculate projections based on primary active GPU or most used historical GPU
    projection_gpu = 'RTX 4090'  # default
    if active_instances:
        projection_gpu = active_instances[0].get('gpu_type', 'RTX 4090')
    elif lifetime.get('gpu_breakdown'):
        # Use GPU with most hours
        projection_gpu = max(
            lifetime['gpu_breakdown'].items(),
            key=lambda x: x[1]['hours']
        )[0]

    projections = calculate_projections(
        gpu_type=projection_gpu,
        daily_hours=daily_hours,
        provider=provider,
        pricing_service=service
    )

    return {
        'lifetime': {
            'savings': lifetime['lifetime_savings'],
            'hours': lifetime['total_hours'],
            'dumont_cost': lifetime['total_dumont_cost'],
            'provider_cost': lifetime['total_provider_cost'],
            'savings_percentage': lifetime['savings_percentage'],
        },
        'current_session': {
            'savings': session['total_savings'],
            'dumont_cost': session['total_dumont_cost'],
            'provider_cost': session['total_provider_cost'],
            'instance_count': session['instance_count'],
        },
        'projections': projections['projections'],
        'provider': provider,
        'calculated_at': now.isoformat() + 'Z',
        'has_active_session': len(active_instances) > 0,
        'currency': 'USD',
    }

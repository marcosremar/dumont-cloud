"""
Dumont Cloud Utilities

This module provides standalone utility functions for various calculations
and operations across the platform.
"""

from .savings_calculator import (
    calculate_savings,
    calculate_session_savings,
    calculate_lifetime_savings,
    calculate_projections,
    calculate_hourly_comparison,
    calculate_savings_rate,
    get_savings_summary,
)

__all__ = [
    # Savings calculator functions
    "calculate_savings",
    "calculate_session_savings",
    "calculate_lifetime_savings",
    "calculate_projections",
    "calculate_hourly_comparison",
    "calculate_savings_rate",
    "get_savings_summary",
Utility modules for Dumont Cloud.
"""

from .region_cache import RegionCache, get_region_cache, clear_region_cache_singleton

__all__ = [
    "RegionCache",
    "get_region_cache",
    "clear_region_cache_singleton",
]

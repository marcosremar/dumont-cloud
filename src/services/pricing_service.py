"""
Pricing service for cloud provider GPU price comparison.

This service provides baseline GPU pricing data for AWS, GCP, and Azure
for comparison with Dumont Cloud pricing.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Baseline hourly GPU pricing by provider (USD)
# These values are approximations based on public pricing as of 2024
# Sources: AWS EC2 pricing, GCP Compute Engine, Azure VMs
# Note: Keys are uppercase to match provider.upper() lookups
PROVIDER_GPU_PRICING: Dict[str, Dict[str, float]] = {
    'AWS': {
        'RTX 4090': 4.10,      # p5.xlarge equivalent
        'RTX 4080': 3.50,
        'RTX 4070': 2.80,
        'RTX 3090': 3.06,      # p4d.xlarge equivalent
        'RTX 3080': 2.50,
        'RTX 3070': 2.00,
        'A100': 32.77,         # p4d.24xlarge
        'A100-80GB': 37.50,    # p5.48xlarge per-GPU
        'A10': 5.67,           # g5.xlarge
        'A10G': 5.67,          # g5.xlarge
        'V100': 3.06,          # p3.2xlarge
        'T4': 0.526,           # g4dn.xlarge
        'L4': 1.20,            # g6.xlarge
        'H100': 65.00,         # p5.48xlarge
        'default': 3.00,
    },
    'GCP': {
        'RTX 4090': 3.80,
        'RTX 4080': 3.20,
        'RTX 4070': 2.60,
        'RTX 3090': 2.80,
        'RTX 3080': 2.30,
        'RTX 3070': 1.80,
        'A100': 29.39,         # a2-highgpu-1g
        'A100-80GB': 33.00,    # a2-ultragpu-1g
        'A10': 5.00,
        'A10G': 5.00,
        'V100': 2.48,
        'T4': 0.35,
        'L4': 0.98,            # g2-standard-4
        'H100': 55.00,         # a3-highgpu-1g
        'default': 2.75,
    },
    'AZURE': {
        'RTX 4090': 4.50,
        'RTX 4080': 3.80,
        'RTX 4070': 3.10,
        'RTX 3090': 3.30,
        'RTX 3080': 2.70,
        'RTX 3070': 2.20,
        'A100': 32.77,         # NC A100 v4
        'A100-80GB': 37.00,    # ND A100 v4
        'A10': 5.80,
        'A10G': 5.80,
        'V100': 3.06,
        'T4': 0.526,
        'L4': 1.30,
        'H100': 68.00,         # ND H100 v5
        'default': 3.25,
    }
}

# Dumont Cloud pricing (competitive rates)
DUMONT_GPU_PRICING: Dict[str, float] = {
    'RTX 4090': 0.74,
    'RTX 4080': 0.60,
    'RTX 4070': 0.45,
    'RTX 3090': 0.50,
    'RTX 3080': 0.40,
    'RTX 3070': 0.32,
    'A100': 2.50,
    'A100-80GB': 3.00,
    'A10': 0.60,
    'A10G': 0.60,
    'V100': 0.50,
    'T4': 0.15,
    'L4': 0.30,
    'H100': 4.50,
    'default': 0.50,
}

# GPU VRAM specifications (GB)
GPU_VRAM_SPECS: Dict[str, int] = {
    'RTX 4090': 24,
    'RTX 4080': 16,
    'RTX 4070': 12,
    'RTX 3090': 24,
    'RTX 3080': 10,
    'RTX 3070': 8,
    'A100': 40,
    'A100-80GB': 80,
    'A10': 24,
    'A10G': 24,
    'V100': 16,
    'T4': 16,
    'L4': 24,
    'H100': 80,
}


class PricingService:
    """
    Service for managing and retrieving GPU pricing data across cloud providers.

    Provides methods to:
    - Get provider pricing for specific GPUs
    - Compare Dumont Cloud pricing with major providers
    - Calculate potential savings
    - Get all available pricing data
    """

    def __init__(self):
        """Initialize the pricing service with baseline pricing data."""
        self._provider_pricing = PROVIDER_GPU_PRICING.copy()
        self._dumont_pricing = DUMONT_GPU_PRICING.copy()
        self._gpu_vram = GPU_VRAM_SPECS.copy()
        self._last_updated = datetime.utcnow()
        self._supported_providers = ['AWS', 'GCP', 'AZURE']

    def get_provider_price(self, provider: str, gpu_type: str) -> float:
        """
        Get the hourly price for a GPU from a specific cloud provider.

        Args:
            provider: Cloud provider name (AWS, GCP, Azure)
            gpu_type: GPU model name (e.g., 'RTX 4090', 'A100')

        Returns:
            Hourly price in USD. Returns default price if GPU not found.
        """
        provider = provider.upper()
        provider_prices = self._provider_pricing.get(provider, self._provider_pricing['AWS'])

        # Try exact match first
        if gpu_type in provider_prices:
            return provider_prices[gpu_type]

        # Try case-insensitive partial match
        gpu_type_lower = gpu_type.lower()
        for gpu_key, price in provider_prices.items():
            if gpu_key == 'default':
                continue
            if gpu_key.lower() in gpu_type_lower or gpu_type_lower in gpu_key.lower():
                return price

        return provider_prices.get('default', 3.00)

    def get_dumont_price(self, gpu_type: str) -> float:
        """
        Get the Dumont Cloud hourly price for a GPU.

        Args:
            gpu_type: GPU model name

        Returns:
            Hourly price in USD
        """
        if gpu_type in self._dumont_pricing:
            return self._dumont_pricing[gpu_type]

        # Try partial match
        gpu_type_lower = gpu_type.lower()
        for gpu_key, price in self._dumont_pricing.items():
            if gpu_key == 'default':
                continue
            if gpu_key.lower() in gpu_type_lower or gpu_type_lower in gpu_key.lower():
                return price

        return self._dumont_pricing.get('default', 0.50)

    def get_all_provider_pricing(self, provider: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Get pricing data for all GPUs, optionally filtered by provider.

        Args:
            provider: Optional provider to filter by (AWS, GCP, Azure)

        Returns:
            Dictionary of provider -> gpu_type -> price mappings
        """
        if provider:
            provider = provider.upper()
            if provider in self._provider_pricing:
                return {provider: self._provider_pricing[provider]}
            return {}
        return self._provider_pricing.copy()

    def get_gpu_comparison(self, gpu_type: str) -> Dict[str, Any]:
        """
        Get a complete pricing comparison for a specific GPU.

        Args:
            gpu_type: GPU model name

        Returns:
            Dictionary with Dumont and all provider prices, plus savings percentages
        """
        dumont_price = self.get_dumont_price(gpu_type)
        vram = self._gpu_vram.get(gpu_type, 0)

        comparison = {
            'gpu_type': gpu_type,
            'vram_gb': vram,
            'dumont_hourly': dumont_price,
            'providers': {},
            'savings': {},
        }

        for provider in self._supported_providers:
            provider_price = self.get_provider_price(provider, gpu_type)
            savings = provider_price - dumont_price
            savings_pct = (savings / provider_price * 100) if provider_price > 0 else 0

            comparison['providers'][provider] = provider_price
            comparison['savings'][provider] = {
                'amount': round(savings, 2),
                'percentage': round(savings_pct, 1),
            }

        return comparison

    def calculate_savings(
        self,
        gpu_type: str,
        hours: float,
        provider: str = 'AWS',
        dumont_cost: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate cost savings for using Dumont Cloud vs a cloud provider.

        Args:
            gpu_type: GPU model name
            hours: Number of hours of usage
            provider: Cloud provider for comparison (default: AWS)
            dumont_cost: Optional actual Dumont cost (if different from base rate)

        Returns:
            Dictionary with detailed savings breakdown
        """
        provider = provider.upper()
        provider_hourly = self.get_provider_price(provider, gpu_type)
        dumont_hourly = self.get_dumont_price(gpu_type)

        provider_cost = provider_hourly * hours
        actual_dumont_cost = dumont_cost if dumont_cost is not None else (dumont_hourly * hours)

        savings = provider_cost - actual_dumont_cost
        savings_pct = (savings / provider_cost * 100) if provider_cost > 0 else 0

        return {
            'gpu_type': gpu_type,
            'hours': round(hours, 2),
            'provider': provider,
            'dumont_hourly': dumont_hourly,
            'provider_hourly': provider_hourly,
            'dumont_cost': round(actual_dumont_cost, 2),
            'provider_cost': round(provider_cost, 2),
            'savings': round(savings, 2),
            'savings_percentage': round(savings_pct, 1),
        }

    def get_supported_gpus(self) -> List[str]:
        """
        Get list of all supported GPU types.

        Returns:
            List of GPU model names
        """
        gpus = set()
        for provider_prices in self._provider_pricing.values():
            gpus.update(k for k in provider_prices.keys() if k != 'default')
        gpus.update(k for k in self._dumont_pricing.keys() if k != 'default')
        return sorted(list(gpus))

    def get_supported_providers(self) -> List[str]:
        """
        Get list of supported cloud providers.

        Returns:
            List of provider names
        """
        return self._supported_providers.copy()

    def get_pricing_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the pricing service.

        Returns:
            Dictionary with service metadata
        """
        return {
            'currency': 'USD',
            'unit': 'per_hour',
            'supported_providers': self._supported_providers,
            'supported_gpus': self.get_supported_gpus(),
            'last_updated': self._last_updated.isoformat(),
        }

    def project_savings(
        self,
        gpu_type: str,
        daily_hours: float = 8,
        provider: str = 'AWS'
    ) -> Dict[str, Any]:
        """
        Project savings over monthly and yearly timeframes.

        Args:
            gpu_type: GPU model name
            daily_hours: Average hours used per day (default: 8)
            provider: Cloud provider for comparison

        Returns:
            Dictionary with projected savings
        """
        hourly_savings = self.get_provider_price(provider, gpu_type) - self.get_dumont_price(gpu_type)

        daily_savings = hourly_savings * daily_hours
        monthly_savings = daily_savings * 30
        yearly_savings = daily_savings * 365

        return {
            'gpu_type': gpu_type,
            'provider': provider,
            'daily_hours': daily_hours,
            'hourly_savings': round(hourly_savings, 2),
            'projections': {
                'daily': round(daily_savings, 2),
                'monthly': round(monthly_savings, 2),
                'yearly': round(yearly_savings, 2),
            }
        }


# Singleton instance for convenience
_pricing_service_instance: Optional[PricingService] = None


def get_pricing_service() -> PricingService:
    """
    Get the singleton pricing service instance.

    Returns:
        PricingService instance
    """
    global _pricing_service_instance
    if _pricing_service_instance is None:
        _pricing_service_instance = PricingService()
    return _pricing_service_instance

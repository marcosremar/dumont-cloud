"""
RegionService for Multi-Region GPU Instance Management.

This service provides a unified API for region operations including:
- Listing available regions with GPU offers
- Getting regional pricing information
- Checking region availability
- Suggesting regions based on user location
- Compliance tagging for GDPR/data residency

It wraps the VastService and RegionMapper to provide a cohesive region API.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .gpu.vast import VastService
from .region_mapper import RegionMapper, ParsedGeolocation, get_region_mapper
from .geolocation_service import get_user_location, UserLocation

logger = logging.getLogger(__name__)


class RegionService:
    """
    Service for region operations.

    Provides methods for listing regions, getting pricing, checking availability,
    and suggesting regions based on user location. Wraps VastService for API
    calls and RegionMapper for geolocation parsing.
    """

    # Cache TTLs in seconds
    REGIONS_CACHE_TTL = 3600  # 1 hour for region list
    PRICING_CACHE_TTL = 21600  # 6 hours for pricing data

    def __init__(self, api_key: str):
        """
        Initialize the RegionService.

        Args:
            api_key: Vast.ai API key for authenticated requests
        """
        self.api_key = api_key
        self.vast_service = VastService(api_key)
        self.region_mapper = get_region_mapper()
        self._region_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    def _is_cache_valid(self, cache_key: str, ttl: int) -> bool:
        """
        Check if a cached entry is still valid.

        Args:
            cache_key: Key for the cached data
            ttl: Time-to-live in seconds

        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self._cache_timestamps:
            return False

        cached_at = self._cache_timestamps[cache_key]
        elapsed = (datetime.utcnow() - cached_at).total_seconds()
        return elapsed < ttl

    def _get_cached(self, cache_key: str, ttl: int) -> Optional[Any]:
        """
        Get data from cache if valid.

        Args:
            cache_key: Key for the cached data
            ttl: Time-to-live in seconds

        Returns:
            Cached data or None if not found/expired
        """
        if self._is_cache_valid(cache_key, ttl):
            return self._region_cache.get(cache_key)
        return None

    def _set_cached(self, cache_key: str, data: Any) -> None:
        """
        Store data in cache.

        Args:
            cache_key: Key for the cached data
            data: Data to cache
        """
        self._region_cache[cache_key] = data
        self._cache_timestamps[cache_key] = datetime.utcnow()

    def get_available_regions(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 10.0,
        min_reliability: float = 0.0,
        eu_only: bool = False,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get list of available regions with GPU offers.

        Args:
            gpu_name: Optional GPU name filter (e.g., "RTX 4090")
            max_price: Maximum price per hour filter
            min_reliability: Minimum reliability score (0.0 to 1.0)
            eu_only: If True, only return EU/GDPR-compliant regions
            use_cache: If True, use cached data when available

        Returns:
            List of region dictionaries with availability and pricing info.
            Each region contains:
            - region_id: Standardized region ID (e.g., "eu-de", "na-us-ca")
            - country_code: Two-letter country code
            - country_name: Full country name
            - continent_code: Continent code (EU, NA, AS, etc.)
            - continent_name: Full continent name
            - is_eu: Boolean for GDPR compliance
            - compliance_tags: List of compliance tags
            - offer_count: Number of available offers
            - min_price: Minimum GPU price per hour
            - max_price: Maximum GPU price per hour
            - avg_price: Average GPU price per hour
            - gpu_types: List of available GPU types
        """
        # Build cache key
        cache_key = f"regions:{gpu_name}:{max_price}:{min_reliability}:{eu_only}"

        # Check cache
        if use_cache:
            cached = self._get_cached(cache_key, self.REGIONS_CACHE_TTL)
            if cached is not None:
                logger.debug(f"Returning cached regions for key: {cache_key}")
                return cached

        try:
            # Fetch regions from VastService
            regions = self.vast_service.get_available_regions(
                gpu_name=gpu_name,
                max_price=max_price,
                min_reliability=min_reliability,
            )

            # Filter EU-only if requested
            if eu_only:
                regions = [r for r in regions if r.get("is_eu", False)]

            # Add metadata timestamp
            for region in regions:
                region["fetched_at"] = datetime.utcnow().isoformat()

            # Cache the results
            self._set_cached(cache_key, regions)

            logger.info(
                f"Fetched {len(regions)} regions "
                f"(gpu={gpu_name}, max_price={max_price}, eu_only={eu_only})"
            )
            return regions

        except Exception as e:
            logger.error(f"Failed to get available regions: {e}")
            return []

    def get_region_pricing(
        self,
        region_id: str,
        gpu_name: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get pricing information for a specific region.

        Args:
            region_id: Standardized region ID (e.g., "eu-de", "na-us-ca")
            gpu_name: Optional GPU name filter
            use_cache: If True, use cached data when available

        Returns:
            Pricing data dictionary containing:
            - region_id: The region ID
            - available: Boolean indicating if offers exist
            - currency: Currency code (USD)
            - offer_count: Number of offers found
            - compute_price: Dict with min, max, avg prices
            - by_gpu: List of pricing breakdown by GPU type
            - fetched_at: Timestamp of data fetch
            - error: Error message if unavailable
        """
        cache_key = f"pricing:{region_id}:{gpu_name}"

        # Check cache
        if use_cache:
            cached = self._get_cached(cache_key, self.PRICING_CACHE_TTL)
            if cached is not None:
                logger.debug(f"Returning cached pricing for region: {region_id}")
                return cached

        try:
            # Fetch pricing from VastService
            pricing = self.vast_service.get_pricing_for_region(
                region_id=region_id,
                gpu_name=gpu_name,
            )

            # Add metadata timestamp
            pricing["fetched_at"] = datetime.utcnow().isoformat()

            # Cache the results
            self._set_cached(cache_key, pricing)

            logger.info(f"Fetched pricing for region {region_id}")
            return pricing

        except Exception as e:
            logger.error(f"Failed to get pricing for region {region_id}: {e}")
            return {
                "region_id": region_id,
                "available": False,
                "error": str(e),
            }

    def check_region_availability(
        self,
        region_id: str,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        max_price: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Check if a specific GPU is available in a region.

        Args:
            region_id: Standardized region ID
            gpu_name: GPU name to check (e.g., "RTX 4090")
            num_gpus: Number of GPUs required
            max_price: Maximum acceptable price per hour

        Returns:
            Availability information containing:
            - region_id: The region ID
            - available: Boolean indicating availability
            - offer_count: Number of matching offers
            - cheapest_price: Lowest price if available
            - gpu_name: The requested GPU name
            - checked_at: Timestamp of check
        """
        try:
            offers = self.vast_service.search_offers_by_region_id(
                region_id=region_id,
                gpu_name=gpu_name,
                num_gpus=num_gpus,
                max_price=max_price,
                limit=10,
            )

            cheapest = min(
                (o.get("dph_total", float("inf")) for o in offers),
                default=None,
            )

            return {
                "region_id": region_id,
                "available": len(offers) > 0,
                "offer_count": len(offers),
                "cheapest_price": cheapest,
                "gpu_name": gpu_name,
                "checked_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to check availability for region {region_id}: {e}")
            return {
                "region_id": region_id,
                "available": False,
                "offer_count": 0,
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat(),
            }

    def get_region_metadata(self, region_id: str) -> Optional[Dict[str, Any]]:
        """
        Get static metadata for a region.

        Args:
            region_id: Standardized region ID

        Returns:
            Region metadata dictionary or None if not found.
            Contains:
            - region_id: The region ID
            - country_code: Two-letter country code
            - country_name: Full country name
            - continent_code: Continent code
            - continent_name: Full continent name
            - is_eu: Boolean for GDPR compliance
            - compliance_tags: List of compliance tags
        """
        all_regions = self.region_mapper.get_all_regions()
        return all_regions.get(region_id)

    def get_all_known_regions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all known regions with their metadata.

        This returns the full list of regions that RegionMapper knows about,
        not filtered by current availability.

        Returns:
            Dictionary mapping region_id to region metadata
        """
        return self.region_mapper.get_all_regions()

    def suggest_regions_for_user(
        self,
        user_ip: Optional[str] = None,
        require_eu: bool = False,
        gpu_name: Optional[str] = None,
        max_price: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Suggest regions for a user based on their location.

        Args:
            user_ip: User's IP address for geolocation
            require_eu: If True, only suggest EU regions
            gpu_name: Optional GPU name filter
            max_price: Maximum price per hour

        Returns:
            List of suggested regions, ordered by preference.
            Each region includes availability and pricing info.
        """
        suggested_region_ids = []

        # Get user location if IP provided
        if user_ip:
            try:
                user_location = get_user_location(user_ip)
                if user_location and user_location.suggested_regions:
                    suggested_region_ids = user_location.suggested_regions
                    logger.info(
                        f"User location: {user_location.city}, {user_location.country} "
                        f"-> Suggested regions: {suggested_region_ids}"
                    )
            except Exception as e:
                logger.warning(f"Failed to get user location: {e}")

        # Get available regions
        available_regions = self.get_available_regions(
            gpu_name=gpu_name,
            max_price=max_price,
            eu_only=require_eu,
        )

        if not available_regions:
            return []

        # Build a lookup map
        region_map = {r["region_id"]: r for r in available_regions}

        # Order by suggestion priority
        result = []
        seen = set()

        # First, add suggested regions in order
        for region_id in suggested_region_ids:
            if region_id in region_map and region_id not in seen:
                region = region_map[region_id]
                region["suggested"] = True
                region["suggestion_rank"] = len(result) + 1
                result.append(region)
                seen.add(region_id)

        # Then add remaining regions by offer count
        remaining = [
            r for r in available_regions
            if r["region_id"] not in seen
        ]
        remaining.sort(key=lambda r: r.get("offer_count", 0), reverse=True)

        for region in remaining:
            region["suggested"] = False
            result.append(region)

        return result

    def get_eu_regions(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Get all available EU/GDPR-compliant regions.

        Convenience method for GDPR compliance filtering.

        Args:
            gpu_name: Optional GPU name filter
            max_price: Maximum price per hour

        Returns:
            List of EU regions with availability and pricing info
        """
        return self.get_available_regions(
            gpu_name=gpu_name,
            max_price=max_price,
            eu_only=True,
        )

    def get_compliance_info(self, region_id: str) -> Dict[str, Any]:
        """
        Get compliance information for a region.

        Args:
            region_id: Standardized region ID

        Returns:
            Compliance information dictionary containing:
            - region_id: The region ID
            - is_eu: Boolean for EU membership
            - is_gdpr_compliant: Boolean for GDPR compliance
            - compliance_tags: List of applicable compliance tags
            - data_residency: Data residency information
        """
        metadata = self.get_region_metadata(region_id)

        if not metadata:
            return {
                "region_id": region_id,
                "is_eu": False,
                "is_gdpr_compliant": False,
                "compliance_tags": [],
                "data_residency": "unknown",
            }

        is_eu = metadata.get("is_eu", False)
        compliance_tags = metadata.get("compliance_tags", [])

        return {
            "region_id": region_id,
            "is_eu": is_eu,
            "is_gdpr_compliant": is_eu or "GDPR" in compliance_tags,
            "compliance_tags": compliance_tags,
            "data_residency": "EU" if is_eu else metadata.get("continent_name", "unknown"),
        }

    def parse_geolocation(self, geolocation: str) -> Optional[ParsedGeolocation]:
        """
        Parse a Vast.ai geolocation string into structured data.

        Args:
            geolocation: Raw geolocation string from Vast.ai

        Returns:
            ParsedGeolocation object or None if parsing fails
        """
        return self.region_mapper.parse_geolocation(geolocation)

    def clear_cache(self) -> int:
        """
        Clear all cached region data.

        Returns:
            Number of cache entries cleared
        """
        count = len(self._region_cache)
        self._region_cache = {}
        self._cache_timestamps = {}
        logger.info(f"Cleared {count} region cache entries")
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache stats
        """
        now = datetime.utcnow()
        valid_region_entries = sum(
            1 for key, ts in self._cache_timestamps.items()
            if key.startswith("regions:") and
            (now - ts).total_seconds() < self.REGIONS_CACHE_TTL
        )
        valid_pricing_entries = sum(
            1 for key, ts in self._cache_timestamps.items()
            if key.startswith("pricing:") and
            (now - ts).total_seconds() < self.PRICING_CACHE_TTL
        )

        return {
            "total_entries": len(self._region_cache),
            "valid_region_entries": valid_region_entries,
            "valid_pricing_entries": valid_pricing_entries,
            "regions_cache_ttl": self.REGIONS_CACHE_TTL,
            "pricing_cache_ttl": self.PRICING_CACHE_TTL,
        }

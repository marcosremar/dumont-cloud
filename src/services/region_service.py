"""
RegionService for Multi-Region GPU Instance Management.

This service provides a unified API for region operations including:
- Listing available regions with GPU offers
- Getting regional pricing information
- Checking region availability
- Suggesting regions based on user location
- Compliance tagging for GDPR/data residency
- Multi-region failover for instance provisioning

It wraps the VastService and RegionMapper to provide a cohesive region API.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from .gpu.vast import VastService
from .region_mapper import RegionMapper, ParsedGeolocation, get_region_mapper
from .geolocation_service import get_user_location, UserLocation

logger = logging.getLogger(__name__)


class ProvisioningPhase(str, Enum):
    """Current phase of multi-region provisioning"""
    IDLE = "idle"
    PRIMARY_REGION_CHECK = "primary_region_check"
    PRIMARY_REGION_PROVISION = "primary_region_provision"
    FALLBACK_REGION_CHECK = "fallback_region_check"
    FALLBACK_REGION_PROVISION = "fallback_region_provision"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RegionalProvisioningResult:
    """
    Result of a multi-region provisioning attempt.

    Follows the pattern from OrchestratedFailoverResult in failover_orchestrator.py.
    """
    success: bool
    provisioning_id: str

    # Region info
    primary_region: str
    attempted_regions: List[str] = field(default_factory=list)
    successful_region: Optional[str] = None
    fallback_regions: List[str] = field(default_factory=list)

    # Selected offer info
    offer_id: Optional[int] = None
    offer_details: Optional[Dict[str, Any]] = None
    gpu_name: Optional[str] = None
    price_per_hour: Optional[float] = None

    # Timing (milliseconds)
    primary_attempt_ms: int = 0
    fallback_attempts_ms: Dict[str, int] = field(default_factory=dict)
    total_ms: int = 0

    # Error info
    error: Optional[str] = None
    region_errors: Dict[str, str] = field(default_factory=dict)

    # Phase tracking
    phase_history: List[tuple] = field(default_factory=list)
    current_phase: ProvisioningPhase = ProvisioningPhase.IDLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "provisioning_id": self.provisioning_id,
            "primary_region": self.primary_region,
            "attempted_regions": self.attempted_regions,
            "successful_region": self.successful_region,
            "fallback_regions": self.fallback_regions,
            "offer_id": self.offer_id,
            "offer_details": self.offer_details,
            "gpu_name": self.gpu_name,
            "price_per_hour": self.price_per_hour,
            "timing": {
                "primary_attempt_ms": self.primary_attempt_ms,
                "fallback_attempts_ms": self.fallback_attempts_ms,
                "total_ms": self.total_ms,
            },
            "error": self.error,
            "region_errors": self.region_errors,
            "current_phase": self.current_phase.value,
            "phase_history": [
                {"phase": phase, "timestamp": ts}
                for phase, ts in self.phase_history
            ],
        }


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

    def find_best_offer_in_region(
        self,
        region_id: str,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        max_price: float = 10.0,
        min_reliability: float = 0.90,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best GPU offer in a specific region.

        Follows the pattern from find_gpu_in_region in regional_volume_failover.py.

        Args:
            region_id: Standardized region ID (e.g., "eu-de", "na-us-ca")
            gpu_name: Optional GPU name filter
            num_gpus: Required number of GPUs
            max_price: Maximum price per hour
            min_reliability: Minimum reliability score

        Returns:
            Best matching offer or None if no offers found
        """
        try:
            offers = self.vast_service.search_offers_by_region_id(
                region_id=region_id,
                gpu_name=gpu_name,
                num_gpus=num_gpus,
                max_price=max_price,
                limit=20,
            )

            if not offers:
                logger.debug(f"No offers found in region {region_id}")
                return None

            # Filter by reliability
            reliable_offers = [
                o for o in offers
                if o.get("reliability2", 0) >= min_reliability
            ]

            if not reliable_offers:
                # Fall back to all offers if none meet reliability threshold
                logger.debug(
                    f"No offers meet reliability threshold {min_reliability} "
                    f"in region {region_id}, using all offers"
                )
                reliable_offers = offers

            # Sort by reliability (desc) then price (asc)
            reliable_offers.sort(
                key=lambda o: (
                    -o.get("reliability2", 0),
                    o.get("dph_total", float("inf")),
                )
            )

            best = reliable_offers[0]
            logger.info(
                f"Found best offer in {region_id}: "
                f"GPU={best.get('gpu_name', 'Unknown')}, "
                f"price=${best.get('dph_total', 0):.3f}/hr, "
                f"reliability={best.get('reliability2', 0):.2f}"
            )
            return best

        except Exception as e:
            logger.error(f"Failed to find offer in region {region_id}: {e}")
            return None

    def provision_with_regional_failover(
        self,
        primary_region: str,
        fallback_regions: Optional[List[str]] = None,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        max_price: float = 2.0,
        min_reliability: float = 0.90,
        provisioning_id: Optional[str] = None,
    ) -> RegionalProvisioningResult:
        """
        Find the best GPU offer with multi-region failover support.

        This method attempts to find an offer in the primary region first,
        then falls back to configured fallback regions if primary is unavailable.
        Follows the pattern from execute_failover in failover_orchestrator.py.

        Args:
            primary_region: Primary region ID to try first
            fallback_regions: List of fallback region IDs to try in order
            gpu_name: Optional GPU name filter (e.g., "RTX 4090")
            num_gpus: Number of GPUs required
            max_price: Maximum price per hour
            min_reliability: Minimum reliability score (0.0 to 1.0)
            provisioning_id: Optional unique ID for tracking

        Returns:
            RegionalProvisioningResult with the best offer or error details
        """
        import uuid

        start_time = time.time()

        if not provisioning_id:
            provisioning_id = f"prov-{uuid.uuid4().hex[:8]}"

        fallback_regions = fallback_regions or []

        logger.info(
            f"[{provisioning_id}] Starting multi-region provisioning: "
            f"primary={primary_region}, fallbacks={fallback_regions}"
        )

        result = RegionalProvisioningResult(
            success=False,
            provisioning_id=provisioning_id,
            primary_region=primary_region,
            fallback_regions=list(fallback_regions),
            current_phase=ProvisioningPhase.IDLE,
        )

        # Track phase history
        result.phase_history.append(("start", time.time()))

        # ============================================================
        # PHASE 1: Try Primary Region
        # ============================================================
        result.current_phase = ProvisioningPhase.PRIMARY_REGION_CHECK
        result.phase_history.append((ProvisioningPhase.PRIMARY_REGION_CHECK.value, time.time()))
        result.attempted_regions.append(primary_region)

        logger.info(f"[{provisioning_id}] Checking primary region: {primary_region}")

        primary_start = time.time()
        primary_offer = self.find_best_offer_in_region(
            region_id=primary_region,
            gpu_name=gpu_name,
            num_gpus=num_gpus,
            max_price=max_price,
            min_reliability=min_reliability,
        )
        result.primary_attempt_ms = int((time.time() - primary_start) * 1000)

        if primary_offer:
            logger.info(
                f"[{provisioning_id}] Found offer in primary region {primary_region} "
                f"in {result.primary_attempt_ms}ms"
            )
            result.success = True
            result.successful_region = primary_region
            result.offer_id = primary_offer.get("id")
            result.offer_details = primary_offer
            result.gpu_name = primary_offer.get("gpu_name")
            result.price_per_hour = primary_offer.get("dph_total")
            result.current_phase = ProvisioningPhase.COMPLETED
            result.phase_history.append((ProvisioningPhase.COMPLETED.value, time.time()))
            result.total_ms = int((time.time() - start_time) * 1000)
            return result

        # Primary region failed
        result.region_errors[primary_region] = "No suitable offers found"
        logger.warning(
            f"[{provisioning_id}] Primary region {primary_region} unavailable, "
            "attempting fallbacks..."
        )

        # ============================================================
        # PHASE 2: Try Fallback Regions
        # ============================================================
        if not fallback_regions:
            result.error = f"No offers in primary region {primary_region} and no fallbacks configured"
            result.current_phase = ProvisioningPhase.FAILED
            result.phase_history.append((ProvisioningPhase.FAILED.value, time.time()))
            result.total_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{provisioning_id}] {result.error}")
            return result

        result.current_phase = ProvisioningPhase.FALLBACK_REGION_CHECK
        result.phase_history.append((ProvisioningPhase.FALLBACK_REGION_CHECK.value, time.time()))

        for fallback_region in fallback_regions:
            logger.info(f"[{provisioning_id}] Trying fallback region: {fallback_region}")
            result.attempted_regions.append(fallback_region)

            fallback_start = time.time()
            fallback_offer = self.find_best_offer_in_region(
                region_id=fallback_region,
                gpu_name=gpu_name,
                num_gpus=num_gpus,
                max_price=max_price,
                min_reliability=min_reliability,
            )
            fallback_ms = int((time.time() - fallback_start) * 1000)
            result.fallback_attempts_ms[fallback_region] = fallback_ms

            if fallback_offer:
                logger.info(
                    f"[{provisioning_id}] Found offer in fallback region {fallback_region} "
                    f"in {fallback_ms}ms"
                )
                result.success = True
                result.successful_region = fallback_region
                result.offer_id = fallback_offer.get("id")
                result.offer_details = fallback_offer
                result.gpu_name = fallback_offer.get("gpu_name")
                result.price_per_hour = fallback_offer.get("dph_total")
                result.current_phase = ProvisioningPhase.COMPLETED
                result.phase_history.append((ProvisioningPhase.COMPLETED.value, time.time()))
                result.total_ms = int((time.time() - start_time) * 1000)
                return result

            # Fallback region failed
            result.region_errors[fallback_region] = "No suitable offers found"
            logger.warning(
                f"[{provisioning_id}] Fallback region {fallback_region} unavailable"
            )

        # ============================================================
        # FAILURE: All regions exhausted
        # ============================================================
        result.current_phase = ProvisioningPhase.FAILED
        result.phase_history.append((ProvisioningPhase.FAILED.value, time.time()))
        result.total_ms = int((time.time() - start_time) * 1000)

        result.error = (
            f"No suitable offers found in any region. "
            f"Tried: {result.attempted_regions}. "
            f"Errors: {result.region_errors}"
        )

        logger.error(f"[{provisioning_id}] All regions exhausted: {result.error}")
        return result

    def get_fallback_regions_for_primary(
        self,
        primary_region: str,
        max_fallbacks: int = 3,
    ) -> List[str]:
        """
        Suggest fallback regions for a primary region based on proximity.

        Args:
            primary_region: The primary region ID
            max_fallbacks: Maximum number of fallback regions to suggest

        Returns:
            List of suggested fallback region IDs
        """
        # Define region proximity mappings
        region_proximity = {
            # North America
            "na-us-ca": ["na-us-tx", "na-us-ny", "na-ca"],
            "na-us-tx": ["na-us-ca", "na-us-ny", "na-ca"],
            "na-us-ny": ["na-us-tx", "na-us-ca", "na-ca", "eu-gb"],
            "na-ca": ["na-us-ny", "na-us-ca", "na-us-tx"],
            # Europe
            "eu-de": ["eu-nl", "eu-fr", "eu-pl", "eu-gb"],
            "eu-gb": ["eu-nl", "eu-de", "eu-fr", "na-us-ny"],
            "eu-fr": ["eu-de", "eu-nl", "eu-es", "eu-gb"],
            "eu-nl": ["eu-de", "eu-gb", "eu-fr", "eu-be"],
            "eu-pl": ["eu-de", "eu-cz", "eu-at", "eu-nl"],
            "eu-se": ["eu-no", "eu-fi", "eu-de", "eu-dk"],
            "eu-no": ["eu-se", "eu-fi", "eu-dk", "eu-de"],
            "eu-es": ["eu-fr", "eu-pt", "eu-de", "eu-it"],
            "eu-it": ["eu-de", "eu-at", "eu-fr", "eu-ch"],
            # Asia Pacific
            "ap-jp": ["ap-kr", "ap-tw", "ap-hk", "ap-sg"],
            "ap-sg": ["ap-hk", "ap-jp", "ap-au", "ap-in"],
            "ap-au": ["ap-sg", "ap-nz", "ap-jp", "ap-hk"],
            "ap-in": ["ap-sg", "ap-ae", "ap-hk", "eu-gb"],
            "ap-hk": ["ap-tw", "ap-jp", "ap-sg", "ap-kr"],
            "ap-kr": ["ap-jp", "ap-tw", "ap-hk", "ap-cn"],
        }

        fallbacks = region_proximity.get(primary_region, [])[:max_fallbacks]

        if not fallbacks:
            # If no specific mapping, suggest popular regions
            default_fallbacks = ["na-us-ca", "eu-de", "ap-sg"]
            fallbacks = [r for r in default_fallbacks if r != primary_region][:max_fallbacks]

        logger.debug(f"Suggested fallbacks for {primary_region}: {fallbacks}")
        return fallbacks

"""
Redis caching utilities for region data.

Provides a RegionCache class for caching region-related data with TTL support.
Used across the multi-region instance management system for performance optimization.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RegionCache:
    """
    Redis-backed cache for region data with TTL support.

    Provides methods for caching region pricing, availability, and metadata.
    Falls back to in-memory caching if Redis is unavailable.
    """

    # Default TTLs in seconds
    DEFAULT_TTL = 3600  # 1 hour
    REGIONS_TTL = 3600  # 1 hour for region list
    PRICING_TTL = 21600  # 6 hours for pricing data
    AVAILABILITY_TTL = 300  # 5 minutes for availability checks

    # Cache key prefixes
    PREFIX_REGION = "region:"
    PREFIX_PRICING = "pricing:"
    PREFIX_AVAILABILITY = "availability:"
    PREFIX_METADATA = "metadata:"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = DEFAULT_TTL,
        key_prefix: str = "dumont:region_cache:",
    ):
        """
        Initialize the RegionCache.

        Args:
            redis_url: Redis connection URL. If None, uses REDIS_URL env var.
            default_ttl: Default TTL in seconds for cached entries.
            key_prefix: Prefix for all cache keys to avoid collisions.
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._redis_client: Optional[Any] = None
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._use_fallback = False

        self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not installed, using in-memory fallback cache")
            self._use_fallback = True
            return

        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            self._redis_client.ping()
            logger.info(f"Connected to Redis at {self._mask_url(self.redis_url)}")
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._use_fallback = True
            self._redis_client = None
        except Exception as e:
            logger.warning(f"Unexpected error connecting to Redis: {e}. Using in-memory fallback.")
            self._use_fallback = True
            self._redis_client = None

    def _mask_url(self, url: str) -> str:
        """Mask password in Redis URL for logging."""
        if "@" in url:
            parts = url.split("@")
            return f"redis://***@{parts[-1]}"
        return url

    def _make_key(self, key: str) -> str:
        """Generate full cache key with prefix."""
        return f"{self.key_prefix}{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            Cached value or None if not found/expired
        """
        full_key = self._make_key(key)

        if self._use_fallback:
            entry = self._fallback_cache.get(full_key)
            if entry:
                if datetime.utcnow().timestamp() < entry.get("expires_at", 0):
                    return entry.get("value")
                else:
                    del self._fallback_cache[full_key]
            return None

        try:
            value = self._redis_client.get(full_key)
            if value is not None:
                return self._deserialize(value)
            return None
        except redis.RedisError as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in the cache with TTL.

        Args:
            key: Cache key (without prefix)
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (uses default_ttl if not specified)

        Returns:
            True if successful, False otherwise
        """
        full_key = self._make_key(key)
        ttl = ttl if ttl is not None else self.default_ttl

        if self._use_fallback:
            self._fallback_cache[full_key] = {
                "value": value,
                "expires_at": datetime.utcnow().timestamp() + ttl,
                "cached_at": datetime.utcnow().isoformat(),
            }
            return True

        try:
            serialized = self._serialize(value)
            self._redis_client.setex(full_key, ttl, serialized)
            return True
        except redis.RedisError as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            True if successful, False otherwise
        """
        full_key = self._make_key(key)

        if self._use_fallback:
            if full_key in self._fallback_cache:
                del self._fallback_cache[full_key]
            return True

        try:
            self._redis_client.delete(full_key)
            return True
        except redis.RedisError as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key (without prefix)

        Returns:
            True if key exists and is not expired, False otherwise
        """
        full_key = self._make_key(key)

        if self._use_fallback:
            entry = self._fallback_cache.get(full_key)
            if entry:
                if datetime.utcnow().timestamp() < entry.get("expires_at", 0):
                    return True
                else:
                    del self._fallback_cache[full_key]
            return False

        try:
            return bool(self._redis_client.exists(full_key))
        except redis.RedisError as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key (without prefix)

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        full_key = self._make_key(key)

        if self._use_fallback:
            entry = self._fallback_cache.get(full_key)
            if entry:
                remaining = entry.get("expires_at", 0) - datetime.utcnow().timestamp()
                return max(0, int(remaining))
            return -2

        try:
            return self._redis_client.ttl(full_key)
        except redis.RedisError as e:
            logger.error(f"Redis ttl error for key {key}: {e}")
            return -2

    # Convenience methods for region-specific caching

    def cache_region(
        self,
        region_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache region data.

        Args:
            region_id: Region ID (e.g., "eu-de", "na-us-ca")
            data: Region data to cache
            ttl: TTL in seconds (uses REGIONS_TTL if not specified)

        Returns:
            True if successful
        """
        key = f"{self.PREFIX_REGION}{region_id}"
        return self.set(key, data, ttl or self.REGIONS_TTL)

    def get_region(self, region_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached region data.

        Args:
            region_id: Region ID

        Returns:
            Cached region data or None
        """
        key = f"{self.PREFIX_REGION}{region_id}"
        return self.get(key)

    def cache_pricing(
        self,
        region_id: str,
        gpu_name: Optional[str],
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache pricing data for a region.

        Args:
            region_id: Region ID
            gpu_name: GPU name filter (can be None for all GPUs)
            data: Pricing data to cache
            ttl: TTL in seconds (uses PRICING_TTL if not specified)

        Returns:
            True if successful
        """
        gpu_key = gpu_name or "all"
        key = f"{self.PREFIX_PRICING}{region_id}:{gpu_key}"
        return self.set(key, data, ttl or self.PRICING_TTL)

    def get_pricing(
        self,
        region_id: str,
        gpu_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached pricing data.

        Args:
            region_id: Region ID
            gpu_name: GPU name filter

        Returns:
            Cached pricing data or None
        """
        gpu_key = gpu_name or "all"
        key = f"{self.PREFIX_PRICING}{region_id}:{gpu_key}"
        return self.get(key)

    def cache_availability(
        self,
        region_id: str,
        gpu_name: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache availability check result.

        Args:
            region_id: Region ID
            gpu_name: GPU name
            data: Availability data to cache
            ttl: TTL in seconds (uses AVAILABILITY_TTL if not specified)

        Returns:
            True if successful
        """
        key = f"{self.PREFIX_AVAILABILITY}{region_id}:{gpu_name}"
        return self.set(key, data, ttl or self.AVAILABILITY_TTL)

    def get_availability(
        self,
        region_id: str,
        gpu_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached availability data.

        Args:
            region_id: Region ID
            gpu_name: GPU name

        Returns:
            Cached availability data or None
        """
        key = f"{self.PREFIX_AVAILABILITY}{region_id}:{gpu_name}"
        return self.get(key)

    def clear_region_cache(self, region_id: Optional[str] = None) -> int:
        """
        Clear region cache entries.

        Args:
            region_id: Optional region ID. If None, clears all regions.

        Returns:
            Number of entries cleared
        """
        if region_id:
            pattern = f"{self.key_prefix}{self.PREFIX_REGION}{region_id}"
        else:
            pattern = f"{self.key_prefix}{self.PREFIX_REGION}*"

        return self._clear_pattern(pattern)

    def clear_pricing_cache(self, region_id: Optional[str] = None) -> int:
        """
        Clear pricing cache entries.

        Args:
            region_id: Optional region ID. If None, clears all pricing.

        Returns:
            Number of entries cleared
        """
        if region_id:
            pattern = f"{self.key_prefix}{self.PREFIX_PRICING}{region_id}:*"
        else:
            pattern = f"{self.key_prefix}{self.PREFIX_PRICING}*"

        return self._clear_pattern(pattern)

    def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        pattern = f"{self.key_prefix}*"
        return self._clear_pattern(pattern)

    def _clear_pattern(self, pattern: str) -> int:
        """
        Clear cache entries matching a pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            Number of entries cleared
        """
        if self._use_fallback:
            to_delete = [k for k in self._fallback_cache.keys() if k.startswith(pattern.rstrip("*"))]
            for key in to_delete:
                del self._fallback_cache[key]
            return len(to_delete)

        try:
            keys = list(self._redis_client.scan_iter(match=pattern, count=100))
            if keys:
                self._redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries matching {pattern}")
            return len(keys)
        except redis.RedisError as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats including:
            - backend: "redis" or "memory"
            - connected: Boolean
            - total_keys: Number of cached entries
            - memory_used: Memory usage (Redis only)
        """
        stats = {
            "backend": "memory" if self._use_fallback else "redis",
            "connected": not self._use_fallback,
            "key_prefix": self.key_prefix,
            "default_ttl": self.default_ttl,
        }

        if self._use_fallback:
            # Clean expired entries
            now = datetime.utcnow().timestamp()
            expired = [k for k, v in self._fallback_cache.items() if v.get("expires_at", 0) < now]
            for key in expired:
                del self._fallback_cache[key]

            stats["total_keys"] = len(self._fallback_cache)
            stats["memory_used"] = "N/A (in-memory)"
        else:
            try:
                pattern = f"{self.key_prefix}*"
                keys = list(self._redis_client.scan_iter(match=pattern, count=1000))
                stats["total_keys"] = len(keys)

                info = self._redis_client.info("memory")
                stats["memory_used"] = info.get("used_memory_human", "unknown")
            except redis.RedisError as e:
                logger.error(f"Redis stats error: {e}")
                stats["total_keys"] = -1
                stats["error"] = str(e)

        return stats

    def health_check(self) -> Dict[str, Any]:
        """
        Check cache health.

        Returns:
            Health check result with status and latency
        """
        import time

        result = {
            "healthy": False,
            "backend": "memory" if self._use_fallback else "redis",
            "latency_ms": 0,
        }

        start = time.time()

        try:
            test_key = "_health_check"
            test_value = {"timestamp": datetime.utcnow().isoformat()}

            self.set(test_key, test_value, ttl=60)
            retrieved = self.get(test_key)
            self.delete(test_key)

            result["healthy"] = retrieved is not None
            result["latency_ms"] = round((time.time() - start) * 1000, 2)

        except Exception as e:
            result["error"] = str(e)
            result["latency_ms"] = round((time.time() - start) * 1000, 2)

        return result

    def close(self) -> None:
        """Close Redis connection."""
        if self._redis_client:
            try:
                self._redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
        self._redis_client = None
        self._fallback_cache = {}


# Singleton instance
_region_cache: Optional[RegionCache] = None


def get_region_cache() -> RegionCache:
    """
    Get the singleton RegionCache instance.

    Returns:
        RegionCache instance
    """
    global _region_cache
    if _region_cache is None:
        _region_cache = RegionCache()
    return _region_cache


def clear_region_cache_singleton() -> None:
    """Clear the singleton RegionCache instance."""
    global _region_cache
    if _region_cache:
        _region_cache.close()
    _region_cache = None

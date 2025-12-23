"""
Circuit Breaker pattern implementation for the Dumont SDK.

Provides resilience by preventing cascading failures when services are unhealthy.
Implements the standard three-state circuit breaker:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is unhealthy, requests fail fast
- HALF_OPEN: Testing if service recovered

Usage:
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

    async with breaker:
        result = await make_request()

    # Or with decorator
    @breaker
    async def make_request():
        ...
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Any, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, breaker_name: str, time_until_retry: float):
        self.breaker_name = breaker_name
        self.time_until_retry = time_until_retry
        super().__init__(
            f"Circuit breaker '{breaker_name}' is OPEN. "
            f"Retry in {time_until_retry:.1f}s"
        )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Thresholds
    failure_threshold: int = 5
    """Number of failures before opening the circuit"""

    success_threshold: int = 2
    """Number of successes in HALF_OPEN before closing"""

    # Timeouts
    recovery_timeout: float = 30.0
    """Seconds to wait before attempting recovery (OPEN -> HALF_OPEN)"""

    half_open_max_calls: int = 3
    """Max concurrent calls allowed in HALF_OPEN state"""

    # Exceptions to track
    expected_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    """Exceptions that count as failures"""

    excluded_exceptions: Tuple[Type[Exception], ...] = ()
    """Exceptions that don't count as failures (e.g., validation errors)"""

    # Identification
    name: str = "default"
    """Name for logging and identification"""


@dataclass
class CircuitBreakerStats:
    """Statistics about circuit breaker behavior."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change_time: Optional[float] = None


class CircuitBreaker:
    """
    Circuit Breaker implementation for resilience.

    Prevents cascading failures by failing fast when a service is unhealthy.

    Example:
        # Create breaker
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            name="api-client"
        )

        # Use as context manager
        async with breaker:
            response = await client.get("/api/endpoint")

        # Or as decorator
        @breaker
        async def fetch_data():
            return await client.get("/api/data")

        # Check state
        if breaker.is_open:
            logger.warning("Service is currently unavailable")
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        excluded_exceptions: Tuple[Type[Exception], ...] = (),
        name: str = "default",
    ):
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
            expected_exceptions=expected_exceptions,
            excluded_exceptions=excluded_exceptions,
            name=name,
        )
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        self.stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Current state of the circuit breaker."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """True if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """True if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """True if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    @property
    def time_until_retry(self) -> float:
        """Seconds until circuit will attempt recovery (0 if not open)."""
        if not self.is_open or self._last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        remaining = self.config.recovery_timeout - elapsed
        return max(0.0, remaining)

    async def _check_state(self) -> None:
        """Check if circuit should transition to HALF_OPEN."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    await self._transition_to(CircuitState.HALF_OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitState.OPEN:
            self._last_failure_time = time.monotonic()

        self.stats.state_changes += 1
        self.stats.last_state_change_time = time.monotonic()

        logger.info(
            f"Circuit breaker '{self.config.name}' transitioned: "
            f"{old_state.value} -> {new_state.value}"
        )

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.successful_calls += 1
            self.stats.last_success_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self, exc: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.failed_calls += 1
            self.stats.last_failure_time = time.monotonic()

            # Check if this exception should be excluded
            if isinstance(exc, self.config.excluded_exceptions):
                return

            # Check if this exception should count as failure
            if not isinstance(exc, self.config.expected_exceptions):
                return

            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open -> back to open
                await self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    async def _can_execute(self) -> bool:
        """Check if a call can be executed."""
        async with self._lock:
            await self._check_state()

            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                self.stats.rejected_calls += 1
                return False
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                self.stats.rejected_calls += 1
                return False

        return False

    async def __aenter__(self) -> "CircuitBreaker":
        """Enter async context manager."""
        if not await self._can_execute():
            raise CircuitBreakerError(
                self.config.name,
                self.time_until_retry
            )
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc_val: Optional[Exception],
        exc_tb: Any,
    ) -> bool:
        """Exit async context manager."""
        if exc_val is not None:
            await self._record_failure(exc_val)
        else:
            await self._record_success()
        return False  # Don't suppress exceptions

    def __call__(self, func: Callable) -> Callable:
        """Use circuit breaker as decorator."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with self:
                return await func(*args, **kwargs)
        return wrapper

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info(f"Circuit breaker '{self.config.name}' manually reset")

    def get_stats(self) -> dict:
        """Get current statistics as dictionary."""
        return {
            "name": self.config.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "rejected_calls": self.stats.rejected_calls,
            "state_changes": self.stats.state_changes,
            "time_until_retry": self.time_until_retry,
        }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Allows creating named circuit breakers and retrieving them by name.

    Example:
        registry = CircuitBreakerRegistry()

        # Get or create breaker
        api_breaker = registry.get("api-client", failure_threshold=5)
        db_breaker = registry.get("database", failure_threshold=3)

        # Use breakers
        async with api_breaker:
            await fetch_from_api()
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: float = 30.0,
        **kwargs: Any,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                recovery_timeout=recovery_timeout,
                **kwargs,
            )
        return self._breakers[name]

    def get_all_stats(self) -> dict[str, dict]:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()

    def remove(self, name: str) -> bool:
        """Remove a circuit breaker by name."""
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False


# Global registry for convenience
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    **kwargs: Any,
) -> CircuitBreaker:
    """Get or create a circuit breaker from the global registry."""
    return _global_registry.get(
        name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        **kwargs,
    )

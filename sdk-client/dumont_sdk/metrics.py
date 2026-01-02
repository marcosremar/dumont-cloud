"""
Market Metrics module.

Provides access to:
- Market snapshots (price history)
- Provider reliability rankings
- Cost-efficiency rankings
- Price predictions
- GPU comparisons
- Savings and hibernation analytics
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarketSnapshot:
    """Market snapshot data point."""
    timestamp: str
    gpu_name: str
    machine_type: str
    min_price: float
    max_price: float
    avg_price: float
    median_price: Optional[float]
    total_offers: int
    available_gpus: int
    verified_offers: int
    avg_reliability: Optional[float]
    avg_total_flops: Optional[float]
    avg_dlperf: Optional[float]
    min_cost_per_tflops: Optional[float]
    avg_cost_per_tflops: Optional[float]
    region_distribution: Optional[Dict[str, int]]


@dataclass
class ProviderRanking:
    """Provider reliability ranking."""
    machine_id: int
    hostname: Optional[str]
    geolocation: Optional[str]
    gpu_name: str
    verified: bool
    reliability_score: float
    availability_score: float
    price_stability_score: float
    total_observations: int
    avg_price: Optional[float]
    min_price_seen: Optional[float]
    max_price_seen: Optional[float]
    avg_total_flops: Optional[float]
    avg_dlperf: Optional[float]
    first_seen: Optional[str]
    last_seen: Optional[str]


@dataclass
class EfficiencyRanking:
    """Cost-efficiency ranking."""
    rank: int
    rank_in_class: Optional[int]
    offer_id: int
    gpu_name: str
    machine_type: str
    dph_total: float
    total_flops: Optional[float]
    gpu_ram: Optional[float]
    dlperf: Optional[float]
    cost_per_tflops: Optional[float]
    cost_per_gb_vram: Optional[float]
    efficiency_score: float
    reliability: Optional[float]
    verified: bool
    geolocation: Optional[str]


@dataclass
class PricePrediction:
    """Price prediction for a GPU."""
    gpu_name: str
    machine_type: str
    hourly_predictions: Dict[str, float]
    daily_predictions: Dict[str, float]
    best_hour_utc: int
    best_day: str
    predicted_min_price: float
    model_confidence: float
    model_version: str
    valid_until: str
    created_at: Optional[str]


@dataclass
class GpuComparison:
    """GPU comparison item."""
    gpu_name: str
    avg_price: float
    min_price: float
    total_offers: int
    avg_reliability: Optional[float]
    min_cost_per_tflops: Optional[float]
    avg_total_flops: Optional[float]


@dataclass
class ComparisonResult:
    """GPU comparison result."""
    machine_type: str
    gpus: List[GpuComparison]
    cheapest: Optional[GpuComparison]
    best_value: Optional[GpuComparison]
    generated_at: str


@dataclass
class SavingsSummary:
    """Savings summary."""
    total_savings_usd: float
    total_hours_saved: float
    hibernation_count: int
    avg_daily_savings_usd: float
    avg_daily_hours_saved: float
    projected_monthly_savings_usd: float


@dataclass
class SavingsHistoryItem:
    """Savings history item."""
    date: str
    hibernations: int
    savings_usd: float
    hours_saved: float
    cumulative_savings_usd: float


class MetricsClient:
    """
    Client for Market Metrics operations.

    Provides access to GPU market data, provider rankings,
    price predictions, and savings analytics.

    Example:
        async with DumontClient(api_key="...") as client:
            # Get market summary
            summary = await client.metrics.market_summary()

            # Get provider rankings
            providers = await client.metrics.providers(gpu_name="RTX_4090")

            # Get savings
            savings = await client.metrics.savings_real(days=30)
    """

    def __init__(self, base_client):
        self._client = base_client

    async def market(
        self,
        gpu_name: Optional[str] = None,
        machine_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[MarketSnapshot]:
        """
        Get market snapshots (price history).

        Args:
            gpu_name: Filter by GPU name
            machine_type: Filter by type (on-demand, interruptible, bid)
            hours: Hours of history (1-168)
            limit: Maximum results (up to 1000)

        Returns:
            List of market snapshots
        """
        params = {
            "hours": hours,
            "limit": limit,
        }
        if gpu_name:
            params["gpu_name"] = gpu_name
        if machine_type:
            params["machine_type"] = machine_type

        response = await self._client.get("/api/v1/metrics/market", params=params)

        return [
            MarketSnapshot(
                timestamp=snap.get("timestamp", ""),
                gpu_name=snap.get("gpu_name", ""),
                machine_type=snap.get("machine_type", ""),
                min_price=snap.get("min_price", 0),
                max_price=snap.get("max_price", 0),
                avg_price=snap.get("avg_price", 0),
                median_price=snap.get("median_price"),
                total_offers=snap.get("total_offers", 0),
                available_gpus=snap.get("available_gpus", 0),
                verified_offers=snap.get("verified_offers", 0),
                avg_reliability=snap.get("avg_reliability"),
                avg_total_flops=snap.get("avg_total_flops"),
                avg_dlperf=snap.get("avg_dlperf"),
                min_cost_per_tflops=snap.get("min_cost_per_tflops"),
                avg_cost_per_tflops=snap.get("avg_cost_per_tflops"),
                region_distribution=snap.get("region_distribution"),
            )
            for snap in response
        ]

    async def market_summary(
        self,
        gpu_name: Optional[str] = None,
        machine_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get market summary grouped by GPU and machine type.

        Args:
            gpu_name: Filter by GPU name (optional)
            machine_type: Filter by machine type (optional)

        Returns:
            Summary with price data per GPU/type
        """
        params = {}
        if gpu_name:
            params["gpu_name"] = gpu_name
        if machine_type:
            params["machine_type"] = machine_type

        return await self._client.get("/api/v1/metrics/market/summary", params=params)

    async def providers(
        self,
        geolocation: Optional[str] = None,
        gpu_name: Optional[str] = None,
        verified_only: bool = False,
        min_observations: int = 1,
        min_reliability: float = 0.0,
        order_by: str = "reliability_score",
        limit: int = 50,
    ) -> List[ProviderRanking]:
        """
        Get provider reliability rankings.

        Args:
            geolocation: Filter by region/country
            gpu_name: Filter by GPU
            verified_only: Only verified providers
            min_observations: Minimum observations required
            min_reliability: Minimum reliability score (0-1)
            order_by: Sort field
            limit: Maximum results

        Returns:
            List of provider rankings
        """
        params = {
            "verified_only": verified_only,
            "min_observations": min_observations,
            "min_reliability": min_reliability,
            "order_by": order_by,
            "limit": limit,
        }
        if geolocation:
            params["geolocation"] = geolocation
        if gpu_name:
            params["gpu_name"] = gpu_name

        response = await self._client.get("/api/v1/metrics/providers", params=params)

        return [
            ProviderRanking(
                machine_id=p.get("machine_id", 0),
                hostname=p.get("hostname"),
                geolocation=p.get("geolocation"),
                gpu_name=p.get("gpu_name", ""),
                verified=p.get("verified", False),
                reliability_score=p.get("reliability_score", 0),
                availability_score=p.get("availability_score", 0),
                price_stability_score=p.get("price_stability_score", 0),
                total_observations=p.get("total_observations", 0),
                avg_price=p.get("avg_price"),
                min_price_seen=p.get("min_price_seen"),
                max_price_seen=p.get("max_price_seen"),
                avg_total_flops=p.get("avg_total_flops"),
                avg_dlperf=p.get("avg_dlperf"),
                first_seen=p.get("first_seen"),
                last_seen=p.get("last_seen"),
            )
            for p in response
        ]

    async def efficiency(
        self,
        gpu_name: Optional[str] = None,
        machine_type: Optional[str] = None,
        verified_only: bool = False,
        min_reliability: float = 0.0,
        max_price: Optional[float] = None,
        geolocation: Optional[str] = None,
        limit: int = 50,
    ) -> List[EfficiencyRanking]:
        """
        Get cost-efficiency rankings.

        Score combines $/TFLOPS, $/VRAM, reliability, verification.

        Args:
            gpu_name: Filter by GPU
            machine_type: Filter by machine type
            verified_only: Only verified providers
            min_reliability: Minimum reliability (0-1)
            max_price: Maximum price per hour
            geolocation: Filter by region
            limit: Maximum results

        Returns:
            List of efficiency rankings
        """
        params = {
            "verified_only": verified_only,
            "min_reliability": min_reliability,
            "limit": limit,
        }
        if gpu_name:
            params["gpu_name"] = gpu_name
        if machine_type:
            params["machine_type"] = machine_type
        if max_price:
            params["max_price"] = max_price
        if geolocation:
            params["geolocation"] = geolocation

        response = await self._client.get("/api/v1/metrics/efficiency", params=params)

        return [
            EfficiencyRanking(
                rank=e.get("rank", 0),
                rank_in_class=e.get("rank_in_class"),
                offer_id=e.get("offer_id", 0),
                gpu_name=e.get("gpu_name", ""),
                machine_type=e.get("machine_type", ""),
                dph_total=e.get("dph_total", 0),
                total_flops=e.get("total_flops"),
                gpu_ram=e.get("gpu_ram"),
                dlperf=e.get("dlperf"),
                cost_per_tflops=e.get("cost_per_tflops"),
                cost_per_gb_vram=e.get("cost_per_gb_vram"),
                efficiency_score=e.get("efficiency_score", 0),
                reliability=e.get("reliability"),
                verified=e.get("verified", False),
                geolocation=e.get("geolocation"),
            )
            for e in response
        ]

    async def predictions(
        self,
        gpu_name: str,
        machine_type: str = "on-demand",
        force_refresh: bool = False,
    ) -> PricePrediction:
        """
        Get price predictions for a GPU.

        Includes hourly predictions (next 24h), daily predictions,
        and best time to rent.

        Args:
            gpu_name: GPU name
            machine_type: Machine type
            force_refresh: Force recalculation

        Returns:
            Price prediction data
        """
        params = {
            "machine_type": machine_type,
            "force_refresh": force_refresh,
        }

        response = await self._client.get(
            f"/api/v1/metrics/predictions/{gpu_name}",
            params=params
        )

        return PricePrediction(
            gpu_name=response.get("gpu_name", gpu_name),
            machine_type=response.get("machine_type", machine_type),
            hourly_predictions=response.get("hourly_predictions", {}),
            daily_predictions=response.get("daily_predictions", {}),
            best_hour_utc=response.get("best_hour_utc", 0),
            best_day=response.get("best_day", "unknown"),
            predicted_min_price=response.get("predicted_min_price", 0),
            model_confidence=response.get("model_confidence", 0),
            model_version=response.get("model_version", "unknown"),
            valid_until=response.get("valid_until", ""),
            created_at=response.get("created_at"),
        )

    async def compare(
        self,
        gpus: List[str],
        machine_type: str = "on-demand",
    ) -> ComparisonResult:
        """
        Compare multiple GPUs.

        Args:
            gpus: List of GPU names to compare
            machine_type: Machine type for comparison

        Returns:
            Comparison result with cheapest and best value
        """
        params = {
            "gpus": ",".join(gpus),
            "machine_type": machine_type,
        }

        response = await self._client.get("/api/v1/metrics/compare", params=params)

        def parse_gpu(g: Dict) -> GpuComparison:
            return GpuComparison(
                gpu_name=g.get("gpu_name", ""),
                avg_price=g.get("avg_price", 0),
                min_price=g.get("min_price", 0),
                total_offers=g.get("total_offers", 0),
                avg_reliability=g.get("avg_reliability"),
                min_cost_per_tflops=g.get("min_cost_per_tflops"),
                avg_total_flops=g.get("avg_total_flops"),
            )

        gpu_list = [parse_gpu(g) for g in response.get("gpus", [])]
        cheapest = parse_gpu(response["cheapest"]) if response.get("cheapest") else None
        best_value = parse_gpu(response["best_value"]) if response.get("best_value") else None

        return ComparisonResult(
            machine_type=response.get("machine_type", machine_type),
            gpus=gpu_list,
            cheapest=cheapest,
            best_value=best_value,
            generated_at=response.get("generated_at", ""),
        )

    async def gpus(self) -> List[str]:
        """
        List all available GPUs with market data.

        Returns:
            Sorted list of GPU names
        """
        return await self._client.get("/api/v1/metrics/gpus")

    async def machine_types(self) -> List[str]:
        """
        List all available machine types.

        Returns:
            List of machine types (on-demand, interruptible, bid)
        """
        return await self._client.get("/api/v1/metrics/types")

    # =========================================================================
    # Savings Analytics
    # =========================================================================

    async def savings_real(
        self,
        days: int = 30,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get real savings based on hibernation events.

        Analyzes hibernation history and calculates:
        - Total hours saved
        - Total USD saved
        - Average per day
        - Breakdown by GPU

        Args:
            days: Period in days (1-365)
            user_id: Filter by user (optional)

        Returns:
            Savings summary with breakdown
        """
        params = {"days": days}
        if user_id:
            params["user_id"] = user_id

        return await self._client.get("/api/v1/metrics/savings/real", params=params)

    async def savings_history(
        self,
        days: int = 30,
        group_by: str = "day",
    ) -> Dict[str, Any]:
        """
        Get savings history over time.

        Useful for cumulative savings charts.

        Args:
            days: Period in days (1-365)
            group_by: Group by: day, week, month

        Returns:
            History with cumulative savings
        """
        params = {
            "days": days,
            "group_by": group_by,
        }

        return await self._client.get("/api/v1/metrics/savings/history", params=params)

    async def hibernation_events(
        self,
        limit: int = 50,
        instance_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recent hibernation events.

        Args:
            limit: Maximum events (up to 200)
            instance_id: Filter by instance
            event_type: Filter by event type

        Returns:
            List of hibernation events
        """
        params = {"limit": limit}
        if instance_id:
            params["instance_id"] = instance_id
        if event_type:
            params["event_type"] = event_type

        return await self._client.get("/api/v1/metrics/hibernation/events", params=params)

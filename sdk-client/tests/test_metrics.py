"""
Tests for the MetricsClient module.

Includes unit tests (with mocks) and integration tests (with real API).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from dumont_sdk.metrics import (
    MetricsClient,
    MarketSnapshot,
    ProviderRanking,
    EfficiencyRanking,
    PricePrediction,
    GpuComparison,
    ComparisonResult,
)


# =============================================================================
# Mock Data
# =============================================================================

@pytest.fixture
def mock_market_snapshots():
    """Mock market snapshots response."""
    return [
        {
            "timestamp": "2024-12-20T10:00:00",
            "gpu_name": "RTX_4090",
            "machine_type": "on-demand",
            "min_price": 0.35,
            "max_price": 0.85,
            "avg_price": 0.55,
            "median_price": 0.50,
            "total_offers": 120,
            "available_gpus": 85,
            "verified_offers": 45,
            "avg_reliability": 0.92,
            "avg_total_flops": 82.6,
            "avg_dlperf": 95.2,
            "min_cost_per_tflops": 0.004,
            "avg_cost_per_tflops": 0.007,
            "region_distribution": {"US": 60, "EU": 40, "ASIA": 20},
        },
        {
            "timestamp": "2024-12-20T09:00:00",
            "gpu_name": "RTX_4090",
            "machine_type": "on-demand",
            "min_price": 0.36,
            "max_price": 0.80,
            "avg_price": 0.54,
            "median_price": 0.49,
            "total_offers": 118,
            "available_gpus": 82,
            "verified_offers": 43,
            "avg_reliability": 0.91,
            "avg_total_flops": 82.5,
            "avg_dlperf": 95.0,
            "min_cost_per_tflops": 0.0043,
            "avg_cost_per_tflops": 0.0068,
            "region_distribution": {"US": 58, "EU": 42, "ASIA": 18},
        },
    ]


@pytest.fixture
def mock_market_summary():
    """Mock market summary response."""
    return {
        "data": {
            "RTX_4090": {
                "on-demand": {
                    "min_price": 0.35,
                    "max_price": 0.85,
                    "avg_price": 0.55,
                    "median_price": 0.50,
                    "total_offers": 120,
                    "available_gpus": 85,
                    "avg_reliability": 0.92,
                    "min_cost_per_tflops": 0.004,
                    "last_update": "2024-12-20T10:00:00",
                },
                "interruptible": {
                    "min_price": 0.20,
                    "max_price": 0.45,
                    "avg_price": 0.30,
                    "median_price": 0.28,
                    "total_offers": 80,
                    "available_gpus": 50,
                    "avg_reliability": 0.85,
                    "min_cost_per_tflops": 0.0025,
                    "last_update": "2024-12-20T10:00:00",
                },
            },
        },
        "generated_at": "2024-12-20T10:05:00",
    }


@pytest.fixture
def mock_providers():
    """Mock provider rankings response."""
    return [
        {
            "machine_id": 12345,
            "hostname": "gpu-host-1",
            "geolocation": "US, CA",
            "gpu_name": "RTX_4090",
            "verified": True,
            "reliability_score": 0.98,
            "availability_score": 0.95,
            "price_stability_score": 0.92,
            "total_observations": 500,
            "avg_price": 0.45,
            "min_price_seen": 0.35,
            "max_price_seen": 0.55,
            "avg_total_flops": 82.6,
            "avg_dlperf": 95.2,
            "first_seen": "2024-01-15T00:00:00",
            "last_seen": "2024-12-20T10:00:00",
        },
        {
            "machine_id": 12346,
            "hostname": "gpu-host-2",
            "geolocation": "DE",
            "gpu_name": "RTX_4090",
            "verified": True,
            "reliability_score": 0.95,
            "availability_score": 0.92,
            "price_stability_score": 0.90,
            "total_observations": 350,
            "avg_price": 0.48,
            "min_price_seen": 0.38,
            "max_price_seen": 0.58,
            "avg_total_flops": 82.5,
            "avg_dlperf": 94.8,
            "first_seen": "2024-03-01T00:00:00",
            "last_seen": "2024-12-20T09:55:00",
        },
    ]


@pytest.fixture
def mock_efficiency():
    """Mock efficiency rankings response."""
    return [
        {
            "rank": 1,
            "rank_in_class": 1,
            "offer_id": 29102589,
            "gpu_name": "RTX_4090",
            "machine_type": "on-demand",
            "dph_total": 0.38,
            "total_flops": 82.6,
            "gpu_ram": 24.0,
            "dlperf": 95.2,
            "cost_per_tflops": 0.0046,
            "cost_per_gb_vram": 0.0158,
            "efficiency_score": 9.5,
            "reliability": 0.95,
            "verified": True,
            "geolocation": "US, CA",
        },
        {
            "rank": 2,
            "rank_in_class": 2,
            "offer_id": 29102590,
            "gpu_name": "RTX_4090",
            "machine_type": "on-demand",
            "dph_total": 0.42,
            "total_flops": 82.6,
            "gpu_ram": 24.0,
            "dlperf": 94.8,
            "cost_per_tflops": 0.0051,
            "cost_per_gb_vram": 0.0175,
            "efficiency_score": 9.2,
            "reliability": 0.92,
            "verified": True,
            "geolocation": "DE",
        },
    ]


@pytest.fixture
def mock_predictions():
    """Mock price prediction response."""
    return {
        "gpu_name": "RTX_4090",
        "machine_type": "on-demand",
        "hourly_predictions": {
            "0": 0.52, "1": 0.50, "2": 0.48, "3": 0.47,
            "4": 0.46, "5": 0.45, "6": 0.44, "7": 0.45,
            "8": 0.48, "9": 0.52, "10": 0.55, "11": 0.58,
        },
        "daily_predictions": {
            "monday": 0.50, "tuesday": 0.48, "wednesday": 0.47,
            "thursday": 0.49, "friday": 0.52, "saturday": 0.45,
            "sunday": 0.44,
        },
        "best_hour_utc": 6,
        "best_day": "sunday",
        "predicted_min_price": 0.44,
        "model_confidence": 0.85,
        "model_version": "v2.1.0",
        "valid_until": "2024-12-21T00:00:00",
        "created_at": "2024-12-20T10:00:00",
    }


@pytest.fixture
def mock_comparison():
    """Mock GPU comparison response."""
    return {
        "machine_type": "on-demand",
        "gpus": [
            {
                "gpu_name": "RTX_3090",
                "avg_price": 0.35,
                "min_price": 0.25,
                "total_offers": 150,
                "avg_reliability": 0.90,
                "min_cost_per_tflops": 0.005,
                "avg_total_flops": 71.0,
            },
            {
                "gpu_name": "RTX_4090",
                "avg_price": 0.55,
                "min_price": 0.35,
                "total_offers": 120,
                "avg_reliability": 0.92,
                "min_cost_per_tflops": 0.004,
                "avg_total_flops": 82.6,
            },
        ],
        "cheapest": {
            "gpu_name": "RTX_3090",
            "avg_price": 0.35,
            "min_price": 0.25,
            "total_offers": 150,
            "avg_reliability": 0.90,
            "min_cost_per_tflops": 0.005,
            "avg_total_flops": 71.0,
        },
        "best_value": {
            "gpu_name": "RTX_4090",
            "avg_price": 0.55,
            "min_price": 0.35,
            "total_offers": 120,
            "avg_reliability": 0.92,
            "min_cost_per_tflops": 0.004,
            "avg_total_flops": 82.6,
        },
        "generated_at": "2024-12-20T10:00:00",
    }


@pytest.fixture
def mock_savings_real():
    """Mock real savings response."""
    return {
        "period_days": 30,
        "summary": {
            "total_savings_usd": 125.50,
            "total_hours_saved": 285.5,
            "hibernation_count": 45,
            "avg_daily_savings_usd": 4.18,
            "avg_daily_hours_saved": 9.5,
            "projected_monthly_savings_usd": 125.50,
        },
        "gpu_breakdown": {
            "RTX_4090": {
                "hibernations": 30,
                "hours_saved": 200.0,
                "usd_saved": 90.00,
            },
            "RTX_3090": {
                "hibernations": 15,
                "hours_saved": 85.5,
                "usd_saved": 35.50,
            },
        },
        "generated_at": "2024-12-20T10:00:00",
    }


@pytest.fixture
def mock_savings_history():
    """Mock savings history response."""
    return {
        "period_days": 7,
        "group_by": "day",
        "history": [
            {
                "date": "2024-12-14",
                "hibernations": 5,
                "savings_usd": 15.25,
                "hours_saved": 35.0,
                "cumulative_savings_usd": 15.25,
            },
            {
                "date": "2024-12-15",
                "hibernations": 8,
                "savings_usd": 22.50,
                "hours_saved": 52.0,
                "cumulative_savings_usd": 37.75,
            },
        ],
        "total_cumulative_savings": 37.75,
        "generated_at": "2024-12-20T10:00:00",
    }


@pytest.fixture
def mock_hibernation_events():
    """Mock hibernation events response."""
    return {
        "events": [
            {
                "id": 1,
                "instance_id": 12345,
                "event_type": "hibernated",
                "timestamp": "2024-12-20T09:00:00",
                "idle_hours": 2.5,
                "savings_usd": 1.25,
            },
            {
                "id": 2,
                "instance_id": 12346,
                "event_type": "deleted",
                "timestamp": "2024-12-20T08:30:00",
                "idle_hours": 1.0,
                "savings_usd": 0.50,
            },
        ],
        "count": 2,
    }


@pytest.fixture
def mock_base_client():
    """Mock base client for unit tests."""
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


# =============================================================================
# Unit Tests
# =============================================================================

class TestMetricsUnit:
    """Unit tests for MetricsClient (using mocks)."""

    @pytest.mark.asyncio
    async def test_get_market_snapshots(self, mock_base_client, mock_market_snapshots):
        """Test getting market snapshots."""
        mock_base_client.get.return_value = mock_market_snapshots

        client = MetricsClient(mock_base_client)
        snapshots = await client.market(gpu_name="RTX_4090", hours=24)

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[0][0] == "/api/v1/metrics/market"
        assert call_args[1]["params"]["gpu_name"] == "RTX_4090"
        assert call_args[1]["params"]["hours"] == 24

        assert len(snapshots) == 2
        assert all(isinstance(s, MarketSnapshot) for s in snapshots)
        assert snapshots[0].gpu_name == "RTX_4090"
        assert snapshots[0].avg_price == 0.55

    @pytest.mark.asyncio
    async def test_get_market_summary(self, mock_base_client, mock_market_summary):
        """Test getting market summary."""
        mock_base_client.get.return_value = mock_market_summary

        client = MetricsClient(mock_base_client)
        summary = await client.market_summary(gpu_name="RTX_4090")

        mock_base_client.get.assert_called_once_with(
            "/api/v1/metrics/market/summary",
            params={"gpu_name": "RTX_4090"}
        )

        assert "data" in summary
        assert "RTX_4090" in summary["data"]
        assert "on-demand" in summary["data"]["RTX_4090"]

    @pytest.mark.asyncio
    async def test_get_providers(self, mock_base_client, mock_providers):
        """Test getting provider rankings."""
        mock_base_client.get.return_value = mock_providers

        client = MetricsClient(mock_base_client)
        providers = await client.providers(
            gpu_name="RTX_4090",
            verified_only=True,
            min_reliability=0.9,
        )

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[1]["params"]["gpu_name"] == "RTX_4090"
        assert call_args[1]["params"]["verified_only"] is True
        assert call_args[1]["params"]["min_reliability"] == 0.9

        assert len(providers) == 2
        assert all(isinstance(p, ProviderRanking) for p in providers)
        assert providers[0].reliability_score == 0.98
        assert providers[0].verified is True

    @pytest.mark.asyncio
    async def test_get_efficiency(self, mock_base_client, mock_efficiency):
        """Test getting efficiency rankings."""
        mock_base_client.get.return_value = mock_efficiency

        client = MetricsClient(mock_base_client)
        efficiency = await client.efficiency(
            gpu_name="RTX_4090",
            max_price=0.50,
        )

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[1]["params"]["gpu_name"] == "RTX_4090"
        assert call_args[1]["params"]["max_price"] == 0.50

        assert len(efficiency) == 2
        assert all(isinstance(e, EfficiencyRanking) for e in efficiency)
        assert efficiency[0].rank == 1
        assert efficiency[0].efficiency_score == 9.5

    @pytest.mark.asyncio
    async def test_get_predictions(self, mock_base_client, mock_predictions):
        """Test getting price predictions."""
        mock_base_client.get.return_value = mock_predictions

        client = MetricsClient(mock_base_client)
        prediction = await client.predictions("RTX_4090")

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert "/api/v1/metrics/predictions/RTX_4090" in call_args[0][0]

        assert isinstance(prediction, PricePrediction)
        assert prediction.gpu_name == "RTX_4090"
        assert prediction.best_day == "sunday"
        assert prediction.best_hour_utc == 6
        assert prediction.model_confidence == 0.85

    @pytest.mark.asyncio
    async def test_compare_gpus(self, mock_base_client, mock_comparison):
        """Test comparing GPUs."""
        mock_base_client.get.return_value = mock_comparison

        client = MetricsClient(mock_base_client)
        result = await client.compare(gpus=["RTX_3090", "RTX_4090"])

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[1]["params"]["gpus"] == "RTX_3090,RTX_4090"

        assert isinstance(result, ComparisonResult)
        assert len(result.gpus) == 2
        assert result.cheapest.gpu_name == "RTX_3090"
        assert result.best_value.gpu_name == "RTX_4090"

    @pytest.mark.asyncio
    async def test_list_gpus(self, mock_base_client):
        """Test listing available GPUs."""
        mock_base_client.get.return_value = ["RTX_3090", "RTX_4090", "A100"]

        client = MetricsClient(mock_base_client)
        gpus = await client.gpus()

        mock_base_client.get.assert_called_once_with("/api/v1/metrics/gpus")
        assert len(gpus) == 3
        assert "RTX_4090" in gpus

    @pytest.mark.asyncio
    async def test_list_machine_types(self, mock_base_client):
        """Test listing machine types."""
        mock_base_client.get.return_value = ["on-demand", "interruptible", "bid"]

        client = MetricsClient(mock_base_client)
        types = await client.machine_types()

        mock_base_client.get.assert_called_once_with("/api/v1/metrics/types")
        assert len(types) == 3
        assert "on-demand" in types

    @pytest.mark.asyncio
    async def test_get_savings_real(self, mock_base_client, mock_savings_real):
        """Test getting real savings."""
        mock_base_client.get.return_value = mock_savings_real

        client = MetricsClient(mock_base_client)
        savings = await client.savings_real(days=30)

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[1]["params"]["days"] == 30

        assert savings["summary"]["total_savings_usd"] == 125.50
        assert savings["summary"]["hibernation_count"] == 45
        assert "gpu_breakdown" in savings

    @pytest.mark.asyncio
    async def test_get_savings_history(self, mock_base_client, mock_savings_history):
        """Test getting savings history."""
        mock_base_client.get.return_value = mock_savings_history

        client = MetricsClient(mock_base_client)
        history = await client.savings_history(days=7, group_by="day")

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[1]["params"]["days"] == 7
        assert call_args[1]["params"]["group_by"] == "day"

        assert len(history["history"]) == 2
        assert history["total_cumulative_savings"] == 37.75

    @pytest.mark.asyncio
    async def test_get_hibernation_events(self, mock_base_client, mock_hibernation_events):
        """Test getting hibernation events."""
        mock_base_client.get.return_value = mock_hibernation_events

        client = MetricsClient(mock_base_client)
        events = await client.hibernation_events(limit=50)

        mock_base_client.get.assert_called_once()
        call_args = mock_base_client.get.call_args
        assert call_args[1]["params"]["limit"] == 50

        assert events["count"] == 2
        assert len(events["events"]) == 2


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests for MetricsClient (requires real API)."""

    @pytest.mark.asyncio
    async def test_list_gpus_real(self, client_with_api_key, rate_limiter):
        """Test listing GPUs from real API."""
        await rate_limiter.wait()

        gpus = await client_with_api_key.metrics.gpus()

        assert isinstance(gpus, list)
        # Should have at least some GPUs with market data
        # (May be empty if no market snapshots exist yet)

    @pytest.mark.asyncio
    async def test_list_machine_types_real(self, client_with_api_key, rate_limiter):
        """Test listing machine types from real API."""
        await rate_limiter.wait()

        types = await client_with_api_key.metrics.machine_types()

        assert isinstance(types, list)
        assert len(types) == 3
        assert "on-demand" in types
        assert "interruptible" in types
        assert "bid" in types

    @pytest.mark.asyncio
    async def test_market_summary_real(self, client_with_api_key, rate_limiter):
        """Test getting market summary from real API."""
        await rate_limiter.wait()

        summary = await client_with_api_key.metrics.market_summary()

        assert isinstance(summary, dict)
        assert "data" in summary or "generated_at" in summary

    @pytest.mark.asyncio
    async def test_get_savings_real(self, client_with_api_key, rate_limiter):
        """Test getting savings from real API."""
        await rate_limiter.wait()

        savings = await client_with_api_key.metrics.savings_real(days=30)

        assert isinstance(savings, dict)
        assert "period_days" in savings
        assert "summary" in savings

    @pytest.mark.asyncio
    async def test_get_providers_real(self, client_with_api_key, rate_limiter):
        """Test getting providers from real API."""
        await rate_limiter.wait()

        providers = await client_with_api_key.metrics.providers(limit=10)

        assert isinstance(providers, list)
        # Should return ProviderRanking objects (may be empty)
        for p in providers:
            assert isinstance(p, ProviderRanking)

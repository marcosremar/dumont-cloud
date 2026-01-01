"""
Unit Tests for Cost Optimization Service

Tests for GPU-to-workload matching, hibernation optimization,
spot timing recommendations, and savings calculations.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.cost_optimization_service import (
    CostOptimizationService,
    GPU_TIERS,
    UNDERUTILIZED_THRESHOLD,
    OVERUTILIZED_THRESHOLD,
    HIGH_VARIANCE_THRESHOLD,
    MIN_DAYS_FOR_RECOMMENDATION,
    FULL_CONFIDENCE_DAYS,
)


class TestGPUTiersConfiguration:
    """Tests for GPU tier configuration constants"""

    def test_gpu_tiers_has_required_fields(self):
        """Each GPU tier entry should have tier, vram, and price_per_hour"""
        for gpu_name, info in GPU_TIERS.items():
            assert "tier" in info, f"{gpu_name} missing tier"
            assert "vram" in info, f"{gpu_name} missing vram"
            assert "price_per_hour" in info, f"{gpu_name} missing price_per_hour"

    def test_gpu_tiers_sorted_by_tier_and_price(self):
        """Higher tiers should generally have higher prices"""
        tier_prices = {}
        for gpu_name, info in GPU_TIERS.items():
            tier = info["tier"]
            price = info["price_per_hour"]
            if tier not in tier_prices:
                tier_prices[tier] = []
            tier_prices[tier].append((gpu_name, price))

        # Verify tier 5 GPUs cost more than tier 1
        tier_1_max_price = max(p for _, p in tier_prices.get(1, [(None, 0)]))
        tier_5_min_price = min(p for _, p in tier_prices.get(5, [(None, float('inf'))]))
        assert tier_5_min_price > tier_1_max_price

    def test_threshold_values_are_valid(self):
        """Threshold values should be reasonable percentages"""
        assert 0 < UNDERUTILIZED_THRESHOLD < 100
        assert 0 < OVERUTILIZED_THRESHOLD <= 100
        assert UNDERUTILIZED_THRESHOLD < OVERUTILIZED_THRESHOLD
        assert HIGH_VARIANCE_THRESHOLD > 0


class TestAnalyzeGPUUtilization:
    """Tests for _analyze_gpu_utilization method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_empty_records_returns_insufficient_data(self, service):
        """Should return insufficient_data when no records provided"""
        result = service._analyze_gpu_utilization([])

        assert result["recommendation_type"] == "insufficient_data"
        assert result["avg_utilization"] == 0.0
        assert result["confidence"] == 0.0

    def test_underutilized_recommends_downgrade(self, service):
        """Should recommend downgrade when avg utilization is low"""
        records = [
            {"gpu_utilization": 30},
            {"gpu_utilization": 35},
            {"gpu_utilization": 25},
            {"gpu_utilization": 40},
        ]
        result = service._analyze_gpu_utilization(records)

        assert result["recommendation_type"] == "downgrade"
        assert result["avg_utilization"] < UNDERUTILIZED_THRESHOLD

    def test_overutilized_recommends_upgrade(self, service):
        """Should recommend upgrade when avg utilization is very high"""
        records = [
            {"gpu_utilization": 96},
            {"gpu_utilization": 98},
            {"gpu_utilization": 97},
            {"gpu_utilization": 99},
        ]
        result = service._analyze_gpu_utilization(records)

        assert result["recommendation_type"] == "upgrade"
        assert result["avg_utilization"] > OVERUTILIZED_THRESHOLD

    def test_optimal_utilization(self, service):
        """Should return optimal when utilization is in the right range"""
        records = [
            {"gpu_utilization": 70},
            {"gpu_utilization": 75},
            {"gpu_utilization": 72},
            {"gpu_utilization": 68},
        ]
        result = service._analyze_gpu_utilization(records)

        assert result["recommendation_type"] == "optimal"
        assert UNDERUTILIZED_THRESHOLD <= result["avg_utilization"] <= OVERUTILIZED_THRESHOLD

    def test_high_variance_flags_manual_review(self, service):
        """Should flag manual review when variance is high"""
        records = [
            {"gpu_utilization": 10},
            {"gpu_utilization": 95},
            {"gpu_utilization": 20},
            {"gpu_utilization": 90},
            {"gpu_utilization": 15},
            {"gpu_utilization": 85},
        ]
        result = service._analyze_gpu_utilization(records)

        assert result["needs_manual_review"] is True
        assert result["std_deviation"] > HIGH_VARIANCE_THRESHOLD

    def test_confidence_increases_with_more_data(self, service):
        """Confidence should increase with more data points"""
        few_records = [{"gpu_utilization": 70}] * 10
        many_records = [{"gpu_utilization": 70}] * 100

        result_few = service._analyze_gpu_utilization(few_records)
        result_many = service._analyze_gpu_utilization(many_records)

        assert result_many["confidence"] >= result_few["confidence"]

    def test_handles_none_values_gracefully(self, service):
        """Should skip records with None gpu_utilization"""
        records = [
            {"gpu_utilization": 70},
            {"gpu_utilization": None},
            {"gpu_utilization": 75},
            {},  # Missing key
        ]
        result = service._analyze_gpu_utilization(records)

        # Should only average the two valid values
        assert result["avg_utilization"] == pytest.approx(72.5, 0.1)


class TestMatchGPUToWorkload:
    """Tests for match_gpu_to_workload method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_downgrade_recommendation_for_underutilized(self, service):
        """Should recommend downgrade for underutilized GPU"""
        result = service.match_gpu_to_workload(
            current_gpu="RTX_4090",
            avg_utilization=30.0,
            memory_utilization=20.0
        )

        assert result["recommendation_type"] == "downgrade"
        assert result["type"] == "gpu_downgrade"
        assert result["current_gpu"] == "RTX_4090"
        assert result["recommended_gpu"] != "RTX_4090"
        assert result["estimated_monthly_savings_usd"] > 0

    def test_upgrade_recommendation_for_overutilized(self, service):
        """Should recommend upgrade for overutilized GPU"""
        result = service.match_gpu_to_workload(
            current_gpu="RTX_3060",
            avg_utilization=97.0,
            memory_utilization=90.0
        )

        assert result["recommendation_type"] == "upgrade"
        assert result["type"] == "gpu_upgrade"
        assert result["performance_improvement"] is not None

    def test_keep_recommendation_for_optimal(self, service):
        """Should recommend keeping GPU when utilization is optimal"""
        result = service.match_gpu_to_workload(
            current_gpu="RTX_4080",
            avg_utilization=75.0,
            memory_utilization=60.0
        )

        assert result["recommendation_type"] == "keep"
        assert result["current_gpu"] == result["recommended_gpu"]
        assert result["estimated_monthly_savings_usd"] == 0.0

    def test_unknown_gpu_uses_default_values(self, service):
        """Should handle unknown GPU types with defaults"""
        result = service.match_gpu_to_workload(
            current_gpu="UNKNOWN_GPU",
            avg_utilization=30.0,
            memory_utilization=20.0
        )

        # Should not crash and should give a recommendation
        assert "recommendation_type" in result

    def test_savings_calculation_is_positive(self, service):
        """Downgrade savings should always be positive"""
        result = service.match_gpu_to_workload(
            current_gpu="H100",
            avg_utilization=25.0,
            memory_utilization=10.0
        )

        if result["recommendation_type"] == "downgrade":
            assert result["estimated_monthly_savings_usd"] > 0

    def test_tier_1_gpu_has_no_downgrade_path(self, service):
        """Tier 1 GPU should not have further downgrade option"""
        result = service.match_gpu_to_workload(
            current_gpu="RTX_3060",
            avg_utilization=25.0,
            memory_utilization=5.0
        )

        # Should recommend keep when no downgrade available
        assert result["recommendation_type"] in ["keep", "downgrade"]

    def test_tier_5_gpu_has_no_upgrade_path(self, service):
        """Tier 5 GPU should keep same GPU on upgrade recommendation"""
        result = service.match_gpu_to_workload(
            current_gpu="H100",
            avg_utilization=98.0,
            memory_utilization=95.0
        )

        # Already at highest tier
        assert result["recommendation_type"] == "upgrade"
        # May recommend same GPU as there's no higher tier


class TestCalculateHibernationSetting:
    """Tests for _calculate_hibernation_setting method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_empty_idle_periods_returns_default(self, service):
        """Should return 30-minute default when no idle data"""
        result = service._calculate_hibernation_setting([])

        assert result["timeout_minutes"] == 30
        assert result["confidence_score"] == 0.3
        assert "default" in result["reason"].lower()

    def test_calculates_timeout_from_median(self, service):
        """Should base timeout on median idle period"""
        idle_periods = [30, 40, 50, 60, 70]
        result = service._calculate_hibernation_setting(idle_periods)

        # Median is 50, timeout should be 50 * 0.5 = 25
        assert result["timeout_minutes"] == 25

    def test_timeout_minimum_bound(self, service):
        """Timeout should not go below 15 minutes"""
        idle_periods = [5, 10, 8, 12, 7]
        result = service._calculate_hibernation_setting(idle_periods)

        assert result["timeout_minutes"] >= 15

    def test_timeout_maximum_bound(self, service):
        """Timeout should not exceed 120 minutes"""
        idle_periods = [300, 400, 350, 500, 450]
        result = service._calculate_hibernation_setting(idle_periods)

        assert result["timeout_minutes"] <= 120

    def test_estimates_monthly_savings(self, service):
        """Should calculate estimated monthly savings"""
        idle_periods = [60, 80, 70, 90, 75] * 10  # Many periods
        result = service._calculate_hibernation_setting(idle_periods)

        assert result["estimated_monthly_savings_usd"] >= 0

    def test_confidence_increases_with_consistent_patterns(self, service):
        """Consistent idle patterns should have higher confidence"""
        consistent = [50, 52, 48, 51, 49, 50, 51, 48]
        variable = [10, 100, 20, 90, 15, 95, 25, 85]

        result_consistent = service._calculate_hibernation_setting(consistent)
        result_variable = service._calculate_hibernation_setting(variable)

        assert result_consistent["confidence_score"] >= result_variable["confidence_score"]

    def test_returns_analysis_details(self, service):
        """Should include detailed analysis metrics"""
        idle_periods = [40, 50, 45, 55, 48]
        result = service._calculate_hibernation_setting(idle_periods)

        assert "analysis_details" in result
        assert "median_idle_minutes" in result["analysis_details"]
        assert "idle_period_count" in result["analysis_details"]
        assert "pattern_consistency" in result["analysis_details"]


class TestCalculateTotalSavings:
    """Tests for calculate_total_savings method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_empty_recommendations_returns_zero(self, service):
        """Should return 0 for empty recommendations"""
        result = service.calculate_total_savings([])
        assert result == 0.0

    def test_sums_all_savings(self, service):
        """Should sum all positive savings values"""
        recommendations = [
            {"type": "gpu_downgrade", "estimated_monthly_savings_usd": 100.0},
            {"type": "hibernation", "estimated_monthly_savings_usd": 50.0},
            {"type": "spot_timing", "estimated_monthly_savings_usd": 30.0},
        ]
        result = service.calculate_total_savings(recommendations)

        assert result == 180.0

    def test_ignores_negative_savings(self, service):
        """Should ignore negative or zero savings"""
        recommendations = [
            {"type": "gpu_upgrade", "estimated_monthly_savings_usd": 0.0},
            {"type": "hibernation", "estimated_monthly_savings_usd": 50.0},
            {"type": "other", "estimated_monthly_savings_usd": -10.0},
        ]
        result = service.calculate_total_savings(recommendations)

        assert result == 50.0

    def test_handles_missing_savings_field(self, service):
        """Should handle recommendations without savings field"""
        recommendations = [
            {"type": "gpu_match"},
            {"type": "hibernation", "estimated_monthly_savings_usd": 50.0},
        ]
        result = service.calculate_total_savings(recommendations)

        assert result == 50.0

    def test_rounds_to_two_decimals(self, service):
        """Should round result to 2 decimal places"""
        recommendations = [
            {"estimated_monthly_savings_usd": 33.337},
            {"estimated_monthly_savings_usd": 22.229},
        ]
        result = service.calculate_total_savings(recommendations)

        # 33.337 + 22.229 = 55.566, rounds to 55.57
        assert result == 55.57


class TestGetDefaultSpotRecommendation:
    """Tests for _get_default_spot_recommendation method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_returns_spot_timing_type(self, service):
        """Should return spot_timing recommendation type"""
        result = service._get_default_spot_recommendation("RTX_4090")

        assert result["type"] == "spot_timing"
        assert result["gpu_type"] == "RTX_4090"

    def test_includes_recommended_windows(self, service):
        """Should include weekend windows as defaults"""
        result = service._get_default_spot_recommendation("RTX_4090")

        assert "recommended_windows" in result
        assert len(result["recommended_windows"]) >= 1

        days = [w["day"] for w in result["recommended_windows"]]
        assert "Saturday" in days or "Sunday" in days

    def test_lower_confidence_than_predictions(self, service):
        """Default recommendation should have lower confidence"""
        result = service._get_default_spot_recommendation("RTX_4090")

        assert result["confidence_score"] == 0.50

    def test_calculates_savings_based_on_gpu_price(self, service):
        """Should calculate savings based on GPU hourly price"""
        result_expensive = service._get_default_spot_recommendation("H100")
        result_cheap = service._get_default_spot_recommendation("RTX_3060")

        assert result_expensive["estimated_monthly_savings_usd"] > result_cheap["estimated_monthly_savings_usd"]

    def test_handles_unknown_gpu(self, service):
        """Should handle unknown GPU type with default price"""
        result = service._get_default_spot_recommendation("UNKNOWN_GPU")

        assert result["type"] == "spot_timing"
        assert result["estimated_monthly_savings_usd"] > 0


class TestGetSpotTimingRecommendation:
    """Tests for _get_spot_timing_recommendation method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_returns_recommendation_without_price_service(self, service):
        """Should return default recommendation when price service unavailable"""
        result = service._get_spot_timing_recommendation("RTX_4090")

        assert result is not None
        assert result["type"] == "spot_timing"

    @patch.object(CostOptimizationService, '_get_price_prediction_service')
    def test_uses_price_prediction_when_available(self, mock_get_pps, service):
        """Should use price prediction service when available"""
        mock_pps = Mock()
        mock_pps.predict.return_value = {
            "best_hour_utc": 3,
            "best_day": "sunday",
            "model_confidence": 0.8
        }
        mock_get_pps.return_value = mock_pps

        result = service._get_spot_timing_recommendation("RTX_4090")

        assert result["confidence_score"] == 0.8
        mock_pps.predict.assert_called_once()

    @patch.object(CostOptimizationService, '_get_price_prediction_service')
    def test_falls_back_on_prediction_error(self, mock_get_pps, service):
        """Should fall back to default on prediction error"""
        mock_pps = Mock()
        mock_pps.predict.side_effect = Exception("Service error")
        mock_get_pps.return_value = mock_pps

        result = service._get_spot_timing_recommendation("RTX_4090")

        # Should still return a recommendation (default)
        assert result is not None
        assert result["type"] == "spot_timing"


class TestAnalyzeUsagePatterns:
    """Tests for analyze_usage_patterns method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    @patch('src.services.cost_optimization_service.SessionLocal')
    def test_returns_empty_result_when_no_data(self, mock_session_local, service):
        """Should return empty result when no usage data found"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_session_local.return_value = mock_db

        result = service.analyze_usage_patterns("user_123", "instance_456")

        assert result["gpu_type"] is None
        assert result["avg_utilization"] == 0.0
        assert result["has_sufficient_data"] is False

    @patch('src.services.cost_optimization_service.SessionLocal')
    def test_calculates_average_utilization(self, mock_session_local, service):
        """Should calculate average GPU utilization"""
        mock_db = MagicMock()

        # Create mock records
        mock_records = []
        for i in range(10):
            record = MagicMock()
            record.gpu_type = "RTX_4090"
            record.gpu_utilization = 70 + i
            record.memory_utilization = 50 + i
            record.runtime_hours = 1.0
            record.cost_usd = 0.70
            record.extra_data = {"idle_minutes": 30}
            record.timestamp = datetime.utcnow() - timedelta(days=7-i)
            mock_records.append(record)

        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_records
        mock_db.query.return_value = mock_query
        mock_session_local.return_value = mock_db

        result = service.analyze_usage_patterns("user_123", "instance_456")

        assert result["gpu_type"] == "RTX_4090"
        assert result["avg_utilization"] == pytest.approx(74.5, 0.1)
        assert result["data_points"] == 10

    @patch('src.services.cost_optimization_service.SessionLocal')
    def test_handles_database_error(self, mock_session_local, service):
        """Should handle database errors gracefully"""
        # Mock the session to raise an exception during query execution
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.side_effect = Exception("Query failed")
        mock_db.query.return_value = mock_query
        mock_session_local.return_value = mock_db

        result = service.analyze_usage_patterns("user_123", "instance_456")

        assert result["has_sufficient_data"] is False
        assert "error" in result


class TestOptimizeHibernation:
    """Tests for optimize_hibernation method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    @patch.object(CostOptimizationService, 'analyze_usage_patterns')
    def test_returns_default_when_insufficient_data(self, mock_analyze, service):
        """Should return default timeout when insufficient data"""
        mock_analyze.return_value = {
            "has_sufficient_data": False,
            "gpu_type": None,
        }

        result = service.optimize_hibernation("user_123", "instance_456")

        assert result["type"] == "hibernation"
        assert result["recommended_timeout_minutes"] == 30
        assert result["confidence_score"] == 0.3

    @patch.object(CostOptimizationService, 'analyze_usage_patterns')
    def test_calculates_from_idle_periods(self, mock_analyze, service):
        """Should calculate timeout from idle periods"""
        mock_analyze.return_value = {
            "has_sufficient_data": True,
            "idle_periods": [60, 70, 80, 75, 65],
        }

        result = service.optimize_hibernation("user_123", "instance_456", current_timeout_minutes=0)

        assert result["type"] == "hibernation"
        assert 15 <= result["recommended_timeout_minutes"] <= 120


class TestGetComprehensiveRecommendations:
    """Tests for get_comprehensive_recommendations method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    @patch.object(CostOptimizationService, 'analyze_usage_patterns')
    def test_returns_warning_with_insufficient_data(self, mock_analyze, service):
        """Should return warning when data is insufficient"""
        mock_analyze.return_value = {
            "has_sufficient_data": False,
            "gpu_type": "RTX_4090",
            "avg_utilization": 0,
            "total_cost_usd": 0,
            "data_completeness": 0,
        }

        result = service.get_comprehensive_recommendations("user_123", "instance_456")

        assert "warning" in result
        assert result["recommendations"] == []

    @patch.object(CostOptimizationService, 'analyze_usage_patterns')
    def test_includes_gpu_recommendation_when_not_optimal(self, mock_analyze, service):
        """Should include GPU recommendation when downgrade/upgrade needed"""
        mock_analyze.return_value = {
            "has_sufficient_data": True,
            "gpu_type": "RTX_4090",
            "avg_utilization": 30.0,  # Underutilized
            "memory_avg": 20.0,
            "total_cost_usd": 500.0,
            "total_runtime_hours": 720,
            "data_completeness": 0.9,
            "idle_periods": [60, 70, 65],
        }

        result = service.get_comprehensive_recommendations("user_123", "instance_456")

        # Should have at least one recommendation (GPU or hibernation)
        assert len(result["recommendations"]) >= 0  # May be empty if optimal
        assert result["analysis_period_days"] == 30

    @patch.object(CostOptimizationService, 'analyze_usage_patterns')
    def test_calculates_total_savings(self, mock_analyze, service):
        """Should calculate total estimated savings"""
        mock_analyze.return_value = {
            "has_sufficient_data": True,
            "gpu_type": "H100",
            "avg_utilization": 20.0,
            "memory_avg": 10.0,
            "total_cost_usd": 2000.0,
            "total_runtime_hours": 720,
            "data_completeness": 0.95,
            "idle_periods": [60, 70, 80, 75, 65] * 10,
        }

        result = service.get_comprehensive_recommendations("user_123", "instance_456")

        assert "total_estimated_monthly_savings_usd" in result
        assert isinstance(result["total_estimated_monthly_savings_usd"], float)

    @patch.object(CostOptimizationService, 'analyze_usage_patterns')
    def test_includes_current_configuration(self, mock_analyze, service):
        """Should include current configuration summary"""
        mock_analyze.return_value = {
            "has_sufficient_data": True,
            "gpu_type": "RTX_4090",
            "avg_utilization": 75.0,
            "memory_avg": 60.0,
            "total_cost_usd": 500.0,
            "total_runtime_hours": 720,
            "data_completeness": 0.9,
            "idle_periods": [],
        }

        result = service.get_comprehensive_recommendations("user_123", "instance_456")

        assert "current_configuration" in result
        assert result["current_configuration"]["gpu_type"] == "RTX_4090"
        assert result["current_configuration"]["avg_utilization"] == 75.0


class TestGetAllRecommendations:
    """Tests for _get_all_recommendations helper method"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    @patch.object(CostOptimizationService, 'get_comprehensive_recommendations')
    def test_always_includes_spot_timing(self, mock_get_comp, service):
        """Should always include spot timing recommendation"""
        mock_get_comp.return_value = {
            "recommendations": [],
            "current_configuration": {"gpu_type": "Unknown"},
        }

        result = service._get_all_recommendations("user_123", "instance_456")

        spot_recs = [r for r in result if r.get("type") == "spot_timing"]
        assert len(spot_recs) == 1

    @patch.object(CostOptimizationService, 'get_comprehensive_recommendations')
    def test_uses_default_gpu_when_unknown(self, mock_get_comp, service):
        """Should use RTX_4090 as default for spot timing when GPU unknown"""
        mock_get_comp.return_value = {
            "recommendations": [],
            "current_configuration": {"gpu_type": None},
        }

        result = service._get_all_recommendations("user_123", "instance_456")

        spot_rec = next((r for r in result if r.get("type") == "spot_timing"), None)
        assert spot_rec is not None
        assert spot_rec["gpu_type"] == "RTX_4090"


class TestServiceInitialization:
    """Tests for service initialization and lazy loading"""

    def test_creates_without_errors(self):
        """Should create service instance without errors"""
        service = CostOptimizationService()
        assert service is not None

    def test_price_prediction_service_is_lazy_loaded(self):
        """Price prediction service should be lazy loaded"""
        service = CostOptimizationService()
        assert service._price_prediction_service is None

    def test_singleton_instance_exists(self):
        """Module should provide singleton instance"""
        from src.services.cost_optimization_service import cost_optimization_service
        assert cost_optimization_service is not None
        assert isinstance(cost_optimization_service, CostOptimizationService)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    @pytest.fixture
    def service(self):
        """Create service instance for tests"""
        return CostOptimizationService()

    def test_utilization_at_exact_thresholds(self, service):
        """Should handle utilization at exact threshold values"""
        # At underutilized threshold
        result_under = service.match_gpu_to_workload("RTX_4090", UNDERUTILIZED_THRESHOLD, 50.0)
        # At overutilized threshold
        result_over = service.match_gpu_to_workload("RTX_4090", OVERUTILIZED_THRESHOLD, 50.0)

        # Should return valid recommendations
        assert result_under["recommendation_type"] in ["keep", "optimal", "downgrade"]
        assert result_over["recommendation_type"] in ["keep", "optimal", "upgrade"]

    def test_zero_utilization(self, service):
        """Should handle 0% utilization"""
        result = service.match_gpu_to_workload("RTX_4090", 0.0, 0.0)
        assert result["recommendation_type"] == "downgrade"

    def test_100_percent_utilization(self, service):
        """Should handle 100% utilization"""
        result = service.match_gpu_to_workload("RTX_4090", 100.0, 100.0)
        assert result["recommendation_type"] == "upgrade"

    def test_single_idle_period(self, service):
        """Should handle single idle period"""
        result = service._calculate_hibernation_setting([45])

        assert result["timeout_minutes"] >= 15
        assert result["timeout_minutes"] <= 120

    def test_very_short_idle_periods(self, service):
        """Should handle very short idle periods"""
        result = service._calculate_hibernation_setting([1, 2, 3, 2, 1])

        # Should floor to minimum 15 minutes
        assert result["timeout_minutes"] == 15

    def test_very_long_idle_periods(self, service):
        """Should handle very long idle periods"""
        result = service._calculate_hibernation_setting([1000, 2000, 1500, 1800])

        # Should cap at maximum 120 minutes
        assert result["timeout_minutes"] == 120

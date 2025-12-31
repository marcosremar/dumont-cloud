"""
Cost Optimization Service for 30-day usage analysis and recommendations.

Analyzes historical GPU usage patterns to provide:
- GPU-to-workload matching recommendations
- Hibernation setting optimization
- Spot timing recommendations (via price prediction integration)
- Estimated monthly cost savings
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from src.config.database import SessionLocal
from src.models.cost_optimization import UsageMetrics

logger = logging.getLogger(__name__)


# GPU tier mapping for upgrade/downgrade recommendations
GPU_TIERS = {
    # Entry level
    "RTX_3060": {"tier": 1, "vram": 12, "price_per_hour": 0.10},
    "RTX_4060": {"tier": 1, "vram": 8, "price_per_hour": 0.12},
    # Mid-range
    "RTX_4070": {"tier": 2, "vram": 12, "price_per_hour": 0.18},
    "RTX_3080": {"tier": 2, "vram": 10, "price_per_hour": 0.25},
    "RTX_4080": {"tier": 2, "vram": 16, "price_per_hour": 0.35},
    # High-end consumer
    "RTX_3090": {"tier": 3, "vram": 24, "price_per_hour": 0.40},
    "RTX_4090": {"tier": 3, "vram": 24, "price_per_hour": 0.70},
    # Professional
    "A4000": {"tier": 3, "vram": 16, "price_per_hour": 0.50},
    "A5000": {"tier": 4, "vram": 24, "price_per_hour": 0.80},
    "A6000": {"tier": 4, "vram": 48, "price_per_hour": 1.00},
    "L40S": {"tier": 4, "vram": 48, "price_per_hour": 1.50},
    # Data center
    "A100": {"tier": 5, "vram": 80, "price_per_hour": 2.50},
    "H100": {"tier": 5, "vram": 80, "price_per_hour": 4.00},
}

# Utilization thresholds for recommendations
UNDERUTILIZED_THRESHOLD = 50.0  # Below 50% avg utilization -> recommend downgrade
OVERUTILIZED_THRESHOLD = 95.0   # Above 95% avg utilization -> recommend upgrade
HIGH_VARIANCE_THRESHOLD = 30.0  # Variance > 30% -> recommend manual review

# Minimum data requirements
MIN_DAYS_FOR_RECOMMENDATION = 3  # Minimum 3 days of data required
FULL_CONFIDENCE_DAYS = 7         # 7+ days for full confidence


class CostOptimizationService:
    """
    Service for analyzing GPU usage patterns and generating cost optimization recommendations.

    Analyzes 30-day usage data to identify:
    - Under-utilized GPUs that can be downgraded
    - Over-utilized GPUs that need upgrading
    - Optimal hibernation timeout settings
    - Best spot instance timing windows
    """

    def __init__(self):
        """Initialize the cost optimization service."""
        self._price_prediction_service = None

    def _get_price_prediction_service(self):
        """Lazy load price prediction service."""
        if self._price_prediction_service is None:
            try:
                from src.services.price_prediction_service import PricePredictionService
                self._price_prediction_service = PricePredictionService()
            except ImportError:
                logger.warning("PricePredictionService not available")
                self._price_prediction_service = None
        return self._price_prediction_service

    def analyze_usage_patterns(
        self,
        user_id: str,
        instance_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze 30-day usage patterns for a specific user and instance.

        Args:
            user_id: User identifier
            instance_id: Instance identifier
            days: Number of days to analyze (default 30)

        Returns:
            Dict containing usage analysis results:
            - gpu_type: Current GPU type
            - avg_utilization: Average GPU utilization
            - memory_avg: Average memory utilization
            - total_runtime_hours: Total hours of runtime
            - total_cost_usd: Total cost in USD
            - data_points: Number of data points analyzed
            - data_completeness: Ratio of expected vs actual data points
            - idle_periods: List of idle period durations in minutes
        """
        db = SessionLocal()
        try:
            start_time = datetime.utcnow() - timedelta(days=days)

            # Query usage metrics for the user/instance
            records = db.query(UsageMetrics).filter(
                UsageMetrics.user_id == user_id,
                UsageMetrics.instance_id == instance_id,
                UsageMetrics.timestamp >= start_time,
            ).order_by(UsageMetrics.timestamp).all()

            if not records:
                logger.info(f"No usage data found for user={user_id}, instance={instance_id}")
                return {
                    "gpu_type": None,
                    "avg_utilization": 0.0,
                    "memory_avg": 0.0,
                    "total_runtime_hours": 0.0,
                    "total_cost_usd": 0.0,
                    "data_points": 0,
                    "data_completeness": 0.0,
                    "idle_periods": [],
                    "has_sufficient_data": False,
                }

            # Extract data points
            gpu_types = [r.gpu_type for r in records if r.gpu_type]
            gpu_utilizations = [r.gpu_utilization for r in records if r.gpu_utilization is not None]
            memory_utilizations = [r.memory_utilization for r in records if r.memory_utilization is not None]

            # Calculate aggregated metrics
            gpu_type = max(set(gpu_types), key=gpu_types.count) if gpu_types else None
            avg_utilization = statistics.mean(gpu_utilizations) if gpu_utilizations else 0.0
            memory_avg = statistics.mean(memory_utilizations) if memory_utilizations else 0.0
            total_runtime = sum(r.runtime_hours or 0 for r in records)
            total_cost = sum(r.cost_usd or 0 for r in records)

            # Calculate idle periods from extra_data
            idle_periods = []
            for r in records:
                if r.extra_data and isinstance(r.extra_data, dict):
                    idle_minutes = r.extra_data.get('idle_minutes')
                    if idle_minutes and idle_minutes > 0:
                        idle_periods.append(idle_minutes)

            # Estimate data completeness (assuming hourly data points)
            expected_data_points = days * 24
            data_completeness = min(1.0, len(records) / expected_data_points)

            # Determine if we have sufficient data
            days_of_data = (records[-1].timestamp - records[0].timestamp).days if len(records) > 1 else 0
            has_sufficient_data = days_of_data >= MIN_DAYS_FOR_RECOMMENDATION and len(records) >= 10

            return {
                "gpu_type": gpu_type,
                "avg_utilization": round(avg_utilization, 2),
                "memory_avg": round(memory_avg, 2),
                "total_runtime_hours": round(total_runtime, 2),
                "total_cost_usd": round(total_cost, 2),
                "data_points": len(records),
                "data_completeness": round(data_completeness, 2),
                "idle_periods": idle_periods,
                "has_sufficient_data": has_sufficient_data,
                "days_of_data": days_of_data,
            }

        except Exception as e:
            logger.error(f"Error analyzing usage patterns: {e}")
            return {
                "gpu_type": None,
                "avg_utilization": 0.0,
                "memory_avg": 0.0,
                "total_runtime_hours": 0.0,
                "total_cost_usd": 0.0,
                "data_points": 0,
                "data_completeness": 0.0,
                "idle_periods": [],
                "has_sufficient_data": False,
                "error": str(e),
            }
        finally:
            db.close()

    def _analyze_gpu_utilization(
        self,
        usage_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze GPU utilization data to determine recommendation type.

        Args:
            usage_records: List of dicts with 'gpu_utilization' key

        Returns:
            Dict with recommendation_type, avg_utilization, confidence, etc.
        """
        utilizations = [
            r.get('gpu_utilization', 0)
            for r in usage_records
            if r.get('gpu_utilization') is not None
        ]

        if not utilizations:
            return {
                "recommendation_type": "insufficient_data",
                "avg_utilization": 0.0,
                "min_utilization": 0.0,
                "max_utilization": 0.0,
                "std_deviation": 0.0,
                "confidence": 0.0,
            }

        avg_util = statistics.mean(utilizations)
        min_util = min(utilizations)
        max_util = max(utilizations)
        std_dev = statistics.stdev(utilizations) if len(utilizations) > 1 else 0.0

        # Calculate confidence based on data volume and consistency
        confidence = min(1.0, len(utilizations) / 100)  # More data = higher confidence
        if std_dev > HIGH_VARIANCE_THRESHOLD:
            confidence *= 0.7  # Reduce confidence for high variance workloads

        # Determine recommendation type
        if avg_util < UNDERUTILIZED_THRESHOLD:
            recommendation_type = "downgrade"
        elif avg_util > OVERUTILIZED_THRESHOLD:
            recommendation_type = "upgrade"
        else:
            recommendation_type = "optimal"

        # Flag high variance workloads for manual review
        needs_manual_review = std_dev > HIGH_VARIANCE_THRESHOLD

        return {
            "recommendation_type": recommendation_type,
            "avg_utilization": round(avg_util, 2),
            "min_utilization": round(min_util, 2),
            "max_utilization": round(max_util, 2),
            "std_deviation": round(std_dev, 2),
            "confidence": round(confidence, 2),
            "needs_manual_review": needs_manual_review,
        }

    def match_gpu_to_workload(
        self,
        current_gpu: str,
        avg_utilization: float,
        memory_utilization: float = 0.0
    ) -> Dict[str, Any]:
        """
        Match GPU to workload based on utilization and recommend changes.

        Args:
            current_gpu: Current GPU type (e.g., "RTX_4090")
            avg_utilization: Average GPU utilization percentage
            memory_utilization: Average memory utilization percentage

        Returns:
            Dict with recommendation including suggested GPU and savings estimate
        """
        current_info = GPU_TIERS.get(current_gpu, {
            "tier": 3, "vram": 24, "price_per_hour": 0.50
        })

        # Determine recommendation based on utilization
        if avg_utilization < UNDERUTILIZED_THRESHOLD:
            # Recommend downgrade
            target_tier = max(1, current_info["tier"] - 1)
            recommended_gpus = [
                (name, info) for name, info in GPU_TIERS.items()
                if info["tier"] == target_tier and info["vram"] >= memory_utilization / 100 * current_info["vram"]
            ]

            if recommended_gpus:
                # Sort by price and pick cheapest
                recommended_gpus.sort(key=lambda x: x[1]["price_per_hour"])
                recommended_gpu, rec_info = recommended_gpus[0]
            else:
                # No suitable downgrade found
                return {
                    "type": "gpu_match",
                    "recommendation_type": "keep",
                    "current_gpu": current_gpu,
                    "recommended_gpu": current_gpu,
                    "reason": "No suitable lower-tier GPU found for your memory requirements",
                    "estimated_monthly_savings_usd": 0.0,
                    "confidence_score": 0.5,
                }

            # Calculate savings (assuming 720 hours/month)
            monthly_hours = 720
            current_monthly = current_info["price_per_hour"] * monthly_hours
            recommended_monthly = rec_info["price_per_hour"] * monthly_hours
            savings = current_monthly - recommended_monthly

            return {
                "type": "gpu_downgrade",
                "recommendation_type": "downgrade",
                "current_gpu": current_gpu,
                "recommended_gpu": recommended_gpu,
                "reason": f"Average GPU utilization is only {avg_utilization:.1f}% over the analysis period",
                "estimated_monthly_savings_usd": round(savings, 2),
                "confidence_score": 0.85,
                "current_price_per_hour": current_info["price_per_hour"],
                "recommended_price_per_hour": rec_info["price_per_hour"],
            }

        elif avg_utilization > OVERUTILIZED_THRESHOLD:
            # Recommend upgrade
            target_tier = min(5, current_info["tier"] + 1)
            recommended_gpus = [
                (name, info) for name, info in GPU_TIERS.items()
                if info["tier"] == target_tier
            ]

            if recommended_gpus:
                # Sort by price and pick cheapest suitable option
                recommended_gpus.sort(key=lambda x: x[1]["price_per_hour"])
                recommended_gpu, rec_info = recommended_gpus[0]
            else:
                recommended_gpu = current_gpu
                rec_info = current_info

            return {
                "type": "gpu_upgrade",
                "recommendation_type": "upgrade",
                "current_gpu": current_gpu,
                "recommended_gpu": recommended_gpu,
                "reason": f"GPU is consistently over-utilized at {avg_utilization:.1f}%, causing potential performance bottlenecks",
                "estimated_monthly_savings_usd": 0.0,  # Upgrade costs more but improves performance
                "confidence_score": 0.80,
                "performance_improvement": "20-40% faster job completion expected",
            }

        else:
            # Current GPU is optimal
            return {
                "type": "gpu_match",
                "recommendation_type": "keep",
                "current_gpu": current_gpu,
                "recommended_gpu": current_gpu,
                "reason": f"GPU utilization at {avg_utilization:.1f}% is within optimal range (50-95%)",
                "estimated_monthly_savings_usd": 0.0,
                "confidence_score": 0.90,
            }

    def _calculate_hibernation_setting(
        self,
        idle_periods: List[int]
    ) -> Dict[str, Any]:
        """
        Calculate optimal hibernation timeout based on idle period patterns.

        Analyzes all idle periods to find an optimal hibernation timeout that
        balances responsiveness with cost savings. Uses the median of all idle
        periods to be robust against outliers, then applies a 50% factor to
        ensure hibernation triggers before typical idle sessions end.

        Args:
            idle_periods: List of idle period durations in minutes

        Returns:
            Dict with recommended timeout_minutes, reason, estimated savings,
            and confidence score based on data quality
        """
        if not idle_periods:
            return {
                "timeout_minutes": 30,  # Default recommendation
                "reason": "No idle period data available, using default 30-minute timeout",
                "estimated_monthly_savings_usd": 0.0,
                "confidence_score": 0.3,
            }

        # Analyze all idle periods to understand usage patterns
        # Using median is robust against outliers (very short or very long idles)
        median_idle = statistics.median(idle_periods)
        mean_idle = statistics.mean(idle_periods)
        min_idle = min(idle_periods)
        max_idle = max(idle_periods)

        # Set hibernation timeout to 50% of median
        # This ensures we catch most idle sessions while still being responsive
        recommended_timeout = int(median_idle * 0.5)

        # Ensure reasonable bounds (15 min to 120 min)
        # Below 15 min causes too many hibernate/resume cycles
        # Above 120 min wastes too much money on truly idle instances
        recommended_timeout = max(15, min(120, recommended_timeout))

        # Calculate variance to assess pattern consistency
        if len(idle_periods) > 1:
            std_dev = statistics.stdev(idle_periods)
            cv = std_dev / mean_idle if mean_idle > 0 else 0  # Coefficient of variation
        else:
            std_dev = 0.0
            cv = 0.0

        # Calculate estimated savings
        # Hibernation saves ~65% of idle time cost (overhead for hibernate/resume cycles)
        total_idle_minutes = sum(idle_periods)
        hibernation_efficiency = 0.65

        # Only count idle time above the timeout as saveable
        saveable_minutes = sum(max(0, p - recommended_timeout) for p in idle_periods)
        saved_minutes = saveable_minutes * hibernation_efficiency

        # Estimate using average GPU cost ($0.50/hour)
        avg_hourly_cost = 0.50
        estimated_monthly_savings = (saved_minutes / 60) * avg_hourly_cost

        # Calculate confidence based on:
        # - Number of data points (more = higher confidence)
        # - Consistency of patterns (lower variance = higher confidence)
        base_confidence = min(0.8, 0.4 + len(idle_periods) / 20)
        variance_penalty = min(0.3, cv * 0.2) if cv > 0.5 else 0
        confidence = max(0.3, min(0.95, base_confidence - variance_penalty))

        # Calculate idle percentage of total time
        # Assumes 30 days of monitoring, 1440 minutes per day
        total_minutes = 1440 * 30
        idle_percentage = round(100 * total_idle_minutes / (total_idle_minutes + total_minutes), 1)

        # Build descriptive reason
        if cv > 0.5:
            pattern_desc = "with variable patterns"
        else:
            pattern_desc = "with consistent patterns"

        return {
            "timeout_minutes": recommended_timeout,
            "reason": f"Analyzed {len(idle_periods)} idle periods (median: {median_idle:.0f}min, range: {min_idle}-{max_idle}min) {pattern_desc}",
            "estimated_monthly_savings_usd": round(estimated_monthly_savings, 2),
            "confidence_score": round(confidence, 2),
            "idle_percentage": idle_percentage,
            "analysis_details": {
                "median_idle_minutes": round(median_idle, 1),
                "mean_idle_minutes": round(mean_idle, 1),
                "idle_period_count": len(idle_periods),
                "pattern_consistency": "high" if cv <= 0.5 else "variable",
            },
        }

    def optimize_hibernation(
        self,
        user_id: str,
        instance_id: str,
        current_timeout_minutes: int = 0,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze usage patterns and recommend optimal hibernation timeout.

        Args:
            user_id: User identifier
            instance_id: Instance identifier
            current_timeout_minutes: Current hibernation timeout (0 = disabled)
            days: Number of days to analyze

        Returns:
            Dict with hibernation recommendation
        """
        # Get usage patterns
        usage = self.analyze_usage_patterns(user_id, instance_id, days)

        if not usage.get("has_sufficient_data"):
            return {
                "type": "hibernation",
                "current_timeout_minutes": current_timeout_minutes,
                "recommended_timeout_minutes": 30,
                "reason": "Insufficient usage data. Recommending default 30-minute timeout.",
                "estimated_monthly_savings_usd": 0.0,
                "confidence_score": 0.3,
            }

        # Calculate hibernation setting from idle periods
        hibernation = self._calculate_hibernation_setting(usage.get("idle_periods", []))

        return {
            "type": "hibernation",
            "current_timeout_minutes": current_timeout_minutes,
            "recommended_timeout_minutes": hibernation["timeout_minutes"],
            "reason": hibernation["reason"],
            "estimated_monthly_savings_usd": hibernation["estimated_monthly_savings_usd"],
            "confidence_score": hibernation["confidence_score"],
        }

    def calculate_total_savings(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate total estimated monthly savings from all recommendations.

        Args:
            recommendations: List of recommendation dicts

        Returns:
            Total estimated monthly savings in USD
        """
        total = 0.0
        for rec in recommendations:
            savings = rec.get("estimated_monthly_savings_usd", 0.0)
            if isinstance(savings, (int, float)) and savings > 0:
                total += savings
        return round(total, 2)

    def get_comprehensive_recommendations(
        self,
        user_id: str,
        instance_id: str,
        current_hibernation_timeout: int = 0,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate comprehensive cost optimization recommendations.

        Combines GPU matching, hibernation optimization, and spot timing
        recommendations into a single response.

        Args:
            user_id: User identifier
            instance_id: Instance identifier
            current_hibernation_timeout: Current hibernation timeout in minutes
            days: Number of days to analyze

        Returns:
            Dict with all recommendations and total estimated savings
        """
        recommendations = []

        # 1. Analyze usage patterns
        usage = self.analyze_usage_patterns(user_id, instance_id, days)

        if not usage.get("has_sufficient_data"):
            return {
                "current_configuration": {
                    "gpu_type": usage.get("gpu_type", "Unknown"),
                    "avg_utilization": usage.get("avg_utilization", 0),
                    "monthly_cost_usd": usage.get("total_cost_usd", 0),
                },
                "recommendations": [],
                "total_estimated_monthly_savings_usd": 0.0,
                "analysis_period_days": days,
                "data_completeness": usage.get("data_completeness", 0),
                "warning": "Insufficient data for recommendations. Need at least 3 days of usage data.",
            }

        gpu_type = usage.get("gpu_type", "Unknown")
        avg_utilization = usage.get("avg_utilization", 0)
        memory_utilization = usage.get("memory_avg", 0)

        # 2. GPU matching recommendation
        gpu_rec = self.match_gpu_to_workload(gpu_type, avg_utilization, memory_utilization)
        if gpu_rec.get("recommendation_type") != "keep":
            recommendations.append(gpu_rec)

        # 3. Hibernation optimization
        hibernation_rec = self._calculate_hibernation_setting(usage.get("idle_periods", []))
        if hibernation_rec.get("timeout_minutes") != current_hibernation_timeout:
            recommendations.append({
                "type": "hibernation",
                "current_timeout_minutes": current_hibernation_timeout,
                "recommended_timeout_minutes": hibernation_rec["timeout_minutes"],
                "reason": hibernation_rec["reason"],
                "estimated_monthly_savings_usd": hibernation_rec["estimated_monthly_savings_usd"],
                "confidence_score": hibernation_rec["confidence_score"],
            })

        # 4. Try to get spot timing recommendations
        spot_rec = self._get_spot_timing_recommendation(gpu_type)
        if spot_rec:
            recommendations.append(spot_rec)

        # Calculate total savings
        total_savings = self.calculate_total_savings(recommendations)

        # Estimate current monthly cost
        gpu_info = GPU_TIERS.get(gpu_type, {"price_per_hour": 0.50})
        estimated_monthly_cost = gpu_info["price_per_hour"] * usage.get("total_runtime_hours", 0)

        return {
            "current_configuration": {
                "gpu_type": gpu_type,
                "avg_utilization": avg_utilization,
                "monthly_cost_usd": round(estimated_monthly_cost, 2),
            },
            "recommendations": recommendations,
            "total_estimated_monthly_savings_usd": total_savings,
            "analysis_period_days": days,
            "data_completeness": usage.get("data_completeness", 0),
        }

    def _get_spot_timing_recommendation(
        self,
        gpu_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get spot timing recommendation from price prediction service.

        Args:
            gpu_type: GPU type to get recommendations for

        Returns:
            Spot timing recommendation dict or None if unavailable
        """
        try:
            pps = self._get_price_prediction_service()
            if not pps:
                return None

            # Try to get prediction
            prediction = pps.predict(gpu_type, "interruptible")
            if not prediction:
                return None

            best_hour = prediction.get("best_hour_utc", 0)
            best_day = prediction.get("best_day", "unknown")
            confidence = prediction.get("model_confidence", 0.5)

            # Only recommend spot instances if confidence is high enough
            if confidence < 0.70:
                return None

            # Calculate estimated savings (spot typically 30-50% cheaper)
            gpu_info = GPU_TIERS.get(gpu_type, {"price_per_hour": 0.50})
            spot_discount = 0.35  # Assume 35% average savings
            monthly_hours = 200  # Assume 200 hours of spot-eligible workloads
            estimated_savings = gpu_info["price_per_hour"] * spot_discount * monthly_hours

            return {
                "type": "spot_timing",
                "recommended_windows": [
                    {"day": best_day.capitalize(), "hours": f"{best_hour}:00-{(best_hour+4)%24}:00 UTC"},
                ],
                "reason": f"Price prediction shows lower spot prices during these windows with {confidence*100:.0f}% confidence",
                "estimated_monthly_savings_usd": round(estimated_savings, 2),
                "confidence_score": confidence,
            }

        except Exception as e:
            logger.warning(f"Could not get spot timing recommendation: {e}")
            return None

    def _get_all_recommendations(
        self,
        user_id: str,
        instance_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations as a list.

        Helper method for testing and API responses.
        """
        result = self.get_comprehensive_recommendations(user_id, instance_id, 0, days)
        return result.get("recommendations", [])


# Singleton instance for convenience
cost_optimization_service = CostOptimizationService()

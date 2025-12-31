"""
Recommendation generator for weekly email reports.

Generates 2-3 actionable optimization tips based on usage patterns.
Uses rule-based logic to provide personalized recommendations.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class RecommendationType(Enum):
    """Types of recommendations that can be generated."""
    COST_OPTIMIZATION = "cost_optimization"
    PERFORMANCE = "performance"
    USAGE_PATTERN = "usage_pattern"
    GPU_SELECTION = "gpu_selection"
    HIBERNATION = "hibernation"
    SPOT_INSTANCE = "spot_instance"
    RIGHT_SIZING = "right_sizing"


@dataclass
class Recommendation:
    """A single optimization recommendation."""

    title: str
    description: str
    recommendation_type: RecommendationType
    priority: int  # 1 = highest, 3 = lowest
    potential_savings: Optional[float] = None  # Estimated savings in USD
    action_url: Optional[str] = None  # Link to take action

    def to_dict(self) -> Dict:
        """Convert to dictionary for template rendering."""
        return {
            'title': self.title,
            'description': self.description,
            'type': self.recommendation_type.value,
            'priority': self.priority,
            'potential_savings': self.potential_savings,
            'action_url': self.action_url,
        }


class EmailRecommendationGenerator:
    """
    Generates personalized recommendations based on usage patterns.

    Analyzes:
    - GPU utilization patterns
    - Cost trends
    - Auto-hibernation opportunities
    - Right-sizing opportunities
    - Spot instance eligibility
    """

    # Thresholds for recommendations
    HIGH_COST_THRESHOLD = 100.0  # USD per week
    LOW_USAGE_HOURS_THRESHOLD = 5.0  # Hours per week
    HIGH_USAGE_HOURS_THRESHOLD = 100.0  # Hours per week
    SAVINGS_OPPORTUNITY_THRESHOLD = 0.20  # 20% potential savings
    HIBERNATION_SAVINGS_THRESHOLD = 10.0  # USD saved by auto-hibernation

    # GPU tier mappings for right-sizing
    GPU_TIERS = {
        'low': ['RTX_3060', 'RTX_4060', 'T4'],
        'mid': ['RTX_3070', 'RTX_4070', 'RTX_3080', 'RTX_4080', 'A4000'],
        'high': ['RTX_3090', 'RTX_4090', 'A5000', 'A6000', 'L40', 'L40S'],
        'premium': ['A100', 'H100', 'H200'],
    }

    def __init__(self):
        self.recommendations: List[Recommendation] = []

    def generate(
        self,
        current_week: Dict,
        previous_week: Dict,
        week_over_week: Dict,
        gpu_breakdown: List[Dict]
    ) -> List[Recommendation]:
        """
        Generate recommendations based on usage data.

        Args:
            current_week: Current week metrics from aggregate_user_usage()
            previous_week: Previous week metrics
            week_over_week: Week-over-week comparison
            gpu_breakdown: GPU usage breakdown

        Returns:
            List of 2-3 prioritized recommendations
        """
        self.recommendations = []

        # Skip if no usage
        if not current_week.get('has_usage', False):
            return self._get_no_usage_recommendations()

        # Analyze patterns and generate recommendations
        self._analyze_cost_patterns(current_week, week_over_week)
        self._analyze_hibernation_savings(current_week)
        self._analyze_gpu_selection(gpu_breakdown, current_week)
        self._analyze_usage_patterns(current_week, week_over_week)
        self._analyze_spot_opportunities(gpu_breakdown)
        self._analyze_right_sizing(gpu_breakdown, current_week)

        # Sort by priority and return top 3
        self.recommendations.sort(key=lambda r: r.priority)
        return self.recommendations[:3]

    def _get_no_usage_recommendations(self) -> List[Recommendation]:
        """Recommendations for users with no usage."""
        return [
            Recommendation(
                title="Get Started with GPU Computing",
                description="Launch your first GPU instance to start training models or running inference. Our AI Wizard can help you choose the right GPU for your workload.",
                recommendation_type=RecommendationType.USAGE_PATTERN,
                priority=1,
                action_url="/ai-wizard"
            ),
            Recommendation(
                title="Explore Available GPUs",
                description="Browse our catalog of GPUs from RTX 4060 to H100. Find the perfect balance of performance and cost for your project.",
                recommendation_type=RecommendationType.GPU_SELECTION,
                priority=2,
                action_url="/marketplace"
            ),
        ]

    def _analyze_cost_patterns(self, current_week: Dict, week_over_week: Dict) -> None:
        """Analyze cost trends and generate recommendations."""
        cost = current_week.get('total_cost_dumont', 0)
        cost_trend = week_over_week.get('cost_trend', 'stable')
        cost_change = week_over_week.get('cost_change_percent', 0)

        # High cost with increasing trend
        if cost > self.HIGH_COST_THRESHOLD and cost_trend == 'up' and cost_change > 20:
            self.recommendations.append(Recommendation(
                title="Cost Alert: Usage Up Significantly",
                description=f"Your GPU costs increased {abs(cost_change):.0f}% this week. Consider using auto-hibernation or spot instances to reduce costs during low-activity periods.",
                recommendation_type=RecommendationType.COST_OPTIMIZATION,
                priority=1,
                potential_savings=cost * 0.15,  # Estimate 15% savings possible
                action_url="/settings/hibernation"
            ))

        # Stable high costs - optimization opportunity
        elif cost > self.HIGH_COST_THRESHOLD * 2:
            savings_vs_aws = current_week.get('savings_vs_aws', 0)
            self.recommendations.append(Recommendation(
                title="Maximize Your Savings",
                description=f"You're already saving ${savings_vs_aws:.0f} vs AWS this week! Enable spot instances for batch workloads to save an additional 30-50%.",
                recommendation_type=RecommendationType.SPOT_INSTANCE,
                priority=2,
                potential_savings=cost * 0.30,
                action_url="/settings/spot-instances"
            ))

    def _analyze_hibernation_savings(self, current_week: Dict) -> None:
        """Analyze auto-hibernation effectiveness."""
        hibernate_savings = current_week.get('auto_hibernate_savings', 0)

        if hibernate_savings >= self.HIBERNATION_SAVINGS_THRESHOLD:
            self.recommendations.append(Recommendation(
                title="Auto-Hibernation is Working!",
                description=f"Auto-hibernation saved you ${hibernate_savings:.2f} this week by automatically stopping idle instances. Keep it enabled for continued savings.",
                recommendation_type=RecommendationType.HIBERNATION,
                priority=3
            ))
        elif hibernate_savings == 0:
            total_hours = current_week.get('total_hours', 0)
            if total_hours > self.LOW_USAGE_HOURS_THRESHOLD:
                self.recommendations.append(Recommendation(
                    title="Enable Auto-Hibernation",
                    description="Automatically pause instances when idle to avoid paying for unused GPU time. Most users save 10-30% on their monthly bills.",
                    recommendation_type=RecommendationType.HIBERNATION,
                    priority=2,
                    potential_savings=current_week.get('total_cost_dumont', 0) * 0.15,
                    action_url="/settings/hibernation"
                ))

    def _analyze_gpu_selection(self, gpu_breakdown: List[Dict], current_week: Dict) -> None:
        """Analyze GPU selection patterns."""
        if not gpu_breakdown:
            return

        # Check for premium GPU usage with low hours
        for gpu in gpu_breakdown:
            gpu_type = gpu.get('gpu_type', '')
            hours = gpu.get('hours', 0)

            is_premium = any(premium in gpu_type for premium in self.GPU_TIERS['premium'])
            is_high = any(high in gpu_type for high in self.GPU_TIERS['high'])

            if (is_premium or is_high) and hours < 10:
                self.recommendations.append(Recommendation(
                    title="Consider Right-Sizing Your GPU",
                    description=f"You used a {gpu_type} for only {hours:.1f} hours. For shorter workloads, a mid-tier GPU like RTX 4080 or A4000 might offer better value.",
                    recommendation_type=RecommendationType.RIGHT_SIZING,
                    priority=2,
                    action_url="/ai-wizard"
                ))
                break

    def _analyze_usage_patterns(self, current_week: Dict, week_over_week: Dict) -> None:
        """Analyze usage patterns for insights."""
        hours = current_week.get('total_hours', 0)
        sessions = current_week.get('total_sessions', 0)
        is_first_week = current_week.get('is_first_week', False)

        # First week user
        if is_first_week:
            self.recommendations.append(Recommendation(
                title="Welcome to DumontCloud!",
                description="Thanks for trying us out! Check out our documentation for tips on optimizing your GPU workflows and maximizing performance.",
                recommendation_type=RecommendationType.USAGE_PATTERN,
                priority=1,
                action_url="/docs/getting-started"
            ))
            return

        # High usage user
        if hours > self.HIGH_USAGE_HOURS_THRESHOLD:
            self.recommendations.append(Recommendation(
                title="Power User Detected!",
                description=f"With {hours:.0f} hours this week, you might benefit from our reserved capacity plans. Lock in lower rates for predictable workloads.",
                recommendation_type=RecommendationType.COST_OPTIMIZATION,
                priority=2,
                action_url="/pricing/reserved"
            ))

        # Many short sessions - might benefit from persistent instances
        if sessions > 10 and hours / sessions < 0.5:
            self.recommendations.append(Recommendation(
                title="Optimize Your Workflow",
                description="You're running many short sessions. Consider using persistent instances to avoid startup time and reduce context switching.",
                recommendation_type=RecommendationType.USAGE_PATTERN,
                priority=3,
                action_url="/docs/persistent-instances"
            ))

    def _analyze_spot_opportunities(self, gpu_breakdown: List[Dict]) -> None:
        """Identify spot instance opportunities."""
        if not gpu_breakdown:
            return

        # High-tier GPUs are good candidates for spot pricing
        for gpu in gpu_breakdown:
            gpu_type = gpu.get('gpu_type', '')
            cost = gpu.get('cost_dumont', 0)

            is_high_tier = any(
                tier_gpu in gpu_type
                for tier_gpu in self.GPU_TIERS['high'] + self.GPU_TIERS['premium']
            )

            if is_high_tier and cost > 50:
                self.recommendations.append(Recommendation(
                    title="Save with Spot Instances",
                    description=f"Your {gpu_type} usage could save up to 50% with spot pricing. Ideal for fault-tolerant workloads like batch training or data processing.",
                    recommendation_type=RecommendationType.SPOT_INSTANCE,
                    priority=2,
                    potential_savings=cost * 0.40,
                    action_url="/docs/spot-instances"
                ))
                break

    def _analyze_right_sizing(self, gpu_breakdown: List[Dict], current_week: Dict) -> None:
        """Analyze if user could benefit from different GPU tiers."""
        if not gpu_breakdown or len(gpu_breakdown) < 2:
            return

        # User is already using multiple GPU types - suggest optimization
        unique_gpus = current_week.get('unique_gpus_used', 0)
        if unique_gpus >= 3:
            self.recommendations.append(Recommendation(
                title="GPU Portfolio Optimization",
                description=f"You used {unique_gpus} different GPU types this week. Our AI Wizard can help identify the optimal GPU for each workload type.",
                recommendation_type=RecommendationType.GPU_SELECTION,
                priority=3,
                action_url="/ai-wizard"
            ))


def generate_recommendations(
    current_week: Dict,
    previous_week: Optional[Dict] = None,
    week_over_week: Optional[Dict] = None,
    gpu_breakdown: Optional[List[Dict]] = None
) -> List[Dict]:
    """
    Convenience function to generate recommendations.

    Args:
        current_week: Current week metrics from aggregate_user_usage()
        previous_week: Previous week metrics (optional)
        week_over_week: Week-over-week comparison (optional)
        gpu_breakdown: GPU usage breakdown (optional)

    Returns:
        List of recommendation dictionaries ready for email templates
    """
    generator = EmailRecommendationGenerator()

    # Provide defaults for optional parameters
    if previous_week is None:
        previous_week = {'has_usage': False}
    if week_over_week is None:
        week_over_week = {
            'hours_change_percent': 0,
            'cost_change_percent': 0,
            'hours_trend': 'stable',
            'cost_trend': 'stable',
            'has_previous_week': False
        }
    if gpu_breakdown is None:
        gpu_breakdown = []

    recommendations = generator.generate(
        current_week=current_week,
        previous_week=previous_week,
        week_over_week=week_over_week,
        gpu_breakdown=gpu_breakdown
    )

    return [rec.to_dict() for rec in recommendations]

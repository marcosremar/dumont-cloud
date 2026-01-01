#!/usr/bin/env python3
"""
Standalone Verification Script for Cost Optimization Flow

This script verifies the cost optimization service functionality
without requiring a running server or database connection.

Run from project root with: python3 src/tests/e2e/verify_cost_optimization.py
"""

import sys
import os

# Determine the correct path to add
# This script is at: src/tests/e2e/verify_cost_optimization.py
# We need to add the project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: e2e -> tests -> src -> project_root
src_dir = os.path.dirname(os.path.dirname(script_dir))  # src/
project_root = os.path.dirname(src_dir)  # project root

# Add both project root and src to path
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)


def verify_service_import():
    """Verify CostOptimizationService can be imported."""
    try:
        from src.services.cost_optimization_service import CostOptimizationService
        print("✓ CostOptimizationService imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import CostOptimizationService: {e}")
        return False


def verify_gpu_matching_algorithm():
    """Verify GPU matching algorithm works correctly."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    # Test 1: Underutilized GPU (< 50%) should recommend downgrade
    result = service.match_gpu_to_workload("RTX_4090", 30.0, 20.0)
    assert result["recommendation_type"] == "downgrade", f"Expected downgrade for 30% util, got {result['recommendation_type']}"
    assert result["type"] == "gpu_downgrade", f"Expected gpu_downgrade type"
    assert result["estimated_monthly_savings_usd"] > 0, "Expected positive savings for downgrade"
    print(f"✓ Underutilized (30%) → downgrade recommendation (saves ${result['estimated_monthly_savings_usd']:.2f}/mo)")

    # Test 2: Overutilized GPU (> 95%) should recommend upgrade
    result = service.match_gpu_to_workload("RTX_4060", 98.0, 80.0)
    assert result["recommendation_type"] == "upgrade", f"Expected upgrade for 98% util, got {result['recommendation_type']}"
    print(f"✓ Overutilized (98%) → upgrade recommendation")

    # Test 3: Optimal utilization (50-95%) should keep current GPU
    result = service.match_gpu_to_workload("RTX_4090", 70.0, 50.0)
    assert result["recommendation_type"] == "keep", f"Expected keep for 70% util, got {result['recommendation_type']}"
    print(f"✓ Optimal (70%) → keep current GPU")

    return True


def verify_hibernation_optimizer():
    """Verify hibernation optimization algorithm."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    # Test with idle periods
    idle_periods = [60, 90, 45, 120, 75, 80, 55]
    result = service._calculate_hibernation_setting(idle_periods)

    # Should recommend timeout of ~50% of median
    assert "timeout_minutes" in result, "Missing timeout_minutes"
    assert 15 <= result["timeout_minutes"] <= 120, f"Timeout {result['timeout_minutes']} out of bounds"
    assert 0 <= result["confidence_score"] <= 1, f"Confidence {result['confidence_score']} out of range"
    print(f"✓ Hibernation optimizer: {result['timeout_minutes']} min timeout (confidence: {result['confidence_score']:.2f})")

    # Test with no idle periods
    result = service._calculate_hibernation_setting([])
    assert result["timeout_minutes"] == 30, "Should default to 30 min with no data"
    print(f"✓ No data → default 30 min timeout")

    return True


def verify_utilization_analysis():
    """Verify GPU utilization analysis."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    # Test underutilized case
    records = [{"gpu_utilization": 25}, {"gpu_utilization": 30}, {"gpu_utilization": 35}]
    result = service._analyze_gpu_utilization(records)

    assert result["recommendation_type"] == "downgrade", f"Expected downgrade, got {result['recommendation_type']}"
    assert 25 <= result["avg_utilization"] <= 35, f"Avg utilization {result['avg_utilization']} unexpected"
    print(f"✓ Low utilization analysis: avg={result['avg_utilization']}% → {result['recommendation_type']}")

    # Test high variance case
    records = [{"gpu_utilization": 10}, {"gpu_utilization": 90}, {"gpu_utilization": 20}, {"gpu_utilization": 80}]
    result = service._analyze_gpu_utilization(records)

    assert result["needs_manual_review"] == True, "High variance should flag for manual review"
    print(f"✓ High variance detected, flagged for manual review")

    return True


def verify_spot_timing_recommendation():
    """Verify spot timing recommendations work."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    # Get spot timing for a GPU
    result = service._get_spot_timing_recommendation("RTX_4090")

    assert result is not None, "Should return spot recommendation"
    assert result["type"] == "spot_timing", f"Expected spot_timing type, got {result['type']}"
    assert "recommended_windows" in result, "Missing recommended_windows"
    assert 0 <= result["confidence_score"] <= 1, f"Confidence {result['confidence_score']} out of range"
    print(f"✓ Spot timing recommendation: {len(result['recommended_windows'])} windows (confidence: {result['confidence_score']:.2f})")

    return True


def verify_total_savings_calculation():
    """Verify total savings calculation."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    recommendations = [
        {"type": "gpu_downgrade", "estimated_monthly_savings_usd": 100.50},
        {"type": "hibernation", "estimated_monthly_savings_usd": 45.25},
        {"type": "spot_timing", "estimated_monthly_savings_usd": 30.00},
    ]

    total = service.calculate_total_savings(recommendations)
    expected = 100.50 + 45.25 + 30.00

    assert abs(total - expected) < 0.01, f"Expected {expected}, got {total}"
    print(f"✓ Total savings calculation: ${total:.2f} (sum of ${100.50} + ${45.25} + ${30.00})")

    return True


def verify_confidence_score_range():
    """Verify all confidence scores are in 0-1 range."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    # Test various scenarios
    test_cases = [
        (service.match_gpu_to_workload, ("RTX_4090", 30.0, 20.0)),
        (service.match_gpu_to_workload, ("RTX_4090", 70.0, 50.0)),
        (service.match_gpu_to_workload, ("RTX_4060", 98.0, 80.0)),
        (service._calculate_hibernation_setting, ([60, 90, 45],)),
        (service._get_spot_timing_recommendation, ("RTX_4090",)),
    ]

    for func, args in test_cases:
        result = func(*args)
        if result and "confidence_score" in result:
            score = result["confidence_score"]
            assert 0 <= score <= 1, f"Confidence {score} out of range for {func.__name__}"

    print(f"✓ All confidence scores in valid range [0, 1]")
    return True


def verify_all_recommendations_helper():
    """Verify _get_all_recommendations includes spot timing."""
    from src.services.cost_optimization_service import CostOptimizationService

    service = CostOptimizationService()

    # This method should always return spot timing even without user data
    recs = service._get_all_recommendations("test_user", "test_instance", 30)

    rec_types = [r.get("type") for r in recs]
    assert "spot_timing" in rec_types, "Should include spot_timing recommendation"
    print(f"✓ _get_all_recommendations includes spot_timing even without user data")

    return True


def run_verification():
    """Run all verification checks."""
    checks = [
        ("Service Import", verify_service_import),
        ("GPU Matching Algorithm", verify_gpu_matching_algorithm),
        ("Hibernation Optimizer", verify_hibernation_optimizer),
        ("Utilization Analysis", verify_utilization_analysis),
        ("Spot Timing Recommendation", verify_spot_timing_recommendation),
        ("Total Savings Calculation", verify_total_savings_calculation),
        ("Confidence Score Range", verify_confidence_score_range),
        ("All Recommendations Helper", verify_all_recommendations_helper),
    ]

    print("=" * 60)
    print("Cost Optimization Verification")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, check in checks:
        print(f"\n--- {name} ---")
        try:
            if check():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name} failed")
        except Exception as e:
            failed += 1
            print(f"✗ {name} error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)

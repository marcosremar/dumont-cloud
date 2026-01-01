#!/usr/bin/env python3
"""Test script to check if vast.ai has CPU-only offers available"""

import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.gpu.vast import VastService
from src.core.config import get_settings

def test_cpu_offers():
    """Test if CPU offers are available"""
    settings = get_settings()
    vast = VastService(settings.vast.api_key)

    print("=" * 80)
    print("Testing CPU-only offers from vast.ai")
    print("=" * 80)

    # Test 1: Very relaxed filters
    print("\n[Test 1] Very relaxed filters (max_price=$2.00, min 2 cores, 4GB RAM)...")
    offers = vast.search_cpu_offers(
        min_cpu_cores=2,
        min_cpu_ram=4,
        min_disk=20,
        min_inet_down=50,
        max_price=2.00,
        limit=10
    )
    print(f"Found {len(offers)} offers")
    if offers:
        print("\nFirst 3 offers:")
        for i, offer in enumerate(offers[:3]):
            print(f"  {i+1}. CPU: {offer.get('cpu_cores')}c/{offer.get('cpu_ram')/1024:.1f}GB - "
                  f"${offer.get('dph_total', 0):.4f}/hr - {offer.get('geolocation', 'Unknown')}")
    else:
        print("  ❌ NO CPU OFFERS FOUND!")

    # Test 2: Ultra relaxed - any CPU offer
    print("\n[Test 2] Ultra relaxed (max_price=$5.00, min 1 core, 1GB RAM)...")
    offers = vast.search_cpu_offers(
        min_cpu_cores=1,
        min_cpu_ram=1,
        min_disk=10,
        min_inet_down=10,
        max_price=5.00,
        limit=10
    )
    print(f"Found {len(offers)} offers")
    if offers:
        print("\nFirst 3 offers:")
        for i, offer in enumerate(offers[:3]):
            print(f"  {i+1}. CPU: {offer.get('cpu_cores')}c/{offer.get('cpu_ram')/1024:.1f}GB - "
                  f"${offer.get('dph_total', 0):.4f}/hr - {offer.get('geolocation', 'Unknown')}")
    else:
        print("  ❌ NO CPU OFFERS FOUND!")

    # Test 3: Default filters from migration service
    print("\n[Test 3] Default migration filters (max_price=$2.00, 4 cores, 8GB RAM)...")
    offers = vast.search_cpu_offers(
        min_cpu_cores=4,
        min_cpu_ram=8,
        min_disk=50,
        max_price=2.00,
        limit=10
    )
    print(f"Found {len(offers)} offers")
    if offers:
        print("\nFirst 3 offers:")
        for i, offer in enumerate(offers[:3]):
            print(f"  {i+1}. CPU: {offer.get('cpu_cores')}c/{offer.get('cpu_ram')/1024:.1f}GB - "
                  f"${offer.get('dph_total', 0):.4f}/hr - {offer.get('geolocation', 'Unknown')}")
    else:
        print("  ❌ NO CPU OFFERS FOUND!")
        print("\nThis is likely why 'Migrar para CPU' is failing!")

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    if not any([len(offers) > 0 for _ in [1, 2, 3]]):
        print("❌ VAST.AI DOES NOT APPEAR TO HAVE CPU-ONLY OFFERS AVAILABLE")
        print("   This is the root cause of the 'No cpu offers found' error.")
        print("\nPOSSIBLE SOLUTIONS:")
        print("1. Vast.ai may not offer CPU-only instances (they focus on GPU rentals)")
        print("2. Consider using GCP/AWS for CPU instances instead")
        print("3. Disable the 'Migrar para CPU' feature in the UI")
    else:
        print("✅ CPU offers are available from vast.ai")

if __name__ == "__main__":
    test_cpu_offers()

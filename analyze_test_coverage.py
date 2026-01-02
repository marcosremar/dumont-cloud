#!/usr/bin/env python3
"""
Analyze test coverage for API endpoints
"""
import re
import os
from pathlib import Path
from collections import defaultdict

def extract_api_calls_from_tests(test_dir):
    """Extract all API endpoint calls from test files"""
    api_calls = set()
    test_files = defaultdict(set)

    for test_file in Path(test_dir).rglob("*.py"):
        if test_file.name in ["__init__.py", "__pycache__"]:
            continue

        try:
            with open(test_file, 'r') as f:
                content = f.read()

            # Find API calls in various formats
            patterns = [
                # requests.get/post/etc
                r'requests\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                # client.get/post/etc
                r'client\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                # self.client.get/post/etc
                r'self\.client\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                # response = get/post/etc
                r'(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                # f"/api/v1/{something}"
                r'f?["\']/(api/v1/)?([^"\'{}]+)["\']',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if len(match) == 2:
                        method, path = match
                    else:
                        path = match
                        method = "UNKNOWN"

                    # Clean path
                    path = path.strip()
                    if not path:
                        continue

                    # Remove /api/v1 prefix for consistency
                    path = path.replace("/api/v1", "")
                    if not path.startswith("/"):
                        path = "/" + path

                    # Skip non-API paths
                    if path in ["/", "/docs", "/openapi.json"]:
                        continue

                    # Add to sets
                    if method != "UNKNOWN":
                        endpoint = f"{method.upper()} {path}"
                        api_calls.add(endpoint)
                        test_files[endpoint].add(str(test_file.relative_to(test_dir.parent)))

        except Exception as e:
            print(f"Error processing {test_file}: {e}")

    return api_calls, test_files

def load_api_routes(routes_file):
    """Load all API routes from the routes file"""
    routes = []
    with open(routes_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Total") or line.startswith("="):
                continue

            parts = line.split()
            if len(parts) >= 2:
                method = parts[0]
                path = parts[1]
                routes.append(f"{method} {path}")

    return set(routes)

def main():
    base_dir = Path("/Users/marcos/CascadeProjects/dumontcloud")
    routes_file = base_dir / "api_routes.txt"
    test_dir = base_dir / "tests"

    print("=" * 80)
    print("API ENDPOINT TEST COVERAGE ANALYSIS")
    print("=" * 80)
    print()

    # Load all API routes
    print("Loading API routes...")
    all_routes = load_api_routes(routes_file)
    print(f"Total API endpoints defined: {len(all_routes)}")
    print()

    # Extract API calls from tests
    print("Analyzing test files...")
    tested_endpoints, test_files_map = extract_api_calls_from_tests(test_dir)
    print(f"Total tested endpoints found: {len(tested_endpoints)}")
    print()

    # Find coverage
    covered = []
    uncovered = []

    for route in sorted(all_routes):
        # Check exact match
        if route in tested_endpoints:
            covered.append(route)
        else:
            # Check without path parameters
            route_base = re.sub(r'\{[^}]+\}', '*', route)
            found = False
            for tested in tested_endpoints:
                tested_base = re.sub(r'\{[^}]+\}', '*', tested)
                if route_base == tested_base:
                    covered.append(route)
                    found = True
                    break

            if not found:
                uncovered.append(route)

    # Calculate coverage
    coverage_pct = (len(covered) / len(all_routes) * 100) if all_routes else 0

    print("=" * 80)
    print(f"COVERAGE SUMMARY")
    print("=" * 80)
    print(f"Total Endpoints:     {len(all_routes)}")
    print(f"Tested Endpoints:    {len(covered)} ({coverage_pct:.1f}%)")
    print(f"Untested Endpoints:  {len(uncovered)} ({100-coverage_pct:.1f}%)")
    print()

    # Show coverage by prefix
    print("=" * 80)
    print("COVERAGE BY API PREFIX")
    print("=" * 80)

    by_prefix = defaultdict(lambda: {"total": 0, "covered": 0})
    for route in all_routes:
        prefix = route.split()[1].split('/')[1] if '/' in route.split()[1] else 'root'
        by_prefix[prefix]["total"] += 1
        if route in covered:
            by_prefix[prefix]["covered"] += 1

    for prefix in sorted(by_prefix.keys()):
        stats = by_prefix[prefix]
        pct = (stats["covered"] / stats["total"] * 100) if stats["total"] else 0
        print(f"  /{prefix:30s} {stats['covered']:3d}/{stats['total']:3d} ({pct:5.1f}%)")

    # Show untested endpoints
    if uncovered:
        print()
        print("=" * 80)
        print(f"UNTESTED ENDPOINTS ({len(uncovered)})")
        print("=" * 80)

        # Group by prefix
        uncovered_by_prefix = defaultdict(list)
        for route in uncovered:
            prefix = route.split()[1].split('/')[1] if '/' in route.split()[1] else 'root'
            uncovered_by_prefix[prefix].append(route)

        for prefix in sorted(uncovered_by_prefix.keys()):
            print(f"\n/{prefix}:")
            print("-" * 80)
            for route in sorted(uncovered_by_prefix[prefix]):
                print(f"  {route}")

    # Show high-priority untested endpoints
    priority_prefixes = ["auth", "instances", "models", "jobs", "serverless", "failover"]
    priority_uncovered = [r for r in uncovered if any(f"/{p}" in r for p in priority_prefixes)]

    if priority_uncovered:
        print()
        print("=" * 80)
        print(f"HIGH PRIORITY UNTESTED ENDPOINTS ({len(priority_uncovered)})")
        print("=" * 80)
        for route in sorted(priority_uncovered):
            print(f"  {route}")

    # Save detailed report
    output_file = base_dir / "test_coverage_report.txt"
    with open(output_file, 'w') as f:
        f.write(f"API TEST COVERAGE REPORT\n")
        f.write(f"Generated: {__import__('datetime').datetime.now()}\n")
        f.write(f"=" * 80 + "\n\n")
        f.write(f"Total Endpoints:     {len(all_routes)}\n")
        f.write(f"Tested Endpoints:    {len(covered)} ({coverage_pct:.1f}%)\n")
        f.write(f"Untested Endpoints:  {len(uncovered)} ({100-coverage_pct:.1f}%)\n\n")

        f.write(f"=" * 80 + "\n")
        f.write(f"UNTESTED ENDPOINTS\n")
        f.write(f"=" * 80 + "\n\n")
        for route in sorted(uncovered):
            f.write(f"{route}\n")

    print(f"\n\nDetailed report saved to: {output_file}")

if __name__ == "__main__":
    main()

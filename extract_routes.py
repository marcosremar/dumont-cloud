#!/usr/bin/env python3
"""
Extract all API routes from endpoint files
"""
import re
import os
from pathlib import Path
from collections import defaultdict

def extract_routes_from_file(file_path):
    """Extract all router decorators from a Python file"""
    routes = []

    with open(file_path, 'r') as f:
        content = f.read()

    # Find router prefix
    prefix_match = re.search(r'router\s*=\s*APIRouter\([^)]*prefix\s*=\s*["\']([^"\']+)["\']', content)
    prefix = prefix_match.group(1) if prefix_match else ""

    # Find all route decorators
    patterns = [
        r'@router\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']',
        r'@router\.(get|post|put|patch|delete)\("([^"]+)"',
        r"@router\.(get|post|put|patch|delete)\('([^']+)'",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        for method, path in matches:
            # Handle path parameters
            full_path = f"{prefix}{path}"
            routes.append({
                'method': method.upper(),
                'path': full_path,
                'file': str(file_path)
            })

    return routes, prefix

def main():
    base_dir = Path("/Users/marcos/CascadeProjects/dumontcloud/src/api/v1/endpoints")

    all_routes = []
    by_file = defaultdict(list)

    # Process all Python files
    for file_path in sorted(base_dir.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue

        try:
            routes, prefix = extract_routes_from_file(file_path)
            relative_path = file_path.relative_to(base_dir.parent.parent.parent.parent)

            for route in routes:
                route['file'] = str(relative_path)
                all_routes.append(route)
                by_file[str(relative_path)].append(route)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    # Print summary
    print(f"=" * 80)
    print(f"TOTAL API ENDPOINTS FOUND: {len(all_routes)}")
    print(f"=" * 80)
    print()

    # Group by file
    print("ENDPOINTS BY FILE:")
    print("=" * 80)

    for file_path in sorted(by_file.keys()):
        routes = by_file[file_path]
        print(f"\n{file_path} ({len(routes)} endpoints):")
        print("-" * 80)

        for route in sorted(routes, key=lambda x: x['path']):
            print(f"  {route['method']:6s} {route['path']}")

    # Group by prefix
    print("\n\n" + "=" * 80)
    print("ENDPOINTS BY PREFIX:")
    print("=" * 80)

    by_prefix = defaultdict(list)
    for route in all_routes:
        prefix = route['path'].split('/')[1] if '/' in route['path'] else '/'
        by_prefix[prefix].append(route)

    for prefix in sorted(by_prefix.keys()):
        routes = by_prefix[prefix]
        print(f"\n/{prefix} ({len(routes)} endpoints):")
        print("-" * 80)
        for route in sorted(routes, key=lambda x: (x['path'], x['method'])):
            print(f"  {route['method']:6s} {route['path']}")

    # Save to file
    output_file = "/Users/marcos/CascadeProjects/dumontcloud/api_routes.txt"
    with open(output_file, 'w') as f:
        f.write(f"Total API Endpoints: {len(all_routes)}\n")
        f.write("=" * 80 + "\n\n")

        for route in sorted(all_routes, key=lambda x: (x['path'], x['method'])):
            f.write(f"{route['method']:6s} {route['path']:50s} # {route['file']}\n")

    print(f"\n\nRoutes saved to: {output_file}")
    print(f"\nTOTAL: {len(all_routes)} API endpoints")

if __name__ == "__main__":
    main()

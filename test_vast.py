#!/usr/bin/env python3
import requests

API_KEY = "a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd"

# Testar diretamente a API vast.ai com query minima
query = {
    "rentable": {"eq": True},
    "num_gpus": {"eq": 1},
}

params = {
    "q": str(query).replace("'", '"'),
    "order": "dph_total",
    "type": "on-demand",
    "limit": 5,
}

print(f"Query params: {params}")

resp = requests.get(
    "https://console.vast.ai/api/v0/bundles",
    params=params,
    headers={"Authorization": f"Bearer {API_KEY}"},
    timeout=30,
)

print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Type of data: {type(data)}")
if isinstance(data, list):
    print(f"Count: {len(data)}")
    if data:
        print("First offer:", data[0].get("gpu_name"), data[0].get("dph_total"))
elif isinstance(data, dict):
    offers = data.get("offers", [])
    print(f"Count: {len(offers)}")
    print("Keys:", data.keys())
    if offers:
        print("First offer:", offers[0].get("gpu_name"), offers[0].get("dph_total"))

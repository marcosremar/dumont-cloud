#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.providers.vast_provider import VastProvider
from src.core.config import settings

provider = VastProvider(settings.vast.api_key)
instances = provider.list_instances()

print(f"\n📊 Total de máquinas: {len(instances)}\n")

for i in instances:
    status_emoji = "🟢" if i.actual_status == "running" else "🟡" if i.actual_status == "loading" else "🔴"
    print(f"{status_emoji} ID: {i.id}")
    print(f"   GPU: {i.gpu_name}")
    print(f"   Status: {i.actual_status}")
    print(f"   SSH: {i.ssh_host}:{i.ssh_port}")
    print(f"   Ports: {i.ports}")
    print()

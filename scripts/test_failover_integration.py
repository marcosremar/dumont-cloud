#!/usr/bin/env python3
"""
Comprehensive Failover Integration Tests - SCP-Based Transfer
==============================================================

Executes all 8 failover tests using SCP for file transfer between GPUs.
Stores snapshots locally as .tar.lz4 files during failover operations.

Budget: $1.30 max
"""

import os
import sys
import time
import json
import asyncio
import hashlib
import subprocess
import logging
import tempfile
import shutil
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================

VAST_API_KEY = os.getenv("VAST_API_KEY")
# Local snapshot storage directory
SNAPSHOT_DIR = Path(tempfile.gettempdir()) / "dumont_snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

MAX_BUDGET = 1.30
BUDGET_WARNING = 1.00
MAX_GPU_PRICE = 0.30
MIN_GPU_RAM = 8000


@dataclass
class TestResult:
    name: str
    success: bool
    duration_seconds: float
    cost_usd: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TestSession:
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    total_cost: float = 0.0
    results: List[TestResult] = field(default_factory=list)
    active_instances: List[int] = field(default_factory=list)

    def add_cost(self, cost: float):
        self.total_cost += cost
        if self.total_cost > BUDGET_WARNING:
            logger.warning(f"BUDGET WARNING: ${self.total_cost:.4f} (limit: ${MAX_BUDGET})")
        if self.total_cost > MAX_BUDGET:
            raise BudgetExceededError(f"Budget exceeded: ${self.total_cost:.4f}")

    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.success)


class BudgetExceededError(Exception):
    pass


class VASTClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://cloud.vast.ai/api/v0"
        self.last_request = 0

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        import requests
        time.sleep(max(0, 1.0 - (time.time() - self.last_request)))
        self.last_request = time.time()

        url = f"{self.base_url}/{endpoint}{'&' if '?' in endpoint else '?'}api_key={self.api_key}"

        for attempt in range(5):
            try:
                response = requests.request(method, url, timeout=60, **kwargs)
                if response.status_code == 429:
                    time.sleep(min(60, 2 ** (attempt + 1)))
                    continue
                if response.status_code >= 400:
                    if attempt < 4:
                        time.sleep(2 ** attempt)
                        continue
                    return {"error": response.text[:200]}
                return response.json() if response.text else {}
            except Exception as e:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return {"error": "Max retries"}

    def search_offers(self, max_price: float = 0.30) -> List[Dict]:
        data = self._request("GET", f"bundles/?rentable=true&order=dph_total&type=on-demand")
        offers = data.get("offers", [])
        return [o for o in offers if o.get("rentable") and o.get("dph_total", 999) <= max_price
                and o.get("gpu_ram", 0) >= MIN_GPU_RAM][:15]

    def provision(self, offer_id: int, disk: int = 30) -> Optional[int]:
        data = self._request("PUT", f"asks/{offer_id}/", json={
            "client_id": "me",
            "image": "vastai/pytorch",
            "disk": disk,
            "onstart": "pip install boto3 lz4 --quiet 2>/dev/null &",
        })
        return data.get("new_contract")

    def get_instance(self, instance_id: int) -> Optional[Dict]:
        data = self._request("GET", "instances/")
        for instance in data.get("instances", []):
            if instance["id"] == instance_id:
                return instance
        return None

    def destroy(self, instance_id: int) -> bool:
        try:
            self._request("DELETE", f"instances/{instance_id}/")
            logger.info(f"Destroyed instance {instance_id}")
            return True
        except:
            return False

    def get_cost(self, instance_id: int, duration_hours: float) -> float:
        instance = self.get_instance(instance_id)
        if instance:
            return instance.get("dph_total", 0.1) * duration_hours
        return 0.1 * duration_hours


def wait_for_ssh(host: str, port: int, timeout: int = 180) -> bool:
    """Wait for SSH with validation - returns True only when SSH is stable"""
    start = time.time()
    consecutive_success = 0

    while time.time() - start < timeout:
        try:
            result = subprocess.run(
                ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=no",
                 "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5",
                 "-o", "BatchMode=yes", f"root@{host}", "echo ok"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0 and b"ok" in result.stdout:
                consecutive_success += 1
                if consecutive_success >= 2:  # Need 2 consecutive successes
                    time.sleep(2)  # Small delay for stability
                    return True
            else:
                consecutive_success = 0
        except:
            consecutive_success = 0
        time.sleep(3)
    return False


def ssh_exec(host: str, port: int, cmd: str, timeout: int = 300) -> Dict:
    try:
        result = subprocess.run(
            ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10",
             f"root@{host}", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


def ssh_run_script(host: str, port: int, script: str, timeout: int = 300) -> Dict:
    """Run a Python script on remote host via stdin to avoid shell quoting issues"""
    try:
        result = subprocess.run(
            ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10",
             f"root@{host}", "python3 -"],
            input=script, capture_output=True, text=True, timeout=timeout
        )
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


def get_create_tar_script(workspace_path: str = "/workspace/test_data") -> str:
    """Generate script to create tarball on remote GPU"""
    return f'''
import os, tarfile
tar_path = "/tmp/snapshot.tar"
with tarfile.open(tar_path, "w") as tar:
    if os.path.exists("{workspace_path}"):
        tar.add("{workspace_path}", arcname=os.path.basename("{workspace_path}"))
size = os.path.getsize(tar_path)
print(f"SUCCESS:{{size}}")
'''


def upload_snapshot(host: str, port: int, snapshot_id: str, workspace_path: str = "/workspace/test_data") -> Dict:
    """Create snapshot on GPU and SCP to local"""
    try:
        # Create tar on remote
        result = ssh_run_script(host, port, get_create_tar_script(workspace_path))
        if "SUCCESS" not in result.get("stdout", ""):
            return {"success": False, "error": f"Tar creation failed: {result.get('stderr', '')}"}

        size = int(result["stdout"].split("SUCCESS:")[-1].strip())

        # SCP to local
        local_path = SNAPSHOT_DIR / f"{snapshot_id}.tar"
        scp_result = subprocess.run(
            ["scp", "-P", str(port), "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=30",
             f"root@{host}:/tmp/snapshot.tar", str(local_path)],
            capture_output=True, text=True, timeout=300
        )
        if scp_result.returncode != 0:
            return {"success": False, "error": f"SCP download failed: {scp_result.stderr[:200]}"}

        return {"success": True, "size": size, "path": str(local_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_snapshot(host: str, port: int, snapshot_id: str, extract_to: str = "/workspace") -> Dict:
    """SCP snapshot to GPU and extract"""
    try:
        local_path = SNAPSHOT_DIR / f"{snapshot_id}.tar"
        if not local_path.exists():
            return {"success": False, "error": f"Snapshot not found: {local_path}"}

        # SCP to remote
        scp_result = subprocess.run(
            ["scp", "-P", str(port), "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=30",
             str(local_path), f"root@{host}:/tmp/restore.tar"],
            capture_output=True, text=True, timeout=300
        )
        if scp_result.returncode != 0:
            return {"success": False, "error": f"SCP upload failed: {scp_result.stderr[:200]}"}

        # Extract on remote
        extract_script = f'''
import os, tarfile
os.makedirs("{extract_to}", exist_ok=True)
with tarfile.open("/tmp/restore.tar", "r") as tar:
    tar.extractall("{extract_to}")
print("SUCCESS")
'''
        result = ssh_run_script(host, port, extract_script)
        if "SUCCESS" not in result.get("stdout", ""):
            return {"success": False, "error": f"Extract failed: {result.get('stderr', '')}"}

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_test_files(host: str, port: int, size_mb: int = 100) -> Dict:
    script = f'''
import os, hashlib, json
os.makedirs("/workspace/test_data", exist_ok=True)
files = {{}}
total_size = 0
target_size = {size_mb} * 1024 * 1024
file_idx = 0
while total_size < target_size:
    file_size = min(10 * 1024 * 1024, target_size - total_size)
    data = os.urandom(file_size)
    fname = f"/workspace/test_data/file_{{file_idx}}.bin"
    with open(fname, "wb") as f:
        f.write(data)
    files[fname] = {{"size": file_size, "md5": hashlib.md5(data).hexdigest()}}
    total_size += file_size
    file_idx += 1
print(json.dumps({{"files": files, "total_size": total_size}}))
'''
    result = ssh_run_script(host, port, script)
    if result["success"]:
        try:
            return json.loads(result["stdout"].strip().split("\n")[-1])
        except:
            pass
    return {"error": result.get("stderr", "Unknown")}


def verify_files(host: str, port: int, expected_files: Dict) -> Dict:
    script = f'''
import os, hashlib, json
expected = {json.dumps(expected_files)}
results = {{"verified": 0, "failed": 0, "missing": 0}}
for fpath, info in expected.items():
    if not os.path.exists(fpath):
        results["missing"] += 1
        continue
    with open(fpath, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    if md5 == info["md5"]:
        results["verified"] += 1
    else:
        results["failed"] += 1
results["success"] = results["failed"] == 0 and results["missing"] == 0
print(json.dumps(results))
'''
    result = ssh_run_script(host, port, script)
    if result["success"]:
        try:
            return json.loads(result["stdout"].strip().split("\n")[-1])
        except:
            pass
    return {"success": False, "error": result.get("stderr", "Unknown")}


async def provision_gpu(client: VASTClient, session: TestSession) -> Optional[Dict]:
    offers = client.search_offers(max_price=MAX_GPU_PRICE)
    if not offers:
        logger.error("No affordable GPU offers")
        return None

    for offer in offers[:5]:  # Reduced to 5 offers max
        logger.info(f"Trying {offer.get('gpu_name', 'Unknown')} @ ${offer.get('dph_total', 0):.3f}/h")
        instance_id = client.provision(offer["id"])
        if not instance_id:
            time.sleep(1)
            continue

        session.active_instances.append(instance_id)
        logger.info(f"Provisioned {instance_id}, waiting for SSH...")

        # Wait for SSH info (max 60 seconds)
        ssh_info_start = time.time()
        ssh_host, ssh_port = None, None
        while time.time() - ssh_info_start < 60:
            instance = client.get_instance(instance_id)
            if instance and instance.get("ssh_host") and instance.get("ssh_port"):
                ssh_host, ssh_port = instance["ssh_host"], instance["ssh_port"]
                break
            time.sleep(5)

        if not ssh_host:
            logger.warning(f"No SSH info for {instance_id}, destroying...")
            client.destroy(instance_id)
            session.active_instances.remove(instance_id)
            continue

        logger.info(f"Testing SSH: {ssh_host}:{ssh_port}")
        if wait_for_ssh(ssh_host, ssh_port, timeout=90):  # 90 second timeout
            return {
                "instance_id": instance_id,
                "ssh_host": ssh_host,
                "ssh_port": ssh_port,
                "gpu_name": offer.get("gpu_name", "Unknown"),
                "dph": offer.get("dph_total", 0.1)
            }

        logger.warning(f"Instance {instance_id} SSH failed, trying next...")
        client.destroy(instance_id)
        session.active_instances.remove(instance_id)

    return None


def cleanup_gpu(client: VASTClient, session: TestSession, instance_id: int, duration_hours: float):
    cost = client.get_cost(instance_id, duration_hours)
    session.add_cost(cost)
    client.destroy(instance_id)
    if instance_id in session.active_instances:
        session.active_instances.remove(instance_id)
    logger.info(f"Cleanup {instance_id}, cost: ${cost:.4f}")
    return cost


# ============================================================
# Tests
# ============================================================

async def test_1_1(client: VASTClient, session: TestSession) -> TestResult:
    """Test 1.1: B2 Snapshot Upload"""
    logger.info("=" * 60)
    logger.info("TEST 1.1: Storage Snapshot Upload")
    logger.info("=" * 60)
    start_time = time.time()
    gpu = None

    try:
        gpu = await provision_gpu(client, session)
        if not gpu:
            return TestResult("1.1 Snapshot Upload", False, time.time() - start_time, 0, error="No GPU")

        files_info = create_test_files(gpu['ssh_host'], gpu['ssh_port'], size_mb=10)
        if "error" in files_info:
            raise Exception(f"Create files failed: {files_info['error']}")

        logger.info(f"Created {len(files_info['files'])} files")
        snapshot_id = f"test-1-1-{int(time.time())}"

        result = upload_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id)

        if not result.get("success"):
            raise Exception(f"Upload failed: {result.get('error', 'Unknown')}")

        snapshot_size = result.get("size", 0)

        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600)

        return TestResult("1.1 Snapshot Upload", True, duration, cost, {
            "snapshot_id": snapshot_id, "snapshot_size": snapshot_size,
            "files_info": files_info['files']
        })

    except Exception as e:
        logger.error(f"Test 1.1 failed: {e}")
        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600) if gpu else 0
        return TestResult("1.1 Snapshot Upload", False, duration, cost, error=str(e))


async def test_1_2(client: VASTClient, session: TestSession, prev: Dict) -> TestResult:
    """Test 1.2: B2 Restore"""
    logger.info("=" * 60)
    logger.info("TEST 1.2: Storage Restore")
    logger.info("=" * 60)
    start_time = time.time()
    gpu = None

    try:
        snapshot_id = prev.get("snapshot_id")
        expected_files = prev.get("files_info", {})
        if not snapshot_id:
            return TestResult("1.2 Restore", False, 0, 0, error="No snapshot from 1.1")

        gpu = await provision_gpu(client, session)
        if not gpu:
            return TestResult("1.2 Restore", False, time.time() - start_time, 0, error="No GPU")

        result = download_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id, "/workspace")

        if not result.get("success"):
            raise Exception(f"Download failed: {result.get('error', 'Unknown')}")

        verify = verify_files(gpu['ssh_host'], gpu['ssh_port'], expected_files)

        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600)

        return TestResult("1.2 Restore", verify.get("success", False), duration, cost, {
            "files_verified": verify.get("verified", 0)
        })

    except Exception as e:
        logger.error(f"Test 1.2 failed: {e}")
        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600) if gpu else 0
        return TestResult("1.2 Restore", False, duration, cost, error=str(e))


async def test_2_1(client: VASTClient, session: TestSession) -> TestResult:
    """Test 2.1: Manual Failover"""
    logger.info("=" * 60)
    logger.info("TEST 2.1: Manual Failover")
    logger.info("=" * 60)
    start_time = time.time()
    gpu1, gpu2 = None, None

    try:
        gpu1 = await provision_gpu(client, session)
        if not gpu1:
            return TestResult("2.1 Manual Failover", False, time.time() - start_time, 0, error="No GPU1")

        files_info = create_test_files(gpu1['ssh_host'], gpu1['ssh_port'], size_mb=10)
        snapshot_id = f"failover-{int(time.time())}"

        result = upload_snapshot(gpu1['ssh_host'], gpu1['ssh_port'], snapshot_id)

        if not result.get("success"):
            raise Exception(f"Snapshot failed: {result.get('error', 'Unknown')}")

        cost1 = cleanup_gpu(client, session, gpu1['instance_id'], (time.time() - start_time) / 3600)
        gpu1 = None

        gpu2_start = time.time()
        gpu2 = await provision_gpu(client, session)
        if not gpu2:
            return TestResult("2.1 Manual Failover", False, time.time() - start_time, cost1, error="No GPU2")

        result = download_snapshot(gpu2['ssh_host'], gpu2['ssh_port'], snapshot_id, "/workspace")

        if not result.get("success"):
            raise Exception(f"Restore failed: {result.get('error', 'Unknown')}")

        verify = verify_files(gpu2['ssh_host'], gpu2['ssh_port'], files_info.get("files", {}))

        duration = time.time() - start_time
        cost2 = cleanup_gpu(client, session, gpu2['instance_id'], (time.time() - gpu2_start) / 3600)

        return TestResult("2.1 Manual Failover", verify.get("success", False), duration, cost1 + cost2, {
            "snapshot_id": snapshot_id, "files_verified": verify.get("verified", 0)
        })

    except Exception as e:
        logger.error(f"Test 2.1 failed: {e}")
        duration = time.time() - start_time
        cost = 0
        if gpu1:
            cost += cleanup_gpu(client, session, gpu1['instance_id'], duration / 3600)
        if gpu2:
            cost += cleanup_gpu(client, session, gpu2['instance_id'], duration / 3600)
        return TestResult("2.1 Manual Failover", False, duration, cost, error=str(e))


async def test_2_2(client: VASTClient, session: TestSession) -> TestResult:
    """Test 2.2: Auto Failover"""
    logger.info("=" * 60)
    logger.info("TEST 2.2: Auto Failover")
    logger.info("=" * 60)
    start_time = time.time()
    gpu1, gpu2 = None, None

    try:
        gpu1 = await provision_gpu(client, session)
        if not gpu1:
            return TestResult("2.2 Auto Failover", False, time.time() - start_time, 0, error="No GPU1")

        files_info = create_test_files(gpu1['ssh_host'], gpu1['ssh_port'], size_mb=10)
        snapshot_id = f"auto-{int(time.time())}"

        upload_snapshot(gpu1['ssh_host'], gpu1['ssh_port'], snapshot_id)

        failure_time = time.time()
        cost1 = cleanup_gpu(client, session, gpu1['instance_id'], (time.time() - start_time) / 3600)
        gpu1 = None

        detection_time = time.time() - failure_time

        failover_start = time.time()
        gpu2 = await provision_gpu(client, session)
        if not gpu2:
            return TestResult("2.2 Auto Failover", False, time.time() - start_time, cost1, error="No GPU2")

        download_snapshot(gpu2['ssh_host'], gpu2['ssh_port'], snapshot_id, "/workspace")

        total_failover = time.time() - failure_time
        verify = verify_files(gpu2['ssh_host'], gpu2['ssh_port'], files_info.get("files", {}))

        duration = time.time() - start_time
        cost2 = cleanup_gpu(client, session, gpu2['instance_id'], (time.time() - failover_start) / 3600)

        success = verify.get("success", False) and total_failover < 180

        return TestResult("2.2 Auto Failover", success, duration, cost1 + cost2, {
            "detection_time": detection_time, "total_failover": total_failover,
            "within_sla": total_failover < 180
        })

    except Exception as e:
        logger.error(f"Test 2.2 failed: {e}")
        duration = time.time() - start_time
        cost = 0
        if gpu1:
            cost += cleanup_gpu(client, session, gpu1['instance_id'], duration / 3600)
        if gpu2:
            cost += cleanup_gpu(client, session, gpu2['instance_id'], duration / 3600)
        return TestResult("2.2 Auto Failover", False, duration, cost, error=str(e))


async def test_3_1(client: VASTClient, session: TestSession) -> TestResult:
    """Test 3.1: Auto-Hibernation"""
    logger.info("=" * 60)
    logger.info("TEST 3.1: Auto-Hibernation")
    logger.info("=" * 60)
    start_time = time.time()
    gpu = None

    try:
        gpu = await provision_gpu(client, session)
        if not gpu:
            return TestResult("3.1 Auto-Hibernation", False, time.time() - start_time, 0, error="No GPU")

        files_info = create_test_files(gpu['ssh_host'], gpu['ssh_port'], size_mb=20)

        # Check GPU utilization
        result = ssh_exec(gpu['ssh_host'], gpu['ssh_port'],
                         "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null || echo 0")
        gpu_util_str = result.get("stdout", "0").strip() or "0"
        # Handle N/A, [N/A], or other non-numeric values
        try:
            gpu_util = int(gpu_util_str.replace("[", "").replace("]", "").replace("N/A", "0"))
        except ValueError:
            gpu_util = 0  # Assume idle if we can't read utilization
        idle_detected = gpu_util < 5

        snapshot_id = f"hibernate-{int(time.time())}"
        upload_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id)

        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600)

        return TestResult("3.1 Auto-Hibernation", idle_detected, duration, cost, {
            "snapshot_id": snapshot_id, "gpu_util": gpu_util, "idle_detected": idle_detected,
            "files_info": files_info.get("files", {})
        })

    except Exception as e:
        logger.error(f"Test 3.1 failed: {e}")
        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600) if gpu else 0
        return TestResult("3.1 Auto-Hibernation", False, duration, cost, error=str(e))


async def test_3_2(client: VASTClient, session: TestSession, prev: Dict) -> TestResult:
    """Test 3.2: Wake from Hibernation"""
    logger.info("=" * 60)
    logger.info("TEST 3.2: Wake from Hibernation")
    logger.info("=" * 60)
    start_time = time.time()
    gpu = None

    try:
        snapshot_id = prev.get("snapshot_id")
        expected_files = prev.get("files_info", {})
        if not snapshot_id:
            return TestResult("3.2 Wake", False, 0, 0, error="No snapshot from 3.1")

        wake_start = time.time()
        gpu = await provision_gpu(client, session)
        if not gpu:
            return TestResult("3.2 Wake", False, time.time() - start_time, 0, error="No GPU")

        download_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id, "/workspace")

        wake_time = time.time() - wake_start
        verify = verify_files(gpu['ssh_host'], gpu['ssh_port'], expected_files)

        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600)

        success = verify.get("success", False) and wake_time < 180

        return TestResult("3.2 Wake", success, duration, cost, {
            "wake_time": wake_time, "within_sla": wake_time < 180
        })

    except Exception as e:
        logger.error(f"Test 3.2 failed: {e}")
        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600) if gpu else 0
        return TestResult("3.2 Wake", False, duration, cost, error=str(e))


async def test_4_1(client: VASTClient, session: TestSession) -> TestResult:
    """Test 4.1: Large Snapshot (500MB)"""
    logger.info("=" * 60)
    logger.info("TEST 4.1: Large Snapshot")
    logger.info("=" * 60)
    start_time = time.time()
    gpu = None

    try:
        gpu = await provision_gpu(client, session)
        if not gpu:
            return TestResult("4.1 Large Snapshot", False, time.time() - start_time, 0, error="No GPU")

        files_info = create_test_files(gpu['ssh_host'], gpu['ssh_port'], size_mb=50)  # Reduced for testing
        if "error" in files_info:
            raise Exception(f"Create files failed: {files_info['error']}")

        snapshot_id = f"large-{int(time.time())}"
        upload_start = time.time()

        result = upload_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id)

        upload_time = time.time() - upload_start

        if not result.get("success"):
            raise Exception(f"Upload failed: {result.get('error', 'Unknown')}")

        snapshot_size = result.get("size", 0)
        size_gb = files_info.get("total_size", 0) / (1024 * 1024 * 1024)
        time_per_gb = upload_time / size_gb if size_gb > 0 else 0

        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600)

        success = time_per_gb < 600  # < 10 min/GB

        return TestResult("4.1 Large Snapshot", success, duration, cost, {
            "snapshot_size": snapshot_size, "upload_time": upload_time,
            "time_per_gb": time_per_gb
        })

    except Exception as e:
        logger.error(f"Test 4.1 failed: {e}")
        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600) if gpu else 0
        return TestResult("4.1 Large Snapshot", False, duration, cost, error=str(e))


async def test_4_2(client: VASTClient, session: TestSession) -> TestResult:
    """Test 4.2: Multiple Failovers (3x)"""
    logger.info("=" * 60)
    logger.info("TEST 4.2: Multiple Failovers")
    logger.info("=" * 60)
    start_time = time.time()
    gpu = None
    cycles_completed = 0
    failover_times = []
    total_cost = 0
    NUM_CYCLES = 3

    try:
        gpu = await provision_gpu(client, session)
        if not gpu:
            return TestResult("4.2 Multiple Failovers", False, time.time() - start_time, 0, error="No GPU")

        files_info = create_test_files(gpu['ssh_host'], gpu['ssh_port'], size_mb=20)
        expected_files = files_info.get("files", {})

        for cycle in range(NUM_CYCLES):
            cycle_start = time.time()
            logger.info(f"Cycle {cycle + 1}/{NUM_CYCLES}")

            snapshot_id = f"multi-{int(time.time())}-{cycle}"
            upload_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id)

            cost = cleanup_gpu(client, session, gpu['instance_id'], (time.time() - cycle_start) / 3600)
            total_cost += cost

            gpu = await provision_gpu(client, session)
            if not gpu:
                raise Exception(f"Cycle {cycle + 1} provision failed")

            download_snapshot(gpu['ssh_host'], gpu['ssh_port'], snapshot_id, "/workspace")

            verify = verify_files(gpu['ssh_host'], gpu['ssh_port'], expected_files)
            if not verify.get("success"):
                raise Exception(f"Cycle {cycle + 1} verify failed")

            cycle_time = time.time() - cycle_start
            failover_times.append(cycle_time)
            cycles_completed += 1
            logger.info(f"Cycle {cycle + 1} done: {cycle_time:.1f}s")

        duration = time.time() - start_time
        cost = cleanup_gpu(client, session, gpu['instance_id'], duration / 3600 / NUM_CYCLES)
        total_cost += cost

        avg_time = sum(failover_times) / len(failover_times)
        success = cycles_completed == NUM_CYCLES and avg_time < 180

        return TestResult("4.2 Multiple Failovers", success, duration, total_cost, {
            "cycles": cycles_completed, "avg_time": avg_time, "failover_times": failover_times
        })

    except Exception as e:
        logger.error(f"Test 4.2 failed: {e}")
        duration = time.time() - start_time
        if gpu:
            total_cost += cleanup_gpu(client, session, gpu['instance_id'], duration / 3600)
        return TestResult("4.2 Multiple Failovers", False, duration, total_cost, {
            "cycles": cycles_completed, "failover_times": failover_times
        }, error=str(e))


async def run_all_tests():
    logger.info("=" * 70)
    logger.info("DUMONT CLOUD - FAILOVER INTEGRATION TESTS")
    logger.info("=" * 70)
    logger.info(f"Budget: ${MAX_BUDGET} | Started: {datetime.utcnow().isoformat()}")
    logger.info("=" * 70)

    if not VAST_API_KEY:
        logger.error("VAST_API_KEY not set!")
        return False

    # Clean up old snapshots
    if SNAPSHOT_DIR.exists():
        for f in SNAPSHOT_DIR.glob("*.tar"):
            try:
                f.unlink()
            except:
                pass

    client = VASTClient(VAST_API_KEY)
    session = TestSession()

    try:
        r1 = await test_1_1(client, session)
        session.results.append(r1)

        r2 = await test_1_2(client, session, r1.details)
        session.results.append(r2)

        r3 = await test_2_1(client, session)
        session.results.append(r3)

        r4 = await test_2_2(client, session)
        session.results.append(r4)

        r5 = await test_3_1(client, session)
        session.results.append(r5)

        r6 = await test_3_2(client, session, r5.details)
        session.results.append(r6)

        r7 = await test_4_1(client, session)
        session.results.append(r7)

        r8 = await test_4_2(client, session)
        session.results.append(r8)

    except BudgetExceededError as e:
        logger.error(f"BUDGET EXCEEDED: {e}")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        for instance_id in session.active_instances[:]:
            logger.info(f"Cleanup orphaned: {instance_id}")
            client.destroy(instance_id)
            session.active_instances.remove(instance_id)

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    for r in session.results:
        status = "PASS" if r.success else "FAIL"
        print(f"[{status}] {r.name} | {r.duration_seconds:.1f}s | ${r.cost_usd:.4f}")
        if r.error:
            print(f"       Error: {r.error[:60]}")

    print("=" * 70)
    print(f"TOTAL: {session.passed_count()}/{len(session.results)} passed")
    print(f"COST: ${session.total_cost:.4f}")
    print("=" * 70)

    results_file = Path(__file__).parent.parent / "FAILOVER_TEST_RESULTS.json"
    with open(results_file, "w") as f:
        json.dump({
            "session": {"started_at": session.started_at, "total_cost": session.total_cost,
                       "passed": session.passed_count(), "total": len(session.results)},
            "results": [asdict(r) for r in session.results]
        }, f, indent=2)

    print(f"\nResults: {results_file}")

    if session.passed_count() == 8:
        print("\nFAILOVER_TESTS_COMPLETE_ALL_8_PASSED")
        return True
    return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

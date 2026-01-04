"""
GPU Provisioner Service - Fast GPU provisioning with race strategy

Strategy:
- Provision N GPUs in parallel
- Check SSH connectivity every 2s on all GPUs
- First one to CONNECT wins
- Delete the losers
- If none connects in timeout, delete all and try next round
- Up to max_rounds attempts
"""

import asyncio
import subprocess
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests

from .vast import get_host_blacklist, blacklist_host, is_host_blacklisted
from ...core.resilience import get_prometheus_metrics

logger = logging.getLogger(__name__)


@dataclass
class GPUCandidate:
    """A GPU candidate in the race"""
    instance_id: int
    offer_id: int
    gpu_name: str
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    status: str = "provisioning"  # provisioning, waiting_ssh, ready, failed
    connected: bool = False
    provision_start_time: float = 0.0  # Time when provisioning started
    ssh_ready_time: Optional[float] = None  # Time when SSH became ready


@dataclass
class ProvisionResult:
    """Result of GPU provisioning"""
    success: bool
    instance_id: Optional[int] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    gpu_name: Optional[str] = None
    rounds_attempted: int = 0
    total_time_ms: int = 0
    gpus_tried: int = 0
    ssh_ready_time_seconds: Optional[float] = None  # Time from provision to SSH ready
    error: Optional[str] = None


class GPUProvisioner:
    """
    Fast GPU provisioner using race strategy.

    Usage:
        provisioner = GPUProvisioner(vast_api_key="...")
        result = await provisioner.provision_fast(
            min_gpu_ram=10000,
            max_price=0.50,
            image="nvidia/cuda:12.1.0-runtime-ubuntu22.04"
        )
        if result.success:
            print(f"GPU ready: {result.ssh_host}:{result.ssh_port}")
    """

    def __init__(self, vast_api_key: str):
        self.api_key = vast_api_key
        self.headers = {"Authorization": f"Bearer {vast_api_key}"}
        self.base_url = "https://cloud.vast.ai/api/v0"

    # Default Docker image - Vast.ai's own image (pre-cached, boots in ~20s)
    DEFAULT_IMAGE = "vastai/pytorch"

    # Robust onstart with retries for reliability
    DEFAULT_ONSTART = """#!/bin/bash
set -e

# Install Python dependencies with retry
for i in 1 2 3; do
    pip install b2sdk lz4 --quiet 2>/dev/null && break
    echo "[onstart] pip install attempt $i failed, retrying..."
    sleep 2
done

# Install Ollama with retry (3 attempts)
OLLAMA_INSTALLED=false
for i in 1 2 3; do
    if curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null; then
        OLLAMA_INSTALLED=true
        echo "[onstart] Ollama installed successfully on attempt $i"
        break
    fi
    echo "[onstart] Ollama install attempt $i failed, retrying in 5s..."
    sleep 5
done

if [ "$OLLAMA_INSTALLED" = false ]; then
    echo "[onstart] WARNING: Ollama installation failed after 3 attempts"
fi

# Start Ollama server with proper environment
export OLLAMA_HOST=0.0.0.0
nohup ollama serve > /var/log/ollama.log 2>&1 &

# Wait for Ollama to start (max 30s)
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[onstart] Ollama server ready after ${i}s"
        break
    fi
    sleep 1
done

echo "[onstart] GPU initialization complete"
"""

    async def provision_fast(
        self,
        min_gpu_ram: int = 10000,
        max_price: float = 1.0,
        image: str = None,  # Uses DEFAULT_IMAGE if not specified
        onstart: str = None,  # Uses DEFAULT_ONSTART if not specified
        disk: int = 50,
        gpus_per_round: int = 5,
        timeout_per_round: int = 15,  # 15s timeout por round (passa rapido pro proximo)
        max_rounds: int = 4,
        check_interval: float = 2.0,
    ) -> ProvisionResult:
        """
        Provision a GPU using race strategy.

        Args:
            min_gpu_ram: Minimum GPU RAM in MB
            max_price: Maximum price per hour
            image: Docker image to use
            onstart: Command to run on start
            disk: Disk space in GB
            gpus_per_round: Number of GPUs to provision per round
            timeout_per_round: Seconds to wait per round
            max_rounds: Maximum number of rounds
            check_interval: Seconds between SSH checks

        Returns:
            ProvisionResult with the winning GPU or error
        """
        # Use defaults if not specified
        if image is None:
            image = self.DEFAULT_IMAGE
        if onstart is None:
            onstart = self.DEFAULT_ONSTART

        start_time = time.time()
        total_gpus_tried = 0

        for round_num in range(1, max_rounds + 1):
            logger.info(f"[GPUProvisioner] Round {round_num}/{max_rounds}")

            # Get available offers - fetch many since most will be stale
            offers = self._search_gpus(min_gpu_ram, max_price, gpus_per_round * 4)

            logger.info(f"[GPUProvisioner] Found {len(offers)} offers in round {round_num}")

            if not offers:
                logger.warning(f"[GPUProvisioner] No offers found in round {round_num}")
                continue

            # Try more offers since many will fail (already rented by others)
            # Try 3x the target to compensate for ~60-70% failure rate
            candidates = await self._provision_batch(
                offers[:gpus_per_round * 3],
                image,
                onstart,
                disk
            )

            if not candidates:
                logger.warning(f"[GPUProvisioner] No GPUs provisioned in round {round_num}")
                continue

            total_gpus_tried += len(candidates)

            # Race! Wait for first to connect
            winner = await self._race_for_connection(
                candidates,
                timeout_per_round,
                check_interval
            )

            if winner:
                # Delete losers
                losers = [c for c in candidates if c.instance_id != winner.instance_id]
                await self._delete_batch(losers)

                total_time = int((time.time() - start_time) * 1000)
                logger.info(
                    f"[GPUProvisioner] Winner: {winner.gpu_name} "
                    f"({winner.ssh_host}:{winner.ssh_port}) in {total_time}ms"
                )

                return ProvisionResult(
                    success=True,
                    instance_id=winner.instance_id,
                    ssh_host=winner.ssh_host,
                    ssh_port=winner.ssh_port,
                    gpu_name=winner.gpu_name,
                    rounds_attempted=round_num,
                    total_time_ms=total_time,
                    gpus_tried=total_gpus_tried,
                    ssh_ready_time_seconds=winner.ssh_ready_time,
                )

            # No winner - delete all and try next round
            logger.info(f"[GPUProvisioner] No winner in round {round_num}, cleaning up")
            await self._delete_batch(candidates)

        # All rounds failed
        total_time = int((time.time() - start_time) * 1000)
        return ProvisionResult(
            success=False,
            rounds_attempted=max_rounds,
            total_time_ms=total_time,
            gpus_tried=total_gpus_tried,
            error=f"No GPU connected after {max_rounds} rounds ({total_gpus_tried} GPUs tried)",
        )

    def _search_gpus(
        self,
        min_gpu_ram: int,
        max_price: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search for available GPUs, excluding blacklisted hosts."""
        try:
            params = {
                "verified": "true",
                "external": "false",
                "rentable": "true",
                "gpu_ram": str(min_gpu_ram),
                "num_gpus": "1",
                "order": "dph_total",
                "type": "on-demand",
            }

            response = requests.get(
                f"{self.base_url}/bundles",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            offers = response.json().get("offers", [])

            # Filter by price
            filtered = [o for o in offers if o.get("dph_total", 999) <= max_price]

            # Filter out blacklisted hosts
            blacklist = get_host_blacklist()
            non_blacklisted = []
            blacklisted_count = 0

            for offer in filtered:
                machine_id = offer.get("machine_id") or offer.get("id")
                if machine_id and is_host_blacklisted(machine_id):
                    blacklisted_count += 1
                    continue
                non_blacklisted.append(offer)

            if blacklisted_count > 0:
                logger.info(
                    f"[GPUProvisioner] Filtered out {blacklisted_count} blacklisted hosts"
                )

            return non_blacklisted[:limit]

        except Exception as e:
            logger.error(f"[GPUProvisioner] Search failed: {e}")
            return []

    async def _provision_batch(
        self,
        offers: List[Dict[str, Any]],
        image: str,
        onstart: str,
        disk: int,
    ) -> List[GPUCandidate]:
        """Provision multiple GPUs in parallel with rate limiting"""
        candidates = []

        async def provision_one(offer: Dict[str, Any], delay: float = 0.0) -> Optional[GPUCandidate]:
            # Rate limiting: stagger requests
            if delay > 0:
                await asyncio.sleep(delay)

            # Retry logic for 429 errors
            for attempt in range(3):
                try:
                    response = requests.put(
                        f"{self.base_url}/asks/{offer['id']}/",
                        headers=self.headers,
                        json={
                            "client_id": "me",
                            "image": image,
                            "disk": disk,
                            "onstart": onstart,
                        },
                        timeout=30
                    )

                    if response.status_code in [200, 201]:
                        data = response.json()
                        instance_id = data.get("new_contract")
                        if instance_id:
                            logger.info(
                                f"[GPUProvisioner] Provisioned {offer.get('gpu_name')} "
                                f"(ID: {instance_id})"
                            )
                            return GPUCandidate(
                                instance_id=instance_id,
                                offer_id=offer["id"],
                                gpu_name=offer.get("gpu_name", "unknown"),
                                status="waiting_ssh",
                                provision_start_time=time.time()
                            )
                    elif response.status_code == 429:
                        # Rate limit hit - exponential backoff
                        wait_time = (2 ** attempt)  # 1s, 2s, 4s
                        logger.warning(
                            f"[GPUProvisioner] Rate limit hit for offer {offer['id']}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/3)"
                        )
                        if attempt < 2:  # Don't sleep on last attempt
                            await asyncio.sleep(wait_time)
                            continue
                    else:
                        # Other error (usually 400 = offer already taken)
                        error_msg = response.text[:200] if response.text else "No error message"
                        logger.warning(
                            f"[GPUProvisioner] Offer {offer['id']} failed "
                            f"({response.status_code}): {error_msg}"
                        )
                        break  # Don't retry non-429 errors

                except Exception as e:
                    logger.warning(f"[GPUProvisioner] Failed to provision {offer['id']}: {e}")
                    break

            return None

        # Stagger requests: 200ms delay between each
        tasks = [provision_one(offer, idx * 0.2) for idx, offer in enumerate(offers)]
        results = await asyncio.gather(*tasks)

        return [c for c in results if c is not None]

    async def _race_for_connection(
        self,
        candidates: List[GPUCandidate],
        timeout: int,
        check_interval: float,
    ) -> Optional[GPUCandidate]:
        """
        Race all candidates - first to have SSH ready wins.
        Blacklists hosts that fail SSH connectivity.
        """
        start_time = time.time()
        ssh_attempts: Dict[int, int] = {}  # instance_id -> attempt count

        while time.time() - start_time < timeout:
            self._update_ssh_info(candidates)

            for candidate in candidates:
                if candidate.ssh_host and candidate.ssh_port and not candidate.connected:
                    # Track SSH attempts per candidate
                    ssh_attempts[candidate.instance_id] = ssh_attempts.get(candidate.instance_id, 0) + 1

                    if self._test_ssh(candidate.ssh_host, candidate.ssh_port):
                        candidate.connected = True
                        candidate.status = "ready"
                        candidate.ssh_ready_time = time.time() - candidate.provision_start_time
                        logger.info(
                            f"[GPUProvisioner] {candidate.gpu_name} SSH ready in "
                            f"{candidate.ssh_ready_time:.1f}s!"
                        )
                        return candidate
                    else:
                        # Mark as failed if too many attempts
                        if ssh_attempts[candidate.instance_id] >= 5:
                            candidate.status = "failed"
                            logger.warning(
                                f"[GPUProvisioner] {candidate.gpu_name} failed SSH after "
                                f"{ssh_attempts[candidate.instance_id]} attempts"
                            )

            await asyncio.sleep(check_interval)

        # Blacklist all candidates that failed SSH
        for candidate in candidates:
            if not candidate.connected and candidate.ssh_host:
                machine_id = candidate.offer_id  # Use offer_id as machine identifier
                blacklist_host(machine_id, f"SSH failed after {timeout}s timeout")
                logger.warning(
                    f"[GPUProvisioner] Blacklisted machine {machine_id} "
                    f"({candidate.gpu_name}) due to SSH failure"
                )

        return None

    def _update_ssh_info(self, candidates: List[GPUCandidate]) -> None:
        """Update SSH host/port info from Vast.ai API"""
        try:
            response = requests.get(
                f"{self.base_url}/instances/",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            instances = {i["id"]: i for i in response.json().get("instances", [])}

            for candidate in candidates:
                if candidate.instance_id in instances:
                    info = instances[candidate.instance_id]
                    candidate.ssh_host = info.get("ssh_host")
                    candidate.ssh_port = info.get("ssh_port")

        except Exception as e:
            logger.warning(f"[GPUProvisioner] Failed to update SSH info: {e}")

    def _test_ssh(self, host: str, port: int, retries: int = 3) -> bool:
        """
        Test if SSH connection works with health check.

        Does multiple checks:
        1. Basic SSH connectivity
        2. Verify host is responsive (uptime check)
        3. Retry with backoff on failure
        4. Records latency metrics for Prometheus
        """
        prom_metrics = get_prometheus_metrics()

        for attempt in range(retries):
            start_time = time.time()
            success = False

            try:
                # First: Basic SSH connectivity with echo
                result = subprocess.run(
                    [
                        "ssh",
                        "-p", str(port),
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        "-o", "ConnectTimeout=5",
                        "-o", "BatchMode=yes",
                        "-o", "ServerAliveInterval=5",
                        "-o", "ServerAliveCountMax=2",
                        f"root@{host}",
                        "echo ok && uptime"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                latency_ms = int((time.time() - start_time) * 1000)

                if result.returncode == 0 and "ok" in result.stdout:
                    logger.debug(f"[GPUProvisioner] SSH health check passed for {host}:{port}")
                    # Record successful SSH latency
                    prom_metrics.record_ssh_latency(host, port, latency_ms, success=True)
                    return True

                # Log failure details for debugging
                logger.warning(
                    f"[GPUProvisioner] SSH health check failed for {host}:{port} "
                    f"(attempt {attempt + 1}/{retries}): "
                    f"rc={result.returncode}, stdout={result.stdout[:100]}, stderr={result.stderr[:100]}"
                )
                # Record failed SSH attempt
                prom_metrics.record_ssh_latency(host, port, latency_ms, success=False)

            except subprocess.TimeoutExpired:
                latency_ms = int((time.time() - start_time) * 1000)
                prom_metrics.record_ssh_latency(host, port, latency_ms, success=False)
                logger.warning(
                    f"[GPUProvisioner] SSH timeout for {host}:{port} "
                    f"(attempt {attempt + 1}/{retries})"
                )
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                prom_metrics.record_ssh_latency(host, port, latency_ms, success=False)
                logger.warning(
                    f"[GPUProvisioner] SSH error for {host}:{port}: {e} "
                    f"(attempt {attempt + 1}/{retries})"
                )

            # Backoff before retry
            if attempt < retries - 1:
                import asyncio
                try:
                    asyncio.get_event_loop().run_until_complete(
                        asyncio.sleep(1 * (attempt + 1))
                    )
                except:
                    time.sleep(1 * (attempt + 1))

        return False

    def _test_deps_ready(self, host: str, port: int) -> bool:
        """Test if dependencies (b2sdk, lz4) are installed"""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-p", str(port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=5",
                    "-o", "BatchMode=yes",
                    f"root@{host}",
                    "python3 -c 'import b2sdk; import lz4' && which lz4 && echo DEPS_OK"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            return "DEPS_OK" in result.stdout
        except:
            return False

    async def _delete_batch(self, candidates: List[GPUCandidate]) -> None:
        """Delete multiple GPUs"""
        for candidate in candidates:
            try:
                response = requests.delete(
                    f"{self.base_url}/instances/{candidate.instance_id}/",
                    headers=self.headers,
                    timeout=10
                )
                if response.status_code in [200, 204]:
                    logger.info(f"[GPUProvisioner] Deleted {candidate.instance_id}")
            except Exception as e:
                logger.warning(f"[GPUProvisioner] Failed to delete {candidate.instance_id}: {e}")


# Convenience function for simple usage
async def provision_gpu_fast(
    vast_api_key: str,
    min_gpu_ram: int = 10000,
    max_price: float = 1.0,
    **kwargs
) -> ProvisionResult:
    """
    Quick function to provision a GPU.

    Example:
        result = await provision_gpu_fast("your-api-key", min_gpu_ram=16000)
        if result.success:
            print(f"SSH: {result.ssh_host}:{result.ssh_port}")
    """
    provisioner = GPUProvisioner(vast_api_key)
    return await provisioner.provision_fast(min_gpu_ram, max_price, **kwargs)

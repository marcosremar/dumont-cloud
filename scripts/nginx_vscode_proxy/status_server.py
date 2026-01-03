#!/usr/bin/env python3
"""
Dumont Cloud - Failover Status Server

Servidor local que monitora o estado GPU/CPU e serve a API de status
para o widget injetado no VS Code.

Uso:
    python3 status_server.py --gpu-host GPU_IP --gpu-port GPU_SSH_PORT \
                             --cpu-host CPU_IP --cpu-port CPU_SSH_PORT

O widget no VS Code consulta /status a cada 2 segundos.
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# State file location
STATE_DIR = Path.home() / ".dumont"
STATE_FILE = STATE_DIR / "failover_state.json"


class FailoverState:
    """Manages failover state"""

    def __init__(self):
        self.mode = "gpu"  # 'gpu', 'cpu', 'failover'
        self.gpu_name = "GPU"
        self.cpu_name = "CPU Standby"
        self.gpu_host = None
        self.gpu_port = 22
        self.cpu_host = None
        self.cpu_port = 22
        self.last_sync = None
        self.sync_count = 0
        self.healthy = True
        self.gpu_health_failures = 0
        self.last_check = None

        # Ensure state directory exists
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing state
        self.load()

    def load(self):
        """Load state from file"""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.mode = data.get("mode", "gpu")
                    self.gpu_name = data.get("gpu_name", "GPU")
                    self.cpu_name = data.get("cpu_name", "CPU Standby")
                    self.last_sync = data.get("last_sync")
                    self.sync_count = data.get("sync_count", 0)
                    self.healthy = data.get("healthy", True)
        except Exception as e:
            print(f"Warning: Could not load state: {e}")

    def save(self):
        """Save state to file"""
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({
                    "mode": self.mode,
                    "gpu_name": self.gpu_name,
                    "cpu_name": self.cpu_name,
                    "last_sync": self.last_sync,
                    "sync_count": self.sync_count,
                    "healthy": self.healthy,
                    "last_check": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")

    def to_dict(self):
        """Return state as dictionary"""
        return {
            "mode": self.mode,
            "gpu_name": self.gpu_name,
            "cpu_name": self.cpu_name,
            "gpu_host": self.gpu_host,
            "gpu_port": self.gpu_port,
            "cpu_host": self.cpu_host,
            "cpu_port": self.cpu_port,
            "last_sync": self.last_sync,
            "sync_count": self.sync_count,
            "healthy": self.healthy,
            "last_check": self.last_check,
        }


# Global state
state = FailoverState()


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP handler for status API"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def _send_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/status" or self.path == "/api/failover/status":
            self._send_response(200, state.to_dict())

        elif self.path == "/health":
            self._send_response(200, {"status": "healthy"})

        elif self.path == "/trigger-failover":
            # Manual failover trigger (for testing)
            if state.mode == "gpu":
                state.mode = "failover"
                state.save()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Manual failover triggered!")

                # Simulate failover process
                def complete_failover():
                    time.sleep(2)
                    state.mode = "cpu"
                    state.save()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Failover complete: now on CPU")

                threading.Thread(target=complete_failover, daemon=True).start()
                self._send_response(200, {"success": True, "message": "Failover initiated"})
            else:
                self._send_response(400, {"success": False, "message": "Already on CPU"})

        elif self.path == "/restore-gpu":
            # Restore to GPU (for testing)
            state.mode = "gpu"
            state.healthy = True
            state.gpu_health_failures = 0
            state.save()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Restored to GPU mode")
            self._send_response(200, {"success": True, "message": "Restored to GPU"})

        else:
            self._send_response(404, {"error": "Not found"})


def check_host_health(host, port, timeout=5):
    """Check if host is reachable via SSH"""
    if not host:
        return False

    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
             "-o", "BatchMode=yes", "-p", str(port), f"root@{host}", "echo ok"],
            capture_output=True,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception:
        return False


def health_monitor_loop():
    """Background thread that monitors GPU health"""
    global state

    check_interval = 5  # seconds
    failure_threshold = 3

    print(f"[Health Monitor] Starting (checking every {check_interval}s)")
    print(f"[Health Monitor] GPU: {state.gpu_host}:{state.gpu_port}")
    print(f"[Health Monitor] CPU: {state.cpu_host}:{state.cpu_port}")

    while True:
        try:
            state.last_check = datetime.now().isoformat()

            if state.mode == "gpu":
                # Check GPU health
                if state.gpu_host:
                    is_healthy = check_host_health(state.gpu_host, state.gpu_port)

                    if is_healthy:
                        state.gpu_health_failures = 0
                        state.healthy = True
                    else:
                        state.gpu_health_failures += 1
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                              f"GPU health check failed ({state.gpu_health_failures}/{failure_threshold})")

                        if state.gpu_health_failures >= failure_threshold:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                  f"GPU FAILURE DETECTED! Initiating failover...")
                            state.mode = "failover"
                            state.healthy = False
                            state.save()

                            # Complete failover after brief delay
                            time.sleep(1)
                            state.mode = "cpu"
                            state.save()
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                  f"Failover complete: now on CPU Standby")

            elif state.mode == "cpu":
                # Check CPU health
                if state.cpu_host:
                    is_healthy = check_host_health(state.cpu_host, state.cpu_port)
                    state.healthy = is_healthy
                    if not is_healthy:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                              f"WARNING: CPU Standby health check failed!")

            state.save()

        except Exception as e:
            print(f"[Health Monitor] Error: {e}")

        time.sleep(check_interval)


def main():
    global state

    parser = argparse.ArgumentParser(description="Dumont Failover Status Server")
    parser.add_argument("--port", type=int, default=8080, help="Status API port")
    parser.add_argument("--gpu-host", help="GPU host IP")
    parser.add_argument("--gpu-port", type=int, default=22, help="GPU SSH port")
    parser.add_argument("--cpu-host", help="CPU Standby host IP")
    parser.add_argument("--cpu-port", type=int, default=22, help="CPU SSH port")
    parser.add_argument("--gpu-name", default="GPU", help="GPU display name")
    parser.add_argument("--cpu-name", default="CPU Standby", help="CPU display name")
    parser.add_argument("--no-monitor", action="store_true", help="Disable health monitoring")

    args = parser.parse_args()

    # Configure state
    state.gpu_host = args.gpu_host
    state.gpu_port = args.gpu_port
    state.cpu_host = args.cpu_host
    state.cpu_port = args.cpu_port
    state.gpu_name = args.gpu_name
    state.cpu_name = args.cpu_name

    print("=" * 60)
    print("  Dumont Cloud - Failover Status Server")
    print("=" * 60)
    print(f"  Status API: http://localhost:{args.port}/status")
    print(f"  GPU: {args.gpu_host}:{args.gpu_port} ({args.gpu_name})")
    print(f"  CPU: {args.cpu_host}:{args.cpu_port} ({args.cpu_name})")
    print("")
    print("  Test endpoints:")
    print(f"    curl http://localhost:{args.port}/status")
    print(f"    curl http://localhost:{args.port}/trigger-failover")
    print(f"    curl http://localhost:{args.port}/restore-gpu")
    print("=" * 60)

    # Start health monitor
    if not args.no_monitor and (args.gpu_host or args.cpu_host):
        monitor_thread = threading.Thread(target=health_monitor_loop, daemon=True)
        monitor_thread.start()
    else:
        print("[Health Monitor] Disabled (no hosts configured)")

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", args.port), StatusHandler)
    print(f"\n[Server] Listening on port {args.port}...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()

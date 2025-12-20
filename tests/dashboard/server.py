#!/usr/bin/env python3
"""
Dumont Cloud - Test Dashboard Server
=====================================
A self-hosted test runner and results visualization dashboard.

Features:
- Run pytest (backend) and Playwright (frontend) tests
- Real-time test output via WebSocket
- LIVE BROWSER STREAMING with screenshots at each step
- Test history and trends
- Allure report integration
- Start/Stop/Cancel test runs

Usage:
    python server.py
    # Open http://localhost:8082
"""

import os
import sys
import json
import asyncio
import subprocess
import base64
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# ============ Configuration ============
BASE_DIR = Path(__file__).parent.parent  # tests/
PROJECT_ROOT = BASE_DIR.parent  # project root
REPORTS_DIR = BASE_DIR / "dashboard" / "reports"
SCREENSHOTS_DIR = BASE_DIR / "dashboard" / "screenshots"
ALLURE_RESULTS = BASE_DIR / "allure-results"
ALLURE_REPORT = BASE_DIR / "allure-report"

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)

# ============ Models ============
class TestType(str, Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    FRONTEND_VISUAL = "frontend_visual"  # With live browser streaming
    ALL = "all"

class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"

class TestStep(BaseModel):
    """Represents a single step in a test"""
    id: int
    name: str
    status: StepStatus = StepStatus.PENDING
    screenshot: Optional[str] = None  # Base64 encoded screenshot
    duration: Optional[float] = None
    error: Optional[str] = None

class TestRun(BaseModel):
    id: str
    type: TestType
    status: TestStatus
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration: Optional[float] = None
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    output: str = ""
    error: Optional[str] = None
    command: Optional[str] = None
    steps: List[TestStep] = []  # For visual tests
    current_screenshot: Optional[str] = None  # Latest browser screenshot

class RunTestRequest(BaseModel):
    type: TestType = TestType.ALL
    filter: Optional[str] = None  # e.g., "test_login" or "auth/"
    headed: bool = False  # For Playwright
    workers: int = 1
    test_file: Optional[str] = None  # Specific test file for visual mode

# ============ State ============
test_runs: Dict[str, TestRun] = {}
active_processes: Dict[str, subprocess.Popen] = {}
connected_clients: List[WebSocket] = []

# ============ App ============
app = FastAPI(
    title="Dumont Cloud Test Dashboard",
    description="Test runner and results visualization",
    version="1.0.0"
)

# ============ WebSocket Manager ============
async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    for client in connected_clients[:]:
        try:
            await client.send_json(message)
        except:
            connected_clients.remove(client)

async def stream_output(run_id: str, process: subprocess.Popen):
    """Stream process output to WebSocket clients"""
    run = test_runs.get(run_id)
    if not run:
        return

    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                decoded = line.decode('utf-8', errors='replace')
                run.output += decoded
                await broadcast({
                    "type": "output",
                    "run_id": run_id,
                    "line": decoded
                })
                await asyncio.sleep(0.01)
    except Exception as e:
        run.error = str(e)

def parse_pytest_output(output: str) -> Dict[str, int]:
    """Parse pytest output to extract pass/fail counts"""
    result = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}

    # Look for summary line like "5 passed, 2 failed, 1 skipped"
    import re
    match = re.search(r'(\d+) passed', output)
    if match:
        result["passed"] = int(match.group(1))

    match = re.search(r'(\d+) failed', output)
    if match:
        result["failed"] = int(match.group(1))

    match = re.search(r'(\d+) skipped', output)
    if match:
        result["skipped"] = int(match.group(1))

    result["total"] = result["passed"] + result["failed"] + result["skipped"]
    return result

def parse_playwright_output(output: str) -> Dict[str, int]:
    """Parse Playwright output to extract pass/fail counts"""
    result = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}

    import re
    # Playwright format: "X passed" or "X failed"
    match = re.search(r'(\d+) passed', output)
    if match:
        result["passed"] = int(match.group(1))

    match = re.search(r'(\d+) failed', output)
    if match:
        result["failed"] = int(match.group(1))

    match = re.search(r'(\d+) skipped', output)
    if match:
        result["skipped"] = int(match.group(1))

    result["total"] = result["passed"] + result["failed"] + result["skipped"]
    return result

# ============ Test Runners ============
async def run_pytest(run_id: str, filter_path: Optional[str] = None):
    """Run pytest backend tests"""
    run = test_runs[run_id]
    run.status = TestStatus.RUNNING
    run.started_at = datetime.now().isoformat()

    await broadcast({"type": "status", "run_id": run_id, "status": "running"})

    # Build command
    backend_path = str(BASE_DIR / "backend")
    cmd = [
        sys.executable, "-m", "pytest",
        backend_path,
        "-v",
        "--tb=short",
        f"--alluredir={ALLURE_RESULTS}",
    ]

    if filter_path:
        cmd.extend(["-k", filter_path])

    run.command = " ".join(cmd)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT)
        )
        active_processes[run_id] = process

        await stream_output(run_id, process)

        return_code = process.wait()

        # Parse results
        results = parse_pytest_output(run.output)
        run.passed = results["passed"]
        run.failed = results["failed"]
        run.skipped = results["skipped"]
        run.total = results["total"]

        run.status = TestStatus.PASSED if return_code == 0 else TestStatus.FAILED

    except Exception as e:
        run.status = TestStatus.ERROR
        run.error = str(e)

    finally:
        run.finished_at = datetime.now().isoformat()
        if run.started_at:
            start = datetime.fromisoformat(run.started_at)
            end = datetime.fromisoformat(run.finished_at)
            run.duration = (end - start).total_seconds()

        active_processes.pop(run_id, None)
        await broadcast({
            "type": "finished",
            "run_id": run_id,
            "status": run.status,
            "results": {
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "total": run.total,
                "duration": run.duration
            }
        })

        # Save to history
        save_run_history(run)

async def run_playwright(run_id: str, filter_path: Optional[str] = None, headed: bool = False):
    """Run Playwright frontend tests"""
    run = test_runs[run_id]
    run.status = TestStatus.RUNNING
    run.started_at = datetime.now().isoformat()

    await broadcast({"type": "status", "run_id": run_id, "status": "running"})

    # Build command
    cmd = ["npx", "playwright", "test"]

    if headed:
        cmd.append("--headed")

    if filter_path:
        cmd.append(filter_path)

    run.command = " ".join(cmd)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR)
        )
        active_processes[run_id] = process

        await stream_output(run_id, process)

        return_code = process.wait()

        # Parse results
        results = parse_playwright_output(run.output)
        run.passed = results["passed"]
        run.failed = results["failed"]
        run.skipped = results["skipped"]
        run.total = results["total"]

        run.status = TestStatus.PASSED if return_code == 0 else TestStatus.FAILED

    except Exception as e:
        run.status = TestStatus.ERROR
        run.error = str(e)

    finally:
        run.finished_at = datetime.now().isoformat()
        if run.started_at:
            start = datetime.fromisoformat(run.started_at)
            end = datetime.fromisoformat(run.finished_at)
            run.duration = (end - start).total_seconds()

        active_processes.pop(run_id, None)
        await broadcast({
            "type": "finished",
            "run_id": run_id,
            "status": run.status,
            "results": {
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "total": run.total,
                "duration": run.duration
            }
        })

        save_run_history(run)


async def run_playwright_visual(run_id: str, test_file: Optional[str] = None):
    """
    Run Playwright tests with LIVE BROWSER STREAMING (VNC-like)

    Uses visual_runner.js for continuous screenshot capture at ~5 FPS,
    streaming to the dashboard via WebSocket for real-time viewing.
    """
    run = test_runs[run_id]
    run.status = TestStatus.RUNNING
    run.started_at = datetime.now().isoformat()

    await broadcast({
        "type": "visual_start",
        "run_id": run_id,
        "status": "running",
        "message": "Iniciando navegador com streaming..."
    })

    # Clean screenshots directory for this run
    run_screenshots_dir = SCREENSHOTS_DIR / run_id
    if run_screenshots_dir.exists():
        shutil.rmtree(run_screenshots_dir)
    run_screenshots_dir.mkdir(parents=True, exist_ok=True)

    # Use visual_runner.js for continuous streaming
    visual_runner_path = Path(__file__).parent / "visual_runner.js"

    # Build command - visual runner will use headless mode automatically
    cmd = ["node", str(visual_runner_path)]
    run.command = f"node visual_runner.js (RUN_ID={run_id})"

    try:
        # Run with environment variables
        env = os.environ.copy()
        env["RUN_ID"] = run_id
        env["TEST_FILE"] = test_file or ""
        env["BASE_URL"] = "http://localhost:5173"
        env["DASHBOARD_WS_URL"] = "ws://localhost:8082/ws/visual"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BASE_DIR),
            env=env
        )
        active_processes[run_id] = process

        step_count = 0

        # Stream output from visual runner
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                decoded = line.decode('utf-8', errors='replace')
                run.output += decoded

                # Parse step markers from visual runner output
                if "📍 Step:" in decoded:
                    step_count += 1
                    step_name = decoded.split("Step:")[1].split("[")[0].strip() if "Step:" in decoded else decoded
                    step_status = "passed" if "[passed]" in decoded else "running" if "[running]" in decoded else "failed"

                    step = TestStep(
                        id=step_count,
                        name=step_name[:100],
                        status=StepStatus(step_status)
                    )
                    run.steps.append(step)

                await broadcast({
                    "type": "output",
                    "run_id": run_id,
                    "line": decoded
                })

                await asyncio.sleep(0.01)

        return_code = process.wait()

        # Count results from steps
        run.passed = sum(1 for s in run.steps if s.status == StepStatus.PASSED)
        run.failed = sum(1 for s in run.steps if s.status == StepStatus.FAILED)
        run.total = len(run.steps)

        run.status = TestStatus.PASSED if return_code == 0 else TestStatus.FAILED

    except Exception as e:
        run.status = TestStatus.ERROR
        run.error = str(e)

    finally:
        run.finished_at = datetime.now().isoformat()
        if run.started_at:
            start = datetime.fromisoformat(run.started_at)
            end = datetime.fromisoformat(run.finished_at)
            run.duration = (end - start).total_seconds()

        active_processes.pop(run_id, None)

        await broadcast({
            "type": "visual_finished",
            "run_id": run_id,
            "status": run.status,
            "results": {
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "total": run.total,
                "duration": run.duration,
                "steps": [s.model_dump() for s in run.steps]
            }
        })

        save_run_history(run)


def parse_playwright_step(line: str) -> Optional[Dict[str, Any]]:
    """Parse a Playwright output line to extract step information"""
    # Match patterns like: "✓ Step description" or "› expect(locator).toBeVisible"
    patterns = [
        r'^\s*[✓✗›\-]\s+(.+)$',
        r'^\s+at.*page\.(goto|click|fill|type|waitFor|expect)\((.+)\)',
        r'^\s*(\d+)\)\s+(.+)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, line.strip())
        if match:
            name = match.group(1) if len(match.groups()) == 1 else match.group(2)
            return {"name": name[:100]}  # Truncate long names

    # Also match test names
    if ' › ' in line or line.strip().startswith('Running'):
        return {"name": line.strip()[:100]}

    return None


def create_visual_test_wrapper(run_id: str, test_file: Optional[str], screenshots_dir: Path) -> Path:
    """
    Create a wrapper that adds screenshot capture to existing tests
    """
    # For now, we'll use Playwright's built-in screenshot on each action
    # A more advanced solution would inject screenshot hooks
    wrapper_content = f'''
// Auto-generated wrapper for visual testing
// Run ID: {run_id}

const {{ test: base }} = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SCREENSHOTS_DIR = '{screenshots_dir}';
let screenshotCounter = 0;

// Export wrapped test
exports.test = base.extend({{
    page: async ({{ page }}, use) => {{
        // Wrap page actions to capture screenshots
        const originalGoto = page.goto.bind(page);
        page.goto = async (...args) => {{
            const result = await originalGoto(...args);
            await captureScreenshot(page, 'navigate');
            return result;
        }};

        const originalClick = page.click.bind(page);
        page.click = async (...args) => {{
            await captureScreenshot(page, 'before-click');
            const result = await originalClick(...args);
            await captureScreenshot(page, 'after-click');
            return result;
        }};

        await use(page);
    }}
}});

async function captureScreenshot(page, action) {{
    try {{
        screenshotCounter++;
        const filename = path.join(SCREENSHOTS_DIR, `step-${{String(screenshotCounter).padStart(4, '0')}}-${{action}}.png`);
        await page.screenshot({{ path: filename, fullPage: false }});
    }} catch (e) {{
        // Ignore screenshot errors
    }}
}}
'''

    wrapper_path = screenshots_dir / "visual_wrapper.js"
    wrapper_path.write_text(wrapper_content)
    return wrapper_path


def save_run_history(run: TestRun):
    """Save test run to history file"""
    history_file = REPORTS_DIR / "history.json"
    history = []

    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
        except:
            pass

    history.append(run.model_dump())

    # Keep last 100 runs
    history = history[-100:]

    history_file.write_text(json.dumps(history, indent=2))

def load_run_history() -> List[dict]:
    """Load test run history"""
    history_file = REPORTS_DIR / "history.json"
    if history_file.exists():
        try:
            return json.loads(history_file.read_text())
        except:
            pass
    return []

# ============ API Endpoints ============
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML"""
    return get_dashboard_html()

@app.post("/api/run")
async def start_test_run(request: RunTestRequest, background_tasks: BackgroundTasks):
    """Start a new test run"""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    run = TestRun(
        id=run_id,
        type=request.type,
        status=TestStatus.PENDING
    )
    test_runs[run_id] = run

    if request.type == TestType.BACKEND:
        background_tasks.add_task(run_pytest, run_id, request.filter)
    elif request.type == TestType.FRONTEND:
        background_tasks.add_task(run_playwright, run_id, request.filter, request.headed)
    elif request.type == TestType.FRONTEND_VISUAL:
        # Run with live browser streaming
        background_tasks.add_task(run_playwright_visual, run_id, request.test_file)
    else:
        # Run both
        background_tasks.add_task(run_pytest, run_id, request.filter)
        # TODO: Run frontend after backend

    return {"run_id": run_id, "status": "started"}

@app.post("/api/cancel/{run_id}")
async def cancel_test_run(run_id: str):
    """Cancel a running test"""
    process = active_processes.get(run_id)
    if process:
        process.terminate()
        process.wait(timeout=5)

        run = test_runs.get(run_id)
        if run:
            run.status = TestStatus.CANCELLED
            run.finished_at = datetime.now().isoformat()

        active_processes.pop(run_id, None)
        await broadcast({"type": "cancelled", "run_id": run_id})
        return {"status": "cancelled"}

    raise HTTPException(status_code=404, detail="Run not found or not running")

@app.get("/api/runs")
async def get_runs():
    """Get all test runs (current + history)"""
    current = [run.model_dump() for run in test_runs.values()]
    history = load_run_history()
    return {"current": current, "history": history[-20:]}

@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    """Get a specific test run"""
    run = test_runs.get(run_id)
    if run:
        return run.model_dump()

    # Check history
    for run_data in load_run_history():
        if run_data["id"] == run_id:
            return run_data

    raise HTTPException(status_code=404, detail="Run not found")

@app.get("/api/stats")
async def get_stats():
    """Get test statistics"""
    history = load_run_history()

    total_runs = len(history)
    passed_runs = sum(1 for r in history if r.get("status") == "passed")
    failed_runs = sum(1 for r in history if r.get("status") == "failed")

    total_tests = sum(r.get("total", 0) for r in history)
    passed_tests = sum(r.get("passed", 0) for r in history)
    failed_tests = sum(r.get("failed", 0) for r in history)

    avg_duration = 0
    durations = [r.get("duration", 0) for r in history if r.get("duration")]
    if durations:
        avg_duration = sum(durations) / len(durations)

    # Trend (last 10 runs)
    recent = history[-10:]
    trend = [{"passed": r.get("passed", 0), "failed": r.get("failed", 0)} for r in recent]

    return {
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "pass_rate": (passed_runs / total_runs * 100) if total_runs > 0 else 0,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "avg_duration": round(avg_duration, 2),
        "trend": trend
    }

@app.get("/api/tests")
async def list_tests():
    """List available tests"""
    backend_tests = []
    frontend_tests = []

    # Scan backend tests
    backend_dir = BASE_DIR / "backend"
    if backend_dir.exists():
        for path in backend_dir.rglob("test_*.py"):
            rel_path = path.relative_to(BASE_DIR)
            backend_tests.append({
                "name": path.stem,
                "path": str(rel_path),
                "category": path.parent.name
            })

    # Scan frontend tests
    for path in BASE_DIR.glob("*.spec.js"):
        frontend_tests.append({
            "name": path.stem,
            "path": str(path.relative_to(BASE_DIR)),
            "category": "e2e"
        })

    for path in BASE_DIR.glob("*.spec.ts"):
        frontend_tests.append({
            "name": path.stem,
            "path": str(path.relative_to(BASE_DIR)),
            "category": "e2e"
        })

    # Scan e2e-journeys
    e2e_dir = BASE_DIR / "e2e-journeys"
    if e2e_dir.exists():
        for path in e2e_dir.glob("*.spec.js"):
            frontend_tests.append({
                "name": path.stem,
                "path": str(path.relative_to(BASE_DIR)),
                "category": "journeys"
            })

    return {
        "backend": backend_tests,
        "frontend": frontend_tests
    }

@app.post("/api/allure/generate")
async def generate_allure_report():
    """Generate Allure report from results"""
    try:
        subprocess.run(
            ["allure", "generate", str(ALLURE_RESULTS), "-o", str(ALLURE_REPORT), "--clean"],
            check=True,
            capture_output=True
        )
        return {"status": "success", "path": str(ALLURE_REPORT)}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e.stderr.decode()}")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Allure CLI not installed. Run: pip install allure-commandline")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


@app.websocket("/ws/visual")
async def visual_websocket_endpoint(websocket: WebSocket):
    """WebSocket for visual runner - receives screenshots from Node.js runner"""
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"[VISUAL WS] Connected. Total clients: {len(connected_clients)}", flush=True)

    try:
        while True:
            # Receive messages from visual runner and broadcast to all clients
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get('type', 'unknown')
            print(f"[VISUAL WS] Received: {msg_type}, broadcasting to {len(connected_clients)-1} clients", flush=True)

            # Broadcast to all dashboard clients
            sent_count = 0
            for client in connected_clients[:]:
                if client != websocket:
                    try:
                        await client.send_json(message)
                        sent_count += 1
                    except Exception as e:
                        print(f"[VISUAL WS] Error sending to client: {e}", flush=True)

            if msg_type == 'screenshot':
                print(f"[VISUAL WS] Screenshot sent to {sent_count} clients", flush=True)

    except WebSocketDisconnect:
        print("[VISUAL WS] Disconnected", flush=True)
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ============ Dashboard HTML ============
def get_dashboard_html():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dumont Cloud - Test Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        dark: { 800: '#1a1a2e', 900: '#0f0f1a' }
                    }
                }
            }
        }
    </script>
    <style>
        :root { --accent: #10b981; }
        body { font-family: 'Inter', system-ui, sans-serif; }
        .terminal {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 12px;
            line-height: 1.5;
            background: #0d1117;
            color: #c9d1d9;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            max-height: 300px;
            overflow-y: auto;
        }
        .terminal .pass { color: #3fb950; }
        .terminal .fail { color: #f85149; }
        .terminal .skip { color: #8b949e; }
        .terminal .info { color: #58a6ff; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .status-dot {
            width: 8px; height: 8px; border-radius: 50%;
            display: inline-block; margin-right: 8px;
        }
        .status-running { background: #f59e0b; }
        .status-passed { background: #10b981; }
        .status-failed { background: #ef4444; }
        .status-pending { background: #6b7280; }
        .browser-frame {
            background: linear-gradient(180deg, #2d2d2d 0%, #1a1a1a 100%);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .browser-toolbar {
            background: #3d3d3d;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .browser-dots {
            display: flex;
            gap: 6px;
        }
        .browser-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        .browser-dot.red { background: #ff5f56; }
        .browser-dot.yellow { background: #ffbd2e; }
        .browser-dot.green { background: #27ca40; }
        .browser-url {
            flex: 1;
            background: #1a1a1a;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
            color: #888;
        }
        .browser-viewport {
            aspect-ratio: 16/10;
            background: #000;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        .browser-viewport img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .step-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .step-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            flex-shrink: 0;
        }
        .step-icon.pending { background: #374151; color: #9ca3af; }
        .step-icon.running { background: #f59e0b; color: #fff; animation: pulse 1s infinite; }
        .step-icon.passed { background: #10b981; color: #fff; }
        .step-icon.failed { background: #ef4444; color: #fff; }
        .live-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: #ef4444;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .live-indicator::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #fff;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        .tab-btn {
            padding: 8px 16px;
            border-radius: 8px 8px 0 0;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: #1a1a2e;
            color: #10b981;
        }
        .tab-btn:not(.active) {
            background: #0f0f1a;
            color: #6b7280;
        }
    </style>
</head>
<body class="dark bg-dark-900 text-gray-100 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <header class="flex items-center justify-between mb-8">
            <div>
                <h1 class="text-2xl font-bold text-white flex items-center gap-3">
                    <span class="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </span>
                    Test Dashboard
                </h1>
                <p class="text-gray-400 mt-1">Dumont Cloud - Backend & Frontend Tests</p>
            </div>
            <div class="flex gap-3">
                <button onclick="runTests('backend')" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition">
                    Run Backend
                </button>
                <button onclick="runTests('frontend')" class="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition">
                    Run Frontend
                </button>
                <button onclick="runVisualTests()" class="px-4 py-2 bg-pink-600 hover:bg-pink-700 rounded-lg font-medium transition flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                    Visual Mode
                </button>
                <button onclick="runTests('all')" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition">
                    Run All
                </button>
            </div>
        </header>

        <!-- Stats Cards -->
        <div class="grid grid-cols-4 gap-4 mb-8" id="stats-cards">
            <div class="bg-dark-800 rounded-xl p-5 border border-gray-800">
                <div class="text-gray-400 text-sm">Total Runs</div>
                <div class="text-3xl font-bold text-white mt-1" id="stat-total">-</div>
            </div>
            <div class="bg-dark-800 rounded-xl p-5 border border-gray-800">
                <div class="text-gray-400 text-sm">Pass Rate</div>
                <div class="text-3xl font-bold text-emerald-400 mt-1" id="stat-rate">-</div>
            </div>
            <div class="bg-dark-800 rounded-xl p-5 border border-gray-800">
                <div class="text-gray-400 text-sm">Avg Duration</div>
                <div class="text-3xl font-bold text-blue-400 mt-1" id="stat-duration">-</div>
            </div>
            <div class="bg-dark-800 rounded-xl p-5 border border-gray-800">
                <div class="text-gray-400 text-sm">Tests Today</div>
                <div class="text-3xl font-bold text-purple-400 mt-1" id="stat-today">-</div>
            </div>
        </div>

        <!-- Visual Test Mode Panel (hidden by default) -->
        <div id="visual-panel" class="mb-8 hidden">
            <div class="grid grid-cols-3 gap-6">
                <!-- Browser Preview -->
                <div class="col-span-2">
                    <div class="browser-frame">
                        <div class="browser-toolbar">
                            <div class="browser-dots">
                                <div class="browser-dot red"></div>
                                <div class="browser-dot yellow"></div>
                                <div class="browser-dot green"></div>
                            </div>
                            <div class="browser-url" id="browser-url">
                                <span class="text-gray-500">Aguardando...</span>
                            </div>
                            <div id="live-badge" class="live-indicator hidden">LIVE</div>
                        </div>
                        <div class="browser-viewport" id="browser-viewport">
                            <div class="text-gray-500 text-center">
                                <svg class="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                                </svg>
                                <p>Clique em "Visual Mode" para iniciar</p>
                                <p class="text-sm text-gray-600 mt-1">O navegador aparecerá aqui em tempo real</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Steps Progress -->
                <div class="col-span-1">
                    <div class="bg-dark-800 rounded-xl border border-gray-800 overflow-hidden h-full">
                        <div class="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
                            <h2 class="font-semibold">Test Steps</h2>
                            <span id="step-counter" class="text-sm text-gray-500">0/0</span>
                        </div>
                        <div class="overflow-y-auto" style="max-height: 400px;" id="steps-list">
                            <div class="p-8 text-gray-500 text-center">
                                <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                                </svg>
                                <p class="text-sm">Os passos do teste aparecerão aqui</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="flex gap-1 mb-0" id="view-tabs">
            <button onclick="switchTab('tests')" class="tab-btn active" data-tab="tests">Tests & Output</button>
            <button onclick="switchTab('visual')" class="tab-btn" data-tab="visual">Visual Mode</button>
        </div>

        <div class="grid grid-cols-3 gap-6" id="tests-panel">
            <!-- Test List -->
            <div class="col-span-1">
                <div class="bg-dark-800 rounded-xl border border-gray-800 overflow-hidden rounded-tl-none">
                    <div class="px-5 py-4 border-b border-gray-800">
                        <h2 class="font-semibold">Available Tests</h2>
                    </div>
                    <div class="divide-y divide-gray-800 max-h-96 overflow-y-auto" id="test-list">
                        <div class="p-4 text-gray-500 text-center">Loading...</div>
                    </div>
                </div>

                <!-- Run History -->
                <div class="bg-dark-800 rounded-xl border border-gray-800 overflow-hidden mt-6">
                    <div class="px-5 py-4 border-b border-gray-800">
                        <h2 class="font-semibold">Recent Runs</h2>
                    </div>
                    <div class="divide-y divide-gray-800 max-h-64 overflow-y-auto" id="history-list">
                        <div class="p-4 text-gray-500 text-center">No runs yet</div>
                    </div>
                </div>
            </div>

            <!-- Output Terminal -->
            <div class="col-span-2">
                <div class="bg-dark-800 rounded-xl border border-gray-800 overflow-hidden">
                    <div class="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <h2 class="font-semibold">Test Output</h2>
                            <span id="run-status" class="text-sm text-gray-500"></span>
                        </div>
                        <button onclick="cancelRun()" id="cancel-btn" class="hidden px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm transition">
                            Cancel
                        </button>
                    </div>
                    <div class="terminal" id="terminal">
                        <div class="text-gray-500">Ready to run tests...</div>
                    </div>
                </div>

                <!-- Results Summary -->
                <div class="bg-dark-800 rounded-xl border border-gray-800 overflow-hidden mt-6" id="results-panel" style="display: none;">
                    <div class="px-5 py-4 border-b border-gray-800">
                        <h2 class="font-semibold">Results</h2>
                    </div>
                    <div class="p-5 grid grid-cols-4 gap-4">
                        <div class="text-center">
                            <div class="text-2xl font-bold text-emerald-400" id="result-passed">0</div>
                            <div class="text-sm text-gray-400">Passed</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-red-400" id="result-failed">0</div>
                            <div class="text-sm text-gray-400">Failed</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-400" id="result-skipped">0</div>
                            <div class="text-sm text-gray-400">Skipped</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-blue-400" id="result-duration">0s</div>
                            <div class="text-sm text-gray-400">Duration</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let currentRunId = null;
        let isVisualMode = false;
        let steps = [];

        // Tab switching
        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tab);
            });
            document.getElementById('tests-panel').classList.toggle('hidden', tab === 'visual');
            document.getElementById('visual-panel').classList.toggle('hidden', tab !== 'visual');
        }

        // WebSocket connection
        function connectWS() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = () => console.log('WebSocket connected');
            ws.onclose = () => {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWS, 2000);
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWSMessage(data);
            };
        }

        function handleWSMessage(data) {
            const terminal = document.getElementById('terminal');
            console.log('[WS] Received:', data.type, data);

            // Visual mode messages
            if (data.type === 'visual_start') {
                isVisualMode = true;
                switchTab('visual');
                document.getElementById('live-badge').classList.remove('hidden');
                document.getElementById('browser-url').innerHTML = '<span class="text-emerald-400">Iniciando navegador...</span>';
                steps = [];
                updateStepsList();
            }
            else if (data.type === 'screenshot') {
                // Update browser viewport with new screenshot (JPEG from visual_runner)
                const viewport = document.getElementById('browser-viewport');
                viewport.innerHTML = `<img src="data:image/jpeg;base64,${data.data}" alt="Browser screenshot" style="width:100%;height:100%;object-fit:contain;"/>`;
            }
            else if (data.type === 'step') {
                steps.push(data.step);
                updateStepsList();
            }
            else if (data.type === 'visual_finished') {
                document.getElementById('live-badge').classList.add('hidden');
                document.getElementById('browser-url').innerHTML = data.status === 'passed'
                    ? '<span class="text-emerald-400">✓ Teste concluído com sucesso</span>'
                    : '<span class="text-red-400">✗ Teste falhou</span>';

                // Update all steps with final status
                if (data.results && data.results.steps) {
                    steps = data.results.steps;
                    updateStepsList();
                }

                // Also show results panel
                document.getElementById('results-panel').style.display = 'block';
                document.getElementById('result-passed').textContent = data.results.passed;
                document.getElementById('result-failed').textContent = data.results.failed;
                document.getElementById('result-skipped').textContent = data.results.skipped;
                document.getElementById('result-duration').textContent = data.results.duration.toFixed(1) + 's';

                loadStats();
                loadHistory();
            }

            // Regular test messages
            if (data.type === 'output') {
                let line = data.line;
                // Colorize output
                if (line.includes('PASSED') || line.includes('passed')) {
                    line = `<span class="pass">${escapeHtml(line)}</span>`;
                } else if (line.includes('FAILED') || line.includes('failed') || line.includes('ERROR')) {
                    line = `<span class="fail">${escapeHtml(line)}</span>`;
                } else if (line.includes('SKIPPED') || line.includes('skipped')) {
                    line = `<span class="skip">${escapeHtml(line)}</span>`;
                } else {
                    line = escapeHtml(line);
                }
                terminal.innerHTML += line;
                terminal.scrollTop = terminal.scrollHeight;
            }
            else if (data.type === 'status') {
                document.getElementById('run-status').innerHTML =
                    `<span class="status-dot status-running pulse"></span> Running...`;
                document.getElementById('cancel-btn').classList.remove('hidden');
            }
            else if (data.type === 'finished') {
                document.getElementById('run-status').innerHTML =
                    data.status === 'passed'
                        ? `<span class="status-dot status-passed"></span> Passed`
                        : `<span class="status-dot status-failed"></span> Failed`;
                document.getElementById('cancel-btn').classList.add('hidden');

                // Show results
                document.getElementById('results-panel').style.display = 'block';
                document.getElementById('result-passed').textContent = data.results.passed;
                document.getElementById('result-failed').textContent = data.results.failed;
                document.getElementById('result-skipped').textContent = data.results.skipped;
                document.getElementById('result-duration').textContent = data.results.duration.toFixed(1) + 's';

                loadStats();
                loadHistory();
            }
            else if (data.type === 'cancelled') {
                document.getElementById('run-status').innerHTML =
                    `<span class="status-dot status-pending"></span> Cancelled`;
                document.getElementById('cancel-btn').classList.add('hidden');
            }
        }

        function updateStepsList() {
            const container = document.getElementById('steps-list');
            const counter = document.getElementById('step-counter');

            const completed = steps.filter(s => s.status === 'passed' || s.status === 'failed').length;
            counter.textContent = `${completed}/${steps.length}`;

            if (steps.length === 0) {
                container.innerHTML = `
                    <div class="p-8 text-gray-500 text-center">
                        <svg class="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                        </svg>
                        <p class="text-sm">Os passos do teste aparecerão aqui</p>
                    </div>`;
                return;
            }

            container.innerHTML = steps.map((step, idx) => {
                let iconClass = 'pending';
                let iconContent = idx + 1;

                if (step.status === 'running') {
                    iconClass = 'running';
                    iconContent = '⟳';
                } else if (step.status === 'passed') {
                    iconClass = 'passed';
                    iconContent = '✓';
                } else if (step.status === 'failed') {
                    iconClass = 'failed';
                    iconContent = '✗';
                }

                return `
                    <div class="step-item">
                        <div class="step-icon ${iconClass}">${iconContent}</div>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm text-white truncate">${escapeHtml(step.name)}</div>
                            ${step.duration ? `<div class="text-xs text-gray-500">${step.duration.toFixed(2)}s</div>` : ''}
                            ${step.error ? `<div class="text-xs text-red-400 mt-1">${escapeHtml(step.error)}</div>` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            // Scroll to latest step
            container.scrollTop = container.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function runTests(type) {
            document.getElementById('terminal').innerHTML = '';
            document.getElementById('results-panel').style.display = 'none';
            isVisualMode = false;

            const response = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type })
            });

            const data = await response.json();
            currentRunId = data.run_id;
        }

        async function runVisualTests(testFile = null) {
            document.getElementById('terminal').innerHTML = '';
            document.getElementById('results-panel').style.display = 'none';
            isVisualMode = true;
            steps = [];
            updateStepsList();

            // Reset browser viewport
            document.getElementById('browser-viewport').innerHTML = `
                <div class="text-gray-500 text-center">
                    <div class="animate-spin w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                    <p>Iniciando navegador...</p>
                </div>`;

            const response = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'frontend_visual',
                    test_file: testFile
                })
            });

            const data = await response.json();
            currentRunId = data.run_id;
        }

        async function cancelRun() {
            if (!currentRunId) return;
            await fetch(`/api/cancel/${currentRunId}`, { method: 'POST' });
        }

        async function loadTests() {
            const response = await fetch('/api/tests');
            const data = await response.json();

            const container = document.getElementById('test-list');
            container.innerHTML = '';

            // Backend tests
            if (data.backend.length > 0) {
                container.innerHTML += `<div class="px-4 py-2 bg-gray-900/50 text-xs font-semibold text-gray-400 uppercase">Backend (${data.backend.length})</div>`;
                data.backend.forEach(test => {
                    container.innerHTML += `
                        <div class="px-4 py-3 hover:bg-gray-800/50 cursor-pointer flex items-center justify-between" onclick="runTests('backend')">
                            <span class="text-sm">${test.name}</span>
                            <span class="text-xs text-gray-500">${test.category}</span>
                        </div>
                    `;
                });
            }

            // Frontend tests
            if (data.frontend.length > 0) {
                container.innerHTML += `<div class="px-4 py-2 bg-gray-900/50 text-xs font-semibold text-gray-400 uppercase">Frontend (${data.frontend.length})</div>`;
                data.frontend.forEach(test => {
                    container.innerHTML += `
                        <div class="px-4 py-3 hover:bg-gray-800/50 cursor-pointer flex items-center justify-between group">
                            <span class="text-sm">${test.name}</span>
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500">${test.category}</span>
                                <button onclick="event.stopPropagation(); runVisualTests('${test.path}')" class="opacity-0 group-hover:opacity-100 px-2 py-1 bg-pink-600 hover:bg-pink-700 rounded text-xs transition">
                                    Visual
                                </button>
                            </div>
                        </div>
                    `;
                });
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();

                document.getElementById('stat-total').textContent = data.total_runs;
                document.getElementById('stat-rate').textContent = data.pass_rate.toFixed(0) + '%';
                document.getElementById('stat-duration').textContent = data.avg_duration + 's';
                document.getElementById('stat-today').textContent = data.total_tests;
            } catch (e) {
                console.error('Failed to load stats:', e);
            }
        }

        async function loadHistory() {
            try {
                const response = await fetch('/api/runs');
                const data = await response.json();

                const container = document.getElementById('history-list');
                const runs = [...data.history].reverse().slice(0, 10);

                if (runs.length === 0) {
                    container.innerHTML = '<div class="p-4 text-gray-500 text-center">No runs yet</div>';
                    return;
                }

                container.innerHTML = runs.map(run => `
                    <div class="px-4 py-3 hover:bg-gray-800/50 cursor-pointer flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="status-dot status-${run.status}"></span>
                            <span class="text-sm">${run.type}</span>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-gray-400">${run.passed}/${run.total}</div>
                            <div class="text-xs text-gray-500">${run.duration?.toFixed(1) || '-'}s</div>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Failed to load history:', e);
            }
        }

        // Initialize
        connectWS();
        loadTests();
        loadStats();
        loadHistory();
    </script>
</body>
</html>'''

# ============ Run Server ============
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Dumont Cloud Test Dashboard")
    print("="*50)
    print(f"\n  URL: http://localhost:8082")
    print(f"\n  Tests directory: {BASE_DIR}")
    print(f"  Reports: {REPORTS_DIR}")
    print("\n" + "="*50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")

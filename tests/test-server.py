import os
import subprocess
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Dumont Cloud Test Runner")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dumont Cloud - Test Runner</title>
        <style>
            body { font-family: system-ui; background: #1a1a2e; color: #eee; padding: 20px; }
            h1 { color: #f59e0b; }
            .section { background: #16213e; padding: 15px; border-radius: 8px; margin: 15px 0; }
            a { color: #60a5fa; }
            button { background: #f59e0b; color: black; border: none; padding: 8px 16px;
                     border-radius: 4px; cursor: pointer; margin: 5px; }
            button:hover { background: #ea580c; }
            pre { background: #0f0f23; padding: 10px; border-radius: 4px; overflow-x: auto; max-height: 400px; }
            .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .success { background: #10b981; color: white; }
            .error { background: #ef4444; color: white; }
            .running { background: #3b82f6; color: white; }
        </style>
    </head>
    <body>
        <h1>Dumont Cloud Test Runner</h1>

        <div class="section">
            <h3>Quick Actions</h3>
            <button onclick="runTest('backend')">Run Backend Tests</button>
            <button onclick="runTest('e2e')">Run E2E Tests</button>
            <button onclick="runTest('unit')">Run Unit Tests</button>
        </div>

        <div class="section">
            <h3>Test Status</h3>
            <div id="status">Click a button to run tests</div>
        </div>

        <div class="section">
            <h3>Output</h3>
            <pre id="output">Waiting for test execution...</pre>
        </div>

        <script>
            async function runTest(type) {
                document.getElementById('status').innerHTML = '<span class="status running">Running...</span>';
                document.getElementById('output').textContent = 'Starting tests...';

                try {
                    const res = await fetch('/run/' + type);
                    const data = await res.json();
                    document.getElementById('output').textContent = data.output;
                    document.getElementById('status').innerHTML = data.success
                        ? '<span class="status success">PASSED</span>'
                        : '<span class="status error">FAILED</span>';
                } catch(e) {
                    document.getElementById('output').textContent = 'Error: ' + e.message;
                    document.getElementById('status').innerHTML = '<span class="status error">ERROR</span>';
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/run/{test_type}")
async def run_tests(test_type: str):
    commands = {
        "backend": f"cd {PROJECT_DIR} && .venv/bin/pytest tests/backend -v --tb=short 2>&1 | tail -50",
        "e2e": f"cd {PROJECT_DIR} && npm exec playwright test -- --reporter=list 2>&1 | tail -50",
        "unit": f"cd {PROJECT_DIR}/web && npm test 2>&1 | tail -50"
    }

    if test_type not in commands:
        raise HTTPException(status_code=400, detail="Invalid test type")

    try:
        result = subprocess.run(commands[test_type], shell=True, capture_output=True, text=True, timeout=120)
        output = result.stdout + result.stderr
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        output = "Test timed out after 120 seconds"
        success = False
    except Exception as e:
        output = str(e)
        success = False

    return {"success": success, "output": output}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")

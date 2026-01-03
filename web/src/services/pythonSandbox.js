/**
 * Python Sandbox Service
 * Uses Pyodide to execute Python code safely in the browser
 * https://pyodide.org/
 */

let pyodide = null
let pyodideLoading = false
let pyodideLoadPromise = null

const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/'

/**
 * Load Pyodide runtime (lazy loading - only when needed)
 */
async function loadPyodide() {
  if (pyodide) return pyodide

  if (pyodideLoading) {
    return pyodideLoadPromise
  }

  pyodideLoading = true

  pyodideLoadPromise = new Promise(async (resolve, reject) => {
    try {
      // Dynamically load the Pyodide script
      if (!window.loadPyodide) {
        const script = document.createElement('script')
        script.src = `${PYODIDE_CDN}pyodide.js`
        script.async = true

        await new Promise((res, rej) => {
          script.onload = res
          script.onerror = () => rej(new Error('Failed to load Pyodide'))
          document.head.appendChild(script)
        })
      }

      // Initialize Pyodide
      pyodide = await window.loadPyodide({
        indexURL: PYODIDE_CDN
      })

      // Load commonly used packages
      await pyodide.loadPackage(['numpy', 'micropip', 'matplotlib', 'pillow'])

      // Set up stdout/stderr capture and matplotlib image capture
      pyodide.runPython(`
import sys
from io import StringIO, BytesIO
import base64

class OutputCapture:
    def __init__(self):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self._stdout = sys.stdout
        self._stderr = sys.stderr

    def __enter__(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        return self

    def __exit__(self, *args):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def get_output(self):
        return self.stdout.getvalue(), self.stderr.getvalue()

_output_capture = OutputCapture

# Patch matplotlib to capture images as base64
def _setup_matplotlib_capture():
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt

        _original_show = plt.show

        def _captured_show(*args, **kwargs):
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            print(f'data:image/png;base64,{img_base64}')
            buf.close()
            plt.close('all')

        plt.show = _captured_show
    except ImportError:
        pass

_setup_matplotlib_capture()
      `)

      console.log('Pyodide loaded successfully')
      resolve(pyodide)
    } catch (error) {
      console.error('Failed to load Pyodide:', error)
      pyodideLoading = false
      reject(error)
    }
  })

  return pyodideLoadPromise
}

/**
 * Check if Pyodide is loaded
 */
export function isPyodideLoaded() {
  return pyodide !== null
}

/**
 * Check if Pyodide is currently loading
 */
export function isPyodideLoading() {
  return pyodideLoading && !pyodide
}

/**
 * Execute Python code in the sandbox
 * @param {string} code - Python code to execute
 * @param {number} timeout - Execution timeout in milliseconds (default: 30000)
 * @returns {Promise<Object>} - Execution result with output, error, and result
 */
export async function executePython(code, timeout = 30000) {
  const startTime = performance.now()

  try {
    // Ensure Pyodide is loaded
    const py = await loadPyodide()

    // Wrap code execution with output capture and timeout
    const wrappedCode = `
_capture = _output_capture()
_result = None
_error = None

with _capture:
    try:
        exec('''${code.replace(/'/g, "\\'")}''')
    except Exception as e:
        _error = str(e)

_stdout, _stderr = _capture.get_output()
(_stdout, _stderr, _error)
`

    // Execute with timeout
    const result = await Promise.race([
      py.runPythonAsync(wrappedCode),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Execution timeout')), timeout)
      )
    ])

    const executionTime = performance.now() - startTime
    const [stdout, stderr, error] = result.toJs()

    return {
      success: !error,
      output: stdout || '',
      error: error || stderr || null,
      executionTime: Math.round(executionTime)
    }
  } catch (error) {
    const executionTime = performance.now() - startTime

    return {
      success: false,
      output: '',
      error: error.message || 'Unknown error',
      executionTime: Math.round(executionTime)
    }
  }
}

/**
 * Install a Python package using micropip
 * @param {string} packageName - Name of the package to install
 */
export async function installPackage(packageName) {
  const py = await loadPyodide()

  try {
    await py.runPythonAsync(`
import micropip
await micropip.install('${packageName}')
    `)
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

/**
 * Preload Pyodide in the background
 * Call this when the user navigates to the Agents page
 */
export function preloadPyodide() {
  if (!pyodide && !pyodideLoading) {
    loadPyodide().catch(console.error)
  }
}

/**
 * Get Pyodide loading status for UI feedback
 */
export function getPyodideStatus() {
  if (pyodide) return 'ready'
  if (pyodideLoading) return 'loading'
  return 'not_loaded'
}

export default {
  executePython,
  installPackage,
  preloadPyodide,
  isPyodideLoaded,
  isPyodideLoading,
  getPyodideStatus
}

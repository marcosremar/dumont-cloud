/**
 * API Helper - Automatically adds JWT token to requests
 */

const API_BASE = ''

/**
 * Check if currently in demo mode
 * Demo mode is active if any of these conditions are true:
 * 1. URL starts with /demo-app
 * 2. URL has ?demo=true parameter
 * 3. localStorage has demo_mode=true (set by tests or login)
 */
export function isDemoMode() {
  // Check URL-based demo mode
  if (window.location.pathname.startsWith('/demo-app')) return true
  if (new URLSearchParams(window.location.search).get('demo') === 'true') return true

  // Check localStorage (set by tests and auth setup)
  if (localStorage.getItem('demo_mode') === 'true') return true

  return false
}

/**
 * Set demo mode flag (called after login with demo credentials)
 */
export function setDemoMode(isDemo) {
  if (isDemo) {
    localStorage.setItem('demo_mode', 'true')
  } else {
    localStorage.removeItem('demo_mode')
  }
}

/**
 * Fetch with authentication
 * Automatically adds JWT token from localStorage
 * In demo mode, adds ?demo=true to API calls
 */
export async function apiFetch(endpoint, options = {}) {
  let token = localStorage.getItem('auth_token')

  // Fallback para sessionStorage
  if (!token) {
    token = sessionStorage.getItem('auth_token')
  }

  const headers = {
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  // Add demo param if in demo mode
  let finalEndpoint = endpoint
  if (isDemoMode()) {
    const separator = endpoint.includes('?') ? '&' : '?'
    finalEndpoint = `${endpoint}${separator}demo=true`
  }

  const response = await fetch(`${API_BASE}${finalEndpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  return response
}

/**
 * GET request with auth
 */
export async function apiGet(endpoint) {
  return apiFetch(endpoint, { method: 'GET' })
}

/**
 * POST request with auth
 */
export async function apiPost(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'POST',
    body: data,
  })
}

/**
 * PUT request with auth
 */
export async function apiPut(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'PUT',
    body: data,
  })
}

/**
 * DELETE request with auth
 */
export async function apiDelete(endpoint) {
  return apiFetch(endpoint, { method: 'DELETE' })
}

export default apiFetch

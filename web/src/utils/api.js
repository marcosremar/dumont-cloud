/**
 * API Helper - Automatically adds JWT token to requests
 */

const API_BASE = ''

/**
 * Check if currently in demo mode
 * True for: demo routes (/demo-app, /demo-docs), OR localStorage demo_mode flag
 */
export function isDemoMode() {
  const path = window.location.pathname
  const demoModeFromStorage = localStorage.getItem('demo_mode') === 'true'
  return path.startsWith('/demo-app') || path.startsWith('/demo-docs') || demoModeFromStorage
}

/**
 * Fetch with authentication
 * Automatically adds JWT token from localStorage
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

  const response = await fetch(`${API_BASE}${endpoint}`, {
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

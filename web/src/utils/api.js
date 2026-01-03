/**
 * API Helper - Automatically adds JWT token to requests
 */

const API_BASE = ''

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

  let body = options.body
  if (body && typeof body === 'object' && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    body,
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

/**
 * Check if currently in demo mode
 * Detects based on URL path or localStorage flag
 */
export function isDemoMode() {
  // Check URL path
  if (typeof window !== 'undefined') {
    const pathname = window.location.pathname
    if (pathname.startsWith('/demo-app') || pathname.startsWith('/demo')) {
      return true
    }
    // Check localStorage flag (set when entering demo)
    if (localStorage.getItem('dumont_demo_mode') === 'true') {
      return true
    }
  }
  return false
}

export default apiFetch

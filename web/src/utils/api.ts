/**
 * API Helper - Automatically adds JWT token to requests
 */

const API_BASE = '';

interface FetchOptions extends RequestInit {
  body?: BodyInit | Record<string, unknown> | null;
}

/**
 * Fetch with authentication
 * Automatically adds JWT token from localStorage
 */
export async function apiFetch(endpoint: string, options: FetchOptions = {}): Promise<Response> {
  let token = localStorage.getItem('auth_token');

  // Fallback para sessionStorage
  if (!token) {
    token = sessionStorage.getItem('auth_token');
  }

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let body = options.body;
  if (body && typeof body === 'object' && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    body: body as BodyInit,
    headers,
    credentials: 'include',
  });

  return response;
}

/**
 * GET request with auth
 */
export async function apiGet(endpoint: string): Promise<Response> {
  return apiFetch(endpoint, { method: 'GET' });
}

/**
 * POST request with auth
 */
export async function apiPost<T = Record<string, unknown>>(endpoint: string, data: T): Promise<Response> {
  return apiFetch(endpoint, {
    method: 'POST',
    body: data as unknown as Record<string, unknown>,
  });
}

/**
 * PUT request with auth
 */
export async function apiPut<T = Record<string, unknown>>(endpoint: string, data: T): Promise<Response> {
  return apiFetch(endpoint, {
    method: 'PUT',
    body: data as unknown as Record<string, unknown>,
  });
}

/**
 * DELETE request with auth
 */
export async function apiDelete(endpoint: string): Promise<Response> {
  return apiFetch(endpoint, { method: 'DELETE' });
}

/**
 * Check if currently in demo mode
 * Always returns false - demo routes were removed
 */
export function isDemoMode(): boolean {
  return false;
}

export default apiFetch;

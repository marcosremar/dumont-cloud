/**
 * Authentication Service
 * Handles all authentication-related API calls and token management
 */

const API_BASE = ''

// Types
export interface User {
  id: string
  username: string
  email: string
  name?: string
  balance?: number
  plan?: string
}

export interface LoginResult {
  success?: boolean
  token?: string
  user?: User
  error?: string
  errorType?: 'credentials' | 'validation' | 'server' | 'timeout' | 'connection' | 'network' | 'unknown'
  hint?: string
}

export interface AuthResult {
  authenticated: boolean
  user?: User
  networkError?: boolean
}

export interface DashboardStats {
  activeMachines: number
  totalMachines: number
  dailyCost: string
  savings: string
  uptime: number
}

/**
 * Login user with credentials
 */
export async function login(username: string, password: string): Promise<LoginResult> {
  // Clear any previous demo mode - real login should use real API
  localStorage.removeItem('demo_mode')

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 5000)

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
      credentials: 'include',
      signal: controller.signal
    })

    clearTimeout(timeoutId)
    const data = await res.json()

    if (!res.ok) {
      return handleLoginError(res.status, data)
    }

    if (data.success) {
      saveAuthData(data.token, data.user)
      return { success: true, token: data.token, user: data.user }
    }

    return { error: data.error || 'Falha no login', errorType: 'unknown' }
  } catch (e) {
    clearTimeout(timeoutId)
    return handleNetworkError(e as Error)
  }
}

/**
 * Logout user
 */
export async function logout(): Promise<void> {
  const token = getToken()

  if (token) {
    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${token}` },
      })
    } catch {
      // Logout API call failed - continue with local cleanup
    }
  }

  clearAuthData()
}

/**
 * Verify current authentication status
 */
export async function verifyAuth(): Promise<AuthResult> {
  const token = getToken()
  if (!token) {
    return { authenticated: false }
  }

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 3000)

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      credentials: 'include',
      headers: { 'Authorization': `Bearer ${token}` },
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    if (!res.ok) {
      if (res.status === 401) {
        clearAuthData()
      }
      return { authenticated: false }
    }

    const text = await res.text()
    const data = text ? JSON.parse(text) : {}

    if (data.authenticated) {
      localStorage.setItem('auth_user', JSON.stringify(data.user))
      return { authenticated: true, user: data.user }
    }

    clearAuthData()
    return { authenticated: false }
  } catch {
    clearTimeout(timeoutId)
    return { authenticated: false, networkError: true }
  }
}

/**
 * Fetch dashboard stats
 */
export async function fetchDashboardStats(): Promise<DashboardStats | null> {
  const token = getToken()
  if (!token) return null

  try {
    const res = await fetch(`${API_BASE}/api/v1/instances`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (res.ok) {
      const data = await res.json()
      const instances = data.instances || []
      const running = instances.filter((i: { status: string }) => i.status === 'running')
      const totalCost = running.reduce((acc: number, i: { dph_total?: number }) => acc + (i.dph_total || 0), 0)

      return {
        activeMachines: running.length,
        totalMachines: instances.length,
        dailyCost: (totalCost * 24).toFixed(2),
        savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
        uptime: running.length > 0 ? 99.9 : 0
      }
    }
  } catch {
    // Silently fail
  }
  return null
}

// Token management
export function getToken(): string | null {
  return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
}

export function saveAuthData(token: string | null, user: User | null): void {
  if (token) {
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_login_time', Date.now().toString())

    if (!localStorage.getItem('auth_token')) {
      sessionStorage.setItem('auth_token', token)
    }
  }
  if (user) {
    localStorage.setItem('auth_user', JSON.stringify(user))
  }
}

export function clearAuthData(): void {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_user')
  localStorage.removeItem('auth_login_time')
  localStorage.removeItem('demo_mode')
  sessionStorage.removeItem('auth_token')
}

export function getStoredUser(): User | null {
  try {
    const token = localStorage.getItem('auth_token')
    const userData = localStorage.getItem('auth_user')
    if (token && userData) {
      const user = JSON.parse(userData) as User
      const loginTime = localStorage.getItem('auth_login_time')
      if (loginTime) {
        const daysSinceLogin = (Date.now() - parseInt(loginTime)) / (1000 * 60 * 60 * 24)
        if (daysSinceLogin > 45) {
          clearAuthData()
          return null
        }
      }
      return user
    }
  } catch {
    // Invalid stored data
  }
  return null
}

// Error handlers
interface ApiErrorData {
  error?: string
  detail?: string
  details?: Array<{ loc?: string[] }>
}

function handleLoginError(status: number, data: ApiErrorData): LoginResult {
  if (status === 401) {
    return {
      error: data.error || data.detail || 'Usuário ou senha incorretos',
      errorType: 'credentials'
    }
  }

  if (status === 400) {
    if (data.details?.some(d => d.loc?.includes('username'))) {
      return {
        error: 'Por favor, insira um e-mail válido',
        errorType: 'validation'
      }
    }
    return {
      error: data.error || data.detail || 'Dados inválidos',
      errorType: 'validation'
    }
  }

  if (status >= 500) {
    return {
      error: 'Erro no servidor. Tente novamente em alguns instantes.',
      errorType: 'server'
    }
  }

  return {
    error: data.error || data.detail || `Erro na autenticação (${status})`,
    errorType: 'unknown'
  }
}

function handleNetworkError(e: Error): LoginResult {
  if (e.name === 'AbortError') {
    return {
      error: 'Servidor offline. Verifique se o backend está rodando.',
      errorType: 'timeout',
      hint: 'Execute: uvicorn src.main:app --reload'
    }
  }

  if (e.name === 'TypeError' && e.message.includes('fetch')) {
    return {
      error: 'Backend offline. Verifique a conexão.',
      errorType: 'connection',
      hint: 'Verifique se o servidor está rodando na porta correta'
    }
  }

  return {
    error: 'Erro de conexão. Verifique sua internet.',
    errorType: 'network'
  }
}

/**
 * Authentication Context
 * Provides authentication state and methods across the application
 */
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { store } from '../store'
import { setToken } from '../store/slices/authSlice'
import * as authService from '../services/authService'
import type { User, LoginResult, DashboardStats } from '../services/authService'

interface AuthContextValue {
  user: User | null
  loading: boolean
  dashboardStats: DashboardStats | null
  setDashboardStats: (stats: DashboardStats | null) => void
  login: (username: string, password: string) => Promise<LoginResult>
  logout: () => Promise<void>
  refreshDashboardStats: () => Promise<void>
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(() => authService.getStoredUser())
  const [loading, setLoading] = useState(() => !authService.getStoredUser())
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null)

  // Fetch dashboard stats
  const refreshDashboardStats = useCallback(async () => {
    const stats = await authService.fetchDashboardStats()
    if (stats) {
      setDashboardStats(stats)
    }
  }, [])

  // Check authentication on mount
  useEffect(() => {
    const initAuth = async () => {
      const storedUser = authService.getStoredUser()

      if (storedUser) {
        const token = authService.getToken()
        if (token) {
          store.dispatch(setToken(token))
        }
        refreshDashboardStats()
        setLoading(false)
        return
      }

      const result = await authService.verifyAuth()

      if (result.authenticated && result.user) {
        setUser(result.user)
        store.dispatch(setToken(authService.getToken()))
      }

      refreshDashboardStats()
      setLoading(false)
    }

    initAuth()

    // Unregister old service workers
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        registrations.forEach(reg => reg.unregister())
      })
    }
  }, [refreshDashboardStats])

  // Login handler
  const handleLogin = useCallback(async (username: string, password: string): Promise<LoginResult> => {
    const result = await authService.login(username, password)

    if (result.success && result.user) {
      setUser(result.user)
      store.dispatch(setToken(result.token || null))
      refreshDashboardStats()
    }

    return result
  }, [refreshDashboardStats])

  // Logout handler
  const handleLogout = useCallback(async () => {
    await authService.logout()
    setUser(null)
    setDashboardStats(null)
    store.dispatch(setToken(null))
  }, [])

  const value: AuthContextValue = {
    user,
    loading,
    dashboardStats,
    setDashboardStats,
    login: handleLogin,
    logout: handleLogout,
    refreshDashboardStats,
    isAuthenticated: !!user
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Hook to access authentication context
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext

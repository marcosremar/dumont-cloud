import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect, createContext, useContext, useMemo, useCallback } from 'react'
import { Provider } from 'react-redux'
import { store } from './store'
import { setToken } from './store/slices/authSlice'
import AppLayout from './components/layout/AppLayout'
import { SidebarProvider } from './context/SidebarContext'
import { ThemeProvider } from './context/ThemeContext'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import EmailPreferences from './pages/Settings/EmailPreferences'
import Login from './pages/Login'
import LandingPage from './pages/LandingPage'
import Machines from './pages/Machines'
import GPUMetrics from './pages/GPUMetrics'
import MetricsHub from './pages/MetricsHub'
import FailoverReportPage from './pages/FailoverReportPage'
import MachinesReportPage from './pages/MachinesReportPage'
import FineTuning from './pages/FineTuning'
import Serverless from './pages/Serverless'
import GpuOffers from './pages/GpuOffers'
import Jobs from './pages/Jobs'
import ChatArena from './pages/ChatArena'
import Models from './pages/Models'
import Savings from './pages/Savings'
import Documentation from './pages/Documentation'
import ButtonShowcase from './pages/ButtonShowcase'
import ForgotPassword from './pages/ForgotPassword'
import TemplatePage from './pages/TemplatePage'
import TemplateDetailPage from './pages/TemplateDetailPage'
import ShareableReportView from './components/tailadmin/reports/ShareableReportView'
import NPSTrends from './pages/Admin/NPSTrends'
import AffiliateDashboard from './components/affiliate/AffiliateDashboard'
import TeamsPage from './pages/TeamsPage'
import TeamDetailsPage from './pages/TeamDetailsPage'
import CreateRolePage from './pages/CreateRolePage'
import Reservations from './pages/Reservations'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import NPSSurvey from './components/NPSSurvey'
import useNPSTrigger, { NPS_TRIGGER_TYPES } from './hooks/useNPSTrigger'
import './styles/landing.css'

const API_BASE = ''

// Context para modo demo
export const DemoContext = createContext(false)
export const useDemoMode = () => useContext(DemoContext)

// Componente para rotas protegidas (requer login)
function ProtectedRoute({ user, children }) {
  const location = useLocation()

  if (!user) {
    // Redireciona para login, salvando a página que o usuário tentou acessar
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}

// Componente wrapper para rotas demo (não requer login)
function DemoRoute({ children }) {
  return (
    <DemoContext.Provider value={true}>
      {children}
    </DemoContext.Provider>
  )
}

/**
 * NPSSurveyManager - Manages NPS survey display and submission
 * This component uses the useNPSTrigger hook to handle survey logic
 * and renders the NPSSurvey modal when appropriate.
 */
function NPSSurveyManager() {
  const {
    isOpen,
    score,
    comment,
    triggerType,
    submitting,
    submitError,
    isAuthenticated,
    handleDismiss,
    handleSubmit,
    handleScoreChange,
    handleCommentChange,
    checkTrigger,
  } = useNPSTrigger({
    triggerType: NPS_TRIGGER_TYPES.MONTHLY,
    autoCheck: false,
    checkOnAuth: true,
  })

  // Check for monthly trigger when component mounts and user is authenticated
  useEffect(() => {
    if (isAuthenticated) {
      // Add a small delay to avoid checking immediately on page load
      const timer = setTimeout(() => {
        checkTrigger(NPS_TRIGGER_TYPES.MONTHLY)
      }, 5000) // 5 second delay after authentication

      return () => clearTimeout(timer)
    }
  }, [isAuthenticated, checkTrigger])

  return (
    <NPSSurvey
      isOpen={isOpen}
      onClose={handleDismiss}
      onDismiss={handleDismiss}
      onSubmit={handleSubmit}
      score={score}
      onScoreChange={handleScoreChange}
      comment={comment}
      onCommentChange={handleCommentChange}
      submitting={submitting}
      error={submitError}
      triggerType={triggerType}
    />
  )
}

// Check if demo mode immediately (before component renders)
const getInitialDemoState = () => {
  const urlParams = new URLSearchParams(window.location.search)
  const isDemoPath = window.location.pathname.startsWith('/demo-app') || window.location.pathname.startsWith('/demo-docs')
  if (urlParams.get('demo') === 'true' || isDemoPath) {
    // CRITICAL: Set demo_mode in localStorage so checkAuth() skips API call
    localStorage.setItem('demo_mode', 'true')
    // Also set a demo token to prevent auth issues
    if (!localStorage.getItem('auth_token')) {
      localStorage.setItem('auth_token', 'demo_token_' + Date.now())
    }
    return { username: 'demo@dumont.cloud', isDemo: true }
  }
  return null
}

// Restore user from localStorage (for session persistence)
const getStoredUser = () => {
  try {
    const token = localStorage.getItem('auth_token')
    const userData = localStorage.getItem('auth_user')
    if (token && userData) {
      const user = JSON.parse(userData)
      // Check if session is still valid (45 days max)
      const loginTime = localStorage.getItem('auth_login_time')
      if (loginTime) {
        const daysSinceLogin = (Date.now() - parseInt(loginTime)) / (1000 * 60 * 60 * 24)
        if (daysSinceLogin > 45) {
          // Session expired
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
          localStorage.removeItem('auth_login_time')
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

export default function App() {
  // Initialize user from: 1) demo state, 2) stored user, 3) null
  const [user, setUser] = useState(() => getInitialDemoState() || getStoredUser())
  const [loading, setLoading] = useState(() => !getInitialDemoState() && !getStoredUser())
  const [dashboardStats, setDashboardStats] = useState(null)

  // Memoize demo user object to prevent creating new object on every render
  const demoUser = useMemo(() => ({ username: 'demo@dumont.cloud', isDemo: true }), [])

  // Memoize demo logout handler to prevent creating new function on every render
  const handleDemoLogout = useCallback(() => {
    window.location.href = '/'
  }, [])

  // Fetch dashboard stats for header display on all pages
  const fetchDashboardStats = useCallback(async () => {
    // Use demo stats in demo mode
    const isDemoMode = localStorage.getItem('demo_mode') === 'true'
    if (isDemoMode) {
      setDashboardStats({
        activeMachines: 2,
        totalMachines: 3,
        dailyCost: '4.80',
        savings: '127',
        uptime: 99.9,
        balance: '4.94'
      })
      return
    }

    try {
      const token = localStorage.getItem('auth_token')
      if (!token) return

      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (res.ok) {
        const data = await res.json()
        const instances = data.instances || []
        const running = instances.filter(i => i.status === 'running')
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0)

        setDashboardStats({
          activeMachines: running.length,
          totalMachines: instances.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
          uptime: running.length > 0 ? 99.9 : 0
        })
      }
    } catch {
      // Silently fail - use demo stats as fallback
      setDashboardStats({
        activeMachines: 2,
        totalMachines: 3,
        dailyCost: '4.80',
        savings: '127',
        uptime: 99.9
      })
    }
  }, [])

  useEffect(() => {
    // If already in demo mode, skip auth check but load stats
    if (user?.isDemo) {
      fetchDashboardStats()
      return
    }

    // If we have a stored user, just sync Redux and skip API validation
    // This makes hot-reload not lose the session
    const storedUser = getStoredUser()
    if (storedUser) {
      const token = localStorage.getItem('auth_token')
      if (token) {
        store.dispatch(setToken(token))
      }
      fetchDashboardStats()
      return
    }

    // Only check auth if we don't have stored user
    checkAuth()
    fetchDashboardStats()

    // Desregistrar Service Workers antigos que podem estar causando cache
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then(registrations => {
        registrations.forEach(reg => reg.unregister())
      })
    }
  }, [])

  const checkAuth = async () => {
    try {
      // Skip API call if in demo mode - just restore demo user
      if (localStorage.getItem('demo_mode') === 'true') {
        const demoToken = localStorage.getItem('auth_token')
        if (demoToken) {
          setUser({
            id: 'demo-user-1',
            username: 'marcosremar@gmail.com',
            email: 'marcosremar@gmail.com',
            name: 'Marcos Remar',
            isDemo: true,
            balance: 150.00,
            plan: 'Pro'
          })
          store.dispatch(setToken(demoToken))
        }
        setLoading(false)
        return
      }

      let token = localStorage.getItem('auth_token')

      // Fallback para sessionStorage
      if (!token) {
        token = sessionStorage.getItem('auth_token')
        if (token) {
          localStorage.setItem('auth_token', token)
        }
      }

      if (!token) {
        setLoading(false)
        return
      }

      // Use AbortController with short timeout to fail fast
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 3000)

      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${token}` },
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      // Handle non-OK responses gracefully
      if (!res.ok) {
        // 401 = token expired/invalid - clear everything
        if (res.status === 401) {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_user')
          localStorage.removeItem('auth_login_time')
          sessionStorage.removeItem('auth_token')
          store.dispatch(setToken(null))
        }
        // For other errors (500, network), keep the session
        // User can continue using the app
        setLoading(false)
        return
      }

      // Parse JSON safely
      let data
      try {
        const text = await res.text()
        data = text ? JSON.parse(text) : {}
      } catch {
        // Invalid JSON - but keep session (might be network issue)
        setLoading(false)
        return
      }

      if (data.authenticated) {
        setUser(data.user)
        // Store user data for session persistence
        localStorage.setItem('auth_user', JSON.stringify(data.user))
        // Sync Redux auth state
        store.dispatch(setToken(token))
      } else {
        // Token is explicitly invalid
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_user')
        localStorage.removeItem('auth_login_time')
        sessionStorage.removeItem('auth_token')
        // Clear Redux auth state
        store.dispatch(setToken(null))
      }
    } catch {
      // Network error - keep the session, don't clear token
      // This prevents logout on hot-reload when backend is temporarily unavailable
    }
    setLoading(false)
  }

  // Demo credentials for offline/development mode
  const DEMO_CREDENTIALS = {
    email: 'marcosremar@gmail.com',
    password: 'dumont123',
    user: {
      id: 'demo-user-1',
      username: 'marcosremar@gmail.com',
      email: 'marcosremar@gmail.com',
      name: 'Marcos Remar',
      isDemo: true,
      balance: 150.00,
      plan: 'Pro'
    }
  }

  const handleLogin = async (username, password) => {
    // Helper function to do demo login
    const doDemoLogin = () => {
      const demoToken = 'demo-token-' + Date.now()
      localStorage.setItem('auth_token', demoToken)
      localStorage.setItem('auth_user', JSON.stringify(DEMO_CREDENTIALS.user))
      localStorage.setItem('auth_login_time', Date.now().toString())
      // NOTE: Don't set demo_mode=true - we want wizard to use real API
      localStorage.removeItem('demo_mode')
      setUser(DEMO_CREDENTIALS.user)
      store.dispatch(setToken(demoToken))
      return { success: true, isDemo: true }
    }

    // Check for demo credentials first (works even if backend is down)
    const isDemoCredentials = (
      (username === DEMO_CREDENTIALS.email || username === 'demo@dumont.cloud') &&
      (password === DEMO_CREDENTIALS.password || password === 'demo')
    )

    try {
      // Timeout para detectar servidor offline
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 segundos (reduzido para falhar rápido)

      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      const data = await res.json()

      // Tratamento de erro HTTP
      if (!res.ok) {
        // 401 - Credenciais inválidas
        if (res.status === 401) {
          // If using demo credentials and backend rejected, still allow demo login
          if (isDemoCredentials) {
            return doDemoLogin()
          }
          return {
            error: data.error || data.detail || 'Usuário ou senha incorretos',
            errorType: 'credentials'
          }
        }

        // 400 - Erro de validação (ex: email inválido)
        if (res.status === 400) {
          // Verificar se é erro de validação de email
          if (data.details && data.details.some(d => d.loc?.includes('username'))) {
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

        // 500 - Erro do servidor
        if (res.status >= 500) {
          // Allow demo login if server error
          if (isDemoCredentials) {
            return doDemoLogin()
          }
          return {
            error: 'Erro no servidor. Tente novamente em alguns instantes.',
            errorType: 'server'
          }
        }

        // Outros erros HTTP
        return {
          error: data.error || data.detail || `Erro na autenticação (${res.status})`,
          errorType: 'unknown'
        }
      }

      // Login bem-sucedido
      if (data.success) {
        if (data.token) {
          localStorage.setItem('auth_token', data.token)
          localStorage.setItem('auth_login_time', Date.now().toString())
          const saved = localStorage.getItem('auth_token')

          // Garantir que o token foi salvo
          if (!saved) {
            // Tentar com sessionStorage como fallback
            sessionStorage.setItem('auth_token', data.token)
          }
        }

        // Store user data for session persistence (survives hot-reload)
        if (data.user) {
          localStorage.setItem('auth_user', JSON.stringify(data.user))
        }

        // Demo mode disabled - always use real data
        localStorage.removeItem('demo_mode')

        setUser(data.user)
        // Sync Redux auth state
        store.dispatch(setToken(data.token))
        return { success: true }
      }

      return { error: data.error || 'Falha no login', errorType: 'unknown' }

    } catch (e) {
      // If backend is offline but using demo credentials, allow login
      if (isDemoCredentials) {
        return doDemoLogin()
      }

      // Timeout ou AbortError - servidor não está respondendo
      if (e.name === 'AbortError') {
        return {
          error: '⚠️ Servidor offline. Use: marcosremar@gmail.com / dumont123',
          errorType: 'timeout',
          hint: 'Use as credenciais demo para acessar sem backend'
        }
      }

      // TypeError: Failed to fetch - servidor offline ou CORS
      if (e.name === 'TypeError' && e.message.includes('fetch')) {
        return {
          error: '🔌 Backend offline. Use: marcosremar@gmail.com / dumont123',
          errorType: 'connection',
          hint: 'Use as credenciais demo para acessar sem backend'
        }
      }

      // Erro de rede genérico
      return {
        error: '⚠️ Erro de conexão. Use: marcosremar@gmail.com / dumont123',
        errorType: 'network',
        hint: 'Use as credenciais demo para acessar sem backend'
      }
    }
  }

  const handleLogout = async () => {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')

    if (token) {
      try {
        await fetch(`${API_BASE}/api/v1/auth/logout`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Authorization': `Bearer ${token}` },
        })
      } catch (e) {
        // Logout API call failed - continue with local cleanup
      }
    }

    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_login_time')
    sessionStorage.removeItem('auth_token')
    localStorage.removeItem('demo_mode')  // Clear demo mode flag
    setUser(null)
    // Clear Redux auth state
    store.dispatch(setToken(null))
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#0a0d0a' }}>
        <div className="spinner" />
      </div>
    )
  }

  return (
    <Provider store={store}>
      <ErrorBoundary>
        <ThemeProvider>
          <SidebarProvider>
            <ToastProvider>
              {/* NPS Survey Manager - handles survey triggers and display */}
              <NPSSurveyManager />
              <Routes>
            {/* Rotas Públicas */}
            <Route path="/" element={
              user ? <Navigate to="/app" replace /> : <LandingPage onLogin={handleLogin} />
            } />
            <Route path="/botoes" element={<ButtonShowcase />} />
            <Route path="/login" element={
              user ? <Navigate to="/app" replace /> : <Login onLogin={handleLogin} />
            } />
            <Route path="/esqueci-senha" element={<ForgotPassword />} />

            {/* Shareable Reports - Public route (no auth required) */}
            <Route path="/reports/:id" element={<ShareableReportView />} />

            {/* Rotas Protegidas (requer login) */}
            <Route path="/app" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Dashboard onStatsUpdate={setDashboardStats} />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/machines" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Machines />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/serverless" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Serverless />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/metrics-hub" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <MetricsHub />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/metrics" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <GPUMetrics />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/settings" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Settings />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/settings/email-preferences" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <EmailPreferences />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/settings/email-preferences" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <EmailPreferences />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/teams" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <TeamsPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/teams/:teamId" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <TeamDetailsPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/teams/:teamId/roles/new" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <CreateRolePage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/failover-report" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <FailoverReportPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/machines-report" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <MachinesReportPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/finetune" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <FineTuning />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/gpu-offers" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <GpuOffers />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/jobs" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Jobs />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/chat-arena" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <ChatArena />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/models" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Models />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/savings" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Savings user={user} onLogout={handleLogout} />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/templates" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <TemplatePage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/templates/:slug" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <TemplateDetailPage />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/affiliate" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <AffiliateDashboard />
                </AppLayout>
              </ProtectedRoute>
            } />
            <Route path="/app/reservations" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <Reservations />
                </AppLayout>
              </ProtectedRoute>
            } />

            {/* Documentation Routes */}
            <Route path="/docs" element={
              <ProtectedRoute user={user}>
                <Documentation />
              </ProtectedRoute>
            } />
            <Route path="/docs/:docId" element={
              <ProtectedRoute user={user}>
                <Documentation />
              </ProtectedRoute>
            } />

            {/* Admin Routes */}
            <Route path="/app/admin/nps" element={
              <ProtectedRoute user={user}>
                <AppLayout user={user} onLogout={handleLogout} dashboardStats={dashboardStats}>
                  <NPSTrends />
                </AppLayout>
              </ProtectedRoute>
            } />

            {/* Rotas Demo - não requer login, dados fictícios */}
            <Route path="/demo-app" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Dashboard onStatsUpdate={setDashboardStats} />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/machines" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Machines />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/serverless" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Serverless />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/metrics-hub" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <MetricsHub />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/metrics" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <GPUMetrics />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/settings" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Settings />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/settings/email-preferences" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <EmailPreferences />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/teams" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <TeamsPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/teams/:teamId" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <TeamDetailsPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/teams/:teamId/roles/new" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <CreateRolePage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/failover-report" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <FailoverReportPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/machines-report" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <MachinesReportPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/finetune" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <FineTuning />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/gpu-offers" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <GpuOffers />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/jobs" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Jobs />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/chat-arena" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <ChatArena />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/models" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Models />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/savings" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Savings user={user || demoUser} onLogout={handleDemoLogout} />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/templates" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <TemplatePage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/templates/:slug" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <TemplateDetailPage />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/affiliate" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <AffiliateDashboard />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-app/reservations" element={
              <DemoRoute>
                <AppLayout user={user || demoUser} onLogout={handleDemoLogout} isDemo={true} dashboardStats={dashboardStats}>
                  <Reservations />
                </AppLayout>
              </DemoRoute>
            } />

            {/* Demo Documentation Routes */}
            <Route path="/demo-docs" element={
              <DemoRoute>
                <AppLayout user={demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Documentation />
                </AppLayout>
              </DemoRoute>
            } />
            <Route path="/demo-docs/:docId" element={
              <DemoRoute>
                <AppLayout user={demoUser} onLogout={handleDemoLogout} isDemo={true}>
                  <Documentation />
                </AppLayout>
              </DemoRoute>
            } />

            {/* Fallback - redireciona para landing page */}
            <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ToastProvider>
        </SidebarProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </Provider>
  )
}

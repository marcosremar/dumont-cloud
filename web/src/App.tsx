/**
 * Application Root Component
 * Sets up providers and renders routes
 */
import { Provider } from 'react-redux'
import { store } from './store'
import { SidebarProvider } from './context/SidebarContext'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/Toast'
import ErrorBoundary from './components/ErrorBoundary'
import NPSSurveyManager from './components/NPSSurveyManager'
import AppRoutes from './routes/AppRoutes'
import './styles/landing.css'

/**
 * Loading Spinner Component
 */
function LoadingSpinner() {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      background: '#0a0d0a'
    }}>
      <div className="spinner" />
    </div>
  )
}

/**
 * App Content - Uses auth context
 */
function AppContent() {
  const { loading } = useAuth()

  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <>
      <NPSSurveyManager />
      <AppRoutes />
    </>
  )
}

/**
 * Main App Component
 */
export default function App() {
  return (
    <Provider store={store}>
      <ErrorBoundary>
        <ThemeProvider>
          <SidebarProvider>
            <ToastProvider>
              <AuthProvider>
                <AppContent />
              </AuthProvider>
            </ToastProvider>
          </SidebarProvider>
        </ThemeProvider>
      </ErrorBoundary>
    </Provider>
  )
}

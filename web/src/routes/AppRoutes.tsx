/**
 * Application Routes
 * Centralized route definitions for the application
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ProtectedRoute from '../components/routing/ProtectedRoute'
import AppLayout from '../components/layout/AppLayout'

// Page imports
import Dashboard from '../pages/Dashboard'
import Settings from '../pages/Settings'
import EmailPreferences from '../pages/Settings/EmailPreferences'
import Login from '../pages/Login'
import LandingPage from '../pages/LandingPage'
import Machines from '../pages/Machines'
import NewMachine from '../pages/NewMachine'
import GPUMetrics from '../pages/GPUMetrics'
import MetricsHub from '../pages/MetricsHub'
import FailoverReportPage from '../pages/FailoverReportPage'
import MachinesReportPage from '../pages/MachinesReportPage'
import FineTuning from '../pages/FineTuning'
import FineTuningJobDetails from '../pages/FineTuningJobDetails'
import Serverless from '../pages/Serverless'
import GpuOffers from '../pages/GpuOffers'
import Jobs from '../pages/Jobs'
import Playground from '../pages/Playground'
import Models from '../pages/Models'
import Savings from '../pages/Savings'
import Documentation from '../pages/Documentation'
import ButtonShowcase from '../pages/ButtonShowcase'
import ForgotPassword from '../pages/ForgotPassword'
import TemplatePage from '../pages/TemplatePage'
import TemplateDetailPage from '../pages/TemplateDetailPage'
import ShareableReportView from '../components/tailadmin/reports/ShareableReportView'
import NPSTrends from '../pages/Admin/NPSTrends'
import AffiliateDashboard from '../components/affiliate/AffiliateDashboard'
import TeamsPage from '../pages/TeamsPage'
import TeamDetailsPage from '../pages/TeamDetailsPage'
import CreateRolePage from '../pages/CreateRolePage'
import Reservations from '../pages/Reservations'
import Agents from '../pages/Agents'

/**
 * Wrapper for protected routes with AppLayout
 */
function ProtectedPage({ children }: { children: React.ReactNode }) {
  const { user, logout, dashboardStats } = useAuth()

  return (
    <ProtectedRoute>
      <AppLayout user={user} onLogout={logout} dashboardStats={dashboardStats}>
        {children}
      </AppLayout>
    </ProtectedRoute>
  )
}

export default function AppRoutes() {
  const { user, login, setDashboardStats } = useAuth()

  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/"
        element={user ? <Navigate to="/app" replace /> : <LandingPage onLogin={login} />}
      />
      <Route path="/botoes" element={<ButtonShowcase />} />
      <Route
        path="/login"
        element={user ? <Navigate to="/app" replace /> : <Login onLogin={login} />}
      />
      <Route path="/esqueci-senha" element={<ForgotPassword />} />
      <Route path="/reports/:id" element={<ShareableReportView />} />

      {/* Protected Routes */}
      <Route
        path="/app"
        element={
          <ProtectedPage>
            <Dashboard onStatsUpdate={setDashboardStats} />
          </ProtectedPage>
        }
      />
      <Route
        path="/app/machines"
        element={<ProtectedPage><Machines /></ProtectedPage>}
      />
      <Route
        path="/app/machines/new"
        element={<ProtectedPage><NewMachine /></ProtectedPage>}
      />
      <Route
        path="/app/serverless"
        element={<ProtectedPage><Serverless /></ProtectedPage>}
      />
      <Route
        path="/app/metrics-hub"
        element={<ProtectedPage><MetricsHub /></ProtectedPage>}
      />
      <Route
        path="/app/metrics"
        element={<ProtectedPage><GPUMetrics /></ProtectedPage>}
      />
      <Route
        path="/app/settings"
        element={<ProtectedPage><Settings /></ProtectedPage>}
      />
      <Route
        path="/app/settings/email-preferences"
        element={<ProtectedPage><EmailPreferences /></ProtectedPage>}
      />
      <Route
        path="/settings/email-preferences"
        element={<ProtectedPage><EmailPreferences /></ProtectedPage>}
      />
      <Route
        path="/app/teams"
        element={<ProtectedPage><TeamsPage /></ProtectedPage>}
      />
      <Route
        path="/app/teams/:teamId"
        element={<ProtectedPage><TeamDetailsPage /></ProtectedPage>}
      />
      <Route
        path="/app/teams/:teamId/roles/new"
        element={<ProtectedPage><CreateRolePage /></ProtectedPage>}
      />
      <Route
        path="/app/failover-report"
        element={<ProtectedPage><FailoverReportPage /></ProtectedPage>}
      />
      <Route
        path="/app/machines-report"
        element={<ProtectedPage><MachinesReportPage /></ProtectedPage>}
      />
      <Route
        path="/app/finetune"
        element={<ProtectedPage><FineTuning /></ProtectedPage>}
      />
      <Route
        path="/app/finetune/:jobId"
        element={<ProtectedPage><FineTuningJobDetails /></ProtectedPage>}
      />
      <Route
        path="/app/gpu-offers"
        element={<ProtectedPage><GpuOffers /></ProtectedPage>}
      />
      <Route
        path="/app/jobs"
        element={<ProtectedPage><Jobs /></ProtectedPage>}
      />
      <Route
        path="/app/playground"
        element={<ProtectedPage><Playground /></ProtectedPage>}
      />
      <Route
        path="/app/agents"
        element={<ProtectedPage><Agents /></ProtectedPage>}
      />
      <Route
        path="/app/models"
        element={<ProtectedPage><Models /></ProtectedPage>}
      />
      <Route
        path="/app/savings"
        element={<ProtectedPage><SavingsPage /></ProtectedPage>}
      />
      <Route
        path="/app/templates"
        element={<ProtectedPage><TemplatePage /></ProtectedPage>}
      />
      <Route
        path="/app/templates/:slug"
        element={<ProtectedPage><TemplateDetailPage /></ProtectedPage>}
      />
      <Route
        path="/app/affiliate"
        element={<ProtectedPage><AffiliateDashboard /></ProtectedPage>}
      />
      <Route
        path="/app/reservations"
        element={<ProtectedPage><Reservations /></ProtectedPage>}
      />

      {/* Documentation Routes */}
      <Route
        path="/docs"
        element={<ProtectedRoute><Documentation /></ProtectedRoute>}
      />
      <Route
        path="/docs/:docId"
        element={<ProtectedRoute><Documentation /></ProtectedRoute>}
      />

      {/* Admin Routes */}
      <Route
        path="/app/admin/nps"
        element={<ProtectedPage><NPSTrends /></ProtectedPage>}
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

/**
 * Savings page wrapper to pass required props
 */
function SavingsPage() {
  const { user, logout } = useAuth()
  return <Savings user={user} onLogout={logout} />
}

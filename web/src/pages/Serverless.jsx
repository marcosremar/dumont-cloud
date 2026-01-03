import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Zap,
  Plus,
  Activity,
  Clock,
  DollarSign,
  Server
} from 'lucide-react'
import ServerlessCard from '../components/serverless/ServerlessCard'
import CreateServerlessModal from '../components/serverless/CreateServerlessModal'

const API_BASE = ''

export default function Serverless() {
  const { t } = useTranslation()
  const location = useLocation()
  const isDemo = location.pathname.startsWith('/demo-app')

  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createError, setCreateError] = useState(null)
  const [stats, setStats] = useState(null)
  const [filter, setFilter] = useState('all') // all, running, idle

  useEffect(() => {
    loadEndpoints()
    loadStats()

    // Poll every 5 seconds
    const interval = setInterval(() => {
      loadEndpoints()
      loadStats()
    }, 5000)

    return () => clearInterval(interval)
  }, [isDemo])

  const loadEndpoints = async () => {
    try {
      if (isDemo) {
        setEndpoints([
          {
            id: 'endpoint-1',
            name: 'llama2-inference',
            status: 'running',
            machine_type: 'spot',
            gpu_name: 'RTX 4090',
            region: 'US',
            created_at: '2024-12-20T10:00:00Z',
            metrics: {
              requests_per_sec: 45.2,
              avg_latency_ms: 120,
              p99_latency_ms: 350,
              cold_starts_24h: 3,
              total_requests_24h: 125000,
              uptime_percent: 99.8,
            },
            pricing: {
              price_per_hour: 0.31,
              price_per_request: 0.00001,
              cost_24h: 7.44,
            },
            auto_scaling: {
              enabled: true,
              min_instances: 0,
              max_instances: 5,
              current_instances: 2,
            },
          },
          {
            id: 'endpoint-2',
            name: 'stable-diffusion-xl',
            status: 'running',
            machine_type: 'on-demand',
            gpu_name: 'RTX 3090',
            region: 'EU',
            created_at: '2024-12-19T15:30:00Z',
            metrics: {
              requests_per_sec: 12.8,
              avg_latency_ms: 2500,
              p99_latency_ms: 4200,
              cold_starts_24h: 0,
              total_requests_24h: 32000,
              uptime_percent: 100,
            },
            pricing: {
              price_per_hour: 0.20,
              price_per_request: 0.00005,
              cost_24h: 4.80,
            },
            auto_scaling: {
              enabled: true,
              min_instances: 1,
              max_instances: 3,
              current_instances: 1,
            },
          },
          {
            id: 'endpoint-3',
            name: 'whisper-transcription',
            status: 'scaled_to_zero',
            machine_type: 'spot',
            gpu_name: 'RTX 3080',
            region: 'ASIA',
            created_at: '2024-12-18T08:00:00Z',
            metrics: {
              requests_per_sec: 0,
              avg_latency_ms: 0,
              p99_latency_ms: 0,
              cold_starts_24h: 15,
              total_requests_24h: 3500,
              uptime_percent: 92.5,
            },
            pricing: {
              price_per_hour: 0.15,
              price_per_request: 0.00002,
              cost_24h: 0.70,
            },
            auto_scaling: {
              enabled: true,
              min_instances: 0,
              max_instances: 10,
              current_instances: 0,
            },
          },
        ])
        setLoading(false)
        return
      }

      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/serverless/endpoints`, {
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
      const data = await res.json()
      setEndpoints(data.endpoints || [])
    } catch (e) {
      console.error('Failed to load serverless endpoints:', e)
    }
    setLoading(false)
  }

  const loadStats = async () => {
    try {
      if (isDemo) {
        setStats({
          total_endpoints: 3,
          total_requests_24h: 160500,
          avg_latency_ms: 856,
          total_cost_24h: 12.94,
          active_instances: 3,
          cold_starts_24h: 18,
        })
        return
      }

      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/serverless/stats`, {
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
      const data = await res.json()
      setStats({
        total_requests_24h: data.total_requests_24h || 0,
        avg_latency_ms: data.avg_latency_ms || 0,
        total_cost_24h: data.total_cost_24h || 0,
        active_instances: data.active_instances || 0,
        cold_starts_24h: data.cold_starts_24h || 0,
        ...data
      })
    } catch (e) {
      console.error('Failed to load serverless stats:', e)
      setStats({
        total_requests_24h: 0,
        avg_latency_ms: 0,
        total_cost_24h: 0,
        active_instances: 0,
        cold_starts_24h: 0,
      })
    }
  }

  const handleCreateEndpoint = async (config) => {
    try {
      setCreateError(null)

      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/serverless/endpoints`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(config)
      })

      if (res.ok) {
        setShowCreateModal(false)
        loadEndpoints()
      } else {
        const errorData = await res.json().catch(() => ({}))
        const errorMsg = errorData.detail || errorData.error || errorData.message || `Error ${res.status}: Failed to create endpoint`
        setCreateError(errorMsg)
      }
    } catch (e) {
      console.error('Failed to create endpoint:', e)
      setCreateError('Network error: Failed to create endpoint')
    }
  }

  // Filter endpoints
  const runningEndpoints = endpoints.filter(e => e.status === 'running')
  const idleEndpoints = endpoints.filter(e => e.status !== 'running')

  const filteredEndpoints = filter === 'running'
    ? runningEndpoints
    : filter === 'idle'
      ? idleEndpoints
      : endpoints

  // Loading state
  if (loading) {
    return (
      <div className="page-container">
        <div className="ta-card p-6">
          <div className="flex items-center justify-center py-12">
            <div className="ta-spinner" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500/20 to-brand-600/10 flex items-center justify-center border border-brand-500/20">
              <Zap className="w-6 h-6 text-brand-400" />
            </div>
            <div className="flex flex-col justify-center">
              <h1 className="page-title leading-tight">Serverless Functions</h1>
              <p className="page-subtitle mt-0.5">Auto-scaling GPU endpoints with pay-per-request</p>
            </div>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="ta-btn ta-btn-primary"
          >
            <Plus className="w-4 h-4" />
            Deploy Function
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="stats-grid mb-6">
          <div className="stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-card-label">Requests (24h)</p>
                <p className="stat-card-value">{(stats.total_requests_24h || 0).toLocaleString()}</p>
              </div>
              <Activity className="w-5 h-5 text-brand-400" />
            </div>
          </div>

          <div className="stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-card-label">Avg Latency</p>
                <p className="stat-card-value">{stats.avg_latency_ms || 0}ms</p>
              </div>
              <Clock className="w-5 h-5 text-violet-400" />
            </div>
          </div>

          <div className="stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-card-label">Cost (24h)</p>
                <p className="stat-card-value text-emerald-400">${(stats.total_cost_24h || 0).toFixed(2)}</p>
              </div>
              <DollarSign className="w-5 h-5 text-emerald-400" />
            </div>
          </div>

          <div className="stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="stat-card-label">Active Instances</p>
                <p className="stat-card-value text-amber-400">{stats.active_instances || 0}</p>
              </div>
              <Server className="w-5 h-5 text-amber-400" />
            </div>
          </div>
        </div>
      )}

      {/* Main Card with Filter Tabs */}
      <div className="ta-card">
        <div className="ta-card-header">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              {[
                { id: 'all', label: 'All', count: endpoints.length, icon: Zap },
                { id: 'running', label: 'Running', count: runningEndpoints.length, icon: Activity, color: 'text-emerald-400' },
                { id: 'idle', label: 'Idle', count: idleEndpoints.length, icon: null, color: 'text-gray-400' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFilter(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    filter === tab.id
                      ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700/50 border border-transparent'
                  }`}
                >
                  {tab.icon && <tab.icon className={`w-4 h-4 ${filter === tab.id ? 'text-brand-400' : tab.color || ''}`} />}
                  <span>{tab.label}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${
                    filter === tab.id ? 'bg-brand-500/30 text-brand-300' : 'bg-gray-700 text-gray-400'
                  }`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Auto-refresh</span>
            </div>
          </div>
        </div>

        <div className="ta-card-body">
          {/* Empty State */}
          {filteredEndpoints.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-500/10 mb-4">
                <Zap className="w-8 h-8 text-brand-400" />
              </div>
              <h3 className="text-lg font-medium text-white mb-2">
                {filter === 'all' ? 'No Serverless Functions' : filter === 'running' ? 'No Running Functions' : 'No Idle Functions'}
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                {filter === 'all'
                  ? 'Deploy your first GPU-powered serverless function.'
                  : filter === 'running'
                    ? 'All functions are idle or scaled to zero.'
                    : 'All functions are currently running.'}
              </p>
              {filter === 'all' && (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="ta-btn ta-btn-primary"
                >
                  <Plus className="w-4 h-4" />
                  Deploy Function
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredEndpoints.map((endpoint) => (
                <ServerlessCard
                  key={endpoint.id}
                  endpoint={endpoint}
                  onReload={loadEndpoints}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateServerlessModal
          onClose={() => { setShowCreateModal(false); setCreateError(null) }}
          onCreate={handleCreateEndpoint}
          error={createError}
        />
      )}
    </div>
  )
}

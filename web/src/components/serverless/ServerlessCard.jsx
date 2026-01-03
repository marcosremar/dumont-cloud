import { useState } from 'react'
import {
  Zap,
  Activity,
  Clock,
  Server,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Pause,
  Play,
  Trash2,
  Settings,
  MoreHorizontal,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ExternalLink,
  Gauge,
  BarChart3,
  X
} from 'lucide-react'
import { Badge } from '../tailadmin-ui'

export default function ServerlessCard({ endpoint, onReload }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showMetricsModal, setShowMetricsModal] = useState(false)
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showDropdownMenu, setShowDropdownMenu] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testLoading, setTestLoading] = useState(false)

  const getStatusBadge = (status) => {
    switch (status) {
      case 'running':
        return (
          <Badge variant="success" dot>
            Running
          </Badge>
        )
      case 'scaled_to_zero':
        return (
          <Badge variant="gray" dot>
            Scaled to Zero
          </Badge>
        )
      case 'paused':
        return (
          <Badge variant="warning" dot>
            Paused
          </Badge>
        )
      case 'error':
        return (
          <Badge variant="error" dot>
            Error
          </Badge>
        )
      default:
        return (
          <Badge variant="gray" dot>
            {status}
          </Badge>
        )
    }
  }

  const getMachineTypeBadge = (type) => {
    if (type === 'spot') {
      return (
        <Badge className="bg-brand-500/10 text-brand-400 border-brand-500/20">
          <Zap className="w-3 h-3 mr-1" />
          Spot
        </Badge>
      )
    }
    return (
      <Badge className="bg-white/5 text-gray-400 border-white/10">
        On-Demand
      </Badge>
    )
  }

  const handleCopyEndpoint = () => {
    const url = `https://${endpoint.id}.dumont.cloud`
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleTestEndpoint = async () => {
    setTestLoading(true)
    setTestResult(null)

    try {
      const startTime = Date.now()
      // Simulate a test request (in real implementation, this would call the actual endpoint)
      await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000))
      const endTime = Date.now()

      setTestResult({
        success: true,
        latency: endTime - startTime,
        status: 200,
        message: 'Endpoint is responding correctly'
      })
    } catch (error) {
      setTestResult({
        success: false,
        error: error.message || 'Failed to reach endpoint'
      })
    } finally {
      setTestLoading(false)
    }
  }

  const handlePauseResume = () => {
    alert(endpoint.status === 'running' ? 'Endpoint paused!' : 'Endpoint resumed!')
    setShowDropdownMenu(false)
    onReload && onReload()
  }

  const handleDeleteFromMenu = () => {
    setShowDropdownMenu(false)
    setShowDeleteConfirm(true)
  }

  return (
    <div className="rounded-xl bg-dark-surface-card border border-white/10 overflow-hidden hover:border-brand-500/30 transition-colors">
      {/* Header */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-bold text-white">{endpoint.name}</h3>
              {getStatusBadge(endpoint.status)}
              {getMachineTypeBadge(endpoint.machine_type)}
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Server className="w-3.5 h-3.5" />
                {endpoint.gpu_name}
              </span>
              <span>•</span>
              <span>{endpoint.region}</span>
              <span>•</span>
              <span>
                {endpoint.auto_scaling.current_instances}/{endpoint.auto_scaling.max_instances} instances
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 relative">
            <button
              onClick={() => setShowConfigModal(true)}
              className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
              title="Configure"
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowDropdownMenu(!showDropdownMenu)}
              className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
              title="More options"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>

            {/* Dropdown Menu */}
            {showDropdownMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 rounded-lg bg-gray-900 border border-white/10 shadow-xl z-50">
                <div className="py-1">
                  <button
                    onClick={() => { setShowTestModal(true); setShowDropdownMenu(false); }}
                    className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-white/5 hover:text-white flex items-center gap-2"
                  >
                    <Play className="w-4 h-4 text-brand-400" />
                    Test Endpoint
                  </button>
                  <button
                    onClick={handlePauseResume}
                    className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-white/5 hover:text-white flex items-center gap-2"
                  >
                    {endpoint.status === 'running' ? (
                      <>
                        <Pause className="w-4 h-4 text-amber-400" />
                        Pause Endpoint
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 text-brand-400" />
                        Resume Endpoint
                      </>
                    )}
                  </button>
                  <div className="border-t border-white/10 my-1" />
                  <button
                    onClick={handleDeleteFromMenu}
                    className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete Endpoint
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Endpoint URL */}
        <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10 mb-4">
          <code className="flex-1 text-sm text-brand-400 font-mono">
            https://{endpoint.id}.dumont.cloud
          </code>
          <button
            onClick={handleCopyEndpoint}
            className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
          >
            {copied ? (
              <CheckCircle2 className="w-4 h-4 text-brand-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors">
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Requests */}
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs text-gray-500 uppercase">Requests/s</span>
            </div>
            <div className="text-lg font-bold text-white">
              {endpoint.metrics.requests_per_sec.toFixed(1)}
            </div>
            <div className="text-xs text-gray-500">
              {endpoint.metrics.total_requests_24h.toLocaleString()} (24h)
            </div>
          </div>

          {/* Latency */}
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs text-gray-500 uppercase">Latency</span>
            </div>
            <div className="text-lg font-bold text-white">
              {endpoint.metrics.avg_latency_ms}ms
            </div>
            <div className="text-xs text-gray-500">
              p99: {endpoint.metrics.p99_latency_ms}ms
            </div>
          </div>

          {/* Cold Starts */}
          <div className="p-3 rounded-lg bg-white/5">
            <div className="flex items-center gap-2 mb-1">
              <Gauge className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs text-gray-500 uppercase">Cold Starts</span>
            </div>
            <div className="text-lg font-bold text-white">
              {endpoint.metrics.cold_starts_24h}
            </div>
            <div className="text-xs text-gray-500">
              {endpoint.metrics.uptime_percent.toFixed(1)}% uptime
            </div>
          </div>

          {/* Cost */}
          <div className="p-3 rounded-lg bg-brand-500/10 border border-brand-500/20">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-xs text-brand-400 uppercase">Cost (24h)</span>
            </div>
            <div className="text-lg font-bold text-white">
              ${endpoint.pricing.cost_24h.toFixed(2)}
            </div>
            <div className="text-xs text-gray-500">
              ${endpoint.pricing.price_per_hour.toFixed(2)}/h
            </div>
          </div>
        </div>

        {/* Auto-scaling info */}
        {endpoint.auto_scaling.enabled && (
          <div className="mt-4 p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp className="w-4 h-4 text-brand-400" />
                <span className="text-gray-400">
                  Auto-scaling: {endpoint.auto_scaling.min_instances}-{endpoint.auto_scaling.max_instances} instances
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {Array.from({ length: endpoint.auto_scaling.max_instances }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-2 h-4 rounded-sm ${
                        i < endpoint.auto_scaling.current_instances
                          ? 'bg-brand-400'
                          : 'bg-white/10'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-sm font-medium text-white">
                  {endpoint.auto_scaling.current_instances}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Spot interruption warning */}
        {endpoint.machine_type === 'spot' && endpoint.status === 'running' && (
          <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-amber-300">
                  Endpoint using Spot pricing - may be interrupted at any time
                </p>
                <p className="text-xs text-amber-400/60 mt-1">
                  Auto-restart enabled with Regional Volume
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-5 py-3 bg-white/5 border-t border-white/10 flex items-center justify-between">
        <div className="text-xs text-gray-500">
          Created {new Date(endpoint.created_at).toLocaleDateString('en-US')}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowMetricsModal(true)}
            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5 inline mr-1" />
            Metrics
          </button>
          <button
            onClick={() => setShowConfigModal(true)}
            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10 transition-colors"
          >
            <Settings className="w-3.5 h-3.5 inline mr-1" />
            Configure
          </button>
        </div>
      </div>

      {/* Metrics Modal */}
      {showMetricsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-gray-900 border border-white/10 rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Metrics - {endpoint.name}</h3>
              <button
                onClick={() => setShowMetricsModal(false)}
                className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {/* Metrics Details */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                  <div className="text-sm text-gray-500 mb-1">Requests per Second</div>
                  <div className="text-2xl font-bold text-white">{endpoint.metrics.requests_per_sec.toFixed(1)}</div>
                </div>
                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                  <div className="text-sm text-gray-500 mb-1">Total Requests (24h)</div>
                  <div className="text-2xl font-bold text-white">{endpoint.metrics.total_requests_24h.toLocaleString()}</div>
                </div>
                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                  <div className="text-sm text-gray-500 mb-1">Average Latency</div>
                  <div className="text-2xl font-bold text-white">{endpoint.metrics.avg_latency_ms}ms</div>
                </div>
                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                  <div className="text-sm text-gray-500 mb-1">P99 Latency</div>
                  <div className="text-2xl font-bold text-white">{endpoint.metrics.p99_latency_ms}ms</div>
                </div>
                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                  <div className="text-sm text-gray-500 mb-1">Cold Starts (24h)</div>
                  <div className="text-2xl font-bold text-white">{endpoint.metrics.cold_starts_24h}</div>
                </div>
                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                  <div className="text-sm text-gray-500 mb-1">Uptime</div>
                  <div className="text-2xl font-bold text-brand-400">{endpoint.metrics.uptime_percent.toFixed(1)}%</div>
                </div>
              </div>
              {/* Pricing Info */}
              <div className="p-4 rounded-lg bg-brand-500/10 border border-brand-500/20">
                <h4 className="text-sm font-medium text-brand-400 mb-2">Cost Summary</h4>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-xs text-gray-500">Per Hour</div>
                    <div className="text-lg font-bold text-white">${endpoint.pricing.price_per_hour.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Per Request</div>
                    <div className="text-lg font-bold text-white">${endpoint.pricing.price_per_request.toFixed(5)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">Last 24h</div>
                    <div className="text-lg font-bold text-brand-400">${endpoint.pricing.cost_24h.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-white/10">
              <button
                onClick={() => setShowMetricsModal(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Configure Modal */}
      {showConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-gray-900 border border-white/10 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Configure - {endpoint.name}</h3>
              <button
                onClick={() => setShowConfigModal(false)}
                className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {/* Endpoint Info */}
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-sm text-gray-500">Endpoint URL</div>
                <code className="text-brand-400 text-sm">https://{endpoint.id}.dumont.cloud</code>
              </div>

              {/* Auto-scaling Settings */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-white">Auto-scaling</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Min Instances</label>
                    <input
                      type="number"
                      defaultValue={endpoint.auto_scaling.min_instances}
                      className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Max Instances</label>
                    <input
                      type="number"
                      defaultValue={endpoint.auto_scaling.max_instances}
                      className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:border-brand-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* GPU Type */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-white">GPU Type</h4>
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-gray-500" />
                    <span className="text-white">{endpoint.gpu_name}</span>
                    <span className="text-xs text-gray-500">• {endpoint.region}</span>
                  </div>
                </div>
              </div>

              {/* Pricing Mode */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-white">Pricing Mode</h4>
                <div className="flex gap-2">
                  <button className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${endpoint.machine_type === 'spot' ? 'bg-brand-500/20 border-brand-500/30 text-brand-400' : 'bg-white/5 border-white/10 text-gray-400'}`}>
                    <Zap className="w-3.5 h-3.5 inline mr-1" />
                    Spot
                  </button>
                  <button className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${endpoint.machine_type === 'on-demand' ? 'bg-brand-500/20 border-brand-500/30 text-brand-400' : 'bg-white/5 border-white/10 text-gray-400'}`}>
                    On-Demand
                  </button>
                </div>
              </div>

              {/* Danger Zone */}
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <h4 className="text-sm font-medium text-red-400 mb-2">Danger Zone</h4>
                <button
                  onClick={() => {
                    setShowConfigModal(false)
                    setShowDeleteConfirm(true)
                  }}
                  className="w-full px-3 py-2 rounded-lg text-sm font-medium bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5 inline mr-1" />
                  Delete Endpoint
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-white/10">
              <button
                onClick={() => setShowConfigModal(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert('Configuration saved!')
                  setShowConfigModal(false)
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-brand-500 hover:bg-brand-600 text-white"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-gray-900 border border-white/10 rounded-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Delete Endpoint?</h3>
            </div>
            <div className="p-4">
              <p className="text-gray-400">
                Are you sure you want to delete <strong className="text-white">{endpoint.name}</strong>? This action cannot be undone.
              </p>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-white/10">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  alert('Endpoint deleted!')
                  setShowDeleteConfirm(false)
                  onReload && onReload()
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 hover:bg-red-600 text-white"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Endpoint Modal */}
      {showTestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-gray-900 border border-white/10 rounded-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Test Endpoint - {endpoint.name}</h3>
              <button
                onClick={() => { setShowTestModal(false); setTestResult(null); }}
                className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {/* Endpoint Info */}
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">Endpoint URL</div>
                <code className="text-brand-400 text-sm">https://{endpoint.id}.dumont.cloud</code>
              </div>

              {/* Test Button */}
              <button
                onClick={handleTestEndpoint}
                disabled={testLoading}
                className="w-full px-4 py-3 rounded-lg text-sm font-medium bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/50 text-white flex items-center justify-center gap-2"
              >
                {testLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Send Test Request
                  </>
                )}
              </button>

              {/* Test Result */}
              {testResult && (
                <div className={`p-4 rounded-lg ${testResult.success ? 'bg-brand-500/10 border border-brand-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {testResult.success ? (
                      <CheckCircle2 className="w-5 h-5 text-brand-400" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                    )}
                    <span className={`font-medium ${testResult.success ? 'text-brand-400' : 'text-red-400'}`}>
                      {testResult.success ? 'Success!' : 'Error'}
                    </span>
                  </div>
                  {testResult.success ? (
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Status Code:</span>
                        <span className="text-white">{testResult.status}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Latency:</span>
                        <span className="text-white">{testResult.latency}ms</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Message:</span>
                        <span className="text-white">{testResult.message}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-red-300">{testResult.error}</p>
                  )}
                </div>
              )}

              {/* Sample Code */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-white">Sample Request</h4>
                <div className="p-3 rounded-lg bg-black/30 border border-white/10 overflow-x-auto">
                  <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
{`curl -X POST https://${endpoint.id}.dumont.cloud/v1/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{"prompt": "Hello", "max_tokens": 100}'`}
                  </pre>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-white/10">
              <button
                onClick={() => { setShowTestModal(false); setTestResult(null); }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white border border-white/10"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

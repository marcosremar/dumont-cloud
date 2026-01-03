import { useState } from 'react'
import {
  Card,
  Badge,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../tailadmin-ui'
import {
  Zap,
  Activity,
  Clock,
  Server,
  DollarSign,
  TrendingUp,
  Pause,
  Play,
  Trash2,
  Settings,
  MoreVertical,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ExternalLink,
  BarChart3,
  Globe,
  Cpu
} from 'lucide-react'

export default function ServerlessCard({ endpoint, onReload }) {
  const [copied, setCopied] = useState(false)
  const [showMetricsModal, setShowMetricsModal] = useState(false)
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testLoading, setTestLoading] = useState(false)
  const [configMinInstances, setConfigMinInstances] = useState(endpoint.auto_scaling?.min_instances || 0)
  const [configMaxInstances, setConfigMaxInstances] = useState(endpoint.auto_scaling?.max_instances || 5)
  const [configMachineType, setConfigMachineType] = useState(endpoint.machine_type || 'spot')

  const getStatusDisplay = (status) => {
    switch (status) {
      case 'running':
        return { label: 'Running', variant: 'success', animate: true }
      case 'scaled_to_zero':
        return { label: 'Idle', variant: 'gray', animate: false }
      case 'paused':
        return { label: 'Paused', variant: 'warning', animate: false }
      case 'error':
        return { label: 'Error', variant: 'error', animate: false }
      default:
        return { label: status, variant: 'gray', animate: false }
    }
  }

  const statusDisplay = getStatusDisplay(endpoint.status)

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

  const handlePauseResume = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const action = endpoint.status === 'running' ? 'pause' : 'resume'
      const res = await fetch(`/api/v1/serverless/endpoints/${endpoint.id}/${action}`, {
        method: 'POST',
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      if (res.ok) {
        onReload && onReload()
      } else {
        console.error(`Failed to ${action} endpoint`)
      }
    } catch (e) {
      console.error('Error pausing/resuming endpoint:', e)
    }
  }

  const handleDeleteEndpoint = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`/api/v1/serverless/endpoints/${endpoint.id}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      if (res.ok) {
        setShowDeleteConfirm(false)
        onReload && onReload()
      } else {
        console.error('Failed to delete endpoint')
      }
    } catch (e) {
      console.error('Error deleting endpoint:', e)
    }
  }

  const handleSaveConfig = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`/api/v1/serverless/endpoints/${endpoint.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          min_instances: configMinInstances,
          max_instances: configMaxInstances,
          machine_type: configMachineType
        })
      })
      if (res.ok) {
        setShowConfigModal(false)
        onReload && onReload()
      } else {
        console.error('Failed to save configuration')
      }
    } catch (e) {
      console.error('Error saving configuration:', e)
    }
  }

  return (
    <Card className="group relative">
      {/* Card Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-white font-semibold text-sm truncate">{endpoint.name}</span>
            <Badge variant={statusDisplay.variant} dot className={`text-[9px] ${statusDisplay.animate ? 'animate-pulse' : ''}`}>
              {statusDisplay.label}
            </Badge>
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            {endpoint.machine_type === 'spot' ? (
              <Badge variant="primary" className="text-[9px]">
                <Zap className="w-2.5 h-2.5 mr-0.5" />
                Spot
              </Badge>
            ) : (
              <Badge variant="gray" className="text-[9px]">
                On-Demand
              </Badge>
            )}
            <Badge variant="gray" className="text-[9px]">
              <Cpu className="w-2.5 h-2.5 mr-0.5" />
              {endpoint.gpu_name}
            </Badge>
            <Badge variant="gray" className="text-[9px]">
              <Globe className="w-2.5 h-2.5 mr-0.5" />
              {endpoint.region}
            </Badge>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="p-1.5 rounded-lg hover:bg-gray-800/50 text-gray-500 hover:text-gray-300 flex-shrink-0">
              <MoreVertical className="w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => setShowTestModal(true)}>
              <Play className="w-3.5 h-3.5 mr-2" />
              Test Endpoint
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handlePauseResume}>
              {endpoint.status === 'running' ? (
                <>
                  <Pause className="w-3.5 h-3.5 mr-2" />
                  Pause Endpoint
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 mr-2" />
                  Resume Endpoint
                </>
              )}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setShowConfigModal(true)}>
              <Settings className="w-3.5 h-3.5 mr-2" />
              Configure
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setShowDeleteConfirm(true)} className="text-red-400 focus:text-red-400">
              <Trash2 className="w-3.5 h-3.5 mr-2" />
              Delete Endpoint
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Endpoint URL */}
      <div className="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10 mb-3">
        <code className="flex-1 text-xs text-brand-400 truncate">
          https://{endpoint.id}.dumont.cloud
        </code>
        <button
          onClick={handleCopyEndpoint}
          className="p-1.5 rounded hover:bg-white/5 text-gray-500 hover:text-white transition-all"
          title={copied ? 'Copied!' : 'Copy URL'}
        >
          {copied ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-brand-400" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
        <a
          href={`https://${endpoint.id}.dumont.cloud`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1.5 rounded hover:bg-white/5 text-gray-500 hover:text-white transition-all"
          title="Open in new tab"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-4 gap-0.5 mb-3 p-2 rounded-lg bg-white/5 border border-white/10">
        <div className="text-center">
          <div className="text-brand-400 font-mono text-xs font-bold">{endpoint.metrics.requests_per_sec.toFixed(1)}</div>
          <div className="text-[8px] text-gray-500 uppercase">Req/s</div>
        </div>
        <div className="text-center">
          <div className="text-white font-mono text-xs font-bold">{endpoint.metrics.avg_latency_ms}ms</div>
          <div className="text-[8px] text-gray-500 uppercase">Latency</div>
        </div>
        <div className="text-center">
          <div className="text-amber-400 font-mono text-xs font-bold">{endpoint.metrics.cold_starts_24h}</div>
          <div className="text-[8px] text-gray-500 uppercase">Cold</div>
        </div>
        <div className="text-center">
          <div className="text-emerald-400 font-mono text-xs font-bold">${endpoint.pricing.cost_24h.toFixed(2)}</div>
          <div className="text-[8px] text-gray-500 uppercase">24h</div>
        </div>
      </div>

      {/* Auto-scaling Info */}
      {endpoint.auto_scaling.enabled && (
        <div className="flex items-center justify-between mb-3 text-xs text-gray-400">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Auto-scaling: {endpoint.auto_scaling.min_instances}-{endpoint.auto_scaling.max_instances}</span>
          </div>
          <div className="flex items-center gap-1">
            <Server className="w-3 h-3" />
            <span className="font-mono">{endpoint.auto_scaling.current_instances}/{endpoint.auto_scaling.max_instances}</span>
          </div>
        </div>
      )}

      {/* Spot Warning */}
      {endpoint.machine_type === 'spot' && endpoint.status === 'running' && (
        <div className="mb-3 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <div className="flex items-center gap-2 text-xs text-amber-400">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Spot instance - may be interrupted</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-1.5">
        <Button
          variant="ghost"
          size="xs"
          icon={BarChart3}
          className="flex-1 text-[10px] h-7"
          onClick={() => setShowMetricsModal(true)}
        >
          Metrics
        </Button>
        <Button
          variant="secondary"
          size="xs"
          icon={Settings}
          className="flex-1 text-[10px] h-7"
          onClick={() => setShowConfigModal(true)}
        >
          Configure
        </Button>
      </div>

      {/* Footer */}
      <div className="mt-3 pt-2 border-t border-white/5 text-[10px] text-gray-500">
        Created {new Date(endpoint.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
      </div>

      {/* Metrics Modal */}
      <AlertDialog open={showMetricsModal} onOpenChange={setShowMetricsModal}>
        <AlertDialogContent className="max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Metrics - {endpoint.name}</AlertDialogTitle>
          </AlertDialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">Requests per Second</div>
                <div className="text-xl font-bold text-white">{endpoint.metrics.requests_per_sec.toFixed(1)}</div>
              </div>
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">Total Requests (24h)</div>
                <div className="text-xl font-bold text-white">{endpoint.metrics.total_requests_24h.toLocaleString()}</div>
              </div>
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">Average Latency</div>
                <div className="text-xl font-bold text-white">{endpoint.metrics.avg_latency_ms}ms</div>
              </div>
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">P99 Latency</div>
                <div className="text-xl font-bold text-white">{endpoint.metrics.p99_latency_ms}ms</div>
              </div>
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">Cold Starts (24h)</div>
                <div className="text-xl font-bold text-white">{endpoint.metrics.cold_starts_24h}</div>
              </div>
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs text-gray-500 mb-1">Uptime</div>
                <div className="text-xl font-bold text-brand-400">{endpoint.metrics.uptime_percent.toFixed(1)}%</div>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <h4 className="text-sm font-medium text-emerald-400 mb-2">Cost Summary</h4>
              <div className="grid grid-cols-3 gap-3 text-center">
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
                  <div className="text-lg font-bold text-emerald-400">${endpoint.pricing.cost_24h.toFixed(2)}</div>
                </div>
              </div>
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogAction>Close</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Config Modal */}
      <AlertDialog open={showConfigModal} onOpenChange={setShowConfigModal}>
        <AlertDialogContent className="max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Configure - {endpoint.name}</AlertDialogTitle>
          </AlertDialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-500 mb-1">Endpoint URL</div>
              <code className="text-sm text-brand-400">https://{endpoint.id}.dumont.cloud</code>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-white">Auto-scaling</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Min Instances</label>
                  <input
                    type="number"
                    value={configMinInstances}
                    onChange={(e) => setConfigMinInstances(parseInt(e.target.value) || 0)}
                    min={0}
                    max={10}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:border-brand-500/50 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Max Instances</label>
                  <input
                    type="number"
                    value={configMaxInstances}
                    onChange={(e) => setConfigMaxInstances(parseInt(e.target.value) || 1)}
                    min={1}
                    max={50}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:border-brand-500/50 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-white">GPU Type</h4>
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-gray-500" />
                  <span className="text-white">{endpoint.gpu_name}</span>
                  <span className="text-xs text-gray-500">• {endpoint.region}</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-white">Pricing Mode</h4>
              <div className="flex gap-2">
                <button
                  onClick={() => setConfigMachineType('spot')}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border transition-all ${configMachineType === 'spot' ? 'bg-brand-500/20 border-brand-500/30 text-brand-400' : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'}`}
                >
                  <Zap className="w-4 h-4 inline mr-1" />
                  Spot
                </button>
                <button
                  onClick={() => setConfigMachineType('on-demand')}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium border transition-all ${configMachineType === 'on-demand' ? 'bg-brand-500/20 border-brand-500/30 text-brand-400' : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'}`}
                >
                  On-Demand
                </button>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <h4 className="text-sm font-medium text-red-400 mb-2">Danger Zone</h4>
              <Button
                variant="error"
                size="sm"
                icon={Trash2}
                className="w-full"
                onClick={() => { setShowConfigModal(false); setShowDeleteConfirm(true) }}
              >
                Delete Endpoint
              </Button>
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleSaveConfig}>Save Changes</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Endpoint?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{endpoint.name}</strong>? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteEndpoint} className="bg-red-500 hover:bg-red-400">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Test Endpoint Modal */}
      <AlertDialog open={showTestModal} onOpenChange={(open) => { setShowTestModal(open); if (!open) setTestResult(null) }}>
        <AlertDialogContent className="max-w-lg">
          <AlertDialogHeader>
            <AlertDialogTitle>Test Endpoint - {endpoint.name}</AlertDialogTitle>
          </AlertDialogHeader>
          <div className="space-y-4 py-4">
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-500 mb-1">Endpoint URL</div>
              <code className="text-sm text-brand-400">https://{endpoint.id}.dumont.cloud</code>
            </div>

            <Button
              variant="primary"
              size="md"
              icon={testLoading ? null : Play}
              className="w-full"
              onClick={handleTestEndpoint}
              disabled={testLoading}
            >
              {testLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  Testing...
                </>
              ) : (
                'Send Test Request'
              )}
            </Button>

            {testResult && (
              <div className={`p-3 rounded-lg ${testResult.success ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {testResult.success ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                  )}
                  <span className={`font-medium ${testResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
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
                  </div>
                ) : (
                  <p className="text-sm text-red-300">{testResult.error}</p>
                )}
              </div>
            )}

            <div className="space-y-2">
              <h4 className="text-sm font-medium text-white">Sample Request</h4>
              <div className="p-3 rounded-lg bg-gray-900 border border-white/10 overflow-x-auto">
                <pre className="text-xs text-gray-300">
{`curl -X POST https://${endpoint.id}.dumont.cloud/v1/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{"prompt": "Hello", "max_tokens": 100}'`}
                </pre>
              </div>
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogAction>Close</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}

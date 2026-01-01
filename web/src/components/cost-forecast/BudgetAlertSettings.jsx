import { useState, useEffect } from 'react'
import { Bell, DollarSign, Mail, Save, AlertCircle, CheckCircle } from 'lucide-react'
import { Slider } from '../ui/slider'
import { Switch } from '../ui/switch'
import { Label } from '../ui/label'

const API_BASE = ''

export default function BudgetAlertSettings({ getAuthHeaders, selectedGPU = 'RTX 4090' }) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const [alertsEnabled, setAlertsEnabled] = useState(false)
  const [threshold, setThreshold] = useState([50])
  const [email, setEmail] = useState('')
  const [dailyDigest, setDailyDigest] = useState(false)

  const loadSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/budget-settings`, {
        credentials: 'include',
        headers: getAuthHeaders ? getAuthHeaders() : {}
      })

      if (res.ok) {
        const result = await res.json()
        setAlertsEnabled(result.alerts_enabled || false)
        setThreshold([result.threshold_percentage || 50])
        setEmail(result.notification_email || '')
        setDailyDigest(result.daily_digest || false)
      } else if (res.status === 404) {
        // No settings found, use defaults
      } else {
        setError('Failed to load settings')
      }
    } catch (err) {
      // Settings endpoint may not exist yet, use defaults
    }
    setLoading(false)
  }

  useEffect(() => {
    loadSettings()
  }, [])

  const handleSave = async () => {
    if (alertsEnabled && !email) {
      setError('Email is required when alerts are enabled')
      return
    }

    if (alertsEnabled && !validateEmail(email)) {
      setError('Please enter a valid email address')
      return
    }

    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/budget-settings`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(getAuthHeaders ? getAuthHeaders() : {})
        },
        body: JSON.stringify({
          alerts_enabled: alertsEnabled,
          threshold_percentage: threshold[0],
          notification_email: email,
          daily_digest: dailyDigest,
          gpu_name: selectedGPU
        })
      })

      if (res.ok) {
        setSuccess('Settings saved successfully')
        setTimeout(() => setSuccess(null), 3000)
      } else {
        const errorData = await res.json()
        setError(errorData.detail || 'Failed to save settings')
      }
    } catch (err) {
      setError('Error saving settings')
    }
    setSaving(false)
  }

  const validateEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  const formatCurrency = (value) => `$${value.toFixed(0)}`

  if (loading) {
    return (
      <div className="ta-card">
        <div className="ta-card-body flex items-center justify-center min-h-[200px]">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  return (
    <div className="ta-card hover-glow">
      <div className="ta-card-header flex justify-between items-center">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-warning pulse-dot">
            <Bell size={18} />
          </div>
          Budget Alert Settings
        </h3>
        <span className="gpu-badge">{selectedGPU}</span>
      </div>

      <div className="ta-card-body">
        {/* Alerts Toggle */}
        <div className="flex items-center justify-between p-3 bg-white/[0.02] rounded-xl border border-white/5 mb-4 animate-fade-in" style={{ animationDelay: '0ms' }}>
          <div className="flex items-center gap-3">
            <div className="stat-card-icon stat-card-icon-primary">
              <Bell size={16} />
            </div>
            <div>
              <Label htmlFor="alerts-enabled" className="text-sm font-medium text-gray-200 cursor-pointer">
                Enable Budget Alerts
              </Label>
              <p className="text-xs text-gray-500 mt-0.5">
                Get notified when costs exceed threshold
              </p>
            </div>
          </div>
          <Switch
            id="alerts-enabled"
            checked={alertsEnabled}
            onCheckedChange={setAlertsEnabled}
          />
        </div>

        {/* Budget Threshold Slider */}
        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/5 mb-4 animate-fade-in" style={{ animationDelay: '50ms' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="stat-card-icon stat-card-icon-success">
                <DollarSign size={16} />
              </div>
              <Label className="text-sm font-medium text-gray-200">
                Daily Budget Threshold
              </Label>
            </div>
            <span className="text-lg font-bold text-brand-400">
              {formatCurrency(threshold[0])}/day
            </span>
          </div>
          <Slider
            value={threshold}
            onValueChange={setThreshold}
            max={500}
            min={10}
            step={5}
            disabled={!alertsEnabled}
            className={!alertsEnabled ? 'opacity-50' : ''}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>$10</span>
            <span>$250</span>
            <span>$500</span>
          </div>
        </div>

        {/* Email Input */}
        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/5 mb-4 animate-fade-in" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-2 mb-3">
            <div className="stat-card-icon stat-card-icon-primary">
              <Mail size={16} />
            </div>
            <Label htmlFor="email-input" className="text-sm font-medium text-gray-200">
              Notification Email
            </Label>
          </div>
          <input
            id="email-input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={!alertsEnabled}
            placeholder="your@email.com"
            className={`w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 placeholder:text-gray-500 ${!alertsEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          />
        </div>

        {/* Daily Digest Toggle */}
        <div className="flex items-center justify-between p-3 bg-white/[0.02] rounded-xl border border-white/5 mb-4 animate-fade-in" style={{ animationDelay: '150ms' }}>
          <div className="flex items-center gap-3">
            <div className="stat-card-icon stat-card-icon-success">
              <Mail size={16} />
            </div>
            <div>
              <Label htmlFor="daily-digest" className="text-sm font-medium text-gray-200 cursor-pointer">
                Daily Cost Digest
              </Label>
              <p className="text-xs text-gray-500 mt-0.5">
                Receive daily summary of costs
              </p>
            </div>
          </div>
          <Switch
            id="daily-digest"
            checked={dailyDigest}
            onCheckedChange={setDailyDigest}
            disabled={!alertsEnabled}
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4 text-sm text-red-400 animate-fade-in">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="flex items-center gap-2 p-3 bg-brand-500/10 border border-brand-500/20 rounded-lg mb-4 text-sm text-brand-400 animate-fade-in">
            <CheckCircle size={16} />
            {success}
          </div>
        )}

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full px-4 py-3 bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/50 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          {saving ? (
            <div className="ta-spinner w-4 h-4" />
          ) : (
            <>
              <Save size={16} />
              Save Settings
            </>
          )}
        </button>

        {/* Footer Info */}
        <div className="flex justify-between pt-3 mt-4 border-t border-white/10 text-xs">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-500"></span>
            <span className="text-gray-400">Status:</span>
            <span className={alertsEnabled ? 'text-brand-400 font-semibold' : 'text-gray-500'}>
              {alertsEnabled ? 'Active' : 'Disabled'}
            </span>
          </span>
          <span className="text-gray-500">
            Alerts for {selectedGPU}
          </span>
        </div>
      </div>
    </div>
  )
}

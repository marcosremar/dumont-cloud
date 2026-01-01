import { useState, useEffect } from 'react'
import { Target, TrendingUp, Activity, BarChart2, RefreshCw } from 'lucide-react'

const API_BASE = ''

export default function AccuracyTracker({ getAuthHeaders, selectedGPU = 'RTX 4090' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/metrics/spot/forecast-accuracy/${encodeURIComponent(selectedGPU)}?days=30`,
        {
          credentials: 'include',
          headers: getAuthHeaders()
        }
      )
      if (res.ok) {
        const result = await res.json()
        setData(result)
      } else {
        const errorData = await res.json().catch(() => ({}))
        setError(errorData.error || 'Failed to load accuracy data')
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [selectedGPU])

  const formatPercent = (value) => `${value?.toFixed(1) || '0.0'}%`
  const formatAccuracy = (mape) => {
    // Accuracy is 100% minus MAPE (lower MAPE = higher accuracy)
    const accuracy = Math.max(0, 100 - (mape || 0))
    return `${accuracy.toFixed(1)}%`
  }
  const formatMoney = (value) => `$${value?.toFixed(4) || '0.0000'}`

  const getAccuracyLevel = (mape) => {
    if (mape === null || mape === undefined) return { label: 'N/A', color: 'text-gray-400' }
    if (mape <= 5) return { label: 'Excellent', color: 'text-brand-400' }
    if (mape <= 10) return { label: 'Good', color: 'text-blue-400' }
    if (mape <= 20) return { label: 'Fair', color: 'text-yellow-400' }
    return { label: 'Needs Improvement', color: 'text-red-400' }
  }

  if (loading) {
    return (
      <div className="ta-card">
        <div className="ta-card-body flex items-center justify-center min-h-[120px]">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="ta-card">
        <div className="ta-card-header">
          <h3 className="ta-card-title flex items-center gap-2">
            <div className="stat-card-icon stat-card-icon-primary">
              <Target size={18} />
            </div>
            Prediction Accuracy
          </h3>
        </div>
        <div className="ta-card-body">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <p className="text-gray-400 text-sm mb-3">{error}</p>
            <button
              onClick={loadData}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
            >
              <RefreshCw size={14} />
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const accuracyLevel = getAccuracyLevel(data?.mape)

  return (
    <div className="ta-card hover-glow">
      <div className="ta-card-header flex justify-between items-center">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-success pulse-dot">
            <Target size={18} />
          </div>
          Prediction Accuracy
        </h3>
        <span className="gpu-badge">{data?.gpu_name || selectedGPU}</span>
      </div>

      <div className="ta-card-body">
        {/* Main MAPE Display */}
        <div className="text-center mb-4 p-4 bg-white/[0.02] rounded-xl border border-white/5 animate-fade-in">
          <div className="text-4xl font-bold text-brand-400 mb-1">
            {formatAccuracy(data?.mape)}
          </div>
          <div className="text-sm text-gray-400">
            accurate over last {data?.evaluation_period_days || 30} days
          </div>
          <div className={`text-xs mt-2 font-semibold ${accuracyLevel.color}`}>
            {accuracyLevel.label}
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '50ms' }}>
            <div className="stat-card-icon stat-card-icon-primary">
              <Activity size={16} />
            </div>
            <div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide">MAPE</span>
              <span className="text-lg font-bold text-brand-400">{formatPercent(data?.mape)}</span>
            </div>
          </div>
          <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '100ms' }}>
            <div className="stat-card-icon stat-card-icon-info">
              <BarChart2 size={16} />
            </div>
            <div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide">R-Squared</span>
              <span className="text-lg font-bold text-blue-400">
                {data?.r_squared !== null ? formatPercent(data?.r_squared * 100) : 'N/A'}
              </span>
            </div>
          </div>
          <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '150ms' }}>
            <div className="stat-card-icon stat-card-icon-warning">
              <TrendingUp size={16} />
            </div>
            <div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide">MAE</span>
              <span className="text-lg font-bold text-yellow-400">{formatMoney(data?.mae)}/h</span>
            </div>
          </div>
          <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '200ms' }}>
            <div className="stat-card-icon stat-card-icon-danger">
              <Activity size={16} />
            </div>
            <div>
              <span className="block text-[11px] text-gray-400 uppercase tracking-wide">RMSE</span>
              <span className="text-lg font-bold text-red-400">{formatMoney(data?.rmse)}/h</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between pt-3 border-t border-white/10 text-xs">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-500"></span>
            <span className="text-gray-400">Samples:</span>
            <span className="text-brand-400 font-semibold">{data?.num_samples || 0}</span>
          </span>
          <span className="text-gray-500">Model: {data?.model_version || 'v1.0'}</span>
        </div>
      </div>
    </div>
  )
}

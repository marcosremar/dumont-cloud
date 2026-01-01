import { useState, useEffect } from 'react'
import { Clock, Target, TrendingDown, Zap, DollarSign, AlertCircle } from 'lucide-react'

const API_BASE = ''

export default function OptimalTimingCard({ getAuthHeaders, selectedGPU = 'RTX 4090' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [jobDuration, setJobDuration] = useState(8)
  const [inputValue, setInputValue] = useState('8')

  const loadData = async (duration) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics/spot/optimal-timing`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(getAuthHeaders ? getAuthHeaders() : {})
        },
        body: JSON.stringify({
          gpu_name: selectedGPU,
          job_duration_hours: duration,
          machine_type: 'interruptible'
        })
      })

      if (res.ok) {
        const result = await res.json()
        setData(result)
      } else if (res.status === 400) {
        const errorData = await res.json()
        setError(errorData.detail?.error || 'Insufficient historical data')
      } else {
        setError('Failed to load optimal timing data')
      }
    } catch (err) {
      setError('Error connecting to server')
    }
    setLoading(false)
  }

  useEffect(() => {
    loadData(jobDuration)
  }, [selectedGPU])

  const handleSubmit = (e) => {
    e.preventDefault()
    const duration = parseFloat(inputValue)
    if (duration > 0 && duration <= 168) {
      setJobDuration(duration)
      loadData(duration)
    }
  }

  const handleInputChange = (e) => {
    setInputValue(e.target.value)
  }

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}`
  const formatPercent = (value) => `${(value || 0).toFixed(1)}%`

  const formatDateTime = (isoString) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getRecommendationStyle = (recommendation) => {
    switch (recommendation) {
      case 'excellent':
        return {
          badgeClass: 'bg-brand-500/20 text-brand-400 border-brand-500/30',
          icon: <Zap size={12} className="text-brand-400" />
        }
      case 'good':
        return {
          badgeClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
          icon: <Target size={12} className="text-blue-400" />
        }
      default:
        return {
          badgeClass: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
          icon: <Clock size={12} className="text-gray-400" />
        }
    }
  }

  const getRankBadgeStyle = (rank) => {
    switch (rank) {
      case 1:
        return 'bg-brand-500 text-white'
      case 2:
        return 'bg-blue-500 text-white'
      case 3:
        return 'bg-gray-500 text-white'
      default:
        return 'bg-gray-600 text-gray-300'
    }
  }

  if (error && !data) {
    return (
      <div className="ta-card">
        <div className="ta-card-header flex justify-between items-center">
          <h3 className="ta-card-title flex items-center gap-2">
            <div className="stat-card-icon stat-card-icon-warning">
              <AlertCircle size={18} />
            </div>
            Optimal Timing
          </h3>
          <span className="gpu-badge">{selectedGPU}</span>
        </div>
        <div className="ta-card-body flex flex-col items-center justify-center min-h-[200px] text-center">
          <AlertCircle size={48} className="text-yellow-500 mb-4" />
          <p className="text-gray-400 mb-2">{error}</p>
          <p className="text-gray-500 text-sm">Need at least 50 hours of price history</p>
          <button
            onClick={() => loadData(jobDuration)}
            className="mt-4 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="ta-card hover-glow">
      <div className="ta-card-header flex justify-between items-center">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-primary pulse-dot">
            <Clock size={18} />
          </div>
          Optimal Timing
        </h3>
        <span className="gpu-badge">{data?.gpu_name || selectedGPU}</span>
      </div>

      <div className="ta-card-body">
        {/* Job Duration Input */}
        <form onSubmit={handleSubmit} className="mb-4">
          <label className="block text-[11px] text-gray-400 uppercase tracking-wide mb-2">
            Job Duration (hours)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              value={inputValue}
              onChange={handleInputChange}
              min="0.5"
              max="168"
              step="0.5"
              className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500"
              placeholder="Enter hours..."
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/50 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              {loading ? (
                <div className="ta-spinner w-4 h-4" />
              ) : (
                <>
                  <Target size={14} />
                  Find Best Time
                </>
              )}
            </button>
          </div>
        </form>

        {loading && !data && (
          <div className="flex items-center justify-center min-h-[200px]">
            <div className="ta-spinner" />
          </div>
        )}

        {data && (
          <>
            {/* Summary Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
              <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '0ms' }}>
                <div className="stat-card-icon stat-card-icon-success">
                  <TrendingDown size={16} />
                </div>
                <div>
                  <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Best Cost</span>
                  <span className="text-lg font-bold text-brand-400">{formatPrice(data.best_time_cost)}</span>
                </div>
              </div>
              <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '50ms' }}>
                <div className="stat-card-icon stat-card-icon-danger">
                  <DollarSign size={16} />
                </div>
                <div>
                  <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Worst Cost</span>
                  <span className="text-lg font-bold text-red-400">{formatPrice(data.worst_time_cost)}</span>
                </div>
              </div>
              <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in col-span-2 sm:col-span-1" style={{ animationDelay: '100ms' }}>
                <div className="stat-card-icon stat-card-icon-primary">
                  <Zap size={16} />
                </div>
                <div>
                  <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Max Savings</span>
                  <span className="text-lg font-bold text-blue-400">{formatPrice(data.max_potential_savings)}</span>
                </div>
              </div>
            </div>

            {/* Top 3 Time Windows */}
            <div className="space-y-3">
              <h4 className="text-xs text-gray-400 uppercase tracking-wide font-medium">
                Top 3 Time Windows
              </h4>
              {data.time_windows?.map((window, index) => {
                const recStyle = getRecommendationStyle(window.recommendation)
                return (
                  <div
                    key={index}
                    className="p-3 bg-white/[0.02] rounded-xl border border-white/5 hover:border-white/10 transition-colors animate-fade-in"
                    style={{ animationDelay: `${150 + index * 50}ms` }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        {/* Rank Badge */}
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${getRankBadgeStyle(window.rank)}`}>
                          {window.rank}
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-gray-200">
                              {formatDateTime(window.start_time)}
                            </span>
                            <span className={`px-1.5 py-0.5 text-[10px] rounded border flex items-center gap-1 ${recStyle.badgeClass}`}>
                              {recStyle.icon}
                              {window.recommendation}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            Duration: {data.job_duration_hours}h &bull; Ends: {formatDateTime(window.end_time)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-brand-400">
                          {formatPrice(window.estimated_cost)}
                        </div>
                        <div className="text-xs text-brand-400">
                          Save {formatPercent(window.savings_percentage)}
                        </div>
                      </div>
                    </div>
                    {/* Savings Bar */}
                    <div className="mt-2 pt-2 border-t border-white/5">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-gray-500">Savings vs worst time</span>
                        <span className="text-brand-400 font-medium">{formatPrice(window.savings_vs_worst)}</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-brand-500 to-brand-400 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(window.savings_percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Footer */}
            <div className="flex flex-wrap justify-between items-center pt-3 mt-4 border-t border-white/10 text-xs gap-2">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-brand-500"></span>
                <span className="text-gray-400">Confidence:</span>
                <span className="text-brand-400 font-semibold">{formatPercent(data.model_confidence * 100)}</span>
              </span>
              <span className="flex items-center gap-2">
                <span className="text-gray-400">Current:</span>
                <span className="text-gray-300">{formatPrice(data.current_price)}/h</span>
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

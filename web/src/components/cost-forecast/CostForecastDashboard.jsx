import { useState, useEffect, useMemo } from 'react'
import { TrendingUp, TrendingDown, Calendar, DollarSign, Target, AlertCircle, RefreshCw, Link2Off } from 'lucide-react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
)

const API_BASE = ''

export default function CostForecastDashboard({ getAuthHeaders, selectedGPU = 'RTX 4090' }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [calendarEvents, setCalendarEvents] = useState([])
  const [calendarStatus, setCalendarStatus] = useState(null)
  const [showCalendarEvents, setShowCalendarEvents] = useState(true)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/metrics/spot/cost-forecast/${encodeURIComponent(selectedGPU)}`,
        {
          credentials: 'include',
          headers: getAuthHeaders ? getAuthHeaders() : {}
        }
      )

      if (res.ok) {
        const result = await res.json()
        setData(result)
      } else if (res.status === 400) {
        const errorData = await res.json()
        setError(errorData.detail || 'Insufficient historical data for forecast')
      } else {
        setError('Failed to load forecast data')
      }
    } catch (err) {
      setError('Error connecting to server')
    }
    setLoading(false)
  }

  const loadCalendarData = async () => {
    try {
      const headers = getAuthHeaders ? getAuthHeaders() : {}

      // Fetch calendar status first
      const statusRes = await fetch(
        `${API_BASE}/api/v1/metrics/spot/calendar-status`,
        { credentials: 'include', headers }
      )

      if (statusRes.ok) {
        const statusData = await statusRes.json()
        setCalendarStatus(statusData)

        // Only fetch events if connected
        if (statusData.connected) {
          const eventsRes = await fetch(
            `${API_BASE}/api/v1/metrics/spot/calendar-events?days=7`,
            { credentials: 'include', headers }
          )

          if (eventsRes.ok) {
            const eventsData = await eventsRes.json()
            setCalendarEvents(eventsData.events || [])
          }
        }
      }
    } catch (err) {
      // Silently fail - calendar is optional
      setCalendarStatus({ connected: false, needs_reauthorization: false })
    }
  }

  const handleReconnectCalendar = () => {
    if (calendarStatus?.authorization_url) {
      window.open(calendarStatus.authorization_url, '_blank', 'width=600,height=700')
    }
  }

  useEffect(() => {
    loadData()
    loadCalendarData()
  }, [selectedGPU])

  const formatPrice = (price) => `$${price?.toFixed(2) || '0.00'}`
  const formatPercent = (value) => `${((value || 0) * 100).toFixed(0)}%`

  // Map calendar events to chart x-axis indices
  const getCalendarEventIndices = () => {
    if (!data?.daily_forecasts || !calendarEvents.length) return []

    const forecastDates = data.daily_forecasts.map(d => new Date(d.date).toDateString())

    return calendarEvents
      .map(event => {
        const eventDate = new Date(event.start_time).toDateString()
        const index = forecastDates.indexOf(eventDate)
        if (index === -1) return null
        return {
          index,
          title: event.title,
          start_time: event.start_time,
          is_compute_intensive: event.is_compute_intensive,
          duration_hours: event.duration_hours
        }
      })
      .filter(Boolean)
  }

  // Custom Chart.js plugin to draw calendar event vertical lines
  const calendarEventPlugin = useMemo(() => ({
    id: 'calendarEvents',
    afterDatasetsDraw: (chart) => {
      if (!showCalendarEvents) return

      const eventIndices = getCalendarEventIndices()
      if (!eventIndices.length) return

      const { ctx, chartArea, scales } = chart
      const { left, right, top, bottom } = chartArea

      eventIndices.forEach(event => {
        const x = scales.x.getPixelForValue(event.index)

        // Skip if outside chart area
        if (x < left || x > right) return

        // Draw vertical dashed line
        ctx.save()
        ctx.beginPath()
        ctx.setLineDash([5, 5])
        ctx.strokeStyle = event.is_compute_intensive ? '#f59e0b' : '#3b82f6'
        ctx.lineWidth = 2
        ctx.moveTo(x, top)
        ctx.lineTo(x, bottom)
        ctx.stroke()

        // Draw event marker circle at top
        ctx.beginPath()
        ctx.setLineDash([])
        ctx.fillStyle = event.is_compute_intensive ? '#f59e0b' : '#3b82f6'
        ctx.arc(x, top + 10, 6, 0, Math.PI * 2)
        ctx.fill()

        // Draw calendar icon in circle
        ctx.fillStyle = '#fff'
        ctx.font = '8px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText('📅', x, top + 10)

        ctx.restore()
      })
    }
  }), [showCalendarEvents, calendarEvents, data])

  const getChartData = () => {
    if (!data?.daily_forecasts) return null

    const labels = data.daily_forecasts.map(d => {
      const date = new Date(d.date)
      return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    })

    const costs = data.daily_forecasts.map(d => d.forecasted_cost)
    const lowerBounds = data.daily_forecasts.map(d => d.confidence_interval?.[0] || d.forecasted_cost * 0.9)
    const upperBounds = data.daily_forecasts.map(d => d.confidence_interval?.[1] || d.forecasted_cost * 1.1)

    return {
      labels,
      datasets: [
        {
          label: 'Upper Bound',
          data: upperBounds,
          borderColor: 'transparent',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          fill: '+1',
          tension: 0.4,
          pointRadius: 0,
        },
        {
          label: 'Forecasted Cost',
          data: costs,
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34, 197, 94, 0.2)',
          fill: false,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#22c55e',
          borderWidth: 2,
        },
        {
          label: 'Lower Bound',
          data: lowerBounds,
          borderColor: 'transparent',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          fill: '-1',
          tension: 0.4,
          pointRadius: 0,
        },
      ]
    }
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#9ca3af',
          usePointStyle: true,
          boxWidth: 6,
          padding: 20,
          filter: (item) => item.text === 'Forecasted Cost'
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          afterTitle: (ctx) => {
            // Show calendar events for this day
            if (!showCalendarEvents) return null
            const eventIndices = getCalendarEventIndices()
            const dayEvents = eventIndices.filter(e => e.index === ctx[0]?.dataIndex)
            if (!dayEvents.length) return null
            return dayEvents.map(e => `📅 ${e.title}${e.is_compute_intensive ? ' (GPU)' : ''}`).join('\n')
          },
          label: (ctx) => {
            if (ctx.dataset.label === 'Forecasted Cost') {
              return `Cost: $${ctx.parsed.y.toFixed(2)}`
            }
            if (ctx.dataset.label === 'Upper Bound') {
              return `Upper: $${ctx.parsed.y.toFixed(2)}`
            }
            if (ctx.dataset.label === 'Lower Bound') {
              return `Lower: $${ctx.parsed.y.toFixed(2)}`
            }
            return null
          }
        }
      }
    },
    scales: {
      y: {
        ticks: {
          color: '#6b7280',
          font: { size: 10 },
          callback: (v) => `$${v.toFixed(0)}`
        },
        grid: { color: '#1f2937' }
      },
      x: {
        ticks: {
          color: '#6b7280',
          font: { size: 10 }
        },
        grid: { display: false }
      }
    }
  }

  const getSummaryStats = () => {
    if (!data?.daily_forecasts) return null

    const costs = data.daily_forecasts.map(d => d.forecasted_cost)
    const totalCost = costs.reduce((sum, c) => sum + c, 0)
    const minCost = Math.min(...costs)
    const maxCost = Math.max(...costs)
    const avgCost = totalCost / costs.length

    // Find best day (lowest cost)
    const bestDayIndex = costs.indexOf(minCost)
    const bestDay = data.daily_forecasts[bestDayIndex]
    const bestDayDate = new Date(bestDay?.date)

    return {
      totalCost,
      minCost,
      maxCost,
      avgCost,
      bestDay: bestDayDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    }
  }

  if (loading) {
    return (
      <div className="ta-card">
        <div className="ta-card-body flex items-center justify-center min-h-[300px]">
          <div className="ta-spinner" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="ta-card">
        <div className="ta-card-header flex justify-between items-center">
          <h3 className="ta-card-title flex items-center gap-2">
            <div className="stat-card-icon stat-card-icon-warning">
              <AlertCircle size={18} />
            </div>
            7-Day Cost Forecast
          </h3>
          <span className="gpu-badge">{selectedGPU}</span>
        </div>
        <div className="ta-card-body flex flex-col items-center justify-center min-h-[200px] text-center">
          <AlertCircle size={48} className="text-yellow-500 mb-4" />
          <p className="text-gray-400 mb-2">{error}</p>
          <p className="text-gray-500 text-sm">Need at least 50 hours of price history to generate forecast</p>
          <button
            onClick={loadData}
            className="mt-4 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const chartData = getChartData()
  const stats = getSummaryStats()

  return (
    <div className="ta-card hover-glow">
      <div className="ta-card-header flex justify-between items-center">
        <h3 className="ta-card-title flex items-center gap-2">
          <div className="stat-card-icon stat-card-icon-success pulse-dot">
            <Calendar size={18} />
          </div>
          7-Day Cost Forecast
        </h3>
        <span className="gpu-badge">{data?.gpu_name || selectedGPU}</span>
      </div>

      <div className="ta-card-body">
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '0ms' }}>
              <div className="stat-card-icon stat-card-icon-primary">
                <DollarSign size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Total 7 Days</span>
                <span className="text-lg font-bold text-blue-400">{formatPrice(stats.totalCost)}</span>
              </div>
            </div>
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '50ms' }}>
              <div className="stat-card-icon stat-card-icon-success">
                <TrendingDown size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Lowest Day</span>
                <span className="text-lg font-bold text-brand-400">{formatPrice(stats.minCost)}</span>
              </div>
            </div>
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '100ms' }}>
              <div className="stat-card-icon stat-card-icon-danger">
                <TrendingUp size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Highest Day</span>
                <span className="text-lg font-bold text-red-400">{formatPrice(stats.maxCost)}</span>
              </div>
            </div>
            <div className="stat-card flex items-center gap-2.5 p-3 animate-fade-in" style={{ animationDelay: '150ms' }}>
              <div className="stat-card-icon stat-card-icon-success">
                <Target size={16} />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 uppercase tracking-wide">Best Day</span>
                <span className="text-sm font-bold text-brand-400">{stats.bestDay}</span>
              </div>
            </div>
          </div>
        )}

        {chartData && (
          <div className="h-[220px] my-4 p-3 bg-white/[0.02] rounded-xl border border-white/5">
            <Line data={chartData} options={chartOptions} plugins={[calendarEventPlugin]} />
          </div>
        )}

        {/* Calendar Integration Section */}
        {calendarStatus && (
          <div className="mt-4 p-3 rounded-lg border border-white/10 bg-white/[0.02]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Calendar size={16} className={calendarStatus.connected ? 'text-brand-400' : 'text-gray-500'} />
                <span className="text-sm font-medium text-gray-300">Calendar Events</span>
                {calendarStatus.connected && calendarEvents.length > 0 && (
                  <span className="text-xs bg-brand-500/20 text-brand-400 px-2 py-0.5 rounded-full">
                    {calendarEvents.length} events
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {calendarStatus.connected && (
                  <button
                    onClick={() => setShowCalendarEvents(!showCalendarEvents)}
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      showCalendarEvents
                        ? 'bg-brand-500/20 text-brand-400'
                        : 'bg-gray-700 text-gray-400'
                    }`}
                  >
                    {showCalendarEvents ? 'Hide' : 'Show'}
                  </button>
                )}
                {calendarStatus.needs_reauthorization && (
                  <button
                    onClick={handleReconnectCalendar}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 rounded-lg transition-colors"
                  >
                    <RefreshCw size={12} />
                    Reconnect Calendar
                  </button>
                )}
                {!calendarStatus.connected && !calendarStatus.needs_reauthorization && calendarStatus.authorization_url && (
                  <button
                    onClick={handleReconnectCalendar}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-colors"
                  >
                    <Calendar size={12} />
                    Connect Calendar
                  </button>
                )}
              </div>
            </div>

            {calendarStatus.connected && calendarEvents.length > 0 && showCalendarEvents && (
              <div className="mt-3 space-y-2 max-h-[120px] overflow-y-auto">
                {calendarEvents.slice(0, 5).map((event, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center justify-between p-2 rounded-lg text-xs ${
                      event.is_compute_intensive
                        ? 'bg-amber-500/10 border border-amber-500/20'
                        : 'bg-blue-500/10 border border-blue-500/20'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={event.is_compute_intensive ? 'text-amber-400' : 'text-blue-400'}>
                        📅
                      </span>
                      <span className="text-gray-300 truncate max-w-[200px]">{event.title}</span>
                      {event.is_compute_intensive && (
                        <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded">GPU</span>
                      )}
                    </div>
                    <span className="text-gray-500">
                      {new Date(event.start_time).toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                ))}
                {calendarEvents.length > 5 && (
                  <p className="text-xs text-gray-500 text-center">
                    +{calendarEvents.length - 5} more events
                  </p>
                )}
              </div>
            )}

            {calendarStatus.connected && calendarEvents.length === 0 && (
              <p className="text-xs text-gray-500 mt-2">No scheduled events in the next 7 days</p>
            )}

            {!calendarStatus.connected && (
              <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                <Link2Off size={12} />
                <span>Connect your Google Calendar to see scheduled events on the forecast</span>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap justify-between items-center pt-3 border-t border-white/10 text-xs gap-2">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-500"></span>
            <span className="text-gray-400">Confidence:</span>
            <span className="text-brand-400 font-semibold">{formatPercent(data?.model_confidence)}</span>
          </span>
          <span className="flex items-center gap-2">
            <span className="text-gray-400">Usage:</span>
            <span className="text-gray-300">{data?.usage_hours_per_day || 8}h/day</span>
          </span>
          <span className="text-gray-500">
            Model: {data?.model_version || 'v1.0'}
          </span>
        </div>

        {data?.best_window && (
          <div className="mt-4 p-3 bg-brand-500/10 rounded-lg border border-brand-500/20">
            <div className="flex items-center gap-2 text-sm">
              <Target size={16} className="text-brand-400" />
              <span className="text-gray-300">
                <strong className="text-brand-400">Best Time Window:</strong>
                {' '}Start on {new Date(data.best_window.start_time).toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit'
                })} - Estimated savings: {formatPrice(data.best_window.potential_savings)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

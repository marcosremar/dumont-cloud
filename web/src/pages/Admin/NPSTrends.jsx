import React, { useEffect, useState, useMemo } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, useLocation } from 'react-router-dom'
import { Line, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js'
import {
  TrendingUp,
  Users,
  ThumbsDown,
  ThumbsUp,
  Meh,
  ArrowLeft,
  Calendar,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  MessageSquare,
  ChevronRight,
} from 'lucide-react'
import {
  fetchTrends,
  fetchDetractors,
  updateFollowup,
  selectNPSTrends,
  selectNPSTrendsLoading,
  selectNPSTrendsError,
  selectNPSDetractors,
  selectNPSDetractorsTotal,
  selectNPSDetractorsLoading,
  selectNPSDetractorsError,
} from '../../store/slices/npsSlice'
import { Button } from '../../components/ui/button'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
)

/**
 * NPSTrends Admin Dashboard - View NPS trends and manage detractor follow-ups
 */

// Date range options for filtering
const DATE_RANGE_OPTIONS = [
  { label: 'Last 7 days', value: '7d', days: 7 },
  { label: 'Last 30 days', value: '30d', days: 30 },
  { label: 'Last 90 days', value: '90d', days: 90 },
  { label: 'Last year', value: '1y', days: 365 },
  { label: 'All time', value: 'all', days: null },
]

/**
 * Get category color based on NPS category
 */
function getCategoryColor(category) {
  switch (category) {
    case 'promoter':
      return '#22c55e' // green-500
    case 'passive':
      return '#eab308' // yellow-500
    case 'detractor':
      return '#ef4444' // red-500
    default:
      return '#6b7280' // gray-500
  }
}

/**
 * Get category icon based on NPS category
 */
function getCategoryIcon(category) {
  switch (category) {
    case 'promoter':
      return ThumbsUp
    case 'passive':
      return Meh
    case 'detractor':
      return ThumbsDown
    default:
      return Users
  }
}

/**
 * Format date for display
 */
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

/**
 * Calculate NPS score from categories
 */
function calculateNPS(promoters, passives, detractors) {
  const total = promoters + passives + detractors
  if (total === 0) return 0
  return Math.round(((promoters - detractors) / total) * 100)
}

/**
 * Stat Card Component
 */
function StatCard({ icon: Icon, label, value, subValue, color, onClick }) {
  const CardWrapper = onClick ? 'button' : 'div'
  return (
    <CardWrapper
      onClick={onClick}
      className={`stat-card ${onClick ? 'group cursor-pointer' : ''}`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="stat-card-icon" style={{ backgroundColor: `${color}20`, color }}>
          <Icon className="w-5 h-5" />
        </div>
        {subValue && (
          <span className="text-xs text-gray-500">{subValue}</span>
        )}
      </div>
      <div className="stat-card-value mb-1" style={{ color }}>
        {value}
      </div>
      <div className="stat-card-label">{label}</div>
      {onClick && (
        <div className="flex items-center justify-end text-xs text-gray-500 pt-3 border-t border-white/5 mt-3">
          <span className="flex items-center gap-1 text-gray-400 group-hover:text-brand-500 transition-colors">
            View details <ChevronRight className="w-3 h-3" />
          </span>
        </div>
      )}
    </CardWrapper>
  )
}

/**
 * NPS Trend Chart Component
 */
function NPSTrendChart({ data, loading }) {
  if (loading || !data) {
    return (
      <div className="nps-chart-container skeleton" style={{ minHeight: '300px' }}>
        <div className="animate-pulse h-full bg-gray-800 rounded-lg" />
      </div>
    )
  }

  const scores = data.daily_scores || []

  const chartData = {
    labels: scores.map(s => formatDate(s.date)),
    datasets: [
      {
        label: 'NPS Score',
        data: scores.map(s => s.nps_score),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#3b82f6',
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#9ca3af', usePointStyle: true, boxWidth: 6, padding: 20 },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (ctx) => `NPS: ${ctx.parsed.y}`,
          afterLabel: (ctx) => {
            const score = scores[ctx.dataIndex]
            if (score) {
              return [
                `Promoters: ${score.promoters || 0}`,
                `Passives: ${score.passives || 0}`,
                `Detractors: ${score.detractors || 0}`,
              ]
            }
            return []
          },
        },
      },
    },
    scales: {
      y: {
        min: -100,
        max: 100,
        ticks: { color: '#6b7280', font: { size: 10 } },
        grid: { color: '#1f2937' },
      },
      x: {
        ticks: { color: '#6b7280', font: { size: 10 }, maxRotation: 45 },
        grid: { display: false },
      },
    },
  }

  return (
    <div className="nps-chart-container" style={{ height: '300px' }}>
      <Line data={chartData} options={chartOptions} />
    </div>
  )
}

/**
 * Category Breakdown Chart (Doughnut)
 */
function CategoryBreakdownChart({ data, loading }) {
  if (loading || !data) {
    return (
      <div className="breakdown-chart skeleton" style={{ minHeight: '200px' }}>
        <div className="animate-pulse h-full bg-gray-800 rounded-lg" />
      </div>
    )
  }

  const categories = data.categories || { promoters: 0, passives: 0, detractors: 0 }
  const total = categories.promoters + categories.passives + categories.detractors

  const chartData = {
    labels: ['Promoters (9-10)', 'Passives (7-8)', 'Detractors (0-6)'],
    datasets: [
      {
        data: [categories.promoters, categories.passives, categories.detractors],
        backgroundColor: ['#22c55e', '#eab308', '#ef4444'],
        borderColor: ['#16a34a', '#ca8a04', '#dc2626'],
        borderWidth: 1,
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#9ca3af', usePointStyle: true, boxWidth: 8, padding: 12 },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const value = ctx.raw
            const pct = total > 0 ? Math.round((value / total) * 100) : 0
            return `${ctx.label}: ${value} (${pct}%)`
          },
        },
      },
    },
  }

  return (
    <div className="breakdown-chart" style={{ height: '200px' }}>
      <Doughnut data={chartData} options={chartOptions} />
    </div>
  )
}

/**
 * Detractor List Item Component
 */
function DetractorItem({ response, onFollowUp }) {
  const [notes, setNotes] = useState(response.followup_notes || '')
  const [isEditing, setIsEditing] = useState(false)

  const handleSave = () => {
    onFollowUp(response.id, true, notes)
    setIsEditing(false)
  }

  return (
    <div className="detractor-item p-4 border border-gray-700 rounded-lg bg-gray-800/50 mb-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span
              className="inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold"
              style={{ backgroundColor: '#ef444420', color: '#ef4444' }}
            >
              {response.score}
            </span>
            <span className="text-sm text-gray-400">
              {response.user_email || 'Anonymous'}
            </span>
            <span className="text-xs text-gray-500">
              {formatDate(response.created_at)}
            </span>
            {response.followed_up && (
              <span className="inline-flex items-center gap-1 text-xs text-green-400 bg-green-900/30 px-2 py-0.5 rounded">
                <CheckCircle2 className="w-3 h-3" />
                Followed up
              </span>
            )}
          </div>

          {response.comment && (
            <div className="text-sm text-gray-300 mb-2 flex items-start gap-2">
              <MessageSquare className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
              <p className="break-words">{response.comment}</p>
            </div>
          )}

          {response.trigger_type && (
            <div className="text-xs text-gray-500">
              Trigger: {response.trigger_type}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          {!response.followed_up ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditing(!isEditing)}
              className="text-xs"
            >
              {isEditing ? 'Cancel' : 'Mark Follow-up'}
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsEditing(!isEditing)}
              className="text-xs text-gray-400"
            >
              {isEditing ? 'Cancel' : 'Edit Notes'}
            </Button>
          )}
        </div>
      </div>

      {isEditing && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <label className="block text-xs text-gray-400 mb-1">Follow-up Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes about the follow-up action taken..."
            className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
          />
          <div className="flex justify-end gap-2 mt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditing(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
            >
              Save & Mark Complete
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Main NPSTrends Component
 */
export default function NPSTrends() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'

  // Redux state
  const trends = useSelector(selectNPSTrends)
  const trendsLoading = useSelector(selectNPSTrendsLoading)
  const trendsError = useSelector(selectNPSTrendsError)
  const detractors = useSelector(selectNPSDetractors)
  const detractorsTotal = useSelector(selectNPSDetractorsTotal)
  const detractorsLoading = useSelector(selectNPSDetractorsLoading)
  const detractorsError = useSelector(selectNPSDetractorsError)

  // Local state
  const [dateRange, setDateRange] = useState('30d')
  const [showAllDetractors, setShowAllDetractors] = useState(false)

  // Calculate date range for API
  const dateParams = useMemo(() => {
    const option = DATE_RANGE_OPTIONS.find(o => o.value === dateRange)
    if (!option || !option.days) return {}

    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - option.days)

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    }
  }, [dateRange])

  // Fetch data on mount and when date range changes
  useEffect(() => {
    dispatch(fetchTrends(dateParams))
    dispatch(fetchDetractors({ pendingOnly: !showAllDetractors }))
  }, [dispatch, dateParams, showAllDetractors])

  // Handle refresh
  const handleRefresh = () => {
    dispatch(fetchTrends(dateParams))
    dispatch(fetchDetractors({ pendingOnly: !showAllDetractors }))
  }

  // Handle follow-up update
  const handleFollowUp = (responseId, followedUp, notes) => {
    dispatch(updateFollowup({ responseId, followedUp, followupNotes: notes }))
  }

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    if (!trends) {
      return {
        npsScore: 0,
        totalResponses: 0,
        promoters: 0,
        passives: 0,
        detractors: 0,
      }
    }

    const categories = trends.categories || { promoters: 0, passives: 0, detractors: 0 }
    const totalResponses = trends.total_responses || 0
    const npsScore = calculateNPS(
      categories.promoters,
      categories.passives,
      categories.detractors
    )

    return {
      npsScore,
      totalResponses,
      promoters: categories.promoters,
      passives: categories.passives,
      detractors: categories.detractors,
    }
  }, [trends])

  return (
    <div className="min-h-screen bg-[#0a0d0a] p-4 md:p-6 lg:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <button
          onClick={() => navigate(`${basePath}/metrics-hub`)}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to Metrics</span>
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3 text-2xl font-bold text-white">
              <div className="stat-card-icon stat-card-icon-primary p-2 rounded-lg bg-blue-500/10">
                <TrendingUp className="w-5 h-5 text-blue-500" />
              </div>
              NPS Dashboard
            </h1>
            <p className="page-subtitle text-gray-400 mt-1">
              Track user satisfaction and follow up with detractors
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Date Range Filter */}
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {DATE_RANGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Refresh Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={trendsLoading}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${trendsLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {(trendsError || detractorsError) && (
        <div className="max-w-7xl mx-auto mb-6">
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-400">
              {trendsError || detractorsError}
            </span>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard
            icon={TrendingUp}
            label="NPS Score"
            value={summaryStats.npsScore}
            subValue="Current"
            color="#3b82f6"
          />
          <StatCard
            icon={Users}
            label="Total Responses"
            value={summaryStats.totalResponses}
            subValue={dateRange === 'all' ? 'All time' : DATE_RANGE_OPTIONS.find(o => o.value === dateRange)?.label}
            color="#8b5cf6"
          />
          <StatCard
            icon={ThumbsUp}
            label="Promoters"
            value={summaryStats.promoters}
            subValue="Score 9-10"
            color="#22c55e"
          />
          <StatCard
            icon={Meh}
            label="Passives"
            value={summaryStats.passives}
            subValue="Score 7-8"
            color="#eab308"
          />
          <StatCard
            icon={ThumbsDown}
            label="Detractors"
            value={summaryStats.detractors}
            subValue="Score 0-6"
            color="#ef4444"
          />
        </div>
      </div>

      {/* Charts Section */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Trend Chart */}
          <div className="lg:col-span-2 bg-[#1c211c] border border-[#30363d] rounded-xl p-6">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              NPS Score Trend
            </h3>
            <NPSTrendChart data={trends} loading={trendsLoading} />
          </div>

          {/* Breakdown Chart */}
          <div className="bg-[#1c211c] border border-[#30363d] rounded-xl p-6">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
              <Users className="w-5 h-5 text-purple-500" />
              Response Breakdown
            </h3>
            <CategoryBreakdownChart data={trends} loading={trendsLoading} />

            {/* Legend with percentages */}
            {trends && trends.categories && (
              <div className="mt-4 space-y-2">
                {[
                  { key: 'promoters', label: 'Promoters', color: '#22c55e' },
                  { key: 'passives', label: 'Passives', color: '#eab308' },
                  { key: 'detractors', label: 'Detractors', color: '#ef4444' },
                ].map((cat) => {
                  const total = summaryStats.totalResponses || 1
                  const value = trends.categories[cat.key] || 0
                  const pct = Math.round((value / total) * 100)
                  return (
                    <div key={cat.key} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: cat.color }}
                        />
                        <span className="text-gray-400">{cat.label}</span>
                      </span>
                      <span className="text-gray-300">{pct}%</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detractor Follow-up Section */}
      <div className="max-w-7xl mx-auto">
        <div className="bg-[#1c211c] border border-[#30363d] rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
              <ThumbsDown className="w-5 h-5 text-red-500" />
              Detractor Follow-ups
              {detractorsTotal > 0 && (
                <span className="text-sm font-normal text-gray-400">
                  ({detractorsTotal} total)
                </span>
              )}
            </h3>

            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={showAllDetractors}
                onChange={(e) => setShowAllDetractors(e.target.checked)}
                className="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              Show completed
            </label>
          </div>

          {detractorsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="animate-pulse h-24 bg-gray-800 rounded-lg"
                />
              ))}
            </div>
          ) : detractors.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <ThumbsUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No detractor responses to follow up on</p>
              <p className="text-sm mt-1">
                {showAllDetractors
                  ? 'No detractor responses recorded yet'
                  : 'All detractors have been followed up'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {detractors.map((response) => (
                <DetractorItem
                  key={response.id}
                  response={response}
                  onFollowUp={handleFollowUp}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Inline Styles */}
      <style jsx>{`
        .skeleton {
          background: linear-gradient(90deg, #1c211c 25%, #2a352a 50%, #1c211c 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
        }

        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }

        .stat-card {
          background: #1c211c;
          border: 1px solid #30363d;
          border-radius: 12px;
          padding: 20px;
          transition: all 0.2s ease;
        }

        .stat-card:hover {
          border-color: #404040;
        }

        .stat-card-icon {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .stat-card-value {
          font-size: 28px;
          font-weight: 700;
          line-height: 1.2;
        }

        .stat-card-label {
          font-size: 14px;
          color: #9ca3af;
        }
      `}</style>
    </div>
  )
}

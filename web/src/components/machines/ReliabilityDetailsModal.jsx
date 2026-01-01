import { useState, useEffect, useMemo } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  Badge,
  Button,
  Progress,
} from '../tailadmin-ui'
import {
  X,
  Activity,
  Clock,
  AlertTriangle,
  TrendingUp,
  Star,
  Calendar,
  RefreshCw,
  Server,
  Zap,
  ThumbsUp,
  Info,
} from 'lucide-react'
import {
  submitMachineRating,
  selectRatingSubmitting,
  selectRatingError,
  clearRatingError,
} from '../../store/slices/instancesSlice'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function ReliabilityDetailsModal({ machine, isOpen, onClose, reliabilityData }) {
  const dispatch = useDispatch()
  const ratingSubmitting = useSelector(selectRatingSubmitting)
  const ratingError = useSelector(selectRatingError)

  const [activeTab, setActiveTab] = useState('overview')
  const [historyData, setHistoryData] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)
  const [userRating, setUserRating] = useState(0)
  const [hoverRating, setHoverRating] = useState(0)
  const [ratingComment, setRatingComment] = useState('')
  const [ratingSuccess, setRatingSuccess] = useState(false)

  // Get reliability score and metrics
  const reliability = reliabilityData || {}
  const overallScore = reliability.overall_score ?? reliability.reliability_score ?? null
  const uptimeScore = reliability.uptime_score ?? 0
  const priceStabilityScore = reliability.price_stability_score ?? 0
  const performanceScore = reliability.performance_score ?? 0
  const historyDays = reliability.history_days ?? 0
  const totalRentals = reliability.total_rentals ?? 0
  const recommendation = reliability.recommendation ?? 'unknown'
  const userRatingCount = reliability.user_rating_count ?? 0
  const userRatingAverage = reliability.user_rating_average ?? null

  // Fetch 30-day history when modal opens
  useEffect(() => {
    if (isOpen && machine?.id) {
      fetchHistory()
    }
    return () => {
      setHistoryData(null)
      setHistoryError(null)
      setRatingSuccess(false)
    }
  }, [isOpen, machine?.id])

  const fetchHistory = async () => {
    if (!machine?.id) return

    setHistoryLoading(true)
    setHistoryError(null)

    try {
      const token = localStorage.getItem('auth_token')
      const machineId = String(machine.id || machine.machine_id)
      const response = await fetch(
        `${API_BASE}/api/v1/reliability/machines/${machineId}/history?days=30`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        throw new Error('Failed to fetch history')
      }

      const data = await response.json()
      setHistoryData(data)
    } catch (err) {
      setHistoryError(err.message)
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleSubmitRating = async () => {
    if (userRating === 0 || !machine?.id) return

    dispatch(clearRatingError())
    const result = await dispatch(submitMachineRating({
      machineId: String(machine.id || machine.machine_id),
      rating: userRating,
      comment: ratingComment,
    }))

    if (!result.error) {
      setRatingSuccess(true)
      setTimeout(() => setRatingSuccess(false), 3000)
    }
  }

  // Get badge variant based on score
  const getScoreBadge = (score) => {
    if (score === null || score === undefined) {
      return { variant: 'gray', label: 'N/A', color: 'text-gray-400' }
    }
    const numScore = Number(score)
    if (numScore >= 80) {
      return { variant: 'success', label: 'Excelente', color: 'text-green-400' }
    } else if (numScore >= 60) {
      return { variant: 'warning', label: 'Bom', color: 'text-yellow-400' }
    } else {
      return { variant: 'error', label: 'Baixo', color: 'text-red-400' }
    }
  }

  const scoreBadge = getScoreBadge(overallScore)

  // Format uptime chart data
  const chartData = useMemo(() => {
    if (!historyData?.history) return []
    return historyData.history
      .slice()
      .reverse()
      .map(item => ({
        date: item.date,
        uptime: item.uptime_percentage || 0,
        interruptions: item.interruption_count || 0,
      }))
  }, [historyData])

  // Calculate chart max height for scaling
  const maxUptime = 100
  const chartHeight = 120

  if (!machine) return null

  const gpuName = machine.gpu_name || 'GPU'
  const machineId = machine.id || machine.machine_id || 'N/A'

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-2xl w-[90vw] max-h-[85vh] overflow-hidden flex flex-col">
        <AlertDialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <AlertDialogTitle className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-brand-400" />
              <span>Reliability Score</span>
              <span className="text-xs font-normal text-gray-500">#{machineId}</span>
            </AlertDialogTitle>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4 border-b border-gray-700">
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'overview'
                  ? 'text-green-400 border-green-400'
                  : 'text-gray-400 border-transparent hover:text-gray-300'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              Visão Geral
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'history'
                  ? 'text-green-400 border-green-400'
                  : 'text-gray-400 border-transparent hover:text-gray-300'
              }`}
            >
              <Calendar className="w-4 h-4" />
              Histórico 30 dias
            </button>
            <button
              onClick={() => setActiveTab('rate')}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === 'rate'
                  ? 'text-green-400 border-green-400'
                  : 'text-gray-400 border-transparent hover:text-gray-300'
              }`}
            >
              <Star className="w-4 h-4" />
              Avaliar
            </button>
          </div>
        </AlertDialogHeader>

        <div className="flex-1 overflow-y-auto mt-4">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6 p-1">
              {/* Main Score Card */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-brand-400" />
                    Score de Confiabilidade
                  </h3>
                  <Badge variant={scoreBadge.variant} className="text-xs">
                    {scoreBadge.label}
                  </Badge>
                </div>

                <div className="flex items-center gap-6">
                  <div className="relative w-24 h-24">
                    {/* Circular Progress Indicator */}
                    <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
                      <circle
                        className="text-gray-700"
                        strokeWidth="8"
                        stroke="currentColor"
                        fill="transparent"
                        r="42"
                        cx="50"
                        cy="50"
                      />
                      <circle
                        className={scoreBadge.color}
                        strokeWidth="8"
                        strokeDasharray={`${(overallScore ?? 0) * 2.64} 264`}
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="transparent"
                        r="42"
                        cx="50"
                        cy="50"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className={`text-2xl font-bold ${scoreBadge.color}`}>
                        {overallScore !== null ? Math.round(overallScore) : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="flex-1 space-y-3">
                    <div className="text-sm text-gray-400">
                      {gpuName}
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-gray-500">Histórico</span>
                        <p className="text-white font-medium">{historyDays} dias</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Aluguéis</span>
                        <p className="text-white font-medium">{totalRentals}</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Avaliações</span>
                        <p className="text-white font-medium">{userRatingCount}</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Média</span>
                        <p className="text-white font-medium flex items-center gap-1">
                          {userRatingAverage ? (
                            <>
                              <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                              {userRatingAverage.toFixed(1)}
                            </>
                          ) : (
                            'N/A'
                          )}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Score Breakdown */}
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  Breakdown de Métricas
                </h3>
                <div className="space-y-4">
                  {/* Uptime Score */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-green-400" />
                        <span className="text-sm text-gray-300">Uptime</span>
                      </div>
                      <span className="text-sm font-medium text-white">{uptimeScore.toFixed(1)}%</span>
                    </div>
                    <Progress value={uptimeScore} max={100} variant="success" size="sm" />
                    <p className="text-xs text-gray-500 mt-1">Percentual de tempo online nos últimos 30 dias</p>
                  </div>

                  {/* Price Stability */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-blue-400" />
                        <span className="text-sm text-gray-300">Estabilidade</span>
                      </div>
                      <span className="text-sm font-medium text-white">{priceStabilityScore.toFixed(1)}%</span>
                    </div>
                    <Progress value={priceStabilityScore} max={100} variant="primary" size="sm" />
                    <p className="text-xs text-gray-500 mt-1">Consistência de disponibilidade e preço</p>
                  </div>

                  {/* Performance Score */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-purple-400" />
                        <span className="text-sm text-gray-300">Performance</span>
                      </div>
                      <span className="text-sm font-medium text-white">{performanceScore.toFixed(1)}%</span>
                    </div>
                    <Progress value={performanceScore} max={100} variant="primary" size="sm" />
                    <p className="text-xs text-gray-500 mt-1">Tempo médio para ficar operacional</p>
                  </div>

                  {/* User Rating Score (if available) */}
                  {userRatingAverage && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Star className="w-4 h-4 text-yellow-400" />
                          <span className="text-sm text-gray-300">Avaliação de Usuários</span>
                        </div>
                        <span className="text-sm font-medium text-white">
                          {userRatingAverage.toFixed(1)}/5
                        </span>
                      </div>
                      <Progress value={(userRatingAverage / 5) * 100} max={100} variant="warning" size="sm" />
                      <p className="text-xs text-gray-500 mt-1">Baseado em {userRatingCount} avaliações</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Recommendation */}
              <div className={`p-4 rounded-xl border ${
                recommendation === 'excellent' ? 'bg-green-500/10 border-green-500/30' :
                recommendation === 'good' ? 'bg-blue-500/10 border-blue-500/30' :
                recommendation === 'fair' ? 'bg-yellow-500/10 border-yellow-500/30' :
                'bg-red-500/10 border-red-500/30'
              }`}>
                <div className="flex items-center gap-3">
                  <ThumbsUp className={`w-5 h-5 ${
                    recommendation === 'excellent' ? 'text-green-400' :
                    recommendation === 'good' ? 'text-blue-400' :
                    recommendation === 'fair' ? 'text-yellow-400' :
                    'text-red-400'
                  }`} />
                  <div>
                    <p className="text-sm font-medium text-white">
                      {recommendation === 'excellent' ? 'Altamente Recomendado' :
                       recommendation === 'good' ? 'Recomendado' :
                       recommendation === 'fair' ? 'Aceitável' :
                       'Não Recomendado'}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {recommendation === 'excellent' ? 'Esta máquina tem histórico excelente de confiabilidade.' :
                       recommendation === 'good' ? 'Bom histórico com raras interrupções.' :
                       recommendation === 'fair' ? 'Algum histórico de instabilidade. Use com cautela.' :
                       'Histórico problemático. Considere outras opções.'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div className="space-y-6 p-1">
              {historyLoading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="w-6 h-6 text-brand-400 animate-spin" />
                  <span className="ml-3 text-gray-400">Carregando histórico...</span>
                </div>
              ) : historyError ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <AlertTriangle className="w-8 h-8 mb-3 text-yellow-400" />
                  <p className="mb-3">Erro ao carregar histórico</p>
                  <Button variant="outline" size="sm" onClick={fetchHistory}>
                    Tentar novamente
                  </Button>
                </div>
              ) : historyData ? (
                <>
                  {/* 30-Day Uptime Chart */}
                  <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-brand-400" />
                        Uptime - Últimos 30 Dias
                      </h3>
                      <span className="text-xs text-gray-500">
                        {historyData.total_records} dias de dados
                      </span>
                    </div>

                    {/* Simple Bar Chart */}
                    <div className="relative" style={{ height: chartHeight + 40 }}>
                      {/* Y-axis labels */}
                      <div className="absolute left-0 top-0 bottom-8 flex flex-col justify-between text-xs text-gray-500 w-8">
                        <span>100%</span>
                        <span>50%</span>
                        <span>0%</span>
                      </div>

                      {/* Chart area */}
                      <div className="ml-10 relative" style={{ height: chartHeight }}>
                        <div className="flex items-end justify-between h-full gap-0.5">
                          {chartData.map((day, idx) => {
                            const barHeight = (day.uptime / maxUptime) * chartHeight
                            const barColor = day.uptime >= 95 ? 'bg-green-500' :
                                            day.uptime >= 80 ? 'bg-yellow-500' :
                                            day.uptime >= 50 ? 'bg-orange-500' : 'bg-red-500'
                            return (
                              <div
                                key={idx}
                                className="flex-1 flex flex-col items-center group"
                                title={`${day.date}: ${day.uptime.toFixed(1)}% uptime, ${day.interruptions} interrupções`}
                              >
                                <div
                                  className={`w-full max-w-3 rounded-t ${barColor} transition-all hover:opacity-80`}
                                  style={{ height: Math.max(2, barHeight) }}
                                />
                                {/* Tooltip on hover */}
                                <div className="hidden group-hover:block absolute bottom-full mb-2 px-2 py-1 bg-gray-900 text-xs text-white rounded shadow-lg whitespace-nowrap z-10">
                                  {day.date}: {day.uptime.toFixed(1)}%
                                  {day.interruptions > 0 && ` (${day.interruptions} int.)`}
                                </div>
                              </div>
                            )
                          })}
                        </div>

                        {/* Grid lines */}
                        <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                          <div className="border-t border-gray-700/50" />
                          <div className="border-t border-gray-700/50" />
                          <div className="border-t border-gray-700/50" />
                        </div>
                      </div>

                      {/* X-axis labels */}
                      <div className="ml-10 flex justify-between mt-2 text-xs text-gray-500">
                        <span>30 dias atrás</span>
                        <span>Hoje</span>
                      </div>
                    </div>

                    {/* Legend */}
                    <div className="flex items-center gap-4 mt-4 text-xs text-gray-400">
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded bg-green-500" />
                        <span>≥95%</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded bg-yellow-500" />
                        <span>80-95%</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded bg-orange-500" />
                        <span>50-80%</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded bg-red-500" />
                        <span>&lt;50%</span>
                      </div>
                    </div>
                  </div>

                  {/* Summary Stats */}
                  {historyData.summary && (
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                        <Info className="w-4 h-4 text-blue-400" />
                        Resumo do Período
                      </h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center p-3 rounded-lg bg-white/5">
                          <div className="text-lg font-bold text-green-400">
                            {historyData.summary.avg_uptime_percentage?.toFixed(1) ?? 'N/A'}%
                          </div>
                          <div className="text-xs text-gray-500">Uptime Médio</div>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-white/5">
                          <div className="text-lg font-bold text-white">
                            {historyData.summary.min_uptime_percentage?.toFixed(1) ?? 'N/A'}%
                          </div>
                          <div className="text-xs text-gray-500">Uptime Mínimo</div>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-white/5">
                          <div className="text-lg font-bold text-white">
                            {historyData.summary.max_uptime_percentage?.toFixed(1) ?? 'N/A'}%
                          </div>
                          <div className="text-xs text-gray-500">Uptime Máximo</div>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-white/5">
                          <div className="text-lg font-bold text-yellow-400">
                            {historyData.summary.total_interruptions ?? 0}
                          </div>
                          <div className="text-xs text-gray-500">Interrupções</div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <Calendar className="w-8 h-8 mb-3 opacity-30" />
                  <p>Nenhum histórico disponível</p>
                </div>
              )}
            </div>
          )}

          {/* Rate Tab */}
          {activeTab === 'rate' && (
            <div className="space-y-6 p-1">
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h3 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
                  <Star className="w-4 h-4 text-yellow-400" />
                  Avalie esta Máquina
                </h3>

                <p className="text-sm text-gray-400 mb-4">
                  Se você já usou esta máquina, sua avaliação ajuda outros usuários a tomarem melhores decisões.
                </p>

                {/* Star Rating */}
                <div className="flex items-center justify-center gap-2 mb-6">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setUserRating(star)}
                      onMouseEnter={() => setHoverRating(star)}
                      onMouseLeave={() => setHoverRating(0)}
                      className="p-1 transition-transform hover:scale-110 focus:outline-none"
                    >
                      <Star
                        className={`w-10 h-10 transition-colors ${
                          star <= (hoverRating || userRating)
                            ? 'text-yellow-400 fill-yellow-400'
                            : 'text-gray-600'
                        }`}
                      />
                    </button>
                  ))}
                </div>

                {/* Rating Labels */}
                <div className="text-center mb-6">
                  {userRating === 0 && <span className="text-gray-500">Clique para avaliar</span>}
                  {userRating === 1 && <span className="text-red-400">Muito ruim</span>}
                  {userRating === 2 && <span className="text-orange-400">Ruim</span>}
                  {userRating === 3 && <span className="text-yellow-400">Regular</span>}
                  {userRating === 4 && <span className="text-green-400">Bom</span>}
                  {userRating === 5 && <span className="text-green-400">Excelente</span>}
                </div>

                {/* Comment Input */}
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-2">
                    Comentário (opcional)
                  </label>
                  <textarea
                    value={ratingComment}
                    onChange={(e) => setRatingComment(e.target.value)}
                    placeholder="Conte sua experiência com esta máquina..."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-brand-500/50 placeholder-gray-500 resize-none"
                    rows={3}
                  />
                </div>

                {/* Submit Button */}
                <Button
                  variant="primary"
                  onClick={handleSubmitRating}
                  disabled={userRating === 0 || ratingSubmitting}
                  loading={ratingSubmitting}
                  className="w-full"
                >
                  {ratingSubmitting ? 'Enviando...' : 'Enviar Avaliação'}
                </Button>

                {/* Success Message */}
                {ratingSuccess && (
                  <div className="mt-4 p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-center">
                    <p className="text-sm text-green-400">
                      ✓ Avaliação enviada com sucesso!
                    </p>
                  </div>
                )}

                {/* Error Message */}
                {ratingError && (
                  <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-center">
                    <p className="text-sm text-red-400">
                      Erro ao enviar avaliação: {ratingError}
                    </p>
                  </div>
                )}
              </div>

              {/* Current Rating Info */}
              {userRatingCount > 0 && (
                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                  <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <Info className="w-4 h-4 text-blue-400" />
                    Avaliações da Comunidade
                  </h3>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star
                          key={star}
                          className={`w-5 h-5 ${
                            star <= Math.round(userRatingAverage || 0)
                              ? 'text-yellow-400 fill-yellow-400'
                              : 'text-gray-600'
                          }`}
                        />
                      ))}
                    </div>
                    <span className="text-white font-medium">
                      {userRatingAverage?.toFixed(1) ?? 'N/A'}
                    </span>
                    <span className="text-gray-500 text-sm">
                      ({userRatingCount} avaliações)
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}

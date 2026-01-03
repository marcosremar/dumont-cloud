import { useState, useEffect, useRef, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { PageHeader, StatCard, Card, Badge, Progress, EmptyState, StatsGrid } from '../tailadmin-ui/index'
import { Button } from '../ui/button'
import { DollarSign, TrendingUp, TrendingDown, PiggyBank, Zap, Clock, Server, RefreshCw, BarChart3, ArrowUpRight, Calculator, CheckCircle, Sparkles, Activity, Play, Pause } from 'lucide-react'
import {
    fetchSavings,
    fetchRealtimeSavings,
    fetchActiveSession,
    setProvider,
    startPolling,
    stopPolling,
    selectLifetimeSavings,
    selectCurrentSessionSavings,
    selectHourlyComparison,
    selectProjections,
    selectSelectedProvider,
    selectAvailableProviders,
    selectActiveSession,
    selectEconomyLoading,
    selectRealtimeLoading,
    selectEconomyError,
    selectIsPolling,
    selectPollingInterval,
    selectHasActiveInstances,
} from '../../store/slices/economySlice'

const API_BASE = ''

// Demo data fallback when API is unavailable
const DEMO_DATA = {
    summary: {
        total_cost_dumont: 247.50,
        total_cost_aws: 892.30,
        total_cost_gcp: 756.80,
        total_cost_azure: 823.40,
        savings_vs_aws: 644.80,
        savings_vs_gcp: 509.30,
        savings_vs_azure: 575.90,
        savings_percentage_avg: 72,
        total_gpu_hours: 186,
        machines_used: 4,
        auto_hibernate_savings: 89.50,
    },
    history: {
        months: ['Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
        dumont: [180, 210, 195, 230, 220, 247],
        aws: [650, 720, 680, 780, 750, 892],
        gcp: [550, 610, 580, 660, 640, 756],
    },
    breakdown: [
        { name: 'RTX 4090 - Training', hours: 72, cost_dumont: 108.00, cost_aws: 432.00, savings: 324.00 },
        { name: 'A100 80GB - LLM', hours: 48, cost_dumont: 86.40, cost_aws: 288.00, savings: 201.60 },
        { name: 'RTX 3090 - Inference', hours: 42, cost_dumont: 33.60, cost_aws: 126.00, savings: 92.40 },
        { name: 'RTX 4080 - Development', hours: 24, cost_dumont: 19.50, cost_aws: 46.30, savings: 26.80 },
    ]
}

// Provider pricing multipliers for demo mode
const PROVIDER_MULTIPLIERS = {
    AWS: 1.0,
    GCP: 0.85,
    Azure: 0.92,
}

export default function SavingsDashboard({ getAuthHeaders }) {
    const dispatch = useDispatch()

    // Redux selectors
    const lifetimeSavings = useSelector(selectLifetimeSavings)
    const currentSessionSavings = useSelector(selectCurrentSessionSavings)
    const hourlyComparison = useSelector(selectHourlyComparison)
    const projections = useSelector(selectProjections)
    const selectedProvider = useSelector(selectSelectedProvider)
    const availableProviders = useSelector(selectAvailableProviders)
    const activeSession = useSelector(selectActiveSession)
    const loading = useSelector(selectEconomyLoading)
    const realtimeLoading = useSelector(selectRealtimeLoading)
    const error = useSelector(selectEconomyError)
    const isPolling = useSelector(selectIsPolling)
    const pollingInterval = useSelector(selectPollingInterval)
    const hasActiveInstances = useSelector(selectHasActiveInstances)

    // Local state
    const [period, setPeriod] = useState('month')
    const [data, setData] = useState(null)
    const [useDemo, setUseDemo] = useState(false)
    const [localLoading, setLocalLoading] = useState(true)
    const [liveCounter, setLiveCounter] = useState(0)
    const [sessionStartTime, setSessionStartTime] = useState(null)

    // Refs for polling cleanup
    const pollIntervalRef = useRef(null)
    const liveCounterRef = useRef(null)

    const periods = [
        { id: 'day', label: 'Hoje' },
        { id: 'week', label: '7 dias' },
        { id: 'month', label: '30 dias' },
        { id: 'year', label: '1 ano' }
    ]

    // Load initial data and setup polling
    useEffect(() => {
        loadAllData()
        dispatch(fetchSavings(selectedProvider))
        dispatch(fetchActiveSession(selectedProvider))

        // Start polling for real-time updates
        startRealtimePolling()

        return () => {
            stopRealtimePolling()
        }
    }, [period, selectedProvider])

    // Live counter effect - updates every second when there are active instances
    useEffect(() => {
        if (hasActiveInstances && hourlyComparison.savingsPerHour > 0) {
            if (!sessionStartTime) {
                setSessionStartTime(Date.now())
            }

            liveCounterRef.current = setInterval(() => {
                const elapsedSeconds = (Date.now() - (sessionStartTime || Date.now())) / 1000
                const savingsPerSecond = hourlyComparison.savingsPerHour / 3600
                setLiveCounter(currentSessionSavings + (savingsPerSecond * elapsedSeconds))
            }, 100) // Update every 100ms for smooth animation

            return () => {
                if (liveCounterRef.current) {
                    clearInterval(liveCounterRef.current)
                }
            }
        } else {
            setLiveCounter(currentSessionSavings)
            setSessionStartTime(null)
        }
    }, [hasActiveInstances, hourlyComparison.savingsPerHour, currentSessionSavings, sessionStartTime])

    const startRealtimePolling = useCallback(() => {
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
        }

        dispatch(startPolling())

        // Poll every 30 seconds for real-time updates
        pollIntervalRef.current = setInterval(() => {
            dispatch(fetchRealtimeSavings(selectedProvider))
            dispatch(fetchActiveSession(selectedProvider))
        }, pollingInterval)
    }, [dispatch, selectedProvider, pollingInterval])

    const stopRealtimePolling = useCallback(() => {
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
        }
        dispatch(stopPolling())
    }, [dispatch])

    const handleProviderChange = (provider) => {
        dispatch(setProvider(provider))
    }

    const togglePolling = () => {
        if (isPolling) {
            stopRealtimePolling()
        } else {
            startRealtimePolling()
        }
    }

    const loadAllData = async () => {
        setLocalLoading(true)
        try {
            const headers = getAuthHeaders ? getAuthHeaders() : {}

            const summaryRes = await fetch(`${API_BASE}/api/v1/savings/summary?period=${period}`, {
                headers,
                credentials: 'include'
            })

            if (!summaryRes.ok) {
                throw new Error('Erro ao carregar dados do dashboard')
            }

            const summaryData = await summaryRes.json()
            setData({
                summary: summaryData,
                history: DEMO_DATA.history,
                breakdown: DEMO_DATA.breakdown
            })
            setUseDemo(false)
        } catch (err) {
            // Use demo data on error
            setData({
                summary: DEMO_DATA.summary,
                history: DEMO_DATA.history,
                breakdown: DEMO_DATA.breakdown
            })
            setUseDemo(true)
        } finally {
            setLocalLoading(false)
        }
    }

    // Compute summary based on selected provider
    const getSummaryForProvider = () => {
        const baseSummary = data?.summary || DEMO_DATA.summary
        const multiplier = PROVIDER_MULTIPLIERS[selectedProvider] || 1.0

        return {
            ...baseSummary,
            total_cost_provider: baseSummary.total_cost_aws * multiplier,
            savings_vs_provider: (baseSummary.total_cost_aws * multiplier) - baseSummary.total_cost_dumont,
        }
    }

    const summary = getSummaryForProvider()

    // Format duration from seconds
    const formatDuration = (seconds) => {
        if (!seconds) return '0m'
        const hours = Math.floor(seconds / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)
        if (hours > 0) {
            return `${hours}h ${minutes}m`
        }
        return `${minutes}m`
    }

    return (
        <div className="p-4 md:p-6 lg:p-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <nav className="flex items-center gap-2 text-sm text-gray-500 mb-3">
                        <a href="/app" className="hover:text-brand-400 transition-colors">Home</a>
                        <span className="text-gray-600">/</span>
                        <span className="text-white font-medium">Economia</span>
                    </nav>
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
                                <div className="stat-card-icon stat-card-icon-success">
                                    <PiggyBank size={24} />
                                </div>
                                Dashboard de Economia
                            </h1>
                            <p className="text-gray-400 mt-1">Compare seus custos reais com grandes cloud providers</p>
                        </div>
                        <div className="flex items-center gap-3">
                            {/* Provider Toggle */}
                            <div className="ta-tabs">
                                {availableProviders.map(provider => (
                                    <button
                                        key={provider}
                                        className={`ta-tab ${selectedProvider === provider ? 'ta-tab-active' : ''}`}
                                        onClick={() => handleProviderChange(provider)}
                                    >
                                        {provider}
                                    </button>
                                ))}
                            </div>

                            {/* Period Tabs */}
                            <div className="ta-tabs">
                                {periods.map(p => (
                                    <button
                                        key={p.id}
                                        className={`ta-tab ${period === p.id ? 'ta-tab-active' : ''}`}
                                        onClick={() => setPeriod(p.id)}
                                    >
                                        {p.label}
                                    </button>
                                ))}
                            </div>

                            {/* Polling Toggle */}
                            <button
                                onClick={togglePolling}
                                className={`ta-btn ta-btn-sm ${isPolling ? 'ta-btn-success' : 'ta-btn-outline'}`}
                                title={isPolling ? 'Atualização automática ativa' : 'Atualização automática pausada'}
                            >
                                {isPolling ? <Play size={14} /> : <Pause size={14} />}
                                {isPolling ? 'Live' : 'Pausado'}
                            </button>

                            <button
                                onClick={loadAllData}
                                disabled={localLoading}
                                className="ta-btn ta-btn-outline ta-btn-sm"
                            >
                                <RefreshCw size={16} className={localLoading ? 'animate-spin' : ''} />
                                {localLoading ? 'Atualizando...' : 'Atualizar'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Demo Mode Alert */}
                {useDemo && (
                    <div className="ta-alert ta-alert-info mb-6 animate-fade-in">
                        <BarChart3 size={20} />
                        <div>
                            <p className="font-medium">Modo Demonstração</p>
                            <p className="text-sm opacity-80">Os dados exibidos são simulados para fins de demonstração.</p>
                        </div>
                    </div>
                )}

                {/* Live Session Tracking Card */}
                {hasActiveInstances && (
                    <div className="mb-6 animate-fade-in">
                        <div className="ta-card hover-glow border-brand-500/30 bg-gradient-to-r from-brand-500/5 to-transparent">
                            <div className="ta-card-body">
                                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                                    <div className="flex items-center gap-4">
                                        <div className="relative">
                                            <div className="w-12 h-12 rounded-full bg-brand-500/20 flex items-center justify-center">
                                                <Activity size={24} className="text-brand-400" />
                                            </div>
                                            <span className="absolute -top-1 -right-1 w-4 h-4 bg-brand-500 rounded-full animate-pulse" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-gray-400">Sessão Ativa</p>
                                            <p className="text-2xl font-bold text-white">
                                                {activeSession.activeInstances} {activeSession.activeInstances === 1 ? 'instância' : 'instâncias'}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Real-time Savings Counter */}
                                    <div className="text-center md:text-right">
                                        <p className="text-xs text-brand-300/70 uppercase tracking-wide mb-1">Economia em Tempo Real</p>
                                        <div className="flex items-baseline gap-2">
                                            <span className="text-3xl md:text-4xl font-extrabold text-brand-400 tabular-nums">
                                                ${liveCounter.toFixed(4)}
                                            </span>
                                            <span className="text-sm text-brand-300/60">vs {selectedProvider}</span>
                                        </div>
                                        <p className="text-xs text-gray-500 mt-1">
                                            +${hourlyComparison.savingsPerHour.toFixed(2)}/hora | Duração: {formatDuration(activeSession.sessionDuration)}
                                        </p>
                                    </div>

                                    {/* Session Stats */}
                                    <div className="flex gap-6">
                                        <div className="text-center">
                                            <p className="text-lg font-bold text-white">${activeSession.currentCostDumont.toFixed(2)}</p>
                                            <p className="text-xs text-gray-500">Custo Dumont</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-lg font-bold text-orange-400">${activeSession.currentCostProvider.toFixed(2)}</p>
                                            <p className="text-xs text-gray-500">Custo {selectedProvider}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* No Active Instances Message */}
                {!hasActiveInstances && (
                    <div className="mb-6 animate-fade-in">
                        <div className="ta-card border-gray-700/50 bg-gray-800/30">
                            <div className="ta-card-body">
                                <div className="flex items-center gap-4 text-gray-400">
                                    <Activity size={24} className="opacity-50" />
                                    <div>
                                        <p className="font-medium text-gray-300">Nenhuma instância ativa</p>
                                        <p className="text-sm">Inicie uma instância GPU para ver economia em tempo real</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Big Savings Highlight */}
                <div className="spot-highlight mb-8 animate-fade-in">
                    <div className="flex flex-col md:flex-row items-center justify-center gap-6 relative z-10">
                        <div className="flex items-center gap-4">
                            <Sparkles size={40} className="text-brand-400" />
                            <div className="text-center md:text-left">
                                <span className="block text-xs text-brand-300/70 uppercase font-semibold tracking-wide">Economia Total vs {selectedProvider}</span>
                                <span className="block text-4xl md:text-5xl font-extrabold text-white">${summary.savings_vs_provider?.toFixed(2) || summary.savings_vs_aws.toFixed(2)}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 px-6 py-3 bg-white/10 rounded-xl">
                            <CheckCircle size={24} className="text-brand-400" />
                            <div>
                                <span className="block text-2xl font-bold text-brand-300">{summary.savings_percentage_avg}%</span>
                                <span className="block text-xs text-brand-200/60">mais barato que {selectedProvider}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    <div className="stat-card animate-fade-in" style={{ animationDelay: '0ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Você Pagou</p>
                                <p className="text-2xl font-bold text-brand-400">${summary.total_cost_dumont.toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Este mês na Dumont Cloud</p>
                            </div>
                            <div className="stat-card-icon stat-card-icon-success">
                                <DollarSign size={20} />
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <span className="text-xs text-brand-400 font-medium flex items-center gap-1">
                                <TrendingDown size={12} />
                                -{summary.savings_percentage_avg}% vs {selectedProvider}
                            </span>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '50ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">{selectedProvider} Pagaria</p>
                                <p className="text-2xl font-bold text-orange-400">${(summary.total_cost_provider || summary.total_cost_aws).toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Mesmo workload na {selectedProvider}</p>
                            </div>
                            <div className="stat-card-icon bg-orange-500/10 text-orange-400">
                                <Server size={20} />
                            </div>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '100ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Projeção Mensal</p>
                                <p className="text-2xl font-bold text-blue-400">${(projections.monthly || (summary.savings_vs_provider * 1.2)).toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Economia projetada</p>
                            </div>
                            <div className="stat-card-icon bg-blue-500/10 text-blue-400">
                                <TrendingUp size={20} />
                            </div>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '150ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Auto-Hibernate</p>
                                <p className="text-2xl font-bold text-yellow-400">${(summary.auto_hibernate_savings || 0).toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">Economia por hibernação</p>
                            </div>
                            <div className="stat-card-icon stat-card-icon-warning">
                                <Zap size={20} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Comparison Chart - Large */}
                    <div className="ta-card hover-glow lg:col-span-2">
                        <div className="ta-card-header">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="stat-card-icon bg-purple-500/10 text-purple-400">
                                        <BarChart3 size={18} />
                                    </div>
                                    <div>
                                        <h3 className="ta-card-title">Comparativo de Custos</h3>
                                        <p className="text-sm text-gray-400">Dumont Cloud vs {selectedProvider}</p>
                                    </div>
                                </div>
                                <span className="ta-badge ta-badge-success">{summary.savings_percentage_avg}% mais barato</span>
                            </div>
                        </div>
                        <div className="ta-card-body">
                            {/* Visual Comparison Bars */}
                            <div className="space-y-5">
                                {/* Dumont */}
                                <div className="animate-fade-in" style={{ animationDelay: '0ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-brand-500 shadow-lg shadow-brand-500/30"></div>
                                            <span className="text-sm font-medium text-white">Dumont Cloud</span>
                                            <span className="ta-badge ta-badge-success text-[10px]">Você</span>
                                        </div>
                                        <span className="text-sm font-bold text-brand-400">${summary.total_cost_dumont.toFixed(2)}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: `${(summary.total_cost_dumont / (summary.total_cost_provider || summary.total_cost_aws)) * 100}%` }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">{Math.round((summary.total_cost_dumont / (summary.total_cost_provider || summary.total_cost_aws)) * 100)}%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Selected Provider */}
                                <div className="animate-fade-in" style={{ animationDelay: '100ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-orange-500 shadow-lg shadow-orange-500/30"></div>
                                            <span className="text-sm font-medium text-white">{selectedProvider}</span>
                                        </div>
                                        <span className="text-sm font-bold text-orange-400">${(summary.total_cost_provider || summary.total_cost_aws).toFixed(2)}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-orange-600 to-orange-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: '100%' }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">100%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Savings Summary Card */}
                    <div className="ta-card hover-glow">
                        <div className="ta-card-header">
                            <h3 className="ta-card-title flex items-center gap-2">
                                <div className="stat-card-icon stat-card-icon-success">
                                    <TrendingUp size={18} />
                                </div>
                                Resumo de Economia
                            </h3>
                        </div>
                        <div className="ta-card-body">
                            <div className="text-center py-4 mb-4 bg-gradient-to-br from-brand-500/10 to-brand-500/5 rounded-xl border border-brand-500/20">
                                <div className="text-5xl font-extrabold text-brand-400 mb-1">
                                    {summary.savings_percentage_avg}%
                                </div>
                                <p className="text-sm text-brand-300/70">de economia média</p>
                            </div>

                            <div className="space-y-3 mb-4">
                                <div className={`flex justify-between items-center p-3 rounded-lg transition-colors ${selectedProvider === 'AWS' ? 'bg-brand-500/10 border border-brand-500/20' : 'bg-white/[0.03] hover:bg-white/[0.05]'}`}>
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                                        <span className="text-sm text-gray-400">vs AWS</span>
                                    </div>
                                    <span className="text-sm font-bold text-brand-400">
                                        +${summary.savings_vs_aws.toFixed(2)}
                                    </span>
                                </div>
                                <div className={`flex justify-between items-center p-3 rounded-lg transition-colors ${selectedProvider === 'GCP' ? 'bg-brand-500/10 border border-brand-500/20' : 'bg-white/[0.03] hover:bg-white/[0.05]'}`}>
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                                        <span className="text-sm text-gray-400">vs GCP</span>
                                    </div>
                                    <span className="text-sm font-bold text-brand-400">
                                        +${(summary.savings_vs_gcp || 509.30).toFixed(2)}
                                    </span>
                                </div>
                                <div className={`flex justify-between items-center p-3 rounded-lg transition-colors ${selectedProvider === 'Azure' ? 'bg-brand-500/10 border border-brand-500/20' : 'bg-white/[0.03] hover:bg-white/[0.05]'}`}>
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-sky-500"></div>
                                        <span className="text-sm text-gray-400">vs Azure</span>
                                    </div>
                                    <span className="text-sm font-bold text-brand-400">
                                        +${(summary.savings_vs_azure || 575.90).toFixed(2)}
                                    </span>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-white/10 grid grid-cols-2 gap-3">
                                <div className="text-center p-3 bg-white/[0.02] rounded-lg">
                                    <Clock size={18} className="mx-auto text-blue-400 mb-1" />
                                    <span className="block text-lg font-bold text-white">{summary.total_gpu_hours}h</span>
                                    <span className="block text-[10px] text-gray-500 uppercase">GPU Hours</span>
                                </div>
                                <div className="text-center p-3 bg-white/[0.02] rounded-lg">
                                    <Server size={18} className="mx-auto text-purple-400 mb-1" />
                                    <span className="block text-lg font-bold text-white">{summary.machines_used}</span>
                                    <span className="block text-[10px] text-gray-500 uppercase">Máquinas</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Usage Breakdown Table */}
                <div className="ta-card hover-glow mt-6">
                    <div className="ta-card-header">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="stat-card-icon bg-blue-500/10 text-blue-400">
                                    <Calculator size={18} />
                                </div>
                                <div>
                                    <h3 className="ta-card-title">Detalhamento por Máquina</h3>
                                    <p className="text-sm text-gray-400">Análise de uso e economia por recurso</p>
                                </div>
                            </div>
                            <button className="ta-btn ta-btn-ghost ta-btn-sm">
                                <Calculator size={16} />
                                Exportar CSV
                            </button>
                        </div>
                    </div>
                    <div className="ta-card-body">
                        <div className="overflow-x-auto">
                            <table className="ta-table">
                                <thead>
                                    <tr>
                                        <th>Recurso</th>
                                        <th>Horas</th>
                                        <th>Custo Dumont</th>
                                        <th>Custo {selectedProvider}</th>
                                        <th>Economia</th>
                                        <th>%</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(data?.breakdown || DEMO_DATA.breakdown).map((item, idx) => {
                                        const providerCost = item.cost_aws * (PROVIDER_MULTIPLIERS[selectedProvider] || 1.0)
                                        const savings = providerCost - item.cost_dumont
                                        return (
                                            <tr key={idx} className="animate-fade-in hover:bg-white/[0.02] transition-colors" style={{ animationDelay: `${idx * 50}ms` }}>
                                                <td>
                                                    <span className="gpu-badge">{item.name}</span>
                                                </td>
                                                <td>
                                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 text-xs text-gray-300">
                                                        <Clock size={12} className="text-blue-400" />
                                                        {item.hours}h
                                                    </span>
                                                </td>
                                                <td className="font-mono text-brand-400 font-semibold">${item.cost_dumont.toFixed(2)}</td>
                                                <td className="font-mono text-gray-400">${providerCost.toFixed(2)}</td>
                                                <td className="font-mono text-brand-400 font-bold">${savings.toFixed(2)}</td>
                                                <td>
                                                    <span className="ta-badge ta-badge-success">
                                                        {Math.round((savings / providerCost) * 100)}%
                                                    </span>
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>

                        {/* Summary Footer */}
                        <div className="mt-4 pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-4">
                            <div className="flex items-center gap-6">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-brand-500"></div>
                                    <span className="text-xs text-gray-400">Dumont Cloud</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                                    <span className="text-xs text-gray-400">{selectedProvider} (Comparação)</span>
                                </div>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-gray-500">
                                <span>Total de {(data?.breakdown || DEMO_DATA.breakdown).reduce((sum, item) => sum + item.hours, 0)} horas de GPU utilizadas</span>
                                {isPolling && (
                                    <span className="flex items-center gap-1 text-brand-400">
                                        <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
                                        Atualizando a cada {pollingInterval / 1000}s
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

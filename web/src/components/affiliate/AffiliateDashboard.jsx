import { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
    fetchAffiliateDashboard,
    fetchAffiliateStats,
    selectAffiliateDashboard,
    selectAffiliateStats,
    selectAffiliateLoading,
    selectStatsLoading,
    selectAffiliateError,
    setStatsPeriod,
} from '../../store/slices/affiliateSlice'
import {
    Users,
    MousePointerClick,
    DollarSign,
    TrendingUp,
    Percent,
    RefreshCw,
    BarChart3,
    Link2,
    UserPlus,
    Wallet,
    ArrowUpRight,
    Copy,
    CheckCircle,
    Sparkles,
} from 'lucide-react'
import AffiliateStatsChart from './AffiliateStatsChart'

// Demo data for when API is not available
const DEMO_DATA = {
    dashboard: {
        totalClicks: 1247,
        totalSignups: 89,
        totalConversions: 42,
        conversionRate: 47.2,
        totalEarnings: 1050.00,
        pendingEarnings: 175.00,
        paidEarnings: 875.00,
        lifetimeValue: 2450.00,
    },
    stats: {
        period: '30d',
        clicks: 312,
        signups: 24,
        conversions: 12,
        earnings: 300.00,
    },
}

export default function AffiliateDashboard() {
    const dispatch = useDispatch()

    const dashboard = useSelector(selectAffiliateDashboard)
    const stats = useSelector(selectAffiliateStats)
    const loading = useSelector(selectAffiliateLoading)
    const statsLoading = useSelector(selectStatsLoading)
    const error = useSelector(selectAffiliateError)

    const [period, setPeriod] = useState('30d')
    const [useDemo, setUseDemo] = useState(false)
    const [copied, setCopied] = useState(false)

    const periods = [
        { id: '7d', label: '7 dias' },
        { id: '30d', label: '30 dias' },
        { id: '90d', label: '90 dias' },
        { id: 'all', label: 'Total' },
    ]

    useEffect(() => {
        loadAllData()
    }, [])

    useEffect(() => {
        dispatch(setStatsPeriod(period))
        dispatch(fetchAffiliateStats(period))
            .unwrap()
            .catch(() => setUseDemo(true))
    }, [period, dispatch])

    const loadAllData = async () => {
        try {
            await dispatch(fetchAffiliateDashboard()).unwrap()
            await dispatch(fetchAffiliateStats(period)).unwrap()
            setUseDemo(false)
        } catch (err) {
            setUseDemo(true)
        }
    }

    const handleRefresh = () => {
        loadAllData()
    }

    const handlePeriodChange = (newPeriod) => {
        setPeriod(newPeriod)
    }

    // Use demo data if API fails
    const displayDashboard = useDemo ? DEMO_DATA.dashboard : dashboard
    const displayStats = useDemo ? DEMO_DATA.stats : stats

    // Referral URL for copying (placeholder - will be from referral slice in real app)
    const referralUrl = 'https://dumont.cloud/r/YOUR_CODE'

    const handleCopyLink = async () => {
        try {
            await navigator.clipboard.writeText(referralUrl)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea')
            textArea.value = referralUrl
            document.body.appendChild(textArea)
            textArea.select()
            document.execCommand('copy')
            document.body.removeChild(textArea)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    return (
        <div className="p-4 md:p-6 lg:p-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <nav className="flex items-center gap-2 text-sm text-gray-500 mb-3">
                        <a href="/app" className="hover:text-brand-400 transition-colors">Home</a>
                        <span className="text-gray-600">/</span>
                        <span className="text-white font-medium">Programa de Afiliados</span>
                    </nav>
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
                                <div className="stat-card-icon bg-purple-500/10 text-purple-400">
                                    <Users size={24} />
                                </div>
                                Dashboard de Afiliados
                            </h1>
                            <p className="text-gray-400 mt-1">Acompanhe suas indicações e ganhos</p>
                        </div>
                        <div className="flex items-center gap-3">
                            {/* Period Tabs */}
                            <div className="ta-tabs">
                                {periods.map((p) => (
                                    <button
                                        key={p.id}
                                        className={`ta-tab ${period === p.id ? 'ta-tab-active' : ''}`}
                                        onClick={() => handlePeriodChange(p.id)}
                                    >
                                        {p.label}
                                    </button>
                                ))}
                            </div>
                            <button
                                onClick={handleRefresh}
                                disabled={loading || statsLoading}
                                className="ta-btn ta-btn-outline ta-btn-sm"
                            >
                                <RefreshCw size={16} className={loading || statsLoading ? 'animate-spin' : ''} />
                                {loading || statsLoading ? 'Atualizando...' : 'Atualizar'}
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

                {/* Big Earnings Highlight */}
                <div className="spot-highlight mb-8 animate-fade-in">
                    <div className="flex flex-col md:flex-row items-center justify-center gap-6 relative z-10">
                        <div className="flex items-center gap-4">
                            <Sparkles size={40} className="text-purple-400" />
                            <div className="text-center md:text-left">
                                <span className="block text-xs text-purple-300/70 uppercase font-semibold tracking-wide">Ganhos Totais</span>
                                <span className="block text-4xl md:text-5xl font-extrabold text-white">${displayDashboard.totalEarnings.toFixed(2)}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 px-6 py-3 bg-white/10 rounded-xl">
                            <CheckCircle size={24} className="text-purple-400" />
                            <div>
                                <span className="block text-2xl font-bold text-purple-300">{displayDashboard.totalConversions}</span>
                                <span className="block text-xs text-purple-200/60">conversões</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Quick Share Card */}
                <div className="ta-card hover-glow mb-6 animate-fade-in">
                    <div className="ta-card-body py-4">
                        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                                <div className="stat-card-icon bg-purple-500/10 text-purple-400">
                                    <Link2 size={20} />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-white">Seu Link de Indicação</p>
                                    <p className="text-xs text-gray-400">Compartilhe para ganhar $25 por indicação</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <code className="px-3 py-2 bg-white/5 rounded-lg text-sm text-gray-300 font-mono">
                                    {referralUrl}
                                </code>
                                <button
                                    onClick={handleCopyLink}
                                    className="ta-btn ta-btn-primary ta-btn-sm"
                                >
                                    {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
                                    {copied ? 'Copiado!' : 'Copiar'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    <div className="stat-card animate-fade-in" style={{ animationDelay: '0ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Cliques</p>
                                <p className="text-2xl font-bold text-purple-400">{displayStats.clicks.toLocaleString()}</p>
                                <p className="text-xs text-gray-500 mt-1">Últimos {period === 'all' ? '' : period.replace('d', ' dias')}</p>
                            </div>
                            <div className="stat-card-icon bg-purple-500/10 text-purple-400">
                                <MousePointerClick size={20} />
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                                Total: {displayDashboard.totalClicks.toLocaleString()}
                            </span>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '50ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Cadastros</p>
                                <p className="text-2xl font-bold text-blue-400">{displayStats.signups.toLocaleString()}</p>
                                <p className="text-xs text-gray-500 mt-1">Novos usuários</p>
                            </div>
                            <div className="stat-card-icon bg-blue-500/10 text-blue-400">
                                <UserPlus size={20} />
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                                Total: {displayDashboard.totalSignups.toLocaleString()}
                            </span>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '100ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Conversões</p>
                                <p className="text-2xl font-bold text-green-400">{displayStats.conversions.toLocaleString()}</p>
                                <p className="text-xs text-gray-500 mt-1">Usuários ativos</p>
                            </div>
                            <div className="stat-card-icon stat-card-icon-success">
                                <TrendingUp size={20} />
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <span className="text-xs text-green-400 font-medium flex items-center gap-1">
                                <Percent size={12} />
                                {displayDashboard.conversionRate.toFixed(1)}% taxa
                            </span>
                        </div>
                    </div>

                    <div className="stat-card animate-fade-in" style={{ animationDelay: '150ms' }}>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Ganhos</p>
                                <p className="text-2xl font-bold text-brand-400">${displayStats.earnings.toFixed(2)}</p>
                                <p className="text-xs text-gray-500 mt-1">No período</p>
                            </div>
                            <div className="stat-card-icon stat-card-icon-primary">
                                <DollarSign size={20} />
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <span className="text-xs text-brand-400 font-medium flex items-center gap-1">
                                <ArrowUpRight size={12} />
                                $25 por conversão
                            </span>
                        </div>
                    </div>
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Conversion Funnel */}
                    <div className="ta-card hover-glow lg:col-span-2">
                        <div className="ta-card-header">
                            <div className="flex items-center gap-3">
                                <div className="stat-card-icon bg-purple-500/10 text-purple-400">
                                    <BarChart3 size={18} />
                                </div>
                                <div>
                                    <h3 className="ta-card-title">Funil de Conversão</h3>
                                    <p className="text-sm text-gray-400">Acompanhe o progresso das suas indicações</p>
                                </div>
                            </div>
                        </div>
                        <div className="ta-card-body">
                            <div className="space-y-5">
                                {/* Clicks */}
                                <div className="animate-fade-in" style={{ animationDelay: '0ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-purple-500 shadow-lg shadow-purple-500/30"></div>
                                            <span className="text-sm font-medium text-white">Cliques no Link</span>
                                        </div>
                                        <span className="text-sm font-bold text-purple-400">{displayDashboard.totalClicks.toLocaleString()}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: '100%' }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">100%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Signups */}
                                <div className="animate-fade-in" style={{ animationDelay: '100ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-blue-500 shadow-lg shadow-blue-500/30"></div>
                                            <span className="text-sm font-medium text-white">Cadastros</span>
                                        </div>
                                        <span className="text-sm font-bold text-blue-400">{displayDashboard.totalSignups.toLocaleString()}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: `${displayDashboard.totalClicks > 0 ? (displayDashboard.totalSignups / displayDashboard.totalClicks) * 100 : 0}%` }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">
                                                {displayDashboard.totalClicks > 0 ? ((displayDashboard.totalSignups / displayDashboard.totalClicks) * 100).toFixed(1) : 0}%
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Conversions */}
                                <div className="animate-fade-in" style={{ animationDelay: '200ms' }}>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-green-500 shadow-lg shadow-green-500/30"></div>
                                            <span className="text-sm font-medium text-white">Conversões</span>
                                            <span className="ta-badge ta-badge-success text-[10px]">$25 cada</span>
                                        </div>
                                        <span className="text-sm font-bold text-green-400">{displayDashboard.totalConversions.toLocaleString()}</span>
                                    </div>
                                    <div className="h-10 bg-white/5 rounded-xl overflow-hidden border border-white/5">
                                        <div
                                            className="h-full bg-gradient-to-r from-green-600 to-green-400 rounded-xl flex items-center justify-end pr-4 transition-all duration-700"
                                            style={{ width: `${displayDashboard.totalSignups > 0 ? (displayDashboard.totalConversions / displayDashboard.totalSignups) * 100 : 0}%` }}
                                        >
                                            <span className="text-xs font-bold text-white drop-shadow-md">
                                                {displayDashboard.conversionRate.toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Earnings Summary Card */}
                    <div className="ta-card hover-glow">
                        <div className="ta-card-header">
                            <h3 className="ta-card-title flex items-center gap-2">
                                <div className="stat-card-icon bg-brand-500/10 text-brand-400">
                                    <Wallet size={18} />
                                </div>
                                Resumo de Ganhos
                            </h3>
                        </div>
                        <div className="ta-card-body">
                            <div className="text-center py-4 mb-4 bg-gradient-to-br from-purple-500/10 to-purple-500/5 rounded-xl border border-purple-500/20">
                                <div className="text-5xl font-extrabold text-purple-400 mb-1">
                                    ${displayDashboard.totalEarnings.toFixed(0)}
                                </div>
                                <p className="text-sm text-purple-300/70">ganhos totais</p>
                            </div>

                            <div className="space-y-3 mb-4">
                                <div className="flex justify-between items-center p-3 bg-white/[0.03] rounded-lg hover:bg-white/[0.05] transition-colors">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                        <span className="text-sm text-gray-400">Pago</span>
                                    </div>
                                    <span className="text-sm font-bold text-green-400">
                                        ${displayDashboard.paidEarnings.toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center p-3 bg-white/[0.03] rounded-lg hover:bg-white/[0.05] transition-colors">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                                        <span className="text-sm text-gray-400">Pendente</span>
                                    </div>
                                    <span className="text-sm font-bold text-yellow-400">
                                        ${displayDashboard.pendingEarnings.toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center p-3 bg-white/[0.03] rounded-lg hover:bg-white/[0.05] transition-colors">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                                        <span className="text-sm text-gray-400">Valor Vitalício</span>
                                    </div>
                                    <span className="text-sm font-bold text-purple-400">
                                        ${displayDashboard.lifetimeValue.toFixed(2)}
                                    </span>
                                </div>
                            </div>

                            <div className="pt-4 border-t border-white/10 grid grid-cols-2 gap-3">
                                <div className="text-center p-3 bg-white/[0.02] rounded-lg">
                                    <Users size={18} className="mx-auto text-blue-400 mb-1" />
                                    <span className="block text-lg font-bold text-white">{displayDashboard.totalConversions}</span>
                                    <span className="block text-[10px] text-gray-500 uppercase">Conversões</span>
                                </div>
                                <div className="text-center p-3 bg-white/[0.02] rounded-lg">
                                    <DollarSign size={18} className="mx-auto text-brand-400 mb-1" />
                                    <span className="block text-lg font-bold text-white">$25</span>
                                    <span className="block text-[10px] text-gray-500 uppercase">Por Indicação</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* How it Works Section */}
                <div className="ta-card hover-glow mt-6">
                    <div className="ta-card-header">
                        <div className="flex items-center gap-3">
                            <div className="stat-card-icon bg-brand-500/10 text-brand-400">
                                <Sparkles size={18} />
                            </div>
                            <div>
                                <h3 className="ta-card-title">Como Funciona</h3>
                                <p className="text-sm text-gray-400">Ganhe créditos indicando a Dumont Cloud</p>
                            </div>
                        </div>
                    </div>
                    <div className="ta-card-body">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="text-center p-4">
                                <div className="w-12 h-12 rounded-full bg-purple-500/10 text-purple-400 flex items-center justify-center mx-auto mb-3">
                                    <Link2 size={24} />
                                </div>
                                <h4 className="font-semibold text-white mb-2">1. Compartilhe</h4>
                                <p className="text-sm text-gray-400">Envie seu link de indicação para amigos e colegas</p>
                            </div>
                            <div className="text-center p-4">
                                <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto mb-3">
                                    <UserPlus size={24} />
                                </div>
                                <h4 className="font-semibold text-white mb-2">2. Eles se Cadastram</h4>
                                <p className="text-sm text-gray-400">Indicados ganham $10 em créditos ao criar conta</p>
                            </div>
                            <div className="text-center p-4">
                                <div className="w-12 h-12 rounded-full bg-green-500/10 text-green-400 flex items-center justify-center mx-auto mb-3">
                                    <DollarSign size={24} />
                                </div>
                                <h4 className="font-semibold text-white mb-2">3. Você Ganha</h4>
                                <p className="text-sm text-gray-400">Receba $25 quando eles gastarem $50 na plataforma</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Conversion Tracking Chart */}
                <div className="mt-6">
                    <AffiliateStatsChart useDemo={useDemo} />
                </div>
            </div>
        </div>
    )
}

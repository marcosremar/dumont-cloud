import { useState, useEffect } from 'react'
import { PageHeader, StatCard, Card, Button, Badge, Progress, EmptyState, StatsGrid } from '../tailadmin-ui/index'
import { DollarSign, TrendingUp, TrendingDown, PiggyBank, Zap, Clock, Server, RefreshCw, BarChart3, ArrowUpRight, Calculator } from 'lucide-react'

const API_BASE = ''

// Dados demo para quando não há dados reais
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

export default function SavingsDashboard({ getAuthHeaders }) {
    const [period, setPeriod] = useState('month')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [data, setData] = useState(null)
    const [useDemo, setUseDemo] = useState(false)

    const periods = [
        { id: 'day', label: 'Hoje' },
        { id: 'week', label: '7 dias' },
        { id: 'month', label: '30 dias' },
        { id: 'year', label: '1 ano' }
    ]

    useEffect(() => {
        loadAllData()
    }, [period])

    const loadAllData = async () => {
        setLoading(true)
        setError(null)
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
            console.error('Error loading savings dashboard:', err)
            // Use demo data on error
            setData({
                summary: DEMO_DATA.summary,
                history: DEMO_DATA.history,
                breakdown: DEMO_DATA.breakdown
            })
            setUseDemo(true)
        } finally {
            setLoading(false)
        }
    }

    const summary = data?.summary || DEMO_DATA.summary

    return (
        <div className="p-4 md:p-6 lg:p-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <PageHeader
                    title="Dashboard de Economia"
                    subtitle="Compare seus custos reais com grandes cloud providers"
                    breadcrumbs={[
                        { label: 'Home', href: '/app' },
                        { label: 'Economia' }
                    ]}
                    actions={
                        <div className="flex items-center gap-3">
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
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={loadAllData}
                                disabled={loading}
                                icon={RefreshCw}
                            >
                                {loading ? 'Atualizando...' : 'Atualizar'}
                            </Button>
                        </div>
                    }
                />

                {/* Demo Mode Alert */}
                {useDemo && (
                    <div className="ta-alert ta-alert-info mb-6">
                        <BarChart3 size={20} />
                        <div>
                            <p className="font-medium">Modo Demonstração</p>
                            <p className="text-sm opacity-80">Os dados exibidos são simulados para fins de demonstração.</p>
                        </div>
                    </div>
                )}

                {/* Stats Grid */}
                <StatsGrid>
                    <StatCard
                        title="Você pagou"
                        value={`$${summary.total_cost_dumont.toFixed(2)}`}
                        subtitle="Este mês na Dumont Cloud"
                        icon={DollarSign}
                        iconColor="success"
                        change={`-${summary.savings_percentage_avg}% vs AWS`}
                        changeType="up"
                    />
                    <StatCard
                        title="AWS pagaria"
                        value={`$${summary.total_cost_aws.toFixed(2)}`}
                        subtitle="Mesmo workload na AWS"
                        icon={Server}
                        iconColor="gray"
                    />
                    <StatCard
                        title="Economia Total"
                        value={`$${summary.savings_vs_aws.toFixed(2)}`}
                        subtitle={`${summary.savings_percentage_avg}% de economia`}
                        icon={PiggyBank}
                        iconColor="success"
                        change={`+$${summary.savings_vs_aws.toFixed(0)} economizados`}
                        changeType="up"
                    />
                    <StatCard
                        title="Auto-Hibernate"
                        value={`$${summary.auto_hibernate_savings?.toFixed(2) || '0.00'}`}
                        subtitle="Economia por hibernação automática"
                        icon={Zap}
                        iconColor="warning"
                    />
                </StatsGrid>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
                    {/* Comparison Chart - Large */}
                    <Card className="lg:col-span-2" header={
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Comparativo de Custos</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">Dumont Cloud vs Big Cloud Providers</p>
                            </div>
                            <Badge variant="success">72% mais barato</Badge>
                        </div>
                    }>
                        {/* Visual Comparison Bars */}
                        <div className="space-y-6">
                            {/* Dumont */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-brand-500"></div>
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">Dumont Cloud</span>
                                    </div>
                                    <span className="text-sm font-bold text-brand-500">${summary.total_cost_dumont.toFixed(2)}</span>
                                </div>
                                <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-brand-500 to-brand-400 rounded-lg flex items-center justify-end pr-3"
                                        style={{ width: `${(summary.total_cost_dumont / summary.total_cost_aws) * 100}%` }}
                                    >
                                        <span className="text-xs font-bold text-white">{Math.round((summary.total_cost_dumont / summary.total_cost_aws) * 100)}%</span>
                                    </div>
                                </div>
                            </div>

                            {/* AWS */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">Amazon AWS</span>
                                    </div>
                                    <span className="text-sm font-bold text-orange-500">${summary.total_cost_aws.toFixed(2)}</span>
                                </div>
                                <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-orange-500 to-orange-400 rounded-lg flex items-center justify-end pr-3"
                                        style={{ width: '100%' }}
                                    >
                                        <span className="text-xs font-bold text-white">100%</span>
                                    </div>
                                </div>
                            </div>

                            {/* GCP */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">Google Cloud</span>
                                    </div>
                                    <span className="text-sm font-bold text-blue-500">${summary.total_cost_gcp?.toFixed(2) || '756.80'}</span>
                                </div>
                                <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-lg flex items-center justify-end pr-3"
                                        style={{ width: `${((summary.total_cost_gcp || 756.80) / summary.total_cost_aws) * 100}%` }}
                                    >
                                        <span className="text-xs font-bold text-white">{Math.round(((summary.total_cost_gcp || 756.80) / summary.total_cost_aws) * 100)}%</span>
                                    </div>
                                </div>
                            </div>

                            {/* Azure */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full bg-sky-500"></div>
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">Microsoft Azure</span>
                                    </div>
                                    <span className="text-sm font-bold text-sky-500">${summary.total_cost_azure?.toFixed(2) || '823.40'}</span>
                                </div>
                                <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-sky-500 to-sky-400 rounded-lg flex items-center justify-end pr-3"
                                        style={{ width: `${((summary.total_cost_azure || 823.40) / summary.total_cost_aws) * 100}%` }}
                                    >
                                        <span className="text-xs font-bold text-white">{Math.round(((summary.total_cost_azure || 823.40) / summary.total_cost_aws) * 100)}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </Card>

                    {/* Savings Summary Card */}
                    <Card header="Resumo de Economia">
                        <div className="space-y-4">
                            <div className="text-center py-4">
                                <div className="text-5xl font-bold text-brand-500 mb-2">
                                    {summary.savings_percentage_avg}%
                                </div>
                                <p className="text-sm text-gray-500 dark:text-gray-400">de economia média</p>
                            </div>

                            <div className="border-t border-gray-200 dark:border-gray-800 pt-4 space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-500 dark:text-gray-400">vs AWS</span>
                                    <span className="text-sm font-semibold text-success-500">
                                        <ArrowUpRight size={14} className="inline mr-1" />
                                        ${summary.savings_vs_aws.toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-500 dark:text-gray-400">vs GCP</span>
                                    <span className="text-sm font-semibold text-success-500">
                                        <ArrowUpRight size={14} className="inline mr-1" />
                                        ${summary.savings_vs_gcp?.toFixed(2) || '509.30'}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-500 dark:text-gray-400">vs Azure</span>
                                    <span className="text-sm font-semibold text-success-500">
                                        <ArrowUpRight size={14} className="inline mr-1" />
                                        ${summary.savings_vs_azure?.toFixed(2) || '575.90'}
                                    </span>
                                </div>
                            </div>

                            <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-500 dark:text-gray-400">GPU Hours</span>
                                    <span className="text-sm font-semibold text-gray-900 dark:text-white">{summary.total_gpu_hours}h</span>
                                </div>
                                <div className="flex justify-between items-center mt-2">
                                    <span className="text-sm text-gray-500 dark:text-gray-400">Máquinas</span>
                                    <span className="text-sm font-semibold text-gray-900 dark:text-white">{summary.machines_used}</span>
                                </div>
                            </div>
                        </div>
                    </Card>
                </div>

                {/* Usage Breakdown Table */}
                <Card className="mt-6" header={
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Detalhamento por Máquina</h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400">Análise de uso e economia por recurso</p>
                        </div>
                        <Button variant="ghost" size="sm" icon={Calculator}>
                            Exportar CSV
                        </Button>
                    </div>
                }>
                    <div className="overflow-x-auto">
                        <table className="ta-table">
                            <thead>
                                <tr>
                                    <th>Recurso</th>
                                    <th>Horas</th>
                                    <th>Custo Dumont</th>
                                    <th>Custo AWS</th>
                                    <th>Economia</th>
                                    <th>%</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(data?.breakdown || DEMO_DATA.breakdown).map((item, idx) => (
                                    <tr key={idx}>
                                        <td className="font-medium text-gray-900 dark:text-white">{item.name}</td>
                                        <td>
                                            <Badge variant="gray" size="sm">
                                                <Clock size={12} className="mr-1" />
                                                {item.hours}h
                                            </Badge>
                                        </td>
                                        <td className="font-mono text-brand-500">${item.cost_dumont.toFixed(2)}</td>
                                        <td className="font-mono text-gray-500">${item.cost_aws.toFixed(2)}</td>
                                        <td className="font-mono text-success-500 font-semibold">${item.savings.toFixed(2)}</td>
                                        <td>
                                            <Badge variant="success" size="sm">
                                                {Math.round((item.savings / item.cost_aws) * 100)}%
                                            </Badge>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </div>
        </div>
    )
}

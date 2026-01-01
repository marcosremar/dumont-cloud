import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { TrendingUp } from 'lucide-react'
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
import {
    fetchDailyMetrics,
    selectDailyMetrics,
    selectMetricsLoading,
} from '../../store/slices/affiliateSlice'

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

// Demo data for when API is not available
const DEMO_METRICS = [
    { date: '01/12', clicks: 45, signups: 5, conversions: 2 },
    { date: '02/12', clicks: 52, signups: 6, conversions: 3 },
    { date: '03/12', clicks: 38, signups: 4, conversions: 1 },
    { date: '04/12', clicks: 61, signups: 8, conversions: 4 },
    { date: '05/12', clicks: 55, signups: 7, conversions: 3 },
    { date: '06/12', clicks: 48, signups: 5, conversions: 2 },
    { date: '07/12', clicks: 72, signups: 9, conversions: 5 },
    { date: '08/12', clicks: 65, signups: 8, conversions: 4 },
    { date: '09/12', clicks: 58, signups: 6, conversions: 3 },
    { date: '10/12', clicks: 80, signups: 10, conversions: 6 },
    { date: '11/12', clicks: 75, signups: 9, conversions: 5 },
    { date: '12/12', clicks: 68, signups: 7, conversions: 4 },
    { date: '13/12', clicks: 82, signups: 11, conversions: 6 },
    { date: '14/12', clicks: 90, signups: 12, conversions: 7 },
]

export default function AffiliateStatsChart({ useDemo = false }) {
    const dispatch = useDispatch()
    const dailyMetrics = useSelector(selectDailyMetrics)
    const loading = useSelector(selectMetricsLoading)

    useEffect(() => {
        if (!useDemo) {
            dispatch(fetchDailyMetrics())
        }
    }, [dispatch, useDemo])

    if (loading && !useDemo) {
        return <div className="affiliate-stats-chart skeleton" />
    }

    const metrics = useDemo || !dailyMetrics?.length ? DEMO_METRICS : dailyMetrics

    const chartData = {
        labels: metrics.map(m => m.date),
        datasets: [
            {
                label: 'Cliques',
                data: metrics.map(m => m.clicks),
                borderColor: '#a855f7',
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#a855f7',
            },
            {
                label: 'Cadastros',
                data: metrics.map(m => m.signups),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.05)',
                fill: false,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#3b82f6',
            },
            {
                label: 'Conversões',
                data: metrics.map(m => m.conversions),
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34, 197, 94, 0.05)',
                fill: false,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#22c55e',
            },
        ]
    }

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    color: '#9ca3af',
                    usePointStyle: true,
                    boxWidth: 6,
                    padding: 20,
                    font: { size: 12 },
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: '#1c211c',
                titleColor: '#fff',
                bodyColor: '#9ca3af',
                borderColor: '#30363d',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}`
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    color: '#6b7280',
                    font: { size: 10 },
                    stepSize: 1,
                },
                grid: { color: '#1f2937' }
            },
            x: {
                ticks: {
                    color: '#6b7280',
                    font: { size: 10 },
                    maxRotation: 45,
                    minRotation: 0,
                },
                grid: { display: false }
            }
        }
    }

    // Calculate totals for the footer
    const totalClicks = metrics.reduce((acc, m) => acc + m.clicks, 0)
    const totalSignups = metrics.reduce((acc, m) => acc + m.signups, 0)
    const totalConversions = metrics.reduce((acc, m) => acc + m.conversions, 0)
    const conversionRate = totalSignups > 0 ? ((totalConversions / totalSignups) * 100).toFixed(1) : 0

    return (
        <div className="affiliate-stats-chart">
            <div className="chart-header">
                <h3>
                    <TrendingUp size={18} />
                    Histórico de Conversões
                </h3>
                <p className="chart-subtitle">Acompanhe suas métricas diárias</p>
            </div>

            <div className="chart-container" style={{ height: '280px' }}>
                <Line data={chartData} options={chartOptions} />
            </div>

            <div className="chart-footer">
                <div className="footer-stats">
                    <span className="stat">
                        <span className="dot purple"></span>
                        Cliques: <strong>{totalClicks.toLocaleString()}</strong>
                    </span>
                    <span className="stat">
                        <span className="dot blue"></span>
                        Cadastros: <strong>{totalSignups.toLocaleString()}</strong>
                    </span>
                    <span className="stat">
                        <span className="dot green"></span>
                        Conversões: <strong>{totalConversions.toLocaleString()}</strong>
                    </span>
                    <span className="stat rate">
                        Taxa: <strong>{conversionRate}%</strong>
                    </span>
                </div>
            </div>

            <style jsx>{`
                .affiliate-stats-chart {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                .chart-header {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                .chart-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .chart-subtitle {
                    font-size: 13px;
                    color: #9ca3af;
                    margin: 0;
                }
                .chart-container {
                    position: relative;
                }
                .chart-footer {
                    padding-top: 16px;
                    border-top: 1px solid #30363d;
                }
                .footer-stats {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                    gap: 16px;
                }
                .stat {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 13px;
                    color: #9ca3af;
                }
                .stat strong {
                    color: #fff;
                }
                .stat.rate strong {
                    color: #22c55e;
                }
                .dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                }
                .dot.purple { background: #a855f7; }
                .dot.blue { background: #3b82f6; }
                .dot.green { background: #22c55e; }

                .skeleton {
                    min-height: 400px;
                    background: linear-gradient(90deg, #1c211c 25%, #2a352a 50%, #1c211c 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                    border-radius: 12px;
                }
                @keyframes shimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }

                @media (max-width: 640px) {
                    .footer-stats {
                        flex-direction: column;
                        align-items: center;
                        gap: 8px;
                    }
                }
            `}</style>
        </div>
    )
}

import { useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Users, UserCheck, TrendingUp, DollarSign, Clock, HelpCircle } from 'lucide-react'
import {
    fetchReferralStats,
    selectReferralStats,
    selectReferralLoading,
    selectReferralError,
} from '../../store/slices/referralSlice'

export default function ReferralStatsCard() {
    const dispatch = useDispatch()
    const stats = useSelector(selectReferralStats)
    const loading = useSelector(selectReferralLoading)
    const error = useSelector(selectReferralError)

    useEffect(() => {
        dispatch(fetchReferralStats())
    }, [dispatch])

    if (loading) {
        return <div className="referral-stats-card skeleton" />
    }

    if (error) {
        return (
            <div className="referral-stats-card error">
                <div className="card-header">
                    <h3>
                        <TrendingUp size={18} className="icon-purple" />
                        Desempenho das Indicações
                    </h3>
                </div>
                <p className="error-message">Erro ao carregar estatísticas</p>

                <style jsx>{`
                    .referral-stats-card {
                        background: #1c211c;
                        border: 1px solid #30363d;
                        border-radius: 12px;
                        padding: 24px;
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                        position: relative;
                        overflow: hidden;
                    }
                    .referral-stats-card.error {
                        border-color: #ef4444;
                    }
                    .referral-stats-card.error::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 4px;
                        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    }
                    .card-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }
                    .card-header h3 {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 18px;
                        font-weight: 700;
                        margin: 0;
                        color: #fff;
                    }
                    .icon-purple { color: #a855f7; }
                    .error-message {
                        font-size: 13px;
                        color: #ef4444;
                        margin: 0;
                    }
                `}</style>
            </div>
        )
    }

    const conversionRate = stats.conversionRate || 0
    const barWidth = Math.min(Math.max(conversionRate, 5), 100)

    return (
        <div className="referral-stats-card">
            <div className="card-header">
                <h3>
                    <TrendingUp size={18} className="icon-purple" />
                    Desempenho das Indicações
                </h3>
                <div className="header-actions">
                    <HelpCircle size={14} className="icon-muted" title="Métricas do seu programa de indicação" />
                </div>
            </div>

            <div className="stats-grid">
                <div className="stat-item main">
                    <span className="label">Total de Indicações</span>
                    <span className="value">{stats.totalReferrals}</span>
                </div>
                <div className="stat-item">
                    <span className="label">Ativos</span>
                    <span className="value">{stats.activeReferrals}</span>
                </div>
                <div className="stat-item highlight">
                    <span className="label">Convertidos</span>
                    <span className="value-purple">
                        <UserCheck size={14} />
                        {stats.convertedReferrals}
                    </span>
                </div>
            </div>

            <div className="earnings-grid">
                <div className="earning-item">
                    <DollarSign size={16} className="icon-green" />
                    <div className="earning-info">
                        <span className="value">${stats.earnedCredits.toFixed(2)}</span>
                        <span className="label">Créditos Ganhos</span>
                    </div>
                </div>
                <div className="earning-item">
                    <Clock size={16} className="icon-yellow" />
                    <div className="earning-info">
                        <span className="value">${stats.pendingCredits.toFixed(2)}</span>
                        <span className="label">Pendentes</span>
                    </div>
                </div>
            </div>

            <div className="progress-container">
                <div className="progress-header">
                    <span className="progress-title">Taxa de Conversão</span>
                    <span className="progress-value">{conversionRate.toFixed(1)}%</span>
                </div>
                <div className="progress-track">
                    <div
                        className="progress-bar"
                        style={{ width: `${barWidth}%` }}
                    />
                </div>
                <p className="progress-label">
                    {stats.convertedReferrals} de {stats.totalReferrals} indicações converteram em clientes pagantes
                </p>
            </div>

            <style jsx>{`
                .referral-stats-card {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    transition: all 0.3s;
                    position: relative;
                    overflow: hidden;
                }

                .referral-stats-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 100%);
                }

                .referral-stats-card:hover {
                    border-color: #a855f7;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 24px rgba(168, 85, 247, 0.2);
                }

                .card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .card-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 18px;
                    font-weight: 700;
                    margin: 0;
                    color: #fff;
                }

                .icon-purple { color: #a855f7; }
                .icon-muted { color: #4b5563; cursor: help; }
                .icon-green { color: #22c55e; }
                .icon-yellow { color: #eab308; }

                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 16px;
                    border-bottom: 1px solid #30363d;
                    padding-bottom: 20px;
                }

                .stat-item {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .stat-item .label {
                    font-size: 12px;
                    color: #9ca3af;
                    font-weight: 500;
                }

                .stat-item .value {
                    font-size: 20px;
                    font-weight: 700;
                    color: #fff;
                }

                .stat-item.main .value {
                    font-size: 32px;
                    background: linear-gradient(135deg, #a855f7, #8b5cf6);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .stat-item.highlight {
                    background: rgba(168, 85, 247, 0.1);
                    padding: 12px;
                    border-radius: 8px;
                    margin: -12px;
                }

                .stat-item.highlight .value-purple {
                    font-size: 22px;
                    font-weight: 700;
                    color: #a855f7;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }

                .earnings-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 12px;
                }

                .earning-item {
                    background: #161a16;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 14px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }

                .earning-info {
                    display: flex;
                    flex-direction: column;
                }

                .earning-info .value {
                    font-size: 18px;
                    font-weight: 700;
                    color: #fff;
                }

                .earning-info .label {
                    font-size: 11px;
                    color: #6b7280;
                    text-transform: uppercase;
                }

                .progress-container {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }

                .progress-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .progress-title {
                    font-size: 13px;
                    font-weight: 600;
                    color: #9ca3af;
                }

                .progress-value {
                    font-size: 14px;
                    font-weight: 700;
                    color: #a855f7;
                }

                .progress-track {
                    height: 8px;
                    background: #161a16;
                    border-radius: 4px;
                    overflow: hidden;
                    border: 1px solid #30363d;
                }

                .progress-bar {
                    background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 100%);
                    height: 100%;
                    border-radius: 4px;
                    transition: width 0.3s ease;
                }

                .progress-label {
                    font-size: 12px;
                    color: #6b7280;
                    text-align: center;
                    margin: 0;
                }

                .skeleton {
                    min-height: 280px;
                    background: #1c211c;
                    position: relative;
                    overflow: hidden;
                }

                .skeleton::after {
                    content: "";
                    position: absolute;
                    inset: 0;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
                    animation: shimmer 1.5s infinite;
                }

                @keyframes shimmer {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }

                @media (max-width: 480px) {
                    .stats-grid {
                        grid-template-columns: 1fr;
                    }

                    .stat-item.highlight {
                        margin: 0;
                    }

                    .earnings-grid {
                        grid-template-columns: 1fr;
                    }
                }
            `}</style>
        </div>
    )
}

import { useState, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { DollarSign, TrendingUp, PiggyBank, Activity, HelpCircle, ArrowUpRight } from 'lucide-react'
import {
    fetchSavings,
    fetchActiveSession,
    selectLifetimeSavings,
    selectCurrentSessionSavings,
    selectHourlyComparison,
    selectProjections,
    selectSelectedProvider,
    selectActiveSession,
    selectEconomyLoading,
    selectHasActiveInstances,
} from '../../store/slices/economySlice'

const API_BASE = ''

export default function EconomyWidget({ getAuthHeaders }) {
    const dispatch = useDispatch()

    // Redux selectors
    const lifetimeSavings = useSelector(selectLifetimeSavings)
    const currentSessionSavings = useSelector(selectCurrentSessionSavings)
    const hourlyComparison = useSelector(selectHourlyComparison)
    const projections = useSelector(selectProjections)
    const selectedProvider = useSelector(selectSelectedProvider)
    const activeSession = useSelector(selectActiveSession)
    const loading = useSelector(selectEconomyLoading)
    const hasActiveInstances = useSelector(selectHasActiveInstances)

    // Local state for live counter animation
    const [liveCounter, setLiveCounter] = useState(0)
    const [sessionStartTime, setSessionStartTime] = useState(null)
    const liveCounterRef = useRef(null)

    // Load data on mount
    useEffect(() => {
        dispatch(fetchSavings(selectedProvider))
        dispatch(fetchActiveSession(selectedProvider))

        // Refresh every 60 seconds
        const interval = setInterval(() => {
            dispatch(fetchSavings(selectedProvider))
            dispatch(fetchActiveSession(selectedProvider))
        }, 60000)

        return () => clearInterval(interval)
    }, [dispatch, selectedProvider])

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
            }, 100)

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

    if (loading && lifetimeSavings === 0) {
        return <div className="economy-widget skeleton" />
    }

    return (
        <div className="economy-widget">
            <div className="card-header">
                <h3>
                    <PiggyBank size={18} className="icon-green" />
                    Economia
                </h3>
                <a href="/savings" className="view-more">
                    Ver mais
                    <ArrowUpRight size={12} />
                </a>
            </div>

            <div className="stats-body">
                {/* Lifetime Savings Highlight */}
                <div className="savings-highlight">
                    <span className="label">Total Economizado vs {selectedProvider}</span>
                    <span className="value">${lifetimeSavings.toFixed(2)}</span>
                </div>

                <div className="stats-grid">
                    {/* Monthly Projection */}
                    <div className="stat-box">
                        <TrendingUp size={16} className="icon-blue" />
                        <div className="stat-info">
                            <span className="value">${projections.monthly.toFixed(0)}</span>
                            <span className="label">Proj. Mensal</span>
                        </div>
                    </div>

                    {/* Hourly Savings Rate */}
                    <div className="stat-box">
                        <DollarSign size={16} className="icon-green" />
                        <div className="stat-info">
                            <span className="value">${hourlyComparison.savingsPerHour.toFixed(2)}</span>
                            <span className="label">Por Hora</span>
                        </div>
                    </div>
                </div>

                {/* Active Session Section */}
                {hasActiveInstances ? (
                    <div className="active-session">
                        <div className="session-header">
                            <div className="pulse-indicator" />
                            <span className="session-label">
                                {activeSession.activeInstances} {activeSession.activeInstances === 1 ? 'instância ativa' : 'instâncias ativas'}
                            </span>
                        </div>
                        <div className="session-savings">
                            <span className="live-value">${liveCounter.toFixed(4)}</span>
                            <span className="session-duration">Duração: {formatDuration(activeSession.sessionDuration)}</span>
                        </div>
                    </div>
                ) : (
                    <div className="no-session">
                        <Activity size={14} className="icon-muted" />
                        <span>Inicie uma instância para ver economia em tempo real</span>
                    </div>
                )}
            </div>

            <style jsx>{`
                .economy-widget {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
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
                    font-size: 15px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .view-more {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 12px;
                    color: #22c55e;
                    text-decoration: none;
                    transition: color 0.2s;
                }
                .view-more:hover {
                    color: #4ade80;
                }
                .icon-green { color: #22c55e; }
                .icon-blue { color: #3b82f6; }
                .icon-muted { color: #4b5563; }

                .savings-highlight {
                    background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(34, 197, 94, 0.05) 100%);
                    border: 1px solid rgba(34, 197, 94, 0.2);
                    border-radius: 10px;
                    padding: 16px;
                    text-align: center;
                }
                .savings-highlight .label {
                    display: block;
                    font-size: 11px;
                    color: #9ca3af;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 4px;
                }
                .savings-highlight .value {
                    display: block;
                    font-size: 28px;
                    font-weight: 700;
                    color: #22c55e;
                }

                .stats-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                }
                .stat-box {
                    background: #161a16;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 12px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .stat-info {
                    display: flex;
                    flex-direction: column;
                }
                .stat-info .value {
                    font-size: 16px;
                    font-weight: 700;
                    color: #fff;
                }
                .stat-info .label {
                    font-size: 10px;
                    color: #6b7280;
                    text-transform: uppercase;
                }

                .active-session {
                    background: linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(34, 197, 94, 0.02) 100%);
                    border: 1px solid rgba(34, 197, 94, 0.15);
                    border-radius: 8px;
                    padding: 12px;
                }
                .session-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 8px;
                }
                .pulse-indicator {
                    width: 8px;
                    height: 8px;
                    background: #22c55e;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(0.8); }
                }
                .session-label {
                    font-size: 12px;
                    color: #9ca3af;
                }
                .session-savings {
                    display: flex;
                    justify-content: space-between;
                    align-items: baseline;
                }
                .live-value {
                    font-size: 20px;
                    font-weight: 700;
                    color: #22c55e;
                    font-variant-numeric: tabular-nums;
                }
                .session-duration {
                    font-size: 11px;
                    color: #6b7280;
                }

                .no-session {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: #161a16;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 11px;
                    color: #6b7280;
                }

                .skeleton {
                    min-height: 220px;
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
            `}</style>
        </div>
    )
}

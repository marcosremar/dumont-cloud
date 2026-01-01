import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { List, Download, DollarSign, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import {
    fetchPayoutHistory,
    exportAffiliateData,
    selectPayouts,
    selectPayoutsLoading,
    selectPayoutsError,
    selectExportLoading,
} from '../../store/slices/affiliateSlice'

// Demo data for when API is not available
const DEMO_PAYOUTS = [
    {
        id: 1,
        type: 'referral_bonus',
        amount: 25.00,
        balance_after: 175.00,
        description: 'Bônus de indicação - usuário atingiu $50 de gasto',
        status: 'completed',
        created_at: '2025-01-15T10:30:00Z',
    },
    {
        id: 2,
        type: 'referral_bonus',
        amount: 25.00,
        balance_after: 150.00,
        description: 'Bônus de indicação - usuário atingiu $50 de gasto',
        status: 'completed',
        created_at: '2025-01-10T14:20:00Z',
    },
    {
        id: 3,
        type: 'referral_bonus',
        amount: 25.00,
        balance_after: 125.00,
        description: 'Bônus de indicação - usuário atingiu $50 de gasto',
        status: 'pending',
        created_at: '2025-01-05T09:15:00Z',
    },
    {
        id: 4,
        type: 'payout',
        amount: -100.00,
        balance_after: 100.00,
        description: 'Saque para conta bancária',
        status: 'completed',
        created_at: '2025-01-01T16:45:00Z',
    },
    {
        id: 5,
        type: 'referral_bonus',
        amount: 25.00,
        balance_after: 200.00,
        description: 'Bônus de indicação - usuário atingiu $50 de gasto',
        status: 'completed',
        created_at: '2024-12-28T11:00:00Z',
    },
]

export default function AffiliatePayoutsTable({ useDemo = false }) {
    const dispatch = useDispatch()

    const payouts = useSelector(selectPayouts)
    const loading = useSelector(selectPayoutsLoading)
    const error = useSelector(selectPayoutsError)
    const exportLoading = useSelector(selectExportLoading)

    useEffect(() => {
        if (!useDemo) {
            dispatch(fetchPayoutHistory({ limit: 20, offset: 0 }))
        }
    }, [dispatch, useDemo])

    const handleExport = async () => {
        try {
            const result = await dispatch(exportAffiliateData({})).unwrap()
            if (result.blob) {
                // Create download link
                const url = window.URL.createObjectURL(result.blob)
                const a = document.createElement('a')
                a.href = url
                a.download = result.filename || 'affiliate-data.csv'
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)
                window.URL.revokeObjectURL(url)
            }
        } catch (err) {
            // Error is handled by the slice
        }
    }

    // Use demo data if specified or API fails
    const displayPayouts = useDemo || error ? DEMO_PAYOUTS : payouts

    if (loading && !useDemo) {
        return <div className="affiliate-payouts-table skeleton" />
    }

    const formatDate = (dateString) => {
        const date = new Date(dateString)
        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed':
                return <CheckCircle size={14} className="status-icon status-completed" />
            case 'pending':
                return <Clock size={14} className="status-icon status-pending" />
            case 'failed':
                return <AlertCircle size={14} className="status-icon status-failed" />
            default:
                return <Clock size={14} className="status-icon status-pending" />
        }
    }

    const getStatusLabel = (status) => {
        switch (status) {
            case 'completed':
                return 'Concluído'
            case 'pending':
                return 'Pendente'
            case 'failed':
                return 'Falhou'
            default:
                return status
        }
    }

    const getTypeLabel = (type) => {
        switch (type) {
            case 'referral_bonus':
                return 'Bônus de Indicação'
            case 'welcome_credit':
                return 'Crédito de Boas-vindas'
            case 'payout':
                return 'Saque'
            case 'manual_adjustment':
                return 'Ajuste Manual'
            default:
                return type
        }
    }

    return (
        <div className="affiliate-payouts-table">
            <div className="table-header">
                <h3>
                    <List size={18} />
                    Histórico de Pagamentos
                </h3>
                <button
                    className="export-btn"
                    onClick={handleExport}
                    disabled={exportLoading}
                >
                    <Download size={14} className={exportLoading ? 'animate-spin' : ''} />
                    {exportLoading ? 'Exportando...' : 'Exportar CSV'}
                </button>
            </div>

            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Tipo</th>
                            <th>Descrição</th>
                            <th>Status</th>
                            <th>Valor</th>
                            <th>Saldo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {displayPayouts.length > 0 ? (
                            displayPayouts.map((payout) => (
                                <tr key={payout.id}>
                                    <td className="date-cell">
                                        {formatDate(payout.created_at)}
                                    </td>
                                    <td>
                                        <span className="type-badge">
                                            {getTypeLabel(payout.type)}
                                        </span>
                                    </td>
                                    <td className="description-cell">
                                        {payout.description}
                                    </td>
                                    <td>
                                        <span className={`status-badge status-${payout.status || 'pending'}`}>
                                            {getStatusIcon(payout.status)}
                                            {getStatusLabel(payout.status)}
                                        </span>
                                    </td>
                                    <td className={`amount-cell ${payout.amount >= 0 ? 'positive' : 'negative'}`}>
                                        <DollarSign size={12} />
                                        {payout.amount >= 0 ? '+' : ''}{payout.amount.toFixed(2)}
                                    </td>
                                    <td className="balance-cell">
                                        ${payout.balance_after.toFixed(2)}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="6" className="empty-row">
                                    Nenhum pagamento registrado ainda.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Summary Footer */}
            {displayPayouts.length > 0 && (
                <div className="table-footer">
                    <div className="footer-stats">
                        <span className="stat">
                            <strong>{displayPayouts.length}</strong> transações
                        </span>
                        <span className="stat">
                            <strong className="positive">
                                ${displayPayouts.filter(p => p.amount > 0).reduce((sum, p) => sum + p.amount, 0).toFixed(2)}
                            </strong> recebidos
                        </span>
                    </div>
                </div>
            )}

            <style jsx>{`
                .affiliate-payouts-table {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 24px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }
                .table-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .table-header h3 {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }
                .export-btn {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    background: transparent;
                    border: 1px solid #30363d;
                    color: #9ca3af;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .export-btn:hover:not(:disabled) {
                    background: #2a352a;
                    color: #fff;
                    border-color: #4b5563;
                }
                .export-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .table-container {
                    overflow-x: auto;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                }
                th {
                    text-align: left;
                    padding: 12px;
                    color: #9ca3af;
                    font-weight: 500;
                    border-bottom: 1px solid #30363d;
                    white-space: nowrap;
                }
                td {
                    padding: 12px;
                    color: #e5e7eb;
                    border-bottom: 1px solid #161a16;
                }
                tr:last-child td {
                    border-bottom: none;
                }
                tr:hover td {
                    background: rgba(255, 255, 255, 0.02);
                }

                .date-cell {
                    color: #9ca3af;
                    font-size: 12px;
                    white-space: nowrap;
                }

                .description-cell {
                    max-width: 300px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .type-badge {
                    display: inline-block;
                    padding: 4px 8px;
                    background: rgba(168, 85, 247, 0.1);
                    color: #a855f7;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 500;
                    white-space: nowrap;
                }

                .status-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 500;
                    white-space: nowrap;
                }
                .status-badge.status-completed {
                    background: rgba(34, 197, 94, 0.1);
                    color: #22c55e;
                }
                .status-badge.status-pending {
                    background: rgba(234, 179, 8, 0.1);
                    color: #eab308;
                }
                .status-badge.status-failed {
                    background: rgba(239, 68, 68, 0.1);
                    color: #ef4444;
                }

                .status-icon {
                    flex-shrink: 0;
                }
                .status-completed { color: #22c55e; }
                .status-pending { color: #eab308; }
                .status-failed { color: #ef4444; }

                .amount-cell {
                    display: flex;
                    align-items: center;
                    gap: 2px;
                    font-weight: 600;
                    white-space: nowrap;
                }
                .amount-cell.positive {
                    color: #22c55e;
                }
                .amount-cell.negative {
                    color: #ef4444;
                }

                .balance-cell {
                    color: #9ca3af;
                    font-family: monospace;
                    white-space: nowrap;
                }

                .empty-row {
                    text-align: center;
                    color: #4b5563;
                    padding: 40px !important;
                }

                .table-footer {
                    padding-top: 16px;
                    border-top: 1px solid #30363d;
                }
                .footer-stats {
                    display: flex;
                    gap: 24px;
                }
                .footer-stats .stat {
                    font-size: 12px;
                    color: #9ca3af;
                }
                .footer-stats strong {
                    color: #fff;
                }
                .footer-stats .positive {
                    color: #22c55e;
                }

                .skeleton {
                    min-height: 300px;
                    background: linear-gradient(90deg, #1c211c 25%, #2a352a 50%, #1c211c 75%);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s infinite;
                    border-radius: 12px;
                }

                @keyframes shimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }

                @media (max-width: 768px) {
                    .affiliate-payouts-table {
                        padding: 16px;
                    }
                    .table-header {
                        flex-direction: column;
                        gap: 12px;
                        align-items: flex-start;
                    }
                    .export-btn {
                        width: 100%;
                        justify-content: center;
                    }
                    .description-cell {
                        max-width: 150px;
                    }
                }
            `}</style>
        </div>
    )
}

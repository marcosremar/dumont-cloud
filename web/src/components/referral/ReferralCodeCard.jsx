import { useState, useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Gift, Copy, Check, Users, DollarSign, Link, HelpCircle } from 'lucide-react'
import {
    fetchReferralCode,
    selectReferralCode,
    selectReferralUrl,
    selectReferralStats,
    selectReferralLoading,
    selectReferralError,
} from '../../store/slices/referralSlice'

export default function ReferralCodeCard() {
    const dispatch = useDispatch()
    const referralCode = useSelector(selectReferralCode)
    const referralUrl = useSelector(selectReferralUrl)
    const stats = useSelector(selectReferralStats)
    const loading = useSelector(selectReferralLoading)
    const error = useSelector(selectReferralError)

    const [codeCopied, setCodeCopied] = useState(false)
    const [urlCopied, setUrlCopied] = useState(false)

    useEffect(() => {
        dispatch(fetchReferralCode())
    }, [dispatch])

    const handleCopyCode = async () => {
        if (!referralCode) return
        try {
            await navigator.clipboard.writeText(referralCode)
            setCodeCopied(true)
            setTimeout(() => setCodeCopied(false), 2000)
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea')
            textArea.value = referralCode
            document.body.appendChild(textArea)
            textArea.select()
            document.execCommand('copy')
            document.body.removeChild(textArea)
            setCodeCopied(true)
            setTimeout(() => setCodeCopied(false), 2000)
        }
    }

    const handleCopyUrl = async () => {
        if (!referralUrl) return
        try {
            await navigator.clipboard.writeText(referralUrl)
            setUrlCopied(true)
            setTimeout(() => setUrlCopied(false), 2000)
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea')
            textArea.value = referralUrl
            document.body.appendChild(textArea)
            textArea.select()
            document.execCommand('copy')
            document.body.removeChild(textArea)
            setUrlCopied(true)
            setTimeout(() => setUrlCopied(false), 2000)
        }
    }

    if (loading) {
        return <div className="referral-code-card skeleton" />
    }

    if (error) {
        return (
            <div className="referral-code-card error">
                <div className="card-header">
                    <h3>
                        <Gift size={18} className="icon-purple" />
                        Programa de Indicação
                    </h3>
                </div>
                <p className="error-message">Erro ao carregar código de indicação</p>
            </div>
        )
    }

    return (
        <div className="referral-code-card">
            <div className="card-header">
                <h3>
                    <Gift size={18} className="icon-purple" />
                    Programa de Indicação
                </h3>
                <HelpCircle size={14} className="icon-muted" title="Indique amigos e ganhe créditos" />
            </div>

            <div className="card-body">
                <p className="summary-text">
                    Compartilhe seu código e ganhe <strong>$25</strong> quando seu indicado gastar $50
                </p>

                {/* Referral Code Display */}
                <div className="code-section">
                    <label className="code-label">Seu Código</label>
                    <div className="code-container">
                        <code className="code-value">{referralCode || '--------'}</code>
                        <button
                            type="button"
                            onClick={handleCopyCode}
                            className={`copy-btn ${codeCopied ? 'copied' : ''}`}
                            disabled={!referralCode}
                            title={codeCopied ? 'Copiado!' : 'Copiar código'}
                        >
                            {codeCopied ? <Check size={16} /> : <Copy size={16} />}
                        </button>
                    </div>
                </div>

                {/* Referral URL Display */}
                <div className="url-section">
                    <label className="code-label">Link de Indicação</label>
                    <div className="url-container">
                        <Link size={14} className="url-icon" />
                        <span className="url-value">{referralUrl || 'Carregando...'}</span>
                        <button
                            type="button"
                            onClick={handleCopyUrl}
                            className={`copy-btn ${urlCopied ? 'copied' : ''}`}
                            disabled={!referralUrl}
                            title={urlCopied ? 'Copiado!' : 'Copiar link'}
                        >
                            {urlCopied ? <Check size={16} /> : <Copy size={16} />}
                        </button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="stats-highlight">
                    <div className="stat-box">
                        <Users size={16} className="icon-blue" />
                        <div className="stat-info">
                            <span className="value">{stats.totalReferrals}</span>
                            <span className="label">Indicações</span>
                        </div>
                    </div>
                    <div className="stat-box">
                        <DollarSign size={16} className="icon-green" />
                        <div className="stat-info">
                            <span className="value">${stats.earnedCredits.toFixed(2)}</span>
                            <span className="label">Ganhos</span>
                        </div>
                    </div>
                </div>

                <div className="info-tip">
                    <p>Novos usuários recebem <strong>$10 de crédito</strong> ao se cadastrar com seu código.</p>
                </div>
            </div>

            <style jsx>{`
                .referral-code-card {
                    background: #1c211c;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    transition: all 0.3s;
                    position: relative;
                    overflow: hidden;
                }

                .referral-code-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 100%);
                }

                .referral-code-card:hover {
                    border-color: #a855f7;
                    box-shadow: 0 4px 16px rgba(168, 85, 247, 0.15);
                }

                .referral-code-card.error {
                    border-color: #ef4444;
                }

                .referral-code-card.error::before {
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
                    font-size: 15px;
                    font-weight: 600;
                    margin: 0;
                    color: #fff;
                }

                .icon-purple { color: #a855f7; }
                .icon-muted { color: #4b5563; cursor: help; }
                .icon-green { color: #22c55e; }
                .icon-blue { color: #3b82f6; }

                .card-body {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }

                .summary-text {
                    font-size: 13px;
                    color: #9ca3af;
                    margin: 0;
                    line-height: 1.5;
                }

                .summary-text strong {
                    color: #22c55e;
                }

                .error-message {
                    font-size: 13px;
                    color: #ef4444;
                    margin: 0;
                }

                .code-section,
                .url-section {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .code-label {
                    font-size: 11px;
                    color: #6b7280;
                    text-transform: uppercase;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }

                .code-container {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: #161a16;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 12px;
                }

                .code-value {
                    flex: 1;
                    font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
                    font-size: 18px;
                    font-weight: 700;
                    color: #a855f7;
                    letter-spacing: 2px;
                    background: transparent;
                }

                .url-container {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: #161a16;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 10px 12px;
                }

                .url-icon {
                    color: #6b7280;
                    flex-shrink: 0;
                }

                .url-value {
                    flex: 1;
                    font-size: 12px;
                    color: #9ca3af;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .copy-btn {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 32px;
                    height: 32px;
                    border: none;
                    border-radius: 6px;
                    background: #a855f7;
                    color: #fff;
                    cursor: pointer;
                    transition: all 0.2s;
                    flex-shrink: 0;
                }

                .copy-btn:hover:not(:disabled) {
                    background: #9333ea;
                    transform: scale(1.05);
                }

                .copy-btn:disabled {
                    background: #374151;
                    cursor: not-allowed;
                }

                .copy-btn.copied {
                    background: #22c55e;
                }

                .stats-highlight {
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

                .info-tip {
                    background: rgba(168, 85, 247, 0.1);
                    border: 1px solid rgba(168, 85, 247, 0.2);
                    border-radius: 6px;
                    padding: 10px;
                }

                .info-tip p {
                    font-size: 11px;
                    color: #9ca3af;
                    margin: 0;
                    line-height: 1.4;
                }

                .info-tip p strong {
                    color: #a855f7;
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
            `}</style>
        </div>
    )
}

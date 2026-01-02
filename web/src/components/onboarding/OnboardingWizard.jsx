import { useState } from 'react'
import { X, ChevronRight, ChevronLeft, Rocket, Cpu, Shield, Zap, Sparkles, CheckCircle2, AlertTriangle, Database, Server, Cloud } from 'lucide-react'
import './OnboardingWizard.css'

export default function OnboardingWizard({ user, onClose, onComplete }) {
    const [step, setStep] = useState(1)
    const totalSteps = 5
    const [failoverStrategy, setFailoverStrategy] = useState('snapshot_only') // Default: Snapshot Only

    const nextStep = () => setStep(s => Math.min(s + 1, totalSteps))
    const prevStep = () => setStep(s => Math.max(s - 1, 1))

    const handleSkip = () => {
        if (onComplete) {
            onComplete()
        }
        if (onClose) {
            onClose()
        }
    }

    const handleFinish = () => {
        if (onComplete) {
            onComplete()
        }
        if (onClose) {
            onClose()
        }
    }

    const userName = user?.username?.split('@')[0] || 'usuário'

    return (
        <div className="onboarding-overlay" onClick={onClose}>
            <div className="onboarding-modal" onClick={e => e.stopPropagation()}>
                {/* Decorative background elements */}
                <div className="modal-glow"></div>
                <div className="modal-grid"></div>

                <button className="close-btn" onClick={onClose} title="Fechar">
                    <X size={18} />
                </button>

                {/* Progress indicator */}
                <div className="onboarding-progress">
                    {[...Array(totalSteps)].map((_, i) => (
                        <div key={i} className="progress-step">
                            <div className={`progress-dot ${step > i ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}>
                                {step > i + 1 ? <CheckCircle2 size={14} /> : <span>{i + 1}</span>}
                            </div>
                            {i < totalSteps - 1 && <div className={`progress-line ${step > i + 1 ? 'completed' : ''}`} />}
                        </div>
                    ))}
                </div>

                <div className="onboarding-content">
                    {step === 1 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-green">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <div className="icon-ring delay-2"></div>
                                <Rocket size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Bem-vindo à <span className="highlight">Dumont Cloud</span></h2>
                                <p className="welcome-name">{userName}!</p>
                                <p className="description">
                                    Estamos felizes em ter você aqui. Vamos configurar seu ambiente de
                                    desenvolvimento GPU em menos de <strong>2 minutos</strong>.
                                </p>
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-purple">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <Sparkles size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Economize até <span className="highlight-purple">89%</span> em GPU</h2>
                                <p className="description">
                                    Nossa plataforma usa instâncias spot inteligentes com auto-hibernação.
                                    Você paga apenas pelo tempo que realmente usar.
                                </p>
                            </div>
                            <div className="feature-cards">
                                <div className="feature-card">
                                    <div className="feature-icon"><Zap size={20} /></div>
                                    <div className="feature-text">
                                        <strong>Auto-hibernação</strong>
                                        <span>Desliga em 3 min de inatividade</span>
                                    </div>
                                </div>
                                <div className="feature-card">
                                    <div className="feature-icon"><Shield size={20} /></div>
                                    <div className="feature-text">
                                        <strong>Snapshots automáticos</strong>
                                        <span>Seus dados sempre seguros</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-orange">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <Shield size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Proteção <span className="highlight-orange">Failover</span></h2>
                                <p className="description">
                                    Escolha como proteger seus dados quando a máquina for interrompida.
                                </p>
                            </div>
                            <div className="failover-options">
                                <div
                                    className={`failover-card ${failoverStrategy === 'snapshot_only' ? 'selected' : ''}`}
                                    onClick={() => setFailoverStrategy('snapshot_only')}
                                >
                                    <div className="failover-radio">
                                        {failoverStrategy === 'snapshot_only' && <CheckCircle2 size={16} />}
                                    </div>
                                    <div className="failover-icon"><Database size={20} /></div>
                                    <div className="failover-info">
                                        <strong>Snapshot Only</strong>
                                        <span>Backup a cada 1h • Recovery em ~5min</span>
                                        <span className="failover-tag recommended">Recomendado</span>
                                    </div>
                                </div>
                                <div
                                    className={`failover-card ${failoverStrategy === 'cpu_standby' ? 'selected' : ''}`}
                                    onClick={() => setFailoverStrategy('cpu_standby')}
                                >
                                    <div className="failover-radio">
                                        {failoverStrategy === 'cpu_standby' && <CheckCircle2 size={16} />}
                                    </div>
                                    <div className="failover-icon"><Server size={20} /></div>
                                    <div className="failover-info">
                                        <strong>CPU Standby</strong>
                                        <span>CPU sempre ativa • Recovery em ~2min</span>
                                        <span className="failover-tag">+$0.02/h</span>
                                    </div>
                                </div>
                                <div
                                    className={`failover-card ${failoverStrategy === 'warm_pool' ? 'selected' : ''}`}
                                    onClick={() => setFailoverStrategy('warm_pool')}
                                >
                                    <div className="failover-radio">
                                        {failoverStrategy === 'warm_pool' && <CheckCircle2 size={16} />}
                                    </div>
                                    <div className="failover-icon"><Cloud size={20} /></div>
                                    <div className="failover-info">
                                        <strong>Warm Pool</strong>
                                        <span>GPU reservada • Recovery em ~30s</span>
                                        <span className="failover-tag premium">Premium</span>
                                    </div>
                                </div>
                                <div
                                    className={`failover-card danger ${failoverStrategy === 'none' ? 'selected' : ''}`}
                                    onClick={() => setFailoverStrategy('none')}
                                >
                                    <div className="failover-radio">
                                        {failoverStrategy === 'none' && <CheckCircle2 size={16} />}
                                    </div>
                                    <div className="failover-icon danger"><AlertTriangle size={20} /></div>
                                    <div className="failover-info">
                                        <strong>Sem Failover</strong>
                                        <span>Sem proteção • Dados podem ser perdidos</span>
                                        <span className="failover-tag danger">Perigoso</span>
                                    </div>
                                </div>
                            </div>
                            {failoverStrategy === 'none' && (
                                <div className="danger-warning">
                                    <AlertTriangle size={18} />
                                    <span>Atenção: Sem failover, você pode perder todo o trabalho se a máquina for interrompida!</span>
                                </div>
                            )}
                        </div>
                    )}

                    {step === 4 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-blue">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <Cpu size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Escolha sua <span className="highlight-blue">GPU Ideal</span></h2>
                                <p className="description">
                                    Não sabe qual GPU escolher? Use nosso <strong>AI Advisor</strong>.
                                    Ele analisa seu projeto e recomenda a melhor máquina para seu bolso.
                                </p>
                            </div>
                            <div className="gpu-preview">
                                <div className="gpu-chip">RTX 4090</div>
                                <div className="gpu-chip">A100</div>
                                <div className="gpu-chip">H100</div>
                                <div className="gpu-chip">RTX 3090</div>
                            </div>
                        </div>
                    )}

                    {step === 5 && (
                        <div className="step-content animate-in">
                            <div className="icon-container icon-green success">
                                <div className="icon-ring"></div>
                                <div className="icon-ring delay-1"></div>
                                <div className="icon-ring delay-2"></div>
                                <CheckCircle2 size={56} strokeWidth={1.5} />
                            </div>
                            <div className="text-content">
                                <h2>Tudo <span className="highlight">Pronto!</span></h2>
                                <p className="description">
                                    Agora você pode criar sua primeira máquina e começar a desenvolver
                                    diretamente no VS Code pelo browser.
                                </p>
                            </div>
                            <button className="finish-btn" onClick={handleFinish}>
                                <Rocket size={20} />
                                <span>Vamos Começar!</span>
                            </button>
                        </div>
                    )}
                </div>

                {step < totalSteps && (
                    <div className="onboarding-footer">
                        <button className="skip-link" onClick={handleSkip}>Pular</button>
                        <div className="nav-buttons">
                            {step > 1 && (
                                <button className="back-btn" onClick={prevStep}>
                                    <ChevronLeft size={18} />
                                    Voltar
                                </button>
                            )}
                            <button className="next-btn" onClick={nextStep}>
                                {step === 1 ? 'Começar' : 'Próximo'}
                                <ChevronRight size={18} />
                            </button>
                        </div>
                    </div>
                )}
            </div>

        </div>
    )
}


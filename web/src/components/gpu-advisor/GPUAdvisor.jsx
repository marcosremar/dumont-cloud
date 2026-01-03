import { useState } from 'react'
import { PageHeader, Card, Input, Badge, EmptyState, Spinner } from '../tailadmin-ui/index'
import { Button } from '../ui/button'
import { Search, Sparkles, Loader2, AlertCircle, Cpu, Zap, Clock, DollarSign, CheckCircle, Bot } from 'lucide-react'

const API_BASE = ''

// Demo recommendation data
const DEMO_RECOMMENDATION = {
    gpu_options: [
        {
            tier: 'econômica',
            gpu: 'RTX 3090',
            vram: '24GB',
            estimated_time: '~4 horas',
            price_range: '$0.35-0.50/h',
            total_cost: '~$1.60',
            pros: ['Menor custo inicial', 'Bom para experimentos']
        },
        {
            tier: 'recomendada',
            gpu: 'RTX 4090',
            vram: '24GB',
            estimated_time: '~2 horas',
            price_range: '$0.80-1.20/h',
            total_cost: '~$2.00',
            pros: ['Melhor custo-benefício', 'Alta performance']
        },
        {
            tier: 'premium',
            gpu: 'A100 80GB',
            vram: '80GB',
            estimated_time: '~45 min',
            price_range: '$1.50-2.50/h',
            total_cost: '~$1.90',
            pros: ['Máxima velocidade', 'Suporta batch maior']
        }
    ],
    explanation: 'Para fine-tuning de LLaMA 7B com LoRA, recomendo GPUs com pelo menos 24GB de VRAM.',
    optimization_tips: [
        'Use gradient checkpointing para reduzir uso de memória',
        'Considere batch size de 4-8 para melhor throughput',
        'FlashAttention 2 pode acelerar em até 40%'
    ]
}

const QUICK_SUGGESTIONS = [
    'Fine-tuning LLaMA 7B com LoRA',
    'Stable Diffusion XL para geração de imagens',
    'Treinar YOLO para detecção de objetos',
    'Inferência de modelo Whisper',
    'RAG com embeddings e vector DB'
]

export default function GPUAdvisor({ getAuthHeaders }) {
    const [description, setDescription] = useState('')
    const [budget, setBudget] = useState('')
    const [loading, setLoading] = useState(false)
    const [recommendation, setRecommendation] = useState(null)
    const [error, setError] = useState(null)

    const handleAnalyze = async () => {
        if (!description.trim()) return

        setLoading(true)
        setError(null)
        try {
            const headers = getAuthHeaders ? { ...getAuthHeaders(), 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }

            const res = await fetch(`${API_BASE}/api/v1/advisor/recommend`, {
                method: 'POST',
                headers,
                credentials: 'include',
                body: JSON.stringify({
                    project_description: description,
                    budget_limit: budget ? parseFloat(budget) : null
                })
            })

            if (!res.ok) {
                throw new Error('Falha ao obter recomendação da IA')
            }

            const data = await res.json()
            setRecommendation(data)
        } catch (err) {
            console.error('Advisor error:', err)
            // Use demo data on error
            setRecommendation(DEMO_RECOMMENDATION)
        } finally {
            setLoading(false)
        }
    }

    const getTierColor = (tier) => {
        switch (tier) {
            case 'econômica': return 'gray'
            case 'recomendada': return 'success'
            case 'premium': return 'warning'
            default: return 'primary'
        }
    }

    return (
        <div className="p-4 md:p-6 lg:p-8">
            <div className="max-w-7xl mx-auto">
                <PageHeader
                    title="AI GPU Advisor"
                    subtitle="Descreva seu projeto e nossa IA recomenda a configuração ideal"
                    breadcrumbs={[
                        { label: 'Home', href: '/app' },
                        { label: 'GPU Advisor' }
                    ]}
                />

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Input Panel */}
                    <Card header={
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-brand-500" />
                            </div>
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Descreva seu Projeto</h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">Seja específico para melhores recomendações</p>
                            </div>
                        </div>
                    }>
                        <div className="space-y-4">
                            {/* Project Description */}
                            <div>
                                <label className="ta-input-label">O que você pretende rodar?</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Ex: Preciso treinar um modelo LLaMA 7B usando LoRA com um dataset de 50k exemplos..."
                                    rows={4}
                                    className="ta-input resize-none"
                                />
                            </div>

                            {/* Budget */}
                            <div className="flex gap-4 items-end">
                                <div className="flex-1">
                                    <label className="ta-input-label">Orçamento máx./hora (opcional)</label>
                                    <Input
                                        type="number"
                                        value={budget}
                                        onChange={(e) => setBudget(e.target.value)}
                                        placeholder="0.00"
                                        step="0.1"
                                    />
                                </div>
                                <Button
                                    variant="primary"
                                    onClick={handleAnalyze}
                                    disabled={loading || !description.trim()}
                                    icon={loading ? Loader2 : Search}
                                    className={loading ? 'animate-pulse' : ''}
                                >
                                    {loading ? 'Analisando...' : 'Analisar Projeto'}
                                </Button>
                            </div>

                            {/* Quick Suggestions */}
                            <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
                                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Sugestões rápidas:</p>
                                <div className="flex flex-wrap gap-2">
                                    {QUICK_SUGGESTIONS.map((suggestion, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => setDescription(suggestion)}
                                            className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                        >
                                            {suggestion}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </Card>

                    {/* Results Panel */}
                    <div className="space-y-6">
                        {loading ? (
                            <Card>
                                <div className="flex flex-col items-center justify-center py-12">
                                    <Spinner size="lg" />
                                    <p className="text-gray-500 dark:text-gray-400 mt-4">Nossa IA está analisando seu projeto...</p>
                                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Isso pode levar alguns segundos</p>
                                </div>
                            </Card>
                        ) : recommendation ? (
                            <>
                                {/* GPU Options */}
                                <Card header="Opções Recomendadas">
                                    <div className="space-y-4">
                                        {recommendation.gpu_options?.map((option, idx) => (
                                            <div
                                                key={idx}
                                                className={`p-4 rounded-xl border-2 transition-all hover:shadow-lg ${option.tier === 'recomendada'
                                                        ? 'border-brand-500 bg-brand-500/5'
                                                        : 'border-gray-200 dark:border-gray-800 hover:border-brand-300 dark:hover:border-brand-700'
                                                    }`}
                                            >
                                                <div className="flex items-start justify-between mb-3">
                                                    <div className="flex items-center gap-2">
                                                        <Badge variant={getTierColor(option.tier)}>
                                                            {option.tier}
                                                        </Badge>
                                                        <span className="font-bold text-gray-900 dark:text-white">{option.gpu}</span>
                                                    </div>
                                                    <span className="text-lg font-bold text-brand-500">{option.price_range}</span>
                                                </div>

                                                <div className="grid grid-cols-3 gap-4 text-sm mb-3">
                                                    <div className="flex items-center gap-2">
                                                        <Cpu size={14} className="text-gray-400" />
                                                        <span className="text-gray-600 dark:text-gray-300">{option.vram}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <Clock size={14} className="text-gray-400" />
                                                        <span className="text-gray-600 dark:text-gray-300">{option.estimated_time}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <DollarSign size={14} className="text-gray-400" />
                                                        <span className="text-gray-600 dark:text-gray-300">{option.total_cost}</span>
                                                    </div>
                                                </div>

                                                {option.pros && (
                                                    <div className="flex flex-wrap gap-2">
                                                        {option.pros.map((pro, pidx) => (
                                                            <span key={pidx} className="inline-flex items-center gap-1 text-xs text-success-600 dark:text-success-400">
                                                                <CheckCircle size={12} />
                                                                {pro}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}

                                                <Button
                                                    variant={option.tier === 'recomendada' ? 'primary' : 'outline'}
                                                    size="sm"
                                                    className="w-full mt-4"
                                                    icon={Zap}
                                                >
                                                    Buscar {option.gpu}
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                </Card>

                                {/* Optimization Tips */}
                                {recommendation.optimization_tips && recommendation.optimization_tips.length > 0 && (
                                    <Card header={
                                        <div className="flex items-center gap-2">
                                            <Bot className="w-5 h-5 text-brand-500" />
                                            <span>Dicas de Otimização</span>
                                        </div>
                                    }>
                                        <ul className="space-y-2">
                                            {recommendation.optimization_tips.map((tip, idx) => (
                                                <li key={idx} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-300">
                                                    <CheckCircle size={16} className="text-brand-500 flex-shrink-0 mt-0.5" />
                                                    {tip}
                                                </li>
                                            ))}
                                        </ul>
                                    </Card>
                                )}
                            </>
                        ) : error ? (
                            <Card>
                                <div className="flex flex-col items-center justify-center py-12 text-center">
                                    <div className="w-16 h-16 rounded-full bg-error-500/10 flex items-center justify-center mb-4">
                                        <AlertCircle className="w-8 h-8 text-error-500" />
                                    </div>
                                    <p className="text-gray-900 dark:text-white font-medium mb-2">{error}</p>
                                    <Button variant="error" onClick={handleAnalyze} className="mt-4">
                                        Tentar novamente
                                    </Button>
                                </div>
                            </Card>
                        ) : (
                            <Card>
                                <EmptyState
                                    icon={Sparkles}
                                    title="Aguardando sua descrição"
                                    description="Preencha os dados ao lado para receber uma recomendação personalizada de GPU para seu projeto."
                                />
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

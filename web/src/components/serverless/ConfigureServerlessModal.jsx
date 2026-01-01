import { useState } from 'react'
import {
  X,
  Zap,
  DollarSign,
  Rocket,
  Info,
  Gauge,
  Clock,
  Target,
  CheckCircle2,
} from 'lucide-react'
import {
  AlertDialog,
  AlertDialogContent,
  Badge,
  Button,
  Input,
} from '../tailadmin-ui'

const MODES = [
  {
    id: 'fast',
    icon: Zap,
    title: 'Fast',
    subtitle: 'CPU Standby',
    description: 'Recovery instantâneo com CPU sempre ativa',
    recovery: '<1s',
    idleCost: '$0.01/hr',
    color: 'blue',
  },
  {
    id: 'economic',
    icon: DollarSign,
    title: 'Economic',
    subtitle: 'Pause/Resume',
    description: 'Pausa automática com recovery rápido',
    recovery: '~7s',
    idleCost: '$0.005/hr',
    color: 'green',
    recommended: true,
  },
  {
    id: 'spot',
    icon: Rocket,
    title: 'Spot',
    subtitle: 'Interruptible',
    description: 'Preço spot com auto-failover',
    recovery: '~30s',
    savings: '60-70%',
    color: 'purple',
  },
]

export default function ConfigureServerlessModal({ instance, onClose, onSave }) {
  const [selectedMode, setSelectedMode] = useState('economic')
  const [config, setConfig] = useState({
    idle_timeout_seconds: 60,
    gpu_threshold_percent: 5,
    max_spot_price: 0.50,
    spot_template_id: null,
  })

  const currentMode = MODES.find(m => m.id === selectedMode)

  const handleSave = () => {
    onSave({
      mode: selectedMode,
      ...config,
    })
  }

  const getModeColor = (modeId) => {
    const colors = {
      fast: 'border-blue-500 bg-blue-500/10 text-blue-400',
      economic: 'border-brand-500 bg-brand-500/10 text-brand-400',
      spot: 'border-purple-500 bg-purple-500/10 text-purple-400',
    }
    return colors[modeId] || 'border-white/10 bg-white/5 text-gray-400'
  }

  return (
    <AlertDialog open={true} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-dark-surface-card border-b border-white/10 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-brand-400" />
              Configurar Serverless
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Instância #{instance?.id} - {instance?.gpu_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content - com scroll */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Mode Selection */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">Escolha o Modo Serverless</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {MODES.map((mode) => {
                const Icon = mode.icon
                const isSelected = selectedMode === mode.id

                return (
                  <button
                    key={mode.id}
                    onClick={() => setSelectedMode(mode.id)}
                    className={`relative p-4 rounded-xl border-2 transition-all text-left ${
                      isSelected
                        ? getModeColor(mode.id)
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    {mode.recommended && (
                      <div className="absolute -top-2 -right-2">
                        <Badge className="bg-brand-500 text-white text-xs font-bold">
                          Recomendado
                        </Badge>
                      </div>
                    )}

                    <div className="flex items-start gap-3 mb-3">
                      <div className={`p-2 rounded-lg ${
                        isSelected
                          ? getModeColor(mode.id)
                          : 'bg-white/5'
                      }`}>
                        <Icon className={`w-5 h-5 ${
                          isSelected ? '' : 'text-gray-400'
                        }`} />
                      </div>
                      <div className="flex-1">
                        <h4 className={`font-bold ${
                          isSelected ? 'text-white' : 'text-gray-400'
                        }`}>
                          {mode.title}
                        </h4>
                        <p className="text-xs text-gray-500">{mode.subtitle}</p>
                      </div>
                    </div>

                    <p className="text-xs text-gray-400 mb-3">
                      {mode.description}
                    </p>

                    <div className="space-y-1.5 text-xs">
                      {mode.recovery && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Recovery:</span>
                          <span className={isSelected ? 'text-white' : 'text-gray-400'}>
                            {mode.recovery}
                          </span>
                        </div>
                      )}
                      {mode.idleCost && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Idle:</span>
                          <span className="text-brand-400 font-medium">
                            {mode.idleCost}
                          </span>
                        </div>
                      )}
                      {mode.savings && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Economia:</span>
                          <span className="text-brand-400 font-bold">
                            {mode.savings}
                          </span>
                        </div>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Mode-specific Configuration */}
          <div className="p-4 rounded-lg bg-dark-surface-secondary border border-white/10">
            <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
              <Info className="w-4 h-4 text-brand-400" />
              Configurações do Modo {currentMode?.title}
            </h4>

            {/* Fast Mode Config */}
            {selectedMode === 'fast' && (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <div className="flex items-start gap-2 text-xs text-blue-300">
                    <Zap className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium mb-1">CPU Standby Ativo</p>
                      <ul className="space-y-0.5 text-blue-400/80">
                        <li>• CPU sempre ativa, GPU pausada quando idle</li>
                        <li>• Recovery instantâneo (&lt;1 segundo)</li>
                        <li>• Sync contínuo com storage</li>
                        <li>• Custo: $0.01/hr quando idle</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Gauge className="w-4 h-4 inline mr-1" />
                    Threshold de GPU Idle
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="1"
                      max="20"
                      value={config.gpu_threshold_percent}
                      onChange={(e) => setConfig({ ...config, gpu_threshold_percent: parseInt(e.target.value) })}
                      className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-500"
                    />
                    <span className="text-white font-bold w-16 text-right">
                      {config.gpu_threshold_percent}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    GPU pausará quando uso ficar abaixo de {config.gpu_threshold_percent}%
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Clock className="w-4 h-4 inline mr-1" />
                    Timeout de Idle
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="30"
                      max="600"
                      step="30"
                      value={config.idle_timeout_seconds}
                      onChange={(e) => setConfig({ ...config, idle_timeout_seconds: parseInt(e.target.value) })}
                      className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-500"
                    />
                    <span className="text-white font-bold w-20 text-right">
                      {config.idle_timeout_seconds}s
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    GPU pausará após {config.idle_timeout_seconds} segundos idle
                  </p>
                </div>
              </div>
            )}

            {/* Economic Mode Config */}
            {selectedMode === 'economic' && (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-brand-500/10 border border-brand-500/20">
                  <div className="flex items-start gap-2 text-xs text-brand-300">
                    <DollarSign className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium mb-1">Pause/Resume Automático</p>
                      <ul className="space-y-0.5 text-brand-400/80">
                        <li>• Pausa total da instância quando idle</li>
                        <li>• Recovery em ~7 segundos</li>
                        <li>• Máxima economia em idle ($0.005/hr)</li>
                        <li>• Ideal para uso intermitente</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Gauge className="w-4 h-4 inline mr-1" />
                    Threshold de GPU Idle
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="1"
                      max="20"
                      value={config.gpu_threshold_percent}
                      onChange={(e) => setConfig({ ...config, gpu_threshold_percent: parseInt(e.target.value) })}
                      className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-500"
                    />
                    <span className="text-white font-bold w-16 text-right">
                      {config.gpu_threshold_percent}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Instância pausará quando GPU ficar abaixo de {config.gpu_threshold_percent}%
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Clock className="w-4 h-4 inline mr-1" />
                    Timeout de Idle
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="30"
                      max="600"
                      step="30"
                      value={config.idle_timeout_seconds}
                      onChange={(e) => setConfig({ ...config, idle_timeout_seconds: parseInt(e.target.value) })}
                      className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-500"
                    />
                    <span className="text-white font-bold w-20 text-right">
                      {config.idle_timeout_seconds}s
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Instância pausará após {config.idle_timeout_seconds} segundos idle
                  </p>
                </div>
              </div>
            )}

            {/* Spot Mode Config */}
            {selectedMode === 'spot' && (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  <div className="flex items-start gap-2 text-xs text-purple-300">
                    <Rocket className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium mb-1">Spot Interruptible</p>
                      <ul className="space-y-0.5 text-purple-400/80">
                        <li>• Economia de 60-70% vs On-Demand</li>
                        <li>• GPU pode ser interrompida a qualquer momento</li>
                        <li>• Auto-restart com regional volume failover</li>
                        <li>• Recovery em ~30 segundos</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Target className="w-4 h-4 inline mr-1" />
                    Template Spot (Regional Volume)
                  </label>
                  <select
                    value={config.spot_template_id || ''}
                    onChange={(e) => setConfig({ ...config, spot_template_id: e.target.value || null })}
                    className="w-full px-4 py-2.5 rounded-lg bg-dark-surface-secondary border border-white/10 text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                  >
                    <option value="">Criar novo template</option>
                    <option value="tpl_abc123">spot_tpl_12345_1703... (US, 2.3GB)</option>
                    <option value="tpl_def456">spot_tpl_67890_1703... (EU, 5.1GB)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Template será usado para failover quando GPU for interrompida
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <DollarSign className="w-4 h-4 inline mr-1" />
                    Preço Máximo (Bid)
                  </label>
                  <div className="flex items-center gap-4">
                    <Input
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="2.00"
                      value={config.max_spot_price}
                      onChange={(e) => setConfig({ ...config, max_spot_price: parseFloat(e.target.value) || 0.50 })}
                      className="flex-1"
                    />
                    <span className="text-gray-500">/hora</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Máquina será pausada se preço spot ultrapassar este valor
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Gauge className="w-4 h-4 inline mr-1" />
                    Threshold de GPU Idle
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="1"
                      max="20"
                      value={config.gpu_threshold_percent}
                      onChange={(e) => setConfig({ ...config, gpu_threshold_percent: parseInt(e.target.value) })}
                      className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-500"
                    />
                    <span className="text-white font-bold w-16 text-right">
                      {config.gpu_threshold_percent}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Destruir instância quando GPU ficar abaixo de {config.gpu_threshold_percent}%
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    <Clock className="w-4 h-4 inline mr-1" />
                    Timeout de Idle
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="30"
                      max="600"
                      step="30"
                      value={config.idle_timeout_seconds}
                      onChange={(e) => setConfig({ ...config, idle_timeout_seconds: parseInt(e.target.value) })}
                      className="flex-1 h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand-500"
                    />
                    <span className="text-white font-bold w-20 text-right">
                      {config.idle_timeout_seconds}s
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Destruir instância após {config.idle_timeout_seconds} segundos idle
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Estimated Savings */}
          <div className="p-4 rounded-lg bg-brand-500/10 border border-brand-500/20">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-white">Estimativa de Economia</h4>
              <DollarSign className="w-4 h-4 text-brand-400" />
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Custo normal (24h):</span>
                <span className="font-bold text-white">$7.44</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Com {currentMode?.title} (estimado):</span>
                <span className="font-bold text-brand-400">
                  {selectedMode === 'spot' ? '$2.23' : selectedMode === 'economic' ? '$3.72' : '$5.58'}
                </span>
              </div>
              <div className="flex justify-between text-brand-400 pt-2 border-t border-white/10">
                <span>Economia mensal:</span>
                <span className="font-bold">
                  {selectedMode === 'spot' ? '70%' : selectedMode === 'economic' ? '50%' : '25%'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-dark-surface-card border-t border-white/10 px-6 py-4 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={onClose}
          >
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            icon={CheckCircle2}
          >
            Ativar Serverless {currentMode?.title}
          </Button>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}

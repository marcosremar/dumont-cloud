import { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle,
  Server,
  Cpu,
  CheckCircle,
  RefreshCw,
  ArrowRight,
  X,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * FailoverNotification - Notificacao em tempo real de eventos de failover
 *
 * Mostra uma notificacao quando:
 * - GPU cai e failover para CPU inicia
 * - Failover para CPU completa
 * - Nova GPU e provisionada (recovery)
 * - Recovery para GPU completa
 *
 * Uso:
 *   <FailoverNotification machineId={12345} />
 */
export default function FailoverNotification({ machineId, onClose }) {
  const [event, setEvent] = useState(null)
  const [isVisible, setIsVisible] = useState(false)
  const [phase, setPhase] = useState('idle') // idle, failover, recovery, complete

  // Poll for failover events
  useEffect(() => {
    if (!machineId) return

    let mounted = true
    let lastEventId = null

    const checkForEvents = async () => {
      try {
        const response = await fetch(`/api/v1/standby/failover/active`)
        const data = await response.json()

        if (!mounted) return

        // Find event for this machine
        const activeEvent = data.failovers?.find(
          e => e.gpu_instance_id === machineId
        )

        if (activeEvent && activeEvent.failover_id !== lastEventId) {
          lastEventId = activeEvent.failover_id
          setEvent(activeEvent)
          setPhase(activeEvent.phase)
          setIsVisible(true)
        } else if (!activeEvent && phase !== 'idle') {
          // Event completed, show completion state briefly
          setTimeout(() => {
            setIsVisible(false)
            setPhase('idle')
          }, 5000)
        }
      } catch (error) {
        console.error('Failed to check failover events:', error)
      }
    }

    // Initial check
    checkForEvents()

    // Poll every 2 seconds
    const interval = setInterval(checkForEvents, 2000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [machineId, phase])

  // Auto-dismiss after completion
  useEffect(() => {
    if (phase === 'complete') {
      const timer = setTimeout(() => {
        setIsVisible(false)
        setPhase('idle')
      }, 10000)
      return () => clearTimeout(timer)
    }
  }, [phase])

  const handleDismiss = () => {
    setIsVisible(false)
    if (onClose) onClose()
  }

  if (!isVisible || !event) return null

  const getPhaseInfo = () => {
    switch (event.phase) {
      case 'detecting':
        return {
          icon: AlertTriangle,
          title: 'Detectando falha de GPU...',
          description: 'Verificando status da conexao',
          color: 'yellow',
          animate: true,
        }
      case 'gpu_lost':
        return {
          icon: WifiOff,
          title: 'GPU Desconectada',
          description: 'Iniciando failover para CPU Standby',
          color: 'red',
          animate: true,
        }
      case 'failover_to_cpu':
        return {
          icon: Cpu,
          title: 'Trocando para CPU Standby',
          description: 'Seu trabalho esta seguro. Redirecionando conexao...',
          color: 'blue',
          animate: true,
        }
      case 'searching_gpu':
        return {
          icon: Server,
          title: 'Buscando Nova GPU',
          description: 'Procurando GPU disponivel para recovery',
          color: 'purple',
          animate: true,
        }
      case 'provisioning':
        return {
          icon: RefreshCw,
          title: 'Provisionando Nova GPU',
          description: 'GPU encontrada. Preparando ambiente...',
          color: 'blue',
          animate: true,
        }
      case 'restoring':
        return {
          icon: ArrowRight,
          title: 'Restaurando Dados',
          description: 'Sincronizando dados do CPU Standby para nova GPU',
          color: 'blue',
          animate: true,
        }
      case 'complete':
        return {
          icon: CheckCircle,
          title: 'Failover Completo!',
          description: event.new_gpu_id
            ? `Nova GPU ativa (ID: ${event.new_gpu_id})`
            : 'Conectado ao CPU Standby',
          color: 'green',
          animate: false,
        }
      case 'failed':
        return {
          icon: AlertTriangle,
          title: 'Failover com Problemas',
          description: 'Verifique o status da maquina',
          color: 'red',
          animate: false,
        }
      default:
        return {
          icon: RefreshCw,
          title: 'Processando...',
          description: event.phase,
          color: 'gray',
          animate: true,
        }
    }
  }

  const phaseInfo = getPhaseInfo()
  const Icon = phaseInfo.icon

  const colorClasses = {
    yellow: {
      bg: 'bg-yellow-500/10 border-yellow-500/30',
      icon: 'text-yellow-400',
      title: 'text-yellow-300',
      desc: 'text-yellow-200/70',
    },
    red: {
      bg: 'bg-red-500/10 border-red-500/30',
      icon: 'text-red-400',
      title: 'text-red-300',
      desc: 'text-red-200/70',
    },
    blue: {
      bg: 'bg-blue-500/10 border-blue-500/30',
      icon: 'text-blue-400',
      title: 'text-blue-300',
      desc: 'text-blue-200/70',
    },
    purple: {
      bg: 'bg-purple-500/10 border-purple-500/30',
      icon: 'text-purple-400',
      title: 'text-purple-300',
      desc: 'text-purple-200/70',
    },
    green: {
      bg: 'bg-green-500/10 border-green-500/30',
      icon: 'text-green-400',
      title: 'text-green-300',
      desc: 'text-green-200/70',
    },
    gray: {
      bg: 'bg-gray-500/10 border-gray-500/30',
      icon: 'text-gray-400',
      title: 'text-gray-300',
      desc: 'text-gray-200/70',
    },
  }

  const colors = colorClasses[phaseInfo.color]

  return (
    <div
      className={cn(
        'fixed bottom-4 right-4 z-50 max-w-sm',
        'animate-in slide-in-from-right-5 duration-300'
      )}
    >
      <div
        className={cn(
          'rounded-lg border p-4 shadow-xl backdrop-blur-sm',
          colors.bg
        )}
      >
        <div className="flex items-start gap-3">
          <div className={cn('mt-0.5', colors.icon)}>
            <Icon
              className={cn('w-5 h-5', phaseInfo.animate && 'animate-pulse')}
            />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <h3 className={cn('font-semibold text-sm', colors.title)}>
                {phaseInfo.title}
              </h3>
              <button
                onClick={handleDismiss}
                className="text-gray-400 hover:text-gray-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className={cn('text-xs mt-1', colors.desc)}>
              {phaseInfo.description}
            </p>

            {/* Progress bar for active phases */}
            {phaseInfo.animate && (
              <div className="mt-3 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full animate-pulse',
                    phaseInfo.color === 'red' && 'bg-red-500',
                    phaseInfo.color === 'yellow' && 'bg-yellow-500',
                    phaseInfo.color === 'blue' && 'bg-blue-500',
                    phaseInfo.color === 'purple' && 'bg-purple-500',
                    phaseInfo.color === 'green' && 'bg-green-500'
                  )}
                  style={{ width: '50%', animation: 'pulse 1.5s infinite' }}
                />
              </div>
            )}

            {/* Timing info */}
            {event.phase_timings_ms && (
              <div className="mt-2 text-[10px] text-gray-400">
                Tempo total:{' '}
                {Object.values(event.phase_timings_ms).reduce((a, b) => a + b, 0)}ms
              </div>
            )}

            {/* VS Code specific message */}
            {(event.phase === 'failover_to_cpu' || event.phase === 'complete') && (
              <div className="mt-2 p-2 rounded bg-black/20 text-[10px] text-gray-300">
                <strong>VS Code:</strong> Se estiver conectado, a conexao sera
                redirecionada automaticamente.
                {event.phase === 'complete' && ' Reconecte se necessario.'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Hook para usar a notificacao de failover
 */
export function useFailoverNotification(machineId) {
  const [showNotification, setShowNotification] = useState(false)
  const [currentEvent, setCurrentEvent] = useState(null)

  useEffect(() => {
    if (!machineId) return

    const checkEvents = async () => {
      try {
        const response = await fetch(`/api/v1/standby/failover/active`)
        const data = await response.json()

        const event = data.failovers?.find(e => e.gpu_instance_id === machineId)

        if (event) {
          setCurrentEvent(event)
          setShowNotification(true)
        }
      } catch (error) {
        console.error('Failed to check failover:', error)
      }
    }

    const interval = setInterval(checkEvents, 3000)
    checkEvents()

    return () => clearInterval(interval)
  }, [machineId])

  const dismissNotification = useCallback(() => {
    setShowNotification(false)
  }, [])

  return {
    showNotification,
    currentEvent,
    dismissNotification,
  }
}

/**
 * Componente de banner para mostrar na pagina de maquinas
 */
export function FailoverBanner({ machines }) {
  const [activeFailovers, setActiveFailovers] = useState([])

  useEffect(() => {
    const checkFailovers = async () => {
      try {
        const response = await fetch(`/api/v1/standby/failover/active`)
        const data = await response.json()
        setActiveFailovers(data.failovers || [])
      } catch (error) {
        console.error('Failed to check failovers:', error)
      }
    }

    const interval = setInterval(checkFailovers, 2000)
    checkFailovers()

    return () => clearInterval(interval)
  }, [])

  if (activeFailovers.length === 0) return null

  return (
    <div className="mb-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-yellow-400 animate-pulse" />
        <span className="text-sm font-medium text-yellow-300">
          Failover em andamento ({activeFailovers.length} maquina{activeFailovers.length > 1 ? 's' : ''})
        </span>
      </div>
      <div className="mt-2 space-y-1">
        {activeFailovers.map(event => {
          const machine = machines?.find(m => m.id === event.gpu_instance_id)
          return (
            <div key={event.failover_id} className="text-xs text-yellow-200/70">
              <span className="font-medium text-yellow-200">
                {machine?.gpu_name || `GPU #${event.gpu_instance_id}`}
              </span>
              : {event.phase.replace('_', ' ')}
            </div>
          )
        })}
      </div>
    </div>
  )
}

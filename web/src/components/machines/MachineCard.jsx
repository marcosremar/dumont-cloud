import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Card,
  Badge,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '../tailadmin-ui'
import {
  ChevronDown,
  MoreVertical,
  Play,
  Cpu,
  Code,
  Settings,
  Trash2,
  Copy,
  Pause,
  Save,
  RefreshCw,
  Upload,
  ArrowLeftRight,
  Check,
  Cloud,
  Shield,
  Layers,
  X,
  MapPin,
  Globe,
  DollarSign,
  Zap,
  Server,
  Info,
  Clock,
  Hash,
  Camera,
  Activity,
} from 'lucide-react'
import HibernationConfigModal from '../HibernationConfigModal'
import SnapshotConfigModal from '../SnapshotConfigModal'
import FailoverMigrationModal from '../FailoverMigrationModal'
import SparklineChart from '../ui/SparklineChart'
import InstanceDetailsModal from './InstanceDetailsModal'
import ReliabilityDetailsModal from './ReliabilityDetailsModal'

// Failover strategies base info (costs calculated dynamically)
const FAILOVER_STRATEGIES_BASE = {
  disabled: { label: 'Desabilitado', color: 'gray', description: 'Sem proteção', recovery: null },
  cpu_standby: { label: 'CPU Standby', color: 'blue', description: 'GCP e2-medium', recovery: '~10-20min' },
  warm_pool: { label: 'GPU Warm Pool', color: 'green', description: 'GPU reservada', recovery: '~30-60s' },
  regional_volume: { label: 'Regional Volume', color: 'purple', description: 'Volume + Spot GPU', recovery: '~2-5min' },
  snapshot: { label: 'Snapshot', color: 'orange', description: 'Backblaze B2', recovery: '~5-10min' },
}

// Calculate real costs based on machine data
const calculateStrategyCosts = (machine) => {
  const gpuCost = machine.dph_total || 0
  const cpuStandbyCost = machine.cpu_standby?.dph_total || 0.01 // Real cost from GCP

  // Warm pool: ~50% of GPU cost (keeping a standby GPU ready)
  const warmPoolCost = gpuCost * 0.5

  // Regional volume: Storage cost (~$0.02/h for 50GB) + average spot GPU (~30% of on-demand)
  const volumeStorageCost = 0.02
  const spotGpuEstimate = gpuCost * 0.3
  const regionalVolumeCost = volumeStorageCost + spotGpuEstimate

  // Snapshot: Only storage cost on B2 (~$0.005/GB/month = ~$0.000007/GB/hour)
  // For 50GB workspace = ~$0.0003/hour, round to $0.01 minimum
  const snapshotCost = 0.01

  return {
    disabled: 0,
    cpu_standby: cpuStandbyCost,
    warm_pool: warmPoolCost,
    regional_volume: regionalVolumeCost,
    snapshot: snapshotCost,
  }
}

export default function MachineCard({
  machine,
  onDestroy,
  onStart,
  onPause,
  onRestoreToNew,
  onSnapshot,
  onRestore,
  onMigrate,
  onSimulateFailover,
  syncStatus,
  syncStats,
  failoverProgress,
  isNew = false, // Highlight animation for newly created machines
  isDeleting = false, // Loading animation for deleting machines
}) {
  const [showConfigModal, setShowConfigModal] = useState(false)
  const [showSnapshotConfigModal, setShowSnapshotConfigModal] = useState(false)
  const [showSSHInstructions, setShowSSHInstructions] = useState(false)
  const [alertDialog, setAlertDialog] = useState({ open: false, title: '', description: '', action: null })
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false)
  const [copiedField, setCopiedField] = useState(null)
  const [copyAnnouncement, setCopyAnnouncement] = useState('')
  const [failoverAnnouncement, setFailoverAnnouncement] = useState('')
  const [showBackupInfo, setShowBackupInfo] = useState(false)
  const [showFailoverMigration, setShowFailoverMigration] = useState(false)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [showReliabilityModal, setShowReliabilityModal] = useState(false)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [showStrategyMenu, setShowStrategyMenu] = useState(false)
  const [focusedStrategyIndex, setFocusedStrategyIndex] = useState(0)
  const strategyMenuRef = useRef(null)
  const strategyButtonRefs = useRef([])
  const strategyTriggerRef = useRef(null)
  const backupBadgeRef = useRef(null)
  const backupPopupRef = useRef(null)

  // Strategy keys for keyboard navigation
  const strategyKeys = Object.keys(FAILOVER_STRATEGIES_BASE)

  // Handle keyboard navigation for failover strategy dropdown
  const handleStrategyKeyDown = useCallback((e) => {
    if (!showStrategyMenu) return

    switch (e.key) {
      case 'Escape':
        e.preventDefault()
        setShowStrategyMenu(false)
        setFocusedStrategyIndex(0)
        // Return focus to trigger button
        strategyTriggerRef.current?.focus()
        break
      case 'ArrowDown':
        e.preventDefault()
        setFocusedStrategyIndex((prev) => {
          const next = prev < strategyKeys.length - 1 ? prev + 1 : 0
          strategyButtonRefs.current[next]?.focus()
          return next
        })
        break
      case 'ArrowUp':
        e.preventDefault()
        setFocusedStrategyIndex((prev) => {
          const next = prev > 0 ? prev - 1 : strategyKeys.length - 1
          strategyButtonRefs.current[next]?.focus()
          return next
        })
        break
      case 'Tab':
        e.preventDefault()
        // Trap focus within dropdown
        if (e.shiftKey) {
          setFocusedStrategyIndex((prev) => {
            const next = prev > 0 ? prev - 1 : strategyKeys.length - 1
            strategyButtonRefs.current[next]?.focus()
            return next
          })
        } else {
          setFocusedStrategyIndex((prev) => {
            const next = prev < strategyKeys.length - 1 ? prev + 1 : 0
            strategyButtonRefs.current[next]?.focus()
            return next
          })
        }
        break
      case 'Enter':
      case ' ':
        // Enter/Space selects the focused option (handled by button's onClick)
        // No need to prevent default here as the button will handle it
        break
      case 'Home':
        e.preventDefault()
        setFocusedStrategyIndex(0)
        strategyButtonRefs.current[0]?.focus()
        break
      case 'End':
        e.preventDefault()
        const lastIndex = strategyKeys.length - 1
        setFocusedStrategyIndex(lastIndex)
        strategyButtonRefs.current[lastIndex]?.focus()
        break
      default:
        break
    }
  }, [showStrategyMenu, strategyKeys.length])

  // Focus first option when dropdown opens
  useEffect(() => {
    if (showStrategyMenu) {
      // Reset to first option and focus it
      setFocusedStrategyIndex(0)
      // Use setTimeout to ensure the dropdown is rendered before focusing
      setTimeout(() => {
        strategyButtonRefs.current[0]?.focus()
      }, 0)
    }
  }, [showStrategyMenu])

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showStrategyMenu) return

    const handleClickOutside = (event) => {
      if (
        strategyMenuRef.current &&
        !strategyMenuRef.current.contains(event.target) &&
        strategyTriggerRef.current &&
        !strategyTriggerRef.current.contains(event.target)
      ) {
        setShowStrategyMenu(false)
        setFocusedStrategyIndex(0)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showStrategyMenu])

  // Handle keyboard navigation for backup info popup
  const handleBackupPopupKeyDown = useCallback((e) => {
    if (!showBackupInfo) return

    if (e.key === 'Escape') {
      e.preventDefault()
      setShowBackupInfo(false)
      // Return focus to trigger badge
      backupBadgeRef.current?.focus()
    }
  }, [showBackupInfo])

  // Close backup popup when clicking outside
  useEffect(() => {
    if (!showBackupInfo) return

    const handleClickOutside = (event) => {
      if (
        backupPopupRef.current &&
        !backupPopupRef.current.contains(event.target) &&
        backupBadgeRef.current &&
        !backupBadgeRef.current.contains(event.target)
      ) {
        setShowBackupInfo(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showBackupInfo])
  const [focusedStrategyIndex, setFocusedStrategyIndex] = useState(-1)
  const strategyMenuRef = useRef(null)
  const strategyItemRefs = useRef([])
  const backupInfoTriggerRef = useRef(null)
  const backupInfoCloseRef = useRef(null)

  // Get current failover strategy and calculate real costs
  const currentStrategy = machine.failover_strategy || (machine.cpu_standby?.enabled ? 'cpu_standby' : 'disabled')

  // Strategy keys for keyboard navigation
  const strategyKeys = Object.keys(FAILOVER_STRATEGIES_BASE)

  // Handle keyboard navigation for failover strategy dropdown
  const handleStrategyMenuKeyDown = useCallback((e) => {
    if (!showStrategyMenu) return

    const itemCount = strategyKeys.length

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setFocusedStrategyIndex(prev => {
          const next = prev < itemCount - 1 ? prev + 1 : 0
          return next
        })
        break
      case 'ArrowUp':
        e.preventDefault()
        setFocusedStrategyIndex(prev => {
          const next = prev > 0 ? prev - 1 : itemCount - 1
          return next
        })
        break
      case 'Enter':
      case ' ':
        e.preventDefault()
        if (focusedStrategyIndex >= 0 && focusedStrategyIndex < itemCount) {
          // Select the focused strategy
          // TODO: Call API to change strategy
          setShowStrategyMenu(false)
          setFocusedStrategyIndex(-1)
        }
        break
      case 'Escape':
        e.preventDefault()
        setShowStrategyMenu(false)
        setFocusedStrategyIndex(-1)
        break
      case 'Tab':
        // Close menu and allow normal tab behavior
        setShowStrategyMenu(false)
        setFocusedStrategyIndex(-1)
        break
      case 'Home':
        e.preventDefault()
        setFocusedStrategyIndex(0)
        break
      case 'End':
        e.preventDefault()
        setFocusedStrategyIndex(itemCount - 1)
        break
      default:
        break
    }
  }, [showStrategyMenu, focusedStrategyIndex, strategyKeys.length])

  // Focus the appropriate item when focusedStrategyIndex changes
  useEffect(() => {
    if (showStrategyMenu && focusedStrategyIndex >= 0 && strategyItemRefs.current[focusedStrategyIndex]) {
      strategyItemRefs.current[focusedStrategyIndex].focus()
    }
  }, [focusedStrategyIndex, showStrategyMenu])

  // Set initial focus when menu opens
  useEffect(() => {
    if (showStrategyMenu) {
      // Find the index of the current strategy
      const currentIndex = strategyKeys.indexOf(currentStrategy)
      setFocusedStrategyIndex(currentIndex >= 0 ? currentIndex : 0)
    } else {
      setFocusedStrategyIndex(-1)
    }
  }, [showStrategyMenu, currentStrategy, strategyKeys])

  // Close backup info popup and return focus to trigger
  const closeBackupInfo = useCallback(() => {
    setShowBackupInfo(false)
    // Return focus to the trigger element
    if (backupInfoTriggerRef.current) {
      backupInfoTriggerRef.current.focus()
    }
  }, [])

  // Focus close button when backup info popup opens
  useEffect(() => {
    if (showBackupInfo && backupInfoCloseRef.current) {
      backupInfoCloseRef.current.focus()
    }
  }, [showBackupInfo])

  // Handle Escape key to close backup info popup
  useEffect(() => {
    if (!showBackupInfo) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        closeBackupInfo()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showBackupInfo, closeBackupInfo])

  const strategyCosts = calculateStrategyCosts(machine)
  const strategyInfo = FAILOVER_STRATEGIES_BASE[currentStrategy] || FAILOVER_STRATEGIES_BASE.disabled
  const currentStrategyCost = strategyCosts[currentStrategy] || 0

  const isInFailover = failoverProgress && failoverProgress.phase !== 'idle'

  // Generate announcements for failover progress changes
  useEffect(() => {
    if (!failoverProgress || failoverProgress.phase === 'idle') {
      setFailoverAnnouncement('')
      return
    }

    const phaseAnnouncements = {
      gpu_lost: 'Failover iniciado: GPU interrompida, preparando recuperação',
      failover_active: 'Failover para CPU Standby em andamento',
      searching: 'Buscando nova GPU disponível',
      provisioning: `Provisionando ${failoverProgress.newGpu || 'nova GPU'}`,
      restoring: 'Restaurando dados para a nova GPU',
      complete: `Failover concluído com sucesso${failoverProgress.metrics?.total_time_ms ? ` em ${(failoverProgress.metrics.total_time_ms / 1000).toFixed(1)} segundos` : ''}`
    }

    const announcement = phaseAnnouncements[failoverProgress.phase]
    if (announcement) {
      setFailoverAnnouncement(announcement)
    }
  }, [failoverProgress?.phase, failoverProgress?.newGpu, failoverProgress?.metrics?.total_time_ms])

  // Timer for loading elapsed time
  useEffect(() => {
    const loadingStates = ['loading', 'creating', 'starting', 'pending', 'provisioning', 'configuring']
    const status = machine.actual_status || 'stopped'
    const isLoading = loadingStates.includes(status)

    if (isLoading) {
      const startTime = machine.created_at ? new Date(machine.created_at).getTime() : Date.now()
      const updateElapsed = () => {
        const now = Date.now()
        setElapsedTime(Math.floor((now - startTime) / 1000))
      }
      updateElapsed()
      const interval = setInterval(updateElapsed, 1000)
      return () => clearInterval(interval)
    } else {
      setElapsedTime(0)
    }
  }, [machine.actual_status, machine.created_at])

  const formatElapsedTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (mins > 0) return `${mins}m ${secs}s`
    return `${secs}s`
  }

  const [gpuHistory] = useState(() => Array.from({ length: 15 }, () => Math.random() * 40 + 30))
  const [memHistory] = useState(() => Array.from({ length: 15 }, () => Math.random() * 30 + 40))

  const gpuUtil = machine.gpu_util ? Number(machine.gpu_util).toFixed(0) : Math.round(gpuHistory[gpuHistory.length - 1])
  const memUtil = machine.mem_usage ? Number(machine.mem_usage).toFixed(0) : Math.round(memHistory[memHistory.length - 1])
  const temp = machine.gpu_temp ? Number(machine.gpu_temp).toFixed(0) : Math.round(Math.random() * 15 + 55)

  const gpuName = machine.gpu_name || 'GPU'
  const isRunning = machine.actual_status === 'running'
  const costPerHour = machine.dph_total || 0
  const status = machine.actual_status || 'stopped'

  // States where machine is loading/starting (should not show Start button)
  const loadingStates = ['loading', 'creating', 'starting', 'pending', 'provisioning', 'configuring']
  const isLoading = loadingStates.includes(status)

  // States where machine is stopped and can be started
  const stoppedStates = ['stopped', 'paused', 'exited', 'offline']
  const isStopped = stoppedStates.includes(status)

  // Map status to display info
  const getStatusDisplay = (status) => {
    const statusMap = {
      'running': { label: 'Online', variant: 'success', animate: false },
      'loading': { label: 'Inicializando', variant: 'warning', animate: true },
      'creating': { label: 'Criando', variant: 'warning', animate: true },
      'starting': { label: 'Iniciando', variant: 'warning', animate: true },
      'pending': { label: 'Pendente', variant: 'warning', animate: true },
      'provisioning': { label: 'Provisionando', variant: 'warning', animate: true },
      'configuring': { label: 'Configurando', variant: 'warning', animate: true },
      'paused': { label: 'Pausada', variant: 'gray', animate: false },
      'stopped': { label: 'Parada', variant: 'gray', animate: false },
      'exited': { label: 'Parada', variant: 'gray', animate: false },
      'offline': { label: 'Offline', variant: 'gray', animate: false },
      'error': { label: 'Erro', variant: 'error', animate: false },
      'failed': { label: 'Falhou', variant: 'error', animate: false },
      'destroying': { label: 'Destruindo', variant: 'error', animate: true },
      'failover': { label: 'Failover', variant: 'primary', animate: true },
    }
    return statusMap[status] || { label: status || 'Desconhecido', variant: 'gray', animate: false }
  }

  const statusDisplay = getStatusDisplay(status)

  // Get reliability score badge color based on score thresholds
  const getReliabilityBadge = (score) => {
    if (score === null || score === undefined) {
      return { variant: 'gray', label: 'N/A' }
    }
    const numScore = Number(score)
    if (numScore > 80) {
      return { variant: 'success', label: `${Math.round(numScore)}` }
    } else if (numScore >= 60) {
      return { variant: 'warning', label: `${Math.round(numScore)}` }
    } else {
      return { variant: 'error', label: `${Math.round(numScore)}` }
    }
  }
  const reliabilityScore = machine.reliability_score
  const reliabilityBadge = getReliabilityBadge(reliabilityScore)

  const cpuStandby = machine.cpu_standby
  const hasCpuStandby = cpuStandby?.enabled
  const cpuCostPerHour = cpuStandby?.dph_total || 0
  const totalCostPerHour = machine.total_dph || (costPerHour + cpuCostPerHour)

  const formatUptime = (startTime) => {
    if (!startTime) return null
    const start = new Date(startTime).getTime()
    const now = Date.now()
    const diff = now - start
    const hours = Math.floor(diff / 3600000)
    const minutes = Math.floor((diff % 3600000) / 60000)
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }
  const uptime = isRunning ? formatUptime(machine.start_date || machine.created_at) : null

  const generateSSHConfig = () => {
    return `Host dumont-${machine.id}
  HostName ${machine.ssh_host || 'ssh.vast.ai'}
  Port ${machine.ssh_port || 22}
  User root
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  IdentityFile ~/.ssh/vast_rsa`
  }

  const copySSHConfig = () => {
    navigator.clipboard.writeText(generateSSHConfig())
    setCopiedField('ssh')
    setCopyAnnouncement('Configuração SSH copiada!')
    setShowSSHInstructions(true)
    setTimeout(() => {
      setShowSSHInstructions(false)
      setCopiedField(null)
      setCopyAnnouncement('')
    }, 2000)
  }

  const copyToClipboard = (text, fieldName) => {
    navigator.clipboard.writeText(text)
    setCopiedField(fieldName)
    // Set contextual announcement for screen readers
    const announcements = {
      ip: 'Endereço IP copiado!',
      ssh: 'Comando SSH copiado!',
    }
    setCopyAnnouncement(announcements[fieldName] || 'Copiado!')
    setTimeout(() => {
      setCopiedField(null)
      setCopyAnnouncement('')
    }, 1500)
  }

  const openIDE = (ideName, protocol) => {
    const sshHost = machine.ssh_host
    const sshPort = machine.ssh_port || 22

    // Check if SSH host is valid (real VAST.ai hosts are like ssh5.vast.ai)
    const isValidHost = sshHost && /^ssh\d+\.vast\.ai$/.test(sshHost)

    if (!isValidHost) {
      setAlertDialog({
        open: true,
        title: 'SSH não disponível',
        description: !sshHost
          ? 'Host SSH não definido. A máquina pode ainda estar inicializando.'
          : sshHost === 'ssh.vast.ai'
            ? 'Esta é uma máquina de demonstração. Use máquinas reais do VAST.ai para conectar via SSH.'
            : `Host SSH inválido (${sshHost}). A máquina pode ainda estar inicializando.`,
        action: null
      })
      return
    }

    // Format: vscode://vscode-remote/ssh-remote+root@host:port/root
    const url = `${protocol}://vscode-remote/ssh-remote+root@${sshHost}:${sshPort}/root`
    window.open(url, '_blank')
  }

  const openVSCodeOnline = () => {
    const ports = machine.ports || {}
    const publicIp = machine.public_ipaddr
    const port8080Mapping = ports['8080/tcp']

    if (!port8080Mapping || !port8080Mapping[0]) {
      setAlertDialog({
        open: true,
        title: 'VS Code Online não disponível',
        description: 'A porta 8080 (code-server) não está mapeada.',
        action: null
      })
      return
    }

    const hostPort = port8080Mapping[0].HostPort
    window.open(`http://${publicIp}:${hostPort}/`, '_blank')
  }

  const gpuRam = Math.round((machine.gpu_ram || 24000) / 1024)
  const cpuCores = machine.cpu_cores || 4
  const ram = machine.cpu_ram ? (machine.cpu_ram > 1000 ? Math.round(machine.cpu_ram / 1024) : Math.round(machine.cpu_ram)) : 16
  const disk = Math.round(machine.disk_space || 100)

  const getFailoverBorderColor = () => {
    if (!isInFailover) return ''
    if (failoverProgress.phase === 'gpu_lost') return 'border-red-500/50 bg-red-950/20'
    if (failoverProgress.phase === 'failover_active') return 'border-brand-500/50 bg-brand-950/20'
    if (failoverProgress.phase === 'searching') return 'border-brand-500/50 bg-brand-950/20'
    if (failoverProgress.phase === 'provisioning') return 'border-brand-500/50 bg-brand-950/20'
    if (failoverProgress.phase === 'restoring') return 'border-brand-500/50 bg-brand-950/20'
    if (failoverProgress.phase === 'complete') return 'border-brand-500/50 bg-brand-950/20'
    return ''
  }

  return (
    <Card
      data-testid={`machine-card-${machine.id}`}
      className={`group relative transition-all
        ${isNew ? 'animate-highlight-new ring-2 ring-brand-400 ring-opacity-75' : ''}
        ${isDeleting ? 'opacity-50 pointer-events-none' : ''}
        ${isInFailover
          ? getFailoverBorderColor()
          : isRunning
            ? 'border-brand-700/50 dark:border-brand-700/50'
            : 'hover:border-gray-700 dark:hover:border-gray-700'
        }
      `}
    >
      {/* Deleting overlay */}
      {isDeleting && (
        <div className="absolute inset-0 bg-gray-900/80 dark:bg-gray-950/80 rounded-lg z-50 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-8 h-8 text-red-500 animate-spin" />
          <div className="text-sm text-gray-300">Destruindo máquina...</div>
        </div>
      )}

      {isInFailover && (
        <div
          className="mb-3 p-3 rounded-lg bg-white/5 border border-white/10"
          data-testid="failover-progress-panel"
          role="region"
          aria-label="Progresso do failover"
          aria-live="polite"
          aria-atomic="false"
        >
          <div className="flex items-center gap-2 mb-3">
            <Zap className={`w-4 h-4 ${failoverProgress.phase === 'gpu_lost' ? 'text-red-400 animate-pulse' :
              failoverProgress.phase === 'complete' ? 'text-brand-400' :
                'text-brand-400 animate-pulse'
              }`} aria-hidden="true" />
            <span className="text-sm font-semibold text-white">Failover em Progresso</span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className={`flex items-center gap-2 ${failoverProgress.phase === 'gpu_lost' ? 'text-red-400' :
              ['failover_active', 'searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'text-green-400' :
                'text-gray-500'
              }`} data-testid="failover-step-gpu-lost">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${failoverProgress.phase === 'gpu_lost' ? 'border-red-400 bg-red-500/20' :
                ['failover_active', 'searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'border-green-400 bg-green-500/20' :
                  'border-gray-600'
                }`}>
                {['failover_active', 'searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '1'}
              </div>
              <span>GPU Interrompida</span>
              {failoverProgress.phase === 'gpu_lost' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.detection_time_ms && <span className="ml-auto text-gray-500">{failoverProgress.metrics.detection_time_ms}ms</span>}
            </div>

            <div className={`flex items-center gap-2 ${failoverProgress.phase === 'failover_active' ? 'text-brand-400' :
              ['searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'text-brand-400' :
                'text-gray-500'
              }`} data-testid="failover-step-active">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${failoverProgress.phase === 'failover_active' ? 'border-brand-400 bg-brand-500/20' :
                ['searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'border-brand-400 bg-brand-500/20' :
                  'border-gray-600'
                }`}>
                {['searching', 'provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '2'}
              </div>
              <span>Failover para CPU Standby</span>
              {failoverProgress.phase === 'failover_active' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.failover_time_ms && <span className="ml-auto text-gray-500">{failoverProgress.metrics.failover_time_ms}ms</span>}
            </div>

            <div className={`flex items-center gap-2 ${failoverProgress.phase === 'searching' ? 'text-brand-400' :
              ['provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'text-brand-400' :
                'text-gray-500'
              }`} data-testid="failover-step-searching">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${failoverProgress.phase === 'searching' ? 'border-brand-400 bg-brand-500/20' :
                ['provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? 'border-brand-400 bg-brand-500/20' :
                  'border-gray-600'
                }`}>
                {['provisioning', 'restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '3'}
              </div>
              <span>Buscando Nova GPU</span>
              {failoverProgress.phase === 'searching' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.search_time_ms && <span className="ml-auto text-gray-500">{(failoverProgress.metrics.search_time_ms / 1000).toFixed(1)}s</span>}
            </div>

            <div className={`flex items-center gap-2 ${failoverProgress.phase === 'provisioning' ? 'text-brand-400' :
              ['restoring', 'complete'].includes(failoverProgress.phase) ? 'text-brand-400' :
                'text-gray-500'
              }`} data-testid="failover-step-provisioning">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${failoverProgress.phase === 'provisioning' ? 'border-brand-400 bg-brand-500/20' :
                ['restoring', 'complete'].includes(failoverProgress.phase) ? 'border-brand-400 bg-brand-500/20' :
                  'border-gray-600'
                }`}>
                {['restoring', 'complete'].includes(failoverProgress.phase) ? '✓' : '4'}
              </div>
              <span>Provisionando {failoverProgress.newGpu || 'Nova GPU'}</span>
              {failoverProgress.phase === 'provisioning' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.provisioning_time_ms && <span className="ml-auto text-gray-500">{(failoverProgress.metrics.provisioning_time_ms / 1000).toFixed(1)}s</span>}
            </div>

            <div className={`flex items-center gap-2 ${failoverProgress.phase === 'restoring' ? 'text-brand-400' :
              failoverProgress.phase === 'complete' ? 'text-brand-400' :
                'text-gray-500'
              }`} data-testid="failover-step-restoring">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${failoverProgress.phase === 'restoring' ? 'border-brand-400 bg-brand-500/20' :
                failoverProgress.phase === 'complete' ? 'border-brand-400 bg-brand-500/20' :
                  'border-gray-600'
                }`}>
                {failoverProgress.phase === 'complete' ? '✓' : '5'}
              </div>
              <span>Restaurando Dados</span>
              {failoverProgress.phase === 'restoring' && <RefreshCw className="w-3 h-3 animate-spin ml-auto" />}
              {failoverProgress.metrics?.restore_time_ms && <span className="ml-auto text-gray-500">{(failoverProgress.metrics.restore_time_ms / 1000).toFixed(1)}s</span>}
            </div>

            <div className={`flex items-center gap-2 ${failoverProgress.phase === 'complete' ? 'text-brand-400' : 'text-gray-500'
              }`} data-testid="failover-step-complete">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${failoverProgress.phase === 'complete' ? 'border-brand-400 bg-brand-500/20' : 'border-gray-600'
                }`}>
                {failoverProgress.phase === 'complete' ? '✓' : '6'}
              </div>
              <span>Recuperação Completa</span>
              {failoverProgress.metrics?.total_time_ms && failoverProgress.phase === 'complete' && (
                <span className="ml-auto text-brand-400 font-medium">{(failoverProgress.metrics.total_time_ms / 1000).toFixed(1)}s total</span>
              )}
            </div>
          </div>

          {failoverProgress.message && (
            <div className="mt-3 pt-2 border-t border-gray-700/50">
              <p className="text-xs text-gray-300" data-testid="failover-message">{failoverProgress.message}</p>
            </div>
          )}

          {failoverProgress.phase === 'complete' && failoverProgress.metrics && (
            <div className="mt-3 pt-2 border-t border-gray-700/50 grid grid-cols-3 gap-2 text-[10px]">
              <div className="text-center">
                <div className="text-gray-500">Arquivos</div>
                <div className="text-white font-medium">{failoverProgress.metrics.files_synced?.toLocaleString() || '0'}</div>
              </div>
              <div className="text-center">
                <div className="text-gray-500">Dados</div>
                <div className="text-white font-medium">{failoverProgress.metrics.data_restored_mb || '0'} MB</div>
              </div>
              <div className="text-center">
                <div className="text-gray-500">Status</div>
                <div className="text-green-400 font-medium">Sucesso</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Card Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-gray-900 dark:text-white font-semibold text-sm truncate">{gpuName}</span>
            <Badge
              variant={statusDisplay.variant}
              dot
              className={`text-[9px] ${statusDisplay.animate ? 'animate-pulse' : ''}`}
              aria-label={`Status da máquina: ${statusDisplay.label}`}
              aria-busy={isLoading}
            >
              {statusDisplay.label}
            </Badge>
            {/* Reliability Score Badge - Clickable */}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setShowReliabilityModal(true)
              }}
              className="focus:outline-none focus:ring-2 focus:ring-brand-500/50 rounded-full"
              title={`Reliability Score: ${reliabilityScore !== null && reliabilityScore !== undefined ? Math.round(reliabilityScore) : 'N/A'}/100 - Clique para detalhes`}
            >
              <Badge
                variant={reliabilityBadge.variant}
                className="text-[9px] cursor-pointer hover:opacity-80 transition-opacity"
                data-testid="reliability-badge"
              >
                <Activity className="w-2.5 h-2.5 mr-0.5" />
                {reliabilityBadge.label}
              </Badge>
            </button>
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            <Badge variant="primary" className="text-[9px]">
              Vast.ai
            </Badge>

            {/* Failover Strategy Badge with Dropdown */}
            <div className="relative" data-testid="failover-strategy-container">
              <button
                ref={strategyTriggerRef}
                type="button"
                id={`failover-trigger-${machine.id}`}
                data-testid="failover-selector"
                className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium cursor-pointer hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-brand-500 ${
                aria-label={`Failover strategy: ${strategyInfo.label}. Click to change strategy`}
                aria-expanded={showStrategyMenu}
                aria-haspopup="menu"
                aria-controls={showStrategyMenu ? `failover-menu-${machine.id}` : undefined}
                className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium cursor-pointer hover:opacity-80 ${
                  currentStrategy === 'disabled' ? 'bg-gray-500/20 text-gray-400' :
                  currentStrategy === 'warm_pool' ? 'bg-green-500/20 text-green-400' :
                  'bg-brand-500/20 text-brand-400'
                }`}
                onClick={() => setShowStrategyMenu(!showStrategyMenu)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowDown' && !showStrategyMenu) {
                    e.preventDefault()
                    setShowStrategyMenu(true)
                  } else if (e.key === 'Escape' && showStrategyMenu) {
                    e.preventDefault()
                    setShowStrategyMenu(false)
                    setFocusedStrategyIndex(0)
                  }
                }}
                aria-haspopup="menu"
                aria-expanded={showStrategyMenu}
                aria-label={`Estratégia de failover: ${strategyInfo.label}`}
              >
                <Shield className="w-2.5 h-2.5 mr-0.5" />
                {strategyInfo.label}
                {currentStrategyCost > 0 && (
                  <span className="ml-0.5 text-[8px] opacity-70">+${currentStrategyCost.toFixed(3)}/h</span>
                )}
              </button>

              {showStrategyMenu && (
                <div
                  ref={strategyMenuRef}
                  className="absolute top-full left-0 mt-1 z-50 w-64 p-2 bg-gray-900 border border-gray-700 rounded-lg shadow-xl"
                  data-testid="failover-dropdown-menu"
                  role="menu"
                  aria-label="Opções de estratégia de failover"
                  onKeyDown={handleStrategyKeyDown}
                  id={`failover-menu-${machine.id}`}
                  ref={strategyMenuRef}
                  role="menu"
                  aria-labelledby={`failover-menu-label-${machine.id}`}
                  aria-activedescendant={focusedStrategyIndex >= 0 ? `failover-option-${machine.id}-${strategyKeys[focusedStrategyIndex]}` : undefined}
                  className="absolute top-full left-0 mt-1 z-50 w-64 p-2 bg-gray-900 border border-gray-700 rounded-lg shadow-xl"
                  data-testid="failover-dropdown-menu"
                  onKeyDown={handleStrategyMenuKeyDown}
                >
                  <div className="flex items-center justify-between mb-2 pb-1 border-b border-gray-700">
                    <span id={`failover-menu-label-${machine.id}`} className="text-[10px] font-semibold text-gray-300">Estratégia de Failover</span>
                    <button
                      onClick={() => {
                        setShowStrategyMenu(false)
                        setFocusedStrategyIndex(0)
                        strategyTriggerRef.current?.focus()
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') {
                          e.preventDefault()
                          setShowStrategyMenu(false)
                          setFocusedStrategyIndex(0)
                          strategyTriggerRef.current?.focus()
                        }
                      }}
                      className="p-0.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
                      data-testid="failover-dropdown-close"
                      aria-label="Fechar menu de failover"
                      aria-label="Close failover strategy menu"
                      tabIndex={-1}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="space-y-1" data-testid="failover-options-list">
                    {Object.entries(FAILOVER_STRATEGIES_BASE).map(([key, strategy], index) => {
                      const cost = strategyCosts[key] || 0
                      const isFocused = focusedStrategyIndex === index
                      return (
                        <button
                          key={key}
                          ref={(el) => (strategyButtonRefs.current[index] = el)}
                          ref={(el) => { strategyItemRefs.current[index] = el }}
                          id={`failover-option-${machine.id}-${key}`}
                          role="menuitem"
                          tabIndex={isFocused ? 0 : -1}
                          data-testid={`failover-option-${key}`}
                          aria-current={currentStrategy === key ? 'true' : undefined}
                          onClick={() => {
                            // TODO: Call API to change strategy
                            setShowStrategyMenu(false)
                            setFocusedStrategyIndex(0)
                            strategyTriggerRef.current?.focus()
                          }}
                          className={`w-full flex items-center justify-between p-1.5 rounded text-left transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 focus:ring-offset-gray-900 ${
                            currentStrategy === key
                              ? 'bg-brand-500/20 border border-brand-500/30'
                              : 'hover:bg-gray-800 border border-transparent'
                          }`}
                          role="menuitem"
                          tabIndex={focusedStrategyIndex === index ? 0 : -1}
                          aria-selected={currentStrategy === key}
                            setFocusedStrategyIndex(-1)
                          }}
                          onKeyDown={handleStrategyMenuKeyDown}
                          className={`w-full flex items-center justify-between p-1.5 rounded text-left transition-colors ${
                            currentStrategy === key
                              ? 'bg-brand-500/20 border border-brand-500/30'
                              : 'hover:bg-gray-800 border border-transparent'
                          } ${isFocused ? 'ring-2 ring-brand-400 ring-offset-1 ring-offset-gray-900' : ''}`}
                        >
                          <div className="flex items-center gap-1.5">
                            <Shield className={`w-3 h-3 ${
                              key === 'disabled' ? 'text-gray-500' :
                              key === 'warm_pool' ? 'text-green-400' :
                              key === 'cpu_standby' ? 'text-blue-400' :
                              key === 'regional_volume' ? 'text-purple-400' :
                              'text-orange-400'
                            }`} />
                            <div>
                              <div className="text-[10px] text-white font-medium">{strategy.label}</div>
                              <div className="text-[8px] text-gray-500">
                                {strategy.description}
                                {strategy.recovery && <span className="ml-1 text-gray-400">• {strategy.recovery}</span>}
                              </div>
                            </div>
                          </div>
                          <div className="text-[9px] text-brand-400 font-mono whitespace-nowrap">
                            {cost > 0 ? `+$${cost.toFixed(3)}/h` : 'Grátis'}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                  <div className="mt-2 pt-2 border-t border-gray-700 text-[8px] text-gray-500" data-testid="failover-cost-basis">
                    Custos baseados em: GPU ${(machine.dph_total || 0).toFixed(2)}/h
                  </div>
                </div>
              )}
            </div>

            {/* Backup Info Badge */}
            <div className="relative">
              <Badge
                ref={backupBadgeRef}
                ref={backupInfoTriggerRef}
                variant={hasCpuStandby ? 'primary' : 'gray'}
                className="cursor-pointer hover:opacity-80 text-[9px] focus:outline-none focus:ring-2 focus:ring-brand-500"
                onClick={() => setShowBackupInfo(!showBackupInfo)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    setShowBackupInfo(!showBackupInfo)
                  } else if (e.key === 'Escape' && showBackupInfo) {
                    e.preventDefault()
                    setShowBackupInfo(false)
                  }
                }}
                role="button"
                tabIndex={0}
                aria-expanded={showBackupInfo}
                aria-label={`Informações de backup: ${hasCpuStandby ? 'Backup ativo' : 'Sem backup'}`}
                aria-label={hasCpuStandby ? 'View CPU backup details' : 'No backup configured. Click for details'}
                aria-expanded={showBackupInfo}
                aria-haspopup="dialog"
                aria-controls={showBackupInfo ? `backup-info-dialog-${machine.id}` : undefined}
              >
                <Layers className="w-2.5 h-2.5 mr-0.5" />
                {hasCpuStandby ? 'Backup' : 'Sem backup'}
              </Badge>

            {showBackupInfo && (
              <div
                ref={backupPopupRef}
                className="absolute top-full left-0 mt-2 z-50 w-72 p-4 bg-[#131713] border border-white/10 rounded-xl shadow-xl"
                onKeyDown={handleBackupPopupKeyDown}
                id={`backup-info-dialog-${machine.id}`}
                role="dialog"
                aria-labelledby={`backup-info-title-${machine.id}`}
                className="absolute top-full left-0 mt-2 z-50 w-72 p-4 bg-[#131713] border border-white/10 rounded-xl shadow-xl"
              >
                <div className="flex items-center justify-between mb-3">
                  <span id={`backup-info-title-${machine.id}`} className="text-sm font-semibold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-brand-400" />
                    CPU Backup (Espelho)
                  </span>
                  <button
                    onClick={() => {
                      setShowBackupInfo(false)
                      backupBadgeRef.current?.focus()
                    }}
                    className="p-1 rounded-lg hover:bg-white/10 text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-brand-500"
                    aria-label="Fechar informações de backup"
                    ref={backupInfoCloseRef}
                    onClick={closeBackupInfo}
                    className="p-1 rounded-lg hover:bg-white/10 text-gray-500 hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                    aria-label="Close backup info popup"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {hasCpuStandby ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs">
                      <Cloud className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-gray-400">Provider:</span>
                      <span className="text-white font-medium">{cpuStandby.provider?.toUpperCase() || 'GCP'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Server className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-gray-400">Máquina:</span>
                      <span className="text-white font-medium">{cpuStandby.name || 'Provisionando...'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <MapPin className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-gray-400">Zona:</span>
                      <span className="text-white font-medium">{cpuStandby.zone || 'europe-west1-b'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Globe className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-gray-400">IP:</span>
                      <span className="text-white font-medium font-mono">{cpuStandby.ip || 'Aguardando...'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Cpu className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-gray-400">Tipo:</span>
                      <span className="text-white font-medium">{cpuStandby.machine_type || 'e2-medium'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <DollarSign className="w-3.5 h-3.5 text-brand-400" />
                      <span className="text-gray-400">Custo:</span>
                      <span className="text-brand-400 font-medium">${cpuStandby.dph_total?.toFixed(3) || '0.010'}/h</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-gray-400">Syncs:</span>
                      <span className="text-white font-medium">{cpuStandby.sync_count || 0}</span>
                    </div>
                    <div className="mt-2 pt-2 border-t border-gray-700/50">
                      <div className={`text-xs px-2 py-1 rounded text-center ${cpuStandby.state === 'ready' ? 'bg-brand-500/20 text-brand-400' :
                        cpuStandby.state === 'syncing' ? 'bg-brand-500/10 text-brand-400' :
                          cpuStandby.state === 'failover_active' ? 'bg-brand-500/20 text-brand-400' :
                            'bg-gray-700/30 text-gray-400'
                        }`}>
                        {cpuStandby.state === 'ready' ? '✓ Pronto para failover' :
                          cpuStandby.state === 'syncing' ? '↻ Sincronizando...' :
                            cpuStandby.state === 'failover_active' ? '⚡ Failover ativo' :
                              '○ Provisionando...'}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-3">
                    <Shield className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                    <p className="text-xs text-gray-400 mb-2">
                      Nenhum backup CPU configurado para esta máquina.
                    </p>
                    <p className="text-[10px] text-gray-500">
                      Ative o auto-standby nas configurações para criar backups automáticos.
                    </p>
                  </div>
                )}
              </div>
            )}
            </div>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
              className="p-1.5 rounded-lg hover:bg-gray-800/50 text-gray-500 hover:text-gray-300 flex-shrink-0"
<button
<button className="p-1.5 rounded-lg hover:bg-gray-800/50 text-gray-500 hover:text-gray-300 flex-shrink-0" aria-label="Menu de opções da máquina" aria-haspopup="menu">
              aria-label="More options menu"
            <button
              data-testid={`machine-menu-${machine.id}`}
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48" data-testid="machine-menu-content">
            <DropdownMenuItem onClick={() => setShowDetailsModal(true)} data-testid="menu-details">
              <Info className="w-3.5 h-3.5 mr-2" />
              Ver Detalhes
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {isRunning && (
              <>
                <DropdownMenuItem
                  onClick={() => onSnapshot && onSnapshot(machine.id)}
                  disabled={isCreatingSnapshot}
                  data-testid="menu-snapshot"
                >
                  <Save className="w-3.5 h-3.5 mr-2" />
                  {isCreatingSnapshot ? 'Criando...' : 'Criar Snapshot'}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem onClick={() => onRestoreToNew && onRestoreToNew(machine)} data-testid="menu-restore">
              <Upload className="w-3.5 h-3.5 mr-2" />
              Restaurar em Nova
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setShowConfigModal(true)} data-testid="menu-hibernation">
              <Settings className="w-3.5 h-3.5 mr-2" />
              Auto-Hibernation
            </DropdownMenuItem>
            <DropdownMenuItem onClick={copySSHConfig}>
            </DropdownMenuItem>
<DropdownMenuItem onClick={() => setShowSnapshotConfigModal(true)}>
              Configure Snapshots
              <Camera className="w-3.5 h-3.5 mr-2" />
            <DropdownMenuItem onClick={copySSHConfig} aria-label="Copiar configuração SSH para o arquivo de config">
<DropdownMenuItem onClick={copySSHConfig} data-testid="menu-ssh-config">
              {copiedField === 'ssh' ? (
                <Check className="w-3.5 h-3.5 mr-2 text-green-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 mr-2" />
              )}
              <span>{copiedField === 'ssh' ? 'Copiado!' : 'Copiar SSH Config'}</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onDestroy(machine.id)}
              className="text-red-400 focus:text-red-400"
              data-testid={`destroy-button-${machine.id}`}
            >
              <Trash2 className="w-3.5 h-3.5 mr-2" />
              Destruir
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Specs Row */}
      <div className="flex items-center gap-1 mb-2 text-[9px] text-gray-400 flex-wrap">
        {machine.public_ipaddr && (
          <button
            onClick={() => copyToClipboard(machine.public_ipaddr, 'ip')}
            className={`px-1.5 py-0.5 rounded border transition-all ${copiedField === 'ip'
              ? 'bg-brand-500/20 text-brand-400 border-brand-500/30'
              : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/10'
              }`}
            title="Clique para copiar IP"
            aria-label="Copiar endereço IP"
            aria-label={copiedField === 'ip' ? 'IP copiado para a área de transferência' : `Copiar endereço IP ${machine.public_ipaddr}`}
          >
            {copiedField === 'ip' ? 'Copiado!' : machine.public_ipaddr}
          </button>
        )}

        <span
          className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
          title={`${gpuRam}GB VRAM - ${machine.gpu_name || 'GPU'}`}
        >
          {gpuRam}GB VRAM
        </span>

        <span
          className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
          title={`${cpuCores} núcleos de CPU`}
        >
          {cpuCores} CPU
        </span>

        <span
          className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
          title={`${ram}GB de memória do sistema`}
        >
          {ram}GB RAM
        </span>

        <span
          className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
          title={`${disk}GB de armazenamento`}
        >
          {disk}GB Disk
        </span>

        {/* SSH Info - clickable to copy */}
        {isRunning && machine.ssh_host && (
          <button
            onClick={() => copyToClipboard(`ssh root@${machine.ssh_host} -p ${machine.ssh_port || 22}`, 'ssh')}
            className={`px-1.5 py-0.5 rounded border transition-all ${copiedField === 'ssh'
              ? 'bg-brand-500/20 text-brand-400 border-brand-500/30'
              : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/10'
              }`}
            title={`SSH: root@${machine.ssh_host}:${machine.ssh_port || 22} (clique para copiar)`}
            aria-label="Copiar comando SSH"
            aria-label={copiedField === 'ssh' ? 'Comando SSH copiado para a área de transferência' : `Copiar comando SSH para conectar na porta ${machine.ssh_port || 22}`}
          >
            {copiedField === 'ssh' ? 'Copiado!' : `SSH :${machine.ssh_port || 22}`}
          </button>
        )}

        {isRunning && syncStatus && (
          <span
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded border ${syncStatus === 'syncing'
              ? 'bg-brand-500/10 text-brand-400 border-brand-500/20'
              : syncStatus === 'synced'
                ? 'bg-brand-500/10 text-brand-400 border-brand-500/20'
                : 'bg-gray-700/30 text-gray-400 border-gray-700/30'
              }`}
            title={syncStats ? `Último sync: ${syncStats.files_changed || 0} modificados, ${syncStats.data_added || '0 B'} enviados` : 'Clique em "Criar Snapshot" para sincronizar'}
          >
            <RefreshCw className={`w-2.5 h-2.5 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} />
            {syncStatus === 'syncing' ? 'Sync...' : syncStatus === 'synced' ? 'Synced' : 'Sync'}
          </span>
        )}
      </div>

      {isRunning ? (
        <>
          {/* Metrics Grid - Compact */}
          <div className="grid grid-cols-5 gap-0.5 mb-2 p-2 rounded-lg bg-white/5 border border-white/10">
            <div className="text-center">
              <div className="text-brand-400 font-mono text-xs font-bold">{gpuUtil}%</div>
              <div className="text-[8px] text-gray-500 uppercase">GPU</div>
            </div>
            <div className="text-center">
              <div className="text-white font-mono text-xs font-bold">{memUtil}%</div>
              <div className="text-[8px] text-gray-500 uppercase">VRAM</div>
            </div>
            <div className="text-center">
              <div className={`font-mono text-xs font-bold ${temp > 75 ? 'text-red-400' : temp > 65 ? 'text-gray-300' : 'text-brand-400'}`}>
                {temp}°C
              </div>
              <div className="text-[8px] text-gray-500 uppercase">TEMP</div>
            </div>
            <div className="text-center">
              <div className="text-brand-400 font-mono text-xs font-bold" title={hasCpuStandby ? `GPU: $${costPerHour.toFixed(2)} + CPU: $${cpuCostPerHour.toFixed(3)}` : ''}>
                ${totalCostPerHour.toFixed(2)}
              </div>
              <div className="text-[8px] text-gray-500 uppercase">/hora</div>
            </div>
            {uptime && (
              <div className="text-center">
                <div className="text-white font-mono text-xs font-bold">{uptime}</div>
                <div className="text-[8px] text-gray-500 uppercase">UP</div>
              </div>
            )}
          </div>

          {/* IDE Buttons */}
          <div className="flex gap-1 mb-2" data-testid="ide-buttons-container">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                >
                  className="flex-1 text-[10px] h-7"
                  icon={Code}
                <Button variant="ghost" size="xs" className="flex-1 text-[10px] h-7" icon={Code} aria-label="Open VS Code IDE. Choose between web browser or desktop application via SSH">
<Button
                  data-testid={`vscode-button-${machine.id}`}
                  variant="ghost"
<Button variant="ghost" size="xs" className="flex-1 text-[10px] h-7" icon={Code} aria-label="Abrir VS Code" aria-haspopup="menu">
                  size="xs"
                  VS Code
                  <ChevronDown className="w-2.5 h-2.5 opacity-50 ml-0.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent data-testid="vscode-dropdown-menu">
                <DropdownMenuItem onClick={openVSCodeOnline} data-testid="vscode-option-web">
                  Online (Web)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => openIDE('VS Code', 'vscode')} data-testid="vscode-option-desktop">
                  Desktop (SSH)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
<Button variant="ghost" size="xs" className="flex-1 text-[10px] h-7" onClick={() => openIDE('Cursor', 'cursor')} aria-label="Abrir Cursor IDE">
              Cursor
            >
            <Button variant="ghost" size="xs" className="flex-1 text-[10px] h-7" onClick={() => openIDE('Cursor', 'cursor')} aria-label="Open machine in Cursor IDE via SSH remote connection">
              data-testid={`windsurf-button-${machine.id}`}
            <Button variant="ghost" size="xs" className="flex-1 text-[10px] h-7" onClick={() => openIDE('Windsurf', 'windsurf')} aria-label="Abrir Windsurf IDE">
              className="flex-1 text-[10px] h-7"
              onClick={() => openIDE('Cursor', 'cursor')}
              size="xs"
            <Button variant="ghost" size="xs" className="flex-1 text-[10px] h-7" onClick={() => openIDE('Windsurf', 'windsurf')} aria-label="Open machine in Windsurf IDE via SSH remote connection">
<Button
            </Button>
              onClick={() => openIDE('Windsurf', 'windsurf')}
              data-testid={`cursor-button-${machine.id}`}
            <Button
              variant="ghost"
              Windsurf
            </Button>
          </div>

          {/* Action Buttons - Row 1: Failover actions */}
          {hasCpuStandby && !isInFailover && (
            <div className="flex gap-1 mb-1.5">
              <Button
                variant="outline"
                size="xs"
                icon={Shield}
                className="flex-1 text-[10px] h-7"
                onClick={() => setShowFailoverMigration(true)}
                title="Migrar para outro tipo de failover"
                aria-label="Configurar failover"
                aria-label="Open failover migration options for this machine"
              >
                Failover
              </Button>
              {onSimulateFailover && (
                <Button
                  variant="outline"
                  size="xs"
                  icon={Zap}
                  className="flex-1 text-[10px] h-7"
                  onClick={() => onSimulateFailover(machine)}
                  title="Simular roubo de GPU e failover automático"
                  aria-label="Simular failover"
                  aria-label="Test failover by simulating GPU interruption"
                >
                  Testar
                </Button>
              )}
            </div>
          )}

          {/* Action Buttons - Row 2: Machine actions */}
          <div className="flex gap-1">
            <Button
              variant="secondary"
              size="xs"
              icon={ArrowLeftRight}
              className="flex-1 text-[10px] h-7"
              onClick={() => onMigrate && onMigrate(machine)}
              aria-label="Migrar para CPU"
              aria-label="Migrate this machine from GPU to CPU instance"
            >
              CPU
            </Button>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="xs" icon={Pause} className="flex-1 text-[10px] h-7" aria-label={`Pausar máquina ${gpuName}`}>
                <Button variant="outline" size="xs" icon={Pause} className="flex-1 text-[10px] h-7" aria-label="Pause this machine. Running processes will be interrupted">
                  Pausar
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Pausar máquina?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Isso irá pausar a máquina {gpuName}. Processos em execução serão interrompidos.
                    Você poderá reiniciá-la depois.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={() => onPause && onPause(machine.id)}>
                    Pausar
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </>
      ) : (
        <>
          {/* Specs Grid - Offline - Compact */}
          <div className="grid grid-cols-4 gap-0.5 mb-2 p-2 rounded-lg bg-gray-800/20 border border-gray-700/20 text-center">
            <div>
              <div className="text-gray-900 dark:text-white font-mono text-xs font-bold">{gpuRam}GB</div>
              <div className="text-[8px] text-gray-500 dark:text-gray-400 uppercase">VRAM</div>
            </div>
            <div>
              <div className="text-gray-900 dark:text-white font-mono text-xs font-bold">{cpuCores}</div>
              <div className="text-[8px] text-gray-500 dark:text-gray-400 uppercase">CPU</div>
            </div>
            <div>
              <div className="text-gray-900 dark:text-white font-mono text-xs font-bold">{disk}GB</div>
              <div className="text-[8px] text-gray-500 dark:text-gray-400 uppercase">DISK</div>
            </div>
            <div>
              <div className="text-brand-500 dark:text-brand-400 font-mono text-xs font-bold" title={hasCpuStandby ? `GPU: $${costPerHour.toFixed(2)} + CPU: $${cpuCostPerHour.toFixed(3)}` : ''}>
                ${totalCostPerHour.toFixed(2)}
              </div>
              <div className="text-[8px] text-gray-500 dark:text-gray-400 uppercase">/hora</div>
            </div>
          </div>

          {/* Action Buttons - Offline/Loading */}
          <div className="flex gap-1.5">
            {isLoading ? (
              /* Show loading indicator with ID and elapsed time */
              <div className="w-full p-2 rounded-lg bg-warning-500/10 border border-warning-500/20" aria-busy="true" aria-label={`Máquina ${statusDisplay.label.toLowerCase()}`}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <RefreshCw className="w-3 h-3 text-warning-400 animate-spin" />
                    <span className="text-xs text-warning-400 font-medium">{statusDisplay.label}...</span>
                  </div>
                  <div className="flex items-center gap-1 text-warning-400">
                    <Clock className="w-3 h-3" />
                    <span className="text-xs font-mono">{formatElapsedTime(elapsedTime)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-gray-400">
                  <Hash className="w-2.5 h-2.5" />
                  <span className="font-mono">VAST ID: {machine.id}</span>
                </div>
              </div>
            ) : (
              <>
                {machine.num_gpus === 0 && (
                  <Button
                    variant="success"
                    size="xs"
                    icon={ArrowLeftRight}
                    className="flex-1 text-[10px] h-7"
                    onClick={() => onMigrate && onMigrate(machine)}
                    aria-label="Migrar para GPU"
                    aria-label="Migrate this machine from CPU to GPU instance"
                  >
                    GPU
                  </Button>
                )}

                <Button
                  variant="secondary"
                  size="xs"
                  icon={Play}
                  className={`text-[10px] h-7 ${machine.num_gpus === 0 ? 'flex-1' : 'w-full'}`}
                  onClick={() => onStart && onStart(machine.id)}
                  aria-label={`Iniciar máquina ${gpuName}`}
                  aria-label={`Start ${gpuName} machine`}
                >
                  Iniciar
                </Button>
              </>
            )}
          </div>
        </>
      )}

      {showSSHInstructions && (
        <div className="mt-2 p-2 rounded bg-brand-500/10 border border-brand-500/20 text-[10px] text-brand-300 text-center">
          SSH Config copiado! Cole em ~/.ssh/config
        </div>
      )}

      <HibernationConfigModal
        instance={{ id: machine.id, name: gpuName }}
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onSave={() => setShowConfigModal(false)}
      />

      <SnapshotConfigModal
        instance={{ id: machine.id, name: gpuName }}
        isOpen={showSnapshotConfigModal}
        onClose={() => setShowSnapshotConfigModal(false)}
        onSave={() => setShowSnapshotConfigModal(false)}
      />

      <FailoverMigrationModal
        machine={machine}
        isOpen={showFailoverMigration}
        onClose={() => setShowFailoverMigration(false)}
        onSuccess={(result) => {
          console.log('Failover migration success:', result)
          setShowFailoverMigration(false)
        }}
      />

      <InstanceDetailsModal
        machine={machine}
        isOpen={showDetailsModal}
        onClose={() => setShowDetailsModal(false)}
      />

      <ReliabilityDetailsModal
        machine={machine}
        isOpen={showReliabilityModal}
        onClose={() => setShowReliabilityModal(false)}
        reliabilityData={machine.reliability_data || { reliability_score: reliabilityScore }}
      />

      <AlertDialog open={alertDialog.open} onOpenChange={(open) => setAlertDialog({ ...alertDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{alertDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>{alertDialog.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setAlertDialog({ ...alertDialog, open: false })}>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Aria-live region for copy announcements */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="copy-announcement"
      >
        {copyAnnouncement}
      </div>

      {/* Aria-live region for failover progress announcements */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="failover-announcement"
      >
        {failoverAnnouncement}
      </div>
    </Card>
  )
}

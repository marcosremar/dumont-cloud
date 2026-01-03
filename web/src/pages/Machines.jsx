import { useState, useEffect, useRef, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSelector } from 'react-redux'
import { apiGet, apiPost, apiDelete } from '../utils/api'
import { selectRacingInstanceIds } from '../store/slices/instancesSlice'
import { ConfirmModal } from '../components/ui/dumont-ui'
import { Plus, Server, Shield, Activity, Check, RefreshCw, DollarSign, ArrowUpDown, Filter, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react'
import { useToast } from '../components/Toast'
import MigrationModal from '../components/MigrationModal'
import { ErrorState } from '../components/ErrorState'
import { EmptyState } from '../components/EmptyState'
import { SkeletonList } from '../components/Skeleton'
import MachineCard from '../components/machines/MachineCard'
import { DEMO_MACHINES } from '../constants/demoData'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  Switch,
  Slider,
  Checkbox,
} from '../components/tailadmin-ui'


// Main Machines Page
export default function Machines() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const toast = useToast()
  const API_BASE = import.meta.env.VITE_API_URL || ''
  const getToken = () => localStorage.getItem('auth_token')
  const isDemo = location.pathname.startsWith('/demo-app')

  // Get racing instance IDs from Redux - these machines should not appear in the list
  const racingInstanceIds = useSelector(selectRacingInstanceIds)

  const [machines, setMachines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // all, online, offline
  const [syncStatus, setSyncStatus] = useState({}) // machineId -> 'idle' | 'syncing' | 'synced'
  const [lastSyncTime, setLastSyncTime] = useState({}) // machineId -> timestamp
  const [destroyDialog, setDestroyDialog] = useState({ open: false, machineId: null, machineName: '' })
  const [migrationTarget, setMigrationTarget] = useState(null)
  const [syncStats, setSyncStats] = useState({}) // machineId -> { files_new, files_changed, data_added, ... }
  const [demoToast, setDemoToast] = useState(null) // Toast message for demo actions
  const [failoverProgress, setFailoverProgress] = useState({}) // machineId -> { phase, message, newGpu, metrics }
  const [failoverHistory, setFailoverHistory] = useState([]) // Array of completed failover events
  const [newMachineIds, setNewMachineIds] = useState(new Set()) // Track newly created machines for highlight animation
  const [vastBalance, setVastBalance] = useState(null) // VAST.ai account balance
  const [deletingMachines, setDeletingMachines] = useState(new Set()) // Track machines being deleted

  // Create machine modal state
  const [createModal, setCreateModal] = useState({ open: false, offer: null, creating: false, error: null })

  // Ref to prevent double creation from React Strict Mode
  const offerProcessedRef = useRef(false)

  // Ref for scrolling to new machines
  const machinesGridRef = useRef(null)

  // Scroll to top of machines grid
  const scrollToNewMachine = () => {
    // Scroll to top of page smoothly
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Show demo toast
  const showDemoToast = (message, type = 'success') => {
    setDemoToast({ message, type })
    setTimeout(() => setDemoToast(null), 3000)
  }

  // Fetch VAST.ai account balance
  const fetchVastBalance = async () => {
    if (isDemo) {
      setVastBalance({ credit: 127.45, spent: 23.55 })
      return
    }
    try {
      const res = await apiGet('/api/v1/instances/balance')
      if (res.ok) {
        const data = await res.json()
        setVastBalance(data)
      }
    } catch (e) {
      // Silently fail - balance is not critical
    }
  }


  useEffect(() => {
    fetchMachines()
    fetchVastBalance()
    if (!isDemo) {
      const interval = setInterval(fetchMachines, 5000)
      const balanceInterval = setInterval(fetchVastBalance, 30000) // Update balance every 30s
      return () => {
        clearInterval(interval)
        clearInterval(balanceInterval)
      }
    }
  }, [])

  // Handle selectedOffer from Dashboard navigation - AUTO CREATE without modal
  useEffect(() => {
    // Prevent double execution from React Strict Mode
    if (offerProcessedRef.current) return

    if (location.state?.selectedOffer) {
      offerProcessedRef.current = true // Mark as processed BEFORE doing anything
      const offer = location.state.selectedOffer
      // Clear the state IMMEDIATELY to prevent reopening on refresh
      window.history.replaceState({}, document.title, window.location.pathname)
      // Directly create instance without showing modal
      handleCreateInstance(offer)
    }
  }, []) // Run only once on mount


  // Auto-sync every 30 seconds for running machines
  useEffect(() => {
    const syncInterval = setInterval(() => {
      const runningMachines = machines.filter(m => m.actual_status === 'running')
      runningMachines.forEach(m => {
        const lastSync = lastSyncTime[m.id] || 0
        const now = Date.now()
        // Auto-sync every 30 seconds
        if (now - lastSync > 30000) {
          handleAutoSync(m.id)
        }
      })
    }, 10000) // Check every 10 seconds
    return () => clearInterval(syncInterval)
  }, [machines, lastSyncTime])

  const fetchMachines = async () => {
    try {
      // In demo mode, use local demo data for more interactivity
      if (isDemo) {
        // Simulate loading delay
        await new Promise(r => setTimeout(r, 500))
        setMachines(DEMO_MACHINES)
        setError(null)
        setLoading(false)
        return
      }

      const res = await apiGet('/api/v1/instances')
      if (!res.ok) {
        // If unauthorized, don't show error - user will be redirected to login
        if (res.status === 401) {
          setMachines([])
          setError(null)
          return
        }
        throw new Error(`Error fetching machines (${res.status})`)
      }
      const data = await res.json()
      setMachines(data.instances || [])
      setError(null)
    } catch (err) {
      // Network errors or API unavailable - show empty state instead of error
      console.error('Error fetching machines:', err)
      setMachines([])
      setError(null)
    } finally {
      setLoading(false)
    }
  }

  const openDestroyDialog = (machineId, machineName) => {
    setDestroyDialog({ open: true, machineId, machineName })
  }

  const confirmDestroy = async () => {
    const { machineId, machineName } = destroyDialog
    setDestroyDialog({ open: false, machineId: null, machineName: '' })

    // Add to deleting machines set for animation
    setDeletingMachines(prev => new Set([...prev, machineId]))

    if (isDemo) {
      // Demo mode: simulate destruction with animation
      showDemoToast(t('machines.toast.destroying', { name: machineName }), 'warning')
      await new Promise(r => setTimeout(r, 1500))
      setMachines(prev => prev.filter(m => m.id !== machineId))
      setDeletingMachines(prev => {
        const next = new Set(prev)
        next.delete(machineId)
        return next
      })
      showDemoToast(t('machines.toast.destroyedSuccess', { name: machineName }), 'success')
      return
    }

    try {
      const res = await apiDelete(`/api/v1/instances/${machineId}`)
      if (!res.ok) throw new Error(t('machines.errors.destroyMachine'))
      fetchMachines()
    } catch (err) {
      alert(err.message)
    } finally {
      // Remove from deleting machines set
      setDeletingMachines(prev => {
        const next = new Set(prev)
        next.delete(machineId)
        return next
      })
    }
  }

  // Create instance from offer (called from Dashboard or Nova Máquina)
  const handleCreateInstance = async (offer) => {
    if (isDemo) {
      showDemoToast(t('machines.toast.creatingDemo'), 'info')
      await new Promise(r => setTimeout(r, 2000))
      const newMachineId = Date.now()
      const newMachine = {
        id: newMachineId,
        gpu_name: offer.gpu_name,
        num_gpus: offer.num_gpus || 1,
        gpu_ram: offer.gpu_ram,
        cpu_cores: offer.cpu_cores,
        cpu_ram: offer.cpu_ram,
        disk_space: offer.disk_space,
        dph_total: offer.dph_total,
        actual_status: 'loading',
        status: 'loading',
        start_date: new Date().toISOString(),
        public_ipaddr: null,
        ssh_host: 'ssh.vast.ai',
        ssh_port: 22000 + Math.floor(Math.random() * 1000),
        cpu_standby: { enabled: true, state: 'syncing' }
      }
      setMachines(prev => [newMachine, ...prev])
      // Add to new machines set for highlight animation
      setNewMachineIds(prev => new Set([...prev, newMachineId]))
      // Scroll to top to show new machine
      setTimeout(() => scrollToNewMachine(), 100)
      // Simulate boot time - change to running after 3s
      setTimeout(() => {
        setMachines(prev => prev.map(m =>
          m.id === newMachineId
            ? { ...m, actual_status: 'running', status: 'running', public_ipaddr: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}` }
            : m
        ))
      }, 3000)
      // Remove highlight after 5 seconds
      setTimeout(() => {
        setNewMachineIds(prev => {
          const next = new Set(prev)
          next.delete(newMachineId)
          return next
        })
      }, 5000)
      setCreateModal({ open: false, offer: null, creating: false, error: null })
      showDemoToast(t('machines.toast.createdWithStandby', { name: offer.gpu_name }), 'success')
      return
    }

    // Show toast that we're creating
    showDemoToast(t('machines.toast.creating', { name: offer.gpu_name }), 'info')

    try {
      const res = await apiPost('/api/v1/instances', {
        offer_id: offer.id,
        disk_size: offer.disk_space || 100,
        label: `${offer.gpu_name} - ${new Date().toLocaleDateString()}`
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || data.error || t('machines.errors.createInstance'))
      }

      const data = await res.json()
      setCreateModal({ open: false, offer: null, creating: false, error: null })

      // Track new machine ID for highlight animation
      const newInstanceId = data.id || data.instance_id
      if (newInstanceId) {
        setNewMachineIds(prev => new Set([...prev, newInstanceId]))
        // Remove highlight after 5 seconds
        setTimeout(() => {
          setNewMachineIds(prev => {
            const next = new Set(prev)
            next.delete(newInstanceId)
            return next
          })
        }, 5000)
      }

      fetchMachines()

      // Scroll to top to show new machine
      setTimeout(() => scrollToNewMachine(), 500)

      // Show success message
      showDemoToast(t('machines.toast.createdProvisioningStandby', { name: offer.gpu_name }), 'success')

    } catch (err) {
      // Show error as toast instead of modal
      showDemoToast(err.message, 'error')
      setCreateModal({ open: false, offer: null, creating: false, error: null })
    }
  }

  const handleStart = async (machineId) => {
    if (isDemo) {
      // Demo mode: simulate starting
      const machine = machines.find(m => m.id === machineId)
      const machineName = machine?.gpu_name || t('common.machine')
      showDemoToast(t('machines.toast.starting', { name: machineName }), 'info')
      await new Promise(r => setTimeout(r, 2000))
      setMachines(prev => prev.map(m =>
        m.id === machineId
          ? {
            ...m,
            actual_status: 'running',
            status: 'running',
            start_date: new Date().toISOString(),
            public_ipaddr: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
            gpu_util: Math.floor(Math.random() * 30) + 10,
            gpu_temp: Math.floor(Math.random() * 15) + 55
          }
          : m
      ))
      showDemoToast(t('machines.toast.started', { name: machineName }), 'success')
      return
    }

    try {
      const res = await apiPost(`/api/v1/instances/${machineId}/resume`)
      if (!res.ok) throw new Error(t('machines.errors.startMachine'))
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  const handlePause = async (machineId) => {
    if (isDemo) {
      // Demo mode: simulate pausing
      const machine = machines.find(m => m.id === machineId)
      const machineName = machine?.gpu_name || t('common.machine')
      showDemoToast(t('machines.toast.pausing', { name: machineName }), 'info')
      await new Promise(r => setTimeout(r, 1500))
      setMachines(prev => prev.map(m =>
        m.id === machineId
          ? {
            ...m,
            actual_status: 'stopped',
            status: 'stopped',
            public_ipaddr: null,
            gpu_util: 0,
            gpu_temp: 0
          }
          : m
      ))
      showDemoToast(t('machines.toast.paused', { name: machineName }), 'success')
      return
    }

    try {
      const res = await apiPost(`/api/v1/instances/${machineId}/pause`)
      if (!res.ok) throw new Error(t('machines.errors.pauseMachine'))
      fetchMachines()
    } catch (err) {
      alert(err.message)
    }
  }

  // Create manual snapshot (using new incremental sync endpoint)
  const handleSnapshot = async (machineId) => {
    if (isDemo) {
      // Demo mode: simulate snapshot
      const machine = machines.find(m => m.id === machineId)
      setSyncStatus(prev => ({ ...prev, [machineId]: 'syncing' }))
      showDemoToast(t('machines.toast.creatingSnapshot', { name: machine?.gpu_name }), 'info')
      await new Promise(r => setTimeout(r, 2500))

      const demoStats = {
        files_new: Math.floor(Math.random() * 50) + 5,
        files_changed: Math.floor(Math.random() * 100) + 20,
        files_unmodified: Math.floor(Math.random() * 500) + 200,
        data_added: `${(Math.random() * 500 + 50).toFixed(1)} MB`,
        duration_seconds: (Math.random() * 10 + 2).toFixed(1),
        is_incremental: true
      }

      setSyncStatus(prev => ({ ...prev, [machineId]: 'synced' }))
      setLastSyncTime(prev => ({ ...prev, [machineId]: Date.now() }))
      setSyncStats(prev => ({ ...prev, [machineId]: demoStats }))
      showDemoToast(t('machines.toast.snapshotComplete', { size: demoStats.data_added }), 'success')
      return
    }

    try {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'syncing' }))

      // Use new sync endpoint with force=true for manual sync
      const res = await apiPost(`/api/v1/instances/${machineId}/sync?force=true`)

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || errorData.error || t('machines.errors.syncFailed'))
      }

      const data = await res.json()

      setSyncStatus(prev => ({ ...prev, [machineId]: 'synced' }))
      setLastSyncTime(prev => ({ ...prev, [machineId]: Date.now() }))
      setSyncStats(prev => ({ ...prev, [machineId]: data }))

      // Show sync result with better visibility
      const syncType = data.is_incremental ? 'Incremental sync' : 'Initial sync'
      const message = `${syncType} completed in ${data.duration_seconds.toFixed(1)}s!\n\n` +
        `New files: ${data.files_new}\n` +
        `Modified files: ${data.files_changed}\n` +
        `Unchanged files: ${data.files_unmodified}\n` +
        `Data sent: ${data.data_added}`

      alert(message)

      // Show success toast if in demo mode helper
      if (showDemoToast) {
        showDemoToast(`Snapshot complete! ${data.data_added} synced`, 'success')
      }
    } catch (err) {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
      alert(`Error creating snapshot: ${err.message}`)
    }
  }

  // Auto-sync (using new incremental sync endpoint)
  const handleAutoSync = async (machineId) => {
    // Skip in demo mode - no real machines to sync
    if (isDemo) return

    // Check if already syncing
    if (syncStatus[machineId] === 'syncing') return

    try {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'syncing' }))
      // Use new sync endpoint (without force - respects 30s minimum interval)
      const res = await apiPost(`/api/v1/instances/${machineId}/sync`)

      if (res.ok) {
        const data = await res.json()
        if (data.success) {
          setSyncStatus(prev => ({ ...prev, [machineId]: 'synced' }))
          setLastSyncTime(prev => ({ ...prev, [machineId]: Date.now() }))
          setSyncStats(prev => ({ ...prev, [machineId]: data }))
          // Reset to idle after 5 seconds
          setTimeout(() => {
            setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
          }, 5000)
        } else {
          // Sync skipped (too soon or error)
          setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
        }
      } else {
        setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
      }
    } catch {
      setSyncStatus(prev => ({ ...prev, [machineId]: 'idle' }))
    }
  }

  // Restore to new machine - redirect to dashboard with restore param
  const handleRestoreToNew = (machine) => {
    window.location.href = `/?restore_from=${machine.id}`
  }

  const handleMigrate = (machine) => {
    // Always open the migration modal - it handles both CPU Standby and regular migration
    setMigrationTarget(machine)
  }

  const handleMigrationSuccess = (result) => {
    fetchMachines()
    setMigrationTarget(null)
  }

  // Simulate GPU failover (demo mode only) - with enriched metrics
  const handleSimulateFailover = async (machine) => {
    if (!machine.cpu_standby?.enabled) {
      showDemoToast(t('machines.toast.noCpuStandby'), 'error')
      return
    }

    // Initialize failover metrics
    const failoverMetrics = {
      id: `fo-${Date.now()}`,
      machine_id: machine.id,
      gpu_name: machine.gpu_name,
      started_at: new Date().toISOString(),
      detection_time_ms: 0,
      failover_time_ms: 0,
      search_time_ms: 0,
      provisioning_time_ms: 0,
      restore_time_ms: 0,
      total_time_ms: 0,
      files_synced: 0,
      data_restored_mb: 0,
      new_gpu_name: null,
      cpu_standby_ip: machine.cpu_standby.ip,
      reason: 'spot_preemption',
      status: 'in_progress',
      phases: []
    }

    // Helper to update failover progress with metrics
    const updateProgress = (phase, message, newGpu = null, phaseMetrics = {}) => {
      const timestamp = Date.now()
      failoverMetrics.phases.push({ phase, timestamp, ...phaseMetrics })

      setFailoverProgress(prev => ({
        ...prev,
        [machine.id]: {
          phase,
          message,
          newGpu,
          metrics: { ...failoverMetrics, ...phaseMetrics }
        }
      }))
    }

    // Phase 1: GPU Lost - Detect the interruption
    const phaseStart = Date.now()
    const detectionTime = Math.floor(Math.random() * 500) + 500 // 500-1000ms
    updateProgress('gpu_lost', t('machines.failover.gpuLost', { name: machine.gpu_name }))
    showDemoToast(t('machines.toast.gpuInterrupted', { name: machine.gpu_name }), 'warning')

    // Update machine status
    setMachines(prev => prev.map(m =>
      m.id === machine.id ? {
        ...m,
        actual_status: 'failover',
        status: 'failover',
        cpu_standby: { ...m.cpu_standby, state: 'failover_active' }
      } : m
    ))

    await new Promise(r => setTimeout(r, 2000))
    failoverMetrics.detection_time_ms = detectionTime

    // Phase 2: Failover to CPU Standby
    const failoverTime = Math.floor(Math.random() * 300) + 800 // 800-1100ms
    updateProgress('failover_active', t('machines.failover.failoverActive', { ip: machine.cpu_standby.ip }), null, { detection_time_ms: detectionTime })
    showDemoToast(t('machines.toast.failoverUsingCpu', { ip: machine.cpu_standby.ip }), 'info')
    await new Promise(r => setTimeout(r, 2500))
    failoverMetrics.failover_time_ms = failoverTime

    // Phase 3: Searching for new GPU
    const searchTime = Math.floor(Math.random() * 2000) + 2000 // 2-4 seconds
    updateProgress('searching', t('machines.failover.searching'), null, { failover_time_ms: failoverTime })
    showDemoToast(t('machines.failover.searching'), 'info')
    await new Promise(r => setTimeout(r, 3000))
    failoverMetrics.search_time_ms = searchTime

    // Phase 4: Provisioning new GPU
    const gpuOptions = ['RTX 4090', 'RTX 4080', 'RTX 3090', 'A100 40GB', 'A100 80GB', 'H100 80GB']
    const newGpu = gpuOptions[Math.floor(Math.random() * gpuOptions.length)]
    const provisioningTime = Math.floor(Math.random() * 20000) + 30000 // 30-50 seconds
    failoverMetrics.new_gpu_name = newGpu
    updateProgress('provisioning', t('machines.failover.provisioning', { name: newGpu }), newGpu, { search_time_ms: searchTime })
    showDemoToast(t('machines.toast.provisioningNewGpu', { name: newGpu }), 'info')
    await new Promise(r => setTimeout(r, 3500))
    failoverMetrics.provisioning_time_ms = provisioningTime

    // Phase 5: Restoring data
    const filesCount = Math.floor(Math.random() * 3000) + 1000
    const dataSize = Math.floor(Math.random() * 2000) + 500 // 500-2500 MB
    const restoreTime = Math.floor(Math.random() * 20000) + 20000 // 20-40 seconds
    failoverMetrics.files_synced = filesCount
    failoverMetrics.data_restored_mb = dataSize
    failoverMetrics.restore_time_ms = restoreTime
    updateProgress('restoring', t('machines.failover.restoring', { count: filesCount.toLocaleString(), size: dataSize }), newGpu, { provisioning_time_ms: provisioningTime })
    showDemoToast(t('machines.toast.restoringFiles', { count: filesCount.toLocaleString() }), 'info')
    await new Promise(r => setTimeout(r, 4000))

    // Phase 6: Complete
    const totalTime = Date.now() - phaseStart
    failoverMetrics.total_time_ms = totalTime
    failoverMetrics.status = 'success'
    failoverMetrics.completed_at = new Date().toISOString()

    updateProgress('complete', t('machines.failover.complete', { name: newGpu }), newGpu, {
      restore_time_ms: restoreTime,
      total_time_ms: totalTime,
      files_synced: filesCount,
      data_restored_mb: dataSize
    })

    // Update machine with new GPU
    setMachines(prev => prev.map(m =>
      m.id === machine.id ? {
        ...m,
        gpu_name: newGpu,
        actual_status: 'running',
        status: 'running',
        cpu_standby: { ...m.cpu_standby, state: 'ready', sync_count: (m.cpu_standby.sync_count || 0) + 1 },
        public_ipaddr: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`
      } : m
    ))

    showDemoToast(t('machines.toast.recoveryComplete', { time: (totalTime / 1000).toFixed(1), name: newGpu }), 'success')

    // Save to failover history
    setFailoverHistory(prev => [...prev, failoverMetrics])

    // Also save to localStorage for persistence
    try {
      const existingHistory = JSON.parse(localStorage.getItem('failover_history') || '[]')
      existingHistory.push(failoverMetrics)
      // Keep only last 100 entries
      if (existingHistory.length > 100) existingHistory.shift()
      localStorage.setItem('failover_history', JSON.stringify(existingHistory))
    } catch (e) {
      console.error('Failed to save failover history:', e)
    }

    // Clear progress after 5 seconds
    setTimeout(() => {
      setFailoverProgress(prev => ({
        ...prev,
        [machine.id]: { phase: 'idle' }
      }))
    }, 5000)
  }

  // Navigate to new machine page
  const goToNewMachine = () => {
    const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'
    navigate(`${basePath}/machines/new`)
  }

  // States where machine is loading/starting
  const loadingStates = ['loading', 'creating', 'starting', 'pending', 'provisioning', 'configuring']

  // Sort function: most recent first (by start_date or id as fallback)
  const sortByRecent = (a, b) => {
    const dateA = a.start_date ? new Date(a.start_date).getTime() : a.id
    const dateB = b.start_date ? new Date(b.start_date).getTime() : b.id
    return dateB - dateA // Most recent first
  }

  // Filter out machines that are in a provisioning race (they only appear after winner is selected)
  const visibleMachines = useMemo(() => {
    return machines.filter(m => !racingInstanceIds.includes(m.id))
  }, [machines, racingInstanceIds])

  // Group machines: Loading → Running → Stopped (using visibleMachines instead of machines)
  const loadingMachines = visibleMachines.filter(m => loadingStates.includes(m.actual_status)).sort(sortByRecent)
  const runningMachines = visibleMachines.filter(m => m.actual_status === 'running').sort(sortByRecent)
  const stoppedMachines = visibleMachines.filter(m =>
    !loadingStates.includes(m.actual_status) && m.actual_status !== 'running'
  ).sort(sortByRecent)

  // For stats, "active" includes loading + running
  const activeMachines = [...loadingMachines, ...runningMachines]
  const inactiveMachines = stoppedMachines

  // Build filtered list: Loading always first, then based on filter
  const filteredMachines = filter === 'online'
    ? [...loadingMachines, ...runningMachines]
    : filter === 'offline'
      ? stoppedMachines
      : [...loadingMachines, ...runningMachines, ...stoppedMachines]

  const totalCostPerHour = activeMachines.reduce((acc, m) => acc + (m.total_dph || m.dph_total || 0), 0)
  const totalCpuStandbyCount = activeMachines.filter(m => m.cpu_standby?.enabled).length

  if (loading) {
    return (
      <div className="page-container">
        <div className="ta-card p-6">
          <SkeletonList count={4} type="machine" />
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Page Header - TailAdmin Style */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 flex items-center justify-center border border-emerald-500/20">
              <Server className="w-6 h-6 text-emerald-400" />
            </div>
            <div className="flex flex-col justify-center">
              <h1 className="page-title leading-tight">My Machines</h1>
              <p className="page-subtitle mt-0.5">Manage your GPU and CPU instances</p>
            </div>
          </div>
          <button
            onClick={goToNewMachine}
            className="ta-btn ta-btn-primary"
          >
            <Plus className="w-4 h-4" />
            New Machine
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">Total</p>
              <p className="stat-card-value">{visibleMachines.length}</p>
            </div>
            <Server className="w-5 h-5 text-gray-400" />
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">Active</p>
              <p className="stat-card-value text-emerald-400">{activeMachines.length}</p>
            </div>
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">Protected</p>
              <p className="stat-card-value text-cyan-400">{totalCpuStandbyCount}</p>
            </div>
            <Shield className="w-5 h-5 text-cyan-400" />
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-card-label">Cost/Hour</p>
              <p className="stat-card-value text-amber-400">${totalCostPerHour.toFixed(2)}</p>
            </div>
            <DollarSign className="w-5 h-5 text-amber-400" />
          </div>
        </div>
      </div>


      {/* Filter Tabs - Enhanced Style */}
      <div className="ta-card">
        <div className="ta-card-header">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              {[
                { id: 'all', label: 'All', count: visibleMachines.length, icon: Server },
                { id: 'online', label: 'Online', count: activeMachines.length, icon: Activity, color: 'text-emerald-400' },
                { id: 'offline', label: 'Offline', count: inactiveMachines.length, icon: null, color: 'text-gray-400' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFilter(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    filter === tab.id
                      ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700/50 border border-transparent'
                  }`}
                >
                  {tab.icon && <tab.icon className={`w-4 h-4 ${filter === tab.id ? 'text-brand-400' : tab.color || ''}`} />}
                  <span>{tab.label}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${
                    filter === tab.id ? 'bg-brand-500/30 text-brand-300' : 'bg-gray-700 text-gray-400'
                  }`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Auto-refresh</span>
            </div>
          </div>
        </div>

        <div className="ta-card-body">

          {/* Error */}
          {error && (
            <ErrorState
              message={error}
              onRetry={fetchMachines}
              retryText="Try again"
              autoRetry={true}
              autoRetryDelay={10000}
            />
          )}

          {/* Machines Grid - Like Dashboard tier cards */}
          {!error && filteredMachines.length === 0 ? (
            <EmptyState
              icon="server"
              title={filter === 'all' ? 'No machines' : filter === 'online' ? 'No online machines' : 'No offline machines'}
              description={filter === 'all'
                ? 'Create your first GPU machine to get started.'
                : filter === 'online'
                  ? 'All your machines are offline. Start one to begin.'
                  : 'All your machines are online.'}
              action={goToNewMachine}
              actionText="Create machine"
            />
          ) : !error && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {filteredMachines.map((machine) => (
                <MachineCard
                  key={machine.id}
                  machine={machine}
                  onDestroy={(id) => openDestroyDialog(id, machine.gpu_name || 'GPU')}
                  onStart={handleStart}
                  onPause={handlePause}
                  onRestoreToNew={handleRestoreToNew}
                  onSnapshot={handleSnapshot}
                  onMigrate={handleMigrate}
                  onSimulateFailover={isDemo ? handleSimulateFailover : null}
                  syncStatus={syncStatus[machine.id] || 'idle'}
                  syncStats={syncStats[machine.id]}
                  failoverProgress={failoverProgress[machine.id] || { phase: 'idle' }}
                  isNew={newMachineIds.has(machine.id)}
                  isDeleting={deletingMachines.has(machine.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Destroy Confirmation Modal */}
      <ConfirmModal
        isOpen={destroyDialog.open}
        onClose={() => setDestroyDialog({ open: false, machineId: null, machineName: '' })}
        onConfirm={confirmDestroy}
        title="Destroy machine?"
        message={`Are you sure you want to destroy ${destroyDialog.machineName}? This action is irreversible and all unsaved data will be lost.`}
        variant="danger"
      />

      {/* Migration Modal */}
      <MigrationModal
        instance={migrationTarget}
        isOpen={!!migrationTarget}
        onClose={() => setMigrationTarget(null)}
        onSuccess={handleMigrationSuccess}
      />

      {/* Create Instance Modal */}
      <AlertDialog open={createModal.open} onOpenChange={(open) => !createModal.creating && setCreateModal(prev => ({ ...prev, open }))}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-green-400" />
              Create GPU Machine
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4 pt-2">
                {createModal.offer && (
                  <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/50">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-white font-semibold">{createModal.offer.gpu_name}</span>
                      <span className="text-green-400 font-mono">${createModal.offer.dph_total?.toFixed(3)}/h</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                      <div>VRAM: {Math.round((createModal.offer.gpu_ram || 24000) / 1024)} GB</div>
                      <div>CPU: {createModal.offer.cpu_cores || 4} cores</div>
                      <div>RAM: {Math.round((createModal.offer.cpu_ram || 16000) / 1024)} GB</div>
                      <div>Disk: {Math.round(createModal.offer.disk_space || 100)} GB</div>
                    </div>
                  </div>
                )}
                <div className="p-3 rounded-lg border border-cyan-700/50 bg-cyan-900/20">
                  <div className="flex items-center gap-2 text-cyan-300 text-sm">
                    <Shield className="w-4 h-4" />
                    <span>CPU Standby will be created automatically</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1 ml-6">
                    A backup VM will be provisioned for protection against interruptions.
                  </p>
                </div>
                {createModal.error && (
                  <div className="p-3 rounded-lg border border-red-700/50 bg-red-900/20 text-red-300 text-sm">
                    {createModal.error}
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={createModal.creating}>Cancel</AlertDialogCancel>
            <button
              onClick={() => handleCreateInstance(createModal.offer)}
              disabled={createModal.creating}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:cursor-not-allowed rounded-lg transition-colors"
              data-testid="confirm-create-instance"
            >
              {createModal.creating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Machine
                </>
              )}
            </button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Demo Toast Notification */}
      {demoToast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 animate-slide-up ${demoToast.type === 'success' ? 'bg-green-900/90 border-green-500/50 text-green-100' :
          demoToast.type === 'warning' ? 'bg-yellow-900/90 border-yellow-500/50 text-yellow-100' :
            demoToast.type === 'error' ? 'bg-red-900/90 border-red-500/50 text-red-100' :
              'bg-cyan-900/90 border-cyan-500/50 text-cyan-100'
          }`}>
          {demoToast.type === 'success' && <Check className="w-5 h-5" />}
          {demoToast.type === 'warning' && <RefreshCw className="w-5 h-5 animate-spin" />}
          {demoToast.type === 'info' && <RefreshCw className="w-5 h-5 animate-spin" />}
          <span className="text-sm font-medium">{demoToast.message}</span>
        </div>
      )}

      <style>{`
        @keyframes slide-up {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
        @keyframes highlight-new {
          0%, 100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }
          50% { box-shadow: 0 0 20px 5px rgba(74, 222, 128, 0.4); }
        }
        .animate-highlight-new {
          animation: highlight-new 1s ease-in-out 3;
        }
      `}</style>
    </div>
  )
}

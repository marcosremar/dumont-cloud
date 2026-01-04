import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { ArrowLeft, Plus } from 'lucide-react'
import { WizardForm } from '../components/dashboard'
import { apiPost, apiGet, apiDelete } from '../utils/api'
import { useToast } from '../components/Toast'
import {
  addRacingInstance,
  addRacingInstances,
  setRaceWinner,
  clearRacingInstances,
} from '../store/slices/instancesSlice'
import { useProvisioningRace, createDefaultApiService, RACE_STATUS } from '../hooks/useProvisioningRace'

/**
 * Dedicated page for creating a new GPU machine
 * Uses provisioning race: creates 5 machines, picks the first to connect
 * If none connect in 15 seconds, destroys all and tries another 5 (up to 3 rounds)
 */
export default function NewMachine() {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch()
  const toast = useToast()

  // Base path for navigation
  const basePath = '/app'

  // Wizard state
  const [wizardLoading, setWizardLoading] = useState(false)
  const [searchCountry, setSearchCountry] = useState('')
  const [selectedLocations, setSelectedLocations] = useState([]) // Multi-select: array of locations
  const [selectedGPU, setSelectedGPU] = useState('any')
  const [selectedGPUCategory, setSelectedGPUCategory] = useState('any')
  const [selectedTier, setSelectedTier] = useState(null)
  const [provisioningMode, setProvisioningMode] = useState(false)

  // API service for provisioning race
  const apiService = useMemo(() => createDefaultApiService(''), [])

  // Provisioning race hook - 5 candidates, 3 rounds, 15 second timeout per round
  const {
    candidates: raceCandidates,
    winner: raceWinner,
    raceStatus,
    currentRound,
    error: raceError,
    elapsedTime,
    maxRounds,
    isRacing,
    isCompleted,
    isFailed,
    startRace,
    cancelRace,
    completeRace,
    reset: resetRace,
    getCreatedInstanceIds,
  } = useProvisioningRace(apiService, {
    maxCandidates: 5,
    maxRounds: 3,
    pollIntervalMs: 2000,      // Poll every 2 seconds
    timeoutMs: 15 * 1000,      // 15 seconds timeout per round
    createDelayMs: 300,        // 300ms delay between creates
  })

  // Handle search change
  const handleSearchChange = (value) => {
    setSearchCountry(value)
  }

  // Handle country click (from map or search) - multi-select
  const handleCountryClick = (locationData) => {
    setSelectedLocations(prev => {
      // Check if already selected (by name)
      const exists = prev.some(loc => loc.name === locationData.name)
      if (exists) {
        // Remove if already selected
        return prev.filter(loc => loc.name !== locationData.name)
      }
      // Add to selections
      return [...prev, locationData]
    })
    setSearchCountry('')
  }

  // Handle clear single selection
  const handleClearSingleSelection = (locationName) => {
    setSelectedLocations(prev => prev.filter(loc => loc.name !== locationName))
  }

  // Handle clear all selections
  const handleClearSelection = () => {
    setSelectedLocations([])
    setSearchCountry('')
  }

  // Region data mapping (same as COUNTRY_DATA in constants) - English names
  const REGION_DATA = {
    'usa': { codes: ['US', 'CA', 'MX'], name: 'USA', isRegion: true },
    'europe': { codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'], name: 'Europe', isRegion: true },
    'asia': { codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'], name: 'Asia', isRegion: true },
    'south america': { codes: ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'], name: 'South America', isRegion: true },
  }

  // Handle region select - multi-select
  const handleRegionSelect = (regionKey) => {
    const regionData = REGION_DATA[regionKey]
    if (regionData) {
      setSelectedLocations(prev => {
        const exists = prev.some(loc => loc.name === regionData.name)
        if (exists) {
          return prev.filter(loc => loc.name !== regionData.name)
        }
        return [...prev, regionData]
      })
    }
    setSearchCountry('')
  }

  // Handle wizard submit - start provisioning race
  const handleWizardSubmit = async (data) => {
    console.log('[NewMachine] handleWizardSubmit called with:', data)

    // Get all available offers for racing
    const allOffers = data?.allOffers || []

    if (allOffers.length === 0) {
      toast?.error('Erro: Nenhuma máquina disponível')
      console.error('[NewMachine] No offers available for racing')
      return
    }

    console.log('[NewMachine] Starting provisioning race with', allOffers.length, 'offers')

    // Enter provisioning mode
    setProvisioningMode(true)
    setWizardLoading(true)

    // Add all potential racing instance IDs to Redux (to hide from Machines page)
    // Note: The hook will handle actual instance creation and tracking

    // Start the race with all available offers
    // The hook will:
    // - Create 5 machines in round 1
    // - Poll their status every 2 seconds
    // - If none connects in 15 seconds, destroy all and try round 2
    // - Repeat up to 3 rounds
    // - First machine to become 'running' wins
    startRace(allOffers)
  }

  // Sync racing instances with Redux when they're created
  useEffect(() => {
    if (isRacing) {
      const instanceIds = getCreatedInstanceIds()
      if (instanceIds.length > 0) {
        dispatch(addRacingInstances(instanceIds))
      }
    }
  }, [isRacing, raceCandidates, dispatch, getCreatedInstanceIds])

  // Handle race completion
  useEffect(() => {
    if (isCompleted && raceWinner) {
      setWizardLoading(false)
      toast?.success('Máquina reservada com sucesso!')
    }
  }, [isCompleted, raceWinner, toast])

  // Handle race failure
  useEffect(() => {
    if (isFailed && raceError) {
      setWizardLoading(false)
      toast?.error(raceError || 'Falha ao reservar máquina após 3 tentativas')
    }
  }, [isFailed, raceError, toast])

  // Cancel provisioning race
  const cancelProvisioningRace = async () => {
    // Cancel the race (hook will destroy all created instances)
    await cancelRace()

    // Clear all racing instances from Redux
    dispatch(clearRacingInstances())

    setProvisioningMode(false)
    setWizardLoading(false)
  }

  // Complete provisioning and go to machines
  const completeProvisioningRace = () => {
    // Mark winner in Redux - this removes it from racing list so it appears in Machines
    if (raceWinner) {
      const winnerId = raceWinner.instanceId || raceWinner.id
      if (winnerId) {
        dispatch(setRaceWinner(winnerId))
      }
    }

    // Complete the race (cleanup)
    completeRace()

    // Clear any remaining racing instances
    dispatch(clearRacingInstances())

    navigate(`${basePath}/machines`)
  }

  // Go back to machines page
  const handleBack = async () => {
    // Cancel and cleanup racing instances if user goes back without completing
    if (provisioningMode) {
      await cancelRace()
      dispatch(clearRacingInstances())
    }
    navigate(`${basePath}/machines`)
  }

  // Cleanup racing instances on unmount (if user navigates away)
  useEffect(() => {
    return () => {
      // Only clear if there's an active race (not completed)
      if (provisioningMode && !raceWinner) {
        cancelRace()
        dispatch(clearRacingInstances())
      }
    }
  }, [provisioningMode, raceWinner, dispatch, cancelRace])

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Plus className="w-9 h-9 flex-shrink-0 text-brand-400" />
            <div className="flex flex-col justify-center">
              <h1 className="page-title leading-tight">New GPU Machine</h1>
              <p className="page-subtitle mt-0.5">Configure and provision a new instance</p>
            </div>
          </div>
          <button
            onClick={handleBack}
            className="ta-btn ta-btn-secondary"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </div>
      </div>

      {/* Wizard Form */}
      <div className="ta-card">
        <div className="ta-card-body">
          <WizardForm
            selectedLocations={selectedLocations}
            onSearchChange={handleSearchChange}
            searchCountry={searchCountry}
            onRegionSelect={handleRegionSelect}
            onCountryClick={handleCountryClick}
            onClearSelection={handleClearSelection}
            onClearSingleSelection={handleClearSingleSelection}
            selectedGPU={selectedGPU}
            onSelectGPU={setSelectedGPU}
            selectedGPUCategory={selectedGPUCategory}
            onSelectGPUCategory={setSelectedGPUCategory}
            selectedTier={selectedTier}
            onSelectTier={setSelectedTier}
            onSubmit={handleWizardSubmit}
            loading={wizardLoading}
            isProvisioning={provisioningMode}
            provisioningCandidates={raceCandidates}
            provisioningWinner={raceWinner}
            currentRound={currentRound}
            maxRounds={maxRounds}
            elapsedTime={elapsedTime}
            raceError={raceError}
            isFailed={isFailed}
            onCancelProvisioning={cancelProvisioningRace}
            onCompleteProvisioning={completeProvisioningRace}
          />
        </div>
      </div>
    </div>
  )
}

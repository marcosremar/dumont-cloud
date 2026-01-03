import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { ArrowLeft, Plus } from 'lucide-react'
import { WizardForm } from '../components/dashboard'
import { apiPost } from '../utils/api'
import { useToast } from '../components/Toast'
import {
  addRacingInstance,
  addRacingInstances,
  setRaceWinner,
  clearRacingInstances,
} from '../store/slices/instancesSlice'

/**
 * Dedicated page for creating a new GPU machine
 * Separated from Machines page for better UX
 */
export default function NewMachine() {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch()
  const toast = useToast()

  // Base path for navigation
  const basePath = '/app'

  // Check if demo mode
  const isDemo = location.pathname.startsWith('/demo-app') || localStorage.getItem('dumont_demo_mode') === 'true'

  // Wizard state
  const [wizardLoading, setWizardLoading] = useState(false)
  const [searchCountry, setSearchCountry] = useState('')
  const [selectedLocations, setSelectedLocations] = useState([]) // Multi-select: array of locations
  const [selectedGPU, setSelectedGPU] = useState('any')
  const [selectedGPUCategory, setSelectedGPUCategory] = useState('any')
  const [selectedTier, setSelectedTier] = useState(null)
  const [raceCandidates, setRaceCandidates] = useState([])
  const [raceWinner, setRaceWinner] = useState(null)
  const [provisioningMode, setProvisioningMode] = useState(false)
  const [currentRound, setCurrentRound] = useState(1)

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

  // Handle wizard submit - start provisioning
  const handleWizardSubmit = async (data) => {
    console.log('[NewMachine] handleWizardSubmit called with:', data)

    if (isDemo) {
      // Demo mode - simulate provisioning
      setProvisioningMode(true)
      setWizardLoading(true)

      // Generate demo instance IDs
      const demoIds = [Date.now() + 1, Date.now() + 2, Date.now() + 3]

      // Simulate finding candidates
      setTimeout(() => {
        const candidates = [
          { id: demoIds[0], gpu: 'RTX 4090', price: 0.45, location: 'US', status: 'testing' },
          { id: demoIds[1], gpu: 'RTX 4090', price: 0.48, location: 'EU', status: 'testing' },
          { id: demoIds[2], gpu: 'RTX 4080', price: 0.35, location: 'US', status: 'testing' },
        ]
        setRaceCandidates(candidates)

        // Add all candidates to racing state (hidden from Machines page)
        dispatch(addRacingInstances(demoIds))
      }, 1000)

      // Simulate finding winner
      setTimeout(() => {
        const winner = { id: demoIds[0], gpu: 'RTX 4090', price: 0.45, location: 'US' }
        setRaceWinner(winner)
        setWizardLoading(false)
      }, 3000)

      return
    }

    // Validate we have an offer_id
    const offerId = data?.offerId
    if (!offerId) {
      toast?.error('Error: No machine selected')
      console.error('[NewMachine] No offerId provided:', data)
      return
    }

    // Real provisioning
    setProvisioningMode(true)
    setWizardLoading(true)

    try {
      // Build request params for creating instance
      // API expects: offer_id, image, disk_size, label, ports, skip_standby
      const params = {
        offer_id: offerId,
        label: `${data?.machine?.gpu_name || 'GPU'} - ${data?.tier || 'Standard'}`,
        // Skip standby if failover is "no_failover"
        skip_standby: data?.failoverStrategy === 'no_failover',
      }

      console.log('[NewMachine] Creating instance with params:', params)

      // Use correct endpoint: POST /api/v1/instances
      const res = await apiPost('/api/v1/instances', params)

      if (res.ok) {
        const instance = await res.json()
        console.log('[NewMachine] Instance created:', instance)

        // Add instance to racing state (will be hidden from Machines page until confirmed)
        const instanceId = instance.id || instance.instance_id
        if (instanceId) {
          dispatch(addRacingInstance(instanceId))
        }

        setRaceWinner(instance)
        toast?.success('Machine created successfully!')
      } else {
        const error = await res.json()
        console.error('[NewMachine] Failed to create instance:', error)
        toast?.error(error.detail || 'Failed to create machine')
      }
    } catch (err) {
      console.error('[NewMachine] Error creating instance:', err)
      toast?.error('Connection error')
    } finally {
      setWizardLoading(false)
    }
  }

  // Cancel provisioning race
  const cancelProvisioningRace = () => {
    // Clear all racing instances from Redux (they will be destroyed by the API)
    dispatch(clearRacingInstances())

    setProvisioningMode(false)
    setRaceCandidates([])
    setRaceWinner(null)
    setCurrentRound(1)
  }

  // Complete provisioning and go to machines
  const completeProvisioningRace = () => {
    // Mark winner in Redux - this removes it from racing list so it appears in Machines
    if (raceWinner) {
      const winnerId = raceWinner.id || raceWinner.instance_id
      if (winnerId) {
        dispatch(setRaceWinner(winnerId))
      }
    }

    // Clear any remaining racing instances
    dispatch(clearRacingInstances())

    navigate(`${basePath}/machines`)
  }

  // Go back to machines page
  const handleBack = () => {
    // Clear racing instances if user goes back without completing
    if (provisioningMode) {
      dispatch(clearRacingInstances())
    }
    navigate(`${basePath}/machines`)
  }

  // Cleanup racing instances on unmount (if user navigates away)
  useEffect(() => {
    return () => {
      // Only clear if there's an active race (not completed)
      if (provisioningMode && !raceWinner) {
        dispatch(clearRacingInstances())
      }
    }
  }, [provisioningMode, raceWinner, dispatch])

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
            onCancelProvisioning={cancelProvisioningRace}
            onCompleteProvisioning={completeProvisioningRace}
          />
        </div>
      </div>
    </div>
  )
}

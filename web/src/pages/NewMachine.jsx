import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { ArrowLeft, Plus } from 'lucide-react'
import { WizardFormNew as WizardForm } from '../components/wizard'
import { useToast } from '../components/Toast'
import {
  addRacingInstances,
  setRaceWinner,
  clearRacingInstances,
} from '../store/slices/instancesSlice'
import { useProvisioningRace, createDefaultApiService } from '../hooks/useProvisioningRace'

/**
 * Dedicated page for creating a new GPU machine
 * Uses provisioning race: creates 5 machines, picks the first to connect
 * If none connect in 15 seconds, destroys all and tries another 5 (up to 3 rounds)
 */
export default function NewMachine() {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const toast = useToast()

  // Base path for navigation
  const basePath = '/app'

  // Loading state
  const [wizardLoading, setWizardLoading] = useState(false)
  const [provisioningMode, setProvisioningMode] = useState(false)

  // API service for provisioning race
  const apiService = useMemo(() => createDefaultApiService(''), [])

  // Provisioning race hook - 5 candidates, 3 rounds, 15 second timeout per round
  const {
    candidates: raceCandidates,
    winner: raceWinner,
    currentRound,
    error: raceError,
    maxRounds,
    isRacing,
    isCompleted,
    isFailed,
    startRace,
    cancelRace,
    completeRace,
    getCreatedInstanceIds,
  } = useProvisioningRace(apiService, {
    maxCandidates: 5,
    maxRounds: 3,
    pollIntervalMs: 2000,
    timeoutMs: 15 * 1000,
    createDelayMs: 300,
  })

  // Handle wizard submit - start provisioning race
  const handleWizardSubmit = async (data) => {
    console.log('[NewMachine] handleWizardSubmit called with:', data)

    const allOffers = data?.allOffers || []

    if (allOffers.length === 0) {
      toast?.error('Erro: Nenhuma máquina disponível')
      console.error('[NewMachine] No offers available for racing')
      return
    }

    console.log('[NewMachine] Starting provisioning race with', allOffers.length, 'offers')

    setProvisioningMode(true)
    setWizardLoading(true)

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
    await cancelRace()
    dispatch(clearRacingInstances())
    setProvisioningMode(false)
    setWizardLoading(false)
  }

  // Complete provisioning and go to machines
  const completeProvisioningRace = () => {
    if (raceWinner) {
      const winnerId = raceWinner.instanceId || raceWinner.id
      if (winnerId) {
        dispatch(setRaceWinner(winnerId))
      }
    }

    completeRace()
    dispatch(clearRacingInstances())
    navigate(`${basePath}/machines`)
  }

  // Go back to machines page
  const handleBack = async () => {
    if (provisioningMode) {
      await cancelRace()
      dispatch(clearRacingInstances())
    }
    navigate(`${basePath}/machines`)
  }

  // Cleanup racing instances on unmount
  useEffect(() => {
    return () => {
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
            onSubmit={handleWizardSubmit}
            loading={wizardLoading}
            isProvisioning={provisioningMode}
            provisioningCandidates={raceCandidates}
            provisioningWinner={raceWinner}
            currentRound={currentRound}
            maxRounds={maxRounds}
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

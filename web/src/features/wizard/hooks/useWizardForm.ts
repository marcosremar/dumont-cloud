/**
 * Main Wizard Form Hook
 *
 * Composes all wizard hooks into a single, easy-to-use interface.
 * This is the primary hook that components should use.
 */

import { useCallback, useEffect, useMemo } from 'react';
import {
  WizardState,
  WizardStep,
  Location,
  TierName,
  MachineOffer,
  FailoverStrategyId,
  PortConfig,
  ProvisioningCandidate,
  UseWizardFormReturn,
  WizardActions,
  WizardValidation,
  WizardComputed,
  ProvisioningConfig,
} from '../types';
import { useWizardState, UseWizardStateReturn } from './useWizardState';
import { useWizardApi, UseWizardApiReturn, UseWizardApiOptions } from './useWizardApi';
import { useProvisioningTimer, UseProvisioningTimerReturn } from './useProvisioningTimer';
import {
  isStepComplete,
  isStepPassed,
  canProceedToStep,
  validateCurrentStep,
  validateBeforeProvisioning,
  hasMinimumBalance,
} from './useWizardValidation';
import {
  getTierByName,
  getStrategyById,
  getEstimatedCostFromTier,
  createLocationFromRegion,
  createLocationFromCountry,
} from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface UseWizardFormOptions {
  initialState?: Partial<WizardState>;
  api?: UseWizardApiOptions;
  onComplete?: (winner: ProvisioningCandidate) => void;
  onCancel?: () => void;
}

// ============================================================================
// Hook
// ============================================================================

export function useWizardForm(options: UseWizardFormOptions = {}): UseWizardFormReturn {
  const { initialState, api: apiOptions, onComplete, onCancel } = options;

  // Compose hooks
  const stateManager = useWizardState(initialState);
  const apiManager = useWizardApi(apiOptions);
  const timer = useProvisioningTimer({
    isActive: stateManager.state.currentStep === 4 && stateManager.state.isProvisioning,
    candidates: stateManager.state.provisioningCandidates,
    hasWinner: stateManager.state.provisioningWinner !== null,
  });

  const { state } = stateManager;

  // ============================================================================
  // Effects
  // ============================================================================

  // Fetch recommended machines when tier or location changes
  useEffect(() => {
    if (!state.selectedTier) {
      stateManager.setRecommendedMachines([]);
      return;
    }

    const fetchMachines = async () => {
      stateManager.setLoadingMachines(true);
      const machines = await apiManager.fetchOffersByTier(
        state.selectedTier!,
        state.selectedLocation,
      );
      stateManager.setRecommendedMachines(machines);
      stateManager.setLoadingMachines(false);
    };

    fetchMachines();
  }, [state.selectedTier, state.selectedLocation]);

  // ============================================================================
  // Actions
  // ============================================================================

  const goToStep = useCallback((step: WizardStep) => {
    if (canProceedToStep(state, step)) {
      stateManager.setStep(step);
    }
  }, [state, stateManager]);

  const startProvisioningFromStep3 = useCallback(async () => {
    if (!state.selectedLocation || !state.selectedTier) return;

    const config: ProvisioningConfig = {
      location: state.selectedLocation,
      tier: state.selectedTier,
      failoverStrategy: state.failoverStrategy,
      dockerImage: state.dockerImage,
      exposedPorts: state.exposedPorts,
      machine: state.selectedMachine ?? undefined,
    };

    stateManager.setStep(4);
    stateManager.setIsProvisioning(true);
    stateManager.setValidationErrors([]);
    timer.reset();

    const candidates = await apiManager.startProvisioning(config);
    stateManager.setProvisioningCandidates(candidates);

    // Simulate provisioning progress for demo mode
    if (candidates.length > 0) {
      console.log('[useWizardForm] Starting provisioning simulation with', candidates.length, 'candidates');

      // Update candidates to "connecting" status
      const connectingCandidates = candidates.map(c => ({ ...c, status: 'connecting' as const, progress: 10 }));
      stateManager.setProvisioningCandidates(connectingCandidates);

      // Simulate progress updates
      let currentProgress = 10;
      const progressInterval = setInterval(() => {
        currentProgress += 15;
        const updatingCandidates = stateManager.state.provisioningCandidates.map(c => ({
          ...c,
          progress: Math.min(95, currentProgress + Math.random() * 10),
        }));
        stateManager.setProvisioningCandidates(updatingCandidates);

        // After ~3-4 seconds, declare a winner
        if (currentProgress >= 60) {
          clearInterval(progressInterval);
          const winnerIndex = Math.floor(Math.random() * Math.min(candidates.length, 3));
          const winner = candidates[winnerIndex];

          // Update all candidates
          const finalCandidates = candidates.map((c, idx) => ({
            ...c,
            status: idx === winnerIndex ? 'connected' as const : 'failed' as const,
            progress: idx === winnerIndex ? 100 : c.progress,
          }));

          console.log('[useWizardForm] Simulation complete, winner:', winner);
          stateManager.setProvisioningCandidates(finalCandidates);
          stateManager.setProvisioningWinner(winner);
          stateManager.setIsProvisioning(false);
        }
      }, 800);
    }
  }, [state, stateManager, apiManager, timer]);

  const nextStep = useCallback(() => {
    if (state.currentStep < 4 && isStepComplete(state, state.currentStep)) {
      if (state.currentStep === 3) {
        // Validate before starting provisioning
        const errors = validateBeforeProvisioning(state, 0); // TODO: get actual balance
        if (errors.length > 0) {
          stateManager.setValidationErrors(errors);
          return;
        }
        // Start provisioning - call directly instead of through actions to avoid circular reference
        startProvisioningFromStep3();
      } else {
        stateManager.setStep((state.currentStep + 1) as WizardStep);
      }
    }
  }, [state, stateManager, startProvisioningFromStep3]);

  const prevStep = useCallback(() => {
    if (state.currentStep > 1) {
      if (state.currentStep === 4) {
        apiManager.cancelProvisioning();
      }
      stateManager.setStep((state.currentStep - 1) as WizardStep);
    }
  }, [state, stateManager, apiManager]);

  const setLocation = useCallback((location: Location | null) => {
    stateManager.setLocation(location);
  }, [stateManager]);

  const selectRegion = useCallback((regionKey: string) => {
    const location = createLocationFromRegion(regionKey);
    if (location) {
      stateManager.setLocation(location);
    }
  }, [stateManager]);

  const selectCountry = useCallback((code: string) => {
    const location = createLocationFromCountry(code);
    if (location) {
      stateManager.setLocation(location);
    }
  }, [stateManager]);

  const clearLocation = useCallback(() => {
    stateManager.setLocation(null);
    stateManager.setSearchCountry('');
  }, [stateManager]);

  const setTier = useCallback((tier: TierName | null) => {
    stateManager.setTier(tier);
  }, [stateManager]);

  const setMachine = useCallback((machine: MachineOffer | null) => {
    stateManager.setMachine(machine);
    if (machine) {
      stateManager.setGPU(machine.gpu_name);
    }
  }, [stateManager]);

  const startProvisioning = useCallback(async () => {
    // Reuse the same provisioning logic
    await startProvisioningFromStep3();
  }, [startProvisioningFromStep3]);

  const cancelProvisioning = useCallback(() => {
    apiManager.cancelProvisioning();
    stateManager.setIsProvisioning(false);
    onCancel?.();
  }, [apiManager, stateManager, onCancel]);

  const completeProvisioning = useCallback(async (winner: ProvisioningCandidate) => {
    // Call the real provisioning API
    const config: ProvisioningConfig = {
      location: state.selectedLocation!,
      tier: state.selectedTier!,
      failoverStrategy: state.failoverStrategy,
      dockerImage: state.dockerImage,
      exposedPorts: state.exposedPorts,
      machine: state.selectedMachine ?? undefined,
    };

    console.log('[useWizardForm] Provisioning machine:', winner.id, 'with config:', config);
    const result = await apiManager.provisionMachine(winner.id, config);

    if (result.success) {
      console.log('[useWizardForm] Provisioning successful, instance:', result.instanceId);
      stateManager.setProvisioningWinner(winner);
      onComplete?.(winner);
    } else {
      console.error('[useWizardForm] Provisioning failed');
      stateManager.setValidationErrors(['Falha ao provisionar máquina. Tente novamente.']);
    }
  }, [state, stateManager, apiManager, onComplete]);

  const reset = useCallback(() => {
    stateManager.reset();
    timer.reset();
  }, [stateManager, timer]);

  // ============================================================================
  // Computed Values
  // ============================================================================

  const computed: WizardComputed = useMemo(() => ({
    selectedTierData: state.selectedTier ? getTierByName(state.selectedTier) : undefined,
    selectedFailoverData: getStrategyById(state.failoverStrategy),
    estimatedCost: state.selectedTier
      ? getEstimatedCostFromTier(state.selectedTier)
      : { hourly: '0.00', daily: '0.00' },
    progress: ((state.currentStep - 1) / 3) * 100,
  }), [state.selectedTier, state.failoverStrategy, state.currentStep]);

  // ============================================================================
  // Validation
  // ============================================================================

  const validation: WizardValidation = useMemo(() => ({
    isStepComplete: (step: WizardStep) => isStepComplete(state, step),
    isStepPassed: (step: WizardStep) => isStepPassed(state, step),
    canProceedToStep: (step: WizardStep) => canProceedToStep(state, step),
    validateCurrentStep: () => validateCurrentStep(state),
    hasMinimumBalance,
  }), [state]);

  // ============================================================================
  // Actions Object
  // ============================================================================

  const actions: WizardActions = useMemo(() => ({
    goToStep,
    nextStep,
    prevStep,
    setLocation,
    setSearchCountry: stateManager.setSearchCountry,
    selectRegion,
    selectCountry,
    clearLocation,
    setTier,
    setGPU: stateManager.setGPU,
    setMachine,
    setFailoverStrategy: stateManager.setFailoverStrategy,
    setDockerImage: stateManager.setDockerImage,
    addPort: stateManager.addPort,
    removePort: stateManager.removePort,
    updatePort: stateManager.updatePort,
    toggleAdvancedSettings: stateManager.toggleAdvancedSettings,
    setSelectionMode: stateManager.setSelectionMode,
    startProvisioning,
    cancelProvisioning,
    completeProvisioning,
    reset,
  }), [
    goToStep,
    nextStep,
    prevStep,
    setLocation,
    selectRegion,
    selectCountry,
    clearLocation,
    setTier,
    setMachine,
    startProvisioning,
    cancelProvisioning,
    completeProvisioning,
    reset,
    stateManager,
  ]);

  return {
    state,
    actions,
    validation,
    computed,
  };
}

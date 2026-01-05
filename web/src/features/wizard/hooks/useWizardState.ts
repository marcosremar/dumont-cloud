/**
 * Wizard State Hook
 *
 * Manages wizard state using useReducer for predictable state updates.
 * Pure reducer function is easily testable.
 */

import { useReducer, useCallback } from 'react';
import {
  WizardState,
  WizardAction,
  WizardStep,
  Location,
  TierName,
  MachineOffer,
  RecommendedMachine,
  FailoverStrategyId,
  PortConfig,
  ProvisioningCandidate,
} from '../types';
import { WIZARD_DEFAULTS } from '../constants';

// ============================================================================
// Initial State
// ============================================================================

export const initialWizardState: WizardState = {
  currentStep: 1,
  // Step 1
  selectedLocation: null,
  searchCountry: '',
  // Step 2
  selectedTier: null,
  selectedGPU: null,
  selectedMachine: null,
  recommendedMachines: [],
  loadingMachines: false,
  // Step 3
  failoverStrategy: 'snapshot_only',
  dockerImage: WIZARD_DEFAULTS.dockerImage,
  exposedPorts: [...WIZARD_DEFAULTS.exposedPorts],
  // Step 4
  provisioningCandidates: [],
  provisioningWinner: null,
  isProvisioning: false,
  currentRound: 1,
  maxRounds: WIZARD_DEFAULTS.maxRounds,
  // UI
  validationErrors: [],
  showAdvancedSettings: false,
  selectionMode: 'recommended',
};

// ============================================================================
// Reducer (Pure Function - Easy to Test)
// ============================================================================

export function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, currentStep: action.payload, validationErrors: [] };

    case 'SET_LOCATION':
      return { ...state, selectedLocation: action.payload };

    case 'SET_SEARCH_COUNTRY':
      return { ...state, searchCountry: action.payload };

    case 'SET_TIER':
      return {
        ...state,
        selectedTier: action.payload,
        selectedMachine: null, // Reset machine when tier changes
        selectedGPU: null,
      };

    case 'SET_GPU':
      return { ...state, selectedGPU: action.payload };

    case 'SET_MACHINE':
      return { ...state, selectedMachine: action.payload };

    case 'SET_RECOMMENDED_MACHINES':
      return { ...state, recommendedMachines: action.payload };

    case 'SET_LOADING_MACHINES':
      return { ...state, loadingMachines: action.payload };

    case 'SET_FAILOVER_STRATEGY':
      return { ...state, failoverStrategy: action.payload };

    case 'SET_DOCKER_IMAGE':
      return { ...state, dockerImage: action.payload };

    case 'SET_EXPOSED_PORTS':
      return { ...state, exposedPorts: action.payload };

    case 'ADD_PORT':
      return {
        ...state,
        exposedPorts: [...state.exposedPorts, action.payload ?? { port: '', protocol: 'TCP' }],
      };

    case 'REMOVE_PORT':
      return {
        ...state,
        exposedPorts: state.exposedPorts.filter((_, i) => i !== action.payload),
      };

    case 'UPDATE_PORT':
      return {
        ...state,
        exposedPorts: state.exposedPorts.map((p, i) =>
          i === action.payload.index ? action.payload.config : p
        ),
      };

    case 'SET_PROVISIONING_CANDIDATES':
      return { ...state, provisioningCandidates: action.payload };

    case 'SET_PROVISIONING_WINNER':
      return { ...state, provisioningWinner: action.payload, isProvisioning: false };

    case 'SET_IS_PROVISIONING':
      return { ...state, isProvisioning: action.payload };

    case 'SET_CURRENT_ROUND':
      return { ...state, currentRound: action.payload };

    case 'SET_VALIDATION_ERRORS':
      return { ...state, validationErrors: action.payload };

    case 'TOGGLE_ADVANCED_SETTINGS':
      return { ...state, showAdvancedSettings: !state.showAdvancedSettings };

    case 'SET_SELECTION_MODE':
      return { ...state, selectionMode: action.payload };

    case 'RESET':
      return { ...initialWizardState };

    default:
      return state;
  }
}

// ============================================================================
// Hook
// ============================================================================

export interface UseWizardStateReturn {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
  // Typed action dispatchers
  setStep: (step: WizardStep) => void;
  setLocation: (location: Location | null) => void;
  setSearchCountry: (search: string) => void;
  setTier: (tier: TierName | null) => void;
  setGPU: (gpu: string | null) => void;
  setMachine: (machine: MachineOffer | null) => void;
  setRecommendedMachines: (machines: RecommendedMachine[]) => void;
  setLoadingMachines: (loading: boolean) => void;
  setFailoverStrategy: (strategy: FailoverStrategyId) => void;
  setDockerImage: (image: string) => void;
  addPort: (port?: PortConfig) => void;
  removePort: (index: number) => void;
  updatePort: (index: number, config: PortConfig) => void;
  setProvisioningCandidates: (candidates: ProvisioningCandidate[]) => void;
  setProvisioningWinner: (winner: ProvisioningCandidate | null) => void;
  setIsProvisioning: (isProvisioning: boolean) => void;
  setCurrentRound: (round: number) => void;
  setValidationErrors: (errors: string[]) => void;
  toggleAdvancedSettings: () => void;
  setSelectionMode: (mode: 'recommended' | 'manual') => void;
  reset: () => void;
}

export function useWizardState(
  initialState: Partial<WizardState> = {},
): UseWizardStateReturn {
  const [state, dispatch] = useReducer(
    wizardReducer,
    { ...initialWizardState, ...initialState },
  );

  // Memoized action dispatchers
  const setStep = useCallback((step: WizardStep) => {
    dispatch({ type: 'SET_STEP', payload: step });
  }, []);

  const setLocation = useCallback((location: Location | null) => {
    dispatch({ type: 'SET_LOCATION', payload: location });
  }, []);

  const setSearchCountry = useCallback((search: string) => {
    dispatch({ type: 'SET_SEARCH_COUNTRY', payload: search });
  }, []);

  const setTier = useCallback((tier: TierName | null) => {
    dispatch({ type: 'SET_TIER', payload: tier });
  }, []);

  const setGPU = useCallback((gpu: string | null) => {
    dispatch({ type: 'SET_GPU', payload: gpu });
  }, []);

  const setMachine = useCallback((machine: MachineOffer | null) => {
    dispatch({ type: 'SET_MACHINE', payload: machine });
  }, []);

  const setRecommendedMachines = useCallback((machines: RecommendedMachine[]) => {
    dispatch({ type: 'SET_RECOMMENDED_MACHINES', payload: machines });
  }, []);

  const setLoadingMachines = useCallback((loading: boolean) => {
    dispatch({ type: 'SET_LOADING_MACHINES', payload: loading });
  }, []);

  const setFailoverStrategy = useCallback((strategy: FailoverStrategyId) => {
    dispatch({ type: 'SET_FAILOVER_STRATEGY', payload: strategy });
  }, []);

  const setDockerImage = useCallback((image: string) => {
    dispatch({ type: 'SET_DOCKER_IMAGE', payload: image });
  }, []);

  const addPort = useCallback((port?: PortConfig) => {
    dispatch({ type: 'ADD_PORT', payload: port });
  }, []);

  const removePort = useCallback((index: number) => {
    dispatch({ type: 'REMOVE_PORT', payload: index });
  }, []);

  const updatePort = useCallback((index: number, config: PortConfig) => {
    dispatch({ type: 'UPDATE_PORT', payload: { index, config } });
  }, []);

  const setProvisioningCandidates = useCallback((candidates: ProvisioningCandidate[]) => {
    dispatch({ type: 'SET_PROVISIONING_CANDIDATES', payload: candidates });
  }, []);

  const setProvisioningWinner = useCallback((winner: ProvisioningCandidate | null) => {
    dispatch({ type: 'SET_PROVISIONING_WINNER', payload: winner });
  }, []);

  const setIsProvisioning = useCallback((isProvisioning: boolean) => {
    dispatch({ type: 'SET_IS_PROVISIONING', payload: isProvisioning });
  }, []);

  const setCurrentRound = useCallback((round: number) => {
    dispatch({ type: 'SET_CURRENT_ROUND', payload: round });
  }, []);

  const setValidationErrors = useCallback((errors: string[]) => {
    dispatch({ type: 'SET_VALIDATION_ERRORS', payload: errors });
  }, []);

  const toggleAdvancedSettings = useCallback(() => {
    dispatch({ type: 'TOGGLE_ADVANCED_SETTINGS' });
  }, []);

  const setSelectionMode = useCallback((mode: 'recommended' | 'manual') => {
    dispatch({ type: 'SET_SELECTION_MODE', payload: mode });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return {
    state,
    dispatch,
    setStep,
    setLocation,
    setSearchCountry,
    setTier,
    setGPU,
    setMachine,
    setRecommendedMachines,
    setLoadingMachines,
    setFailoverStrategy,
    setDockerImage,
    addPort,
    removePort,
    updatePort,
    setProvisioningCandidates,
    setProvisioningWinner,
    setIsProvisioning,
    setCurrentRound,
    setValidationErrors,
    toggleAdvancedSettings,
    setSelectionMode,
    reset,
  };
}

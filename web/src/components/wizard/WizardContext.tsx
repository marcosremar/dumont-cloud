/**
 * WizardContext
 * Central state management for the wizard using useReducer
 */

import React, { createContext, useContext, useReducer, useMemo } from 'react';
import type {
  WizardState,
  WizardAction,
  WizardStep,
  MachineOffer,
  Snapshot,
  SelectedLocation,
} from './types/wizard.types';
import { isStepComplete, isStepPassed } from './utils/validation';
import { useMachineOffers } from './hooks/useMachineOffers';
import { useSnapshots } from './hooks/useSnapshots';
import { useBalance } from './hooks/useBalance';

// ============================================================================
// Initial State
// ============================================================================

export const initialWizardState: WizardState = {
  // Navigation
  currentStep: 1,

  // Step 1: Location
  selectedLocations: [],
  searchCountry: '',

  // Step 2: Hardware
  selectedTier: null,
  selectedGPU: 'any',
  selectedGPUCategory: 'any',
  selectionMode: 'recommended',
  selectedMachine: null,
  gpuSearchQuery: '',

  // Step 3: Strategy
  failoverStrategy: 'snapshot_only',

  // Advanced Settings
  showAdvancedSettings: false,
  dockerImage: 'pytorch/pytorch:latest',
  exposedPorts: [
    { port: '22', protocol: 'TCP' },
    { port: '8080', protocol: 'TCP' },
    { port: '8888', protocol: 'TCP' },
    { port: '6006', protocol: 'TCP' },
  ],

  // Migration Mode
  migrationType: 'restore',
  selectedSnapshot: null,

  // Validation
  validationErrors: [],

  // Loading States
  loading: false,
};

// ============================================================================
// Reducer
// ============================================================================

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, currentStep: action.payload };

    case 'NEXT_STEP':
      if (state.currentStep < 4) {
        return { ...state, currentStep: (state.currentStep + 1) as WizardStep };
      }
      return state;

    case 'PREV_STEP':
      if (state.currentStep > 1) {
        return { ...state, currentStep: (state.currentStep - 1) as WizardStep };
      }
      return state;

    case 'SET_LOCATIONS':
      return { ...state, selectedLocations: action.payload };

    case 'ADD_LOCATION':
      // Check if already exists
      if (state.selectedLocations.some((loc) => loc.name === action.payload.name)) {
        return state;
      }
      return {
        ...state,
        selectedLocations: [...state.selectedLocations, action.payload],
        searchCountry: '',
      };

    case 'REMOVE_LOCATION':
      return {
        ...state,
        selectedLocations: state.selectedLocations.filter(
          (loc) => loc.name !== action.payload
        ),
      };

    case 'CLEAR_LOCATIONS':
      return { ...state, selectedLocations: [], searchCountry: '' };

    case 'SET_SEARCH_COUNTRY':
      return { ...state, searchCountry: action.payload };

    case 'SET_TIER':
      return { ...state, selectedTier: action.payload, selectedMachine: null };

    case 'SET_GPU':
      return { ...state, selectedGPU: action.payload, selectedMachine: null };

    case 'SET_GPU_CATEGORY':
      return { ...state, selectedGPUCategory: action.payload };

    case 'SET_SELECTION_MODE':
      return { ...state, selectionMode: action.payload };

    case 'SET_SELECTED_MACHINE':
      return { ...state, selectedMachine: action.payload };

    case 'SET_GPU_SEARCH_QUERY':
      return { ...state, gpuSearchQuery: action.payload };

    case 'SET_FAILOVER_STRATEGY':
      return { ...state, failoverStrategy: action.payload };

    case 'SET_SHOW_ADVANCED':
      return { ...state, showAdvancedSettings: action.payload };

    case 'SET_DOCKER_IMAGE':
      return { ...state, dockerImage: action.payload };

    case 'SET_EXPOSED_PORTS':
      return { ...state, exposedPorts: action.payload };

    case 'SET_MIGRATION_TYPE':
      return { ...state, migrationType: action.payload };

    case 'SET_SELECTED_SNAPSHOT':
      return { ...state, selectedSnapshot: action.payload };

    case 'SET_VALIDATION_ERRORS':
      return { ...state, validationErrors: action.payload };

    case 'CLEAR_VALIDATION_ERRORS':
      return { ...state, validationErrors: [] };

    case 'SET_LOADING':
      return { ...state, loading: action.payload };

    case 'RESET':
      return initialWizardState;

    default:
      return state;
  }
}

// ============================================================================
// Context
// ============================================================================

interface WizardContextValue {
  // State
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;

  // Derived state
  isStepComplete: (step: WizardStep) => boolean;
  isStepPassed: (step: WizardStep) => boolean;
  canProceed: boolean;

  // Data from hooks
  recommendedMachines: MachineOffer[];
  allAvailableOffers: MachineOffer[];
  availableSnapshots: Snapshot[];
  userBalance: number | null;

  // Loading states
  loadingMachines: boolean;
  loadingSnapshots: boolean;
  loadingBalance: boolean;

  // Errors
  apiError: string | null;
  balanceError: string | null;

  // Snapshot management
  setSelectedSnapshot: (snapshot: Snapshot | null) => void;
}

const WizardContext = createContext<WizardContextValue | null>(null);

// ============================================================================
// Provider Props
// ============================================================================

interface WizardProviderProps {
  children: React.ReactNode;
  initialStep?: WizardStep;
  migrationMode?: boolean;
}

// ============================================================================
// Provider Component
// ============================================================================

export function WizardProvider({
  children,
  initialStep = 1,
  migrationMode = false,
}: WizardProviderProps) {
  // Reducer
  const [state, dispatch] = useReducer(wizardReducer, {
    ...initialWizardState,
    currentStep: initialStep,
    migrationType: migrationMode ? 'restore' : 'new',
  });

  // Data hooks
  const {
    recommendedMachines,
    allAvailableOffers,
    loading: loadingMachines,
    error: apiError,
  } = useMachineOffers({
    selectedTier: state.selectedTier,
    selectedLocations: state.selectedLocations,
    enabled: state.currentStep >= 2,
  });

  const {
    snapshots: availableSnapshots,
    selectedSnapshot,
    setSelectedSnapshot,
    loading: loadingSnapshots,
  } = useSnapshots({
    enabled: migrationMode && state.migrationType === 'restore',
  });

  const {
    balance: userBalance,
    loading: loadingBalance,
    error: balanceError,
  } = useBalance({
    enabled: state.currentStep === 3,
  });

  // Sync selected snapshot with state
  React.useEffect(() => {
    if (selectedSnapshot && !state.selectedSnapshot) {
      dispatch({ type: 'SET_SELECTED_SNAPSHOT', payload: selectedSnapshot });
    }
  }, [selectedSnapshot, state.selectedSnapshot]);

  // Memoized context value
  const value = useMemo<WizardContextValue>(
    () => ({
      state,
      dispatch,
      isStepComplete: (step: WizardStep) => isStepComplete(step, state),
      isStepPassed: (step: WizardStep) => isStepPassed(step, state.currentStep, state),
      canProceed: isStepComplete(state.currentStep, state),
      recommendedMachines,
      allAvailableOffers,
      availableSnapshots,
      userBalance,
      loadingMachines,
      loadingSnapshots,
      loadingBalance,
      apiError,
      balanceError,
      setSelectedSnapshot: (snapshot: Snapshot | null) => {
        setSelectedSnapshot(snapshot);
        dispatch({ type: 'SET_SELECTED_SNAPSHOT', payload: snapshot });
      },
    }),
    [
      state,
      recommendedMachines,
      allAvailableOffers,
      availableSnapshots,
      userBalance,
      loadingMachines,
      loadingSnapshots,
      loadingBalance,
      apiError,
      balanceError,
      setSelectedSnapshot,
    ]
  );

  return (
    <WizardContext.Provider value={value}>{children}</WizardContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useWizard(): WizardContextValue {
  const context = useContext(WizardContext);
  if (!context) {
    throw new Error('useWizard must be used within a WizardProvider');
  }
  return context;
}

export default WizardContext;

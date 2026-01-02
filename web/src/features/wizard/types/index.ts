/**
 * Wizard Types - Core type definitions
 * All wizard-related types are defined here for strong typing
 */

import { LucideIcon } from 'lucide-react';

// ============================================================================
// Location Types
// ============================================================================

export interface Location {
  codes: string[];
  name: string;
  isRegion: boolean;
}

export interface Region {
  name: string;
  codes: string[];
  isRegion: true;
}

export type RegionKey = 'eua' | 'europa' | 'asia' | 'america-do-sul';

// ============================================================================
// GPU & Tier Types
// ============================================================================

export interface TierFilter {
  min_gpu_ram?: number;
  max_price?: number;
  gpu_count?: number;
  verified_only?: boolean;
}

export interface PerformanceTier {
  name: string;
  label: string;
  description: string;
  gpu: string;
  vram: string;
  priceRange: string;
  filter: TierFilter;
}

export type TierName = 'CPU' | 'Lento' | 'Medio' | 'Rapido' | 'Ultra';

export interface GPUOption {
  name: string;
  vram: string;
  priceRange: string;
}

// ============================================================================
// Machine/Offer Types
// ============================================================================

export interface MachineOffer {
  id: number;
  gpu_name: string;
  gpu_ram: number;
  num_gpus: number;
  cpu_cores?: number;
  cpu_ram?: number;
  dph_total: number;
  geolocation: string;
  location?: string;
  provider?: string;
  reliability?: number;
  verified?: boolean;
  label?: string;
  isCPU?: boolean;
}

export interface RecommendedMachine extends MachineOffer {
  label: 'Mais econômico' | 'Melhor custo-benefício' | 'Mais rápido';
}

// ============================================================================
// Failover Strategy Types
// ============================================================================

export interface FailoverStrategy {
  id: string;
  name: string;
  provider: string;
  icon: LucideIcon;
  description: string;
  recoveryTime: string;
  dataLoss: string;
  costHour?: string;
  costMonth?: string;
  costDetail?: string;
  howItWorks: string;
  features: string[];
  requirements: string;
  recommended?: boolean;
  available: boolean;
  danger?: boolean;
  comingSoon?: boolean;
}

export type FailoverStrategyId =
  | 'snapshot_only'
  | 'vast_warmpool'
  | 'cpu_standby_only'
  | 'tensordock'
  | 'no_failover';

// ============================================================================
// Provisioning Types
// ============================================================================

export type ProvisioningStatus = 'pending' | 'connecting' | 'connected' | 'failed';

export interface ProvisioningCandidate extends MachineOffer {
  status: ProvisioningStatus;
  progress?: number;
  statusMessage?: string;
  errorMessage?: string;
}

// ============================================================================
// Wizard State Types
// ============================================================================

export type WizardStep = 1 | 2 | 3 | 4;

export interface WizardState {
  currentStep: WizardStep;
  // Step 1: Location
  selectedLocation: Location | null;
  searchCountry: string;
  // Step 2: Hardware
  selectedTier: TierName | null;
  selectedGPU: string | null;
  selectedMachine: MachineOffer | null;
  recommendedMachines: RecommendedMachine[];
  loadingMachines: boolean;
  // Step 3: Strategy
  failoverStrategy: FailoverStrategyId;
  dockerImage: string;
  exposedPorts: PortConfig[];
  // Step 4: Provisioning
  provisioningCandidates: ProvisioningCandidate[];
  provisioningWinner: ProvisioningCandidate | null;
  isProvisioning: boolean;
  currentRound: number;
  maxRounds: number;
  // UI State
  validationErrors: string[];
  showAdvancedSettings: boolean;
  selectionMode: 'recommended' | 'manual';
}

export interface PortConfig {
  port: string;
  protocol: 'TCP' | 'UDP';
}

// ============================================================================
// API Types
// ============================================================================

export interface OffersApiParams {
  limit?: number;
  order_by?: string;
  region?: string;
  min_gpu_ram?: number;
  max_price?: number;
  verified_only?: boolean;
}

export interface OffersApiResponse {
  offers: MachineOffer[];
  count: number;
}

export interface BalanceApiResponse {
  credit?: number;
  balance?: number;
}

// ============================================================================
// Action Types (for reducer pattern)
// ============================================================================

export type WizardAction =
  | { type: 'SET_STEP'; payload: WizardStep }
  | { type: 'SET_LOCATION'; payload: Location | null }
  | { type: 'SET_SEARCH_COUNTRY'; payload: string }
  | { type: 'SET_TIER'; payload: TierName | null }
  | { type: 'SET_GPU'; payload: string | null }
  | { type: 'SET_MACHINE'; payload: MachineOffer | null }
  | { type: 'SET_RECOMMENDED_MACHINES'; payload: RecommendedMachine[] }
  | { type: 'SET_LOADING_MACHINES'; payload: boolean }
  | { type: 'SET_FAILOVER_STRATEGY'; payload: FailoverStrategyId }
  | { type: 'SET_DOCKER_IMAGE'; payload: string }
  | { type: 'SET_EXPOSED_PORTS'; payload: PortConfig[] }
  | { type: 'ADD_PORT' }
  | { type: 'REMOVE_PORT'; payload: number }
  | { type: 'UPDATE_PORT'; payload: { index: number; config: PortConfig } }
  | { type: 'SET_PROVISIONING_CANDIDATES'; payload: ProvisioningCandidate[] }
  | { type: 'SET_PROVISIONING_WINNER'; payload: ProvisioningCandidate | null }
  | { type: 'SET_IS_PROVISIONING'; payload: boolean }
  | { type: 'SET_CURRENT_ROUND'; payload: number }
  | { type: 'SET_VALIDATION_ERRORS'; payload: string[] }
  | { type: 'TOGGLE_ADVANCED_SETTINGS' }
  | { type: 'SET_SELECTION_MODE'; payload: 'recommended' | 'manual' }
  | { type: 'RESET' };

// ============================================================================
// Hook Return Types
// ============================================================================

export interface UseWizardApiReturn {
  fetchOffers: (params: OffersApiParams) => Promise<MachineOffer[]>;
  fetchBalance: () => Promise<number>;
  startProvisioning: (config: ProvisioningConfig) => Promise<void>;
  cancelProvisioning: () => void;
  isLoading: boolean;
  error: string | null;
}

export interface ProvisioningConfig {
  location: Location;
  tier: TierName;
  failoverStrategy: FailoverStrategyId;
  dockerImage: string;
  exposedPorts: PortConfig[];
  machine?: MachineOffer;
}

export interface UseWizardFormReturn {
  state: WizardState;
  actions: WizardActions;
  validation: WizardValidation;
  computed: WizardComputed;
}

export interface WizardActions {
  goToStep: (step: WizardStep) => void;
  nextStep: () => void;
  prevStep: () => void;
  setLocation: (location: Location | null) => void;
  setSearchCountry: (search: string) => void;
  selectRegion: (regionKey: string) => void;
  selectCountry: (code: string) => void;
  clearLocation: () => void;
  setTier: (tier: TierName | null) => void;
  setGPU: (gpu: string | null) => void;
  setMachine: (machine: MachineOffer | null) => void;
  setFailoverStrategy: (strategy: FailoverStrategyId) => void;
  setDockerImage: (image: string) => void;
  addPort: () => void;
  removePort: (index: number) => void;
  updatePort: (index: number, config: PortConfig) => void;
  toggleAdvancedSettings: () => void;
  setSelectionMode: (mode: 'recommended' | 'manual') => void;
  startProvisioning: () => void;
  cancelProvisioning: () => void;
  completeProvisioning: (winner: ProvisioningCandidate) => Promise<void>;
  reset: () => void;
}

export interface WizardValidation {
  isStepComplete: (step: WizardStep) => boolean;
  isStepPassed: (step: WizardStep) => boolean;
  canProceedToStep: (step: WizardStep) => boolean;
  validateCurrentStep: () => string[];
  hasMinimumBalance: (balance: number) => boolean;
}

export interface WizardComputed {
  selectedTierData: PerformanceTier | undefined;
  selectedFailoverData: FailoverStrategy | undefined;
  estimatedCost: { hourly: string; daily: string };
  progress: number;
}

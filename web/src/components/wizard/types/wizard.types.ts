/**
 * Wizard Types
 * Central type definitions for the wizard components
 */

import { LucideIcon } from 'lucide-react';

// ============================================================================
// Location Types
// ============================================================================

export interface LocationData {
  name: string;
  codes: string[];
  isRegion?: boolean;
}

export interface SelectedLocation extends LocationData {
  // Additional runtime properties
}

// ============================================================================
// GPU & Hardware Types
// ============================================================================

export interface GPUInfo {
  name: string;
  vram: string;
  priceRange: string;
}

export interface PerformanceTier {
  name: string;
  icon: LucideIcon;
  description: string;
  priceRange: string;
  gpuExamples: string[];
  recommended?: boolean;
}

export interface MachineOffer {
  id: string | number;
  gpu_name: string;
  num_gpus: number;
  gpu_ram?: number;
  dph_total: number;
  disk_space?: number;
  geolocation?: string;
  location?: string;
  verified?: boolean;
  reliability?: number;
  dlperf?: number;
  inet_down?: number;
  inet_up?: number;
  cuda_max_good?: number;
  [key: string]: unknown;
}

// ============================================================================
// Failover Types
// ============================================================================

export interface FailoverOption {
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
  howItWorks?: string;
  features?: string[];
  requirements?: string;
  recommended?: boolean;
  available: boolean;
  comingSoon?: boolean;
  danger?: boolean;
}

// ============================================================================
// Snapshot Types
// ============================================================================

export interface Snapshot {
  id: string;
  name: string;
  short_id: string;
  created_at: string;
  size_gb: number | null;
  status: 'ready' | 'pending' | 'failed';
  isLatest?: boolean;
  paths: string[];
  hostname?: string;
}

// ============================================================================
// Provisioning Types
// ============================================================================

export type CandidateStatus =
  | 'idle'
  | 'creating'
  | 'connecting'
  | 'connected'
  | 'ready'
  | 'failed'
  | 'cancelled';

export interface ProvisioningCandidate extends MachineOffer {
  index: number;
  status: CandidateStatus;
  progress: number;
  errorMessage: string | null;
  instanceId: string | null;
  actualStatus?: string;
}

export interface ProvisioningWinner extends ProvisioningCandidate {
  instanceId: string;
  ssh_host?: string | null;
  ssh_port?: number | null;
  actual_status: string;
}

// ============================================================================
// Wizard State Types
// ============================================================================

export type WizardStep = 1 | 2 | 3 | 4;

export type SelectionMode = 'recommended' | 'manual';

export type MigrationType = 'new' | 'restore';

export type FailoverStrategy =
  | 'snapshot_only'
  | 'vast_warmpool'
  | 'cpu_standby_only'
  | 'tensordock'
  | 'no_failover';

export interface PortConfig {
  port: string;
  protocol: 'TCP' | 'UDP';
}

export interface WizardState {
  // Navigation
  currentStep: WizardStep;

  // Step 1: Location
  selectedLocations: SelectedLocation[];
  searchCountry: string;

  // Step 2: Hardware
  selectedTier: string | null;
  selectedGPU: string;
  selectedGPUCategory: string;
  selectionMode: SelectionMode;
  selectedMachine: MachineOffer | null;
  gpuSearchQuery: string;

  // Step 3: Strategy
  failoverStrategy: FailoverStrategy;

  // Advanced Settings
  showAdvancedSettings: boolean;
  dockerImage: string;
  exposedPorts: PortConfig[];

  // Migration Mode
  migrationType: MigrationType;
  selectedSnapshot: Snapshot | null;

  // Validation
  validationErrors: string[];

  // Loading States
  loading: boolean;
}

// ============================================================================
// Wizard Actions
// ============================================================================

export type WizardAction =
  | { type: 'SET_STEP'; payload: WizardStep }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'SET_LOCATIONS'; payload: SelectedLocation[] }
  | { type: 'ADD_LOCATION'; payload: SelectedLocation }
  | { type: 'REMOVE_LOCATION'; payload: string }
  | { type: 'CLEAR_LOCATIONS' }
  | { type: 'SET_SEARCH_COUNTRY'; payload: string }
  | { type: 'SET_TIER'; payload: string | null }
  | { type: 'SET_GPU'; payload: string }
  | { type: 'SET_GPU_CATEGORY'; payload: string }
  | { type: 'SET_SELECTION_MODE'; payload: SelectionMode }
  | { type: 'SET_SELECTED_MACHINE'; payload: MachineOffer | null }
  | { type: 'SET_GPU_SEARCH_QUERY'; payload: string }
  | { type: 'SET_FAILOVER_STRATEGY'; payload: FailoverStrategy }
  | { type: 'SET_SHOW_ADVANCED'; payload: boolean }
  | { type: 'SET_DOCKER_IMAGE'; payload: string }
  | { type: 'SET_EXPOSED_PORTS'; payload: PortConfig[] }
  | { type: 'SET_MIGRATION_TYPE'; payload: MigrationType }
  | { type: 'SET_SELECTED_SNAPSHOT'; payload: Snapshot | null }
  | { type: 'SET_VALIDATION_ERRORS'; payload: string[] }
  | { type: 'CLEAR_VALIDATION_ERRORS' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'RESET' };

// ============================================================================
// Wizard Context Types
// ============================================================================

export interface WizardContextValue {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;

  // Derived state
  isStepComplete: (step: WizardStep) => boolean;
  isStepPassed: (step: WizardStep) => boolean;
  canProceed: boolean;

  // Data
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
}

// ============================================================================
// Component Props Types
// ============================================================================

export interface StepProps {
  // Common step props are inherited from context
}

export interface WizardFormProps {
  // Migration mode
  migrationMode?: boolean;
  sourceMachine?: MachineOffer | null;
  targetType?: 'cpu' | 'gpu' | null;
  initialStep?: WizardStep;

  // Callbacks
  onSubmit: (data: WizardSubmitData) => void;
  onCancel?: () => void;

  // External state (from parent)
  loading?: boolean;

  // Provisioning (passed from parent hook)
  provisioningCandidates?: ProvisioningCandidate[];
  provisioningWinner?: ProvisioningWinner | null;
  isProvisioning?: boolean;
  currentRound?: number;
  maxRounds?: number;
  raceError?: string | null;
  isFailed?: boolean;
  onCancelProvisioning?: () => void;
  onCompleteProvisioning?: (winner: ProvisioningWinner) => void;
}

export interface WizardSubmitData {
  machine: MachineOffer;
  offerId: string | number;
  failoverStrategy: FailoverStrategy;
  tier: string | null;
  regions: SelectedLocation[];
  allOffers: MachineOffer[];
  dockerImage?: string;
  exposedPorts?: PortConfig[];
  snapshot?: Snapshot | null;
}

// ============================================================================
// Step Definition Types
// ============================================================================

export interface StepDefinition {
  id: WizardStep;
  name: string;
  icon: LucideIcon;
  description: string;
}

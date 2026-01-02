/**
 * Wizard Feature Module
 *
 * GPU provisioning wizard with multi-step flow.
 *
 * @example
 * ```tsx
 * import { WizardForm, useWizardForm } from '@/features/wizard';
 *
 * // Using the component directly
 * <WizardForm
 *   onComplete={(winner) => console.log('Selected:', winner)}
 *   WorldMapComponent={WorldMap}
 * />
 *
 * // Or using the hook for custom UI
 * const { state, actions, validation } = useWizardForm();
 * ```
 */

// Main Component
export { WizardForm, type WizardFormProps } from './components';

// Adapter for backward compatibility with legacy Dashboard
export { WizardFormAdapter, type WizardFormAdapterProps } from './components';

// Hooks
export {
  useWizardForm,
  useWizardState,
  useWizardApi,
  useProvisioningTimer,
  useWizardValidation,
  // State management
  wizardReducer,
  initialWizardState,
  // Validation utilities
  isStepComplete,
  isStepPassed,
  canProceedToStep,
  validateCurrentStep,
  validateBeforeProvisioning,
  hasMinimumBalance,
  // Timer utilities
  formatTime,
  calculateETA,
  type UseWizardFormOptions,
} from './hooks';

// Services
export {
  WizardApiService,
  ApiError,
  createWizardApi,
  getWizardApi,
  resetWizardApi,
  type HttpClient,
  type WizardApiConfig,
} from './services';

// Constants
export {
  PERFORMANCE_TIERS,
  TIER_NAMES,
  FAILOVER_STRATEGIES,
  STRATEGY_IDS,
  REGIONS,
  REGION_KEYS,
  COUNTRY_NAMES,
  GPU_OPTIONS,
  GPU_CATEGORIES,
  WIZARD_DEFAULTS,
  WIZARD_STEPS,
  // Utility functions
  getTierByName,
  getTierFilterParams,
  getEstimatedCostFromTier,
  getStrategyById,
  getDefaultStrategy,
  getAvailableStrategies,
  getRegionByKey,
  getCountryName,
  createLocationFromCountry,
  createLocationFromRegion,
  filterGPUs,
  getGPUByName,
} from './constants';

// Types
export type {
  // Core types
  WizardState,
  WizardStep,
  WizardAction,
  Location,
  Region,
  RegionKey,
  // GPU/Tier types
  PerformanceTier,
  TierName,
  TierFilter,
  GPUOption,
  // Machine types
  MachineOffer,
  RecommendedMachine,
  // Failover types
  FailoverStrategy,
  FailoverStrategyId,
  // Provisioning types
  ProvisioningStatus,
  ProvisioningCandidate,
  ProvisioningConfig,
  PortConfig,
  // API types
  OffersApiParams,
  OffersApiResponse,
  BalanceApiResponse,
  // Hook return types
  UseWizardFormReturn,
  UseWizardApiReturn,
  WizardActions,
  WizardValidation,
  WizardComputed,
} from './types';

// Step Components (for custom layouts)
export {
  LocationStep,
  HardwareStep,
  StrategyStep,
  ProvisioningStep,
  WizardStepper,
  type LocationStepProps,
  type HardwareStepProps,
  type StrategyStepProps,
  type ProvisioningStepProps,
  type WizardStepperProps,
} from './components';

/**
 * Wizard Hooks - Re-exports
 */

// Main hook
export { useWizardForm, type UseWizardFormOptions } from './useWizardForm';

// State management
export {
  useWizardState,
  wizardReducer,
  initialWizardState,
  type UseWizardStateReturn,
} from './useWizardState';

// API hook
export {
  useWizardApi,
  type UseWizardApiOptions,
  type UseWizardApiReturn,
} from './useWizardApi';

// Timer hook
export {
  useProvisioningTimer,
  formatTime,
  calculateETA,
  type UseProvisioningTimerOptions,
  type UseProvisioningTimerReturn,
} from './useProvisioningTimer';

// Validation
export {
  useWizardValidation,
  // Pure validation functions (for testing)
  isStepComplete,
  isStepPassed,
  canProceedToStep,
  validateCurrentStep,
  validateBeforeProvisioning,
  validateLocationStep,
  validateHardwareStep,
  validateStrategyStep,
  validateBalance,
  hasMinimumBalance,
  isLocationComplete,
  isHardwareComplete,
  isStrategyComplete,
  isProvisioningComplete,
  type UseWizardValidationReturn,
} from './useWizardValidation';

/**
 * Wizard Validation Hook
 *
 * Pure validation logic extracted for easy testing.
 * All validation functions are pure and can be tested independently.
 */

import { WizardState, WizardStep } from '../types';
import { WIZARD_DEFAULTS } from '../constants';

// ============================================================================
// Pure Validation Functions (Easy to Test)
// ============================================================================

/**
 * Check if step 1 (Location) is complete
 */
export function isLocationComplete(state: WizardState): boolean {
  return state.selectedLocation !== null;
}

/**
 * Check if step 2 (Hardware) is complete
 */
export function isHardwareComplete(state: WizardState): boolean {
  return state.selectedTier !== null;
}

/**
 * Check if step 3 (Strategy) is complete
 */
export function isStrategyComplete(state: WizardState): boolean {
  return state.failoverStrategy !== null;
}

/**
 * Check if step 4 (Provisioning) is complete
 */
export function isProvisioningComplete(state: WizardState): boolean {
  return state.provisioningWinner !== null;
}

/**
 * Check if a specific step is complete
 */
export function isStepComplete(state: WizardState, step: WizardStep): boolean {
  switch (step) {
    case 1:
      return isLocationComplete(state);
    case 2:
      return isHardwareComplete(state);
    case 3:
      return isStrategyComplete(state);
    case 4:
      return isProvisioningComplete(state);
    default:
      return false;
  }
}

/**
 * Check if a step has been passed (completed and moved beyond)
 */
export function isStepPassed(state: WizardState, step: WizardStep): boolean {
  return state.currentStep > step && isStepComplete(state, step);
}

/**
 * Check if user can proceed to a specific step
 */
export function canProceedToStep(state: WizardState, targetStep: WizardStep): boolean {
  if (targetStep < state.currentStep) return true;
  if (targetStep === state.currentStep) return true;
  if (targetStep === state.currentStep + 1) {
    return isStepComplete(state, state.currentStep);
  }
  return false;
}

/**
 * Validate step 1
 */
export function validateLocationStep(state: WizardState): string[] {
  const errors: string[] = [];
  if (!state.selectedLocation) {
    errors.push('Por favor, selecione uma localização para sua máquina');
  }
  return errors;
}

/**
 * Validate step 2
 */
export function validateHardwareStep(state: WizardState): string[] {
  const errors: string[] = [];
  if (!state.selectedTier) {
    errors.push('Por favor, selecione um tier de performance');
  }
  return errors;
}

/**
 * Validate step 3
 */
export function validateStrategyStep(state: WizardState): string[] {
  const errors: string[] = [];
  if (!state.failoverStrategy) {
    errors.push('Por favor, selecione uma estratégia de failover');
  }
  return errors;
}

/**
 * Validate balance requirement
 */
export function validateBalance(
  balance: number,
  minBalance: number = WIZARD_DEFAULTS.minBalance,
): string[] {
  const errors: string[] = [];
  if (balance < minBalance) {
    errors.push(
      `Saldo insuficiente. Você precisa de pelo menos $${minBalance.toFixed(2)} para criar uma máquina. Saldo atual: $${balance.toFixed(2)}`,
    );
  }
  return errors;
}

/**
 * Get all validation errors for current step
 */
export function validateCurrentStep(state: WizardState): string[] {
  switch (state.currentStep) {
    case 1:
      return validateLocationStep(state);
    case 2:
      return validateHardwareStep(state);
    case 3:
      return validateStrategyStep(state);
    default:
      return [];
  }
}

/**
 * Validate before starting provisioning
 */
export function validateBeforeProvisioning(
  state: WizardState,
  balance: number,
): string[] {
  const errors: string[] = [];

  // Validate all steps
  errors.push(...validateLocationStep(state));
  errors.push(...validateHardwareStep(state));
  errors.push(...validateStrategyStep(state));

  // Validate balance
  errors.push(...validateBalance(balance));

  return errors;
}

/**
 * Check if has minimum balance
 */
export function hasMinimumBalance(
  balance: number,
  minBalance: number = WIZARD_DEFAULTS.minBalance,
): boolean {
  return balance >= minBalance;
}

// ============================================================================
// Hook (Optional - wraps pure functions with state)
// ============================================================================

export interface UseWizardValidationReturn {
  isStepComplete: (step: WizardStep) => boolean;
  isStepPassed: (step: WizardStep) => boolean;
  canProceedToStep: (step: WizardStep) => boolean;
  validateCurrentStep: () => string[];
  validateBeforeProvisioning: (balance: number) => string[];
  hasMinimumBalance: (balance: number) => boolean;
}

export function useWizardValidation(state: WizardState): UseWizardValidationReturn {
  return {
    isStepComplete: (step: WizardStep) => isStepComplete(state, step),
    isStepPassed: (step: WizardStep) => isStepPassed(state, step),
    canProceedToStep: (step: WizardStep) => canProceedToStep(state, step),
    validateCurrentStep: () => validateCurrentStep(state),
    validateBeforeProvisioning: (balance: number) => validateBeforeProvisioning(state, balance),
    hasMinimumBalance,
  };
}

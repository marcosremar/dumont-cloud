/**
 * Wizard Validation Utilities
 */

import type { WizardState, WizardStep, MachineOffer } from '../types/wizard.types';

const MIN_BALANCE = 0.10; // Minimum balance required ($0.10)

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

/**
 * Validate Step 1: Location
 */
export function validateLocationStep(state: WizardState): ValidationResult {
  const errors: string[] = [];

  if (state.selectedLocations.length === 0) {
    errors.push('Please select a location for your machine');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate Step 2: Hardware
 */
export function validateHardwareStep(state: WizardState): ValidationResult {
  const errors: string[] = [];

  if (!state.selectedTier) {
    errors.push('Please select a performance tier');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate Step 3: Strategy
 */
export function validateStrategyStep(
  state: WizardState,
  userBalance: number | null
): ValidationResult {
  const errors: string[] = [];

  if (!state.failoverStrategy) {
    errors.push('Please select a failover strategy');
  }

  if (userBalance !== null && userBalance < MIN_BALANCE) {
    errors.push(
      `Insufficient balance. You need at least $${MIN_BALANCE.toFixed(2)} to create a machine. Current balance: $${userBalance.toFixed(2)}`
    );
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate all steps before submission
 */
export function validateAllSteps(
  state: WizardState,
  userBalance: number | null,
  selectedMachine: MachineOffer | null,
  recommendedMachines: MachineOffer[]
): ValidationResult {
  const allErrors: string[] = [];

  // Step 1
  const step1 = validateLocationStep(state);
  allErrors.push(...step1.errors);

  // Step 2
  const step2 = validateHardwareStep(state);
  allErrors.push(...step2.errors);

  // Step 3
  const step3 = validateStrategyStep(state, userBalance);
  allErrors.push(...step3.errors);

  // Machine availability
  const machineToUse = selectedMachine || recommendedMachines[0];
  if (!machineToUse) {
    allErrors.push('No machines available. Please try a different region or tier.');
  }

  return {
    isValid: allErrors.length === 0,
    errors: allErrors,
  };
}

/**
 * Check if a specific step is complete
 */
export function isStepComplete(step: WizardStep, state: WizardState): boolean {
  switch (step) {
    case 1:
      return state.selectedLocations.length > 0;
    case 2:
      return state.selectedTier !== null;
    case 3:
      return state.failoverStrategy !== null;
    case 4:
      return true; // Provisioning step is always "complete" for navigation
    default:
      return false;
  }
}

/**
 * Check if a step has been passed (completed and moved past)
 */
export function isStepPassed(step: WizardStep, currentStep: WizardStep, state: WizardState): boolean {
  if (step >= currentStep) return false;
  return isStepComplete(step, state);
}

/**
 * Get the first incomplete step
 */
export function getFirstIncompleteStep(state: WizardState): WizardStep {
  for (let step = 1; step <= 4; step++) {
    if (!isStepComplete(step as WizardStep, state)) {
      return step as WizardStep;
    }
  }
  return 4;
}

export default {
  validateLocationStep,
  validateHardwareStep,
  validateStrategyStep,
  validateAllSteps,
  isStepComplete,
  isStepPassed,
  getFirstIncompleteStep,
  MIN_BALANCE,
};

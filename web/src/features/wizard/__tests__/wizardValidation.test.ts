/**
 * Wizard Validation Tests
 *
 * Tests for pure validation functions.
 */

import { describe, it, expect } from 'vitest';
import {
  isStepComplete,
  isStepPassed,
  canProceedToStep,
  validateLocationStep,
  validateHardwareStep,
  validateStrategyStep,
  validateBalance,
  validateBeforeProvisioning,
  hasMinimumBalance,
} from '../hooks/useWizardValidation';
import { initialWizardState } from '../hooks/useWizardState';
import { WizardState } from '../types';

describe('Validation Functions', () => {
  describe('isStepComplete', () => {
    it('step 1 is complete when location is selected', () => {
      const state = {
        ...initialWizardState,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
      };

      expect(isStepComplete(state, 1)).toBe(true);
    });

    it('step 1 is incomplete when location is null', () => {
      expect(isStepComplete(initialWizardState, 1)).toBe(false);
    });

    it('step 2 is complete when tier is selected', () => {
      const state = { ...initialWizardState, selectedTier: 'Rapido' as const };

      expect(isStepComplete(state, 2)).toBe(true);
    });

    it('step 2 is incomplete when tier is null', () => {
      expect(isStepComplete(initialWizardState, 2)).toBe(false);
    });

    it('step 3 is complete when failover strategy is selected', () => {
      // Default state has snapshot_only selected
      expect(isStepComplete(initialWizardState, 3)).toBe(true);
    });

    it('step 4 is complete when winner is selected', () => {
      const state = {
        ...initialWizardState,
        provisioningWinner: { id: 1, gpu_name: 'RTX 4090' } as any,
      };

      expect(isStepComplete(state, 4)).toBe(true);
    });

    it('step 4 is incomplete when winner is null', () => {
      expect(isStepComplete(initialWizardState, 4)).toBe(false);
    });
  });

  describe('isStepPassed', () => {
    it('step is passed when current step is greater and step is complete', () => {
      const state: WizardState = {
        ...initialWizardState,
        currentStep: 2,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
      };

      expect(isStepPassed(state, 1)).toBe(true);
    });

    it('step is not passed when current step equals the step', () => {
      const state = {
        ...initialWizardState,
        currentStep: 1 as const,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
      };

      expect(isStepPassed(state, 1)).toBe(false);
    });

    it('step is not passed when step is incomplete', () => {
      const state = { ...initialWizardState, currentStep: 2 as const };

      expect(isStepPassed(state, 1)).toBe(false);
    });
  });

  describe('canProceedToStep', () => {
    it('can go back to previous steps', () => {
      const state = { ...initialWizardState, currentStep: 3 as const };

      expect(canProceedToStep(state, 1)).toBe(true);
      expect(canProceedToStep(state, 2)).toBe(true);
    });

    it('can stay on current step', () => {
      const state = { ...initialWizardState, currentStep: 2 as const };

      expect(canProceedToStep(state, 2)).toBe(true);
    });

    it('can go to next step if current is complete', () => {
      const state = {
        ...initialWizardState,
        currentStep: 1 as const,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
      };

      expect(canProceedToStep(state, 2)).toBe(true);
    });

    it('cannot go to next step if current is incomplete', () => {
      const state = { ...initialWizardState, currentStep: 1 as const };

      expect(canProceedToStep(state, 2)).toBe(false);
    });

    it('cannot skip steps', () => {
      const state = {
        ...initialWizardState,
        currentStep: 1 as const,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
      };

      expect(canProceedToStep(state, 3)).toBe(false);
    });
  });

  describe('validateLocationStep', () => {
    it('returns error when location is null', () => {
      const errors = validateLocationStep(initialWizardState);

      expect(errors).toHaveLength(1);
      expect(errors[0]).toContain('localização');
    });

    it('returns empty array when location is selected', () => {
      const state = {
        ...initialWizardState,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
      };

      expect(validateLocationStep(state)).toEqual([]);
    });
  });

  describe('validateHardwareStep', () => {
    it('returns error when tier is null', () => {
      const errors = validateHardwareStep(initialWizardState);

      expect(errors).toHaveLength(1);
      expect(errors[0]).toContain('tier');
    });

    it('returns empty array when tier is selected', () => {
      const state = { ...initialWizardState, selectedTier: 'Rapido' as const };

      expect(validateHardwareStep(state)).toEqual([]);
    });
  });

  describe('validateBalance', () => {
    it('returns error when balance is below minimum', () => {
      const errors = validateBalance(0.05, 0.10);

      expect(errors).toHaveLength(1);
      expect(errors[0]).toContain('insuficiente');
    });

    it('returns empty array when balance is sufficient', () => {
      const errors = validateBalance(0.50, 0.10);

      expect(errors).toEqual([]);
    });

    it('returns empty array when balance equals minimum', () => {
      const errors = validateBalance(0.10, 0.10);

      expect(errors).toEqual([]);
    });
  });

  describe('hasMinimumBalance', () => {
    it('returns true when balance is sufficient', () => {
      expect(hasMinimumBalance(1.00, 0.10)).toBe(true);
    });

    it('returns false when balance is insufficient', () => {
      expect(hasMinimumBalance(0.05, 0.10)).toBe(false);
    });

    it('returns true when balance equals minimum', () => {
      expect(hasMinimumBalance(0.10, 0.10)).toBe(true);
    });
  });

  describe('validateBeforeProvisioning', () => {
    it('returns all validation errors for incomplete state', () => {
      const errors = validateBeforeProvisioning(initialWizardState, 0.05);

      expect(errors.length).toBeGreaterThan(0);
      expect(errors.some((e) => e.includes('localização'))).toBe(true);
      expect(errors.some((e) => e.includes('tier'))).toBe(true);
      expect(errors.some((e) => e.includes('insuficiente'))).toBe(true);
    });

    it('returns only balance error for complete state with low balance', () => {
      const state: WizardState = {
        ...initialWizardState,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
        selectedTier: 'Rapido',
        failoverStrategy: 'snapshot_only',
      };

      const errors = validateBeforeProvisioning(state, 0.05);

      expect(errors).toHaveLength(1);
      expect(errors[0]).toContain('insuficiente');
    });

    it('returns empty array for complete state with sufficient balance', () => {
      const state: WizardState = {
        ...initialWizardState,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
        selectedTier: 'Rapido',
        failoverStrategy: 'snapshot_only',
      };

      const errors = validateBeforeProvisioning(state, 10.00);

      expect(errors).toEqual([]);
    });
  });
});

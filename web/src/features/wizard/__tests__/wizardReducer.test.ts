/**
 * Wizard Reducer Tests
 *
 * Tests for the pure reducer function.
 */

import { describe, it, expect } from 'vitest';
import { wizardReducer, initialWizardState } from '../hooks/useWizardState';
import { WizardState, WizardAction } from '../types';

describe('wizardReducer', () => {
  describe('SET_STEP', () => {
    it('should update current step', () => {
      const state = { ...initialWizardState, currentStep: 1 as const };
      const action: WizardAction = { type: 'SET_STEP', payload: 2 };

      const result = wizardReducer(state, action);

      expect(result.currentStep).toBe(2);
    });

    it('should clear validation errors when changing step', () => {
      const state = {
        ...initialWizardState,
        currentStep: 1 as const,
        validationErrors: ['Some error'],
      };
      const action: WizardAction = { type: 'SET_STEP', payload: 2 };

      const result = wizardReducer(state, action);

      expect(result.validationErrors).toEqual([]);
    });
  });

  describe('SET_LOCATION', () => {
    it('should update selected location', () => {
      const location = { codes: ['US'], name: 'Estados Unidos', isRegion: false };
      const action: WizardAction = { type: 'SET_LOCATION', payload: location };

      const result = wizardReducer(initialWizardState, action);

      expect(result.selectedLocation).toEqual(location);
    });

    it('should allow setting location to null', () => {
      const state = {
        ...initialWizardState,
        selectedLocation: { codes: ['US'], name: 'Estados Unidos', isRegion: false },
      };
      const action: WizardAction = { type: 'SET_LOCATION', payload: null };

      const result = wizardReducer(state, action);

      expect(result.selectedLocation).toBeNull();
    });
  });

  describe('SET_TIER', () => {
    it('should update selected tier', () => {
      const action: WizardAction = { type: 'SET_TIER', payload: 'Rapido' };

      const result = wizardReducer(initialWizardState, action);

      expect(result.selectedTier).toBe('Rapido');
    });

    it('should reset machine and GPU when tier changes', () => {
      const state = {
        ...initialWizardState,
        selectedTier: 'Lento' as const,
        selectedMachine: { id: 1, gpu_name: 'RTX 3060' } as any,
        selectedGPU: 'RTX 3060',
      };
      const action: WizardAction = { type: 'SET_TIER', payload: 'Rapido' };

      const result = wizardReducer(state, action);

      expect(result.selectedTier).toBe('Rapido');
      expect(result.selectedMachine).toBeNull();
      expect(result.selectedGPU).toBeNull();
    });
  });

  describe('SET_FAILOVER_STRATEGY', () => {
    it('should update failover strategy', () => {
      const action: WizardAction = { type: 'SET_FAILOVER_STRATEGY', payload: 'vast_warmpool' };

      const result = wizardReducer(initialWizardState, action);

      expect(result.failoverStrategy).toBe('vast_warmpool');
    });
  });

  describe('Port Management', () => {
    it('ADD_PORT should add a new port config', () => {
      const initialPorts = initialWizardState.exposedPorts.length;
      const action: WizardAction = { type: 'ADD_PORT' };

      const result = wizardReducer(initialWizardState, action);

      expect(result.exposedPorts).toHaveLength(initialPorts + 1);
      expect(result.exposedPorts[result.exposedPorts.length - 1]).toEqual({
        port: '',
        protocol: 'TCP',
      });
    });

    it('REMOVE_PORT should remove port at index', () => {
      const state = {
        ...initialWizardState,
        exposedPorts: [
          { port: '22', protocol: 'TCP' as const },
          { port: '8888', protocol: 'TCP' as const },
          { port: '6006', protocol: 'TCP' as const },
        ],
      };
      const action: WizardAction = { type: 'REMOVE_PORT', payload: 1 };

      const result = wizardReducer(state, action);

      expect(result.exposedPorts).toHaveLength(2);
      expect(result.exposedPorts.map((p) => p.port)).toEqual(['22', '6006']);
    });

    it('UPDATE_PORT should update port at index', () => {
      const action: WizardAction = {
        type: 'UPDATE_PORT',
        payload: { index: 0, config: { port: '3000', protocol: 'UDP' } },
      };

      const result = wizardReducer(initialWizardState, action);

      expect(result.exposedPorts[0]).toEqual({ port: '3000', protocol: 'UDP' });
    });
  });

  describe('Provisioning', () => {
    it('SET_PROVISIONING_CANDIDATES should update candidates', () => {
      const candidates = [
        { id: 1, gpu_name: 'RTX 4090', status: 'pending' as const },
        { id: 2, gpu_name: 'RTX 3090', status: 'pending' as const },
      ] as any[];
      const action: WizardAction = { type: 'SET_PROVISIONING_CANDIDATES', payload: candidates };

      const result = wizardReducer(initialWizardState, action);

      expect(result.provisioningCandidates).toEqual(candidates);
    });

    it('SET_PROVISIONING_WINNER should set winner and stop provisioning', () => {
      const state = { ...initialWizardState, isProvisioning: true };
      const winner = { id: 1, gpu_name: 'RTX 4090', status: 'connected' as const } as any;
      const action: WizardAction = { type: 'SET_PROVISIONING_WINNER', payload: winner };

      const result = wizardReducer(state, action);

      expect(result.provisioningWinner).toEqual(winner);
      expect(result.isProvisioning).toBe(false);
    });
  });

  describe('RESET', () => {
    it('should reset to initial state', () => {
      const modifiedState: WizardState = {
        ...initialWizardState,
        currentStep: 3,
        selectedLocation: { codes: ['US'], name: 'EUA', isRegion: true },
        selectedTier: 'Ultra',
        failoverStrategy: 'vast_warmpool',
        validationErrors: ['Error'],
      };
      const action: WizardAction = { type: 'RESET' };

      const result = wizardReducer(modifiedState, action);

      expect(result).toEqual(initialWizardState);
    });
  });

  describe('TOGGLE_ADVANCED_SETTINGS', () => {
    it('should toggle showAdvancedSettings', () => {
      expect(initialWizardState.showAdvancedSettings).toBe(false);

      const result1 = wizardReducer(initialWizardState, { type: 'TOGGLE_ADVANCED_SETTINGS' });
      expect(result1.showAdvancedSettings).toBe(true);

      const result2 = wizardReducer(result1, { type: 'TOGGLE_ADVANCED_SETTINGS' });
      expect(result2.showAdvancedSettings).toBe(false);
    });
  });
});

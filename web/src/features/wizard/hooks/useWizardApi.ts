/**
 * Wizard API Hook
 *
 * Handles API calls with loading and error states.
 * Accepts optional api service for testing.
 */

import { useState, useCallback, useRef } from 'react';
import {
  MachineOffer,
  RecommendedMachine,
  OffersApiParams,
  ProvisioningConfig,
  ProvisioningCandidate,
  TierName,
  Location,
} from '../types';
import { WizardApiService, createWizardApi } from '../services';
import { WIZARD_DEFAULTS } from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface UseWizardApiOptions {
  api?: WizardApiService;
}

export interface UseWizardApiReturn {
  // State
  isLoading: boolean;
  error: string | null;
  // Actions
  fetchOffers: (params: OffersApiParams) => Promise<MachineOffer[]>;
  fetchOffersByTier: (
    tierName: TierName,
    location: Location | null,
  ) => Promise<RecommendedMachine[]>;
  fetchBalance: () => Promise<number>;
  startProvisioning: (config: ProvisioningConfig) => Promise<ProvisioningCandidate[]>;
  provisionMachine: (machineId: number, config: ProvisioningConfig) => Promise<{ success: boolean; instanceId?: string }>;
  cancelProvisioning: () => void;
  clearError: () => void;
}

// ============================================================================
// Hook
// ============================================================================

export function useWizardApi(options: UseWizardApiOptions = {}): UseWizardApiReturn {
  const api = useRef(options.api ?? createWizardApi());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Fetch offers with params
   */
  const fetchOffers = useCallback(async (params: OffersApiParams): Promise<MachineOffer[]> => {
    setIsLoading(true);
    setError(null);

    try {
      const offers = await api.current.fetchOffers(params);
      return offers;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao buscar ofertas';
      setError(message);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Fetch offers filtered by tier and location
   */
  const fetchOffersByTier = useCallback(async (
    tierName: TierName,
    location: Location | null,
  ): Promise<RecommendedMachine[]> => {
    setIsLoading(true);
    setError(null);

    try {
      const regionCode = location?.codes?.[0];
      const offers = await api.current.fetchOffersByTier(
        tierName,
        regionCode,
        WIZARD_DEFAULTS.offersLimit,
      );
      return offers;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao buscar ofertas';
      setError(message);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Fetch user balance
   */
  const fetchBalance = useCallback(async (): Promise<number> => {
    try {
      return await api.current.fetchBalance();
    } catch (err) {
      console.error('Failed to fetch balance:', err);
      return 0;
    }
  }, []);

  /**
   * Start provisioning machines
   */
  const startProvisioning = useCallback(async (
    config: ProvisioningConfig,
  ): Promise<ProvisioningCandidate[]> => {
    setIsLoading(true);
    setError(null);

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    try {
      const result = await api.current.startProvisioning(config);
      return result.candidates;
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Cancelled by user, not an error
        return [];
      }
      const message = err instanceof Error ? err.message : 'Erro ao provisionar';
      setError(message);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Provision a specific machine (call real API)
   */
  const provisionMachine = useCallback(async (
    machineId: number,
    config: ProvisioningConfig,
  ): Promise<{ success: boolean; instanceId?: string }> => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await api.current.provisionMachine(machineId, config);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao provisionar máquina';
      setError(message);
      return { success: false };
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Cancel ongoing provisioning
   */
  const cancelProvisioning = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    isLoading,
    error,
    fetchOffers,
    fetchOffersByTier,
    fetchBalance,
    startProvisioning,
    provisionMachine,
    cancelProvisioning,
    clearError,
  };
}

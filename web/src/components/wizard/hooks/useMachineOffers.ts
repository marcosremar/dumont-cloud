/**
 * useMachineOffers Hook
 * Fetches and manages machine offers from the API
 */

import { useState, useEffect, useCallback } from 'react';
import type { MachineOffer, SelectedLocation } from '../types/wizard.types';
import { locationsToRegionCodes } from '../constants/regionMapping';
import { PERFORMANCE_TIERS } from '../../dashboard/constants';

interface UseMachineOffersOptions {
  selectedTier: string | null;
  selectedLocations: SelectedLocation[];
  enabled?: boolean;
}

interface UseMachineOffersReturn {
  recommendedMachines: MachineOffer[];
  allAvailableOffers: MachineOffer[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useMachineOffers({
  selectedTier,
  selectedLocations,
  enabled = true,
}: UseMachineOffersOptions): UseMachineOffersReturn {
  const [recommendedMachines, setRecommendedMachines] = useState<MachineOffer[]>([]);
  const [allAvailableOffers, setAllAvailableOffers] = useState<MachineOffer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMachines = useCallback(async () => {
    if (!selectedTier || !enabled) {
      setRecommendedMachines([]);
      setAllAvailableOffers([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Get tier config for price range
      const tier = PERFORMANCE_TIERS.find((t) => t.name === selectedTier);

      // Map region selection to API-expected codes
      const regionCodes = locationsToRegionCodes(selectedLocations);

      // Build query params
      const params = new URLSearchParams();
      params.set('limit', '50');
      params.set('order', 'dph_total');

      // Add tier-based filters
      if (tier) {
        if (tier.minVram) params.set('min_gpu_ram', tier.minVram.toString());
        if (tier.maxVram) params.set('max_gpu_ram', tier.maxVram.toString());
        if (tier.minPrice) params.set('min_dph', tier.minPrice.toString());
        if (tier.maxPrice) params.set('max_dph', tier.maxPrice.toString());
      }

      // Add region filter if selected
      if (regionCodes.length > 0) {
        params.set('geolocation', regionCodes.join(','));
      }

      // Fetch from API
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/v1/gpu/offers?${params.toString()}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const offers: MachineOffer[] = data.offers || data || [];

      // Store all offers for racing
      setAllAvailableOffers(offers);

      // Filter recommended (verified, reliable)
      const recommended = offers
        .filter((o: MachineOffer) => o.verified && (o.reliability || 0) > 90)
        .slice(0, 5);

      setRecommendedMachines(recommended.length > 0 ? recommended : offers.slice(0, 5));
    } catch (err) {
      console.error('Failed to fetch machines:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch machines');
      setRecommendedMachines([]);
      setAllAvailableOffers([]);
    } finally {
      setLoading(false);
    }
  }, [selectedTier, selectedLocations, enabled]);

  useEffect(() => {
    fetchMachines();
  }, [fetchMachines]);

  return {
    recommendedMachines,
    allAvailableOffers,
    loading,
    error,
    refetch: fetchMachines,
  };
}

export default useMachineOffers;

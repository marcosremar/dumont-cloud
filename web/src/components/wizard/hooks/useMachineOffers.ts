/**
 * useMachineOffers Hook
 * Fetches and manages machine offers from the API
 */

import { useState, useEffect, useCallback } from 'react';
import type { MachineOffer, SelectedLocation } from '../types/wizard.types';
import { locationsToRegionCodes } from '../constants/regionMapping';
import { PERFORMANCE_TIERS, DEMO_OFFERS } from '../../dashboard/constants';

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

      // Add tier-based filters (using filter object from PERFORMANCE_TIERS)
      if (tier?.filter) {
        const filter = tier.filter as {
          max_price?: number;
          min_gpu_ram?: number;
          cpu_only?: boolean;
          verified_only?: boolean;
        };
        if (filter.cpu_only) {
          params.set('cpu_only', 'true');
        }
        if (filter.min_gpu_ram) {
          params.set('min_gpu_ram', filter.min_gpu_ram.toString());
        }
        if (filter.max_price) {
          params.set('max_price', filter.max_price.toString());
        }
        if (filter.verified_only) {
          params.set('verified_only', 'true');
        }
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
      console.error('Failed to fetch machines, using demo data:', err);

      // Fallback to demo offers when API fails
      const tier = PERFORMANCE_TIERS.find((t) => t.name === selectedTier);
      const regionCodes = locationsToRegionCodes(selectedLocations);

      let filteredDemo = DEMO_OFFERS.filter((offer: MachineOffer) => {
        // Region filter
        if (regionCodes.length > 0) {
          const offerRegion = offer.geolocation || '';
          if (!regionCodes.some(r => offerRegion.includes(r))) return false;
        }

        // Tier filter
        if (tier?.filter) {
          const filter = tier.filter as { max_price?: number; min_gpu_ram?: number; cpu_only?: boolean };
          if (filter.cpu_only && !offer.isCPU) return false;
          if (!filter.cpu_only && offer.isCPU) return false;
          if (filter.min_gpu_ram && (offer.gpu_ram || 0) < filter.min_gpu_ram) return false;
          if (filter.max_price && (offer.dph_total || 0) > filter.max_price) return false;
        }

        return true;
      });

      setAllAvailableOffers(filteredDemo);
      setRecommendedMachines(filteredDemo.slice(0, 5));
      setError(null); // Clear error since we have fallback data
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

/**
 * Offer Filtering and Sorting Utilities
 * Used for preparing offers for the provisioning race
 */

import type { MachineOffer } from '../types/wizard.types';

const MIN_RACING_MACHINES = 5;
const MAX_RACING_MACHINES = 15; // 5 per round x 3 rounds

export interface OfferBreakdown {
  exactMatches: MachineOffer[];
  sameGpuMatches: MachineOffer[];
  otherOffers: MachineOffer[];
  total: number;
}

/**
 * Get offers for racing with progressive relaxation
 * Priority:
 * 1. Exact match (same GPU name AND same GPU count)
 * 2. Same GPU name (any count)
 * 3. Any available machine (sorted by price)
 */
export function getOffersForRacing(
  allOffers: MachineOffer[],
  selectedMachine: MachineOffer
): MachineOffer[] {
  const breakdown = getOfferBreakdown(allOffers, selectedMachine);

  // Combine: selected machine first, then exact matches, then same GPU, then others
  let offersForRacing: MachineOffer[] = [selectedMachine, ...breakdown.exactMatches];

  // Add more if we don't have enough
  if (offersForRacing.length < MIN_RACING_MACHINES) {
    const needed = MIN_RACING_MACHINES - offersForRacing.length;
    offersForRacing = [...offersForRacing, ...breakdown.sameGpuMatches.slice(0, needed)];
  }

  // Still not enough? Add from other offers
  if (offersForRacing.length < MIN_RACING_MACHINES) {
    const needed = MIN_RACING_MACHINES - offersForRacing.length;
    offersForRacing = [...offersForRacing, ...breakdown.otherOffers.slice(0, needed)];
  }

  // Limit to max (for 3 rounds)
  return offersForRacing.slice(0, MAX_RACING_MACHINES);
}

/**
 * Get breakdown of offers by match priority
 */
export function getOfferBreakdown(
  allOffers: MachineOffer[],
  selectedMachine: MachineOffer
): OfferBreakdown {
  // Priority 1: Exact match (same GPU name AND same GPU count)
  const exactMatches = allOffers.filter((offer) => {
    const sameGpu = offer.gpu_name === selectedMachine.gpu_name;
    const sameGpuCount = offer.num_gpus === selectedMachine.num_gpus;
    const notSameMachine = offer.id !== selectedMachine.id;
    return sameGpu && sameGpuCount && notSameMachine;
  });

  // Priority 2: Same GPU name (any count)
  const sameGpuMatches = allOffers.filter((offer) => {
    const sameGpu = offer.gpu_name === selectedMachine.gpu_name;
    const notSameMachine = offer.id !== selectedMachine.id;
    const notInExact = !exactMatches.some((e) => e.id === offer.id);
    return sameGpu && notSameMachine && notInExact;
  });

  // Priority 3: Any available machine from the tier (sorted by price)
  const otherOffers = allOffers
    .filter((offer) => {
      const notSameMachine = offer.id !== selectedMachine.id;
      const notInExact = !exactMatches.some((e) => e.id === offer.id);
      const notInSameGpu = !sameGpuMatches.some((e) => e.id === offer.id);
      return notSameMachine && notInExact && notInSameGpu;
    })
    .sort((a, b) => (a.dph_total || 0) - (b.dph_total || 0));

  return {
    exactMatches,
    sameGpuMatches,
    otherOffers,
    total: 1 + exactMatches.length + sameGpuMatches.length + otherOffers.length,
  };
}

/**
 * Sort offers by price (ascending)
 */
export function sortByPrice(offers: MachineOffer[]): MachineOffer[] {
  return [...offers].sort((a, b) => (a.dph_total || 0) - (b.dph_total || 0));
}

/**
 * Sort offers by reliability (descending)
 */
export function sortByReliability(offers: MachineOffer[]): MachineOffer[] {
  return [...offers].sort((a, b) => (b.reliability || 0) - (a.reliability || 0));
}

/**
 * Sort offers by performance (descending)
 */
export function sortByPerformance(offers: MachineOffer[]): MachineOffer[] {
  return [...offers].sort((a, b) => (b.dlperf || 0) - (a.dlperf || 0));
}

/**
 * Filter verified offers only
 */
export function filterVerified(offers: MachineOffer[]): MachineOffer[] {
  return offers.filter((offer) => offer.verified);
}

/**
 * Get recommended offers (verified, high reliability, sorted by price)
 */
export function getRecommendedOffers(
  offers: MachineOffer[],
  limit: number = 5
): MachineOffer[] {
  return offers
    .filter((offer) => offer.verified && (offer.reliability || 0) > 90)
    .sort((a, b) => (a.dph_total || 0) - (b.dph_total || 0))
    .slice(0, limit);
}

export default {
  getOffersForRacing,
  getOfferBreakdown,
  sortByPrice,
  sortByReliability,
  sortByPerformance,
  filterVerified,
  getRecommendedOffers,
  MIN_RACING_MACHINES,
  MAX_RACING_MACHINES,
};

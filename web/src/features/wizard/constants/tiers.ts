/**
 * Performance Tiers Constants
 * Defines GPU performance tiers with filters for API queries
 */

import { PerformanceTier, TierName, TierFilter } from '../types';

export const PERFORMANCE_TIERS: readonly PerformanceTier[] = [
  {
    name: 'CPU',
    label: 'Apenas CPU',
    description: 'Sem GPU - apenas processamento CPU',
    gpu: 'Nenhuma',
    vram: '0GB',
    priceRange: '$0.01-0.05/h',
    filter: {
      gpu_count: 0,
      max_price: 0.05,
    },
  },
  {
    name: 'Lento',
    label: 'Experimentar',
    description: 'Para testes rápidos e experimentação',
    gpu: 'RTX 3060 / GTX 1080 Ti',
    vram: '8-12GB',
    priceRange: '$0.05-0.25/h',
    filter: {
      min_gpu_ram: 8,
      max_price: 0.25,
    },
  },
  {
    name: 'Medio',
    label: 'Desenvolver',
    description: 'Para desenvolvimento diário',
    gpu: 'RTX 3080 / RTX 4070',
    vram: '10-16GB',
    priceRange: '$0.20-0.45/h',
    filter: {
      min_gpu_ram: 10,
      max_price: 0.45,
    },
  },
  {
    name: 'Rapido',
    label: 'Treinar',
    description: 'Para fine-tuning e treinamento',
    gpu: 'RTX 4080 / RTX 4090',
    vram: '16-24GB',
    priceRange: '$0.35-0.85/h',
    filter: {
      min_gpu_ram: 16,
      max_price: 0.85,
    },
  },
  {
    name: 'Ultra',
    label: 'Produção',
    description: 'Para LLMs grandes e produção',
    gpu: 'A100 / H100',
    vram: '40-80GB',
    priceRange: '$0.80-3.50/h',
    filter: {
      min_gpu_ram: 40,
      max_price: 5.00,
    },
  },
] as const;

/**
 * Get tier by name
 */
export function getTierByName(name: TierName): PerformanceTier | undefined {
  return PERFORMANCE_TIERS.find(t => t.name === name);
}

/**
 * Get tier filter params for API
 */
export function getTierFilterParams(tierName: TierName): TierFilter {
  const tier = getTierByName(tierName);
  return tier?.filter ?? {};
}

/**
 * Calculate estimated cost from tier price range
 */
export function getEstimatedCostFromTier(tierName: TierName): { hourly: string; daily: string } {
  const tier = getTierByName(tierName);
  if (!tier) return { hourly: '0.00', daily: '0.00' };

  // Extract min price from priceRange like "$0.10-0.30/h"
  const match = tier.priceRange.match(/\$(\d+\.?\d*)/);
  const minPrice = match ? parseFloat(match[1]) : 0.20;

  return {
    hourly: minPrice.toFixed(2),
    daily: (minPrice * 24).toFixed(2),
  };
}

/**
 * Tier names as array for iteration
 */
export const TIER_NAMES: readonly TierName[] = ['CPU', 'Lento', 'Medio', 'Rapido', 'Ultra'] as const;

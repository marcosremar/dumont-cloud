/**
 * GPU Options Constants
 * Available GPU models for manual selection
 */

import { GPUOption } from '../types';

/**
 * All available GPU options for manual selection
 */
export const GPU_OPTIONS: readonly GPUOption[] = [
  { name: 'RTX 3060', vram: '12GB', priceRange: '$0.10-0.20/h' },
  { name: 'RTX 3060 Ti', vram: '8GB', priceRange: '$0.12-0.22/h' },
  { name: 'RTX 3070', vram: '8GB', priceRange: '$0.15-0.25/h' },
  { name: 'RTX 3070 Ti', vram: '8GB', priceRange: '$0.18-0.28/h' },
  { name: 'RTX 3080', vram: '10GB', priceRange: '$0.20-0.35/h' },
  { name: 'RTX 3080 Ti', vram: '12GB', priceRange: '$0.25-0.40/h' },
  { name: 'RTX 3090', vram: '24GB', priceRange: '$0.30-0.50/h' },
  { name: 'RTX 3090 Ti', vram: '24GB', priceRange: '$0.35-0.55/h' },
  { name: 'RTX 4070', vram: '12GB', priceRange: '$0.25-0.40/h' },
  { name: 'RTX 4070 Ti', vram: '12GB', priceRange: '$0.30-0.45/h' },
  { name: 'RTX 4080', vram: '16GB', priceRange: '$0.40-0.60/h' },
  { name: 'RTX 4090', vram: '24GB', priceRange: '$0.55-0.85/h' },
  { name: 'RTX 5070', vram: '12GB', priceRange: '$0.35-0.50/h' },
  { name: 'RTX 5080', vram: '16GB', priceRange: '$0.50-0.70/h' },
  { name: 'RTX 5090', vram: '32GB', priceRange: '$0.70-1.00/h' },
  { name: 'GTX 1080 Ti', vram: '11GB', priceRange: '$0.08-0.15/h' },
  { name: 'A10', vram: '24GB', priceRange: '$0.35-0.55/h' },
  { name: 'A40', vram: '48GB', priceRange: '$0.50-0.80/h' },
  { name: 'A100 40GB', vram: '40GB', priceRange: '$0.80-1.20/h' },
  { name: 'A100 80GB', vram: '80GB', priceRange: '$1.20-2.00/h' },
  { name: 'H100 80GB', vram: '80GB', priceRange: '$2.00-3.50/h' },
  { name: 'L40', vram: '48GB', priceRange: '$0.70-1.00/h' },
  { name: 'L40S', vram: '48GB', priceRange: '$0.80-1.20/h' },
  { name: 'V100', vram: '16GB', priceRange: '$0.40-0.70/h' },
  { name: 'V100 32GB', vram: '32GB', priceRange: '$0.50-0.80/h' },
  { name: 'T4', vram: '16GB', priceRange: '$0.20-0.35/h' },
] as const;

/**
 * Filter GPUs by search query
 */
export function filterGPUs(query: string): GPUOption[] {
  if (!query.trim()) return [...GPU_OPTIONS];

  const lowerQuery = query.toLowerCase();
  return GPU_OPTIONS.filter(
    gpu =>
      gpu.name.toLowerCase().includes(lowerQuery) ||
      gpu.vram.toLowerCase().includes(lowerQuery)
  );
}

/**
 * Get GPU by name
 */
export function getGPUByName(name: string): GPUOption | undefined {
  return GPU_OPTIONS.find(g => g.name === name);
}

/**
 * GPU categories for grouping
 */
export const GPU_CATEGORIES = {
  consumer: ['RTX 3060', 'RTX 3070', 'RTX 3080', 'RTX 3090', 'RTX 4070', 'RTX 4080', 'RTX 4090', 'RTX 5070', 'RTX 5080', 'RTX 5090'],
  datacenter: ['A10', 'A40', 'A100 40GB', 'A100 80GB', 'H100 80GB', 'L40', 'L40S', 'V100', 'V100 32GB', 'T4'],
  legacy: ['GTX 1080 Ti'],
} as const;

/**
 * Check if GPU is datacenter class
 */
export function isDatacenterGPU(gpuName: string): boolean {
  return GPU_CATEGORIES.datacenter.some(name => gpuName.includes(name));
}

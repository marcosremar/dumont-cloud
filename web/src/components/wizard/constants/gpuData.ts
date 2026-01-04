/**
 * GPU Data Constants
 * Complete list of available GPUs with specifications
 */

import type { GPUInfo } from '../types/wizard.types';

export const GPU_LIST: GPUInfo[] = [
  // RTX 30 Series
  { name: 'RTX 3060', vram: '12GB', priceRange: '$0.10-0.20/h' },
  { name: 'RTX 3070', vram: '8GB', priceRange: '$0.15-0.25/h' },
  { name: 'RTX 3080', vram: '10GB', priceRange: '$0.20-0.35/h' },
  { name: 'RTX 3090', vram: '24GB', priceRange: '$0.30-0.50/h' },

  // RTX 40 Series
  { name: 'RTX 4070', vram: '12GB', priceRange: '$0.25-0.40/h' },
  { name: 'RTX 4080', vram: '16GB', priceRange: '$0.40-0.60/h' },
  { name: 'RTX 4090', vram: '24GB', priceRange: '$0.55-0.85/h' },

  // RTX 50 Series
  { name: 'RTX 5070', vram: '12GB', priceRange: '$0.35-0.55/h' },
  { name: 'RTX 5080', vram: '16GB', priceRange: '$0.50-0.75/h' },
  { name: 'RTX 5090', vram: '32GB', priceRange: '$0.80-1.20/h' },

  // Legacy
  { name: 'GTX 1080 Ti', vram: '11GB', priceRange: '$0.08-0.15/h' },

  // Data Center GPUs
  { name: 'A100 40GB', vram: '40GB', priceRange: '$0.80-1.20/h' },
  { name: 'A100 80GB', vram: '80GB', priceRange: '$1.20-2.00/h' },
  { name: 'H100 80GB', vram: '80GB', priceRange: '$2.00-3.50/h' },
  { name: 'A10', vram: '24GB', priceRange: '$0.35-0.55/h' },
  { name: 'A40', vram: '48GB', priceRange: '$0.50-0.80/h' },
  { name: 'L40', vram: '48GB', priceRange: '$0.70-1.00/h' },
  { name: 'V100', vram: '16GB', priceRange: '$0.40-0.70/h' },
  { name: 'T4', vram: '16GB', priceRange: '$0.20-0.35/h' },
];

/**
 * Filter GPUs by search query
 */
export function filterGPUs(query: string): GPUInfo[] {
  if (!query) return GPU_LIST;

  const lowerQuery = query.toLowerCase();
  return GPU_LIST.filter(
    (gpu) =>
      gpu.name.toLowerCase().includes(lowerQuery) ||
      gpu.vram.toLowerCase().includes(lowerQuery)
  );
}

/**
 * GPU Categories for filtering
 */
export const GPU_CATEGORIES = {
  consumer: ['RTX 3060', 'RTX 3070', 'RTX 3080', 'RTX 3090', 'RTX 4070', 'RTX 4080', 'RTX 4090', 'RTX 5070', 'RTX 5080', 'RTX 5090', 'GTX 1080 Ti'],
  datacenter: ['A100 40GB', 'A100 80GB', 'H100 80GB', 'A10', 'A40', 'L40', 'V100', 'T4'],
  budget: ['RTX 3060', 'RTX 3070', 'GTX 1080 Ti', 'T4'],
  highEnd: ['RTX 4090', 'RTX 5090', 'A100 80GB', 'H100 80GB'],
} as const;

export default GPU_LIST;

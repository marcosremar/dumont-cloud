/**
 * Wizard Constants - Re-exports
 */

// Tiers
export {
  PERFORMANCE_TIERS,
  TIER_NAMES,
  getTierByName,
  getTierFilterParams,
  getEstimatedCostFromTier,
} from './tiers';

// Failover Strategies
export {
  FAILOVER_STRATEGIES,
  STRATEGY_IDS,
  getStrategyById,
  getDefaultStrategy,
  getAvailableStrategies,
} from './failoverStrategies';

// Regions
export {
  REGIONS,
  REGION_KEYS,
  COUNTRY_NAMES,
  getRegionByKey,
  getCountryName,
  createLocationFromCountry,
  createLocationFromRegion,
  isCountryInRegion,
  getRegionForCountry,
} from './regions';

// GPUs
export {
  GPU_OPTIONS,
  GPU_CATEGORIES,
  filterGPUs,
  getGPUByName,
  isDatacenterGPU,
} from './gpus';

/**
 * Default values
 */
export const WIZARD_DEFAULTS = {
  dockerImage: 'pytorch/pytorch:latest',
  exposedPorts: [
    { port: '22', protocol: 'TCP' as const },
    { port: '8888', protocol: 'TCP' as const },
    { port: '6006', protocol: 'TCP' as const },
  ],
  maxRounds: 3,
  minBalance: 0.10,
  offersLimit: 5,
} as const;

/**
 * Wizard steps configuration
 */
export const WIZARD_STEPS = [
  { id: 1 as const, name: 'Região', description: 'Localização' },
  { id: 2 as const, name: 'Hardware', description: 'GPU e performance' },
  { id: 3 as const, name: 'Estratégia', description: 'Failover' },
  { id: 4 as const, name: 'Provisionar', description: 'Conectando' },
] as const;

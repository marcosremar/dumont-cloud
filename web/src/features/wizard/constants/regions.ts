/**
 * Regions and Countries Constants
 * Geographic data for location selection
 */

import { Region, Location, RegionKey } from '../types';

/**
 * Available regions with country codes
 */
export const REGIONS: Record<string, Region> = {
  eua: {
    name: 'EUA',
    codes: ['US', 'CA', 'MX'],
    isRegion: true,
  },
  europa: {
    name: 'Europa',
    codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'PL'],
    isRegion: true,
  },
  asia: {
    name: 'Ásia',
    codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TW', 'HK'],
    isRegion: true,
  },
  'america-do-sul': {
    name: 'América do Sul',
    codes: ['BR', 'AR', 'CL', 'CO', 'PE'],
    isRegion: true,
  },
} as const;

/**
 * Country code to localized name mapping
 */
export const COUNTRY_NAMES: Record<string, string> = {
  US: 'Estados Unidos',
  CA: 'Canadá',
  MX: 'México',
  GB: 'Reino Unido',
  FR: 'França',
  DE: 'Alemanha',
  ES: 'Espanha',
  IT: 'Itália',
  PT: 'Portugal',
  NL: 'Holanda',
  BE: 'Bélgica',
  CH: 'Suíça',
  AT: 'Áustria',
  PL: 'Polônia',
  JP: 'Japão',
  CN: 'China',
  KR: 'Coreia do Sul',
  SG: 'Singapura',
  IN: 'Índia',
  TW: 'Taiwan',
  HK: 'Hong Kong',
  BR: 'Brasil',
  AR: 'Argentina',
  CL: 'Chile',
  CO: 'Colômbia',
  PE: 'Peru',
} as const;

/**
 * Region keys for iteration
 */
export const REGION_KEYS: readonly string[] = ['eua', 'europa', 'asia', 'america-do-sul'] as const;

/**
 * Get region by key (normalized)
 */
export function getRegionByKey(key: string): Region | undefined {
  const normalizedKey = key.toLowerCase().replace(' ', '-');
  return REGIONS[normalizedKey];
}

/**
 * Get country name by code
 */
export function getCountryName(code: string): string {
  return COUNTRY_NAMES[code] ?? code;
}

/**
 * Create location object from country code
 */
export function createLocationFromCountry(code: string): Location | null {
  const name = COUNTRY_NAMES[code];
  if (!name) return null;

  return {
    codes: [code],
    name,
    isRegion: false,
  };
}

/**
 * Create location object from region key
 */
export function createLocationFromRegion(regionKey: string): Location | null {
  const region = getRegionByKey(regionKey);
  if (!region) return null;

  return {
    codes: region.codes,
    name: region.name,
    isRegion: true,
  };
}

/**
 * Check if a country code belongs to a region
 */
export function isCountryInRegion(countryCode: string, regionKey: string): boolean {
  const region = getRegionByKey(regionKey);
  if (!region) return false;
  return region.codes.includes(countryCode);
}

/**
 * Get region that contains a country
 */
export function getRegionForCountry(countryCode: string): Region | undefined {
  for (const key of REGION_KEYS) {
    const region = REGIONS[key];
    if (region.codes.includes(countryCode)) {
      return region;
    }
  }
  return undefined;
}

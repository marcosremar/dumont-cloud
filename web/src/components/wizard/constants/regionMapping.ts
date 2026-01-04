/**
 * Region Mapping Constants
 * Maps countries to API region codes
 */

import type { SelectedLocation } from '../types/wizard.types';

// Country codes by region
export const US_COUNTRIES = ['US', 'CA', 'MX'];
export const EU_COUNTRIES = [
  'GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT',
  'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'
];
export const ASIA_COUNTRIES = [
  'JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'
];
export const SA_COUNTRIES = [
  'BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'
];

// Region name mappings (multiple languages)
export const REGION_NAME_MAPPING: Record<string, string> = {
  'usa': 'US',
  'eua': 'US',
  'united states': 'US',
  'estados unidos': 'US',
  'europe': 'EU',
  'europa': 'EU',
  'asia': 'ASIA',
  'ásia': 'ASIA',
  'south america': 'SA',
  'américa do sul': 'SA',
  'sudamérica': 'SA',
};

/**
 * Get API region code from country code
 */
export function getRegionFromCountry(countryCode: string): string {
  if (US_COUNTRIES.includes(countryCode)) return 'US';
  if (EU_COUNTRIES.includes(countryCode)) return 'EU';
  if (ASIA_COUNTRIES.includes(countryCode)) return 'ASIA';
  if (SA_COUNTRIES.includes(countryCode)) return 'SA';
  return countryCode; // Return as-is if not mapped
}

/**
 * Convert selected locations to API region codes
 */
export function locationsToRegionCodes(locations: SelectedLocation[]): string[] {
  const regionCodes: string[] = [];

  for (const loc of locations) {
    if (loc?.isRegion) {
      const regionName = loc.name?.toLowerCase();
      const mappedRegion = REGION_NAME_MAPPING[regionName];
      if (mappedRegion && !regionCodes.includes(mappedRegion)) {
        regionCodes.push(mappedRegion);
      }
    } else if (loc?.codes?.[0]) {
      const countryCode = loc.codes[0];
      const region = getRegionFromCountry(countryCode);
      if (!regionCodes.includes(region)) {
        regionCodes.push(region);
      }
    }
  }

  return regionCodes;
}

/**
 * Region data for quick selection
 */
export const QUICK_REGIONS = [
  { key: 'usa', name: 'USA', codes: US_COUNTRIES, isRegion: true },
  { key: 'europe', name: 'Europe', codes: EU_COUNTRIES, isRegion: true },
  { key: 'asia', name: 'Asia', codes: ASIA_COUNTRIES, isRegion: true },
  { key: 'south america', name: 'South America', codes: SA_COUNTRIES, isRegion: true },
];

export default {
  US_COUNTRIES,
  EU_COUNTRIES,
  ASIA_COUNTRIES,
  SA_COUNTRIES,
  locationsToRegionCodes,
  getRegionFromCountry,
};

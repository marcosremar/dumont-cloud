/**
 * Location Step Component
 *
 * Step 1: Select geographic location for GPU instance.
 */

import React from 'react';
import { Search, Globe, MapPin, X } from 'lucide-react';
import { Location } from '../../types';
import { REGION_KEYS, REGIONS, COUNTRY_NAMES } from '../../constants';

// ============================================================================
// Types
// ============================================================================

export interface LocationStepProps {
  selectedLocation: Location | null;
  searchCountry: string;
  onSearchChange: (search: string) => void;
  onRegionSelect: (regionKey: string) => void;
  onCountryClick: (code: string) => void;
  onClearSelection: () => void;
  WorldMapComponent?: React.ComponentType<{
    selectedCodes: string[];
    onCountryClick: (code: string) => void;
  }>;
}

// ============================================================================
// Component
// ============================================================================

export const LocationStep: React.FC<LocationStepProps> = ({
  selectedLocation,
  searchCountry,
  onSearchChange,
  onRegionSelect,
  onCountryClick,
  onClearSelection,
  WorldMapComponent,
}) => {
  return (
    <div className="space-y-5 animate-fadeIn">
      <div className="space-y-4">
        <div className="flex flex-col gap-3">
          {/* Search Input */}
          <div className="relative">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
              <Search className="w-4 h-4 text-gray-500" />
            </div>
            <input
              type="text"
              placeholder="Buscar país ou região (ex: Brasil, Europa, Japão...)"
              className="w-full pl-11 pr-4 py-3 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-white/20 focus:border-white/20 placeholder:text-gray-500 transition-all"
              value={searchCountry}
              onChange={(e) => onSearchChange(e.target.value)}
              data-testid="location-search-input"
            />
          </div>

          {/* Selected Location Badge */}
          {selectedLocation && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">
                {selectedLocation.isRegion ? 'Região:' : 'País:'}
              </span>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 text-gray-200 rounded-full text-sm font-medium">
                {selectedLocation.isRegion ? (
                  <Globe className="w-3.5 h-3.5" />
                ) : (
                  <MapPin className="w-3.5 h-3.5" />
                )}
                <span>{selectedLocation.name}</span>
                <button
                  onClick={onClearSelection}
                  className="ml-1 p-0.5 rounded-full hover:bg-white/10 transition-colors"
                  data-testid="clear-location-button"
                  aria-label="Limpar seleção"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Region Quick Select */}
          {!selectedLocation && (
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-gray-500 mr-1 self-center">Regiões:</span>
              {REGION_KEYS.map((regionKey) => {
                const region = REGIONS[regionKey];
                return (
                  <button
                    key={regionKey}
                    data-testid={`region-${regionKey}`}
                    onClick={() => onRegionSelect(regionKey)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10 hover:border-white/20 hover:text-gray-200 transition-all cursor-pointer"
                  >
                    <Globe className="w-3 h-3" />
                    {region.name}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* World Map */}
        <div className="h-64 rounded-lg overflow-hidden border border-white/10 bg-dark-surface-card relative">
          {WorldMapComponent ? (
            <WorldMapComponent
              selectedCodes={selectedLocation?.codes ?? []}
              onCountryClick={(code) => {
                if (COUNTRY_NAMES[code]) {
                  onCountryClick(code);
                }
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 text-sm">
              Mapa não disponível
            </div>
          )}
          <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-[#0a0d0a] via-transparent to-transparent opacity-60" />
        </div>
      </div>
    </div>
  );
};

export default LocationStep;

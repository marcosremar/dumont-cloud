/**
 * LocationStep Component
 * Step 1: Region/Location selection
 */

import React from 'react';
import {
  Search,
  Globe,
  MapPin,
  X,
  Check,
  AlertCircle,
} from 'lucide-react';
import { useWizard } from '../WizardContext';
import { WorldMap } from '../../dashboard';
import { COUNTRY_DATA } from '../../dashboard/constants';
import { QUICK_REGIONS } from '../constants/regionMapping';

export function LocationStep() {
  const { state, dispatch } = useWizard();
  const { selectedLocations, searchCountry } = state;

  // Handle country/region selection
  const handleLocationSelect = (locationData: any) => {
    const exists = selectedLocations.some((loc) => loc.name === locationData.name);
    if (exists) {
      dispatch({ type: 'REMOVE_LOCATION', payload: locationData.name });
    } else {
      dispatch({ type: 'ADD_LOCATION', payload: locationData });
    }
  };

  // Handle region quick select
  const handleRegionSelect = (region: typeof QUICK_REGIONS[number]) => {
    const exists = selectedLocations.some((loc) => loc.name === region.name);
    if (exists) {
      dispatch({ type: 'REMOVE_LOCATION', payload: region.name });
    } else {
      dispatch({
        type: 'ADD_LOCATION',
        payload: { name: region.name, codes: region.codes, isRegion: true },
      });
    }
  };

  // Handle search change
  const handleSearchChange = (value: string) => {
    dispatch({ type: 'SET_SEARCH_COUNTRY', payload: value });
  };

  // Handle clear all
  const handleClearAll = () => {
    dispatch({ type: 'CLEAR_LOCATIONS' });
  };

  // Get autocomplete matches
  const getSearchMatches = () => {
    if (!searchCountry || searchCountry.length < 2) return [];

    const query = searchCountry.toLowerCase().trim();
    return Object.entries(COUNTRY_DATA)
      .filter(([key, data]) =>
        key.includes(query) || (data as any).name.toLowerCase().includes(query)
      )
      .slice(0, 10)
      .reduce((acc: any[], [, data]) => {
        if (!acc.some((item) => item.name === (data as any).name)) {
          acc.push(data);
        }
        return acc;
      }, []);
  };

  const searchMatches = getSearchMatches();

  return (
    <div className="space-y-5 animate-fadeIn">
      <div className="space-y-4">
        <div className="flex flex-col gap-3">
          {/* Search with Autocomplete */}
          <div className="relative">
            <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
              <Search className="w-4 h-4 text-gray-500" />
            </div>
            <input
              type="text"
              placeholder="Type country or region (e.g., Brazil, Europe, Japan...)"
              className="w-full pl-11 pr-4 py-3 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/30 placeholder:text-gray-500 transition-all"
              value={searchCountry}
              onChange={(e) => handleSearchChange(e.target.value)}
            />

            {/* Autocomplete Dropdown */}
            {searchCountry && searchCountry.length >= 2 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-dark-surface-card border border-white/10 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto">
                {searchMatches.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-gray-500 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    No countries found for "{searchCountry}"
                  </div>
                ) : (
                  searchMatches.map((data: any, idx: number) => {
                    const isAlreadySelected = selectedLocations.some(
                      (loc) => loc.name === data.name
                    );
                    return (
                      <button
                        key={data.name + idx}
                        onClick={() => !isAlreadySelected && handleLocationSelect(data)}
                        disabled={isAlreadySelected}
                        className={`w-full px-4 py-2.5 text-left flex items-center gap-3 transition-all ${
                          isAlreadySelected
                            ? 'bg-brand-500/10 text-brand-400 cursor-default'
                            : 'hover:bg-white/5 text-gray-300'
                        }`}
                      >
                        {data.isRegion ? (
                          <Globe className="w-4 h-4 text-brand-400 flex-shrink-0" />
                        ) : (
                          <MapPin className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{data.name}</div>
                          <div className="text-[10px] text-gray-500">
                            {data.isRegion
                              ? `Region • ${data.codes.length} countries`
                              : `Country • ${data.codes[0]}`}
                          </div>
                        </div>
                        {isAlreadySelected && (
                          <Check className="w-4 h-4 text-brand-400 flex-shrink-0" />
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {/* Quick Region Buttons */}
          <div className="flex flex-wrap gap-2">
            {QUICK_REGIONS.map((region) => {
              const isSelected = selectedLocations.some(
                (loc) => loc.name === region.name
              );
              return (
                <button
                  key={region.key}
                  onClick={() => handleRegionSelect(region)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    isSelected
                      ? 'bg-brand-500 text-white'
                      : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-300'
                  }`}
                >
                  <Globe className="w-3 h-3 inline mr-1.5" />
                  {region.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* World Map */}
        <div className="rounded-lg overflow-hidden border border-white/10 bg-white/[0.02]">
          <WorldMap
            selectedCountries={selectedLocations.flatMap((loc) => loc.codes)}
            onCountryClick={handleLocationSelect}
            searchQuery={searchCountry}
          />
        </div>

        {/* Selected Locations */}
        {selectedLocations.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">
                {selectedLocations.length} location(s) selected
              </span>
              <button
                onClick={handleClearAll}
                className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
              >
                <X className="w-3 h-3" />
                Clear all
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedLocations.map((loc, idx) => (
                <div
                  key={loc.name + idx}
                  className="inline-flex items-center gap-2 px-3 py-1.5 bg-brand-500/10 border border-brand-500/30 text-brand-400 rounded-full text-xs"
                >
                  {loc.isRegion ? (
                    <Globe className="w-3 h-3" />
                  ) : (
                    <MapPin className="w-3 h-3" />
                  )}
                  <span>{loc.name}</span>
                  <button
                    onClick={() =>
                      dispatch({ type: 'REMOVE_LOCATION', payload: loc.name })
                    }
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default LocationStep;

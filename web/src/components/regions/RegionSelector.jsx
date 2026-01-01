import React, { useState, useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Globe, MapPin, Shield, ChevronDown, Loader2 } from 'lucide-react';
import { VectorMap } from '@react-jvectormap/core';
import { worldMill } from '@react-jvectormap/world';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Label,
  Badge,
} from '../tailadmin-ui';
import { useTheme } from '../../context/ThemeContext';
import {
  fetchRegions,
  setSelectedRegion,
  selectRegions,
  selectSelectedRegion,
  selectRegionsLoading,
  selectEuRegions,
} from '../../store/slices/regionsSlice';

// Map country codes to jVectorMap region codes
const COUNTRY_TO_JVECTOR = {
  'US': 'US',
  'CA': 'CA',
  'MX': 'MX',
  'BR': 'BR',
  'AR': 'AR',
  'CL': 'CL',
  'CO': 'CO',
  'GB': 'GB',
  'FR': 'FR',
  'DE': 'DE',
  'ES': 'ES',
  'IT': 'IT',
  'PT': 'PT',
  'NL': 'NL',
  'BE': 'BE',
  'CH': 'CH',
  'AT': 'AT',
  'IE': 'IE',
  'SE': 'SE',
  'NO': 'NO',
  'DK': 'DK',
  'FI': 'FI',
  'PL': 'PL',
  'CZ': 'CZ',
  'GR': 'GR',
  'HU': 'HU',
  'RO': 'RO',
  'JP': 'JP',
  'CN': 'CN',
  'KR': 'KR',
  'SG': 'SG',
  'IN': 'IN',
  'TH': 'TH',
  'VN': 'VN',
  'ID': 'ID',
  'MY': 'MY',
  'PH': 'PH',
  'TW': 'TW',
  'AU': 'AU',
  'NZ': 'NZ',
};

// Region categories for filtering
const REGION_CATEGORIES = [
  {
    id: 'any',
    name: 'Todas',
    icon: 'globe',
    description: 'Qualquer localidade',
    countries: [],
  },
  {
    id: 'na',
    name: 'Americas',
    icon: 'map',
    description: 'EUA, Canada, Brasil',
    countries: ['US', 'CA', 'MX', 'BR', 'AR', 'CL', 'CO'],
  },
  {
    id: 'eu',
    name: 'Europa',
    icon: 'shield',
    description: 'GDPR Compliant',
    countries: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'],
  },
  {
    id: 'apac',
    name: 'APAC',
    icon: 'map',
    description: 'Asia-Pacific',
    countries: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW', 'AU', 'NZ'],
  },
];

const RegionSelector = ({ selectedRegion, onSelectRegion, showMap = true, compact = false }) => {
  const dispatch = useDispatch();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Redux state
  const regions = useSelector(selectRegions);
  const reduxSelectedRegion = useSelector(selectSelectedRegion);
  const loading = useSelector(selectRegionsLoading);
  const euRegions = useSelector(selectEuRegions);

  // Local state
  const [selectedCategory, setSelectedCategory] = useState('any');
  const [isExpanded, setIsExpanded] = useState(false);
  const [hoveredCountry, setHoveredCountry] = useState(null);

  // Use props or redux state
  const currentSelection = selectedRegion !== undefined ? selectedRegion : reduxSelectedRegion;
  const handleSelect = onSelectRegion || ((region) => dispatch(setSelectedRegion(region)));

  // Fetch regions on mount
  useEffect(() => {
    if (regions.length === 0 && !loading) {
      dispatch(fetchRegions());
    }
  }, [dispatch, regions.length, loading]);

  // Map theme colors
  const mapColors = useMemo(() => ({
    dark: {
      background: 'transparent',
      landFill: 'rgb(31, 41, 55)',
      landStroke: 'rgb(55, 65, 81)',
      hoverFill: 'rgb(46, 125, 50)',
      hoverStroke: 'rgb(76, 175, 80)',
      selectedFill: 'rgb(46, 125, 50)',
      markerFill: 'rgb(76, 175, 80)',
      markerStroke: 'rgb(129, 199, 132)',
    },
    light: {
      background: 'transparent',
      landFill: 'rgb(229, 231, 235)',
      landStroke: 'rgb(209, 213, 219)',
      hoverFill: 'rgb(46, 125, 50)',
      hoverStroke: 'rgb(76, 175, 80)',
      selectedFill: 'rgb(46, 125, 50)',
      markerFill: 'rgb(46, 125, 50)',
      markerStroke: 'rgb(76, 175, 80)',
    },
  }), []);

  const colors = isDark ? mapColors.dark : mapColors.light;

  // Get active countries for category
  const activeCountries = useMemo(() => {
    const category = REGION_CATEGORIES.find(c => c.id === selectedCategory);
    if (!category || category.id === 'any') {
      // For 'any', return countries that have regions available
      return regions.map(r => r.country_code).filter(Boolean);
    }
    return category.countries;
  }, [selectedCategory, regions]);

  // Filter regions by category
  const filteredRegions = useMemo(() => {
    if (selectedCategory === 'any') {
      return regions;
    }
    const category = REGION_CATEGORIES.find(c => c.id === selectedCategory);
    if (!category) return regions;
    return regions.filter(r => category.countries.includes(r.country_code));
  }, [selectedCategory, regions]);

  // Get selected region data
  const selectedRegionData = useMemo(() => {
    if (!currentSelection) return null;
    return regions.find(r => r.id === currentSelection || r.region_id === currentSelection);
  }, [currentSelection, regions]);

  // Map markers for available datacenters
  const markers = useMemo(() => {
    return regions
      .filter(r => r.lat && r.lon)
      .map(r => ({
        latLng: [r.lat, r.lon],
        name: r.name || r.region_name || r.region_id,
        regionId: r.id || r.region_id,
        isEu: r.is_eu,
      }));
  }, [regions]);

  // Handle country click on map
  const handleCountryClick = (e, countryCode) => {
    // Find a region in this country
    const region = regions.find(r => r.country_code === countryCode);
    if (region) {
      handleSelect(region.id || region.region_id);
    }
  };

  // Handle marker click
  const handleMarkerClick = (e, markerIndex) => {
    const marker = markers[markerIndex];
    if (marker) {
      handleSelect(marker.regionId);
    }
  };

  // Get category icon
  const getCategoryIcon = (iconType, isActive) => {
    const colorClass = isActive ? 'text-white' : 'text-gray-700 dark:text-gray-300';
    switch (iconType) {
      case 'globe':
        return <Globe className={`w-4 h-4 ${colorClass}`} />;
      case 'shield':
        return <Shield className={`w-4 h-4 ${colorClass}`} />;
      case 'map':
      default:
        return <MapPin className={`w-4 h-4 ${colorClass}`} />;
    }
  };

  // Build region values for series (highlight available countries)
  const regionValues = useMemo(() => {
    const values = {};
    activeCountries.forEach(code => {
      if (COUNTRY_TO_JVECTOR[code]) {
        values[COUNTRY_TO_JVECTOR[code]] = 1;
      }
    });
    // Highlight selected country more
    if (selectedRegionData?.country_code && COUNTRY_TO_JVECTOR[selectedRegionData.country_code]) {
      values[COUNTRY_TO_JVECTOR[selectedRegionData.country_code]] = 2;
    }
    return values;
  }, [activeCountries, selectedRegionData]);

  if (loading && regions.length === 0) {
    return (
      <Card className="overflow-hidden">
        <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center">
              <Globe className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <CardTitle className="text-sm">Regiao</CardTitle>
              <CardDescription className="text-[10px]">Carregando...</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center">
            <Globe className="w-4 h-4 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <CardTitle className="text-sm">Regiao</CardTitle>
            <CardDescription className="text-[10px]">Selecione a localidade</CardDescription>
          </div>
        </div>
        {selectedRegionData && (
          <div className="flex items-center gap-1.5">
            {selectedRegionData.is_eu && (
              <span className="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 text-[10px] font-medium flex items-center gap-1">
                <Shield className="w-3 h-3" />
                GDPR
              </span>
            )}
            <span className="px-2 py-1 rounded-full bg-brand-100 dark:bg-brand-500/20 text-brand-600 dark:text-brand-400 text-[10px] font-medium">
              {selectedRegionData.name || selectedRegionData.region_name || selectedRegionData.region_id}
            </span>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-3">
        {/* Category Grid */}
        <div className="grid grid-cols-2 gap-2">
          {REGION_CATEGORIES.map((cat) => {
            const isActive = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => {
                  setSelectedCategory(cat.id);
                  if (cat.id === 'any') {
                    handleSelect(null);
                    setIsExpanded(false);
                  } else {
                    setIsExpanded(true);
                  }
                }}
                className={`relative p-3 rounded-lg border transition-all text-left overflow-hidden ${
                  isActive
                    ? 'border-brand-500/50 bg-brand-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                }`}
              >
                {/* Left accent when active */}
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-brand-500" />
                )}
                <div className="flex items-center gap-2.5 mb-1.5">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${isActive ? 'bg-brand-500/20' : 'bg-white/10'}`}>
                    {getCategoryIcon(cat.icon, isActive)}
                  </div>
                  <span className={`text-sm font-bold ${isActive ? 'text-white' : 'text-gray-100'}`}>
                    {cat.name}
                  </span>
                </div>
                <p className={`text-[10px] pl-9 ${isActive ? 'text-brand-300' : 'text-gray-400'}`}>
                  {cat.description}
                </p>
              </button>
            );
          })}
        </div>

        {/* Map Visualization */}
        {showMap && !compact && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50">
            <div className={`relative w-full h-48 rounded-lg overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
              <VectorMap
                key={`map-${theme}-${selectedCategory}`}
                map={worldMill}
                backgroundColor="transparent"
                containerStyle={{
                  width: '100%',
                  height: '100%',
                }}
                markerStyle={{
                  initial: {
                    fill: colors.markerFill,
                    r: 5,
                    stroke: colors.markerStroke,
                    strokeWidth: 2,
                    fillOpacity: 0.9,
                  },
                  hover: {
                    fill: colors.hoverFill,
                    r: 7,
                    stroke: colors.hoverStroke,
                    strokeWidth: 2,
                    fillOpacity: 1,
                    cursor: 'pointer',
                  },
                }}
                markers={markers.map((m, idx) => ({
                  latLng: m.latLng,
                  name: m.name,
                  style: {
                    fill: m.regionId === currentSelection ? colors.selectedFill : colors.markerFill,
                    stroke: colors.markerStroke,
                    strokeWidth: 2,
                    fillOpacity: m.regionId === currentSelection ? 1 : 0.7,
                    r: m.regionId === currentSelection ? 7 : 5,
                  },
                }))}
                onMarkerClick={handleMarkerClick}
                zoomOnScroll={false}
                zoomMax={12}
                zoomMin={1}
                onRegionClick={handleCountryClick}
                onRegionTipShow={(e, label, code) => {
                  // Find region info for this country
                  const region = regions.find(r => r.country_code === code);
                  if (region) {
                    label.html(`
                      <div class="p-2 bg-gray-900 rounded-lg shadow-lg border border-gray-700">
                        <div class="font-semibold text-white">${region.name || region.region_name || code}</div>
                        ${region.is_eu ? '<div class="text-xs text-blue-400 mt-1">GDPR Compliant</div>' : ''}
                        ${region.avg_price ? `<div class="text-xs text-gray-400 mt-1">~$${region.avg_price.toFixed(2)}/hr</div>` : ''}
                      </div>
                    `);
                  }
                }}
                regionStyle={{
                  initial: {
                    fill: colors.landFill,
                    fillOpacity: 1,
                    stroke: colors.landStroke,
                    strokeWidth: 0.5,
                    strokeOpacity: 1,
                  },
                  hover: {
                    fillOpacity: 0.9,
                    cursor: 'pointer',
                    fill: colors.hoverFill,
                    stroke: colors.hoverStroke,
                    strokeWidth: 1,
                  },
                }}
                series={{
                  regions: [{
                    values: regionValues,
                    scale: {
                      '1': 'rgba(76, 175, 80, 0.3)',
                      '2': 'rgba(46, 125, 50, 0.7)',
                    },
                    attribute: 'fill',
                  }],
                }}
              />
            </div>
          </div>
        )}

        {/* Region Dropdown - appears when specific category is selected */}
        {isExpanded && selectedCategory !== 'any' && filteredRegions.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50">
            <Label className="text-[10px] text-gray-500 dark:text-gray-400 mb-2 block">
              Localidade Especifica (opcional)
            </Label>
            <Select value={currentSelection || 'any'} onValueChange={(val) => handleSelect(val === 'any' ? null : val)}>
              <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-gray-800 h-9 text-xs">
                <SelectValue placeholder="Qualquer localidade na regiao" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Qualquer {REGION_CATEGORIES.find(c => c.id === selectedCategory)?.name}</SelectItem>
                {filteredRegions.map(region => (
                  <SelectItem key={region.id || region.region_id} value={region.id || region.region_id}>
                    <div className="flex items-center gap-2">
                      <span>{region.name || region.region_name || region.region_id}</span>
                      {region.is_eu && (
                        <Shield className="w-3 h-3 text-blue-500" />
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Fallback when no regions available */}
        {regions.length === 0 && !loading && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50">
            <p className="text-xs text-gray-500 text-center py-4">
              Nenhuma regiao disponivel no momento
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RegionSelector;

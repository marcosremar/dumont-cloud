/**
 * GPU Filters Component
 *
 * Advanced filters for GPU selection: VRAM, price, provider, etc.
 * Enhanced with prominent visibility and preset filters.
 */

import React, { useState, useMemo } from 'react';
import {
  SlidersHorizontal,
  X,
  MemoryStick,
  DollarSign,
  Globe,
  Shield,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Check,
  Zap,
  Sparkles,
  Wallet,
  TrendingUp,
  Filter,
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

export interface GPUFilterState {
  minVram: number;
  maxVram: number;
  minPrice: number;
  maxPrice: number;
  providers: string[];
  minReliability: number;
  regions: string[];
  gpuCount: number | null;
  verified: boolean | null;
}

export interface GPUFiltersProps {
  filters: GPUFilterState;
  onFiltersChange: (filters: GPUFilterState) => void;
  availableProviders?: string[];
  availableRegions?: string[];
  resultCount?: number;
  className?: string;
}

// ============================================================================
// Default Values
// ============================================================================

export const DEFAULT_GPU_FILTERS: GPUFilterState = {
  minVram: 0,
  maxVram: 80,
  minPrice: 0,
  maxPrice: 5,
  providers: [],
  minReliability: 0,
  regions: [],
  gpuCount: null,
  verified: null,
};

const VRAM_OPTIONS = [0, 8, 12, 16, 24, 40, 48, 80];
const PRICE_OPTIONS = [0.05, 0.10, 0.25, 0.50, 1.00, 2.00, 5.00];
const RELIABILITY_OPTIONS = [0, 80, 90, 95, 99];
const GPU_COUNT_OPTIONS = [1, 2, 4, 8];

const DEFAULT_PROVIDERS = ['VAST.ai', 'TensorDock', 'RunPod', 'Lambda'];
const DEFAULT_REGIONS = ['US', 'EU', 'ASIA', 'SA'];

// ============================================================================
// Filter Presets
// ============================================================================

export interface FilterPreset {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  filters: Partial<GPUFilterState>;
  color: string;
}

export const FILTER_PRESETS: FilterPreset[] = [
  {
    id: 'budget',
    name: 'Econômico',
    description: 'Máquinas baratas para testes',
    icon: Wallet,
    color: 'emerald',
    filters: {
      maxPrice: 0.15,
      minVram: 0,
      maxVram: 16,
    },
  },
  {
    id: 'balanced',
    name: 'Equilibrado',
    description: 'Melhor custo-benefício',
    icon: TrendingUp,
    color: 'brand',
    filters: {
      minPrice: 0.10,
      maxPrice: 0.50,
      minVram: 12,
      maxVram: 48,
      minReliability: 90,
    },
  },
  {
    id: 'performance',
    name: 'Alta Performance',
    description: 'GPUs premium para produção',
    icon: Zap,
    color: 'amber',
    filters: {
      minVram: 24,
      minReliability: 95,
    },
  },
  {
    id: 'datacenter',
    name: 'Datacenter',
    description: 'A100, H100 para LLMs',
    icon: Sparkles,
    color: 'purple',
    filters: {
      minVram: 40,
      minReliability: 95,
    },
  },
];

// ============================================================================
// Sub-components
// ============================================================================

interface FilterSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  isOpen?: boolean;
  onToggle?: () => void;
}

const FilterSection: React.FC<FilterSectionProps> = ({
  title,
  icon,
  children,
  isOpen = true,
  onToggle,
}) => (
  <div className="border-b border-white/10 last:border-b-0">
    {onToggle ? (
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-gray-400">{icon}</span>
          <span className="text-xs font-medium text-gray-300">{title}</span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>
    ) : (
      <div className="flex items-center gap-2 py-3">
        <span className="text-gray-400">{icon}</span>
        <span className="text-xs font-medium text-gray-300">{title}</span>
      </div>
    )}
    {isOpen && <div className="pb-3">{children}</div>}
  </div>
);

interface RangeSliderProps {
  min: number;
  max: number;
  value: [number, number];
  onChange: (value: [number, number]) => void;
  step?: number;
  formatValue?: (value: number) => string;
  options?: number[];
}

const RangeSlider: React.FC<RangeSliderProps> = ({
  min,
  max,
  value,
  onChange,
  formatValue = (v) => v.toString(),
  options,
}) => {
  const displayOptions = options || [min, max];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">Min: {formatValue(value[0])}</span>
        <span className="text-gray-400">Max: {formatValue(value[1])}</span>
      </div>
      <div className="flex gap-2">
        <select
          value={value[0]}
          onChange={(e) => onChange([Number(e.target.value), value[1]])}
          className="flex-1 px-2 py-1.5 text-xs text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50"
        >
          {displayOptions
            .filter((v) => v <= value[1])
            .map((v) => (
              <option key={v} value={v}>
                {formatValue(v)}
              </option>
            ))}
        </select>
        <span className="text-gray-500 self-center">-</span>
        <select
          value={value[1]}
          onChange={(e) => onChange([value[0], Number(e.target.value)])}
          className="flex-1 px-2 py-1.5 text-xs text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50"
        >
          {displayOptions
            .filter((v) => v >= value[0])
            .map((v) => (
              <option key={v} value={v}>
                {formatValue(v)}
              </option>
            ))}
        </select>
      </div>
    </div>
  );
};

interface ChipSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  allowMultiple?: boolean;
}

const ChipSelect: React.FC<ChipSelectProps> = ({
  options,
  selected,
  onChange,
  allowMultiple = true,
}) => {
  const handleToggle = (option: string) => {
    if (allowMultiple) {
      if (selected.includes(option)) {
        onChange(selected.filter((s) => s !== option));
      } else {
        onChange([...selected, option]);
      }
    } else {
      onChange(selected.includes(option) ? [] : [option]);
    }
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const isSelected = selected.includes(option);
        return (
          <button
            key={option}
            onClick={() => handleToggle(option)}
            className={`px-2.5 py-1 text-xs rounded-md border transition-all ${
              isSelected
                ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-gray-300'
            }`}
          >
            {isSelected && <Check className="w-3 h-3 inline-block mr-1" />}
            {option}
          </button>
        );
      })}
    </div>
  );
};

// ============================================================================
// Preset Button Component
// ============================================================================

interface PresetButtonProps {
  preset: FilterPreset;
  isActive: boolean;
  onClick: () => void;
}

const PresetButton: React.FC<PresetButtonProps> = ({ preset, isActive, onClick }) => {
  const Icon = preset.icon;
  const colorClasses = {
    emerald: {
      active: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400',
      inactive: 'hover:bg-emerald-500/10 hover:border-emerald-500/30',
    },
    brand: {
      active: 'bg-brand-500/20 border-brand-500/50 text-brand-400',
      inactive: 'hover:bg-brand-500/10 hover:border-brand-500/30',
    },
    amber: {
      active: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
      inactive: 'hover:bg-amber-500/10 hover:border-amber-500/30',
    },
    purple: {
      active: 'bg-purple-500/20 border-purple-500/50 text-purple-400',
      inactive: 'hover:bg-purple-500/10 hover:border-purple-500/30',
    },
  };

  const colors = colorClasses[preset.color as keyof typeof colorClasses] || colorClasses.brand;

  return (
    <button
      onClick={onClick}
      data-testid={`filter-preset-${preset.id}`}
      className={`flex-1 min-w-[100px] p-2 rounded-lg border transition-all ${
        isActive
          ? colors.active
          : `bg-white/5 border-white/10 text-gray-400 ${colors.inactive}`
      }`}
    >
      <div className="flex flex-col items-center gap-1">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium">{preset.name}</span>
        <span className="text-[10px] opacity-70">{preset.description}</span>
      </div>
    </button>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const GPUFilters: React.FC<GPUFiltersProps> = ({
  filters,
  onFiltersChange,
  availableProviders = DEFAULT_PROVIDERS,
  availableRegions = DEFAULT_REGIONS,
  resultCount,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSections, setExpandedSections] = useState<string[]>(['vram', 'price']);
  const [activePreset, setActivePreset] = useState<string | null>(null);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) =>
      prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section]
    );
  };

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.minVram > 0 || filters.maxVram < 80) count++;
    if (filters.minPrice > 0 || filters.maxPrice < 5) count++;
    if (filters.providers.length > 0) count++;
    if (filters.minReliability > 0) count++;
    if (filters.regions.length > 0) count++;
    if (filters.gpuCount !== null) count++;
    if (filters.verified !== null) count++;
    return count;
  }, [filters]);

  const handleReset = () => {
    onFiltersChange(DEFAULT_GPU_FILTERS);
    setActivePreset(null);
  };

  const applyPreset = (preset: FilterPreset) => {
    if (activePreset === preset.id) {
      // Toggle off - reset to defaults
      handleReset();
    } else {
      // Apply preset
      onFiltersChange({
        ...DEFAULT_GPU_FILTERS,
        ...preset.filters,
      });
      setActivePreset(preset.id);
    }
  };

  const updateFilter = <K extends keyof GPUFilterState>(key: K, value: GPUFilterState[K]) => {
    onFiltersChange({ ...filters, [key]: value });
    setActivePreset(null); // Clear preset when manually adjusting
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Quick Preset Filters - Always Visible */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs text-gray-400 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" />
            Filtros Rápidos
          </label>
          {resultCount !== undefined && (
            <span className="text-xs text-gray-500 font-mono">
              {resultCount} {resultCount === 1 ? 'máquina' : 'máquinas'}
            </span>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          {FILTER_PRESETS.map((preset) => (
            <PresetButton
              key={preset.id}
              preset={preset}
              isActive={activePreset === preset.id}
              onClick={() => applyPreset(preset)}
            />
          ))}
        </div>
      </div>

      {/* Active Filters Chips - Always Visible When Active */}
      {activeFiltersCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/10">
          <span className="text-[10px] text-gray-500">Filtros ativos:</span>
          {filters.minVram > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              VRAM ≥{filters.minVram}GB
              <button onClick={() => updateFilter('minVram', 0)} className="hover:text-brand-300">
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          {filters.maxVram < 80 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              VRAM ≤{filters.maxVram}GB
              <button onClick={() => updateFilter('maxVram', 80)} className="hover:text-brand-300">
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          {filters.maxPrice < 5 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              ≤${filters.maxPrice}/h
              <button onClick={() => updateFilter('maxPrice', 5)} className="hover:text-brand-300">
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          {filters.minReliability > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              ≥{filters.minReliability}% uptime
              <button onClick={() => updateFilter('minReliability', 0)} className="hover:text-brand-300">
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          {filters.providers.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              {filters.providers.join(', ')}
              <button onClick={() => updateFilter('providers', [])} className="hover:text-brand-300">
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          )}
          <button
            onClick={handleReset}
            className="ml-auto text-[10px] text-gray-500 hover:text-gray-300 flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            Limpar
          </button>
        </div>
      )}

      {/* Advanced Filters Toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-2.5 rounded-lg bg-white/[0.03] border border-white/5 hover:bg-white/[0.05] hover:border-white/10 transition-all"
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-xs text-gray-400">Filtros Avançados</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-gray-500" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>

      {/* Filters Panel */}
      {isExpanded && (
        <div className="mt-2 p-4 rounded-lg bg-gray-900 border border-white/10 space-y-1 animate-fadeIn">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <span className="text-xs text-gray-400">Refinar busca</span>
            <button
              onClick={handleReset}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Limpar filtros
            </button>
          </div>

          {/* VRAM Filter */}
          <FilterSection
            title="Memória VRAM"
            icon={<MemoryStick className="w-4 h-4" />}
            isOpen={expandedSections.includes('vram')}
            onToggle={() => toggleSection('vram')}
          >
            <RangeSlider
              min={0}
              max={80}
              value={[filters.minVram, filters.maxVram]}
              onChange={([min, max]) => {
                updateFilter('minVram', min);
                updateFilter('maxVram', max);
              }}
              options={VRAM_OPTIONS}
              formatValue={(v) => `${v}GB`}
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {[8, 16, 24, 48].map((vram) => (
                <button
                  key={vram}
                  onClick={() => {
                    updateFilter('minVram', vram);
                    updateFilter('maxVram', 80);
                  }}
                  className={`px-2 py-1 text-[10px] rounded border transition-all ${
                    filters.minVram === vram
                      ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                      : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-400'
                  }`}
                >
                  ≥{vram}GB
                </button>
              ))}
            </div>
          </FilterSection>

          {/* Price Filter */}
          <FilterSection
            title="Preço por Hora"
            icon={<DollarSign className="w-4 h-4" />}
            isOpen={expandedSections.includes('price')}
            onToggle={() => toggleSection('price')}
          >
            <RangeSlider
              min={0}
              max={5}
              value={[filters.minPrice, filters.maxPrice]}
              onChange={([min, max]) => {
                updateFilter('minPrice', min);
                updateFilter('maxPrice', max);
              }}
              options={PRICE_OPTIONS}
              formatValue={(v) => `$${v.toFixed(2)}`}
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {[
                { label: 'Econômico', max: 0.25 },
                { label: 'Médio', max: 0.50 },
                { label: 'Premium', max: 2.0 },
              ].map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => {
                    updateFilter('minPrice', 0);
                    updateFilter('maxPrice', preset.max);
                  }}
                  className={`px-2 py-1 text-[10px] rounded border transition-all ${
                    filters.maxPrice === preset.max && filters.minPrice === 0
                      ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                      : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-400'
                  }`}
                >
                  {preset.label} (≤${preset.max})
                </button>
              ))}
            </div>
          </FilterSection>

          {/* Provider Filter */}
          <FilterSection
            title="Provedores"
            icon={<Globe className="w-4 h-4" />}
            isOpen={expandedSections.includes('provider')}
            onToggle={() => toggleSection('provider')}
          >
            <ChipSelect
              options={availableProviders}
              selected={filters.providers}
              onChange={(providers) => updateFilter('providers', providers)}
            />
          </FilterSection>

          {/* Reliability Filter */}
          <FilterSection
            title="Confiabilidade"
            icon={<Shield className="w-4 h-4" />}
            isOpen={expandedSections.includes('reliability')}
            onToggle={() => toggleSection('reliability')}
          >
            <div className="flex flex-wrap gap-1.5">
              {RELIABILITY_OPTIONS.map((reliability) => (
                <button
                  key={reliability}
                  onClick={() => updateFilter('minReliability', reliability)}
                  className={`px-2.5 py-1 text-xs rounded border transition-all ${
                    filters.minReliability === reliability
                      ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  {reliability === 0 ? 'Qualquer' : `≥${reliability}%`}
                </button>
              ))}
            </div>
          </FilterSection>

          {/* GPU Count Filter */}
          <FilterSection
            title="Quantidade de GPUs"
            icon={<MemoryStick className="w-4 h-4" />}
            isOpen={expandedSections.includes('gpuCount')}
            onToggle={() => toggleSection('gpuCount')}
          >
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => updateFilter('gpuCount', null)}
                className={`px-2.5 py-1 text-xs rounded border transition-all ${
                  filters.gpuCount === null
                    ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                    : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                }`}
              >
                Qualquer
              </button>
              {GPU_COUNT_OPTIONS.map((count) => (
                <button
                  key={count}
                  onClick={() => updateFilter('gpuCount', count)}
                  className={`px-2.5 py-1 text-xs rounded border transition-all ${
                    filters.gpuCount === count
                      ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  {count}x GPU
                </button>
              ))}
            </div>
          </FilterSection>

        </div>
      )}
    </div>
  );
};

export default GPUFilters;

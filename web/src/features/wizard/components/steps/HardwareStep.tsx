/**
 * Hardware Step Component
 *
 * Step 2: Select GPU tier and specific machine.
 */

import React, { useState } from 'react';
import {
  Search,
  Server,
  Lightbulb,
  Code,
  Zap,
  Sparkles,
  Cpu,
  DollarSign,
  TrendingUp,
  Star,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Gauge,
  Activity,
} from 'lucide-react';
import { TierName, MachineOffer, RecommendedMachine, PerformanceTier } from '../../types';
import { PERFORMANCE_TIERS, GPU_OPTIONS, filterGPUs } from '../../constants';
import { GPUFilters, DEFAULT_GPU_FILTERS, GPUFilterState } from '../GPUFilters';

// ============================================================================
// Types
// ============================================================================

export interface HardwareStepProps {
  selectedTier: TierName | null;
  selectedGPU: string | null;
  selectedMachine: MachineOffer | null;
  recommendedMachines: RecommendedMachine[];
  loadingMachines: boolean;
  selectionMode: 'recommended' | 'manual';
  onSelectTier: (tier: TierName) => void;
  onSelectGPU: (gpu: string) => void;
  onSelectMachine: (machine: MachineOffer) => void;
  onToggleSelectionMode: () => void;
}

// ============================================================================
// Use Case Cards Data
// ============================================================================

const USE_CASES = [
  { id: 'cpu_only', label: 'Apenas CPU', icon: Server, tier: 'CPU' as TierName, desc: 'Sem GPU' },
  { id: 'test', label: 'Experimentar', icon: Lightbulb, tier: 'Lento' as TierName, desc: 'Testes rápidos' },
  { id: 'develop', label: 'Desenvolver', icon: Code, tier: 'Medio' as TierName, desc: 'Dev diário' },
  { id: 'train', label: 'Treinar modelo', icon: Zap, tier: 'Rapido' as TierName, desc: 'Fine-tuning' },
  { id: 'production', label: 'Produção', icon: Sparkles, tier: 'Ultra' as TierName, desc: 'LLMs grandes' },
] as const;

// ============================================================================
// Sub-components
// ============================================================================

interface UseCaseCardProps {
  id: string;
  label: string;
  icon: React.ElementType;
  tier: TierName;
  desc: string;
  isSelected: boolean;
  onClick: () => void;
}

const UseCaseCard: React.FC<UseCaseCardProps> = ({
  id,
  label,
  icon: Icon,
  isSelected,
  desc,
  onClick,
}) => (
  <button
    data-testid={`use-case-${id}`}
    onClick={onClick}
    className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
      isSelected
        ? 'bg-brand-500/10 border-brand-500'
        : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
    }`}
  >
    <div className="flex flex-col items-center gap-2 text-center">
      <div
        className={`w-8 h-8 rounded-md flex items-center justify-center ${
          isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-white/5 text-gray-500'
        }`}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <div className={`text-xs font-medium ${isSelected ? 'text-brand-400' : 'text-gray-300'}`}>
          {label}
        </div>
        <div className={`text-[10px] ${isSelected ? 'text-gray-400' : 'text-gray-500'}`}>
          {desc}
        </div>
      </div>
    </div>
  </button>
);

interface MachineCardProps {
  machine: RecommendedMachine;
  index: number;
  isSelected: boolean;
  onClick: () => void;
}

const MachineCard: React.FC<MachineCardProps> = ({ machine, index, isSelected, onClick }) => {
  const labelIcons = {
    'Mais econômico': DollarSign,
    'Melhor custo-benefício': TrendingUp,
    'Mais rápido': Zap,
  };
  const LabelIcon = labelIcons[machine.label] ?? Star;

  return (
    <button
      data-testid={`machine-${machine.id}`}
      onClick={onClick}
      className={`w-full p-3 rounded-lg border text-left transition-all cursor-pointer ${
        isSelected
          ? 'bg-brand-500/10 border-brand-500'
          : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
      }`}
    >
      <div className="flex items-center gap-3">
        {/* Radio indicator */}
        <div
          className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
            isSelected ? 'border-brand-500 bg-brand-500/20' : 'border-white/20'
          }`}
        >
          {isSelected && <div className="w-2 h-2 rounded-full bg-brand-400" />}
        </div>

        {/* GPU Icon */}
        <div
          className={`w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 ${
            isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-white/5 text-gray-500'
          }`}
        >
          <Cpu className="w-4 h-4" />
        </div>

        {/* Machine Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${isSelected ? 'text-brand-400' : 'text-gray-200'}`}>
              {machine.gpu_name}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
              {machine.gpu_ram}GB
            </span>
            {machine.num_gpus > 1 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                x{machine.num_gpus}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
            <span>{machine.location}</span>
            <span>•</span>
            <span>{machine.provider}</span>
            <span>•</span>
            <span>{machine.reliability}% uptime</span>
          </div>
        </div>

        {/* Label & Price */}
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <div
            className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded ${
              index === 1 ? 'bg-brand-500/20 text-brand-400' : 'bg-white/10 text-gray-400'
            }`}
          >
            <LabelIcon className="w-3 h-3" />
            {machine.label}
          </div>
          <span className="text-sm font-mono font-medium text-gray-200">
            ${machine.dph_total.toFixed(2)}/h
          </span>
        </div>
      </div>
    </button>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const HardwareStep: React.FC<HardwareStepProps> = ({
  selectedTier,
  selectedGPU,
  selectedMachine,
  recommendedMachines,
  loadingMachines,
  selectionMode,
  onSelectTier,
  onSelectGPU,
  onSelectMachine,
  onToggleSelectionMode,
}) => {
  const [gpuSearchQuery, setGpuSearchQuery] = useState('');
  const [gpuFilters, setGpuFilters] = useState<GPUFilterState>(DEFAULT_GPU_FILTERS);
  const filteredGPUs = filterGPUs(gpuSearchQuery);
  const selectedTierData = PERFORMANCE_TIERS.find((t) => t.name === selectedTier);

  // Apply filters to recommended machines
  const filteredMachines = recommendedMachines.filter((machine) => {
    if (machine.gpu_ram < gpuFilters.minVram) return false;
    if (machine.gpu_ram > gpuFilters.maxVram) return false;
    if (machine.dph_total < gpuFilters.minPrice) return false;
    if (machine.dph_total > gpuFilters.maxPrice) return false;
    if (gpuFilters.minReliability > 0 && (machine.reliability ?? 0) < gpuFilters.minReliability) return false;
    if (gpuFilters.providers.length > 0 && machine.provider && !gpuFilters.providers.includes(machine.provider)) return false;
    if (gpuFilters.gpuCount !== null && machine.num_gpus !== gpuFilters.gpuCount) return false;
    return true;
  });

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Section 1: Use Case Selection */}
      <div className="space-y-3">
        <div>
          <label className="text-gray-300 text-sm font-medium">O que você vai fazer?</label>
          <p className="text-xs text-gray-500 mt-1">
            Selecione seu objetivo para recomendarmos o hardware ideal
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {USE_CASES.map((useCase) => (
            <UseCaseCard
              key={useCase.id}
              {...useCase}
              isSelected={selectedTier === useCase.tier}
              onClick={() => onSelectTier(useCase.tier)}
            />
          ))}
        </div>
      </div>

      {/* Section 2: GPU Selection */}
      {selectedTier && (
        <div className="space-y-3">
          <div>
            <label className="text-gray-300 text-sm font-medium">Seleção de GPU</label>
            <p className="text-xs text-gray-500 mt-1">Escolha uma das máquinas recomendadas</p>
          </div>

          {/* GPU Filters */}
          <GPUFilters
            filters={gpuFilters}
            onFiltersChange={setGpuFilters}
            resultCount={filteredMachines.length}
          />

          <div className="space-y-2">
            {loadingMachines ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400 mr-2" />
                <span className="text-sm text-gray-400">Buscando máquinas disponíveis...</span>
              </div>
            ) : filteredMachines.length > 0 ? (
              filteredMachines.map((machine, index) => (
                <MachineCard
                  key={machine.id}
                  machine={machine}
                  index={index}
                  isSelected={selectedMachine?.id === machine.id}
                  onClick={() => onSelectMachine(machine)}
                />
              ))
            ) : recommendedMachines.length > 0 ? (
              <div className="text-center py-6 text-amber-500/80 text-sm">
                <AlertCircle className="w-5 h-5 mx-auto mb-2 opacity-70" />
                Nenhuma máquina corresponde aos filtros selecionados.
                <button
                  onClick={() => setGpuFilters(DEFAULT_GPU_FILTERS)}
                  className="block mx-auto mt-2 text-xs text-brand-400 hover:text-brand-300"
                >
                  Limpar filtros
                </button>
              </div>
            ) : (
              <div className="text-center py-6 text-gray-500 text-sm">
                <AlertCircle className="w-5 h-5 mx-auto mb-2 opacity-50" />
                Nenhuma máquina encontrada para esta configuração
              </div>
            )}

            {/* Toggle Manual Selection */}
            <button
              onClick={onToggleSelectionMode}
              className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-all flex items-center justify-center gap-1.5"
              data-testid="toggle-manual-selection"
            >
              {selectionMode === 'manual' ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5" />
                  Ocultar opções avançadas
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5" />
                  Ver mais opções
                </>
              )}
            </button>

            {/* Manual GPU Selection */}
            {selectionMode === 'manual' && (
              <div className="pt-3 border-t border-white/10 space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Buscar GPU (ex: RTX 4090, A100, H100...)"
                    className="w-full pl-10 pr-4 py-2.5 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all"
                    value={gpuSearchQuery}
                    onChange={(e) => setGpuSearchQuery(e.target.value)}
                    data-testid="gpu-search-input"
                  />
                </div>

                <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                  {filteredGPUs.length > 0 ? (
                    filteredGPUs.map((gpu) => {
                      const isSelected = selectedGPU === gpu.name;
                      return (
                        <button
                          key={gpu.name}
                          data-testid={`gpu-option-${gpu.name.toLowerCase().replace(/\s+/g, '-')}`}
                          onClick={() => onSelectGPU(gpu.name)}
                          className={`w-full p-2.5 rounded-lg border text-left transition-all cursor-pointer flex items-center justify-between ${
                            isSelected
                              ? 'bg-brand-500/10 border-brand-500'
                              : 'bg-white/[0.02] border-white/10 hover:bg-white/5 hover:border-white/20'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-7 h-7 rounded flex items-center justify-center ${
                                isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-white/5 text-gray-500'
                              }`}
                            >
                              <Cpu className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <span
                                className={`text-sm font-medium ${
                                  isSelected ? 'text-brand-400' : 'text-gray-200'
                                }`}
                              >
                                {gpu.name}
                              </span>
                              <span className="text-[10px] text-gray-500 ml-2">{gpu.vram}</span>
                            </div>
                          </div>
                          <span className="text-xs text-gray-500">{gpu.priceRange}</span>
                        </button>
                      );
                    })
                  ) : (
                    <div className="text-center py-4 text-gray-500 text-xs">
                      Nenhuma GPU encontrada para "{gpuSearchQuery}"
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tier Summary */}
      {selectedTierData && (
        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-md bg-brand-500/20 flex items-center justify-center flex-shrink-0">
              {selectedTier === 'Lento' && <Gauge className="w-4 h-4 text-brand-400" />}
              {selectedTier === 'Medio' && <Activity className="w-4 h-4 text-brand-400" />}
              {selectedTier === 'Rapido' && <Zap className="w-4 h-4 text-brand-400" />}
              {selectedTier === 'Ultra' && <Sparkles className="w-4 h-4 text-brand-400" />}
              {selectedTier === 'CPU' && <Server className="w-4 h-4 text-brand-400" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-200">Tier: {selectedTierData.name}</span>
                <span className="text-xs font-mono text-brand-400">{selectedTierData.priceRange}</span>
              </div>
              <div className="text-xs text-gray-500">
                <span>{selectedTierData.gpu}</span>
                <span className="mx-1">•</span>
                <span>{selectedTierData.vram}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HardwareStep;

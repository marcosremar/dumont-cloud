/**
 * HardwareStep Component
 * Step 2: Hardware/GPU selection
 */

import React from 'react';
import {
  Cpu,
  Search,
  Loader2,
  Check,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Star,
  TrendingUp,
  DollarSign,
  HardDrive,
} from 'lucide-react';
import { useWizard } from '../WizardContext';
import { PERFORMANCE_TIERS } from '../../dashboard/constants';
import { GPU_LIST, filterGPUs } from '../constants/gpuData';
import type { MachineOffer } from '../types/wizard.types';

export function HardwareStep() {
  const {
    state,
    dispatch,
    recommendedMachines,
    loadingMachines,
    apiError,
  } = useWizard();

  const {
    selectedTier,
    selectionMode,
    selectedMachine,
    gpuSearchQuery,
  } = state;

  const filteredGPUs = filterGPUs(gpuSearchQuery);

  // Handle tier selection
  const handleTierSelect = (tierName: string) => {
    dispatch({ type: 'SET_TIER', payload: tierName });
  };

  // Handle machine selection
  const handleMachineSelect = (machine: MachineOffer) => {
    dispatch({ type: 'SET_SELECTED_MACHINE', payload: machine });
  };

  // Handle GPU selection (manual mode)
  const handleGPUSelect = (gpuName: string) => {
    dispatch({ type: 'SET_GPU', payload: gpuName });
    dispatch({ type: 'SET_SELECTED_MACHINE', payload: null });
  };

  // Toggle selection mode
  const toggleSelectionMode = () => {
    dispatch({
      type: 'SET_SELECTION_MODE',
      payload: selectionMode === 'recommended' ? 'manual' : 'recommended',
    });
  };

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Performance Tier Selection */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-gray-300">Performance Tier</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Select based on your workload requirements
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {PERFORMANCE_TIERS.map((tier) => {
            const isSelected = selectedTier === tier.name;
            const TierIcon = tier.icon;

            return (
              <button
                key={tier.name}
                onClick={() => handleTierSelect(tier.name)}
                data-testid={`tier-${tier.name.toLowerCase()}`}
                className={`p-4 rounded-lg border text-left transition-all ${
                  isSelected
                    ? 'bg-brand-500/10 border-brand-500'
                    : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isSelected
                        ? 'bg-brand-500/20 text-brand-400'
                        : 'bg-white/5 text-gray-500'
                    }`}
                  >
                    <TierIcon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-sm font-medium ${
                          isSelected ? 'text-brand-400' : 'text-gray-300'
                        }`}
                      >
                        {tier.name}
                      </span>
                      {tier.recommended && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                          Popular
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-gray-500 mt-1 line-clamp-2">
                      {tier.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-[10px] text-brand-400 font-medium">
                        {tier.priceRange}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Recommended Machines */}
      {selectedTier && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-300">
                Recommended Machines
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {loadingMachines
                  ? 'Loading available machines...'
                  : `${recommendedMachines.length} machines found for ${selectedTier}`}
              </p>
            </div>
          </div>

          {loadingMachines ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-brand-400" />
            </div>
          ) : apiError ? (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">{apiError}</span>
              </div>
            </div>
          ) : recommendedMachines.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {recommendedMachines.map((machine, idx) => {
                const isSelected = selectedMachine?.id === machine.id;

                return (
                  <button
                    key={machine.id}
                    onClick={() => handleMachineSelect(machine)}
                    data-testid={`machine-${idx}`}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'bg-brand-500/10 border-brand-500'
                        : 'bg-white/[0.02] border-white/10 hover:bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-8 h-8 rounded-md flex items-center justify-center ${
                            isSelected
                              ? 'bg-brand-500/20 text-brand-400'
                              : 'bg-white/5 text-gray-500'
                          }`}
                        >
                          <Cpu className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-sm font-medium ${
                                isSelected ? 'text-gray-100' : 'text-gray-300'
                              }`}
                            >
                              {machine.gpu_name}
                            </span>
                            {machine.num_gpus > 1 && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                                x{machine.num_gpus}
                              </span>
                            )}
                            {machine.verified && (
                              <Star className="w-3 h-3 text-yellow-400" />
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-gray-500 mt-0.5">
                            <span>{machine.gpu_ram?.toFixed(0)}GB VRAM</span>
                            <span>•</span>
                            <span>
                              {machine.geolocation || machine.location || 'Unknown'}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-brand-400 font-medium text-sm">
                          <DollarSign className="w-3 h-3" />
                          {machine.dph_total?.toFixed(2)}/h
                        </div>
                        {machine.reliability !== undefined && (
                          <div className="flex items-center gap-1 text-[10px] text-gray-500 mt-0.5">
                            <TrendingUp className="w-3 h-3" />
                            {machine.reliability?.toFixed(0)}% reliable
                          </div>
                        )}
                      </div>
                    </div>
                    {isSelected && (
                      <div className="flex items-center justify-end mt-2">
                        <Check className="w-4 h-4 text-brand-400" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-white/5 border border-white/10 text-center">
              <HardDrive className="w-8 h-8 text-gray-500 mx-auto mb-2" />
              <p className="text-sm text-gray-400">
                No machines available for this configuration
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Try selecting a different region or tier
              </p>
            </div>
          )}

          {/* Toggle Manual Mode */}
          <button
            onClick={toggleSelectionMode}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-400 transition-colors"
          >
            {selectionMode === 'manual' ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" />
                Hide advanced options
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" />
                See more options
              </>
            )}
          </button>

          {/* Manual GPU Search */}
          {selectionMode === 'manual' && (
            <div className="pt-3 border-t border-white/10 space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search GPU (e.g., RTX 4090, A100, H100...)"
                  className="w-full pl-10 pr-4 py-2.5 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all"
                  value={gpuSearchQuery}
                  onChange={(e) =>
                    dispatch({ type: 'SET_GPU_SEARCH_QUERY', payload: e.target.value })
                  }
                  data-testid="gpu-search-input"
                />
              </div>

              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                {filteredGPUs.length > 0 ? (
                  filteredGPUs.map((gpu) => {
                    const isSelected = state.selectedGPU === gpu.name;
                    return (
                      <button
                        key={gpu.name}
                        data-testid={`gpu-option-${gpu.name
                          .toLowerCase()
                          .replace(/\s+/g, '-')}`}
                        onClick={() => handleGPUSelect(gpu.name)}
                        className={`w-full p-2.5 rounded-lg border text-left transition-all cursor-pointer flex items-center justify-between ${
                          isSelected
                            ? 'bg-brand-500/10 border-brand-500'
                            : 'bg-white/[0.02] border-white/10 hover:bg-white/5 hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <div
                            className={`w-7 h-7 rounded flex items-center justify-center ${
                              isSelected
                                ? 'bg-brand-500/20 text-brand-400'
                                : 'bg-white/5 text-gray-500'
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
                            <span className="text-[10px] text-gray-500 ml-2">
                              {gpu.vram}
                            </span>
                          </div>
                        </div>
                        <span className="text-xs text-gray-500">{gpu.priceRange}</span>
                      </button>
                    );
                  })
                ) : (
                  <div className="text-center py-4 text-gray-500 text-xs">
                    No GPUs found for "{gpuSearchQuery}"
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default HardwareStep;

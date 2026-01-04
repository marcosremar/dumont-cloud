/**
 * SelectionSummary Component
 * Displays a summary of selections from previous steps
 */

import React from 'react';
import { Globe, MapPin, Cpu, Server, Shield } from 'lucide-react';
import type { WizardStep, SelectedLocation, FailoverStrategy } from '../types/wizard.types';
import { getFailoverOption } from '../constants/failoverOptions';

interface SelectionSummaryProps {
  currentStep: WizardStep;
  selectedLocations: SelectedLocation[];
  selectedTier: string | null;
  selectedGPU: string;
  failoverStrategy: FailoverStrategy;
}

export function SelectionSummary({
  currentStep,
  selectedLocations,
  selectedTier,
  selectedGPU,
  failoverStrategy,
}: SelectionSummaryProps) {
  if (currentStep <= 1) return null;

  const failoverOption = getFailoverOption(failoverStrategy);

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10 mb-4">
      <span className="text-xs text-gray-500 mr-1">Selected:</span>

      {/* Location Tags */}
      {selectedLocations.map((loc, idx) => (
        <div
          key={loc.name + idx}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-brand-500/10 border border-brand-500/30 text-brand-400 rounded-full text-xs font-medium"
        >
          {loc.isRegion ? (
            <Globe className="w-3 h-3" />
          ) : (
            <MapPin className="w-3 h-3" />
          )}
          <span>{loc.name}</span>
        </div>
      ))}

      {/* Tier Tag */}
      {currentStep > 2 && selectedTier && (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded-full text-xs font-medium">
          <Cpu className="w-3 h-3" />
          <span>{selectedTier}</span>
        </div>
      )}

      {/* GPU Tag */}
      {currentStep > 2 && selectedGPU && selectedGPU !== 'any' && (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-full text-xs font-medium">
          <Server className="w-3 h-3" />
          <span>{selectedGPU}</span>
        </div>
      )}

      {/* Strategy Tag */}
      {currentStep > 3 && failoverStrategy && (
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-full text-xs font-medium">
          <Shield className="w-3 h-3" />
          <span>{failoverOption?.name || failoverStrategy}</span>
        </div>
      )}
    </div>
  );
}

export default SelectionSummary;

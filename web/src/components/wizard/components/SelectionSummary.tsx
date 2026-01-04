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
  // Only show from step 2 onwards and only if there are selections
  if (currentStep <= 1 || selectedLocations.length === 0) return null;

  const failoverOption = getFailoverOption(failoverStrategy);

  return (
    <div className="flex flex-wrap items-center gap-1.5 mb-4 text-xs">
      <span className="text-gray-500">Selected:</span>

      {/* Location Tags */}
      {selectedLocations.map((loc, idx) => (
        <span
          key={loc.name + idx}
          className="inline-flex items-center gap-1 px-2 py-0.5 bg-brand-500/10 text-brand-400 rounded text-[11px]"
        >
          {loc.isRegion ? <Globe className="w-3 h-3" /> : <MapPin className="w-3 h-3" />}
          {loc.name}
        </span>
      ))}

      {/* Tier Tag */}
      {currentStep >= 2 && selectedTier && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded text-[11px]">
          <Cpu className="w-3 h-3" />
          {selectedTier}
        </span>
      )}

      {/* Strategy Tag */}
      {currentStep >= 4 && failoverStrategy && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded text-[11px]">
          <Shield className="w-3 h-3" />
          {failoverOption?.name || failoverStrategy}
        </span>
      )}
    </div>
  );
}

export default SelectionSummary;

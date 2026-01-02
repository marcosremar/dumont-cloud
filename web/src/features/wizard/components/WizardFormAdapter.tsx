/**
 * Wizard Form Adapter
 *
 * Adapter component that bridges the old prop-based API
 * with the new internally-managed wizard.
 * This allows gradual migration without breaking existing code.
 */

import React from 'react';
import { WizardForm } from './WizardForm';
import { ProvisioningCandidate, Location, TierName } from '../types';

// ============================================================================
// Legacy Props Interface (matches old WizardForm)
// ============================================================================

export interface WizardFormAdapterProps {
  // Step 1: Location (legacy - ignored, wizard manages internally)
  searchCountry?: string;
  selectedLocation?: Location | null;
  onSearchChange?: (search: string) => void;
  onRegionSelect?: (region: string) => void;
  onCountryClick?: (location: Location) => void;
  onClearSelection?: () => void;

  // Step 2: Hardware (legacy - ignored, wizard manages internally)
  selectedGPU?: string | null;
  onSelectGPU?: (gpu: string) => void;
  selectedGPUCategory?: string;
  onSelectGPUCategory?: (category: string) => void;
  selectedTier?: TierName | null;
  onSelectTier?: (tier: TierName) => void;

  // Actions
  loading?: boolean;
  onSubmit?: () => void;

  // Provisioning (Step 4) - legacy, ignored
  provisioningCandidates?: ProvisioningCandidate[];
  provisioningWinner?: ProvisioningCandidate | null;
  isProvisioning?: boolean;
  onCancelProvisioning?: () => void;
  onCompleteProvisioning?: (winner: ProvisioningCandidate) => void;
  currentRound?: number;
  maxRounds?: number;

  // World Map component
  WorldMapComponent?: React.ComponentType<{
    selectedCodes: string[];
    onCountryClick: (code: string) => void;
  }>;
}

// ============================================================================
// Adapter Component
// ============================================================================

/**
 * Adapter that wraps the new WizardForm with the old props API.
 * The new wizard manages all state internally, so most legacy props are ignored.
 * Only `onCompleteProvisioning` and `onCancelProvisioning` are passed through.
 */
export const WizardFormAdapter: React.FC<WizardFormAdapterProps> = ({
  onCompleteProvisioning,
  onCancelProvisioning,
  WorldMapComponent,
}) => {
  return (
    <WizardForm
      onComplete={onCompleteProvisioning}
      onCancel={onCancelProvisioning}
      WorldMapComponent={WorldMapComponent}
    />
  );
};

export default WizardFormAdapter;

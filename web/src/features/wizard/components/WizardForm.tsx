/**
 * Wizard Form Component
 *
 * Main orchestrator component that composes all wizard steps.
 * This is a "thin" component - all logic is in hooks.
 */

import React from 'react';
import { ChevronLeft, ChevronRight, X, Check, Loader2, Zap, AlertCircle } from 'lucide-react';
import { WizardStep, ProvisioningCandidate } from '../types';
import { useWizardForm, UseWizardFormOptions } from '../hooks';
import { useProvisioningTimer } from '../hooks/useProvisioningTimer';
import { getStrategyById } from '../constants';
import { WizardStepper } from './WizardStepper';
import { LocationStep, HardwareStep, StrategyStep, ProvisioningStep } from './steps';

// ============================================================================
// Types
// ============================================================================

export interface WizardFormProps extends UseWizardFormOptions {
  /** World map component to render in location step */
  WorldMapComponent?: React.ComponentType<{
    selectedCodes: string[];
    onCountryClick: (code: string) => void;
  }>;
  /** Class name for the container */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export const WizardForm: React.FC<WizardFormProps> = ({
  WorldMapComponent,
  className = '',
  ...hookOptions
}) => {
  const { state, actions, validation, computed } = useWizardForm(hookOptions);

  const timer = useProvisioningTimer({
    isActive: state.currentStep === 4 && state.isProvisioning,
    candidates: state.provisioningCandidates,
    hasWinner: state.provisioningWinner !== null,
  });

  const selectedFailoverData = getStrategyById(state.failoverStrategy);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  const renderStep = () => {
    switch (state.currentStep) {
      case 1:
        return (
          <LocationStep
            selectedLocation={state.selectedLocation}
            searchCountry={state.searchCountry}
            onSearchChange={actions.setSearchCountry}
            onRegionSelect={actions.selectRegion}
            onCountryClick={actions.selectCountry}
            onClearSelection={actions.clearLocation}
            WorldMapComponent={WorldMapComponent}
          />
        );

      case 2:
        return (
          <HardwareStep
            selectedTier={state.selectedTier}
            selectedGPU={state.selectedGPU}
            selectedMachine={state.selectedMachine}
            recommendedMachines={state.recommendedMachines}
            loadingMachines={state.loadingMachines}
            selectionMode={state.selectionMode}
            onSelectTier={actions.setTier}
            onSelectGPU={actions.setGPU}
            onSelectMachine={actions.setMachine}
            onToggleSelectionMode={() =>
              actions.setSelectionMode(state.selectionMode === 'manual' ? 'recommended' : 'manual')
            }
          />
        );

      case 3:
        return (
          <StrategyStep
            failoverStrategy={state.failoverStrategy}
            selectedLocation={state.selectedLocation}
            selectedTier={state.selectedTier}
            showAdvancedSettings={state.showAdvancedSettings}
            dockerImage={state.dockerImage}
            exposedPorts={state.exposedPorts}
            onSelectStrategy={actions.setFailoverStrategy}
            onToggleAdvancedSettings={actions.toggleAdvancedSettings}
            onDockerImageChange={actions.setDockerImage}
            onAddPort={actions.addPort}
            onRemovePort={actions.removePort}
            onUpdatePort={actions.updatePort}
          />
        );

      case 4:
        return (
          <ProvisioningStep
            candidates={state.provisioningCandidates}
            winner={state.provisioningWinner}
            currentRound={state.currentRound}
            maxRounds={state.maxRounds}
            elapsedTime={timer.formattedTime}
            eta={timer.eta}
            selectedFailover={selectedFailoverData}
          />
        );

      default:
        return null;
    }
  };

  const renderNavigationButtons = () => {
    const isStep4 = state.currentStep === 4;
    const hasWinner = state.provisioningWinner !== null;

    return (
      <div className="flex items-center justify-between pt-4 border-t border-white/10">
        {/* Left Button */}
        {isStep4 ? (
          <button
            onClick={() => {
              actions.cancelProvisioning();
              actions.goToStep(3);
            }}
            className="px-4 py-2 text-gray-400 hover:text-gray-200 flex items-center gap-1 transition-colors"
          >
            <X className="w-4 h-4" />
            {hasWinner ? 'Buscar Outras' : 'Cancelar'}
          </button>
        ) : (
          <button
            onClick={actions.prevStep}
            disabled={state.currentStep === 1}
            className={`px-4 py-2 text-gray-400 hover:text-gray-200 flex items-center gap-1 transition-colors ${
              state.currentStep === 1 ? 'opacity-0 pointer-events-none' : ''
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            Voltar
          </button>
        )}

        {/* Right Button */}
        {isStep4 ? (
          <button
            onClick={() => state.provisioningWinner && actions.completeProvisioning(state.provisioningWinner)}
            disabled={!hasWinner}
            className="group relative px-6 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 hover:scale-[1.02] active:scale-[0.98]"
          >
            <span className="flex items-center gap-2">
              {hasWinner ? (
                <>
                  <Check className="w-4 h-4" />
                  Usar Esta Máquina
                </>
              ) : (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Conectando...
                </>
              )}
            </span>
          </button>
        ) : state.currentStep < 3 ? (
          <button
            onClick={actions.nextStep}
            disabled={!validation.isStepComplete(state.currentStep)}
            className="group relative px-6 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 hover:scale-[1.02] active:scale-[0.98]"
          >
            <span className="flex items-center gap-2">
              Próximo
              <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </button>
        ) : (
          <button
            onClick={actions.startProvisioning}
            disabled={!validation.isStepComplete(state.currentStep)}
            className="group relative px-6 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 hover:scale-[1.02] active:scale-[0.98]"
          >
            <span className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Iniciar
            </span>
          </button>
        )}
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={`p-6 space-y-6 ${className}`}>
      {/* Stepper */}
      <WizardStepper
        currentStep={state.currentStep}
        isStepPassed={validation.isStepPassed}
        canProceedToStep={validation.canProceedToStep}
        onStepClick={actions.goToStep}
      />

      {/* Validation Errors */}
      {state.validationErrors.length > 0 && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-400 mb-2">
                Por favor, corrija os seguintes campos:
              </h4>
              <ul className="space-y-1">
                {state.validationErrors.map((error, idx) => (
                  <li key={idx} className="text-sm text-red-300/80 flex items-start gap-2">
                    <span className="text-red-400/60 mt-1">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Current Step Content */}
      {renderStep()}

      {/* Navigation */}
      {renderNavigationButtons()}
    </div>
  );
};

export default WizardForm;

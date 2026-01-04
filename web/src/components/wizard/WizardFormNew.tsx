/**
 * WizardForm Component (Refactored)
 * Main orchestrator component that brings together all wizard pieces
 *
 * This is a slim orchestrator that:
 * - Renders the appropriate step based on currentStep
 * - Handles navigation between steps
 * - Manages submission logic
 * - Coordinates with parent component for provisioning
 */

import React, { useCallback } from 'react';
import { CardContent } from '../tailadmin-ui';
import { WizardProvider, useWizard } from './WizardContext';
import { WizardProgress, ValidationErrors, SelectionSummary, WizardNavigation } from './components';
import { LocationStep, HardwareStep, StrategyStep, ProvisioningStep } from './steps';
import { validateAllSteps } from './utils/validation';
import { getOffersForRacing, getOfferBreakdown } from './utils/offerFiltering';
import { useElapsedTime } from './hooks/useElapsedTime';
import type {
  WizardFormProps,
  WizardStep,
  WizardSubmitData,
  ProvisioningCandidate,
  ProvisioningWinner,
} from './types/wizard.types';

// ============================================================================
// Inner Component (uses context)
// ============================================================================

interface WizardFormInnerProps {
  onSubmit: (data: WizardSubmitData) => void;
  loading?: boolean;
  provisioningCandidates?: ProvisioningCandidate[];
  provisioningWinner?: ProvisioningWinner | null;
  currentRound?: number;
  maxRounds?: number;
  raceError?: string | null;
  isFailed?: boolean;
  onCancelProvisioning?: () => void;
  onCompleteProvisioning?: (winner: ProvisioningWinner) => void;
}

function WizardFormInner({
  onSubmit,
  loading = false,
  provisioningCandidates = [],
  provisioningWinner = null,
  currentRound = 1,
  maxRounds = 3,
  raceError = null,
  isFailed = false,
  onCancelProvisioning,
  onCompleteProvisioning,
}: WizardFormInnerProps) {
  const {
    state,
    dispatch,
    isStepComplete,
    isStepPassed,
    canProceed,
    recommendedMachines,
    allAvailableOffers,
    userBalance,
  } = useWizard();

  const { currentStep, validationErrors, failoverStrategy } = state;

  // Elapsed time for provisioning
  const { elapsedTime } = useElapsedTime({
    running: currentStep === 4 && !provisioningWinner && !isFailed,
    resetOn: currentRound,
  });

  // Handle step navigation
  const handleStepClick = useCallback(
    (step: WizardStep) => {
      if (isStepPassed(step) || step === currentStep) {
        dispatch({ type: 'SET_STEP', payload: step });
      }
    },
    [dispatch, isStepPassed, currentStep]
  );

  // Handle next step
  const handleNext = useCallback(() => {
    if (currentStep < 3) {
      dispatch({ type: 'NEXT_STEP' });
      return;
    }

    // Step 3 -> Step 4: Validate and submit
    const machineToUse = state.selectedMachine || recommendedMachines[0];

    const validation = validateAllSteps(
      state,
      userBalance,
      state.selectedMachine,
      recommendedMachines
    );

    if (!validation.isValid) {
      dispatch({ type: 'SET_VALIDATION_ERRORS', payload: validation.errors });
      return;
    }

    dispatch({ type: 'CLEAR_VALIDATION_ERRORS' });
    dispatch({ type: 'SET_STEP', payload: 4 });

    // Get offers for racing
    const offersForRacing = getOffersForRacing(allAvailableOffers, machineToUse);
    const breakdown = getOfferBreakdown(allAvailableOffers, machineToUse);

    console.log('[WizardForm] Racing offers breakdown:');
    console.log('  - Selected machine:', machineToUse.gpu_name, 'x', machineToUse.num_gpus);
    console.log('  - Exact matches:', breakdown.exactMatches.length);
    console.log('  - Same GPU matches:', breakdown.sameGpuMatches.length);
    console.log('  - Other offers:', breakdown.otherOffers.length);
    console.log('  - Total for racing:', offersForRacing.length);

    // Submit
    const submitData: WizardSubmitData = {
      machine: machineToUse,
      offerId: machineToUse.id,
      failoverStrategy: state.failoverStrategy,
      tier: state.selectedTier,
      regions: state.selectedLocations,
      allOffers: offersForRacing,
      dockerImage: state.dockerImage,
      exposedPorts: state.exposedPorts,
      snapshot: state.selectedSnapshot,
    };

    onSubmit(submitData);
  }, [
    currentStep,
    state,
    dispatch,
    recommendedMachines,
    allAvailableOffers,
    userBalance,
    onSubmit,
  ]);

  // Handle previous step
  const handlePrev = useCallback(() => {
    if (currentStep === 4 && onCancelProvisioning) {
      onCancelProvisioning();
    }
    dispatch({ type: 'PREV_STEP' });
  }, [currentStep, dispatch, onCancelProvisioning]);

  // Handle cancel provisioning
  const handleCancel = useCallback(() => {
    if (onCancelProvisioning) {
      onCancelProvisioning();
    }
    dispatch({ type: 'SET_STEP', payload: 3 });
  }, [dispatch, onCancelProvisioning]);

  // Handle complete provisioning
  const handleComplete = useCallback(() => {
    if (provisioningWinner && onCompleteProvisioning) {
      onCompleteProvisioning(provisioningWinner);
    }
  }, [provisioningWinner, onCompleteProvisioning]);

  // Render current step
  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <LocationStep />;
      case 2:
        return <HardwareStep />;
      case 3:
        return <StrategyStep />;
      case 4:
        return (
          <ProvisioningStep
            candidates={provisioningCandidates}
            winner={provisioningWinner}
            currentRound={currentRound}
            maxRounds={maxRounds}
            elapsedTime={elapsedTime}
            raceError={raceError}
            isFailed={isFailed}
            failoverStrategy={failoverStrategy}
          />
        );
      default:
        return null;
    }
  };

  return (
    <CardContent>
      {/* Progress Indicator */}
      <WizardProgress
        currentStep={currentStep}
        isStepComplete={isStepComplete}
        isStepPassed={isStepPassed}
        onStepClick={handleStepClick}
      />

      {/* Validation Errors */}
      <ValidationErrors errors={validationErrors} />

      {/* Selection Summary */}
      <SelectionSummary
        currentStep={currentStep}
        selectedLocations={state.selectedLocations}
        selectedTier={state.selectedTier}
        selectedGPU={state.selectedGPU}
        failoverStrategy={state.failoverStrategy}
      />

      {/* Current Step Content */}
      {renderStep()}

      {/* Navigation */}
      <WizardNavigation
        currentStep={currentStep}
        canProceed={canProceed}
        loading={loading}
        provisioningWinner={provisioningWinner}
        onNext={handleNext}
        onPrev={handlePrev}
        onCancel={handleCancel}
        onComplete={handleComplete}
      />
    </CardContent>
  );
}

// ============================================================================
// Main Component (provides context)
// ============================================================================

export function WizardFormNew({
  migrationMode = false,
  sourceMachine = null,
  targetType = null,
  initialStep = 1,
  onSubmit,
  loading = false,
  provisioningCandidates = [],
  provisioningWinner = null,
  isProvisioning = false,
  currentRound = 1,
  maxRounds = 3,
  raceError = null,
  isFailed = false,
  onCancelProvisioning,
  onCompleteProvisioning,
}: WizardFormProps) {
  return (
    <WizardProvider initialStep={initialStep} migrationMode={migrationMode}>
      <WizardFormInner
        onSubmit={onSubmit}
        loading={loading}
        provisioningCandidates={provisioningCandidates}
        provisioningWinner={provisioningWinner}
        currentRound={currentRound}
        maxRounds={maxRounds}
        raceError={raceError}
        isFailed={isFailed}
        onCancelProvisioning={onCancelProvisioning}
        onCompleteProvisioning={onCompleteProvisioning}
      />
    </WizardProvider>
  );
}

export default WizardFormNew;

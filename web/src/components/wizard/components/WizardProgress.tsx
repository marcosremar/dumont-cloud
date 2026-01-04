/**
 * WizardProgress Component
 * Displays the step progress indicator
 */

import React from 'react';
import { Check } from 'lucide-react';
import { WIZARD_STEPS } from '../constants/steps';
import type { WizardStep } from '../types/wizard.types';

interface WizardProgressProps {
  currentStep: WizardStep;
  isStepComplete: (step: WizardStep) => boolean;
  isStepPassed: (step: WizardStep) => boolean;
  onStepClick?: (step: WizardStep) => void;
}

export function WizardProgress({
  currentStep,
  isStepComplete,
  isStepPassed,
  onStepClick,
}: WizardProgressProps) {
  return (
    <div className="flex items-center justify-between mb-6 px-2">
      {WIZARD_STEPS.map((step, index) => {
        const StepIcon = step.icon;
        const isCurrent = currentStep === step.id;
        const isPassed = isStepPassed(step.id);
        const isComplete = isStepComplete(step.id);
        const isClickable = isPassed || isCurrent;

        return (
          <React.Fragment key={step.id}>
            <button
              onClick={() => isClickable && onStepClick?.(step.id)}
              disabled={!isClickable}
              className={`flex items-center gap-2 relative group ${
                isClickable ? 'cursor-pointer' : 'cursor-default'
              }`}
            >
              {/* Step Circle */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 flex-shrink-0 ${
                  isCurrent
                    ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/30'
                    : isPassed
                    ? 'bg-brand-500/20 text-brand-400'
                    : 'bg-white/5 text-gray-500'
                }`}
              >
                {isPassed ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <StepIcon className="w-4 h-4" />
                )}
              </div>

              {/* Step Label - only show on larger screens or current step */}
              <div className={`hidden sm:block ${isCurrent ? '' : 'sm:hidden md:block'}`}>
                <span
                  className={`text-xs font-medium whitespace-nowrap ${
                    isCurrent
                      ? 'text-brand-400'
                      : isPassed
                      ? 'text-gray-400'
                      : 'text-gray-600'
                  }`}
                >
                  {step.name}
                </span>
                <span
                  className={`text-[10px] block whitespace-nowrap ${
                    isCurrent ? 'text-gray-400' : 'text-gray-600'
                  }`}
                >
                  {step.description}
                </span>
              </div>
            </button>

            {/* Connector Line */}
            {index < WIZARD_STEPS.length - 1 && (
              <div className="flex-1 h-0.5 mx-2 md:mx-4 min-w-[20px] md:min-w-[40px]">
                <div className="h-full bg-white/10 rounded-full relative overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-brand-500 rounded-full transition-all duration-500"
                    style={{ width: isPassed ? '100%' : '0%' }}
                  />
                </div>
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export default WizardProgress;

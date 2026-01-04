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
    <div className="flex items-center justify-center mb-6">
      <div className="flex items-center">
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
                className={`flex flex-col items-center relative group ${
                  isClickable ? 'cursor-pointer' : 'cursor-default'
                }`}
              >
                {/* Step Circle */}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isCurrent
                      ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/30'
                      : isPassed
                      ? 'bg-brand-500/20 text-brand-400'
                      : 'bg-white/5 text-gray-500'
                  }`}
                >
                  {isPassed ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <StepIcon className="w-5 h-5" />
                  )}
                </div>

                {/* Step Label */}
                <div className="mt-2 text-center">
                  <span
                    className={`text-xs font-medium block ${
                      isCurrent
                        ? 'text-brand-400'
                        : isPassed
                        ? 'text-gray-400'
                        : 'text-gray-600'
                    }`}
                  >
                    {step.name}
                  </span>
                  <span className="text-[10px] text-gray-600 hidden sm:block">
                    {step.description}
                  </span>
                </div>

                {/* Tooltip on hover */}
                {isPassed && (
                  <div className="absolute -bottom-8 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[10px] text-gray-400 whitespace-nowrap">
                      Click para editar
                    </span>
                  </div>
                )}
              </button>

              {/* Connector Line */}
              {index < WIZARD_STEPS.length - 1 && (
                <div className="flex-1 h-0.5 mx-3 relative top-[-16px] min-w-[40px]">
                  <div className="absolute inset-0 bg-white/10 rounded-full" />
                  <div
                    className="absolute inset-y-0 left-0 bg-brand-500 rounded-full transition-all duration-500"
                    style={{ width: isPassed ? '100%' : '0%' }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

export default WizardProgress;

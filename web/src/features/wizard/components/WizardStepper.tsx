/**
 * Wizard Stepper Component
 *
 * Progress indicator showing current step and navigation.
 */

import React from 'react';
import { Check, Globe, Cpu, Shield, Rocket, LucideIcon } from 'lucide-react';
import { WizardStep } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface Step {
  id: WizardStep;
  name: string;
  description: string;
  icon: LucideIcon;
}

export interface WizardStepperProps {
  currentStep: WizardStep;
  isStepPassed: (step: WizardStep) => boolean;
  canProceedToStep: (step: WizardStep) => boolean;
  onStepClick: (step: WizardStep) => void;
}

// ============================================================================
// Steps Configuration
// ============================================================================

const STEPS: Step[] = [
  { id: 1, name: 'Região', description: 'Localização', icon: Globe },
  { id: 2, name: 'Hardware', description: 'GPU e performance', icon: Cpu },
  { id: 3, name: 'Estratégia', description: 'Failover', icon: Shield },
  { id: 4, name: 'Provisionar', description: 'Conectando', icon: Rocket },
];

// ============================================================================
// Component
// ============================================================================

export const WizardStepper: React.FC<WizardStepperProps> = ({
  currentStep,
  isStepPassed,
  canProceedToStep,
  onStepClick,
}) => {
  return (
    <div className="relative">
      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const StepIcon = step.icon;
          const isPassed = isStepPassed(step.id);
          const isCurrent = currentStep === step.id;
          const isClickable = canProceedToStep(step.id);

          return (
            <React.Fragment key={step.id}>
              <button
                onClick={() => onStepClick(step.id)}
                disabled={!isClickable}
                className={`relative z-10 flex flex-col items-center gap-2 transition-all ${
                  isClickable ? 'cursor-pointer' : 'cursor-not-allowed'
                }`}
                data-testid={`wizard-step-${step.id}`}
              >
                {/* Step Circle */}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                    isPassed
                      ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                      : isCurrent
                      ? 'bg-brand-500/10 border-brand-400 text-brand-400'
                      : 'bg-white/5 border-white/10 text-gray-500'
                  }`}
                >
                  {isPassed ? <Check className="w-4 h-4" /> : <StepIcon className="w-4 h-4" />}
                </div>

                {/* Step Info */}
                <div className="text-center">
                  <div
                    className={`text-[10px] font-bold mb-0.5 ${
                      isPassed ? 'text-brand-400' : isCurrent ? 'text-brand-400' : 'text-gray-600'
                    }`}
                  >
                    {step.id}/{STEPS.length}
                  </div>
                  <div
                    className={`text-xs font-medium ${
                      isPassed ? 'text-brand-400' : isCurrent ? 'text-gray-200' : 'text-gray-500'
                    }`}
                  >
                    {step.name}
                  </div>
                  <div
                    className={`text-[10px] ${
                      isCurrent || isPassed ? 'text-gray-400' : 'text-gray-600'
                    }`}
                  >
                    {step.description}
                  </div>
                </div>
              </button>

              {/* Connector Line */}
              {index < STEPS.length - 1 && (
                <div className="flex-1 h-0.5 mx-3 relative top-[-16px]">
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
};

export default WizardStepper;

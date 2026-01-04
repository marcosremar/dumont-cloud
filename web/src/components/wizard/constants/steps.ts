/**
 * Wizard Steps Definition
 */

import { Globe, Cpu, Shield, Rocket } from 'lucide-react';
import type { StepDefinition, WizardStep } from '../types/wizard.types';

export const WIZARD_STEPS: StepDefinition[] = [
  {
    id: 1,
    name: 'Region',
    icon: Globe,
    description: 'Location',
  },
  {
    id: 2,
    name: 'Hardware',
    icon: Cpu,
    description: 'GPU & performance',
  },
  {
    id: 3,
    name: 'Strategy',
    icon: Shield,
    description: 'Failover',
  },
  {
    id: 4,
    name: 'Provision',
    icon: Rocket,
    description: 'Connecting',
  },
];

export const TOTAL_STEPS = WIZARD_STEPS.length;

export function getStepById(id: WizardStep): StepDefinition | undefined {
  return WIZARD_STEPS.find((step) => step.id === id);
}

export function getNextStep(currentStep: WizardStep): WizardStep | null {
  if (currentStep >= TOTAL_STEPS) return null;
  return (currentStep + 1) as WizardStep;
}

export function getPrevStep(currentStep: WizardStep): WizardStep | null {
  if (currentStep <= 1) return null;
  return (currentStep - 1) as WizardStep;
}

export default WIZARD_STEPS;

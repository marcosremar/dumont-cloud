/**
 * WizardNavigation Component
 * Navigation buttons for the wizard (Next/Back/Submit)
 */

import React from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Zap,
  Loader2,
  X,
  Check,
} from 'lucide-react';
import { Button } from '../../ui/button';
import type { WizardStep, ProvisioningWinner } from '../types/wizard.types';

interface WizardNavigationProps {
  currentStep: WizardStep;
  canProceed: boolean;
  loading?: boolean;
  provisioningWinner?: ProvisioningWinner | null;
  onNext: () => void;
  onPrev: () => void;
  onCancel?: () => void;
  onComplete?: () => void;
}

export function WizardNavigation({
  currentStep,
  canProceed,
  loading = false,
  provisioningWinner,
  onNext,
  onPrev,
  onCancel,
  onComplete,
}: WizardNavigationProps) {
  // Provisioning step (Step 4)
  if (currentStep === 4) {
    return (
      <div className="flex items-center justify-between pt-4 border-t border-white/10">
        {/* Cancel Button */}
        <Button
          onClick={onCancel}
          variant="ghost"
          className="px-4 py-2 text-gray-400 hover:text-gray-200"
        >
          <X className="w-4 h-4 mr-1" />
          {provisioningWinner ? 'Buscar Outras' : 'Cancelar'}
        </Button>

        {/* Complete Button */}
        <button
          onClick={onComplete}
          disabled={!provisioningWinner}
          className="ta-btn ta-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="flex items-center gap-2">
            {provisioningWinner ? (
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
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between pt-4 border-t border-white/10">
      {/* Back Button */}
      {currentStep > 1 ? (
        <Button
          onClick={onPrev}
          variant="ghost"
          className="px-4 py-2 text-gray-400 hover:text-gray-200"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Voltar
        </Button>
      ) : (
        <div />
      )}

      {/* Next/Submit Button */}
      {currentStep < 3 ? (
        <button
          onClick={onNext}
          disabled={!canProceed}
          className="ta-btn ta-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="flex items-center gap-2">
            Próximo
            <ChevronRight className="w-4 h-4" />
          </span>
        </button>
      ) : (
        <button
          onClick={onNext}
          disabled={!canProceed || loading}
          className="ta-btn ta-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <span className="flex items-center gap-2">
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Iniciando...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Iniciar
              </>
            )}
          </span>
        </button>
      )}
    </div>
  );
}

export default WizardNavigation;

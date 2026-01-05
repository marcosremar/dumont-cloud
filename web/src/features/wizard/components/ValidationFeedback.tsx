/**
 * Validation Feedback Component
 *
 * Provides clear, visual feedback for form validation in Portuguese.
 * Includes quick-fix actions for common issues.
 */

import React from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Info,
  MapPin,
  Cpu,
  Shield,
  AlertTriangle,
  Zap,
  ArrowRight,
  RefreshCw,
  Globe,
  Lightbulb,
} from 'lucide-react';
import { WizardStep } from '../types';

// ============================================================================
// Types
// ============================================================================

export type ValidationStatus = 'valid' | 'invalid' | 'warning' | 'pending';

export interface QuickFixAction {
  label: string;
  action: () => void;
  icon?: React.ElementType;
}

export interface ValidationItem {
  step: WizardStep;
  field: string;
  message: string;
  status: ValidationStatus;
  suggestion?: string;
  quickFix?: QuickFixAction;
}

export interface ValidationFeedbackProps {
  items: ValidationItem[];
  showAll?: boolean;
  className?: string;
}

export interface StepValidationProps {
  step: WizardStep;
  isComplete: boolean;
  errors: string[];
  warnings?: string[];
  quickFixes?: QuickFixAction[];
  className?: string;
}

export interface ActionableValidationProps {
  step: WizardStep;
  issues: Array<{
    type: 'error' | 'warning' | 'info';
    message: string;
    suggestion?: string;
    quickFix?: QuickFixAction;
  }>;
  onGoToStep?: (step: WizardStep) => void;
  className?: string;
}

// ============================================================================
// Helpers
// ============================================================================

const getStepIcon = (step: WizardStep) => {
  switch (step) {
    case 1:
      return MapPin;
    case 2:
      return Cpu;
    case 3:
      return Shield;
    default:
      return Info;
  }
};

const getStepName = (step: WizardStep): string => {
  switch (step) {
    case 1:
      return 'Localização';
    case 2:
      return 'Hardware';
    case 3:
      return 'Estratégia';
    case 4:
      return 'Provisionamento';
    default:
      return 'Etapa';
  }
};

const getStatusConfig = (status: ValidationStatus) => {
  switch (status) {
    case 'valid':
      return {
        Icon: CheckCircle2,
        bgClass: 'bg-emerald-500/10',
        borderClass: 'border-emerald-500/20',
        iconClass: 'text-emerald-400',
        textClass: 'text-emerald-300',
      };
    case 'invalid':
      return {
        Icon: AlertCircle,
        bgClass: 'bg-red-500/10',
        borderClass: 'border-red-500/20',
        iconClass: 'text-red-400',
        textClass: 'text-red-300',
      };
    case 'warning':
      return {
        Icon: AlertTriangle,
        bgClass: 'bg-amber-500/10',
        borderClass: 'border-amber-500/20',
        iconClass: 'text-amber-400',
        textClass: 'text-amber-300',
      };
    case 'pending':
    default:
      return {
        Icon: Info,
        bgClass: 'bg-gray-500/10',
        borderClass: 'border-gray-500/20',
        iconClass: 'text-gray-400',
        textClass: 'text-gray-300',
      };
  }
};

// ============================================================================
// Validation Messages in Portuguese
// ============================================================================

export const VALIDATION_MESSAGES = {
  location: {
    required: 'Selecione pelo menos uma região ou país para sua máquina',
    suggestion: 'Dica: Escolha regiões próximas para menor latência',
  },
  hardware: {
    required: 'Escolha o nível de performance desejado',
    noMachines: 'Nenhuma máquina disponível nesta região com este tier',
    suggestion: 'Dica: Para testes, "Experimentar" é mais econômico',
  },
  strategy: {
    required: 'Selecione uma estratégia de failover',
    noFailoverWarning: 'Sem failover: você pode perder todos os dados em caso de falha',
    suggestion: 'Dica: "Snapshot Only" oferece proteção básica sem custo extra',
  },
  balance: {
    insufficient: (required: number, current: number) =>
      `Saldo insuficiente: você tem $${current.toFixed(2)}, precisa de pelo menos $${required.toFixed(2)}`,
    suggestion: 'Adicione créditos para continuar',
  },
  ports: {
    duplicate: 'Existem portas duplicadas na configuração',
    invalid: 'Algumas portas têm formato inválido',
    suggestion: 'Use números entre 1 e 65535',
  },
  docker: {
    empty: 'Informe uma imagem Docker válida',
    suggestion: 'Ex: pytorch/pytorch:latest',
  },
};

// ============================================================================
// Sub-components
// ============================================================================

interface ValidationItemRowProps {
  item: ValidationItem;
}

const ValidationItemRow: React.FC<ValidationItemRowProps> = ({ item }) => {
  const config = getStatusConfig(item.status);
  const StepIcon = getStepIcon(item.step);
  const StatusIcon = config.Icon;
  const QuickFixIcon = item.quickFix?.icon || Zap;

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border ${config.bgClass} ${config.borderClass}`}
    >
      <div className="flex items-center gap-2">
        <StepIcon className="w-4 h-4 text-gray-500" />
        <StatusIcon className={`w-4 h-4 ${config.iconClass}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs text-gray-500">{getStepName(item.step)}</span>
          <span className="text-xs text-gray-600">•</span>
          <span className="text-xs text-gray-400">{item.field}</span>
        </div>
        <p className={`text-sm ${config.textClass}`}>{item.message}</p>
        {item.suggestion && (
          <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
            <Lightbulb className="w-3 h-3" />
            {item.suggestion}
          </p>
        )}
        {/* Quick Fix Button */}
        {item.quickFix && (
          <button
            onClick={item.quickFix.action}
            className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-brand-500/20 text-brand-400 border border-brand-500/30 hover:bg-brand-500/30 transition-all"
          >
            <QuickFixIcon className="w-3 h-3" />
            {item.quickFix.label}
          </button>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Quick Fix Button Component
// ============================================================================

interface QuickFixButtonProps {
  quickFix: QuickFixAction;
  variant?: 'primary' | 'secondary';
}

const QuickFixButton: React.FC<QuickFixButtonProps> = ({ quickFix, variant = 'primary' }) => {
  const Icon = quickFix.icon || Zap;

  if (variant === 'secondary') {
    return (
      <button
        onClick={quickFix.action}
        className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] text-gray-400 hover:text-brand-400 transition-colors"
      >
        <Icon className="w-3 h-3" />
        {quickFix.label}
      </button>
    );
  }

  return (
    <button
      onClick={quickFix.action}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-brand-500/20 text-brand-400 border border-brand-500/30 hover:bg-brand-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all"
    >
      <Icon className="w-3.5 h-3.5" />
      {quickFix.label}
      <ArrowRight className="w-3 h-3" />
    </button>
  );
};

// ============================================================================
// Main Components
// ============================================================================

/**
 * Displays a list of validation items
 */
export const ValidationFeedback: React.FC<ValidationFeedbackProps> = ({
  items,
  showAll = false,
  className = '',
}) => {
  const displayItems = showAll
    ? items
    : items.filter((item) => item.status === 'invalid' || item.status === 'warning');

  if (displayItems.length === 0) return null;

  return (
    <div className={`space-y-2 ${className}`}>
      {displayItems.map((item, index) => (
        <ValidationItemRow key={`${item.step}-${item.field}-${index}`} item={item} />
      ))}
    </div>
  );
};

/**
 * Inline validation indicator for a single field
 */
export interface InlineValidationProps {
  isValid: boolean;
  message?: string;
  className?: string;
}

export const InlineValidation: React.FC<InlineValidationProps> = ({
  isValid,
  message,
  className = '',
}) => {
  if (isValid || !message) return null;

  return (
    <div className={`flex items-center gap-1.5 mt-1.5 ${className}`}>
      <AlertCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
      <span className="text-xs text-red-400">{message}</span>
    </div>
  );
};

/**
 * Step completion indicator with validation status
 */
export const StepValidation: React.FC<StepValidationProps> = ({
  step,
  isComplete,
  errors,
  warnings = [],
  className = '',
}) => {
  const StepIcon = getStepIcon(step);
  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0;

  const status: ValidationStatus = isComplete
    ? hasWarnings
      ? 'warning'
      : 'valid'
    : hasErrors
    ? 'invalid'
    : 'pending';

  const config = getStatusConfig(status);
  const StatusIcon = config.Icon;

  return (
    <div className={`${className}`}>
      <div className="flex items-center gap-2 mb-2">
        <div
          className={`w-6 h-6 rounded-full flex items-center justify-center ${config.bgClass}`}
        >
          <StepIcon className={`w-3.5 h-3.5 ${config.iconClass}`} />
        </div>
        <span className="text-sm font-medium text-gray-300">{getStepName(step)}</span>
        <StatusIcon className={`w-4 h-4 ${config.iconClass}`} />
      </div>

      {(hasErrors || hasWarnings) && (
        <div className="pl-8 space-y-1">
          {errors.map((error, idx) => (
            <p key={idx} className="text-xs text-red-400 flex items-start gap-1.5">
              <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              {error}
            </p>
          ))}
          {warnings.map((warning, idx) => (
            <p key={idx} className="text-xs text-amber-400 flex items-start gap-1.5">
              <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              {warning}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Summary validation box for all steps
 */
export interface ValidationSummaryProps {
  steps: Array<{
    step: WizardStep;
    isComplete: boolean;
    errors: string[];
    warnings?: string[];
  }>;
  className?: string;
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({
  steps,
  className = '',
}) => {
  const totalErrors = steps.reduce((sum, s) => sum + s.errors.length, 0);
  const totalWarnings = steps.reduce((sum, s) => sum + (s.warnings?.length || 0), 0);
  const allComplete = steps.every((s) => s.isComplete);

  if (allComplete && totalErrors === 0 && totalWarnings === 0) {
    return (
      <div
        className={`flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 ${className}`}
      >
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        <span className="text-sm text-emerald-300">
          Tudo pronto! Você pode iniciar o provisionamento.
        </span>
      </div>
    );
  }

  return (
    <div
      className={`p-4 rounded-lg bg-gray-800/50 border border-white/10 space-y-3 ${className}`}
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">Validação</h4>
        <div className="flex items-center gap-3 text-xs">
          {totalErrors > 0 && (
            <span className="flex items-center gap-1 text-red-400">
              <AlertCircle className="w-3 h-3" />
              {totalErrors} {totalErrors === 1 ? 'erro' : 'erros'}
            </span>
          )}
          {totalWarnings > 0 && (
            <span className="flex items-center gap-1 text-amber-400">
              <AlertTriangle className="w-3 h-3" />
              {totalWarnings} {totalWarnings === 1 ? 'aviso' : 'avisos'}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((stepData) => (
          <StepValidation
            key={stepData.step}
            step={stepData.step}
            isComplete={stepData.isComplete}
            errors={stepData.errors}
            warnings={stepData.warnings}
          />
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Actionable Validation Component (with Quick Fixes)
// ============================================================================

export const ActionableValidation: React.FC<ActionableValidationProps> = ({
  step,
  issues,
  onGoToStep,
  className = '',
}) => {
  const StepIcon = getStepIcon(step);

  if (issues.length === 0) return null;

  const errorCount = issues.filter((i) => i.type === 'error').length;
  const warningCount = issues.filter((i) => i.type === 'warning').length;

  return (
    <div className={`p-4 rounded-xl bg-gray-800/50 border border-white/10 space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-red-500/10 flex items-center justify-center">
            <StepIcon className="w-4 h-4 text-red-400" />
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-200">{getStepName(step)}</h4>
            <div className="flex items-center gap-2 text-[10px]">
              {errorCount > 0 && (
                <span className="text-red-400">
                  {errorCount} {errorCount === 1 ? 'erro' : 'erros'}
                </span>
              )}
              {warningCount > 0 && (
                <span className="text-amber-400">
                  {warningCount} {warningCount === 1 ? 'aviso' : 'avisos'}
                </span>
              )}
            </div>
          </div>
        </div>
        {onGoToStep && (
          <button
            onClick={() => onGoToStep(step)}
            className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
          >
            Ir para etapa
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Issues List */}
      <div className="space-y-2">
        {issues.map((issue, idx) => {
          const Icon = issue.type === 'error' ? AlertCircle : issue.type === 'warning' ? AlertTriangle : Info;
          const colorClass = issue.type === 'error' ? 'text-red-400' : issue.type === 'warning' ? 'text-amber-400' : 'text-gray-400';
          const bgClass = issue.type === 'error' ? 'bg-red-500/5' : issue.type === 'warning' ? 'bg-amber-500/5' : 'bg-gray-500/5';

          return (
            <div
              key={idx}
              className={`p-3 rounded-lg ${bgClass} border border-white/5`}
            >
              <div className="flex items-start gap-2">
                <Icon className={`w-4 h-4 ${colorClass} mt-0.5 flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${colorClass}`}>{issue.message}</p>
                  {issue.suggestion && (
                    <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                      <Lightbulb className="w-3 h-3" />
                      {issue.suggestion}
                    </p>
                  )}
                  {issue.quickFix && (
                    <button
                      onClick={issue.quickFix.action}
                      className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-brand-500/20 text-brand-400 border border-brand-500/30 hover:bg-brand-500/30 transition-all"
                    >
                      {issue.quickFix.icon ? (
                        <issue.quickFix.icon className="w-3 h-3" />
                      ) : (
                        <Zap className="w-3 h-3" />
                      )}
                      {issue.quickFix.label}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// Compact Inline Quick Fix
// ============================================================================

export interface InlineQuickFixProps {
  message: string;
  quickFix: QuickFixAction;
  variant?: 'error' | 'warning' | 'info';
  className?: string;
}

export const InlineQuickFix: React.FC<InlineQuickFixProps> = ({
  message,
  quickFix,
  variant = 'error',
  className = '',
}) => {
  const Icon = variant === 'error' ? AlertCircle : variant === 'warning' ? AlertTriangle : Info;
  const QuickFixIcon = quickFix.icon || Zap;

  const colors = {
    error: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      icon: 'text-red-400',
      text: 'text-red-300',
    },
    warning: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      icon: 'text-amber-400',
      text: 'text-amber-300',
    },
    info: {
      bg: 'bg-gray-500/10',
      border: 'border-gray-500/20',
      icon: 'text-gray-400',
      text: 'text-gray-300',
    },
  };

  const c = colors[variant];

  return (
    <div className={`flex items-center justify-between p-2 rounded-lg ${c.bg} border ${c.border} ${className}`}>
      <div className="flex items-center gap-2">
        <Icon className={`w-3.5 h-3.5 ${c.icon}`} />
        <span className={`text-xs ${c.text}`}>{message}</span>
      </div>
      <button
        onClick={quickFix.action}
        className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 transition-all"
      >
        <QuickFixIcon className="w-2.5 h-2.5" />
        {quickFix.label}
      </button>
    </div>
  );
};

export default ValidationFeedback;

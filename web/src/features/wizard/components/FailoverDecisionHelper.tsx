/**
 * Failover Decision Helper Component
 *
 * Helps users choose the right failover strategy with examples,
 * comparisons, and use-case recommendations.
 */

import React, { useState } from 'react';
import {
  X,
  Shield,
  Clock,
  DollarSign,
  Database,
  HardDrive,
  Zap,
  Server,
  AlertTriangle,
  CheckCircle2,
  Info,
  ChevronRight,
  Sparkles,
  Book,
  Target,
  ArrowRight,
  Brain,
} from 'lucide-react';
import { FailoverStrategyId, FailoverStrategy } from '../types';
import { FAILOVER_STRATEGIES, getStrategyById } from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface FailoverDecisionHelperProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectStrategy: (strategyId: FailoverStrategyId) => void;
  currentStrategy: FailoverStrategyId;
}

interface UseCase {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  recommendedStrategy: FailoverStrategyId;
  examples: string[];
  dataLoss: 'none' | 'minimal' | 'possible' | 'likely';
  priority: 'cost' | 'recovery' | 'reliability';
}

// ============================================================================
// Use Cases Data
// ============================================================================

const USE_CASES: UseCase[] = [
  {
    id: 'testing',
    name: 'Testes & Experimentação',
    description: 'Testes rápidos, provas de conceito, aprendizado',
    icon: Book,
    recommendedStrategy: 'no_failover',
    examples: [
      'Testar um modelo novo por algumas horas',
      'Experimentar frameworks diferentes',
      'Cursos e tutoriais de ML',
    ],
    dataLoss: 'likely',
    priority: 'cost',
  },
  {
    id: 'development',
    name: 'Desenvolvimento Diário',
    description: 'Coding, debugging, desenvolvimento iterativo',
    icon: Target,
    recommendedStrategy: 'snapshot_only',
    examples: [
      'Desenvolvimento de aplicações ML',
      'Debugging de modelos',
      'Trabalho diário com código versionado (git)',
    ],
    dataLoss: 'minimal',
    priority: 'cost',
  },
  {
    id: 'training',
    name: 'Fine-tuning & Training',
    description: 'Treinamento de modelos que leva horas/dias',
    icon: Brain,
    recommendedStrategy: 'cpu_standby_only',
    examples: [
      'Fine-tuning de LLMs (LoRA, PEFT)',
      'Treinamento de modelos de imagem',
      'Experimentos que não podem ser reiniciados',
    ],
    dataLoss: 'none',
    priority: 'reliability',
  },
  {
    id: 'production',
    name: 'Produção 24/7',
    description: 'APIs em produção, serviços críticos',
    icon: Sparkles,
    recommendedStrategy: 'vast_warmpool',
    examples: [
      'API de inferência em produção',
      'Chatbots com SLA',
      'Sistemas que não podem ficar offline',
    ],
    dataLoss: 'none',
    priority: 'recovery',
  },
];

const DATA_LOSS_LABELS = {
  none: { label: 'Sem perda', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  minimal: { label: 'Mínima', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  possible: { label: 'Possível', color: 'text-amber-400', bg: 'bg-amber-500/10' },
  likely: { label: 'Provável', color: 'text-red-400', bg: 'bg-red-500/10' },
};

// ============================================================================
// Sub-components
// ============================================================================

interface UseCaseCardProps {
  useCase: UseCase;
  isSelected: boolean;
  onSelect: () => void;
}

const UseCaseCard: React.FC<UseCaseCardProps> = ({ useCase, isSelected, onSelect }) => {
  const Icon = useCase.icon;
  const dataLoss = DATA_LOSS_LABELS[useCase.dataLoss];

  return (
    <button
      onClick={onSelect}
      className={`w-full p-4 rounded-xl border text-left transition-all ${
        isSelected
          ? 'bg-brand-500/10 border-brand-500/50'
          : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-white/10 text-gray-400'
          }`}
        >
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4
              className={`text-sm font-medium ${
                isSelected ? 'text-brand-400' : 'text-gray-200'
              }`}
            >
              {useCase.name}
            </h4>
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full ${dataLoss.bg} ${dataLoss.color}`}
            >
              {dataLoss.label}
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-2">{useCase.description}</p>
          <div className="flex flex-wrap gap-1">
            {useCase.examples.slice(0, 2).map((example, idx) => (
              <span
                key={idx}
                className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-gray-500"
              >
                {example}
              </span>
            ))}
          </div>
        </div>
      </div>
    </button>
  );
};

interface StrategyComparisonProps {
  strategies: FailoverStrategy[];
  currentStrategy: FailoverStrategyId;
  recommendedStrategy: FailoverStrategyId;
  onSelect: (id: FailoverStrategyId) => void;
}

const StrategyComparison: React.FC<StrategyComparisonProps> = ({
  strategies,
  currentStrategy,
  recommendedStrategy,
  onSelect,
}) => {
  return (
    <div className="space-y-2">
      {strategies.map((strategy) => {
        const isRecommended = strategy.id === recommendedStrategy;
        const isCurrent = strategy.id === currentStrategy;
        const Icon = strategy.icon;

        return (
          <button
            key={strategy.id}
            onClick={() => onSelect(strategy.id as FailoverStrategyId)}
            disabled={!strategy.available}
            className={`w-full p-3 rounded-lg border text-left transition-all ${
              isCurrent
                ? 'bg-brand-500/10 border-brand-500/50'
                : strategy.available
                ? 'bg-white/5 border-white/10 hover:bg-white/[0.07]'
                : 'bg-white/[0.02] border-white/5 opacity-50 cursor-not-allowed'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Icon
                  className={`w-5 h-5 ${
                    isCurrent ? 'text-brand-400' : 'text-gray-400'
                  }`}
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-sm font-medium ${
                        isCurrent ? 'text-brand-400' : 'text-gray-200'
                      }`}
                    >
                      {strategy.name}
                    </span>
                    {isRecommended && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                        Recomendado
                      </span>
                    )}
                    {strategy.comingSoon && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-500/20 text-gray-400">
                        Em breve
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-[10px] text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {strategy.recoveryTime}
                    </span>
                    <span className="flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      {strategy.dataLoss}
                    </span>
                    <span className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      {strategy.costHour || strategy.costMonth || 'Grátis'}
                    </span>
                  </div>
                </div>
              </div>
              {isCurrent && <CheckCircle2 className="w-5 h-5 text-brand-400" />}
            </div>
          </button>
        );
      })}
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const FailoverDecisionHelper: React.FC<FailoverDecisionHelperProps> = ({
  isOpen,
  onClose,
  onSelectStrategy,
  currentStrategy,
}) => {
  const [selectedUseCase, setSelectedUseCase] = useState<string | null>(null);

  const selectedUseCaseData = USE_CASES.find((uc) => uc.id === selectedUseCase);
  const availableStrategies = FAILOVER_STRATEGIES.filter((s) => s.available || s.comingSoon);

  const handleSelectStrategy = (strategyId: FailoverStrategyId) => {
    onSelectStrategy(strategyId);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-2xl bg-gray-900 border border-white/10 shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/20 flex items-center justify-center">
              <Shield className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-100">
                Escolher Estratégia de Failover
              </h2>
              <p className="text-xs text-gray-500">
                Responda algumas perguntas para encontrar a melhor opção
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {/* Step 1: Use Case Selection */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400">
                1
              </div>
              <h3 className="text-sm font-medium text-gray-200">
                O que você vai fazer com a máquina?
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {USE_CASES.map((useCase) => (
                <UseCaseCard
                  key={useCase.id}
                  useCase={useCase}
                  isSelected={selectedUseCase === useCase.id}
                  onSelect={() => setSelectedUseCase(useCase.id)}
                />
              ))}
            </div>
          </div>

          {/* Step 2: Strategy Recommendation */}
          {selectedUseCaseData && (
            <div className="animate-fadeIn">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400">
                  2
                </div>
                <h3 className="text-sm font-medium text-gray-200">
                  Estratégia recomendada para {selectedUseCaseData.name}
                </h3>
              </div>

              {/* Recommendation Box */}
              <div className="mb-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <div className="flex items-start gap-3">
                  <Zap className="w-5 h-5 text-emerald-400 mt-0.5" />
                  <div>
                    <p className="text-sm text-emerald-300">
                      Para <strong>{selectedUseCaseData.name.toLowerCase()}</strong>, recomendamos{' '}
                      <strong>
                        {getStrategyById(selectedUseCaseData.recommendedStrategy)?.name}
                      </strong>
                    </p>
                    <p className="text-xs text-emerald-400/70 mt-1">
                      {getStrategyById(selectedUseCaseData.recommendedStrategy)?.howItWorks}
                    </p>
                  </div>
                </div>
              </div>

              {/* All Options */}
              <StrategyComparison
                strategies={availableStrategies}
                currentStrategy={currentStrategy}
                recommendedStrategy={selectedUseCaseData.recommendedStrategy}
                onSelect={handleSelectStrategy}
              />
            </div>
          )}

          {/* Info Box */}
          {!selectedUseCaseData && (
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-sm text-gray-300">
                    Selecione seu caso de uso acima para ver a estratégia recomendada.
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Cada estratégia tem trade-offs entre custo, tempo de recuperação e
                    proteção de dados.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 bg-gray-800/30 flex items-center justify-between">
          <div className="flex items-center gap-4 text-[10px] text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Tempo de recuperação
            </span>
            <span className="flex items-center gap-1">
              <Database className="w-3 h-3" />
              Perda de dados
            </span>
            <span className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              Custo adicional
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Fechar
            </button>
            {selectedUseCaseData && (
              <button
                onClick={() => {
                  handleSelectStrategy(selectedUseCaseData.recommendedStrategy);
                  onClose();
                }}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-gradient-to-r from-brand-500 to-brand-600 text-white hover:shadow-brand-500/25 hover:shadow-lg transition-all"
              >
                <span className="flex items-center gap-2">
                  Usar {getStrategyById(selectedUseCaseData.recommendedStrategy)?.name}
                  <ArrowRight className="w-4 h-4" />
                </span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FailoverDecisionHelper;

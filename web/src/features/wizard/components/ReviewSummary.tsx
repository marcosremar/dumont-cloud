/**
 * Review Summary Component
 *
 * Shows a complete summary of all wizard selections before provisioning.
 * Allows users to review and edit any section.
 */

import React from 'react';
import {
  MapPin,
  Cpu,
  Shield,
  DollarSign,
  Clock,
  Server,
  Globe,
  MemoryStick,
  Database,
  CheckCircle2,
  AlertTriangle,
  Edit2,
  Zap,
  Container,
  Network,
  TrendingUp,
  Calendar,
} from 'lucide-react';
import {
  Location,
  TierName,
  MachineOffer,
  FailoverStrategyId,
  PortConfig,
  WizardStep,
  EstimatedCost,
} from '../types';
import { getStrategyById } from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface ReviewSummaryProps {
  selectedLocation: Location | null;
  selectedTier: TierName | null;
  selectedMachine: MachineOffer | null;
  failoverStrategy: FailoverStrategyId;
  dockerImage: string;
  exposedPorts: PortConfig[];
  estimatedCost: EstimatedCost;
  onEditSection?: (step: WizardStep) => void;
  className?: string;
}

interface SummaryCardProps {
  title: string;
  icon: React.ElementType;
  step: WizardStep;
  isComplete: boolean;
  hasWarning?: boolean;
  warningMessage?: string;
  onEdit?: () => void;
  children: React.ReactNode;
}

// ============================================================================
// Sub-components
// ============================================================================

const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  icon: Icon,
  step,
  isComplete,
  hasWarning,
  warningMessage,
  onEdit,
  children,
}) => (
  <div
    className={`p-4 rounded-xl border ${
      hasWarning
        ? 'bg-amber-500/5 border-amber-500/20'
        : isComplete
        ? 'bg-white/5 border-white/10'
        : 'bg-red-500/5 border-red-500/20'
    }`}
  >
    {/* Header */}
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            hasWarning
              ? 'bg-amber-500/20'
              : isComplete
              ? 'bg-brand-500/20'
              : 'bg-red-500/20'
          }`}
        >
          <Icon
            className={`w-4 h-4 ${
              hasWarning
                ? 'text-amber-400'
                : isComplete
                ? 'text-brand-400'
                : 'text-red-400'
            }`}
          />
        </div>
        <span className="text-sm font-medium text-gray-200">{title}</span>
        {isComplete && !hasWarning && (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        )}
        {hasWarning && <AlertTriangle className="w-4 h-4 text-amber-400" />}
      </div>
      {onEdit && (
        <button
          onClick={onEdit}
          className="px-2 py-1 text-xs text-gray-400 hover:text-brand-400 hover:bg-white/5 rounded transition-colors flex items-center gap-1"
        >
          <Edit2 className="w-3 h-3" />
          Editar
        </button>
      )}
    </div>

    {/* Content */}
    <div className="pl-10">{children}</div>

    {/* Warning */}
    {hasWarning && warningMessage && (
      <div className="mt-3 pl-10 flex items-start gap-2">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
        <span className="text-xs text-amber-400/80">{warningMessage}</span>
      </div>
    )}
  </div>
);

interface DetailRowProps {
  icon: React.ElementType;
  label: string;
  value: string;
  subValue?: string;
  highlight?: boolean;
}

const DetailRow: React.FC<DetailRowProps> = ({
  icon: Icon,
  label,
  value,
  subValue,
  highlight,
}) => (
  <div className="flex items-center justify-between py-1.5">
    <div className="flex items-center gap-2 text-gray-400">
      <Icon className="w-3.5 h-3.5" />
      <span className="text-xs">{label}</span>
    </div>
    <div className="text-right">
      <span
        className={`text-sm ${highlight ? 'text-brand-400 font-medium' : 'text-gray-200'}`}
      >
        {value}
      </span>
      {subValue && <span className="text-xs text-gray-500 ml-1">{subValue}</span>}
    </div>
  </div>
);

// ============================================================================
// Main Component
// ============================================================================

export const ReviewSummary: React.FC<ReviewSummaryProps> = ({
  selectedLocation,
  selectedTier,
  selectedMachine,
  failoverStrategy,
  dockerImage,
  exposedPorts,
  estimatedCost,
  onEditSection,
  className = '',
}) => {
  const strategyData = getStrategyById(failoverStrategy);
  const hasNoFailover = failoverStrategy === 'no_failover';
  const hasLocation = !!selectedLocation;
  const hasMachine = !!selectedMachine;
  const hasStrategy = !!failoverStrategy;

  const formatCost = (value: number) => {
    if (value < 0.01 && value > 0) return '<$0.01';
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
    return `$${value.toFixed(2)}`;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500/20 to-purple-500/20 flex items-center justify-center">
          <Zap className="w-6 h-6 text-brand-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-100">Revisão Final</h3>
          <p className="text-xs text-gray-500">
            Revise suas seleções antes de iniciar o provisionamento
          </p>
        </div>
      </div>

      {/* Location Summary */}
      <SummaryCard
        title="Localização"
        icon={MapPin}
        step={1}
        isComplete={hasLocation}
        onEdit={onEditSection ? () => onEditSection(1) : undefined}
      >
        {hasLocation ? (
          <div className="space-y-1">
            <DetailRow
              icon={Globe}
              label="Região"
              value={selectedLocation.name}
              highlight
            />
            <DetailRow
              icon={MapPin}
              label="Códigos"
              value={selectedLocation.codes.join(', ')}
            />
          </div>
        ) : (
          <p className="text-sm text-red-400">Nenhuma localização selecionada</p>
        )}
      </SummaryCard>

      {/* Hardware Summary */}
      <SummaryCard
        title="Hardware"
        icon={Cpu}
        step={2}
        isComplete={hasMachine}
        onEdit={onEditSection ? () => onEditSection(2) : undefined}
      >
        {hasMachine ? (
          <div className="space-y-1">
            <DetailRow
              icon={Cpu}
              label="GPU"
              value={selectedMachine.gpu_name}
              subValue={`x${selectedMachine.num_gpus}`}
              highlight
            />
            <DetailRow
              icon={MemoryStick}
              label="VRAM"
              value={`${selectedMachine.gpu_ram}GB`}
            />
            <DetailRow
              icon={Server}
              label="Tier"
              value={selectedTier || 'N/A'}
            />
            <DetailRow
              icon={DollarSign}
              label="Custo/hora"
              value={`$${selectedMachine.dph_total.toFixed(2)}`}
            />
            {selectedMachine.provider && (
              <DetailRow
                icon={Globe}
                label="Provedor"
                value={selectedMachine.provider}
              />
            )}
          </div>
        ) : (
          <p className="text-sm text-red-400">Nenhuma máquina selecionada</p>
        )}
      </SummaryCard>

      {/* Strategy Summary */}
      <SummaryCard
        title="Estratégia de Failover"
        icon={Shield}
        step={3}
        isComplete={hasStrategy}
        hasWarning={hasNoFailover}
        warningMessage="Sem failover: você pode perder todos os dados em caso de falha da máquina"
        onEdit={onEditSection ? () => onEditSection(3) : undefined}
      >
        {strategyData ? (
          <div className="space-y-1">
            <DetailRow
              icon={Shield}
              label="Estratégia"
              value={strategyData.name}
              highlight
            />
            <DetailRow
              icon={Clock}
              label="Recuperação"
              value={strategyData.recoveryTime}
            />
            <DetailRow
              icon={Database}
              label="Perda de Dados"
              value={strategyData.dataLoss}
            />
            {(strategyData.costHour || strategyData.costMonth) && (
              <DetailRow
                icon={DollarSign}
                label="Custo Adicional"
                value={strategyData.costHour || strategyData.costMonth || 'Grátis'}
              />
            )}
          </div>
        ) : (
          <p className="text-sm text-red-400">Nenhuma estratégia selecionada</p>
        )}
      </SummaryCard>

      {/* Docker & Ports Summary */}
      <SummaryCard
        title="Configuração de Container"
        icon={Container}
        step={3}
        isComplete={!!dockerImage}
        onEdit={onEditSection ? () => onEditSection(3) : undefined}
      >
        <div className="space-y-1">
          <DetailRow
            icon={Container}
            label="Imagem Docker"
            value={dockerImage || 'pytorch/pytorch:latest'}
            highlight
          />
          <DetailRow
            icon={Network}
            label="Portas Expostas"
            value={exposedPorts.length > 0
              ? exposedPorts.map((p) => `${p.port}/${p.protocol}`).join(', ')
              : '22/TCP (SSH)'
            }
          />
        </div>
      </SummaryCard>

      {/* Cost Summary */}
      <div className="p-4 rounded-xl bg-gradient-to-br from-brand-500/10 to-purple-500/10 border border-brand-500/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-brand-400" />
            </div>
            <span className="text-sm font-medium text-gray-200">Custo Total Estimado</span>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold text-brand-400">
              {formatCost(estimatedCost.totalMonthly)}
            </span>
            <span className="text-sm text-gray-400">/mês</span>
          </div>
        </div>

        <div className="pl-10 space-y-2 border-t border-white/10 pt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Por hora
            </span>
            <span className="text-gray-200">{formatCost(estimatedCost.totalHourly)}/h</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400 flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              Por dia
            </span>
            <span className="text-gray-200">{formatCost(estimatedCost.daily)}/dia</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Por ano
            </span>
            <span className="text-gray-200">{formatCost(estimatedCost.totalMonthly * 12)}/ano</span>
          </div>
        </div>

        {/* Cost Breakdown */}
        <div className="mt-3 pt-3 border-t border-white/10 grid grid-cols-2 gap-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-gray-500">GPU</span>
            <span className="text-gray-300">{formatCost(estimatedCost.monthly)}/mês</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Failover</span>
            <span className={estimatedCost.failoverMonthly > 0 ? 'text-gray-300' : 'text-gray-600'}>
              {estimatedCost.failoverMonthly > 0
                ? `+${formatCost(estimatedCost.failoverMonthly)}/mês`
                : '$0'
              }
            </span>
          </div>
        </div>
      </div>

      {/* Ready Status */}
      {hasLocation && hasMachine && hasStrategy && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          <span className="text-sm text-emerald-300">
            Tudo pronto! Você pode iniciar o provisionamento.
          </span>
        </div>
      )}
    </div>
  );
};

export default ReviewSummary;

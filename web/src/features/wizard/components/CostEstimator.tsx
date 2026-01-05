/**
 * Cost Estimator Component
 *
 * Shows a detailed breakdown of estimated costs including GPU, failover, and total.
 * Includes a compact floating variant for sticky sidebar display.
 */

import React, { useState } from 'react';
import {
  DollarSign,
  Calculator,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
  Cpu,
  Shield,
  Clock,
  Calendar,
  X,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { EstimatedCost } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface CostEstimatorProps {
  cost: EstimatedCost;
  gpuName?: string;
  failoverName?: string;
  showBreakdown?: boolean;
  className?: string;
}

export interface FloatingCostCardProps {
  cost: EstimatedCost;
  gpuName?: string;
  failoverName?: string;
  locationName?: string;
  isVisible?: boolean;
  onClose?: () => void;
  className?: string;
}

type Period = 'hourly' | 'daily' | 'weekly' | 'monthly';

// ============================================================================
// Sub-components
// ============================================================================

interface PeriodButtonProps {
  period: Period;
  label: string;
  isActive: boolean;
  onClick: () => void;
}

const PeriodButton: React.FC<PeriodButtonProps> = ({ label, isActive, onClick }) => (
  <button
    onClick={onClick}
    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
      isActive
        ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
        : 'bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10 hover:text-gray-300'
    }`}
  >
    {label}
  </button>
);

// ============================================================================
// Helpers
// ============================================================================

const formatCurrency = (value: number): string => {
  if (value < 0.01 && value > 0) return '<$0.01';
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
  return `$${value.toFixed(2)}`;
};

const getPeriodMultiplier = (period: Period): { gpu: number; total: number } => {
  switch (period) {
    case 'hourly':
      return { gpu: 1, total: 1 };
    case 'daily':
      return { gpu: 24, total: 24 };
    case 'weekly':
      return { gpu: 24 * 7, total: 24 * 7 };
    case 'monthly':
      return { gpu: 24 * 30, total: 24 * 30 };
  }
};

const getPeriodLabel = (period: Period): string => {
  switch (period) {
    case 'hourly':
      return '/hora';
    case 'daily':
      return '/dia';
    case 'weekly':
      return '/semana';
    case 'monthly':
      return '/mês';
  }
};

// ============================================================================
// Main Component
// ============================================================================

export const CostEstimator: React.FC<CostEstimatorProps> = ({
  cost,
  gpuName,
  failoverName,
  showBreakdown = true,
  className = '',
}) => {
  const [selectedPeriod, setSelectedPeriod] = useState<Period>('monthly');
  const [isExpanded, setIsExpanded] = useState(false);

  const multiplier = getPeriodMultiplier(selectedPeriod);
  const periodLabel = getPeriodLabel(selectedPeriod);

  // Calculate costs for selected period
  const gpuCost = cost.hourly * multiplier.gpu;
  const failoverCost = selectedPeriod === 'monthly'
    ? cost.failoverMonthly
    : cost.failoverHourly * multiplier.total;
  const totalCost = gpuCost + failoverCost;

  // Determine if costs are significant
  const isExpensive = cost.totalMonthly > 100;
  const hasNoFailover = cost.failoverHourly === 0 && cost.failoverMonthly === 0;

  return (
    <div className={`rounded-xl bg-gradient-to-br from-white/[0.08] to-white/[0.02] border border-white/10 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center">
            <Calculator className="w-4 h-4 text-brand-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-200">Custo Estimado</h3>
            <p className="text-[10px] text-gray-500">Baseado no uso contínuo (24/7)</p>
          </div>
        </div>

        {/* Period Selector */}
        <div className="flex gap-1">
          <PeriodButton
            period="hourly"
            label="Hora"
            isActive={selectedPeriod === 'hourly'}
            onClick={() => setSelectedPeriod('hourly')}
          />
          <PeriodButton
            period="daily"
            label="Dia"
            isActive={selectedPeriod === 'daily'}
            onClick={() => setSelectedPeriod('daily')}
          />
          <PeriodButton
            period="monthly"
            label="Mês"
            isActive={selectedPeriod === 'monthly'}
            onClick={() => setSelectedPeriod('monthly')}
          />
        </div>
      </div>

      {/* Main Cost Display */}
      <div className="px-4 py-4">
        <div className="flex items-end justify-between mb-3">
          <div>
            <span className="text-3xl font-bold text-gray-100">{formatCurrency(totalCost)}</span>
            <span className="text-sm text-gray-400 ml-1">{periodLabel}</span>
          </div>
          {isExpensive && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-amber-500/10 border border-amber-500/20">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span className="text-[10px] text-amber-400">Custo elevado</span>
            </div>
          )}
        </div>

        {/* Breakdown Toggle */}
        {showBreakdown && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between py-2 text-xs text-gray-400 hover:text-gray-300 transition-colors"
          >
            <span>Ver detalhamento</span>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        )}

        {/* Expanded Breakdown */}
        {showBreakdown && isExpanded && (
          <div className="pt-3 border-t border-white/10 space-y-3 animate-fadeIn">
            {/* GPU Cost */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-brand-500" />
                <span className="text-xs text-gray-400">
                  GPU {gpuName || 'selecionada'}
                </span>
              </div>
              <span className="text-sm font-medium text-gray-200">
                {formatCurrency(gpuCost)}{periodLabel}
              </span>
            </div>

            {/* Failover Cost */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${hasNoFailover ? 'bg-gray-600' : 'bg-emerald-500'}`} />
                <span className="text-xs text-gray-400">
                  Failover ({failoverName || 'Snapshot Only'})
                </span>
              </div>
              <span className={`text-sm font-medium ${hasNoFailover ? 'text-gray-500' : 'text-gray-200'}`}>
                {hasNoFailover ? '$0' : `+${formatCurrency(failoverCost)}${periodLabel}`}
              </span>
            </div>

            {/* Divider */}
            <div className="border-t border-white/10 pt-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-300">Total</span>
                <span className="text-sm font-bold text-gray-100">
                  {formatCurrency(totalCost)}{periodLabel}
                </span>
              </div>
            </div>

            {/* Monthly/Annual Summary */}
            {selectedPeriod !== 'monthly' && (
              <div className="flex items-start gap-2 p-2 rounded-lg bg-white/5 text-[10px]">
                <Info className="w-3 h-3 text-gray-500 mt-0.5 flex-shrink-0" />
                <div className="text-gray-400">
                  <span className="text-gray-300 font-medium">Projeção mensal:</span>{' '}
                  {formatCurrency(cost.totalMonthly)} | {' '}
                  <span className="text-gray-300 font-medium">Anual:</span>{' '}
                  {formatCurrency(cost.totalMonthly * 12)}
                </div>
              </div>
            )}

            {/* No Failover Warning */}
            {hasNoFailover && (
              <div className="flex items-start gap-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-[10px]">
                <AlertTriangle className="w-3 h-3 text-red-400 mt-0.5 flex-shrink-0" />
                <div className="text-red-300/80">
                  Sem failover: Se a máquina falhar, você perderá todos os dados.
                  Considere adicionar proteção para trabalhos importantes.
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer with quick stats */}
      <div className="px-4 py-2 bg-white/[0.02] border-t border-white/10 flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-gray-500">Por hora: </span>
            <span className="text-gray-300 font-medium">{formatCurrency(cost.totalHourly)}</span>
          </div>
          <div>
            <span className="text-gray-500">Por mês: </span>
            <span className="text-gray-300 font-medium">{formatCurrency(cost.totalMonthly)}</span>
          </div>
          <div>
            <span className="text-gray-500">Por ano: </span>
            <span className="text-gray-300 font-medium">{formatCurrency(cost.totalMonthly * 12)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Floating Cost Card Component (Sticky Sidebar)
// ============================================================================

export const FloatingCostCard: React.FC<FloatingCostCardProps> = ({
  cost,
  gpuName,
  failoverName,
  locationName,
  isVisible = true,
  onClose,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState<'hourly' | 'monthly'>('monthly');

  const isConfigured = cost.hourly > 0;
  const hasNoFailover = cost.failoverHourly === 0 && cost.failoverMonthly === 0;
  const isExpensive = cost.totalMonthly > 100;

  const displayCost = selectedPeriod === 'hourly' ? cost.totalHourly : cost.totalMonthly;
  const periodLabel = selectedPeriod === 'hourly' ? '/h' : '/mês';
  const gpuDisplayCost = selectedPeriod === 'hourly' ? cost.hourly : cost.monthly;
  const failoverDisplayCost = selectedPeriod === 'hourly' ? cost.failoverHourly : cost.failoverMonthly;

  if (!isVisible) return null;

  return (
    <div
      className={`bg-gray-900/95 backdrop-blur-sm border border-white/10 rounded-xl shadow-2xl overflow-hidden transition-all duration-300 ${className}`}
      data-testid="floating-cost-card"
    >
      {/* Header */}
      <div className="px-3 py-2 bg-gradient-to-r from-brand-500/10 to-transparent border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-brand-500/20 flex items-center justify-center">
            <Calculator className="w-3.5 h-3.5 text-brand-400" />
          </div>
          <span className="text-xs font-medium text-gray-300">Custo em Tempo Real</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-white/10 rounded transition-colors"
          >
            {isExpanded ? (
              <Minimize2 className="w-3.5 h-3.5 text-gray-500" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5 text-gray-500" />
            )}
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1 hover:bg-white/10 rounded transition-colors">
              <X className="w-3.5 h-3.5 text-gray-500" />
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      {isExpanded && (
        <div className="p-3 space-y-3">
          {/* Period Toggle */}
          <div className="flex gap-1 p-0.5 bg-white/5 rounded-lg">
            <button
              onClick={() => setSelectedPeriod('hourly')}
              className={`flex-1 py-1 text-[10px] font-medium rounded-md transition-all ${
                selectedPeriod === 'hourly'
                  ? 'bg-brand-500/20 text-brand-400'
                  : 'text-gray-500 hover:text-gray-400'
              }`}
            >
              <Clock className="w-3 h-3 inline mr-1" />
              Hora
            </button>
            <button
              onClick={() => setSelectedPeriod('monthly')}
              className={`flex-1 py-1 text-[10px] font-medium rounded-md transition-all ${
                selectedPeriod === 'monthly'
                  ? 'bg-brand-500/20 text-brand-400'
                  : 'text-gray-500 hover:text-gray-400'
              }`}
            >
              <Calendar className="w-3 h-3 inline mr-1" />
              Mês
            </button>
          </div>

          {/* Total Cost */}
          <div className="text-center py-2">
            {isConfigured ? (
              <>
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-2xl font-bold text-gray-100">
                    {formatCurrency(displayCost)}
                  </span>
                  <span className="text-sm text-gray-500">{periodLabel}</span>
                </div>
                {isExpensive && (
                  <div className="flex items-center justify-center gap-1 mt-1">
                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                    <span className="text-[10px] text-amber-400">Custo elevado</span>
                  </div>
                )}
              </>
            ) : (
              <div className="text-gray-500 text-sm">
                Selecione GPU para ver custos
              </div>
            )}
          </div>

          {/* Breakdown */}
          {isConfigured && (
            <div className="space-y-2 pt-2 border-t border-white/10">
              {/* GPU Cost */}
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 text-gray-400">
                  <Cpu className="w-3 h-3" />
                  <span className="truncate max-w-[100px]">{gpuName || 'GPU'}</span>
                </div>
                <span className="font-mono text-gray-300">
                  {formatCurrency(gpuDisplayCost)}
                </span>
              </div>

              {/* Failover Cost */}
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 text-gray-400">
                  <Shield className={`w-3 h-3 ${hasNoFailover ? 'text-red-400/50' : ''}`} />
                  <span className="truncate max-w-[100px]">
                    {failoverName || (hasNoFailover ? 'Sem Failover' : 'Failover')}
                  </span>
                </div>
                <span className={`font-mono ${hasNoFailover ? 'text-gray-600' : 'text-gray-300'}`}>
                  {hasNoFailover ? '$0' : `+${formatCurrency(failoverDisplayCost)}`}
                </span>
              </div>

              {/* Location if provided */}
              {locationName && (
                <div className="flex items-center gap-1.5 text-[10px] text-gray-500 pt-1 border-t border-white/5">
                  <Info className="w-3 h-3" />
                  <span>Região: {locationName}</span>
                </div>
              )}
            </div>
          )}

          {/* No Failover Warning */}
          {isConfigured && hasNoFailover && (
            <div className="flex items-start gap-1.5 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="w-3 h-3 text-red-400 mt-0.5 flex-shrink-0" />
              <span className="text-[10px] text-red-300/80">
                Dados não protegidos
              </span>
            </div>
          )}

          {/* Annual projection */}
          {isConfigured && selectedPeriod === 'monthly' && (
            <div className="text-center text-[10px] text-gray-500 pt-2 border-t border-white/5">
              Projeção anual: <span className="text-gray-400 font-medium">{formatCurrency(cost.totalMonthly * 12)}</span>
            </div>
          )}
        </div>
      )}

      {/* Collapsed View */}
      {!isExpanded && isConfigured && (
        <div className="px-3 py-2 flex items-center justify-between">
          <span className="text-xs text-gray-400">Total:</span>
          <span className="text-sm font-bold text-gray-200">
            {formatCurrency(cost.totalMonthly)}/mês
          </span>
        </div>
      )}
    </div>
  );
};

export default CostEstimator;

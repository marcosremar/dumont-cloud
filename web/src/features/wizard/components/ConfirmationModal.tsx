/**
 * Confirmation Modal Component
 *
 * Shows a summary of all selections before provisioning starts.
 */

import React from 'react';
import {
  X,
  MapPin,
  Cpu,
  Shield,
  DollarSign,
  AlertTriangle,
  Check,
  Zap,
  Server,
  Network,
} from 'lucide-react';
import { Location, TierName, FailoverStrategyId, PortConfig, EstimatedCost, MachineOffer } from '../types';
import { getTierByName, getStrategyById } from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface ConfirmationModalProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  // Selection data
  selectedLocation: Location | null;
  selectedTier: TierName | null;
  selectedMachine: MachineOffer | null;
  failoverStrategy: FailoverStrategyId;
  dockerImage: string;
  exposedPorts: PortConfig[];
  estimatedCost: EstimatedCost;
}

// ============================================================================
// Helpers
// ============================================================================

const formatCurrency = (value: number): string => {
  if (value < 0.01 && value > 0) return '<$0.01';
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
  return `$${value.toFixed(2)}`;
};

// ============================================================================
// Sub-components
// ============================================================================

interface SummaryRowProps {
  icon: React.ReactNode;
  label: string;
  value: string | React.ReactNode;
  warning?: boolean;
}

const SummaryRow: React.FC<SummaryRowProps> = ({ icon, label, value, warning }) => (
  <div className={`flex items-start gap-3 p-3 rounded-lg ${warning ? 'bg-red-500/10 border border-red-500/20' : 'bg-white/5'}`}>
    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${warning ? 'bg-red-500/20 text-red-400' : 'bg-white/10 text-gray-400'}`}>
      {icon}
    </div>
    <div className="flex-1 min-w-0">
      <span className="text-xs text-gray-500 block">{label}</span>
      <span className={`text-sm font-medium ${warning ? 'text-red-300' : 'text-gray-200'}`}>{value}</span>
    </div>
  </div>
);

// ============================================================================
// Main Component
// ============================================================================

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onConfirm,
  onCancel,
  selectedLocation,
  selectedTier,
  selectedMachine,
  failoverStrategy,
  dockerImage,
  exposedPorts,
  estimatedCost,
}) => {
  if (!isOpen) return null;

  const tierData = selectedTier ? getTierByName(selectedTier) : undefined;
  const failoverData = getStrategyById(failoverStrategy);
  const isNoFailover = failoverStrategy === 'no_failover';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-gray-900 rounded-2xl border border-white/10 shadow-2xl overflow-hidden animate-fadeIn">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Confirmar Provisionamento</h2>
              <p className="text-xs text-gray-500">Revise suas escolhas antes de continuar</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-2 text-gray-400 hover:text-gray-200 hover:bg-white/10 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {/* Location */}
          <SummaryRow
            icon={<MapPin className="w-4 h-4" />}
            label="Localização"
            value={selectedLocation?.name || 'Não selecionada'}
          />

          {/* Hardware */}
          <SummaryRow
            icon={<Cpu className="w-4 h-4" />}
            label="Hardware"
            value={
              selectedMachine ? (
                <span>
                  {selectedMachine.gpu_name} ({selectedMachine.gpu_ram}GB VRAM)
                  <span className="text-gray-500 ml-2">
                    ${selectedMachine.dph_total.toFixed(2)}/h
                  </span>
                </span>
              ) : tierData ? (
                <span>
                  {tierData.label} - {tierData.gpu}
                  <span className="text-gray-500 ml-2">{tierData.priceRange}</span>
                </span>
              ) : (
                'Não selecionado'
              )
            }
          />

          {/* Failover */}
          <SummaryRow
            icon={<Shield className="w-4 h-4" />}
            label="Estratégia de Failover"
            value={
              <span className="flex items-center gap-2">
                {failoverData?.name || failoverStrategy}
                {isNoFailover && (
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 animate-pulse">
                    Risco
                  </span>
                )}
                {failoverData?.recommended && (
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-500/20 text-emerald-400">
                    Recomendado
                  </span>
                )}
              </span>
            }
            warning={isNoFailover}
          />

          {/* Docker Image */}
          <SummaryRow
            icon={<Server className="w-4 h-4" />}
            label="Docker Image"
            value={<code className="text-xs font-mono">{dockerImage}</code>}
          />

          {/* Ports */}
          <SummaryRow
            icon={<Network className="w-4 h-4" />}
            label="Portas Expostas"
            value={
              <span className="flex flex-wrap gap-1">
                {exposedPorts.map((p, i) => (
                  <span key={i} className="px-2 py-0.5 text-xs rounded bg-white/10 font-mono">
                    {p.port}/{p.protocol}
                  </span>
                ))}
              </span>
            }
          />

          {/* Cost Summary */}
          <div className="mt-4 p-4 rounded-xl bg-gradient-to-br from-brand-500/10 to-brand-600/5 border border-brand-500/20">
            <div className="flex items-center gap-2 mb-3">
              <DollarSign className="w-4 h-4 text-brand-400" />
              <span className="text-sm font-medium text-gray-200">Resumo de Custos</span>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <span className="text-2xl font-bold text-gray-100">
                  {formatCurrency(estimatedCost.totalHourly)}
                </span>
                <span className="text-xs text-gray-500 block">/hora</span>
              </div>
              <div>
                <span className="text-2xl font-bold text-gray-100">
                  {formatCurrency(estimatedCost.totalHourly * 24)}
                </span>
                <span className="text-xs text-gray-500 block">/dia</span>
              </div>
              <div>
                <span className="text-2xl font-bold text-gray-100">
                  {formatCurrency(estimatedCost.totalMonthly)}
                </span>
                <span className="text-xs text-gray-500 block">/mês</span>
              </div>
            </div>
            <p className="text-[10px] text-gray-500 mt-3 text-center">
              * Valores estimados baseados em uso contínuo (24/7). Custos reais podem variar.
            </p>
          </div>

          {/* No Failover Warning */}
          {isNoFailover && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-red-300 mb-1">
                  Atenção: Sem proteção de dados
                </h4>
                <p className="text-xs text-red-300/80">
                  Você escolheu não usar nenhuma estratégia de failover. Se a máquina falhar por
                  qualquer motivo, <strong>todos os seus dados serão perdidos</strong>. Recomendamos
                  fortemente usar pelo menos "Snapshot Only" para trabalhos importantes.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between bg-white/[0.02]">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
          >
            Voltar e Editar
          </button>
          <button
            onClick={onConfirm}
            className="group relative px-6 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 hover:scale-[1.02] active:scale-[0.98]"
          >
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4" />
              Confirmar e Provisionar
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;

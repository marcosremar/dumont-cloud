/**
 * Machine Compare Modal Component
 *
 * Allows users to compare multiple GPU machines side-by-side.
 */

import React, { useState, useMemo } from 'react';
import {
  X,
  Cpu,
  MemoryStick,
  DollarSign,
  MapPin,
  Shield,
  Zap,
  Clock,
  Check,
  Minus,
  Plus,
  TrendingUp,
  BarChart3,
  Server,
} from 'lucide-react';
import { RecommendedMachine, MachineOffer } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface MachineCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  machines: RecommendedMachine[];
  onSelectMachine: (machine: MachineOffer) => void;
  selectedMachineId?: number;
}

interface ComparisonMetric {
  id: string;
  label: string;
  icon: React.ElementType;
  getValue: (machine: RecommendedMachine) => string | number;
  format?: (value: string | number) => string;
  higherIsBetter?: boolean;
  unit?: string;
}

// ============================================================================
// Comparison Metrics
// ============================================================================

const COMPARISON_METRICS: ComparisonMetric[] = [
  {
    id: 'gpu_name',
    label: 'GPU',
    icon: Cpu,
    getValue: (m) => m.gpu_name,
  },
  {
    id: 'gpu_ram',
    label: 'VRAM',
    icon: MemoryStick,
    getValue: (m) => m.gpu_ram,
    format: (v) => `${v}GB`,
    higherIsBetter: true,
  },
  {
    id: 'num_gpus',
    label: 'Qtd GPUs',
    icon: Server,
    getValue: (m) => m.num_gpus,
    format: (v) => `${v}x`,
    higherIsBetter: true,
  },
  {
    id: 'dph_total',
    label: 'Preço/Hora',
    icon: DollarSign,
    getValue: (m) => m.dph_total,
    format: (v) => `$${Number(v).toFixed(2)}`,
    higherIsBetter: false,
  },
  {
    id: 'monthly_cost',
    label: 'Custo/Mês',
    icon: TrendingUp,
    getValue: (m) => m.dph_total * 24 * 30,
    format: (v) => `$${Number(v).toFixed(0)}`,
    higherIsBetter: false,
  },
  {
    id: 'location',
    label: 'Localização',
    icon: MapPin,
    getValue: (m) => m.location || m.geolocation || '-',
  },
  {
    id: 'provider',
    label: 'Provedor',
    icon: Shield,
    getValue: (m) => m.provider || '-',
  },
  {
    id: 'reliability',
    label: 'Uptime',
    icon: Clock,
    getValue: (m) => m.reliability || 0,
    format: (v) => `${v}%`,
    higherIsBetter: true,
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

const getBestValue = (
  machines: RecommendedMachine[],
  metric: ComparisonMetric
): string | number | null => {
  if (metric.higherIsBetter === undefined) return null;

  const values = machines.map((m) => {
    const val = metric.getValue(m);
    return typeof val === 'number' ? val : parseFloat(val as string) || 0;
  });

  if (metric.higherIsBetter) {
    return Math.max(...values);
  }
  return Math.min(...values);
};

// ============================================================================
// Sub-components
// ============================================================================

interface MetricRowProps {
  metric: ComparisonMetric;
  machines: RecommendedMachine[];
  selectedId?: number;
}

const MetricRow: React.FC<MetricRowProps> = ({ metric, machines, selectedId }) => {
  const Icon = metric.icon;
  const bestValue = getBestValue(machines, metric);

  return (
    <div className="flex items-center border-b border-white/5 last:border-b-0">
      {/* Metric Label */}
      <div className="w-32 flex-shrink-0 py-3 px-4 flex items-center gap-2 text-gray-400 bg-white/[0.02]">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium">{metric.label}</span>
      </div>

      {/* Values */}
      {machines.map((machine) => {
        const value = metric.getValue(machine);
        const numValue = typeof value === 'number' ? value : parseFloat(value as string) || 0;
        const isBest = bestValue !== null && numValue === bestValue;
        const isSelected = machine.id === selectedId;
        const displayValue = metric.format ? metric.format(value) : value;

        return (
          <div
            key={machine.id}
            className={`flex-1 py-3 px-4 text-center ${
              isSelected ? 'bg-brand-500/5' : ''
            }`}
          >
            <span
              className={`text-sm ${
                isBest
                  ? 'text-emerald-400 font-medium'
                  : isSelected
                  ? 'text-brand-400'
                  : 'text-gray-300'
              }`}
            >
              {displayValue}
              {isBest && metric.higherIsBetter !== undefined && (
                <Check className="w-3 h-3 inline ml-1 text-emerald-400" />
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const MachineCompareModal: React.FC<MachineCompareModalProps> = ({
  isOpen,
  onClose,
  machines,
  onSelectMachine,
  selectedMachineId,
}) => {
  const [selectedToCompare, setSelectedToCompare] = useState<number[]>([]);

  // Get machines to compare (either selected or first 3)
  const machinesToCompare = useMemo(() => {
    if (selectedToCompare.length > 0) {
      return machines.filter((m) => selectedToCompare.includes(m.id));
    }
    return machines.slice(0, 3);
  }, [machines, selectedToCompare]);

  const toggleMachineSelection = (id: number) => {
    setSelectedToCompare((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      if (prev.length < 4) {
        return [...prev, id];
      }
      return prev;
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl bg-gray-900 border border-white/10 shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/20 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Comparar Máquinas</h2>
              <p className="text-xs text-gray-500">
                Compare até 4 máquinas lado a lado
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

        {/* Machine Selection */}
        <div className="px-6 py-3 border-b border-white/10 bg-white/[0.02]">
          <label className="text-xs text-gray-500 mb-2 block">
            Selecione as máquinas para comparar (máx. 4):
          </label>
          <div className="flex flex-wrap gap-2">
            {machines.map((machine) => {
              const isInComparison = selectedToCompare.length === 0
                ? machinesToCompare.some((m) => m.id === machine.id)
                : selectedToCompare.includes(machine.id);

              return (
                <button
                  key={machine.id}
                  onClick={() => toggleMachineSelection(machine.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    isInComparison
                      ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    {isInComparison ? (
                      <Minus className="w-3 h-3" />
                    ) : (
                      <Plus className="w-3 h-3" />
                    )}
                    {machine.gpu_name} ({machine.gpu_ram}GB)
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Comparison Table */}
        <div className="overflow-x-auto max-h-[50vh] overflow-y-auto">
          {machinesToCompare.length > 0 ? (
            <div className="min-w-full">
              {/* Machine Headers */}
              <div className="flex items-center border-b border-white/10 bg-gray-800/50 sticky top-0 z-10">
                <div className="w-32 flex-shrink-0 py-3 px-4">
                  <span className="text-xs font-medium text-gray-500">Métrica</span>
                </div>
                {machinesToCompare.map((machine) => {
                  const isSelected = machine.id === selectedMachineId;
                  return (
                    <div
                      key={machine.id}
                      className={`flex-1 py-3 px-4 text-center ${
                        isSelected ? 'bg-brand-500/10' : ''
                      }`}
                    >
                      <div className="flex flex-col items-center gap-1">
                        <span
                          className={`text-sm font-medium ${
                            isSelected ? 'text-brand-400' : 'text-gray-200'
                          }`}
                        >
                          {machine.gpu_name}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-gray-400">
                          {machine.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Metrics */}
              {COMPARISON_METRICS.map((metric) => (
                <MetricRow
                  key={metric.id}
                  metric={metric}
                  machines={machinesToCompare}
                  selectedId={selectedMachineId}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Selecione máquinas para comparar</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-white/10 bg-gray-800/30 flex items-center justify-between">
          <div className="text-xs text-gray-500">
            <Check className="w-3 h-3 inline mr-1 text-emerald-400" />
            Indica o melhor valor para a métrica
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Fechar
            </button>
            {machinesToCompare.length > 0 && (
              <div className="flex gap-2">
                {machinesToCompare.map((machine) => (
                  <button
                    key={machine.id}
                    onClick={() => {
                      onSelectMachine(machine);
                      onClose();
                    }}
                    className={`px-4 py-2 text-sm rounded-lg transition-all ${
                      machine.id === selectedMachineId
                        ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                        : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
                    }`}
                  >
                    Escolher {machine.gpu_name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MachineCompareModal;

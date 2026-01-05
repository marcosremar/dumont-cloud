/**
 * Strategy Step Component
 *
 * Step 3: Select failover strategy and advanced settings.
 */

import React from 'react';
import {
  HelpCircle,
  Timer,
  HardDrive,
  DollarSign,
  Check,
  ChevronDown,
  ChevronUp,
  Settings,
  Code,
  Network,
  Plus,
  Trash2,
} from 'lucide-react';
import { FailoverStrategyId, FailoverStrategy, PortConfig, Location, TierName, EstimatedCost } from '../../types';
import { FAILOVER_STRATEGIES, getStrategyById } from '../../constants';
import { CostEstimator } from '../CostEstimator';
import { Tooltip, WIZARD_TOOLTIPS } from '../Tooltip';
import { DockerImageSelector } from '../DockerImageSelector';
import { PortSelector } from '../PortSelector';

// ============================================================================
// Types
// ============================================================================

export interface StrategyStepProps {
  failoverStrategy: FailoverStrategyId;
  selectedLocation: Location | null;
  selectedTier: TierName | null;
  selectedGPUName?: string;
  estimatedCost?: EstimatedCost;
  showAdvancedSettings: boolean;
  dockerImage: string;
  exposedPorts: PortConfig[];
  onSelectStrategy: (strategy: FailoverStrategyId) => void;
  onToggleAdvancedSettings: () => void;
  onDockerImageChange: (image: string) => void;
  onAddPort: (port?: PortConfig) => void;
  onRemovePort: (index: number) => void;
  onUpdatePort: (index: number, config: PortConfig) => void;
}

// ============================================================================
// Sub-components
// ============================================================================

interface StrategyCardProps {
  strategy: FailoverStrategy;
  isSelected: boolean;
  onClick: () => void;
}

const StrategyCard: React.FC<StrategyCardProps> = ({ strategy, isSelected, onClick }) => {
  const Icon = strategy.icon;
  const isDisabled = strategy.comingSoon;

  return (
    <button
      data-testid={`failover-option-${strategy.id}`}
      onClick={() => !isDisabled && onClick()}
      disabled={isDisabled}
      className={`w-full p-4 rounded-lg border text-left transition-all ${
        isDisabled
          ? 'bg-white/[0.02] border-white/5 cursor-not-allowed opacity-60'
          : isSelected && strategy.danger
          ? 'bg-red-500/10 border-red-500'
          : isSelected
          ? 'bg-brand-500/10 border-brand-500'
          : strategy.danger
          ? 'bg-white/5 border-white/10 hover:bg-red-500/5 hover:border-red-500/30'
          : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
      }`}
    >
      <div className="flex items-start gap-4">
        <div
          className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isDisabled
              ? 'bg-white/5 text-gray-600'
              : isSelected
              ? 'bg-white/20 text-white'
              : 'bg-white/5 text-gray-500'
          }`}
        >
          <Icon className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className={`text-sm font-medium ${
                isDisabled ? 'text-gray-500' : isSelected ? 'text-gray-100' : 'text-gray-300'
              }`}
            >
              {strategy.name}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
              {strategy.provider}
            </span>
            {strategy.recommended && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                Recomendado
              </span>
            )}
            {strategy.danger && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 animate-pulse">
                ⚠️ Risco
              </span>
            )}
            {strategy.comingSoon && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
                Em breve
              </span>
            )}
          </div>

          <p className={`text-xs mb-3 ${isDisabled ? 'text-gray-600' : 'text-gray-400'}`}>
            {strategy.description}
          </p>

          {/* Features */}
          {strategy.features && (
            <div className="grid grid-cols-2 gap-1 mb-3">
              {strategy.features.map((feature, idx) => (
                <div key={idx} className="flex items-center gap-1.5 text-[10px]">
                  <Check className={`w-3 h-3 ${isDisabled ? 'text-gray-600' : 'text-gray-500'}`} />
                  <span className={isDisabled ? 'text-gray-600' : 'text-gray-400'}>{feature}</span>
                </div>
              ))}
            </div>
          )}

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-2 text-[10px]">
            <div className="flex items-center gap-1">
              <Timer className={`w-3 h-3 ${isDisabled ? 'text-gray-600' : 'text-gray-500'}`} />
              <span className={isDisabled ? 'text-gray-600' : 'text-gray-500'}>Recovery:</span>
              <span
                className={`font-medium ${
                  isDisabled ? 'text-gray-600' : isSelected ? 'text-gray-200' : 'text-gray-400'
                }`}
              >
                {strategy.recoveryTime}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <HardDrive className={`w-3 h-3 ${isDisabled ? 'text-gray-600' : 'text-gray-500'}`} />
              <span className={isDisabled ? 'text-gray-600' : 'text-gray-500'}>Perda:</span>
              <span
                className={`font-medium ${
                  isDisabled
                    ? 'text-gray-600'
                    : strategy.dataLoss === 'Zero'
                    ? 'text-emerald-400'
                    : 'text-gray-400'
                }`}
              >
                {strategy.dataLoss}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <DollarSign className={`w-3 h-3 ${isDisabled ? 'text-gray-600' : 'text-gray-500'}`} />
              <span className={isDisabled ? 'text-gray-600' : 'text-gray-500'}>Custo:</span>
              <span
                className={`font-medium ${
                  isDisabled ? 'text-gray-600' : isSelected ? 'text-gray-200' : 'text-gray-400'
                }`}
              >
                {strategy.costHour}
              </span>
            </div>
          </div>
        </div>

        {/* Radio indicator */}
        <div
          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
            isDisabled ? 'border-white/10' : isSelected ? 'border-white/40 bg-white/20' : 'border-white/20'
          }`}
        >
          {isSelected && !isDisabled && <div className="w-2 h-2 rounded-full bg-white" />}
        </div>
      </div>
    </button>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const StrategyStep: React.FC<StrategyStepProps> = ({
  failoverStrategy,
  selectedLocation,
  selectedTier,
  selectedGPUName,
  estimatedCost,
  showAdvancedSettings,
  dockerImage,
  exposedPorts,
  onSelectStrategy,
  onToggleAdvancedSettings,
  onDockerImageChange,
  onAddPort,
  onRemovePort,
  onUpdatePort,
}) => {
  const selectedStrategyData = getStrategyById(failoverStrategy);

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <label className="text-gray-300 text-sm font-medium">Estratégia de Failover</label>
          <Tooltip
            title={WIZARD_TOOLTIPS.failover.title}
            content={WIZARD_TOOLTIPS.failover.content}
            variant={WIZARD_TOOLTIPS.failover.variant}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Como recuperar automaticamente se a máquina falhar?
        </p>
      </div>

      {/* Strategy Cards */}
      <div className="space-y-3">
        {FAILOVER_STRATEGIES.map((strategy) => (
          <StrategyCard
            key={strategy.id}
            strategy={strategy}
            isSelected={failoverStrategy === strategy.id}
            onClick={() => onSelectStrategy(strategy.id as FailoverStrategyId)}
          />
        ))}
      </div>

      {/* Cost Estimator */}
      {estimatedCost && (
        <CostEstimator
          cost={estimatedCost}
          gpuName={selectedGPUName}
          failoverName={selectedStrategyData?.name}
          showBreakdown={true}
        />
      )}

      {/* Selected Strategy Details */}
      {selectedStrategyData && (
        <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-3">
          <h4 className="text-xs font-medium text-gray-300">Como funciona</h4>
          <p className="text-xs text-gray-400">{selectedStrategyData.howItWorks}</p>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500">Requisitos:</span>
            <span className="text-gray-400">{selectedStrategyData.requirements}</span>
          </div>

          <div className="pt-3 border-t border-white/10">
            <h4 className="text-xs font-medium text-gray-400 mb-2">Resumo da configuração</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Região</span>
                <span className="text-gray-300">{selectedLocation?.name ?? '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Performance</span>
                <span className="text-gray-300">{selectedTier ?? '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Failover</span>
                <span className="text-gray-300">{selectedStrategyData.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Custo extra</span>
                <span className="text-gray-300">{selectedStrategyData.costHour}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Advanced Settings */}
      {failoverStrategy && (
        <div className="space-y-2">
          <button
            onClick={onToggleAdvancedSettings}
            className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-all flex items-center justify-center gap-1.5"
            data-testid="toggle-advanced-settings"
          >
            <Settings className="w-3.5 h-3.5" />
            {showAdvancedSettings ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" />
                Ocultar configurações avançadas
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" />
                Configurações avançadas
              </>
            )}
          </button>

          {showAdvancedSettings && (
            <div className="pt-3 border-t border-white/10 space-y-5 animate-fadeIn">
              {/* Docker Image */}
              <div className="space-y-2">
                <label className="text-gray-300 text-xs font-medium flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5" />
                  Template Docker
                  <Tooltip
                    title={WIZARD_TOOLTIPS.dockerImage.title}
                    content={WIZARD_TOOLTIPS.dockerImage.content}
                    variant={WIZARD_TOOLTIPS.dockerImage.variant}
                  />
                </label>
                <DockerImageSelector
                  value={dockerImage}
                  onChange={onDockerImageChange}
                />
              </div>

              {/* Exposed Ports */}
              <div className="space-y-2">
                <label className="text-gray-300 text-xs font-medium flex items-center gap-1.5">
                  <Network className="w-3.5 h-3.5" />
                  Portas Expostas
                  <Tooltip
                    title={WIZARD_TOOLTIPS.exposedPorts.title}
                    content={WIZARD_TOOLTIPS.exposedPorts.content}
                    variant={WIZARD_TOOLTIPS.exposedPorts.variant}
                  />
                </label>
                <PortSelector
                  ports={exposedPorts}
                  onAddPort={onAddPort}
                  onRemovePort={onRemovePort}
                  onUpdatePort={onUpdatePort}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StrategyStep;

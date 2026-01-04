/**
 * StrategyStep Component
 * Step 3: Failover strategy selection
 */

import React from 'react';
import {
  Clock,
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Settings,
  Plus,
  Trash2,
} from 'lucide-react';
import { useWizard } from '../WizardContext';
import { FAILOVER_OPTIONS } from '../constants/failoverOptions';
import { Tooltip } from '../components/Tooltip';
import { Label } from '../../tailadmin-ui';
import type { FailoverStrategy } from '../types/wizard.types';

export function StrategyStep() {
  const { state, dispatch, userBalance, loadingBalance, balanceError } = useWizard();

  const { failoverStrategy, showAdvancedSettings, dockerImage, exposedPorts } = state;

  // Handle failover selection
  const handleFailoverSelect = (id: FailoverStrategy) => {
    dispatch({ type: 'SET_FAILOVER_STRATEGY', payload: id });
  };

  // Handle advanced settings toggle
  const toggleAdvancedSettings = () => {
    dispatch({ type: 'SET_SHOW_ADVANCED', payload: !showAdvancedSettings });
  };

  // Handle docker image change
  const handleDockerImageChange = (value: string) => {
    dispatch({ type: 'SET_DOCKER_IMAGE', payload: value });
  };

  // Handle port changes
  const handlePortChange = (index: number, field: 'port' | 'protocol', value: string) => {
    const newPorts = [...exposedPorts];
    newPorts[index] = { ...newPorts[index], [field]: value };
    dispatch({ type: 'SET_EXPOSED_PORTS', payload: newPorts });
  };

  // Add new port
  const addPort = () => {
    dispatch({
      type: 'SET_EXPOSED_PORTS',
      payload: [...exposedPorts, { port: '', protocol: 'TCP' as const }],
    });
  };

  // Remove port
  const removePort = (index: number) => {
    if (exposedPorts.length > 1) {
      dispatch({
        type: 'SET_EXPOSED_PORTS',
        payload: exposedPorts.filter((_, i) => i !== index),
      });
    }
  };

  return (
    <div className="space-y-5 animate-fadeIn">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Label className="text-gray-300 text-sm font-medium">
            Estratégia de Failover (V6)
          </Label>
          <Tooltip text="Recuperação automática em caso de falha da GPU">
            <HelpCircle className="w-3.5 h-3.5 text-gray-500 hover:text-gray-400 cursor-help" />
          </Tooltip>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Como recuperar automaticamente se a máquina falhar?
        </p>
      </div>

      {/* Balance Display */}
      {!loadingBalance && userBalance !== null && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
          <span className="text-xs text-gray-400">Saldo disponível:</span>
          <span className="text-sm font-medium text-brand-400">
            ${userBalance.toFixed(2)}
          </span>
        </div>
      )}
      {balanceError && (
        <div className="text-xs text-red-400">{balanceError}</div>
      )}

      {/* Failover Options */}
      <div className="space-y-3">
        {FAILOVER_OPTIONS.map((option) => {
          const isSelected = failoverStrategy === option.id;
          const OptionIcon = option.icon;
          const isDisabled = option.comingSoon;

          return (
            <button
              key={option.id}
              data-testid={`failover-option-${option.id}`}
              onClick={() => !isDisabled && handleFailoverSelect(option.id as FailoverStrategy)}
              disabled={isDisabled}
              className={`w-full p-4 rounded-lg border text-left transition-all ${
                isDisabled
                  ? 'bg-white/[0.02] border-white/5 cursor-not-allowed opacity-60'
                  : isSelected && option.danger
                  ? 'bg-red-500/10 border-red-500'
                  : isSelected
                  ? 'bg-brand-500/10 border-brand-500'
                  : option.danger
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
                  <OptionIcon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span
                      className={`text-sm font-medium ${
                        isDisabled
                          ? 'text-gray-500'
                          : isSelected
                          ? 'text-gray-100'
                          : 'text-gray-300'
                      }`}
                    >
                      {option.name}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                      {option.provider}
                    </span>
                    {option.recommended && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                        Recomendado
                      </span>
                    )}
                    {option.danger && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 animate-pulse">
                        ⚠️ Risco
                      </span>
                    )}
                    {option.comingSoon && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
                        Em breve
                      </span>
                    )}
                  </div>
                  <p
                    className={`text-xs mb-3 ${
                      isDisabled ? 'text-gray-600' : 'text-gray-400'
                    }`}
                  >
                    {option.description}
                  </p>

                  {/* Stats */}
                  <div className="flex flex-wrap gap-3 text-[10px]">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-gray-500" />
                      <span className="text-gray-400">Recovery:</span>
                      <span className="text-gray-300">{option.recoveryTime}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <AlertCircle className="w-3 h-3 text-gray-500" />
                      <span className="text-gray-400">Data loss:</span>
                      <span
                        className={
                          option.dataLoss === 'Zero'
                            ? 'text-emerald-400'
                            : option.dataLoss === 'Total'
                            ? 'text-red-400'
                            : 'text-gray-300'
                        }
                      >
                        {option.dataLoss}
                      </span>
                    </div>
                    {option.costHour && (
                      <div className="flex items-center gap-1">
                        <span className="text-gray-400">Cost:</span>
                        <span className="text-brand-400 font-medium">
                          {option.costHour}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Expanded details when selected */}
                  {isSelected && option.features && (
                    <div className="mt-3 pt-3 border-t border-white/10">
                      <ul className="space-y-1">
                        {option.features.map((feature, idx) => (
                          <li
                            key={idx}
                            className="text-[10px] text-gray-400 flex items-center gap-1.5"
                          >
                            <span className="w-1 h-1 rounded-full bg-brand-400" />
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Advanced Settings Toggle */}
      <button
        onClick={toggleAdvancedSettings}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-400 transition-colors"
      >
        <Settings className="w-3.5 h-3.5" />
        <span>Advanced Settings</span>
        {showAdvancedSettings ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {/* Advanced Settings Panel */}
      {showAdvancedSettings && (
        <div className="space-y-4 p-4 rounded-lg bg-white/[0.02] border border-white/10">
          {/* Docker Image */}
          <div className="space-y-2">
            <Label className="text-gray-400 text-xs font-medium">Docker Image</Label>
            <input
              type="text"
              value={dockerImage}
              onChange={(e) => handleDockerImageChange(e.target.value)}
              placeholder="pytorch/pytorch:latest"
              className="w-full px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all font-mono"
              data-testid="docker-image-input"
            />
            <p className="text-[10px] text-gray-500">
              Docker image to use for your environment
            </p>
          </div>

          {/* Exposed Ports */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-gray-400 text-xs font-medium">Exposed Ports</Label>
              <button
                onClick={addPort}
                className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
              >
                <Plus className="w-3 h-3" />
                Add Port
              </button>
            </div>

            <div className="space-y-2">
              {exposedPorts.map((portConfig, index) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={portConfig.port}
                    onChange={(e) => handlePortChange(index, 'port', e.target.value)}
                    placeholder="8080"
                    className="flex-1 px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all font-mono"
                    data-testid={`port-input-${index}`}
                  />

                  <select
                    value={portConfig.protocol}
                    onChange={(e) => handlePortChange(index, 'protocol', e.target.value)}
                    className="px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all font-mono"
                    data-testid={`protocol-select-${index}`}
                  >
                    <option value="TCP">TCP</option>
                    <option value="UDP">UDP</option>
                  </select>

                  {exposedPorts.length > 1 && (
                    <button
                      onClick={() => removePort(index)}
                      className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all"
                      data-testid={`remove-port-${index}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <p className="text-[10px] text-gray-500">
              Ports that will be available for external access. Choose TCP or UDP for each port.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default StrategyStep;

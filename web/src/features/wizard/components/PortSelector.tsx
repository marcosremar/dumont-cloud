/**
 * Port Selector Component
 *
 * Enhanced port configuration with presets.
 */

import React, { useState } from 'react';
import { Plus, Trash2, ChevronDown, Check, Network } from 'lucide-react';
import { PortConfig } from '../types';
import { PORT_PRESETS, getPortPresetByPort, PortPreset } from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface PortSelectorProps {
  ports: PortConfig[];
  onAddPort: (port?: PortConfig) => void;
  onRemovePort: (index: number) => void;
  onUpdatePort: (index: number, config: PortConfig) => void;
  className?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface QuickAddButtonProps {
  preset: PortPreset;
  isAdded: boolean;
  onClick: () => void;
}

const QuickAddButton: React.FC<QuickAddButtonProps> = ({ preset, isAdded, onClick }) => (
  <button
    onClick={onClick}
    disabled={isAdded}
    className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${
      isAdded
        ? 'bg-brand-500/10 border-brand-500/30 text-brand-400 cursor-default'
        : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-gray-300 hover:border-white/20'
    }`}
    title={preset.description}
  >
    <span className="flex items-center gap-1.5">
      {isAdded && <Check className="w-3 h-3" />}
      {preset.name}
      <span className="text-[10px] text-gray-500">:{preset.port}</span>
    </span>
  </button>
);

interface PortRowProps {
  config: PortConfig;
  index: number;
  canRemove: boolean;
  onUpdate: (config: PortConfig) => void;
  onRemove: () => void;
}

const PortRow: React.FC<PortRowProps> = ({ config, index, canRemove, onUpdate, onRemove }) => {
  const preset = getPortPresetByPort(config.port);

  return (
    <div className="flex items-center gap-2 group">
      <div className="flex-1 flex items-center gap-2">
        <input
          type="text"
          value={config.port}
          onChange={(e) => onUpdate({ ...config, port: e.target.value.replace(/\D/g, '') })}
          placeholder="8080"
          className="w-20 px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all font-mono text-center"
          data-testid={`port-input-${index}`}
        />

        <select
          value={config.protocol}
          onChange={(e) => onUpdate({ ...config, protocol: e.target.value as 'TCP' | 'UDP' })}
          className="px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all font-mono"
          data-testid={`protocol-select-${index}`}
        >
          <option value="TCP">TCP</option>
          <option value="UDP">UDP</option>
        </select>

        {preset && (
          <span className="px-2 py-1 text-[10px] rounded bg-white/5 text-gray-400">
            {preset.name}
          </span>
        )}
      </div>

      {canRemove && (
        <button
          onClick={onRemove}
          className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
          data-testid={`remove-port-${index}`}
          title="Remover porta"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const PortSelector: React.FC<PortSelectorProps> = ({
  ports,
  onAddPort,
  onRemovePort,
  onUpdatePort,
  className = '',
}) => {
  const [showQuickAdd, setShowQuickAdd] = useState(false);

  const commonPresets = PORT_PRESETS.filter(p => p.common);
  const otherPresets = PORT_PRESETS.filter(p => !p.common);

  const isPortAdded = (preset: PortPreset) => {
    return ports.some(p => p.port === preset.port);
  };

  const handleQuickAdd = (preset: PortPreset) => {
    if (!isPortAdded(preset)) {
      onAddPort({ port: preset.port, protocol: preset.protocol });
    }
  };

  const handleAddCustom = () => {
    onAddPort({ port: '', protocol: 'TCP' });
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Quick Add - Common Ports */}
      <div className="space-y-2">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">Adicionar rapidamente</span>
        <div className="flex flex-wrap gap-2">
          {commonPresets.map((preset) => (
            <QuickAddButton
              key={preset.id}
              preset={preset}
              isAdded={isPortAdded(preset)}
              onClick={() => handleQuickAdd(preset)}
            />
          ))}
          <button
            onClick={() => setShowQuickAdd(!showQuickAdd)}
            className="px-3 py-1.5 text-xs rounded-lg border bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-gray-300 hover:border-white/20 transition-all"
          >
            <span className="flex items-center gap-1">
              Mais
              <ChevronDown className={`w-3 h-3 transition-transform ${showQuickAdd ? 'rotate-180' : ''}`} />
            </span>
          </button>
        </div>

        {/* Expanded Presets */}
        {showQuickAdd && (
          <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10 animate-fadeIn">
            {otherPresets.map((preset) => (
              <QuickAddButton
                key={preset.id}
                preset={preset}
                isAdded={isPortAdded(preset)}
                onClick={() => handleQuickAdd(preset)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Current Ports */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">
            Portas configuradas ({ports.length})
          </span>
          <button
            onClick={handleAddCustom}
            className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 transition-all"
            data-testid="add-port-button"
          >
            <Plus className="w-3 h-3" />
            Porta customizada
          </button>
        </div>

        <div className="space-y-2">
          {ports.map((config, index) => (
            <PortRow
              key={index}
              config={config}
              index={index}
              canRemove={ports.length > 1}
              onUpdate={(newConfig) => onUpdatePort(index, newConfig)}
              onRemove={() => onRemovePort(index)}
            />
          ))}
        </div>
      </div>

      {/* Helper Text */}
      <p className="text-[10px] text-gray-500">
        Portas que estarão disponíveis para acesso externo via internet.
      </p>
    </div>
  );
};

export default PortSelector;

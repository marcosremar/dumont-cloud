/**
 * Docker Image Selector Component
 *
 * Enhanced dropdown with popular presets and custom option.
 */

import React, { useState, useMemo } from 'react';
import { ChevronDown, Check, Code, Sparkles, Box, Settings } from 'lucide-react';
import { DOCKER_PRESETS, getDockerPresetByImage, DockerImagePreset } from '../constants';

// ============================================================================
// Types
// ============================================================================

export interface DockerImageSelectorProps {
  value: string;
  onChange: (image: string) => void;
  className?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface PresetCardProps {
  preset: DockerImagePreset;
  isSelected: boolean;
  onClick: () => void;
}

const PresetCard: React.FC<PresetCardProps> = ({ preset, isSelected, onClick }) => {
  const getCategoryIcon = () => {
    switch (preset.category) {
      case 'ml':
        return <Sparkles className="w-3.5 h-3.5" />;
      case 'dev':
        return <Code className="w-3.5 h-3.5" />;
      case 'custom':
        return <Settings className="w-3.5 h-3.5" />;
      default:
        return <Box className="w-3.5 h-3.5" />;
    }
  };

  return (
    <button
      onClick={onClick}
      className={`w-full p-3 text-left rounded-lg border transition-all ${
        isSelected
          ? 'bg-brand-500/10 border-brand-500/50'
          : 'bg-white/[0.03] border-white/10 hover:bg-white/[0.06] hover:border-white/20'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-white/10 text-gray-500'
          }`}
        >
          {getCategoryIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${isSelected ? 'text-gray-100' : 'text-gray-300'}`}>
              {preset.name}
            </span>
            {preset.popular && (
              <span className="px-1.5 py-0.5 text-[9px] rounded bg-amber-500/20 text-amber-400">
                Popular
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{preset.description}</p>
          {preset.image && (
            <code className="text-[10px] text-gray-600 font-mono mt-1 block truncate">
              {preset.image}
            </code>
          )}
        </div>
        {isSelected && (
          <Check className="w-4 h-4 text-brand-400 flex-shrink-0" />
        )}
      </div>
    </button>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const DockerImageSelector: React.FC<DockerImageSelectorProps> = ({
  value,
  onChange,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [customImage, setCustomImage] = useState('');
  const [activeCategory, setActiveCategory] = useState<'ml' | 'dev' | 'custom'>('ml');

  const currentPreset = getDockerPresetByImage(value);
  const isCustom = !currentPreset || currentPreset.id === 'custom';

  const filteredPresets = useMemo(() => {
    if (activeCategory === 'custom') {
      return DOCKER_PRESETS.filter(p => p.id === 'custom');
    }
    return DOCKER_PRESETS.filter(p => p.category === activeCategory);
  }, [activeCategory]);

  const handlePresetSelect = (preset: DockerImagePreset) => {
    if (preset.id === 'custom') {
      setActiveCategory('custom');
      return;
    }
    onChange(preset.image);
    setIsOpen(false);
  };

  const handleCustomSubmit = () => {
    if (customImage.trim()) {
      onChange(customImage.trim());
      setIsOpen(false);
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2.5 text-left rounded-lg border border-white/10 bg-white/5 hover:bg-white/[0.07] hover:border-white/20 transition-all"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <Code className="w-4 h-4 text-gray-500 flex-shrink-0" />
            <div className="min-w-0">
              <span className="text-sm text-gray-200 block">
                {isCustom ? 'Imagem Customizada' : currentPreset?.name}
              </span>
              <code className="text-[10px] text-gray-500 font-mono truncate block">
                {value || 'Selecione uma imagem'}
              </code>
            </div>
          </div>
          <ChevronDown
            className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-2 rounded-xl border border-white/10 bg-gray-900 shadow-2xl overflow-hidden animate-fadeIn">
          {/* Category Tabs */}
          <div className="flex border-b border-white/10">
            <button
              onClick={() => setActiveCategory('ml')}
              className={`flex-1 px-4 py-2.5 text-xs font-medium transition-all ${
                activeCategory === 'ml'
                  ? 'text-brand-400 border-b-2 border-brand-400 bg-brand-500/5'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 inline-block mr-1.5" />
              Machine Learning
            </button>
            <button
              onClick={() => setActiveCategory('dev')}
              className={`flex-1 px-4 py-2.5 text-xs font-medium transition-all ${
                activeCategory === 'dev'
                  ? 'text-brand-400 border-b-2 border-brand-400 bg-brand-500/5'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              <Code className="w-3.5 h-3.5 inline-block mr-1.5" />
              Desenvolvimento
            </button>
            <button
              onClick={() => setActiveCategory('custom')}
              className={`flex-1 px-4 py-2.5 text-xs font-medium transition-all ${
                activeCategory === 'custom'
                  ? 'text-brand-400 border-b-2 border-brand-400 bg-brand-500/5'
                  : 'text-gray-400 hover:text-gray-300 hover:bg-white/5'
              }`}
            >
              <Settings className="w-3.5 h-3.5 inline-block mr-1.5" />
              Customizado
            </button>
          </div>

          {/* Preset List */}
          <div className="p-2 max-h-64 overflow-y-auto space-y-1">
            {activeCategory === 'custom' ? (
              <div className="p-3 space-y-3">
                <p className="text-xs text-gray-400">
                  Digite o nome completo da imagem Docker (ex: user/image:tag)
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customImage}
                    onChange={(e) => setCustomImage(e.target.value)}
                    placeholder="pytorch/pytorch:latest"
                    className="flex-1 px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-600 transition-all font-mono"
                    onKeyDown={(e) => e.key === 'Enter' && handleCustomSubmit()}
                  />
                  <button
                    onClick={handleCustomSubmit}
                    disabled={!customImage.trim()}
                    className="px-4 py-2 text-sm font-medium text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    Usar
                  </button>
                </div>
              </div>
            ) : (
              filteredPresets.map((preset) => (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  isSelected={value === preset.image}
                  onClick={() => handlePresetSelect(preset)}
                />
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-2 border-t border-white/10 bg-white/[0.02]">
            <p className="text-[10px] text-gray-500">
              A imagem Docker contém todo o software pré-instalado para sua máquina.
            </p>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default DockerImageSelector;

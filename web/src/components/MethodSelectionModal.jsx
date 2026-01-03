import { useState } from 'react';
import {
  Brain,
  Sparkles,
  Scale,
  Check,
  X,
} from 'lucide-react';

// Fine-tuning methods (matching Fireworks.ai exactly)
const METHODS = [
  {
    id: 'supervised',
    name: 'Supervised (SFT)',
    description: 'Train models on examples of correct inputs and outputs to teach specific patterns and formats.',
    useCases: [
      'Classification tasks (sentiment, categorization, routing)',
      'Content extraction and entity recognition',
      'Style transfer and format standardization',
    ],
    icon: Brain,
    color: 'purple',
  },
  {
    id: 'reinforcement',
    name: 'Reinforced (RFT)',
    description: 'A way to help AI models reason better using feedback scores instead of tons of labeled examples.',
    useCases: [
      'Complex reasoning tasks',
      'Mathematical problem solving',
      'Multi-step decision making',
    ],
    icon: Sparkles,
    color: 'blue',
  },
  {
    id: 'preference',
    name: 'Direct Preference (DPO)',
    description: 'Uses pairs of preferred vs. rejected answers to directly teach the model what people like.',
    useCases: [
      'Alignment with human preferences',
      'Reducing harmful outputs',
      'Improving response quality',
    ],
    icon: Scale,
    color: 'green',
  },
];

export default function MethodSelectionModal({ isOpen, onClose, onSelect }) {
  const [selectedMethod, setSelectedMethod] = useState('supervised');

  if (!isOpen) return null;

  const handleContinue = () => {
    onSelect(selectedMethod);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[999999]">
      <div className="bg-[#1a1f2e] rounded-xl border border-white/10 w-full max-w-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <h2 className="text-base font-semibold text-white">Select Fine-Tuning Method</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-2.5">
          {METHODS.map((method) => {
            const Icon = method.icon;
            const isSelected = selectedMethod === method.id;
            const colorClasses = {
              purple: {
                bg: 'bg-purple-500/10',
                border: 'border-purple-500',
                icon: 'text-purple-400',
                check: 'bg-purple-500',
              },
              blue: {
                bg: 'bg-blue-500/10',
                border: 'border-blue-500',
                icon: 'text-blue-400',
                check: 'bg-blue-500',
              },
              green: {
                bg: 'bg-green-500/10',
                border: 'border-green-500',
                icon: 'text-green-400',
                check: 'bg-green-500',
              },
            }[method.color];

            return (
              <button
                key={method.id}
                onClick={() => setSelectedMethod(method.id)}
                className={`w-full px-3 py-2.5 rounded-lg border-2 text-left transition-all ${
                  isSelected
                    ? `${colorClasses.border} ${colorClasses.bg}`
                    : 'border-white/10 hover:border-white/20 bg-white/[0.02]'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  {/* Icon */}
                  <div className={`p-1.5 rounded-md ${colorClasses.bg}`}>
                    <Icon className={`w-4 h-4 ${colorClasses.icon}`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-white">{method.name}</h3>
                      {isSelected && (
                        <div className={`w-4 h-4 rounded-full ${colorClasses.check} flex items-center justify-center`}>
                          <Check className="w-2.5 h-2.5 text-white" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{method.description}</p>

                    {/* Use Cases */}
                    <ul className="mt-1.5 space-y-0.5">
                      {method.useCases.map((useCase, idx) => (
                        <li key={idx} className="flex items-center gap-1.5 text-xs text-gray-500">
                          <span className="w-1 h-1 rounded-full bg-gray-500 flex-shrink-0" />
                          {useCase}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleContinue}
            className="px-4 py-2 rounded-lg text-sm bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}

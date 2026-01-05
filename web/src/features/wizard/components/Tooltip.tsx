/**
 * Enhanced Tooltip Component
 *
 * Provides educational tooltips with rich content support.
 */

import React, { useState, useRef, useEffect } from 'react';
import { HelpCircle, Info, AlertTriangle, Lightbulb } from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

export type TooltipVariant = 'info' | 'help' | 'warning' | 'tip';
export type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

export interface TooltipProps {
  /** Main tooltip content */
  content: string;
  /** Optional title for the tooltip */
  title?: string;
  /** Variant affects icon and color */
  variant?: TooltipVariant;
  /** Position relative to trigger */
  position?: TooltipPosition;
  /** Optional link for "learn more" */
  learnMoreUrl?: string;
  /** Custom trigger element (default: icon based on variant) */
  children?: React.ReactNode;
  /** Show as inline icon */
  inline?: boolean;
  /** Max width of tooltip */
  maxWidth?: number;
}

// ============================================================================
// Helpers
// ============================================================================

const getVariantConfig = (variant: TooltipVariant) => {
  switch (variant) {
    case 'help':
      return {
        Icon: HelpCircle,
        iconClass: 'text-gray-500 hover:text-gray-400',
        bgClass: 'bg-gray-800',
        borderClass: 'border-gray-700',
      };
    case 'warning':
      return {
        Icon: AlertTriangle,
        iconClass: 'text-amber-500 hover:text-amber-400',
        bgClass: 'bg-amber-950',
        borderClass: 'border-amber-800',
      };
    case 'tip':
      return {
        Icon: Lightbulb,
        iconClass: 'text-emerald-500 hover:text-emerald-400',
        bgClass: 'bg-emerald-950',
        borderClass: 'border-emerald-800',
      };
    case 'info':
    default:
      return {
        Icon: Info,
        iconClass: 'text-brand-500 hover:text-brand-400',
        bgClass: 'bg-gray-800',
        borderClass: 'border-gray-700',
      };
  }
};

const getPositionClasses = (position: TooltipPosition) => {
  switch (position) {
    case 'bottom':
      return {
        container: 'top-full left-1/2 -translate-x-1/2 mt-2',
        arrow: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800',
      };
    case 'left':
      return {
        container: 'right-full top-1/2 -translate-y-1/2 mr-2',
        arrow: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800',
      };
    case 'right':
      return {
        container: 'left-full top-1/2 -translate-y-1/2 ml-2',
        arrow: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800',
      };
    case 'top':
    default:
      return {
        container: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
        arrow: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800',
      };
  }
};

// ============================================================================
// Main Component
// ============================================================================

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  title,
  variant = 'info',
  position = 'top',
  learnMoreUrl,
  children,
  inline = true,
  maxWidth = 280,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [adjustedPosition, setAdjustedPosition] = useState(position);
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const config = getVariantConfig(variant);
  const positionClasses = getPositionClasses(adjustedPosition);

  // Adjust position if tooltip would overflow viewport
  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();

      // Check if tooltip overflows top
      if (position === 'top' && triggerRect.top - tooltipRect.height < 10) {
        setAdjustedPosition('bottom');
      }
      // Check if tooltip overflows bottom
      else if (position === 'bottom' && triggerRect.bottom + tooltipRect.height > window.innerHeight - 10) {
        setAdjustedPosition('top');
      }
      // Check if tooltip overflows left
      else if (position === 'left' && triggerRect.left - tooltipRect.width < 10) {
        setAdjustedPosition('right');
      }
      // Check if tooltip overflows right
      else if (position === 'right' && triggerRect.right + tooltipRect.width > window.innerWidth - 10) {
        setAdjustedPosition('left');
      } else {
        setAdjustedPosition(position);
      }
    }
  }, [isVisible, position]);

  const Icon = config.Icon;

  return (
    <span
      ref={triggerRef}
      className={`relative ${inline ? 'inline-flex items-center' : ''}`}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {/* Trigger */}
      {children || (
        <button
          type="button"
          className={`p-0.5 rounded transition-colors cursor-help ${config.iconClass}`}
          aria-label="Mais informações"
        >
          <Icon className="w-3.5 h-3.5" />
        </button>
      )}

      {/* Tooltip */}
      {isVisible && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className={`absolute z-50 ${positionClasses.container} animate-fadeIn`}
          style={{ maxWidth }}
        >
          <div
            className={`px-3 py-2 rounded-lg shadow-xl border ${config.bgClass} ${config.borderClass}`}
          >
            {title && (
              <div className="flex items-center gap-1.5 mb-1">
                <Icon className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-xs font-medium text-gray-200">{title}</span>
              </div>
            )}
            <p className="text-xs text-gray-300 leading-relaxed">{content}</p>
            {learnMoreUrl && (
              <a
                href={learnMoreUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 mt-2 text-[10px] text-brand-400 hover:text-brand-300 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                Saiba mais
                <span className="text-[8px]">↗</span>
              </a>
            )}
          </div>
          {/* Arrow */}
          <span
            className={`absolute w-0 h-0 border-4 border-transparent ${positionClasses.arrow}`}
          />
        </div>
      )}
    </span>
  );
};

// ============================================================================
// Pre-configured Tooltips for Common Terms
// ============================================================================

export const WIZARD_TOOLTIPS = {
  failover: {
    title: 'O que é Failover?',
    content:
      'Failover é a capacidade de mudar automaticamente para um sistema de backup quando o sistema principal falha. Protege seus dados e mantém seu trabalho disponível.',
    variant: 'help' as const,
  },
  vram: {
    title: 'VRAM (Memória de Vídeo)',
    content:
      'VRAM é a memória dedicada da GPU. Modelos maiores de IA precisam de mais VRAM. Por exemplo: LLaMA 7B precisa ~14GB, LLaMA 70B precisa ~140GB.',
    variant: 'info' as const,
  },
  dockerImage: {
    title: 'Docker Image',
    content:
      'Uma imagem Docker contém todo o software pré-instalado que você precisa. Escolha PyTorch para ML, TensorFlow para deep learning, ou use uma imagem customizada.',
    variant: 'info' as const,
  },
  exposedPorts: {
    title: 'Portas Expostas',
    content:
      'Portas que você pode acessar remotamente. 22 = SSH, 8888 = Jupyter Notebook, 6006 = TensorBoard, 8080 = Web apps.',
    variant: 'info' as const,
  },
  snapshotOnly: {
    title: 'Snapshot Only',
    content:
      'Backups automáticos a cada 60 minutos. Se a GPU falhar, você perde no máximo 1 hora de trabalho. Restauração manual ou automática.',
    variant: 'tip' as const,
  },
  warmPool: {
    title: 'Warm Pool',
    content:
      'Uma GPU de backup fica em standby no mesmo servidor. Se a principal falhar, a backup assume em segundos. Custo extra de ~$0.03/h.',
    variant: 'info' as const,
  },
  cpuStandby: {
    title: 'CPU Standby',
    content:
      'Uma máquina CPU mantém seus dados sincronizados continuamente. Se a GPU falhar, o CPU preserva seu trabalho enquanto uma nova GPU é provisionada.',
    variant: 'info' as const,
  },
  noFailover: {
    title: 'Sem Failover - RISCO!',
    content:
      'Sem proteção alguma. Se a GPU falhar por qualquer motivo (manutenção, queda de energia, etc), TODOS os seus dados serão perdidos permanentemente.',
    variant: 'warning' as const,
  },
  tier: {
    title: 'Níveis de Performance',
    content:
      'CPU = Sem GPU (processamento básico). Lento = Testes rápidos. Médio = Desenvolvimento. Rápido = Fine-tuning. Ultra = Produção e LLMs grandes.',
    variant: 'info' as const,
  },
  region: {
    title: 'Região',
    content:
      'A localização física da GPU. Escolha regiões mais próximas de você para menor latência. Preços variam por região.',
    variant: 'info' as const,
  },
};

// ============================================================================
// Helper Component for Quick Tooltips
// ============================================================================

interface QuickTooltipProps {
  termKey: keyof typeof WIZARD_TOOLTIPS;
  className?: string;
}

export const QuickTooltip: React.FC<QuickTooltipProps> = ({ termKey, className }) => {
  const config = WIZARD_TOOLTIPS[termKey];
  return (
    <Tooltip
      title={config.title}
      content={config.content}
      variant={config.variant}
    />
  );
};

export default Tooltip;

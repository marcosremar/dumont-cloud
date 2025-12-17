import { useState, useRef, useEffect } from 'react'
import { HelpCircle } from 'lucide-react'
import './Tooltip.css'

export function Tooltip({ content, children, position = 'top', delay = 200 }) {
  const [isVisible, setIsVisible] = useState(false)
  const [coords, setCoords] = useState({ top: 0, left: 0 })
  const triggerRef = useRef(null)
  const tooltipRef = useRef(null)
  const timeoutRef = useRef(null)

  const showTooltip = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true)
    }, delay)
  }

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setIsVisible(false)
  }

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect()
      const tooltipRect = tooltipRef.current.getBoundingClientRect()

      let top = 0
      let left = 0

      switch (position) {
        case 'top':
          top = triggerRect.top - tooltipRect.height - 8
          left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
          break
        case 'bottom':
          top = triggerRect.bottom + 8
          left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
          break
        case 'left':
          top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
          left = triggerRect.left - tooltipRect.width - 8
          break
        case 'right':
          top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
          left = triggerRect.right + 8
          break
      }

      // Manter dentro da viewport
      const padding = 8
      if (left < padding) left = padding
      if (left + tooltipRect.width > window.innerWidth - padding) {
        left = window.innerWidth - tooltipRect.width - padding
      }
      if (top < padding) top = triggerRect.bottom + 8
      if (top + tooltipRect.height > window.innerHeight - padding) {
        top = triggerRect.top - tooltipRect.height - 8
      }

      setCoords({ top, left })
    }
  }, [isVisible, position])

  return (
    <span className="tooltip-wrapper">
      <span
        ref={triggerRef}
        className="tooltip-trigger"
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
      >
        {children}
      </span>
      {isVisible && (
        <div
          ref={tooltipRef}
          className={`tooltip-content tooltip-${position}`}
          style={{ top: coords.top, left: coords.left }}
          role="tooltip"
        >
          {content}
          <div className={`tooltip-arrow tooltip-arrow-${position}`} />
        </div>
      )}
    </span>
  )
}

// Tooltip com ícone de ajuda integrado
export function HelpTooltip({ content, size = 14 }) {
  return (
    <Tooltip content={content} position="top">
      <HelpCircle
        size={size}
        className="help-tooltip-icon"
        tabIndex={0}
        aria-label="Ajuda"
      />
    </Tooltip>
  )
}

// Definições de termos técnicos comuns
export const GLOSSARY = {
  'GPU Frac': 'Fração da GPU disponível. 1.0 = GPU completa, 0.5 = metade da GPU compartilhada.',
  'DLPerf': 'Deep Learning Performance. Score relativo de desempenho para cargas de trabalho de ML.',
  'PCIe BW': 'PCIe Bandwidth. Velocidade de transferência entre CPU e GPU em GB/s.',
  'VRAM': 'Video RAM. Memória dedicada da GPU para processar gráficos e dados.',
  'TFlops': 'Teraflops. Trilhões de operações de ponto flutuante por segundo.',
  'Uptime': 'Tempo que a máquina está rodando desde o início.',
  'Stage Timeout': 'Tempo máximo para cada etapa do processo de restore.',
  'Restic': 'Ferramenta de backup incremental usada para snapshots.',
  'R2': 'Cloudflare R2. Serviço de armazenamento compatível com S3.',
  'Vast.ai': 'Provedor de GPUs em nuvem usado para alugar máquinas.',
  'Hot Start': 'Mantém uma máquina em standby para restore instantâneo.',
  'Cold Start': 'Inicia uma máquina nova, mais barato mas mais lento.',
}

// Componente que adiciona tooltip a termos do glossário automaticamente
export function GlossaryTerm({ term }) {
  const definition = GLOSSARY[term]
  if (!definition) return <span>{term}</span>

  return (
    <Tooltip content={definition}>
      <span className="glossary-term">{term}</span>
    </Tooltip>
  )
}

export default Tooltip

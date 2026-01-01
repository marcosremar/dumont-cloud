/**
 * TemplateCard Component
 * Displays a template card with GPU requirements badge for the marketplace
 * Following patterns from MachineCard.jsx
 */
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Badge,
  Button,
} from '../tailadmin-ui'
import {
  Cpu,
  HardDrive,
  FileCode,
  Server,
  Sparkles,
  Zap,
  Check,
  Image,
  MessageSquare,
  BookOpen,
  ArrowRight,
} from 'lucide-react'

// Category icons and display info
const CATEGORY_INFO = {
  notebook: {
    icon: BookOpen,
    label: 'Notebook',
    color: 'primary',
  },
  image_generation: {
    icon: Image,
    label: 'Image Gen',
    color: 'success',
  },
  llm_inference: {
    icon: MessageSquare,
    label: 'LLM Inference',
    color: 'warning',
  },
  default: {
    icon: Server,
    label: 'Template',
    color: 'gray',
  },
}

// Get VRAM tier display info
const getVramTier = (minVram) => {
  if (minVram >= 24) return { label: 'High-End', variant: 'error', description: '24GB+ VRAM required' }
  if (minVram >= 16) return { label: 'Premium', variant: 'warning', description: '16GB+ VRAM required' }
  if (minVram >= 8) return { label: 'Standard', variant: 'primary', description: '8GB+ VRAM required' }
  return { label: 'Entry', variant: 'success', description: '4GB+ VRAM required' }
}

export function TemplateCard({ template, onDeploy, isCompact = false }) {
  const navigate = useNavigate()

  const {
    slug,
    name,
    description,
    gpu_min_vram,
    gpu_recommended_vram,
    cuda_version,
    ports = [],
    volumes = [],
    category = 'default',
    is_verified = false,
  } = template

  const categoryInfo = CATEGORY_INFO[category] || CATEGORY_INFO.default
  const CategoryIcon = categoryInfo.icon
  const vramTier = getVramTier(gpu_min_vram)

  const handleCardClick = () => {
    navigate(`/templates/${slug}`)
  }

  const handleDeploy = (e) => {
    e.stopPropagation()
    if (onDeploy) {
      onDeploy(template)
    } else {
      navigate(`/templates/${slug}`)
    }
  }

  if (isCompact) {
    return (
      <Card
        className="group relative cursor-pointer transition-all hover:border-brand-500/50 hover:shadow-lg"
        onClick={handleCardClick}
      >
        <div className="flex items-center gap-3">
          {/* Icon */}
          <div className={`p-2 rounded-lg bg-${categoryInfo.color}-500/10`}>
            <CategoryIcon className={`w-5 h-5 text-${categoryInfo.color}-400`} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-gray-900 dark:text-white font-semibold text-sm truncate">
                {name}
              </span>
              {is_verified && (
                <Badge variant="success" className="text-[9px]">
                  <Check className="w-2.5 h-2.5 mr-0.5" />
                  Verified
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <Badge variant={categoryInfo.color} className="text-[9px]">
                {categoryInfo.label}
              </Badge>
              <Badge variant={vramTier.variant} className="text-[9px]">
                <Cpu className="w-2.5 h-2.5 mr-0.5" />
                {gpu_min_vram}GB+
              </Badge>
            </div>
          </div>

          {/* Arrow */}
          <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-400 transition-colors" />
        </div>
      </Card>
    )
  }

  return (
    <Card
      className="group relative cursor-pointer transition-all hover:border-brand-500/50 hover:shadow-lg"
      onClick={handleCardClick}
    >
      {/* Card Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <div className={`p-1.5 rounded-lg bg-${categoryInfo.color}-500/10`}>
              <CategoryIcon className={`w-4 h-4 text-${categoryInfo.color}-400`} />
            </div>
            <span className="text-gray-900 dark:text-white font-semibold text-sm truncate">
              {name}
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <Badge variant={categoryInfo.color} className="text-[9px]">
              {categoryInfo.label}
            </Badge>
            {is_verified && (
              <Badge variant="success" className="text-[9px]">
                <Check className="w-2.5 h-2.5 mr-0.5" />
                Verified
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
        {description}
      </p>

      {/* GPU Requirements Badge - Main Feature */}
      <div className="p-2.5 rounded-lg bg-white/5 border border-white/10 mb-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">
            GPU Requirements
          </span>
          <Badge variant={vramTier.variant} className="text-[9px]">
            <Zap className="w-2.5 h-2.5 mr-0.5" />
            {vramTier.label}
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="text-center p-1.5 rounded bg-gray-800/30">
            <div className="text-brand-400 font-mono text-sm font-bold">{gpu_min_vram}GB</div>
            <div className="text-[8px] text-gray-500 uppercase">Min VRAM</div>
          </div>
          <div className="text-center p-1.5 rounded bg-gray-800/30">
            <div className="text-white font-mono text-sm font-bold">{gpu_recommended_vram}GB</div>
            <div className="text-[8px] text-gray-500 uppercase">Recommended</div>
          </div>
        </div>
      </div>

      {/* Specs Row */}
      <div className="flex items-center gap-1.5 mb-3 text-[9px] text-gray-400 flex-wrap">
        <span
          className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
          title={`CUDA Version ${cuda_version}`}
        >
          <Sparkles className="w-2.5 h-2.5 inline mr-0.5" />
          CUDA {cuda_version}
        </span>

        {ports.length > 0 && (
          <span
            className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
            title={`Ports: ${ports.join(', ')}`}
          >
            <Server className="w-2.5 h-2.5 inline mr-0.5" />
            Port {ports[0]}
          </span>
        )}

        {volumes.length > 0 && (
          <span
            className="px-1.5 py-0.5 rounded bg-gray-700/30 border border-gray-700/30"
            title={`Volumes: ${volumes.join(', ')}`}
          >
            <HardDrive className="w-2.5 h-2.5 inline mr-0.5" />
            {volumes.length} volume{volumes.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Deploy Button */}
      <Button
        variant="primary"
        size="sm"
        className="w-full text-xs group-hover:bg-brand-500"
        onClick={handleDeploy}
      >
        <Cpu className="w-3.5 h-3.5 mr-1.5" />
        Deploy Now
      </Button>
    </Card>
  )
}

export default TemplateCard

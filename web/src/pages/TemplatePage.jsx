/**
 * TemplatePage - Template Marketplace
 * Displays template cards with filtering and one-click deployment
 * Following patterns from Machines.jsx
 */
import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  Cpu,
  Store,
  Sparkles,
  RefreshCw,
  Grid,
  List,
  Search,
  BookOpen,
  Image,
  MessageSquare,
  Server,
  Filter,
  X,
} from 'lucide-react'
import {
  Card,
  Badge,
  Button,
  Input,
} from '../components/tailadmin-ui'
import { ErrorState } from '../components/ErrorState'
import { EmptyState } from '../components/EmptyState'
import { SkeletonList } from '../components/Skeleton'
import { TemplateCard } from '../components/marketplace/TemplateCard'
import { TemplateFilters } from '../components/marketplace/TemplateFilters'
import {
  fetchTemplates,
  selectTemplates,
  selectTemplatesLoading,
  selectTemplatesError,
  selectTemplateFilters,
  setFilters,
  resetFilters,
  clearError,
} from '../store/slices/templateSlice'
import { isDemoMode } from '../utils/api'

// Demo templates for demo mode
const DEMO_TEMPLATES = [
  {
    id: 1,
    slug: 'jupyter-lab',
    name: 'JupyterLab',
    description: 'Interactive Python development environment with GPU support for ML/AI workloads. Pre-configured with PyTorch 2.0 and popular data science libraries.',
    docker_image: 'jupyter/pytorch-notebook:latest',
    gpu_min_vram: 4,
    gpu_recommended_vram: 8,
    cuda_version: '11.8',
    ports: [8888],
    volumes: ['/home/jovyan/work'],
    category: 'notebook',
    is_verified: true,
  },
  {
    id: 2,
    slug: 'stable-diffusion',
    name: 'Stable Diffusion WebUI',
    description: 'AUTOMATIC1111 WebUI for generating AI images with Stable Diffusion. Supports ControlNet, LoRA, and other extensions.',
    docker_image: 'ghcr.io/absolutelyludicrous/automatic1111-webui:latest',
    gpu_min_vram: 4,
    gpu_recommended_vram: 8,
    cuda_version: '11.8',
    ports: [7860],
    volumes: ['/app/models', '/app/outputs'],
    category: 'image_generation',
    is_verified: false,
  },
  {
    id: 3,
    slug: 'comfy-ui',
    name: 'ComfyUI',
    description: 'Node-based UI for Stable Diffusion with powerful workflow capabilities. Perfect for complex image generation pipelines.',
    docker_image: 'yanwk/comfyui-boot:latest',
    gpu_min_vram: 4,
    gpu_recommended_vram: 8,
    cuda_version: '11.8',
    ports: [8188],
    volumes: ['/app/models', '/app/output', '/app/input'],
    category: 'image_generation',
    is_verified: false,
  },
  {
    id: 4,
    slug: 'vllm',
    name: 'vLLM',
    description: 'High-performance LLM inference server with OpenAI-compatible API. Run models like Llama 2, Mistral, and more.',
    docker_image: 'vllm/vllm-openai:latest',
    gpu_min_vram: 16,
    gpu_recommended_vram: 24,
    cuda_version: '11.8',
    ports: [8000],
    volumes: ['/root/.cache/huggingface'],
    category: 'llm_inference',
    is_verified: false,
  },
]

// Category icons for quick filters
const CATEGORY_ICONS = {
  notebook: BookOpen,
  image_generation: Image,
  llm_inference: MessageSquare,
}

export default function TemplatePage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const isDemo = isDemoMode()

  // Redux state
  const templates = useSelector(selectTemplates)
  const loading = useSelector(selectTemplatesLoading)
  const error = useSelector(selectTemplatesError)
  const filters = useSelector(selectTemplateFilters)

  // Local state
  const [viewMode, setViewMode] = useState('grid') // 'grid' | 'list'
  const [searchQuery, setSearchQuery] = useState('')
  const [showMobileFilters, setShowMobileFilters] = useState(false)

  // Determine base path for routing (demo vs real)
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'

  // Fetch templates on mount
  useEffect(() => {
    if (!isDemo) {
      dispatch(fetchTemplates(filters))
    }
  }, [dispatch, filters, isDemo])

  // Get templates to display (use demo data in demo mode)
  const displayTemplates = isDemo ? DEMO_TEMPLATES : templates

  // Filter templates by search query and filters
  const filteredTemplates = useMemo(() => {
    let result = [...displayTemplates]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.slug.toLowerCase().includes(query)
      )
    }

    // Apply category filter (client-side for demo mode)
    if (isDemo && filters.category) {
      result = result.filter((t) => t.category === filters.category)
    }

    // Apply VRAM filter (client-side for demo mode)
    if (isDemo && filters.min_vram) {
      result = result.filter((t) => t.gpu_min_vram <= filters.min_vram)
    }

    // Apply verified filter (client-side for demo mode)
    if (isDemo && filters.verified_only) {
      result = result.filter((t) => t.is_verified)
    }

    return result
  }, [displayTemplates, searchQuery, filters, isDemo])

  // Handle template deployment navigation
  const handleDeploy = (template) => {
    navigate(`${basePath}/templates/${template.slug}`)
  }

  // Handle refresh
  const handleRefresh = () => {
    dispatch(clearError())
    dispatch(fetchTemplates(filters))
  }

  // Render loading state
  if (loading && !displayTemplates.length) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-brand-500/10">
                <Store className="w-6 h-6 text-brand-400" />
              </div>
              <h1 className="text-2xl font-bold text-white">Template Marketplace</h1>
            </div>
            <p className="text-gray-400 text-sm">
              Pre-configured ML workloads ready to deploy in minutes
            </p>
          </div>

          {/* Skeleton loading */}
          <SkeletonList count={4} type="offer" />
        </div>
      </div>
    )
  }

  // Render error state
  if (error && !displayTemplates.length) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-brand-500/10">
                <Store className="w-6 h-6 text-brand-400" />
              </div>
              <h1 className="text-2xl font-bold text-white">Template Marketplace</h1>
            </div>
          </div>

          <ErrorState message={error} onRetry={handleRefresh} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-brand-500/10">
                  <Store className="w-6 h-6 text-brand-400" />
                </div>
                <h1 className="text-2xl font-bold text-white">Template Marketplace</h1>
                {isDemo && (
                  <Badge variant="warning" className="text-[10px]">
                    <Sparkles className="w-3 h-3 mr-1" />
                    Demo Mode
                  </Badge>
                )}
              </div>
              <p className="text-gray-400 text-sm">
                Pre-configured ML workloads ready to deploy in minutes. All templates include GPU drivers and dependencies.
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={loading}
                className="text-gray-400 hover:text-white"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>

              {/* View Mode Toggle */}
              <div className="flex items-center gap-1 p-1 bg-gray-800/50 rounded-lg">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-1.5 rounded transition-colors ${
                    viewMode === 'grid'
                      ? 'bg-brand-500 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-1.5 rounded transition-colors ${
                    viewMode === 'list'
                      ? 'bg-brand-500 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>

              {/* Mobile filters toggle */}
              <button
                onClick={() => setShowMobileFilters(!showMobileFilters)}
                className="md:hidden p-2 rounded-lg bg-gray-800/50 text-gray-400 hover:text-white"
              >
                <Filter className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="mb-6 p-4 rounded-xl bg-gray-800/30 border border-white/5">
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-brand-500/10">
                <Server className="w-4 h-4 text-brand-400" />
              </div>
              <div>
                <span className="text-lg font-bold text-white">{filteredTemplates.length}</span>
                <span className="text-gray-400 text-sm ml-1.5">
                  {filteredTemplates.length === 1 ? 'Template' : 'Templates'}
                </span>
              </div>
            </div>

            {/* Category stats */}
            {Object.entries(CATEGORY_ICONS).map(([category, Icon]) => {
              const count = filteredTemplates.filter((t) => t.category === category).length
              if (count === 0) return null
              return (
                <div key={category} className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-400">{count}</span>
                </div>
              )
            })}

            {/* Verified count */}
            {filteredTemplates.filter((t) => t.is_verified).length > 0 && (
              <div className="flex items-center gap-2">
                <Badge variant="success" className="text-[9px]">
                  {filteredTemplates.filter((t) => t.is_verified).length} Verified
                </Badge>
              </div>
            )}
          </div>
        </div>

        {/* Search and Filters Row */}
        <div className="mb-6 flex flex-col gap-4">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-gray-800/50 border-gray-700 text-white placeholder:text-gray-500 w-full md:max-w-md"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Compact Filters (Desktop) */}
          <div className="hidden md:block">
            <TemplateFilters compact />
          </div>

          {/* Mobile Filters Panel */}
          {showMobileFilters && (
            <div className="md:hidden">
              <TemplateFilters />
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="flex gap-6">
          {/* Sidebar Filters (Desktop) - Hidden for cleaner look, using compact filters above */}
          {/*
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <TemplateFilters />
          </aside>
          */}

          {/* Template Grid/List */}
          <main className="flex-1">
            {filteredTemplates.length === 0 ? (
              <EmptyState
                icon="search"
                title="No templates found"
                description={
                  searchQuery
                    ? `No templates match "${searchQuery}". Try a different search term.`
                    : 'No templates match the current filters. Try adjusting your filters.'
                }
                action={() => {
                  setSearchQuery('')
                  dispatch(resetFilters())
                }}
                actionText="Clear filters"
              />
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredTemplates.map((template) => (
                  <TemplateCard
                    key={template.id || template.slug}
                    template={template}
                    onDeploy={handleDeploy}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredTemplates.map((template) => (
                  <TemplateCard
                    key={template.id || template.slug}
                    template={template}
                    onDeploy={handleDeploy}
                    isCompact
                  />
                ))}
              </div>
            )}
          </main>
        </div>

        {/* Footer Info */}
        {filteredTemplates.length > 0 && (
          <div className="mt-8 p-4 rounded-xl bg-gray-800/20 border border-white/5">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-brand-500/10">
                <Sparkles className="w-4 h-4 text-brand-400" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-white mb-1">One-Click Deployment</h3>
                <p className="text-xs text-gray-400">
                  All templates come pre-configured with CUDA drivers, GPU dependencies, and optimized settings.
                  Click any template to see details and deploy to your preferred GPU in minutes.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

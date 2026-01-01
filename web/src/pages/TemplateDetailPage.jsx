/**
 * TemplateDetailPage - Template Detail & Deployment Page
 * Displays full template specs, GPU requirements, and deployment form
 * Following patterns from Machines.jsx
 */
import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  ArrowLeft,
  Cpu,
  Server,
  HardDrive,
  FileCode,
  Sparkles,
  Zap,
  Check,
  Image,
  MessageSquare,
  BookOpen,
  ExternalLink,
  Play,
  AlertCircle,
  CheckCircle,
  Loader2,
  RefreshCw,
  Copy,
  Terminal,
  Globe,
  Box,
  Settings,
} from 'lucide-react'
import {
  Card,
  Badge,
  Button,
  Alert,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  PageHeader,
  Spinner,
} from '../components/tailadmin-ui'
import { ErrorState } from '../components/ErrorState'
import { SkeletonList } from '../components/Skeleton'
import {
  fetchTemplateBySlug,
  fetchTemplateOffers,
  deployTemplate,
  selectSelectedTemplate,
  selectTemplateOffers,
  selectTemplatesLoading,
  selectOffersLoading,
  selectTemplatesError,
  selectDeployment,
  resetDeployment,
  clearSelectedTemplate,
} from '../store/slices/templateSlice'
import { isDemoMode } from '../utils/api'

// Demo templates for demo mode
const DEMO_TEMPLATES = {
  'jupyter-lab': {
    id: 1,
    slug: 'jupyter-lab',
    name: 'JupyterLab',
    description: 'Interactive Python development environment with GPU support for ML/AI workloads. Pre-configured with PyTorch 2.0 and popular data science libraries including NumPy, Pandas, Matplotlib, and Scikit-learn.',
    docker_image: 'jupyter/pytorch-notebook:latest',
    gpu_min_vram: 4,
    gpu_recommended_vram: 8,
    cuda_version: '11.8',
    ports: [8888],
    volumes: ['/home/jovyan/work'],
    launch_command: 'jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root',
    env_vars: { JUPYTER_ENABLE_LAB: 'yes' },
    category: 'notebook',
    is_verified: true,
    documentation_url: 'https://jupyter.org/documentation',
  },
  'stable-diffusion': {
    id: 2,
    slug: 'stable-diffusion',
    name: 'Stable Diffusion WebUI',
    description: 'AUTOMATIC1111 WebUI for generating AI images with Stable Diffusion. Supports ControlNet, LoRA, textual inversion, and many other extensions for advanced image generation workflows.',
    docker_image: 'ghcr.io/absolutelyludicrous/automatic1111-webui:latest',
    gpu_min_vram: 4,
    gpu_recommended_vram: 8,
    cuda_version: '11.8',
    ports: [7860],
    volumes: ['/app/models', '/app/outputs'],
    launch_command: 'python launch.py --listen --port 7860',
    env_vars: { COMMANDLINE_ARGS: '--medvram' },
    category: 'image_generation',
    is_verified: false,
    documentation_url: 'https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki',
  },
  'comfy-ui': {
    id: 3,
    slug: 'comfy-ui',
    name: 'ComfyUI',
    description: 'Node-based UI for Stable Diffusion with powerful workflow capabilities. Perfect for complex image generation pipelines with visual node programming.',
    docker_image: 'yanwk/comfyui-boot:latest',
    gpu_min_vram: 4,
    gpu_recommended_vram: 8,
    cuda_version: '11.8',
    ports: [8188],
    volumes: ['/app/models', '/app/output', '/app/input'],
    launch_command: 'python main.py --listen 0.0.0.0 --port 8188',
    env_vars: {},
    category: 'image_generation',
    is_verified: false,
    documentation_url: 'https://github.com/comfyanonymous/ComfyUI',
  },
  'vllm': {
    id: 4,
    slug: 'vllm',
    name: 'vLLM',
    description: 'High-performance LLM inference server with OpenAI-compatible API. Run models like Llama 2, Mistral, and more with optimized throughput.',
    docker_image: 'vllm/vllm-openai:latest',
    gpu_min_vram: 16,
    gpu_recommended_vram: 24,
    cuda_version: '11.8',
    ports: [8000],
    volumes: ['/root/.cache/huggingface'],
    launch_command: 'python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-7b-hf --host 0.0.0.0 --port 8000',
    env_vars: { HUGGING_FACE_HUB_TOKEN: '' },
    category: 'llm_inference',
    is_verified: false,
    documentation_url: 'https://docs.vllm.ai/',
  },
}

// Demo GPU offers
const DEMO_GPU_OFFERS = [
  { id: 1, gpu_name: 'RTX 3090', num_gpus: 1, gpu_ram: 24, dph_total: 0.45, reliability: 0.98 },
  { id: 2, gpu_name: 'RTX 4090', num_gpus: 1, gpu_ram: 24, dph_total: 0.65, reliability: 0.99 },
  { id: 3, gpu_name: 'A100 40GB', num_gpus: 1, gpu_ram: 40, dph_total: 1.20, reliability: 0.99 },
  { id: 4, gpu_name: 'RTX 3080', num_gpus: 1, gpu_ram: 10, dph_total: 0.25, reliability: 0.97 },
  { id: 5, gpu_name: 'RTX 4080', num_gpus: 1, gpu_ram: 16, dph_total: 0.40, reliability: 0.98 },
]

// Category icons and display info
const CATEGORY_INFO = {
  notebook: {
    icon: BookOpen,
    label: 'Notebook',
    color: 'primary',
  },
  image_generation: {
    icon: Image,
    label: 'Image Generation',
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

export default function TemplateDetailPage() {
  const { slug } = useParams()
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const isDemo = isDemoMode()

  // Redux state
  const template = useSelector(selectSelectedTemplate)
  const offers = useSelector(selectTemplateOffers)
  const loading = useSelector(selectTemplatesLoading)
  const offersLoading = useSelector(selectOffersLoading)
  const error = useSelector(selectTemplatesError)
  const deployment = useSelector(selectDeployment)

  // Local state
  const [selectedGpuId, setSelectedGpuId] = useState('')
  const [showDeployForm, setShowDeployForm] = useState(false)
  const [copiedCommand, setCopiedCommand] = useState(false)

  // Determine base path for routing (demo vs real)
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app'

  // Get template data (demo or real)
  const displayTemplate = isDemo ? DEMO_TEMPLATES[slug] : template
  const displayOffers = isDemo ? DEMO_GPU_OFFERS.filter(o => o.gpu_ram >= (displayTemplate?.gpu_min_vram || 0)) : offers

  // Fetch template and offers on mount
  useEffect(() => {
    if (!isDemo && slug) {
      dispatch(fetchTemplateBySlug(slug))
      dispatch(fetchTemplateOffers(slug))
    }

    // Cleanup on unmount
    return () => {
      dispatch(clearSelectedTemplate())
      dispatch(resetDeployment())
    }
  }, [dispatch, slug, isDemo])

  // Reset deployment state when changing templates
  useEffect(() => {
    dispatch(resetDeployment())
    setSelectedGpuId('')
    setShowDeployForm(false)
  }, [slug, dispatch])

  // Handle copy command to clipboard
  const handleCopyCommand = () => {
    if (displayTemplate?.launch_command) {
      navigator.clipboard.writeText(displayTemplate.launch_command)
      setCopiedCommand(true)
      setTimeout(() => setCopiedCommand(false), 2000)
    }
  }

  // Handle deploy
  const handleDeploy = async () => {
    if (!selectedGpuId) return

    if (isDemo) {
      // Simulate deployment in demo mode
      dispatch({ type: 'templates/deployTemplate/pending' })
      await new Promise(r => setTimeout(r, 2000))
      dispatch({
        type: 'templates/deployTemplate/fulfilled',
        payload: {
          instance_id: Date.now(),
          status: 'creating',
          message: 'Instance is being created...',
          connection_url: `https://demo-instance-${Date.now()}.vast.ai`,
        }
      })
      return
    }

    dispatch(deployTemplate({ slug, gpuId: parseInt(selectedGpuId) }))
  }

  // Handle refresh
  const handleRefresh = () => {
    if (!isDemo && slug) {
      dispatch(fetchTemplateBySlug(slug))
      dispatch(fetchTemplateOffers(slug))
    }
  }

  // Render loading state
  if (loading && !displayTemplate) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center gap-3 mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(`${basePath}/templates`)}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Templates
            </Button>
          </div>
          <SkeletonList count={1} type="card" />
        </div>
      </div>
    )
  }

  // Render error state
  if (error && !displayTemplate) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center gap-3 mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(`${basePath}/templates`)}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Templates
            </Button>
          </div>
          <ErrorState message={error} onRetry={handleRefresh} />
        </div>
      </div>
    )
  }

  // Template not found
  if (!displayTemplate) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center gap-3 mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(`${basePath}/templates`)}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Templates
            </Button>
          </div>
          <Card className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Template Not Found</h2>
            <p className="text-gray-400 mb-4">The template "{slug}" does not exist.</p>
            <Button variant="primary" onClick={() => navigate(`${basePath}/templates`)}>
              Browse Templates
            </Button>
          </Card>
        </div>
      </div>
    )
  }

  const categoryInfo = CATEGORY_INFO[displayTemplate.category] || CATEGORY_INFO.default
  const CategoryIcon = categoryInfo.icon
  const vramTier = getVramTier(displayTemplate.gpu_min_vram)

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Back Navigation */}
        <div className="flex items-center justify-between mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`${basePath}/templates`)}
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Templates
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
            className="text-gray-400 hover:text-white"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Template Header */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
            {/* Title Section */}
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className={`p-2.5 rounded-xl bg-${categoryInfo.color}-500/10`}>
                  <CategoryIcon className={`w-6 h-6 text-${categoryInfo.color}-400`} />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white">{displayTemplate.name}</h1>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={categoryInfo.color} className="text-[10px]">
                      {categoryInfo.label}
                    </Badge>
                    {displayTemplate.is_verified && (
                      <Badge variant="success" className="text-[10px]">
                        <Check className="w-2.5 h-2.5 mr-0.5" />
                        Verified
                      </Badge>
                    )}
                    {isDemo && (
                      <Badge variant="warning" className="text-[10px]">
                        <Sparkles className="w-2.5 h-2.5 mr-0.5" />
                        Demo Mode
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
              <p className="text-gray-400 text-sm max-w-2xl">
                {displayTemplate.description}
              </p>
            </div>

            {/* Quick Deploy Button */}
            <div className="flex-shrink-0">
              <Button
                variant="primary"
                size="lg"
                onClick={() => setShowDeployForm(true)}
                className="w-full lg:w-auto"
              >
                <Play className="w-5 h-5 mr-2" />
                Deploy Now
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* GPU Requirements Card */}
            <Card>
              <div className="p-5">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-brand-400" />
                  GPU Requirements
                </h2>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                    <div className="text-brand-400 font-mono text-2xl font-bold">
                      {displayTemplate.gpu_min_vram}GB
                    </div>
                    <div className="text-xs text-gray-500 uppercase mt-1">Min VRAM</div>
                  </div>
                  <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                    <div className="text-white font-mono text-2xl font-bold">
                      {displayTemplate.gpu_recommended_vram}GB
                    </div>
                    <div className="text-xs text-gray-500 uppercase mt-1">Recommended</div>
                  </div>
                  <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                    <div className="text-white font-mono text-2xl font-bold">
                      {displayTemplate.cuda_version}
                    </div>
                    <div className="text-xs text-gray-500 uppercase mt-1">CUDA Version</div>
                  </div>
                  <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                    <Badge variant={vramTier.variant} className="text-sm">
                      <Zap className="w-3 h-3 mr-1" />
                      {vramTier.label}
                    </Badge>
                    <div className="text-xs text-gray-500 uppercase mt-2">Tier</div>
                  </div>
                </div>

                <p className="text-xs text-gray-400">
                  {vramTier.description}. Recommended VRAM for optimal performance: {displayTemplate.gpu_recommended_vram}GB.
                </p>
              </div>
            </Card>

            {/* Technical Specs Card */}
            <Card>
              <div className="p-5">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-brand-400" />
                  Technical Specifications
                </h2>

                <div className="space-y-4">
                  {/* Docker Image */}
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                    <Box className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-gray-500 uppercase mb-1">Docker Image</div>
                      <code className="text-sm text-brand-300 break-all">
                        {displayTemplate.docker_image}
                      </code>
                    </div>
                  </div>

                  {/* Ports */}
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                    <Globe className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 uppercase mb-1">Exposed Ports</div>
                      <div className="flex flex-wrap gap-2">
                        {displayTemplate.ports?.map((port) => (
                          <Badge key={port} variant="gray" className="font-mono">
                            {port}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Volumes */}
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                    <HardDrive className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 uppercase mb-1">Persistent Volumes</div>
                      <div className="space-y-1">
                        {displayTemplate.volumes?.map((volume) => (
                          <code key={volume} className="block text-sm text-gray-300">
                            {volume}
                          </code>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Launch Command */}
                  <div className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                    <Terminal className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <div className="text-xs text-gray-500 uppercase">Launch Command</div>
                        <button
                          onClick={handleCopyCommand}
                          className="text-xs text-gray-400 hover:text-white flex items-center gap-1"
                        >
                          {copiedCommand ? (
                            <>
                              <CheckCircle className="w-3 h-3 text-success-400" />
                              Copied!
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      <code className="block text-sm text-gray-300 break-all">
                        {displayTemplate.launch_command}
                      </code>
                    </div>
                  </div>

                  {/* Environment Variables */}
                  {displayTemplate.env_vars && Object.keys(displayTemplate.env_vars).length > 0 && (
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-white/5">
                      <FileCode className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <div className="text-xs text-gray-500 uppercase mb-1">Environment Variables</div>
                        <div className="space-y-1">
                          {Object.entries(displayTemplate.env_vars).map(([key, value]) => (
                            <div key={key} className="flex items-center gap-2">
                              <code className="text-sm text-brand-300">{key}</code>
                              <span className="text-gray-500">=</span>
                              <code className="text-sm text-gray-300">{value || '(empty)'}</code>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* Documentation Link */}
            {displayTemplate.documentation_url && (
              <Card>
                <div className="p-5">
                  <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-brand-400" />
                    Documentation
                  </h2>
                  <p className="text-gray-400 text-sm mb-4">
                    Learn more about {displayTemplate.name} and how to get started.
                  </p>
                  <a
                    href={displayTemplate.documentation_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-brand-400 hover:text-brand-300 text-sm"
                  >
                    <ExternalLink className="w-4 h-4" />
                    View Official Documentation
                  </a>
                </div>
              </Card>
            )}
          </div>

          {/* Sidebar - Deploy Form */}
          <div className="lg:col-span-1">
            <Card className="sticky top-4">
              <div className="p-5">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-brand-400" />
                  Deploy Template
                </h2>

                {/* Deployment Success */}
                {deployment.status === 'succeeded' && (
                  <Alert variant="success" className="mb-4">
                    <div className="flex items-start gap-2">
                      <CheckCircle className="w-5 h-5 text-success-400 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-success-300">Deployment Started!</p>
                        <p className="text-xs text-success-400 mt-1">
                          Your instance is being created. It will be ready in a few minutes.
                        </p>
                        {deployment.result?.connection_url && (
                          <a
                            href={deployment.result.connection_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-success-300 hover:text-success-200 mt-2"
                          >
                            <ExternalLink className="w-3 h-3" />
                            Open Instance
                          </a>
                        )}
                      </div>
                    </div>
                  </Alert>
                )}

                {/* Deployment Error */}
                {deployment.status === 'failed' && (
                  <Alert variant="error" className="mb-4">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-5 h-5 text-error-400 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-error-300">Deployment Failed</p>
                        <p className="text-xs text-error-400 mt-1">
                          {deployment.error || 'An error occurred during deployment.'}
                        </p>
                      </div>
                    </div>
                  </Alert>
                )}

                {/* GPU Selection */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select GPU
                  </label>
                  {offersLoading && !displayOffers.length ? (
                    <div className="flex items-center justify-center p-4 bg-white/5 rounded-lg">
                      <Spinner size="sm" />
                      <span className="ml-2 text-sm text-gray-400">Loading offers...</span>
                    </div>
                  ) : displayOffers.length === 0 ? (
                    <div className="p-4 bg-warning-500/10 rounded-lg border border-warning-500/20">
                      <p className="text-sm text-warning-300">
                        No compatible GPUs available with {displayTemplate.gpu_min_vram}GB+ VRAM.
                      </p>
                    </div>
                  ) : (
                    <Select value={selectedGpuId} onValueChange={setSelectedGpuId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a GPU..." />
                      </SelectTrigger>
                      <SelectContent>
                        {displayOffers.map((offer) => (
                          <SelectItem key={offer.id} value={String(offer.id)}>
                            <div className="flex items-center justify-between w-full">
                              <span>{offer.gpu_name} ({offer.gpu_ram}GB)</span>
                              <span className="text-brand-400 ml-2">${offer.dph_total?.toFixed(2)}/hr</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>

                {/* Selected GPU Info */}
                {selectedGpuId && (
                  <div className="mb-4 p-3 rounded-lg bg-white/5 border border-white/10">
                    {(() => {
                      const selected = displayOffers.find(o => String(o.id) === selectedGpuId)
                      if (!selected) return null
                      return (
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-400">GPU</span>
                            <span className="text-white font-medium">{selected.gpu_name}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-400">VRAM</span>
                            <span className="text-white">{selected.gpu_ram}GB</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-400">Price</span>
                            <span className="text-brand-400 font-medium">${selected.dph_total?.toFixed(2)}/hr</span>
                          </div>
                          {selected.reliability && (
                            <div className="flex justify-between">
                              <span className="text-gray-400">Reliability</span>
                              <span className="text-success-400">{(selected.reliability * 100).toFixed(0)}%</span>
                            </div>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                )}

                {/* Deploy Button */}
                <Button
                  variant="primary"
                  size="lg"
                  className="w-full"
                  onClick={handleDeploy}
                  disabled={!selectedGpuId || deployment.status === 'deploying'}
                  loading={deployment.status === 'deploying'}
                >
                  {deployment.status === 'deploying' ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Deploying...
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5 mr-2" />
                      Deploy {displayTemplate.name}
                    </>
                  )}
                </Button>

                {/* Estimated Boot Time */}
                <p className="text-xs text-gray-500 text-center mt-3">
                  Estimated boot time: &lt;2 minutes
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

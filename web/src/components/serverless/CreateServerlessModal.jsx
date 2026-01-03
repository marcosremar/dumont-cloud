import { useState } from 'react'
import {
  X,
  Zap,
  Server,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  Cloud,
  MapPin,
  Gauge,
  HardDrive,
  Info
} from 'lucide-react'
import {
  AlertDialog,
  AlertDialogContent,
  Badge,
  Button,
  Input,
} from '../tailadmin-ui'

const GPU_OPTIONS = [
  { name: 'RTX 4090', vram: 24, price_ondemand: 0.31, price_spot: 0.18, available: 'high' },
  { name: 'RTX 4080', vram: 16, price_ondemand: 0.25, price_spot: 0.15, available: 'high' },
  { name: 'RTX 3090', vram: 24, price_ondemand: 0.20, price_spot: 0.12, available: 'medium' },
  { name: 'RTX 3080', vram: 10, price_ondemand: 0.15, price_spot: 0.09, available: 'high' },
  { name: 'A100 40GB', vram: 40, price_ondemand: 0.64, price_spot: 0.38, available: 'medium' },
  { name: 'A100 80GB', vram: 80, price_ondemand: 0.90, price_spot: 0.54, available: 'low' },
  { name: 'H100 PCIe', vram: 80, price_ondemand: 1.20, price_spot: 0.72, available: 'low' },
  { name: 'L40S', vram: 48, price_ondemand: 0.85, price_spot: 0.51, available: 'medium' },
]

const REGIONS = [
  { id: 'US', name: 'United States', latency: '15ms' },
  { id: 'EU', name: 'Europe', latency: '45ms' },
  { id: 'ASIA', name: 'Asia Pacific', latency: '180ms' },
]

// Model templates for quick deployment
const MODEL_TEMPLATES = [
  // Small models - great for testing (< 2GB VRAM)
  {
    id: 'qwen3-0.6b',
    name: 'Qwen3 0.6B',
    description: 'Small and fast model, ideal for testing',
    type: 'llm',
    docker_image: 'vllm/vllm-openai:latest',
    model_id: 'Qwen/Qwen3-0.6B',
    vram_required: 2,
    recommended_gpu: 'RTX 3080',
  },
  {
    id: 'qwen2.5-0.5b',
    name: 'Qwen 2.5 0.5B',
    description: 'Ultra light, < 1GB VRAM',
    type: 'llm',
    docker_image: 'vllm/vllm-openai:latest',
    model_id: 'Qwen/Qwen2.5-0.5B-Instruct',
    vram_required: 1,
    recommended_gpu: 'RTX 3080',
  },
  {
    id: 'phi-3-mini',
    name: 'Phi-3 Mini',
    description: 'Compact Microsoft model',
    type: 'llm',
    docker_image: 'vllm/vllm-openai:latest',
    model_id: 'microsoft/Phi-3-mini-4k-instruct',
    vram_required: 8,
    recommended_gpu: 'RTX 3080',
  },
  // Medium models
  {
    id: 'qwen2.5-7b',
    name: 'Qwen 2.5 7B',
    description: 'Balance between performance and cost',
    type: 'llm',
    docker_image: 'vllm/vllm-openai:latest',
    model_id: 'Qwen/Qwen2.5-7B-Instruct',
    vram_required: 14,
    recommended_gpu: 'RTX 4090',
  },
  {
    id: 'mistral-7b',
    name: 'Mistral 7B',
    description: 'Popular and efficient LLM',
    type: 'llm',
    docker_image: 'vllm/vllm-openai:latest',
    model_id: 'mistralai/Mistral-7B-Instruct-v0.3',
    vram_required: 14,
    recommended_gpu: 'RTX 4090',
  },
  {
    id: 'llama-3.1-8b',
    name: 'Llama 3.1 8B',
    description: 'High quality Meta LLM',
    type: 'llm',
    docker_image: 'vllm/vllm-openai:latest',
    model_id: 'meta-llama/Llama-3.1-8B-Instruct',
    vram_required: 16,
    recommended_gpu: 'RTX 4090',
  },
  // Speech
  {
    id: 'whisper-small',
    name: 'Whisper Small',
    description: 'Lightweight audio transcription',
    type: 'speech',
    docker_image: 'ghcr.io/huggingface/text-generation-inference:latest',
    model_id: 'openai/whisper-small',
    vram_required: 2,
    recommended_gpu: 'RTX 3080',
  },
  // Image
  {
    id: 'sdxl-turbo',
    name: 'SDXL Turbo',
    description: 'Fast image generation',
    type: 'image',
    docker_image: 'ghcr.io/huggingface/diffusers:latest',
    model_id: 'stabilityai/sdxl-turbo',
    vram_required: 12,
    recommended_gpu: 'RTX 4090',
  },
]

export default function CreateServerlessModal({ onClose, onCreate, error }) {
  const [step, setStep] = useState(1)
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [config, setConfig] = useState({
    name: '',
    machine_type: 'spot', // padrão: spot
    gpu_name: 'RTX 4090',
    region: 'US',
    min_instances: 0,
    max_instances: 5,
    target_latency_ms: 500,
    timeout_seconds: 300,
    docker_image: '',
    model_id: '',
    env_vars: {},
  })

  // Apply template when selected
  const applyTemplate = (template) => {
    setSelectedTemplate(template)
    setConfig({
      ...config,
      name: template.id,
      docker_image: template.docker_image,
      model_id: template.model_id,
      gpu_name: template.recommended_gpu,
    })
  }

  const selectedGpu = GPU_OPTIONS.find(g => g.name === config.gpu_name)
  const selectedRegion = REGIONS.find(r => r.id === config.region)

  const pricePerHour = config.machine_type === 'spot'
    ? selectedGpu?.price_spot
    : selectedGpu?.price_ondemand

  const savingsPercent = selectedGpu
    ? Math.round(((selectedGpu.price_ondemand - selectedGpu.price_spot) / selectedGpu.price_ondemand) * 100)
    : 0

  const handleSubmit = () => {
    onCreate(config)
  }

  return (
    <AlertDialog open={true} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent className="!max-w-[90vw] !w-[1200px] max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-dark-surface-card border-b border-white/10 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-brand-400" />
              Create Serverless Endpoint
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Auto-scaling GPU endpoint with optimized pricing
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content - com scroll */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Templates Section */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">Model Templates</h3>
            <p className="text-sm text-gray-400 mb-4">
              Select a pre-configured model or configure manually
            </p>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-4">
              {MODEL_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => applyTemplate(template)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    selectedTemplate?.id === template.id
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-white/10 bg-white/5 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-sm font-medium ${
                      selectedTemplate?.id === template.id ? 'text-white' : 'text-gray-300'
                    }`}>
                      {template.name}
                    </span>
                    <Badge className={`text-[10px] ${
                      template.type === 'llm' ? 'bg-blue-500/20 text-blue-400' :
                      template.type === 'speech' ? 'bg-purple-500/20 text-purple-400' :
                      'bg-pink-500/20 text-pink-400'
                    }`}>
                      {template.type}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{template.description}</p>
                  <div className="flex items-center gap-2 text-[10px] text-gray-500">
                    <span className="px-1.5 py-0.5 rounded bg-white/10">{template.vram_required}GB VRAM</span>
                    <span>{template.recommended_gpu}</span>
                  </div>
                </button>
              ))}
            </div>

            {selectedTemplate && (
              <div className="p-3 rounded-lg bg-brand-500/10 border border-brand-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-brand-400" />
                  <span className="text-sm font-medium text-brand-300">
                    Selected template: {selectedTemplate.name}
                  </span>
                </div>
                <div className="text-xs text-gray-400 font-mono">
                  Model ID: {selectedTemplate.model_id}
                </div>
              </div>
            )}
          </div>

          {/* Step 1: Básico */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">1. Basic Information</h3>
            <div className="space-y-4">
              <div>
                <Input
                  label="Endpoint Name"
                  value={config.name}
                  onChange={(e) => setConfig({ ...config, name: e.target.value })}
                  placeholder="my-llama2-endpoint"
                  helper={`URL: https://${config.name || 'my-endpoint'}.dumont.cloud`}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Docker Image"
                  value={config.docker_image}
                  onChange={(e) => setConfig({ ...config, docker_image: e.target.value })}
                  placeholder="vllm/vllm-openai:latest"
                />
                <Input
                  label="Model ID (HuggingFace)"
                  value={config.model_id}
                  onChange={(e) => setConfig({ ...config, model_id: e.target.value })}
                  placeholder="Qwen/Qwen3-0.6B"
                />
              </div>
            </div>
          </div>

          {/* Step 2: Machine Type (SPOT vs ON-DEMAND) */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">2. Machine Type</h3>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Spot Option */}
              <button
                onClick={() => setConfig({ ...config, machine_type: 'spot' })}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  config.machine_type === 'spot'
                    ? 'border-brand-500 bg-brand-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Zap className={`w-5 h-5 ${
                      config.machine_type === 'spot' ? 'text-brand-400' : 'text-gray-400'
                    }`} />
                    <span className={`font-bold ${
                      config.machine_type === 'spot' ? 'text-white' : 'text-gray-400'
                    }`}>
                      Spot
                    </span>
                  </div>
                  <Badge className="bg-brand-500/20 text-brand-400 border-brand-500/30">
                    -{savingsPercent}%
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  Cheaper, can be interrupted. Automatic auto-restart.
                </p>
                <div className="flex items-center gap-1 text-sm">
                  <DollarSign className="w-4 h-4 text-brand-400" />
                  <span className="font-bold text-white">
                    ${selectedGpu?.price_spot.toFixed(2)}
                  </span>
                  <span className="text-gray-500">/hr</span>
                </div>
              </button>

              {/* On-Demand Option */}
              <button
                onClick={() => setConfig({ ...config, machine_type: 'on-demand' })}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  config.machine_type === 'on-demand'
                    ? 'border-brand-500 bg-brand-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Server className={`w-5 h-5 ${
                      config.machine_type === 'on-demand' ? 'text-brand-400' : 'text-gray-400'
                    }`} />
                    <span className={`font-bold ${
                      config.machine_type === 'on-demand' ? 'text-white' : 'text-gray-400'
                    }`}>
                      On-Demand
                    </span>
                  </div>
                  <Badge className="bg-white/5 text-gray-400 border-white/10">
                    Stable
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  Fixed price, not interruptible. More stable and predictable.
                </p>
                <div className="flex items-center gap-1 text-sm">
                  <DollarSign className="w-4 h-4 text-gray-400" />
                  <span className="font-bold text-white">
                    ${selectedGpu?.price_ondemand.toFixed(2)}
                  </span>
                  <span className="text-gray-500">/hr</span>
                </div>
              </button>
            </div>

            {/* Spot Warning */}
            {config.machine_type === 'spot' && (
              <div className="p-4 rounded-lg bg-brand-500/10 border border-brand-500/20">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-brand-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="text-sm font-medium text-brand-300 mb-1">
                      How Spot works
                    </h4>
                    <ul className="text-xs text-gray-400 space-y-1">
                      <li>• Persistent disk in chosen region (Regional Volume + R2)</li>
                      <li>• GPU can be interrupted at any time</li>
                      <li>• Auto-restart finds new GPU and reconnects disk</li>
                      <li>• Save up to {savingsPercent}% vs On-Demand</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Step 3: GPU & Region */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">3. GPU and Region</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  <Server className="w-4 h-4 inline mr-1" />
                  GPU
                </label>
                <select
                  value={config.gpu_name}
                  onChange={(e) => setConfig({ ...config, gpu_name: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg bg-dark-surface-secondary border border-white/10 text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                >
                  {GPU_OPTIONS.map((gpu) => (
                    <option key={gpu.name} value={gpu.name}>
                      {gpu.name} - {gpu.vram}GB - ${config.machine_type === 'spot' ? gpu.price_spot : gpu.price_ondemand}/h
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  <MapPin className="w-4 h-4 inline mr-1" />
                  Region
                </label>
                <select
                  value={config.region}
                  onChange={(e) => setConfig({ ...config, region: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg bg-dark-surface-secondary border border-white/10 text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
                >
                  {REGIONS.map((region) => (
                    <option key={region.id} value={region.id}>
                      {region.name} ({region.latency})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Step 4: Auto-scaling */}
          <div>
            <h3 className="text-lg font-medium text-white mb-4">4. Auto-Scaling</h3>

            <div className="grid grid-cols-2 gap-4">
              <Input
                type="number"
                label="Min Instances"
                value={config.min_instances}
                onChange={(e) => setConfig({ ...config, min_instances: parseInt(e.target.value) || 0 })}
                min="0"
                max="10"
                helper="0 = scale to zero when idle"
              />

              <Input
                type="number"
                label="Max Instances"
                value={config.max_instances}
                onChange={(e) => setConfig({ ...config, max_instances: parseInt(e.target.value) || 1 })}
                min="1"
                max="50"
              />
            </div>
          </div>

          {/* Price Estimate */}
          <div className="p-4 rounded-lg bg-brand-500/10 border border-brand-500/20">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-white">Cost Estimate</h4>
              <DollarSign className="w-4 h-4 text-brand-400" />
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Per hour (1 instance):</span>
                <span className="font-bold text-white">${pricePerHour?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Max per day ({config.max_instances}x 24h):</span>
                <span className="font-bold text-white">
                  ${((pricePerHour || 0) * config.max_instances * 24).toFixed(2)}
                </span>
              </div>
              {config.machine_type === 'spot' && (
                <div className="flex justify-between text-brand-400">
                  <span>Savings vs On-Demand:</span>
                  <span className="font-bold">{savingsPercent}%</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-dark-surface-card border-t border-white/10 px-6 py-4">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span className="text-sm text-red-400">{error}</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmit}
              disabled={!config.name || !config.docker_image}
              icon={CheckCircle2}
            >
              Create Endpoint
            </Button>
          </div>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}

// Popular models catalog for Deploy Model page
// Based on Fireworks AI model offerings

export type ModelType = 'llm' | 'speech' | 'image' | 'embeddings';

export interface ModelInfo {
  id: string;
  name: string;
  size: string;
  vram: string;
  description: string;
}

export interface ModelWithType extends ModelInfo {
  type: ModelType;
}

export interface RuntimeInfo {
  name: string;
  port: number;
  description: string;
  docker: string;
}

export interface GatedModelInfo {
  provider: string;
  accessUrl: string;
  instructions: string;
}

export const POPULAR_MODELS: Record<ModelType, ModelInfo[]> = {
  llm: [
    { id: 'meta-llama/Llama-3.2-3B-Instruct', name: 'Llama 3.2 3B', size: '3B', vram: '6GB', description: 'Fast, efficient multilingual model' },
    { id: 'meta-llama/Llama-3.2-1B-Instruct', name: 'Llama 3.2 1B', size: '1B', vram: '2GB', description: 'Ultra-lightweight for edge deployment' },
    { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1 8B', size: '8B', vram: '16GB', description: 'Best balance of speed and quality' },
    { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen 2.5 7B', size: '7B', vram: '14GB', description: 'Excellent for coding and math' },
    { id: 'Qwen/Qwen2.5-3B-Instruct', name: 'Qwen 2.5 3B', size: '3B', vram: '6GB', description: 'Fast Chinese/English bilingual' },
    { id: 'mistralai/Mistral-7B-Instruct-v0.3', name: 'Mistral 7B', size: '7B', vram: '14GB', description: 'Strong reasoning capabilities' },
    { id: 'google/gemma-2-9b-it', name: 'Gemma 2 9B', size: '9B', vram: '18GB', description: "Google's latest open model" },
    { id: 'google/gemma-2-2b-it', name: 'Gemma 2 2B', size: '2B', vram: '4GB', description: 'Lightweight Google model' },
    { id: 'microsoft/Phi-3.5-mini-instruct', name: 'Phi 3.5 Mini', size: '3.8B', vram: '8GB', description: "Microsoft's efficient SLM" },
    { id: 'deepseek-ai/deepseek-coder-6.7b-instruct', name: 'DeepSeek Coder', size: '6.7B', vram: '14GB', description: 'Optimized for code generation' },
    { id: 'codellama/CodeLlama-7b-Instruct-hf', name: 'CodeLlama 7B', size: '7B', vram: '14GB', description: "Meta's code-specialized model" },
    { id: 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', name: 'TinyLlama 1.1B', size: '1.1B', vram: '2GB', description: 'Extremely fast inference' },
  ],
  speech: [
    { id: 'openai/whisper-large-v3', name: 'Whisper Large V3', size: '1.5B', vram: '4GB', description: 'Best accuracy, 99+ languages' },
    { id: 'openai/whisper-large-v3-turbo', name: 'Whisper V3 Turbo', size: '0.8B', vram: '2GB', description: '8x faster, similar quality' },
    { id: 'distil-whisper/distil-large-v3', name: 'Distil Whisper', size: '0.7B', vram: '2GB', description: '6x faster distilled model' },
    { id: 'openai/whisper-medium', name: 'Whisper Medium', size: '0.7B', vram: '2GB', description: 'Good balance speed/quality' },
    { id: 'openai/whisper-small', name: 'Whisper Small', size: '0.2B', vram: '1GB', description: 'Fast real-time transcription' },
  ],
  image: [
    { id: 'black-forest-labs/FLUX.1-schnell', name: 'FLUX.1 Schnell', size: '12B', vram: '24GB', description: 'Fastest FLUX model, 4 steps' },
    { id: 'black-forest-labs/FLUX.1-dev', name: 'FLUX.1 Dev', size: '12B', vram: '24GB', description: 'High quality, 20-50 steps' },
    { id: 'stabilityai/stable-diffusion-xl-base-1.0', name: 'SDXL', size: '3.5B', vram: '12GB', description: 'Stable Diffusion XL base' },
    { id: 'stabilityai/stable-diffusion-3-medium', name: 'SD3 Medium', size: '2B', vram: '8GB', description: 'Latest Stability AI model' },
    { id: 'runwayml/stable-diffusion-v1-5', name: 'SD 1.5', size: '0.9B', vram: '6GB', description: 'Classic, fast, well-supported' },
    { id: 'playgroundai/playground-v2.5-1024px', name: 'Playground V2.5', size: '2.5B', vram: '10GB', description: 'Artistic style generation' },
  ],
  embeddings: [
    { id: 'BAAI/bge-large-en-v1.5', name: 'BGE Large', size: '0.3B', vram: '1GB', description: 'Best open-source embeddings' },
    { id: 'BAAI/bge-m3', name: 'BGE M3', size: '0.5B', vram: '2GB', description: 'Multilingual, multi-task' },
    { id: 'intfloat/e5-large-v2', name: 'E5 Large', size: '0.3B', vram: '1GB', description: 'Strong retrieval performance' },
    { id: 'intfloat/multilingual-e5-large', name: 'E5 Multilingual', size: '0.5B', vram: '2GB', description: '100+ languages support' },
    { id: 'sentence-transformers/all-MiniLM-L6-v2', name: 'MiniLM L6', size: '0.02B', vram: '0.5GB', description: 'Ultra-fast, 384 dimensions' },
    { id: 'sentence-transformers/all-mpnet-base-v2', name: 'MPNet Base', size: '0.1B', vram: '0.5GB', description: '768 dimensions, high quality' },
    { id: 'nomic-ai/nomic-embed-text-v1.5', name: 'Nomic Embed', size: '0.1B', vram: '0.5GB', description: '8192 context, Matryoshka' },
    { id: 'jinaai/jina-embeddings-v2-base-en', name: 'Jina V2', size: '0.1B', vram: '0.5GB', description: '8192 context length' },
  ],
};

export const RUNTIMES: Record<ModelType, RuntimeInfo> = {
  llm: {
    name: 'vLLM',
    port: 8000,
    description: 'High-performance LLM inference',
    docker: 'vllm/vllm-openai:latest'
  },
  speech: {
    name: 'faster-whisper',
    port: 8001,
    description: 'CTranslate2 optimized Whisper',
    docker: 'fedirz/faster-whisper-server:latest'
  },
  image: {
    name: 'Diffusers',
    port: 8002,
    description: 'HuggingFace Diffusers pipeline',
    docker: 'pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime'
  },
  embeddings: {
    name: 'TEI',
    port: 8003,
    description: 'Text Embeddings Inference',
    docker: 'ghcr.io/huggingface/text-embeddings-inference:latest'
  },
};

export const MODEL_TYPE_ICONS: Record<ModelType, string> = {
  llm: 'MessageSquare',
  speech: 'Mic',
  image: 'Image',
  embeddings: 'Database',
};

export const MODEL_TYPE_COLORS: Record<ModelType, string> = {
  llm: 'emerald',
  speech: 'blue',
  image: 'purple',
  embeddings: 'amber',
};

// Auto-detect model type from HuggingFace model ID
export const detectModelType = (modelId: string): ModelType => {
  const id = modelId.toLowerCase();

  // Speech models
  if (/whisper|wav2vec|speech|audio|transcri/i.test(id)) return 'speech';

  // Image models
  if (/flux|diffusion|sdxl|stable-diffusion|dall-e|imagen|playground|kandinsky/i.test(id)) return 'image';

  // Embedding models
  if (/embed|bge|e5-|minilm|mpnet|sentence-transformer|nomic|jina/i.test(id)) return 'embeddings';

  // Default to LLM
  return 'llm';
};

// Extract model ID from HuggingFace URL
export const extractModelIdFromUrl = (url: string): string => {
  // Handle various URL formats
  // https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
  // https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct/tree/main
  // huggingface.co/meta-llama/Llama-3.2-3B-Instruct

  const match = url.match(/huggingface\.co\/([^\/]+\/[^\/\s]+)/i);
  return match ? match[1] : url;
};

// Get all models as flat array
export const getAllModels = (): ModelWithType[] => {
  return (Object.entries(POPULAR_MODELS) as [ModelType, ModelInfo[]][]).flatMap(([type, models]) =>
    models.map(model => ({ ...model, type }))
  );
};

// Get recommended GPU for model based on VRAM requirement
export const getRecommendedGPU = (vramRequired: string): string => {
  const vram = parseFloat(vramRequired);
  if (vram <= 4) return 'RTX 3080';
  if (vram <= 8) return 'RTX 3090';
  if (vram <= 16) return 'RTX 4090';
  if (vram <= 24) return 'RTX 4090';
  return 'A100';
};

// Gated models that require HuggingFace authentication
// These models need a valid HF_TOKEN to download
export const GATED_MODEL_PATTERNS: RegExp[] = [
  /^meta-llama\//i,           // All Llama models from Meta
  /^google\/gemma/i,          // Google Gemma models
  /^codellama\//i,            // CodeLlama models
  /^mistralai\/Mistral-/i,    // Some Mistral models are gated
  /^mistralai\/Mixtral-/i,    // Mixtral models
  /^bigscience\/bloom/i,      // BLOOM models
  /^tiiuae\/falcon/i,         // Falcon models
  /^stabilityai\/stable-diffusion-3/i,  // SD3 is gated
  /^black-forest-labs\/FLUX/i, // FLUX models are gated
];

// Check if a model requires HuggingFace authentication
export const isGatedModel = (modelId: string | null | undefined): boolean => {
  if (!modelId) return false;
  return GATED_MODEL_PATTERNS.some(pattern => pattern.test(modelId));
};

// Get gated model info message
export const getGatedModelInfo = (modelId: string | null | undefined): GatedModelInfo => {
  const id = modelId?.toLowerCase() || '';

  if (/meta-llama|codellama/i.test(id)) {
    return {
      provider: 'Meta',
      accessUrl: 'https://huggingface.co/meta-llama',
      instructions: "You need to accept Meta's license agreement on HuggingFace to access Llama models."
    };
  }
  if (/google\/gemma/i.test(id)) {
    return {
      provider: 'Google',
      accessUrl: 'https://huggingface.co/google/gemma-2-9b-it',
      instructions: "You need to accept Google's license agreement on HuggingFace to access Gemma models."
    };
  }
  if (/mistralai/i.test(id)) {
    return {
      provider: 'Mistral AI',
      accessUrl: 'https://huggingface.co/mistralai',
      instructions: 'Some Mistral models require accepting the license agreement on HuggingFace.'
    };
  }
  if (/black-forest-labs\/FLUX/i.test(id)) {
    return {
      provider: 'Black Forest Labs',
      accessUrl: 'https://huggingface.co/black-forest-labs',
      instructions: 'FLUX models require accepting the license agreement on HuggingFace.'
    };
  }
  if (/stabilityai\/stable-diffusion-3/i.test(id)) {
    return {
      provider: 'Stability AI',
      accessUrl: 'https://huggingface.co/stabilityai/stable-diffusion-3-medium',
      instructions: "SD3 requires accepting Stability AI's license agreement on HuggingFace."
    };
  }

  return {
    provider: 'Unknown',
    accessUrl: `https://huggingface.co/${modelId}`,
    instructions: 'This model may require accepting a license agreement on HuggingFace.'
  };
};

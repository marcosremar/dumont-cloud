// Demo machines data with rich details for demo mode
export const DEMO_MACHINES = [
  {
    id: 12345678,
    gpu_name: 'RTX 4090',
    actual_status: 'running',
    status: 'running',
    gpu_ram: 24576,
    cpu_cores: 16,
    cpu_ram: 64,
    disk_space: 500,
    dph_total: 0.45,
    total_dph: 0.46,
    public_ipaddr: '203.0.113.45',
    ssh_host: 'ssh4.vast.ai',
    ssh_port: 22345,
    start_date: new Date(Date.now() - 3600000 * 5).toISOString(),
    label: 'dev-workspace-01',
    gpu_util: 45.2,
    gpu_temp: 62,
    ports: {
      '22/tcp': [{ HostPort: '22345' }],
      '8080/tcp': [{ HostPort: '8080' }]
    },
    provider: 'vast.ai',
    cpu_standby: {
      enabled: true,
      provider: 'gcp',
      name: 'standby-dev-us',
      zone: 'us-central1-a',
      ip: '35.192.45.123',
      machine_type: 'e2-medium',
      status: 'running',
      dph_total: 0.01,
      sync_enabled: true,
      sync_count: 234,
      state: 'ready'
    }
  },
  {
    id: 23456789,
    gpu_name: 'A100 80GB',
    actual_status: 'running',
    status: 'running',
    gpu_ram: 81920,
    cpu_cores: 32,
    cpu_ram: 128,
    disk_space: 1000,
    dph_total: 2.10,
    total_dph: 2.11,
    public_ipaddr: '198.51.100.78',
    ssh_host: 'ssh7.vast.ai',
    ssh_port: 22789,
    start_date: new Date(Date.now() - 3600000 * 12).toISOString(),
    label: 'ml-training-large',
    gpu_util: 92.5,
    gpu_temp: 71,
    ports: {
      '22/tcp': [{ HostPort: '22789' }],
      '8080/tcp': [{ HostPort: '8080' }],
      '6006/tcp': [{ HostPort: '6006' }]
    },
    provider: 'vast.ai',
    cpu_standby: {
      enabled: true,
      provider: 'gcp',
      name: 'standby-ml-eu',
      zone: 'europe-west1-b',
      ip: '35.204.123.45',
      machine_type: 'e2-medium',
      status: 'running',
      dph_total: 0.01,
      sync_enabled: true,
      sync_count: 567,
      state: 'syncing'
    }
  },
  {
    id: 34567890,
    gpu_name: 'RTX 3090',
    actual_status: 'stopped',
    status: 'stopped',
    gpu_ram: 24576,
    cpu_cores: 12,
    cpu_ram: 48,
    disk_space: 250,
    dph_total: 0.35,
    total_dph: 0.35,
    ssh_host: 'ssh2.vast.ai',
    ssh_port: 22123,
    label: 'stable-diffusion-dev',
    provider: 'vast.ai',
    cpu_standby: null
  },
  {
    id: 45678901,
    gpu_name: 'RTX 4080',
    actual_status: 'stopped',
    status: 'stopped',
    gpu_ram: 16384,
    cpu_cores: 8,
    cpu_ram: 32,
    disk_space: 200,
    dph_total: 0.28,
    total_dph: 0.28,
    ssh_host: 'ssh5.vast.ai',
    ssh_port: 22456,
    label: 'inference-api',
    provider: 'vast.ai',
    cpu_standby: null
  },
  {
    id: 56789012,
    gpu_name: 'H100 80GB',
    actual_status: 'running',
    status: 'running',
    gpu_ram: 81920,
    cpu_cores: 64,
    cpu_ram: 256,
    disk_space: 2000,
    dph_total: 3.50,
    total_dph: 3.51,
    public_ipaddr: '192.0.2.100',
    ssh_host: 'ssh9.vast.ai',
    ssh_port: 22999,
    start_date: new Date(Date.now() - 3600000 * 2).toISOString(),
    label: 'llm-finetuning',
    gpu_util: 78.3,
    gpu_temp: 68,
    ports: {
      '22/tcp': [{ HostPort: '22999' }],
      '8080/tcp': [{ HostPort: '8080' }]
    },
    provider: 'vast.ai',
    cpu_standby: {
      enabled: true,
      provider: 'gcp',
      name: 'standby-llm-us',
      zone: 'us-east1-b',
      ip: '35.231.89.123',
      machine_type: 'e2-standard-4',
      status: 'running',
      dph_total: 0.02,
      sync_enabled: true,
      sync_count: 89,
      state: 'ready'
    }
  }
]

// Demo deployed models for Models page
export const DEMO_MODELS = [
  {
    id: 'model-001',
    name: 'Llama 3.2 3B Instruct',
    model_id: 'meta-llama/Llama-3.2-3B-Instruct',
    model_type: 'llm',
    status: 'running',
    runtime: 'vLLM',
    gpu_name: 'RTX 4090',
    num_gpus: 1,
    dph_total: 0.45,
    endpoint_url: 'https://llm-001.dumont.cloud/v1',
    access_type: 'private',
    api_key: 'dm-sk-xxxx-xxxx-xxxx-xxxx-demo001',
    progress: 100,
    status_message: 'Running',
    port: 8000,
  },
  {
    id: 'model-002',
    name: 'Whisper Large V3',
    model_id: 'openai/whisper-large-v3',
    model_type: 'speech',
    status: 'running',
    runtime: 'faster-whisper',
    gpu_name: 'RTX 3090',
    num_gpus: 1,
    dph_total: 0.35,
    endpoint_url: 'https://whisper-001.dumont.cloud/transcribe',
    access_type: 'public',
    progress: 100,
    status_message: 'Running',
    port: 8001,
  },
  {
    id: 'model-003',
    name: 'FLUX.1 Schnell',
    model_id: 'black-forest-labs/FLUX.1-schnell',
    model_type: 'image',
    status: 'deploying',
    runtime: 'diffusers',
    gpu_name: 'RTX 4090',
    num_gpus: 1,
    dph_total: 0.45,
    progress: 67,
    status_message: 'Downloading model weights...',
    port: 8002,
  },
]

// Fireworks AI compatible models - comprehensive catalog for vLLM deployment
// Based on Fireworks AI, HuggingFace, and vLLM supported models
export const FIREWORKS_MODELS = {
  llm: [
    // ========== LLAMA SERIES ==========
    // Llama 4 (Latest)
    { id: 'meta-llama/Llama-4-Scout-17B-16E-Instruct', name: 'Llama 4 Scout 17B', size: '17B', vram: 34, featured: true, category: 'llama' },
    { id: 'meta-llama/Llama-4-Maverick-17B-128E-Instruct', name: 'Llama 4 Maverick', size: '17B', vram: 34, featured: true, category: 'llama' },
    // Llama 3.3
    { id: 'meta-llama/Llama-3.3-70B-Instruct', name: 'Llama 3.3 70B Instruct', size: '70B', vram: 140, featured: true, category: 'llama' },
    // Llama 3.2 Series
    { id: 'meta-llama/Llama-3.2-1B-Instruct', name: 'Llama 3.2 1B Instruct', size: '1B', vram: 4, featured: true, category: 'llama' },
    { id: 'meta-llama/Llama-3.2-3B-Instruct', name: 'Llama 3.2 3B Instruct', size: '3B', vram: 8, featured: true, category: 'llama' },
    { id: 'meta-llama/Llama-3.2-11B-Vision-Instruct', name: 'Llama 3.2 11B Vision', size: '11B', vram: 22, featured: false, category: 'llama' },
    { id: 'meta-llama/Llama-3.2-90B-Vision-Instruct', name: 'Llama 3.2 90B Vision', size: '90B', vram: 180, featured: false, category: 'llama' },
    // Llama 3.1 Series
    { id: 'meta-llama/Llama-3.1-8B-Instruct', name: 'Llama 3.1 8B Instruct', size: '8B', vram: 16, featured: true, category: 'llama' },
    { id: 'meta-llama/Llama-3.1-70B-Instruct', name: 'Llama 3.1 70B Instruct', size: '70B', vram: 140, featured: true, category: 'llama' },
    { id: 'meta-llama/Llama-3.1-405B-Instruct', name: 'Llama 3.1 405B Instruct', size: '405B', vram: 810, featured: false, category: 'llama' },
    { id: 'meta-llama/Llama-3.1-405B-Instruct-FP8', name: 'Llama 3.1 405B FP8', size: '405B', vram: 405, featured: false, category: 'llama' },
    // Llama 3 Series
    { id: 'meta-llama/Meta-Llama-3-8B-Instruct', name: 'Llama 3 8B Instruct', size: '8B', vram: 16, featured: false, category: 'llama' },
    { id: 'meta-llama/Meta-Llama-3-70B-Instruct', name: 'Llama 3 70B Instruct', size: '70B', vram: 140, featured: false, category: 'llama' },

    // ========== QWEN SERIES ==========
    // Qwen 3 (Latest)
    { id: 'Qwen/Qwen3-235B-A22B', name: 'Qwen 3 235B MoE', size: '235B', vram: 470, featured: true, category: 'qwen' },
    { id: 'Qwen/Qwen3-30B-A3B', name: 'Qwen 3 30B MoE', size: '30B', vram: 60, featured: true, category: 'qwen' },
    { id: 'Qwen/Qwen3-32B', name: 'Qwen 3 32B', size: '32B', vram: 64, featured: true, category: 'qwen' },
    { id: 'Qwen/Qwen3-14B', name: 'Qwen 3 14B', size: '14B', vram: 28, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen3-8B', name: 'Qwen 3 8B', size: '8B', vram: 16, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen3-4B', name: 'Qwen 3 4B', size: '4B', vram: 8, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen3-1.7B', name: 'Qwen 3 1.7B', size: '1.7B', vram: 4, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen3-0.6B', name: 'Qwen 3 0.6B', size: '0.6B', vram: 2, featured: false, category: 'qwen' },
    // Qwen 2.5 Series
    { id: 'Qwen/Qwen2.5-0.5B-Instruct', name: 'Qwen 2.5 0.5B Instruct', size: '0.5B', vram: 2, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-1.5B-Instruct', name: 'Qwen 2.5 1.5B Instruct', size: '1.5B', vram: 4, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-3B-Instruct', name: 'Qwen 2.5 3B Instruct', size: '3B', vram: 6, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen 2.5 7B Instruct', size: '7B', vram: 14, featured: true, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-14B-Instruct', name: 'Qwen 2.5 14B Instruct', size: '14B', vram: 28, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-32B-Instruct', name: 'Qwen 2.5 32B Instruct', size: '32B', vram: 64, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen 2.5 72B Instruct', size: '72B', vram: 144, featured: true, category: 'qwen' },
    // Qwen Coder Series
    { id: 'Qwen/Qwen2.5-Coder-0.5B-Instruct', name: 'Qwen 2.5 Coder 0.5B', size: '0.5B', vram: 2, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-Coder-1.5B-Instruct', name: 'Qwen 2.5 Coder 1.5B', size: '1.5B', vram: 4, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-Coder-3B-Instruct', name: 'Qwen 2.5 Coder 3B', size: '3B', vram: 6, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-Coder-7B-Instruct', name: 'Qwen 2.5 Coder 7B', size: '7B', vram: 14, featured: true, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-Coder-14B-Instruct', name: 'Qwen 2.5 Coder 14B', size: '14B', vram: 28, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2.5-Coder-32B-Instruct', name: 'Qwen 2.5 Coder 32B', size: '32B', vram: 64, featured: true, category: 'qwen' },
    { id: 'Qwen/Qwen3-Coder-480B-A35B-Instruct', name: 'Qwen 3 Coder 480B MoE', size: '480B', vram: 960, featured: false, category: 'qwen' },
    // Qwen Vision
    { id: 'Qwen/Qwen2-VL-7B-Instruct', name: 'Qwen 2 VL 7B', size: '7B', vram: 14, featured: false, category: 'qwen' },
    { id: 'Qwen/Qwen2-VL-72B-Instruct', name: 'Qwen 2 VL 72B', size: '72B', vram: 144, featured: false, category: 'qwen' },

    // ========== DEEPSEEK SERIES ==========
    { id: 'deepseek-ai/DeepSeek-V3', name: 'DeepSeek V3', size: '671B', vram: 1342, featured: true, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-V3-0324', name: 'DeepSeek V3 (0324)', size: '671B', vram: 1342, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1', name: 'DeepSeek R1', size: '671B', vram: 1342, featured: true, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-0528', name: 'DeepSeek R1 (0528)', size: '671B', vram: 1342, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B', name: 'DeepSeek R1 Distill 8B', size: '8B', vram: 16, featured: true, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Llama-70B', name: 'DeepSeek R1 Distill 70B', size: '70B', vram: 140, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B', name: 'DeepSeek R1 Distill 1.5B', size: '1.5B', vram: 4, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', name: 'DeepSeek R1 Distill Qwen 7B', size: '7B', vram: 14, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-14B', name: 'DeepSeek R1 Distill Qwen 14B', size: '14B', vram: 28, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', name: 'DeepSeek R1 Distill Qwen 32B', size: '32B', vram: 64, featured: true, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-V2-Lite-Chat', name: 'DeepSeek V2 Lite Chat', size: '16B', vram: 32, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-V2.5', name: 'DeepSeek V2.5', size: '236B', vram: 472, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/DeepSeek-Coder-V2-Instruct', name: 'DeepSeek Coder V2', size: '21B', vram: 42, featured: true, category: 'deepseek' },
    { id: 'deepseek-ai/deepseek-coder-6.7b-instruct', name: 'DeepSeek Coder 6.7B', size: '6.7B', vram: 14, featured: false, category: 'deepseek' },
    { id: 'deepseek-ai/deepseek-coder-33b-instruct', name: 'DeepSeek Coder 33B', size: '33B', vram: 66, featured: false, category: 'deepseek' },

    // ========== MISTRAL SERIES ==========
    { id: 'mistralai/Mistral-7B-Instruct-v0.3', name: 'Mistral 7B Instruct v0.3', size: '7B', vram: 14, featured: true, category: 'mistral' },
    { id: 'mistralai/Mistral-Small-24B-Instruct-2501', name: 'Mistral Small 24B', size: '24B', vram: 48, featured: true, category: 'mistral' },
    { id: 'mistralai/Mistral-Nemo-Instruct-2407', name: 'Mistral Nemo 12B', size: '12B', vram: 24, featured: true, category: 'mistral' },
    { id: 'mistralai/Mistral-Large-Instruct-2407', name: 'Mistral Large', size: '123B', vram: 246, featured: false, category: 'mistral' },
    { id: 'mistralai/Mixtral-8x7B-Instruct-v0.1', name: 'Mixtral 8x7B Instruct', size: '47B', vram: 94, featured: true, category: 'mistral' },
    { id: 'mistralai/Mixtral-8x22B-Instruct-v0.1', name: 'Mixtral 8x22B Instruct', size: '141B', vram: 282, featured: false, category: 'mistral' },
    { id: 'mistralai/Codestral-22B-v0.1', name: 'Codestral 22B', size: '22B', vram: 44, featured: true, category: 'mistral' },
    { id: 'mistralai/Mathstral-7B-v0.1', name: 'Mathstral 7B', size: '7B', vram: 14, featured: false, category: 'mistral' },

    // ========== GOOGLE GEMMA SERIES ==========
    { id: 'google/gemma-2-2b-it', name: 'Gemma 2 2B IT', size: '2B', vram: 5, featured: false, category: 'gemma' },
    { id: 'google/gemma-2-9b-it', name: 'Gemma 2 9B IT', size: '9B', vram: 18, featured: true, category: 'gemma' },
    { id: 'google/gemma-2-27b-it', name: 'Gemma 2 27B IT', size: '27B', vram: 54, featured: true, category: 'gemma' },
    { id: 'google/gemma-3-12b-it', name: 'Gemma 3 12B IT', size: '12B', vram: 24, featured: true, category: 'gemma' },
    { id: 'google/gemma-3-27b-it', name: 'Gemma 3 27B IT', size: '27B', vram: 54, featured: true, category: 'gemma' },
    { id: 'google/codegemma-7b-it', name: 'CodeGemma 7B', size: '7B', vram: 14, featured: false, category: 'gemma' },

    // ========== MICROSOFT PHI SERIES ==========
    { id: 'microsoft/Phi-3-mini-4k-instruct', name: 'Phi 3 Mini 4K', size: '3.8B', vram: 8, featured: true, category: 'phi' },
    { id: 'microsoft/Phi-3-mini-128k-instruct', name: 'Phi 3 Mini 128K', size: '3.8B', vram: 8, featured: false, category: 'phi' },
    { id: 'microsoft/Phi-3-small-8k-instruct', name: 'Phi 3 Small 8K', size: '7B', vram: 14, featured: false, category: 'phi' },
    { id: 'microsoft/Phi-3-small-128k-instruct', name: 'Phi 3 Small 128K', size: '7B', vram: 14, featured: false, category: 'phi' },
    { id: 'microsoft/Phi-3-medium-4k-instruct', name: 'Phi 3 Medium 4K', size: '14B', vram: 28, featured: false, category: 'phi' },
    { id: 'microsoft/Phi-3-medium-128k-instruct', name: 'Phi 3 Medium 128K', size: '14B', vram: 28, featured: false, category: 'phi' },
    { id: 'microsoft/Phi-3.5-mini-instruct', name: 'Phi 3.5 Mini', size: '3.8B', vram: 8, featured: true, category: 'phi' },
    { id: 'microsoft/Phi-3.5-MoE-instruct', name: 'Phi 3.5 MoE', size: '42B', vram: 84, featured: false, category: 'phi' },
    { id: 'microsoft/Phi-4', name: 'Phi 4', size: '14B', vram: 28, featured: true, category: 'phi' },
    { id: 'microsoft/Phi-4-mini-instruct', name: 'Phi 4 Mini', size: '3.8B', vram: 8, featured: true, category: 'phi' },

    // ========== NVIDIA NEMOTRON ==========
    { id: 'nvidia/Llama-3.1-Nemotron-70B-Instruct-HF', name: 'Nemotron 70B', size: '70B', vram: 140, featured: true, category: 'nvidia' },
    { id: 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8', name: 'Nemotron Nano 30B', size: '30B', vram: 60, featured: false, category: 'nvidia' },
    { id: 'nvidia/Mistral-NeMo-Minitron-8B-Instruct', name: 'Minitron 8B', size: '8B', vram: 16, featured: false, category: 'nvidia' },

    // ========== COHERE ==========
    { id: 'CohereForAI/c4ai-command-r-v01', name: 'Command R', size: '35B', vram: 70, featured: false, category: 'cohere' },
    { id: 'CohereForAI/c4ai-command-r-plus', name: 'Command R+', size: '104B', vram: 208, featured: true, category: 'cohere' },
    { id: 'CohereForAI/aya-expanse-8b', name: 'Aya Expanse 8B', size: '8B', vram: 16, featured: false, category: 'cohere' },
    { id: 'CohereForAI/aya-expanse-32b', name: 'Aya Expanse 32B', size: '32B', vram: 64, featured: false, category: 'cohere' },

    // ========== YI SERIES ==========
    { id: '01-ai/Yi-1.5-6B-Chat', name: 'Yi 1.5 6B Chat', size: '6B', vram: 12, featured: false, category: 'yi' },
    { id: '01-ai/Yi-1.5-9B-Chat', name: 'Yi 1.5 9B Chat', size: '9B', vram: 18, featured: false, category: 'yi' },
    { id: '01-ai/Yi-1.5-34B-Chat', name: 'Yi 1.5 34B Chat', size: '34B', vram: 68, featured: false, category: 'yi' },
    { id: '01-ai/Yi-Coder-9B-Chat', name: 'Yi Coder 9B', size: '9B', vram: 18, featured: false, category: 'yi' },

    // ========== CODING MODELS ==========
    { id: 'bigcode/starcoder2-3b', name: 'StarCoder2 3B', size: '3B', vram: 6, featured: false, category: 'coding' },
    { id: 'bigcode/starcoder2-7b', name: 'StarCoder2 7B', size: '7B', vram: 14, featured: false, category: 'coding' },
    { id: 'bigcode/starcoder2-15b', name: 'StarCoder2 15B', size: '15B', vram: 30, featured: true, category: 'coding' },
    { id: 'codellama/CodeLlama-7b-Instruct-hf', name: 'CodeLlama 7B', size: '7B', vram: 14, featured: false, category: 'coding' },
    { id: 'codellama/CodeLlama-13b-Instruct-hf', name: 'CodeLlama 13B', size: '13B', vram: 26, featured: false, category: 'coding' },
    { id: 'codellama/CodeLlama-34b-Instruct-hf', name: 'CodeLlama 34B', size: '34B', vram: 68, featured: true, category: 'coding' },
    { id: 'codellama/CodeLlama-70b-Instruct-hf', name: 'CodeLlama 70B', size: '70B', vram: 140, featured: false, category: 'coding' },

    // ========== OTHER NOTABLE MODELS ==========
    // Falcon
    { id: 'tiiuae/falcon-7b-instruct', name: 'Falcon 7B Instruct', size: '7B', vram: 14, featured: false, category: 'other' },
    { id: 'tiiuae/falcon-40b-instruct', name: 'Falcon 40B Instruct', size: '40B', vram: 80, featured: false, category: 'other' },
    { id: 'tiiuae/falcon-180B-chat', name: 'Falcon 180B Chat', size: '180B', vram: 360, featured: false, category: 'other' },
    // MiniMax
    { id: 'MiniMaxAI/MiniMax-M2', name: 'MiniMax M2', size: '456B', vram: 912, featured: false, category: 'other' },
    // GLM
    { id: 'THUDM/glm-4-9b-chat', name: 'GLM 4 9B Chat', size: '9B', vram: 18, featured: false, category: 'other' },
    { id: 'THUDM/chatglm3-6b', name: 'ChatGLM3 6B', size: '6B', vram: 12, featured: false, category: 'other' },
    // InternLM
    { id: 'internlm/internlm2_5-7b-chat', name: 'InternLM2.5 7B Chat', size: '7B', vram: 14, featured: false, category: 'other' },
    { id: 'internlm/internlm2_5-20b-chat', name: 'InternLM2.5 20B Chat', size: '20B', vram: 40, featured: false, category: 'other' },
    // Vicuna
    { id: 'lmsys/vicuna-7b-v1.5', name: 'Vicuna 7B v1.5', size: '7B', vram: 14, featured: false, category: 'other' },
    { id: 'lmsys/vicuna-13b-v1.5', name: 'Vicuna 13B v1.5', size: '13B', vram: 26, featured: false, category: 'other' },
    // Zephyr
    { id: 'HuggingFaceH4/zephyr-7b-beta', name: 'Zephyr 7B Beta', size: '7B', vram: 14, featured: false, category: 'other' },
    // OpenChat
    { id: 'openchat/openchat-3.5-0106', name: 'OpenChat 3.5', size: '7B', vram: 14, featured: false, category: 'other' },
    // Nous Research
    { id: 'NousResearch/Hermes-3-Llama-3.1-8B', name: 'Hermes 3 8B', size: '8B', vram: 16, featured: false, category: 'other' },
    { id: 'NousResearch/Hermes-3-Llama-3.1-70B', name: 'Hermes 3 70B', size: '70B', vram: 140, featured: false, category: 'other' },
    // WizardLM
    { id: 'WizardLMTeam/WizardLM-2-7B', name: 'WizardLM 2 7B', size: '7B', vram: 14, featured: false, category: 'other' },
    { id: 'WizardLMTeam/WizardCoder-33B-V1.1', name: 'WizardCoder 33B', size: '33B', vram: 66, featured: false, category: 'other' },
    // TinyLlama
    { id: 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', name: 'TinyLlama 1.1B', size: '1.1B', vram: 3, featured: false, category: 'other' },
    // SmolLM
    { id: 'HuggingFaceTB/SmolLM2-360M-Instruct', name: 'SmolLM2 360M', size: '360M', vram: 1, featured: false, category: 'other' },
    { id: 'HuggingFaceTB/SmolLM2-1.7B-Instruct', name: 'SmolLM2 1.7B', size: '1.7B', vram: 4, featured: false, category: 'other' },
    // LiquidAI
    { id: 'LiquidAI/LFM2-2.6B', name: 'LiquidAI LFM2 2.6B', size: '2.6B', vram: 6, featured: false, category: 'other' },
  ],
  speech: [
    // OpenAI Whisper Series
    { id: 'openai/whisper-large-v3', name: 'Whisper Large V3', size: '1.5B', vram: 4, featured: true },
    { id: 'openai/whisper-large-v3-turbo', name: 'Whisper Large V3 Turbo', size: '0.8B', vram: 2, featured: true },
    { id: 'openai/whisper-large-v2', name: 'Whisper Large V2', size: '1.5B', vram: 4, featured: false },
    { id: 'openai/whisper-medium', name: 'Whisper Medium', size: '769M', vram: 2, featured: false },
    { id: 'openai/whisper-small', name: 'Whisper Small', size: '244M', vram: 1, featured: false },
    { id: 'openai/whisper-base', name: 'Whisper Base', size: '74M', vram: 0.5, featured: false },
    { id: 'openai/whisper-tiny', name: 'Whisper Tiny', size: '39M', vram: 0.5, featured: false },
    // Distil Whisper
    { id: 'distil-whisper/distil-large-v3', name: 'Distil Whisper Large V3', size: '756M', vram: 2, featured: true },
    { id: 'distil-whisper/distil-medium.en', name: 'Distil Whisper Medium EN', size: '394M', vram: 1, featured: false },
    { id: 'distil-whisper/distil-small.en', name: 'Distil Whisper Small EN', size: '166M', vram: 0.5, featured: false },
    // Other ASR
    { id: 'facebook/seamless-m4t-v2-large', name: 'SeamlessM4T V2 Large', size: '2.3B', vram: 5, featured: false },
    { id: 'nvidia/canary-1b', name: 'NVIDIA Canary 1B', size: '1B', vram: 2, featured: false },
    // TTS
    { id: 'parler-tts/parler-tts-mini-v1', name: 'Parler TTS Mini', size: '880M', vram: 2, featured: true },
    { id: 'parler-tts/parler-tts-large-v1', name: 'Parler TTS Large', size: '2.3B', vram: 5, featured: false },
    { id: 'coqui/XTTS-v2', name: 'XTTS V2', size: '467M', vram: 1, featured: true },
    { id: 'microsoft/speecht5_tts', name: 'SpeechT5 TTS', size: '143M', vram: 0.5, featured: false },
    { id: 'suno/bark', name: 'Suno Bark', size: '1.2B', vram: 3, featured: false },
  ],
  image: [
    // FLUX Series
    { id: 'black-forest-labs/FLUX.1-schnell', name: 'FLUX.1 Schnell', size: '12B', vram: 24, featured: true },
    { id: 'black-forest-labs/FLUX.1-dev', name: 'FLUX.1 Dev', size: '12B', vram: 24, featured: true },
    { id: 'black-forest-labs/FLUX.1-Fill-dev', name: 'FLUX.1 Fill Dev', size: '12B', vram: 24, featured: false },
    { id: 'black-forest-labs/FLUX.1-Canny-dev', name: 'FLUX.1 Canny Dev', size: '12B', vram: 24, featured: false },
    { id: 'black-forest-labs/FLUX.1-Depth-dev', name: 'FLUX.1 Depth Dev', size: '12B', vram: 24, featured: false },
    { id: 'black-forest-labs/FLUX.1-Redux-dev', name: 'FLUX.1 Redux Dev', size: '12B', vram: 24, featured: false },
    // Stable Diffusion 3.x
    { id: 'stabilityai/stable-diffusion-3.5-large', name: 'SD 3.5 Large', size: '8B', vram: 16, featured: true },
    { id: 'stabilityai/stable-diffusion-3.5-medium', name: 'SD 3.5 Medium', size: '2.5B', vram: 8, featured: true },
    { id: 'stabilityai/stable-diffusion-3-medium', name: 'SD 3 Medium', size: '2B', vram: 8, featured: false },
    // Stable Diffusion XL
    { id: 'stabilityai/stable-diffusion-xl-base-1.0', name: 'SDXL Base 1.0', size: '3.5B', vram: 12, featured: true },
    { id: 'stabilityai/stable-diffusion-xl-refiner-1.0', name: 'SDXL Refiner 1.0', size: '3.5B', vram: 12, featured: false },
    { id: 'stabilityai/sdxl-turbo', name: 'SDXL Turbo', size: '3.5B', vram: 12, featured: true },
    { id: 'stabilityai/sd-turbo', name: 'SD Turbo', size: '1B', vram: 4, featured: false },
    // Stable Diffusion 1.x/2.x
    { id: 'runwayml/stable-diffusion-v1-5', name: 'SD 1.5', size: '1B', vram: 4, featured: false },
    { id: 'stabilityai/stable-diffusion-2-1', name: 'SD 2.1', size: '1B', vram: 4, featured: false },
    // Playground
    { id: 'playgroundai/playground-v2.5-1024px-aesthetic', name: 'Playground V2.5', size: '2.6B', vram: 8, featured: true },
    { id: 'playgroundai/playground-v2-1024px-aesthetic', name: 'Playground V2', size: '2.6B', vram: 8, featured: false },
    // Kandinsky
    { id: 'kandinsky-community/kandinsky-3', name: 'Kandinsky 3', size: '12B', vram: 24, featured: false },
    // PixArt
    { id: 'PixArt-alpha/PixArt-Sigma-XL-2-1024-MS', name: 'PixArt Sigma XL', size: '0.6B', vram: 4, featured: false },
    { id: 'PixArt-alpha/PixArt-XL-2-1024-MS', name: 'PixArt Alpha XL', size: '0.6B', vram: 4, featured: false },
    // Hunyuan
    { id: 'Tencent-Hunyuan/HunyuanDiT-v1.2-Diffusers', name: 'Hunyuan DiT v1.2', size: '1.5B', vram: 6, featured: false },
    // Stable Video
    { id: 'stabilityai/stable-video-diffusion-img2vid-xt-1-1', name: 'SVD XT 1.1', size: '1.5B', vram: 12, featured: false },
    // AnimateDiff
    { id: 'guoyww/animatediff-motion-adapter-v1-5-3', name: 'AnimateDiff V1.5', size: '0.5B', vram: 8, featured: false },
    // ControlNet
    { id: 'lllyasviel/control_v11p_sd15_canny', name: 'ControlNet Canny SD1.5', size: '1.4B', vram: 4, featured: false },
    { id: 'diffusers/controlnet-canny-sdxl-1.0', name: 'ControlNet Canny SDXL', size: '2.5B', vram: 8, featured: false },
    // IP-Adapter
    { id: 'h94/IP-Adapter', name: 'IP-Adapter', size: '0.1B', vram: 2, featured: false },
  ],
  embeddings: [
    // BGE Series
    { id: 'BAAI/bge-large-en-v1.5', name: 'BGE Large EN v1.5', size: '335M', vram: 1, featured: true },
    { id: 'BAAI/bge-base-en-v1.5', name: 'BGE Base EN v1.5', size: '110M', vram: 0.5, featured: false },
    { id: 'BAAI/bge-small-en-v1.5', name: 'BGE Small EN v1.5', size: '33M', vram: 0.5, featured: false },
    { id: 'BAAI/bge-m3', name: 'BGE M3 (Multilingual)', size: '568M', vram: 2, featured: true },
    { id: 'BAAI/bge-reranker-v2-m3', name: 'BGE Reranker V2 M3', size: '568M', vram: 2, featured: false },
    { id: 'BAAI/bge-reranker-large', name: 'BGE Reranker Large', size: '560M', vram: 2, featured: false },
    // E5 Series
    { id: 'intfloat/e5-large-v2', name: 'E5 Large V2', size: '335M', vram: 1, featured: true },
    { id: 'intfloat/e5-base-v2', name: 'E5 Base V2', size: '110M', vram: 0.5, featured: false },
    { id: 'intfloat/e5-small-v2', name: 'E5 Small V2', size: '33M', vram: 0.5, featured: false },
    { id: 'intfloat/multilingual-e5-large', name: 'E5 Large Multilingual', size: '560M', vram: 2, featured: true },
    { id: 'intfloat/multilingual-e5-base', name: 'E5 Base Multilingual', size: '278M', vram: 1, featured: false },
    { id: 'intfloat/e5-mistral-7b-instruct', name: 'E5 Mistral 7B', size: '7B', vram: 14, featured: false },
    // Sentence Transformers
    { id: 'sentence-transformers/all-MiniLM-L6-v2', name: 'MiniLM L6 V2', size: '22M', vram: 0.5, featured: false },
    { id: 'sentence-transformers/all-MiniLM-L12-v2', name: 'MiniLM L12 V2', size: '33M', vram: 0.5, featured: false },
    { id: 'sentence-transformers/all-mpnet-base-v2', name: 'MPNet Base V2', size: '110M', vram: 0.5, featured: true },
    { id: 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2', name: 'Multilingual MPNet', size: '278M', vram: 1, featured: false },
    // Jina
    { id: 'jinaai/jina-embeddings-v2-base-en', name: 'Jina V2 Base EN', size: '137M', vram: 0.5, featured: true },
    { id: 'jinaai/jina-embeddings-v2-small-en', name: 'Jina V2 Small EN', size: '33M', vram: 0.5, featured: false },
    { id: 'jinaai/jina-embeddings-v3', name: 'Jina V3', size: '572M', vram: 2, featured: true },
    { id: 'jinaai/jina-reranker-v2-base-multilingual', name: 'Jina Reranker V2', size: '278M', vram: 1, featured: false },
    // Nomic
    { id: 'nomic-ai/nomic-embed-text-v1.5', name: 'Nomic Embed V1.5', size: '137M', vram: 0.5, featured: true },
    { id: 'nomic-ai/nomic-embed-text-v1', name: 'Nomic Embed V1', size: '137M', vram: 0.5, featured: false },
    // Cohere
    { id: 'Cohere/Cohere-embed-english-v3.0', name: 'Cohere English V3', size: '335M', vram: 1, featured: false },
    { id: 'Cohere/Cohere-embed-multilingual-v3.0', name: 'Cohere Multilingual V3', size: '560M', vram: 2, featured: false },
    // GTE
    { id: 'thenlper/gte-large', name: 'GTE Large', size: '335M', vram: 1, featured: false },
    { id: 'thenlper/gte-base', name: 'GTE Base', size: '110M', vram: 0.5, featured: false },
    { id: 'Alibaba-NLP/gte-Qwen2-7B-instruct', name: 'GTE Qwen2 7B', size: '7B', vram: 14, featured: false },
    { id: 'Alibaba-NLP/gte-Qwen2-1.5B-instruct', name: 'GTE Qwen2 1.5B', size: '1.5B', vram: 4, featured: false },
    // Voyage (HF mirrors)
    { id: 'voyageai/voyage-large-2-instruct', name: 'Voyage Large 2', size: '1.2B', vram: 3, featured: false },
    // UAE
    { id: 'WhereIsAI/UAE-Large-V1', name: 'UAE Large V1', size: '335M', vram: 1, featured: false },
    // Stella
    { id: 'dunzhang/stella_en_1.5B_v5', name: 'Stella EN 1.5B V5', size: '1.5B', vram: 4, featured: false },
    { id: 'dunzhang/stella_en_400M_v5', name: 'Stella EN 400M V5', size: '400M', vram: 1, featured: false },
  ],
};

// Runtime options for each model type
export const RUNTIME_OPTIONS = {
  llm: [
    { id: 'vllm', name: 'vLLM', description: 'Alto desempenho para inferência', recommended: true },
    { id: 'ollama', name: 'Ollama', description: 'Fácil de usar, suporta quantização' },
    { id: 'tgi', name: 'Text Generation Inference (TGI)', description: 'HuggingFace runtime otimizado' },
    { id: 'sglang', name: 'SGLang', description: 'Máxima performance para produção' },
  ],
  speech: [
    { id: 'faster-whisper', name: 'Faster Whisper', description: '4x mais rápido que original', recommended: true },
    { id: 'whisper', name: 'OpenAI Whisper', description: 'Implementação original' },
  ],
  image: [
    { id: 'diffusers', name: 'Diffusers', description: 'HuggingFace library padrão', recommended: true },
    { id: 'comfyui', name: 'ComfyUI', description: 'Interface visual com workflows' },
    { id: 'automatic1111', name: 'Automatic1111', description: 'WebUI popular com muitas extensões' },
  ],
  embeddings: [
    { id: 'sentence-transformers', name: 'Sentence Transformers', description: 'Biblioteca padrão', recommended: true },
    { id: 'tei', name: 'Text Embeddings Inference (TEI)', description: 'HuggingFace runtime otimizado' },
  ],
};

// Demo templates for model deployment wizard
export const DEMO_TEMPLATES = [
  {
    type: 'llm',
    name: 'LLM (Chat/Completion)',
    description: 'Deploy modelos de linguagem para chat e text completion',
    runtime: 'vLLM',
    gpu_memory_required: 8,
    default_port: 8000,
    popular_models: FIREWORKS_MODELS.llm.filter(m => m.featured).slice(0, 6),
  },
  {
    type: 'speech',
    name: 'Speech (Transcription)',
    description: 'Transcreva áudio para texto com alta precisão',
    runtime: 'faster-whisper',
    gpu_memory_required: 4,
    default_port: 8001,
    popular_models: FIREWORKS_MODELS.speech.filter(m => m.featured),
  },
  {
    type: 'image',
    name: 'Image (Generation)',
    description: 'Gere imagens a partir de texto (text-to-image)',
    runtime: 'diffusers',
    gpu_memory_required: 12,
    default_port: 8002,
    popular_models: FIREWORKS_MODELS.image.filter(m => m.featured),
  },
  {
    type: 'embeddings',
    name: 'Embeddings (Vectors)',
    description: 'Gere embeddings para busca semântica e RAG',
    runtime: 'sentence-transformers',
    gpu_memory_required: 2,
    default_port: 8003,
    popular_models: FIREWORKS_MODELS.embeddings.filter(m => m.featured),
  },
]

import { useState, useEffect } from 'react';
import {
  Brain,
  Upload,
  Database,
  Settings2,
  Loader2,
  Check,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  Search,
  Copy,
  X,
  Info,
} from 'lucide-react';

// Model Library (matching Fireworks.ai structure)
const MODEL_LIBRARY = [
  // Meta Llama models
  { id: 'unsloth/llama-3-8b-bnb-4bit', name: 'Llama 3 8B', provider: 'Meta', vram: '16GB', category: 'llama' },
  { id: 'unsloth/llama-3.1-8b-bnb-4bit', name: 'Llama 3.1 8B', provider: 'Meta', vram: '16GB', category: 'llama' },
  { id: 'unsloth/llama-3.2-3b-bnb-4bit', name: 'Llama 3.2 3B', provider: 'Meta', vram: '8GB', category: 'llama' },
  // Mistral models
  { id: 'unsloth/mistral-7b-bnb-4bit', name: 'Mistral 7B', provider: 'Mistral AI', vram: '12GB', category: 'mistral' },
  { id: 'unsloth/mistral-7b-instruct-v0.3-bnb-4bit', name: 'Mistral 7B Instruct v0.3', provider: 'Mistral AI', vram: '12GB', category: 'mistral' },
  // Google models
  { id: 'unsloth/gemma-7b-bnb-4bit', name: 'Gemma 7B', provider: 'Google', vram: '12GB', category: 'gemma' },
  { id: 'unsloth/gemma-2-9b-bnb-4bit', name: 'Gemma 2 9B', provider: 'Google', vram: '18GB', category: 'gemma' },
  // Qwen models
  { id: 'unsloth/Qwen2-7B-bnb-4bit', name: 'Qwen 2 7B', provider: 'Alibaba', vram: '12GB', category: 'qwen' },
  { id: 'unsloth/Qwen2.5-7B-bnb-4bit', name: 'Qwen 2.5 7B', provider: 'Alibaba', vram: '12GB', category: 'qwen' },
  { id: 'unsloth/Qwen2.5-3B-bnb-4bit', name: 'Qwen 2.5 3B', provider: 'Alibaba', vram: '8GB', category: 'qwen' },
  // Microsoft models
  { id: 'unsloth/Phi-3-mini-4k-instruct-bnb-4bit', name: 'Phi-3 Mini', provider: 'Microsoft', vram: '8GB', category: 'phi' },
  { id: 'unsloth/Phi-3.5-mini-instruct-bnb-4bit', name: 'Phi-3.5 Mini', provider: 'Microsoft', vram: '8GB', category: 'phi' },
  // Lightweight models
  { id: 'unsloth/tinyllama-bnb-4bit', name: 'TinyLlama 1.1B', provider: 'TinyLlama', vram: '4GB', category: 'tiny' },
  { id: 'unsloth/stablelm-2-1_6b-bnb-4bit', name: 'StableLM 2 1.6B', provider: 'Stability AI', vram: '6GB', category: 'stablelm' },
  // Code models
  { id: 'unsloth/codellama-7b-bnb-4bit', name: 'CodeLlama 7B', provider: 'Meta', vram: '12GB', category: 'code' },
  { id: 'unsloth/deepseek-coder-6.7b-base-bnb-4bit', name: 'DeepSeek Coder 6.7B', provider: 'DeepSeek', vram: '12GB', category: 'code' },
  // Chat-optimized models
  { id: 'unsloth/zephyr-7b-beta-bnb-4bit', name: 'Zephyr 7B Beta', provider: 'HuggingFace', vram: '12GB', category: 'chat' },
  { id: 'unsloth/openhermes-2.5-mistral-7b-bnb-4bit', name: 'OpenHermes 2.5', provider: 'Nous Research', vram: '12GB', category: 'chat' },
];

// HuggingFace datasets available for fine-tuning
const SAMPLE_DATASETS = [
  { id: 'yahma/alpaca-cleaned', name: 'Alpaca Cleaned (52K)', format: 'alpaca', size: '24 MB' },
  { id: 'teknium/OpenHermes-2.5', name: 'OpenHermes 2.5 (1M)', format: 'sharegpt', size: '2.1 GB' },
  { id: 'mlabonne/guanaco-llama2-1k', name: 'Guanaco 1K', format: 'alpaca', size: '1.5 MB' },
];

// Copy to clipboard helper
function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}

// Generate random string for job ID
function generateId(length = 12) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
}

// Generate timestamp string
function generateTimestamp() {
  const now = new Date();
  return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
}

export default function FineTuningModal({ isOpen, onClose, method = 'supervised', onSuccess }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Step 1: Model
  const [modelTab, setModelTab] = useState('library');
  const [modelSearch, setModelSearch] = useState('');
  const [selectedModel, setSelectedModel] = useState(null);
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  // Step 2: Dataset
  const [datasetTab, setDatasetTab] = useState('existing');
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [showDatasetDropdown, setShowDatasetDropdown] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [datasetPath, setDatasetPath] = useState('');
  const [evalDataset, setEvalDataset] = useState('none');

  // Step 3: Optional Settings
  const [modelOutputName, setModelOutputName] = useState('');
  const [jobId, setJobId] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [epochs, setEpochs] = useState(1);
  const [batchSize, setBatchSize] = useState(65536);
  const [loraRank, setLoraRank] = useState(8);
  const [learningRate, setLearningRate] = useState(0.0001);
  const [maxContextLength, setMaxContextLength] = useState(65536);
  const [gradientAccumulationSteps, setGradientAccumulationSteps] = useState(1);
  const [warmupSteps, setWarmupSteps] = useState(0);
  const [turboMode, setTurboMode] = useState(false);
  const [enableWandb, setEnableWandb] = useState(false);

  // Reset on modal open
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setError(null);
      setSelectedModel(null);
      setSelectedDataset(null);
      setUploadedFile(null);
      setDatasetPath('');
      // Generate default values
      const timestamp = generateTimestamp();
      const randomStr = generateId(8);
      setModelOutputName(`ft-${timestamp}-${randomStr}`);
      setJobId(generateId(12));
      setDisplayName('');
    }
  }, [isOpen]);

  // Filter models based on search
  const filteredModels = MODEL_LIBRARY.filter(model =>
    model.name.toLowerCase().includes(modelSearch.toLowerCase()) ||
    model.provider.toLowerCase().includes(modelSearch.toLowerCase()) ||
    model.id.toLowerCase().includes(modelSearch.toLowerCase())
  );

  // Handle file upload
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadedFile(file);
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/v1/finetune/jobs/upload-dataset', {
        method: 'POST',
        body: formData,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Upload failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      setDatasetPath(data.dataset_path);
    } catch (err) {
      setError('Failed to upload dataset: ' + err.message);
      setUploadedFile(null);
    } finally {
      setUploading(false);
    }
  };

  // Launch fine-tuning job
  const handleCreate = async () => {
    if (loading) return;

    if (!selectedModel) {
      setError('Please select a base model');
      return;
    }

    if (!datasetPath && !selectedDataset) {
      setError('Please select or upload a dataset');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('auth_token');

      const res = await fetch('/api/v1/finetune/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: displayName || modelOutputName,
          base_model: selectedModel.id,
          dataset_source: uploadedFile ? 'upload' : 'existing',
          dataset_path: datasetPath || selectedDataset?.id,
          dataset_format: 'alpaca',
          config: {
            lora_rank: loraRank,
            lora_alpha: loraRank,
            learning_rate: learningRate,
            epochs: epochs,
            batch_size: batchSize,
            max_seq_length: maxContextLength,
            gradient_accumulation_steps: gradientAccumulationSteps,
            warmup_steps: warmupSteps,
            turbo_mode: turboMode,
          },
          gpu_type: 'A100',
          num_gpus: 1,
          method: method,
          job_id: jobId,
          model_output_name: modelOutputName,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed to create job (HTTP ${res.status})`);
      }

      const job = await res.json();
      onSuccess && onSuccess(job);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Navigation
  const canProceedStep1 = !!selectedModel;
  const canProceedStep2 = !!(datasetPath || selectedDataset);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[999999]">
      <div className="bg-[#1a1f2e] rounded-xl border border-white/10 w-full max-w-2xl min-h-[70vh] max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div>
            <h2 className="text-base font-semibold text-white">Create Fine-Tuning Job</h2>
            <p className="text-xs text-gray-400">
              {method === 'supervised' && 'Supervised Fine-Tuning (SFT)'}
              {method === 'reinforcement' && 'Reinforcement Fine-Tuning (RFT)'}
              {method === 'preference' && 'Direct Preference Optimization (DPO)'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Wizard Steps Indicator */}
        <div className="flex items-center px-4 py-3 border-b border-white/5">
          {[
            { num: 1, label: 'Model', icon: Brain },
            { num: 2, label: 'Dataset', icon: Database },
            { num: 3, label: 'Settings', icon: Settings2 },
          ].map((s, idx) => (
            <div key={s.num} className="flex items-center">
              <div className="flex items-center gap-1.5">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                    step > s.num
                      ? 'bg-green-500 text-white'
                      : step === s.num
                      ? 'bg-purple-500 text-white'
                      : 'bg-white/10 text-gray-400'
                  }`}
                >
                  {step > s.num ? <Check className="w-3 h-3" /> : s.num}
                </div>
                <span className={`text-xs ${step >= s.num ? 'text-white' : 'text-gray-500'}`}>
                  {s.label}
                </span>
              </div>
              {idx < 2 && (
                <div className={`w-12 h-0.5 mx-2 ${step > s.num ? 'bg-green-500' : 'bg-white/10'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-3 p-2.5 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          {/* Step 1: Model Selection */}
          {step === 1 && (
            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-medium text-white mb-0.5">Model</h3>
                <p className="text-xs text-gray-400">Choose a base model or a LoRA adapter to start fine-tuning.</p>
              </div>

              {/* Model Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowModelDropdown(!showModelDropdown)}
                  className="w-full p-3 bg-[#0f1219] border border-white/10 rounded-lg flex items-center justify-between text-left hover:border-white/20 transition-colors"
                >
                  {selectedModel ? (
                    <div className="flex items-center gap-2">
                      <Brain className="w-4 h-4 text-purple-400" />
                      <div>
                        <div className="text-sm text-white font-medium">{selectedModel.name}</div>
                        <div className="text-xs text-gray-500 font-mono">{selectedModel.id}</div>
                      </div>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">Select a model...</span>
                  )}
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showModelDropdown ? 'rotate-180' : ''}`} />
                </button>

                {showModelDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-[#1e2330] border border-white/10 rounded-lg shadow-xl z-10 max-h-80 overflow-hidden">
                    {/* Search */}
                    <div className="p-2 border-b border-white/10">
                      <div className="relative">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Search models..."
                          value={modelSearch}
                          onChange={(e) => setModelSearch(e.target.value)}
                          className="w-full bg-[#0f1219] border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-purple-500 outline-none"
                        />
                      </div>
                    </div>

                    {/* Tabs */}
                    <div className="flex border-b border-white/10">
                      <button
                        onClick={() => setModelTab('library')}
                        className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                          modelTab === 'library' ? 'text-white border-b-2 border-purple-500' : 'text-gray-400'
                        }`}
                      >
                        Model Library
                      </button>
                      <button
                        onClick={() => setModelTab('custom')}
                        className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                          modelTab === 'custom' ? 'text-white border-b-2 border-purple-500' : 'text-gray-400'
                        }`}
                      >
                        Custom Models
                      </button>
                    </div>

                    {/* Model List */}
                    <div className="max-h-52 overflow-y-auto">
                      {modelTab === 'library' ? (
                        filteredModels.length > 0 ? (
                          filteredModels.map((model) => (
                            <button
                              key={model.id}
                              onClick={() => {
                                setSelectedModel(model);
                                setShowModelDropdown(false);
                              }}
                              className={`w-full p-2.5 flex items-center gap-2 hover:bg-white/5 transition-colors ${
                                selectedModel?.id === model.id ? 'bg-purple-500/10' : ''
                              }`}
                            >
                              <Brain className="w-4 h-4 text-purple-400 flex-shrink-0" />
                              <div className="flex-1 min-w-0 text-left">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-sm text-white font-medium">{model.name}</span>
                                  <span className="text-xs text-gray-500">{model.provider}</span>
                                </div>
                                <div className="text-xs text-gray-500 font-mono truncate">{model.id}</div>
                              </div>
                              <span className="text-xs text-gray-500 bg-white/5 px-1.5 py-0.5 rounded">{model.vram}</span>
                              {selectedModel?.id === model.id && (
                                <Check className="w-3.5 h-3.5 text-purple-400" />
                              )}
                            </button>
                          ))
                        ) : (
                          <div className="p-3 text-center text-gray-400 text-xs">
                            No models found matching "{modelSearch}"
                          </div>
                        )
                      ) : (
                        <div className="p-3 text-center text-gray-400 text-xs">
                          No custom models available. Upload a LoRA adapter to use here.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Selected Model Info */}
              {selectedModel && (
                <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs text-gray-400">Selected:</span>
                      <span className="text-sm text-white ml-1.5 font-medium">{selectedModel.name}</span>
                    </div>
                    <span className="text-xs text-purple-400 bg-purple-500/20 px-1.5 py-0.5 rounded">
                      {selectedModel.vram} VRAM
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Dataset Selection */}
          {step === 2 && (
            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-medium text-white mb-0.5">Dataset</h3>
                <p className="text-xs text-gray-400">Select an existing dataset or upload a new one.</p>
              </div>

              {/* Dataset Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setShowDatasetDropdown(!showDatasetDropdown)}
                  className="w-full p-3 bg-[#0f1219] border border-white/10 rounded-lg flex items-center justify-between text-left hover:border-white/20 transition-colors"
                >
                  {selectedDataset ? (
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-cyan-400" />
                      <div>
                        <div className="text-sm text-white font-medium">{selectedDataset.name}</div>
                        <div className="text-xs text-gray-500">{selectedDataset.format} • {selectedDataset.size}</div>
                      </div>
                    </div>
                  ) : uploadedFile ? (
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-green-400" />
                      <div>
                        <div className="text-sm text-white font-medium">{uploadedFile.name}</div>
                        <div className="text-xs text-gray-500">Uploaded file</div>
                      </div>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">Select a dataset...</span>
                  )}
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showDatasetDropdown ? 'rotate-180' : ''}`} />
                </button>

                {showDatasetDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-[#1e2330] border border-white/10 rounded-lg shadow-xl z-10">
                    {SAMPLE_DATASETS.map((dataset) => (
                      <button
                        key={dataset.id}
                        onClick={() => {
                          setSelectedDataset(dataset);
                          setUploadedFile(null);
                          setDatasetPath(dataset.id);
                          setShowDatasetDropdown(false);
                        }}
                        className={`w-full p-2.5 flex items-center gap-2 hover:bg-white/5 transition-colors ${
                          selectedDataset?.id === dataset.id ? 'bg-cyan-500/10' : ''
                        }`}
                      >
                        <Database className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0 text-left">
                          <div className="text-sm text-white font-medium">{dataset.name}</div>
                          <div className="text-xs text-gray-500">{dataset.format} • {dataset.size}</div>
                        </div>
                        {selectedDataset?.id === dataset.id && (
                          <Check className="w-3.5 h-3.5 text-cyan-400" />
                        )}
                      </button>
                    ))}
                    <div className="border-t border-white/10 p-1.5">
                      <span className="text-xs text-gray-500 px-2">Or upload a new dataset below</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Upload Area */}
              <div
                className={`border-2 border-dashed rounded-lg p-5 text-center transition-all ${
                  uploadedFile ? 'border-green-500/50 bg-green-500/5' : 'border-white/10 hover:border-white/20'
                }`}
              >
                {uploading ? (
                  <div className="flex flex-col items-center gap-1.5">
                    <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                    <span className="text-sm text-gray-400">Uploading...</span>
                  </div>
                ) : uploadedFile ? (
                  <div className="flex flex-col items-center gap-1.5">
                    <Check className="w-6 h-6 text-green-400" />
                    <span className="text-sm text-white font-medium">{uploadedFile.name}</span>
                    <span className="text-xs text-gray-400">Upload successful</span>
                    <button
                      onClick={() => {
                        setUploadedFile(null);
                        setDatasetPath('');
                      }}
                      className="text-xs text-red-400 hover:text-red-300 mt-1"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <label className="cursor-pointer">
                    <div className="flex flex-col items-center gap-2">
                      <Upload className="w-7 h-7 text-gray-400" />
                      <div className="text-sm">
                        <span className="text-purple-400 font-medium">Click to upload</span>
                        <span className="text-gray-400"> or drag and drop</span>
                      </div>
                      <span className="text-xs text-gray-500">JSON or JSONL files up to 100MB</span>
                    </div>
                    <input
                      type="file"
                      accept=".json,.jsonl"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                )}
              </div>

              {/* Evaluation Dataset */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Evaluation Dataset (Optional)</label>
                <select
                  value={evalDataset}
                  onChange={(e) => setEvalDataset(e.target.value)}
                  className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                >
                  <option value="none">Do not use a validation dataset</option>
                  {SAMPLE_DATASETS.map(ds => (
                    <option key={ds.id} value={ds.id}>{ds.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Step 3: Optional Settings */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-white mb-0.5">Optional Settings</h3>
                <p className="text-xs text-gray-400">Configure training parameters for your fine-tuning job.</p>
              </div>

              {/* Model Output Name */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Model Output Name</label>
                <input
                  type="text"
                  value={modelOutputName}
                  onChange={(e) => setModelOutputName(e.target.value)}
                  className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none font-mono"
                />
              </div>

              {/* Job ID */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Job ID</label>
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={jobId}
                    onChange={(e) => setJobId(e.target.value)}
                    className="flex-1 bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none font-mono"
                  />
                  <button
                    onClick={() => copyToClipboard(jobId)}
                    className="p-2 bg-[#0f1219] border border-white/10 rounded-lg hover:bg-white/5"
                  >
                    <Copy className="w-3.5 h-3.5 text-gray-400" />
                  </button>
                </div>
              </div>

              {/* Display Name */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Display Name (Optional)</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="My Fine-Tuned Model"
                  className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-purple-500 outline-none"
                />
              </div>

              {/* Training Parameters Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Epochs</label>
                  <input
                    type="number"
                    value={epochs}
                    onChange={(e) => setEpochs(parseInt(e.target.value) || 1)}
                    min={1}
                    max={10}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Batch Size</label>
                  <input
                    type="number"
                    value={batchSize}
                    onChange={(e) => setBatchSize(parseInt(e.target.value) || 65536)}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">LoRA Rank</label>
                  <input
                    type="number"
                    value={loraRank}
                    onChange={(e) => setLoraRank(parseInt(e.target.value) || 8)}
                    min={4}
                    max={64}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Learning Rate</label>
                  <input
                    type="number"
                    value={learningRate}
                    onChange={(e) => setLearningRate(parseFloat(e.target.value) || 0.0001)}
                    step={0.00001}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Max Context Length</label>
                  <input
                    type="number"
                    value={maxContextLength}
                    onChange={(e) => setMaxContextLength(parseInt(e.target.value) || 65536)}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Gradient Accum. Steps</label>
                  <input
                    type="number"
                    value={gradientAccumulationSteps}
                    onChange={(e) => setGradientAccumulationSteps(parseInt(e.target.value) || 1)}
                    min={1}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Warmup Steps</label>
                  <input
                    type="number"
                    value={warmupSteps}
                    onChange={(e) => setWarmupSteps(parseInt(e.target.value) || 0)}
                    min={0}
                    className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-purple-500 outline-none"
                  />
                </div>
              </div>

              {/* Checkboxes */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={turboMode}
                    onChange={(e) => setTurboMode(e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-white/20 bg-[#0f1219] text-purple-500 focus:ring-purple-500"
                  />
                  <span className="text-sm text-white">Turbo Mode</span>
                  <span className="text-xs text-gray-500">(Faster, higher cost)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableWandb}
                    onChange={(e) => setEnableWandb(e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-white/20 bg-[#0f1219] text-purple-500 focus:ring-purple-500"
                  />
                  <span className="text-sm text-white">Weights & Biases</span>
                  <span className="text-xs text-gray-500">(Experiment tracking)</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-between px-4 py-3 border-t border-white/10">
          <div>
            {step > 1 && (
              <button
                onClick={() => setStep(step - 1)}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Back
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            {step < 3 ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={(step === 1 && !canProceedStep1) || (step === 2 && !canProceedStep2)}
                className="flex items-center gap-1 px-4 py-1.5 rounded-lg text-sm bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={handleCreate}
                disabled={loading}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create'
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

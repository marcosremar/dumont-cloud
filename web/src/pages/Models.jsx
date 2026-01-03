import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Play, Square, RefreshCw, Clock, DollarSign, Cpu, Server,
  Plus, Loader2, CheckCircle, XCircle, AlertCircle, Terminal,
  Eye, ExternalLink, Copy, Key, Globe, Lock, Mic, Image, MessageSquare, Search,
  ChevronRight, ChevronLeft, Rocket, Zap, Link2, Sparkles, Filter, ChevronDown,
  Columns, Star, ArrowRight
} from 'lucide-react';
import { FIREWORKS_MODELS, RUNTIME_OPTIONS } from '../constants/demoData';
import { detectModelType, extractModelIdFromUrl, RUNTIMES, isGatedModel, getGatedModelInfo } from '../constants/popularModels';
import { useToast } from '../components/Toast';

// Model type icons (labels are translation keys)
const MODEL_TYPE_CONFIG = {
  llm: { icon: MessageSquare, labelKey: 'models.types.llm', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  speech: { icon: Mic, labelKey: 'models.types.speech', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  image: { icon: Image, labelKey: 'models.types.image', color: 'text-pink-400', bg: 'bg-pink-500/10' },
  embeddings: { icon: Search, labelKey: 'models.types.embeddings', color: 'text-amber-400', bg: 'bg-amber-500/10' },
};

// Status colors and icons (labels are translation keys)
const STATUS_CONFIG = {
  pending: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Clock, labelKey: 'models.status.pending' },
  deploying: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, labelKey: 'models.status.deploying' },
  downloading: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, labelKey: 'models.status.downloading' },
  starting: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: Loader2, labelKey: 'models.status.starting' },
  running: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', icon: Play, labelKey: 'models.status.running' },
  stopped: { color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Square, labelKey: 'models.status.stopped' },
  error: { color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircle, labelKey: 'models.status.error' },
};

const Models = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';

  const [models, setModels] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDeployWizard, setShowDeployWizard] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);

  // Wizard form state
  const [formData, setFormData] = useState({
    model_type: 'llm',
    model_id: '',
    custom_model: false,
    huggingface_url: '',
    runtime: 'vllm',
    instance_id: null,
    create_new_instance: true,
    gpu_type: 'RTX 4090',
    num_gpus: 1,
    max_price: 2.0,
    access_type: 'private',
    port: 8000,
    name: '',
    hf_token: '', // HuggingFace token for gated models
  });

  // Model search/filter state
  const [modelSearch, setModelSearch] = useState('');
  const [showAllModels, setShowAllModels] = useState(false);

  // HuggingFace URL import state
  const [hfUrl, setHfUrl] = useState('');
  const [detectedType, setDetectedType] = useState(null);

  // Tab state for main view
  const [activeTab, setActiveTab] = useState('popular'); // 'popular' | 'deployed'


  // Fetch models and templates
  const fetchModels = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/v1/models', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setModels(data.models || []);
      }
    } catch (error) {
      console.error('Error fetching models:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/v1/models/templates', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      }
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  }, []);

  useEffect(() => {
    fetchModels();
    fetchTemplates();
    // Auto-refresh every 10 seconds for deploying models
    const interval = setInterval(() => {
      if (models.some(m => ['pending', 'deploying', 'downloading', 'starting'].includes(m.status))) {
        fetchModels();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchModels, fetchTemplates, models]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchModels();
  };

  // Parse Hugging Face URL to extract model ID
  const parseHuggingFaceUrl = (url) => {
    if (!url) return null;
    // Match patterns like:
    // https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
    // huggingface.co/meta-llama/Llama-3.2-3B-Instruct
    // meta-llama/Llama-3.2-3B-Instruct
    const hfPattern = /(?:https?:\/\/)?(?:huggingface\.co\/)?([a-zA-Z0-9_-]+\/[a-zA-Z0-9._-]+)/;
    const match = url.match(hfPattern);
    return match ? match[1] : null;
  };

  // Get all models for current type
  const getAllModelsForType = useMemo(() => {
    return FIREWORKS_MODELS[formData.model_type] || [];
  }, [formData.model_type]);

  // Filter models based on search
  const filteredModels = useMemo(() => {
    const allModels = getAllModelsForType;
    if (!modelSearch.trim()) {
      return showAllModels ? allModels : allModels.filter(m => m.featured);
    }
    const query = modelSearch.toLowerCase();
    return allModels.filter(m =>
      m.name.toLowerCase().includes(query) ||
      m.id.toLowerCase().includes(query) ||
      m.size.toLowerCase().includes(query)
    );
  }, [getAllModelsForType, modelSearch, showAllModels]);

  // Get runtime options for current type
  const runtimeOptions = useMemo(() => {
    return RUNTIME_OPTIONS[formData.model_type] || [];
  }, [formData.model_type]);

  const openDeployWizard = () => {
    setWizardStep(1);
    setModelSearch('');
    setShowAllModels(false);
    setFormData({
      model_type: 'llm',
      model_id: '',
      custom_model: false,
      huggingface_url: '',
      runtime: 'vllm',
      instance_id: null,
      create_new_instance: true,
      gpu_type: 'RTX 4090',
      num_gpus: 1,
      max_price: 2.0,
      access_type: 'private',
      port: 8000,
      name: '',
      hf_token: '',
    });
    setShowDeployWizard(true);
  };

  const handleDeploy = async () => {
    setDeploying(true);

    try {
      const token = localStorage.getItem('auth_token');
      const payload = {
        model_type: formData.model_type,
        model_id: formData.model_id,
        instance_id: formData.create_new_instance ? null : formData.instance_id,
        gpu_type: formData.gpu_type,
        num_gpus: formData.num_gpus,
        max_price: formData.max_price,
        access_type: formData.access_type,
        port: formData.port,
        name: formData.name || undefined,
        hf_token: formData.hf_token || undefined, // HuggingFace token for gated models
      };

      const response = await fetch('/api/v1/models/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const modelName = formData.name || formData.model_id.split('/').pop();
        toast?.success(`Deploy iniciado: ${modelName}`);
        setShowDeployWizard(false);
        setActiveTab('deployed'); // Switch to deploys tab to show progress
        fetchModels();
      } else {
        const error = await response.json();
        alert(`${t('models.errors.deployError')}: ${error.detail || t('models.errors.unknownError')}`);
      }
    } catch (error) {
      console.error('Error deploying model:', error);
      alert(t('models.errors.deployError'));
    } finally {
      setDeploying(false);
    }
  };

  const handleStopModel = async (modelId) => {
    if (!confirm(t('models.confirmStop'))) return;

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/v1/models/${modelId}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ force: false }),
      });
      if (response.ok) fetchModels();
    } catch (error) {
      console.error('Error stopping model:', error);
    }
  };

  const handleDeleteModel = async (modelId) => {
    if (!confirm(t('models.confirmDelete'))) return;

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`/api/v1/models/${modelId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) fetchModels();
    } catch (error) {
      console.error('Error deleting model:', error);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  // Handle HuggingFace URL input
  const handleHfUrlChange = (url) => {
    setHfUrl(url);
    if (url.includes('huggingface.co') || url.includes('/')) {
      const modelId = extractModelIdFromUrl(url);
      const type = detectModelType(modelId);
      setDetectedType(type);
      setFormData(prev => ({
        ...prev,
        model_id: modelId,
        model_type: type,
        huggingface_url: url,
        custom_model: true,
        port: RUNTIMES[type]?.port || 8000,
      }));
    } else {
      setDetectedType(null);
    }
  };

  // Quick deploy from HuggingFace URL
  const handleHfQuickDeploy = () => {
    if (!hfUrl || !detectedType) return;
    const modelId = extractModelIdFromUrl(hfUrl);
    setFormData(prev => ({
      ...prev,
      model_id: modelId,
      model_type: detectedType,
      custom_model: true,
      port: RUNTIMES[detectedType]?.port || 8000,
    }));
    setWizardStep(3);
    setShowDeployWizard(true);
  };

  const ModelStatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    const isAnimated = ['deploying', 'downloading', 'starting'].includes(status);

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
        <Icon className={`w-3.5 h-3.5 ${isAnimated ? 'animate-spin' : ''}`} />
        {t(config.labelKey)}
      </span>
    );
  };

  const ModelTypeIcon = ({ type }) => {
    const config = MODEL_TYPE_CONFIG[type] || MODEL_TYPE_CONFIG.llm;
    const Icon = config.icon;
    return (
      <div className={`p-2 rounded-lg ${config.bg}`}>
        <Icon className={`w-5 h-5 ${config.color}`} />
      </div>
    );
  };

  // Get selected template
  const selectedTemplate = templates.find(t => t.type === formData.model_type);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Rocket className="w-9 h-9 flex-shrink-0" style={{ color: '#4caf50' }} />
          <div className="flex flex-col justify-center">
            <h1 className="text-2xl font-bold text-gray-100 leading-tight">{t('models.title')}</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              {t('models.pageSubtitle')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ta-btn ta-btn-secondary p-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={openDeployWizard}
            className="ta-btn ta-btn-primary"
          >
            <Rocket className="w-4 h-4" />
            {t('models.deployModel')}
          </button>
        </div>
      </div>

      {/* Deploy Wizard Modal */}
      {showDeployWizard && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4">
          <div className="bg-dark-surface-card border border-white/10 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Wizard Header */}
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-100">{t('models.wizard.title')}</h2>
                  <p className="text-xs text-gray-500 mt-1">
                    {t('models.wizard.stepOf', { current: wizardStep, total: 4 })}
                  </p>
                </div>
                <button
                  onClick={() => setShowDeployWizard(false)}
                  className="p-2 rounded-lg hover:bg-white/10 text-gray-400"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>

              {/* Progress bar */}
              <div className="flex gap-1">
                {[1, 2, 3, 4].map((step) => (
                  <div
                    key={step}
                    className={`h-1 flex-1 rounded-full transition-all ${
                      step <= wizardStep ? 'bg-brand-500' : 'bg-white/10'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Wizard Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Step 1: Choose Model Type */}
              {wizardStep === 1 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      {t('models.wizard.chooseModelType')}
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      {templates.map((template) => {
                        const config = MODEL_TYPE_CONFIG[template.type];
                        const Icon = config?.icon || MessageSquare;
                        const isSelected = formData.model_type === template.type;

                        return (
                          <button
                            key={template.type}
                            type="button"
                            onClick={() => {
                              setFormData({ ...formData, model_type: template.type, model_id: '', port: template.default_port });
                            }}
                            className={`p-4 rounded-xl border text-left transition-all ${
                              isSelected
                                ? 'bg-brand-500/10 border-brand-500/50'
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className={`p-2 rounded-lg ${config?.bg || 'bg-blue-500/10'}`}>
                                <Icon className={`w-5 h-5 ${config?.color || 'text-blue-400'}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium text-gray-200">{template.name}</div>
                                <div className="text-xs text-gray-500 mt-1">{template.description}</div>
                                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                                  <span className="px-1.5 py-0.5 rounded bg-white/10">{template.runtime}</span>
                                  <span>GPU: {template.gpu_memory_required}GB+</span>
                                </div>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Step 2: Choose Model */}
              {wizardStep === 2 && selectedTemplate && (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-medium text-gray-300">
                        {t('models.wizard.chooseModel')}
                      </h3>
                      <button
                        type="button"
                        onClick={() => setShowAllModels(!showAllModels)}
                        className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
                      >
                        {showAllModels ? 'Mostrar Populares' : 'Ver Todos os Modelos'}
                        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAllModels ? 'rotate-180' : ''}`} />
                      </button>
                    </div>

                    {/* Search input */}
                    <div className="relative mb-4">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                      <input
                        type="text"
                        placeholder="Buscar modelo..."
                        value={modelSearch}
                        onChange={(e) => setModelSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                    </div>

                    {/* Models list */}
                    <div className="space-y-2 mb-6 max-h-[280px] overflow-y-auto pr-1">
                      {filteredModels.map((model) => {
                        const modelIsGated = isGatedModel(model.id);
                        return (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => setFormData({ ...formData, model_id: model.id, custom_model: false })}
                          className={`w-full p-3 rounded-lg border text-left transition-all flex items-center justify-between ${
                            formData.model_id === model.id && !formData.custom_model
                              ? 'bg-brand-500/10 border-brand-500/50'
                              : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            {model.featured && (
                              <Star className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                            )}
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-200">{model.name}</span>
                                {modelIsGated && (
                                  <Lock className="w-3.5 h-3.5 text-amber-400" title="Modelo requer autenticação HuggingFace" />
                                )}
                              </div>
                              <div className="text-xs text-gray-500 font-mono">{model.id}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs px-2 py-1 rounded bg-white/10 text-gray-400">
                              {model.size}
                            </span>
                            <span className="text-xs text-gray-500">
                              {model.vram}GB
                            </span>
                          </div>
                        </button>
                      );})}
                      {filteredModels.length === 0 && (
                        <div className="text-center py-8 text-gray-500 text-sm">
                          Nenhum modelo encontrado
                        </div>
                      )}
                    </div>

                    {/* Hugging Face URL import */}
                    <div className="border-t border-white/10 pt-6">
                      <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                        <Link2 className="w-4 h-4 text-amber-400" />
                        Import do Hugging Face
                      </label>
                      <input
                        type="text"
                        value={formData.huggingface_url || (formData.custom_model ? formData.model_id : '')}
                        onChange={(e) => {
                          const url = e.target.value;
                          const modelId = parseHuggingFaceUrl(url) || url;
                          setFormData({ ...formData, model_id: modelId, huggingface_url: url, custom_model: true });
                        }}
                        placeholder="https://huggingface.co/org/model ou org/model"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                      />
                      <p className="mt-1.5 text-xs text-gray-500">
                        Cole o link ou ID do modelo do Hugging Face
                      </p>
                    </div>

                    {/* Gated Model Alert - HuggingFace Token Required */}
                    {formData.model_id && isGatedModel(formData.model_id) && (
                      <div className="mt-6 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10">
                        <div className="flex items-start gap-3">
                          <Key className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <h4 className="text-sm font-medium text-amber-200">
                              Modelo Gated - Autenticação Necessária
                            </h4>
                            <p className="text-xs text-amber-300/80 mt-1">
                              {getGatedModelInfo(formData.model_id).instructions}
                            </p>
                            <a
                              href={getGatedModelInfo(formData.model_id).accessUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 mt-2"
                            >
                              Aceitar licença no HuggingFace
                              <ExternalLink className="w-3 h-3" />
                            </a>

                            <div className="mt-4">
                              <label className="block text-xs font-medium text-amber-200 mb-2">
                                HuggingFace Token (obrigatório)
                              </label>
                              <input
                                type="password"
                                value={formData.hf_token}
                                onChange={(e) => setFormData({ ...formData, hf_token: e.target.value })}
                                placeholder="hf_xxxxxxxxxxxxxxxxxxxxxxxx"
                                className="w-full px-3 py-2 rounded-lg bg-black/20 border border-amber-500/30 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-amber-500/50"
                              />
                              <p className="mt-1.5 text-xs text-amber-300/60">
                                Obtenha seu token em{' '}
                                <a
                                  href="https://huggingface.co/settings/tokens"
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-amber-400 hover:text-amber-300"
                                >
                                  huggingface.co/settings/tokens
                                </a>
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Step 3: GPU Config */}
              {wizardStep === 3 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      {t('models.wizard.gpuConfig')}
                    </h3>

                    <div className="space-y-4">
                      {/* Runtime Selection */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          Runtime
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                          {runtimeOptions.map((runtime) => (
                            <button
                              key={runtime.id}
                              type="button"
                              onClick={() => setFormData({ ...formData, runtime: runtime.id })}
                              className={`p-3 rounded-lg border text-left transition-all ${
                                formData.runtime === runtime.id
                                  ? 'bg-brand-500/10 border-brand-500/50'
                                  : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-200">{runtime.name}</span>
                                {runtime.recommended && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400">
                                    Recomendado
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 mt-1">{runtime.description}</p>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* GPU Type */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          {t('models.wizard.gpuType')}
                        </label>
                        <select
                          value={formData.gpu_type}
                          onChange={(e) => setFormData({ ...formData, gpu_type: e.target.value })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        >
                          <option value="RTX 3080">RTX 3080 (10GB)</option>
                          <option value="RTX 3090">RTX 3090 (24GB)</option>
                          <option value="RTX 4080">RTX 4080 (16GB)</option>
                          <option value="RTX 4090">RTX 4090 (24GB)</option>
                          <option value="A100">A100 (40/80GB)</option>
                          <option value="H100">H100 (80GB)</option>
                        </select>
                      </div>

                      {/* Num GPUs */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          {t('models.wizard.numGpus')}
                        </label>
                        <select
                          value={formData.num_gpus}
                          onChange={(e) => setFormData({ ...formData, num_gpus: parseInt(e.target.value) })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        >
                          {[1, 2, 4, 8].map((n) => (
                            <option key={n} value={n}>{n} GPU{n > 1 ? 's' : ''}</option>
                          ))}
                        </select>
                      </div>

                      {/* Max Price */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          {t('models.wizard.maxPrice')}
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.1"
                          max="10"
                          value={formData.max_price}
                          onChange={(e) => setFormData({ ...formData, max_price: parseFloat(e.target.value) })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        />
                      </div>

                      {/* Name */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          {t('models.wizard.name')}
                        </label>
                        <input
                          type="text"
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          placeholder={t('models.wizard.namePlaceholder')}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-brand-500/50"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 4: Access Config */}
              {wizardStep === 4 && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-4">
                      {t('models.wizard.accessConfig')}
                    </h3>

                    <div className="space-y-4">
                      {/* Access Type */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          {t('models.wizard.accessType')}
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            type="button"
                            onClick={() => setFormData({ ...formData, access_type: 'private' })}
                            className={`p-4 rounded-lg border text-left transition-all ${
                              formData.access_type === 'private'
                                ? 'bg-brand-500/10 border-brand-500/50'
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Lock className="w-4 h-4 text-amber-400" />
                              <span className="text-sm font-medium text-gray-200">{t('models.wizard.private')}</span>
                            </div>
                            <p className="text-xs text-gray-500">
                              {t('models.wizard.privateDescription')}
                            </p>
                          </button>
                          <button
                            type="button"
                            onClick={() => setFormData({ ...formData, access_type: 'public' })}
                            className={`p-4 rounded-lg border text-left transition-all ${
                              formData.access_type === 'public'
                                ? 'bg-brand-500/10 border-brand-500/50'
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <Globe className="w-4 h-4 text-emerald-400" />
                              <span className="text-sm font-medium text-gray-200">{t('models.wizard.public')}</span>
                            </div>
                            <p className="text-xs text-gray-500">
                              {t('models.wizard.publicDescription')}
                            </p>
                          </button>
                        </div>
                      </div>

                      {/* Port */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-2">
                          {t('models.wizard.port')}
                        </label>
                        <input
                          type="number"
                          min="1024"
                          max="65535"
                          value={formData.port}
                          onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                          className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-200 text-sm focus:ring-1 focus:ring-brand-500/50"
                        />
                      </div>

                      {/* Summary */}
                      <div className="mt-6 p-4 rounded-lg bg-white/5 border border-white/10">
                        <h4 className="text-xs font-medium text-gray-400 mb-3">{t('models.wizard.deploySummary')}</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-500">{t('models.wizard.type')}:</span>
                            <span className="text-gray-200">{t(MODEL_TYPE_CONFIG[formData.model_type]?.labelKey)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">{t('models.wizard.modelLabel')}:</span>
                            <span className="text-gray-200 font-mono text-xs">{formData.model_id || t('models.wizard.notSelected')}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">{t('models.wizard.gpu')}:</span>
                            <span className="text-gray-200">{formData.num_gpus}x {formData.gpu_type}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">{t('models.wizard.access')}:</span>
                            <span className="text-gray-200">{formData.access_type === 'private' ? t('models.wizard.privateApiKey') : t('models.wizard.public')}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">{t('models.wizard.port')}:</span>
                            <span className="text-gray-200">{formData.port}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Wizard Footer */}
            <div className="p-6 border-t border-white/10 flex items-center justify-between">
              <button
                type="button"
                onClick={() => wizardStep > 1 ? setWizardStep(wizardStep - 1) : setShowDeployWizard(false)}
                className="ta-btn ta-btn-secondary"
              >
                <ChevronLeft className="w-4 h-4" />
                {wizardStep === 1 ? t('models.wizard.cancel') : t('models.wizard.back')}
              </button>

              {wizardStep < 4 ? (
                <button
                  type="button"
                  onClick={() => setWizardStep(wizardStep + 1)}
                  disabled={wizardStep === 2 && (!formData.model_id || (isGatedModel(formData.model_id) && !formData.hf_token))}
                  className="ta-btn ta-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('models.wizard.next')}
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleDeploy}
                  disabled={deploying || !formData.model_id || (isGatedModel(formData.model_id) && !formData.hf_token)}
                  className="ta-btn ta-btn-primary disabled:opacity-50"
                >
                  {deploying ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('models.wizard.deploying')}
                    </>
                  ) : (
                    <>
                      <Rocket className="w-4 h-4" />
                      {t('models.wizard.deploy')}
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* HuggingFace Import Section - Always visible at top */}
      <div className="border border-white/10 rounded-xl bg-gradient-to-r from-amber-500/5 to-orange-500/5 p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <Link2 className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-100">Deploy from HuggingFace</h3>
            <p className="text-sm text-gray-500">Cole qualquer link do HuggingFace - detectamos o tipo automaticamente</p>
          </div>
        </div>
        <div className="flex gap-3 items-center">
          <div className="flex-1 relative">
            <input
              type="text"
              value={hfUrl}
              onChange={(e) => handleHfUrlChange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleHfQuickDeploy()}
              placeholder="https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct"
              className="w-full px-4 py-2.5 rounded-lg bg-black/20 border border-white/10 text-gray-200 text-sm placeholder:text-gray-500 focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
            />
          </div>
          {detectedType && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
              {MODEL_TYPE_CONFIG[detectedType] && (
                <>
                  {(() => {
                    const Icon = MODEL_TYPE_CONFIG[detectedType].icon;
                    return <Icon className={`w-4 h-4 ${MODEL_TYPE_CONFIG[detectedType].color}`} />;
                  })()}
                  <span className="text-sm text-gray-300">{detectedType.toUpperCase()}</span>
                  <span className="text-xs text-gray-500">· {RUNTIMES[detectedType]?.name}</span>
                </>
              )}
            </div>
          )}
          <button
            onClick={handleHfQuickDeploy}
            disabled={!hfUrl || !detectedType}
            className="px-5 py-2.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/30 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Rocket className="w-4 h-4" />
            Deploy
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-white/10">
        <button
          onClick={() => setActiveTab('popular')}
          className={`px-4 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px ${
            activeTab === 'popular'
              ? 'text-brand-400 border-brand-500'
              : 'text-gray-400 border-transparent hover:text-gray-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Modelos Populares
          </div>
        </button>
        <button
          onClick={() => setActiveTab('deployed')}
          className={`px-4 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px ${
            activeTab === 'deployed'
              ? 'text-brand-400 border-brand-500'
              : 'text-gray-400 border-transparent hover:text-gray-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4" />
            Meus Deploys
            {models.length > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-brand-500/20 text-brand-400">
                {models.length}
              </span>
            )}
          </div>
        </button>
      </div>

      {/* Tab Content: Popular Models */}
      {activeTab === 'popular' && (
        <div className="space-y-6">
          {/* LLM Models */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-gray-300">LLMs (Chat/Completion)</span>
                <span className="text-xs text-gray-500">· vLLM Runtime</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {FIREWORKS_MODELS.llm.filter(m => m.featured).slice(0, 8).map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    setFormData(prev => ({ ...prev, model_type: 'llm', model_id: model.id, custom_model: false, port: 8000 }));
                    setWizardStep(3);
                    setShowDeployWizard(true);
                  }}
                  className="p-3 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-blue-500/30 text-left transition-all group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-200 group-hover:text-white truncate">{model.name}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-blue-400 transition-colors flex-shrink-0" />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">{model.size}</span>
                    <span>{model.vram}GB</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Image Models */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Image className="w-4 h-4 text-pink-400" />
              <span className="text-sm font-medium text-gray-300">Image Generation</span>
              <span className="text-xs text-gray-500">· Diffusers Runtime</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {FIREWORKS_MODELS.image.filter(m => m.featured).slice(0, 4).map((model) => (
                <button
                  key={model.id}
                  onClick={() => {
                    setFormData(prev => ({ ...prev, model_type: 'image', model_id: model.id, custom_model: false, port: 8002 }));
                    setWizardStep(3);
                    setShowDeployWizard(true);
                  }}
                  className="p-3 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-pink-500/30 text-left transition-all group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-200 group-hover:text-white truncate">{model.name}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-pink-400 transition-colors flex-shrink-0" />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="px-1.5 py-0.5 rounded bg-pink-500/10 text-pink-400">{model.size}</span>
                    <span>{model.vram}GB</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Speech & Embeddings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Mic className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-gray-300">Speech Recognition</span>
                <span className="text-xs text-gray-500">· Faster-Whisper</span>
              </div>
              <div className="grid gap-2">
                {FIREWORKS_MODELS.speech.filter(m => m.featured).slice(0, 3).map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setFormData(prev => ({ ...prev, model_type: 'speech', model_id: model.id, custom_model: false, port: 8001 }));
                      setWizardStep(3);
                      setShowDeployWizard(true);
                    }}
                    className="p-3 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-purple-500/30 text-left transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm font-medium text-gray-200 group-hover:text-white">{model.name}</span>
                        <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                          <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">{model.size}</span>
                          <span>{model.vram}GB</span>
                        </div>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-purple-400 transition-colors" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Search className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-gray-300">Embeddings</span>
                <span className="text-xs text-gray-500">· Sentence-Transformers</span>
              </div>
              <div className="grid gap-2">
                {FIREWORKS_MODELS.embeddings.filter(m => m.featured).slice(0, 3).map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setFormData(prev => ({ ...prev, model_type: 'embeddings', model_id: model.id, custom_model: false, port: 8003 }));
                      setWizardStep(3);
                      setShowDeployWizard(true);
                    }}
                    className="p-3 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-amber-500/30 text-left transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm font-medium text-gray-200 group-hover:text-white">{model.name}</span>
                        <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                          <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">{model.size}</span>
                          <span>{model.vram}GB</span>
                        </div>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-amber-400 transition-colors" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab Content: Deployed Models */}
      {activeTab === 'deployed' && (
        <>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400 mr-3" />
              <span className="text-gray-400">{t('models.loading')}</span>
            </div>
          ) : models.length === 0 ? (
            <div className="text-center py-16">
              <Server className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">Nenhum modelo deployado</h3>
              <p className="text-sm text-gray-500 mb-6">Escolha um modelo popular acima ou importe do HuggingFace</p>
              <button
                onClick={() => setActiveTab('popular')}
                className="px-4 py-2 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 transition-all text-sm"
              >
                Ver Modelos Populares
              </button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {models.map((model) => {
            const isDeploying = ['pending', 'deploying', 'downloading', 'starting'].includes(model.status);
            const isRunning = model.status === 'running';

            return (
              <div
                key={model.id}
                className="border border-white/10 rounded-xl bg-white/[0.02] overflow-hidden"
              >
                {/* Card Header */}
                <div className="p-4 border-b border-white/5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <ModelTypeIcon type={model.model_type} />
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-200 truncate">
                          {model.name || model.model_id.split('/').pop()}
                        </div>
                        <div className="text-xs text-gray-500 font-mono truncate">
                          {model.model_id}
                        </div>
                      </div>
                    </div>
                    <ModelStatusBadge status={model.status} />
                  </div>
                </div>

                {/* Progress bar (when deploying) */}
                {isDeploying && (
                  <div className="px-4 py-3 border-b border-white/5 bg-white/[0.02]">
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="text-gray-400">{model.status_message || t('models.wizard.preparing')}</span>
                      <span className="text-gray-500">{Math.round(model.progress)}%</span>
                    </div>
                    <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full transition-all duration-500"
                        style={{ width: `${model.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Card Body */}
                <div className="p-4 space-y-3">
                  {/* GPU Info */}
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Cpu className="w-3.5 h-3.5" />
                    <span>{model.num_gpus}x {model.gpu_name || 'GPU'}</span>
                    <span className="text-gray-600">•</span>
                    <span>{model.runtime}</span>
                  </div>

                  {/* Endpoint (when running) */}
                  {isRunning && model.endpoint_url && (
                    <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                      <div className="flex items-center justify-between gap-2">
                        <code className="text-xs text-gray-300 truncate">{model.endpoint_url}</code>
                        <button
                          onClick={() => copyToClipboard(model.endpoint_url)}
                          className="p-1 rounded hover:bg-white/10 text-gray-400"
                          title={t('models.card.copyUrl')}
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* API Key (when private) */}
                  {isRunning && model.access_type === 'private' && model.api_key && (
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Key className="w-3.5 h-3.5 text-amber-400" />
                          <code className="text-xs text-amber-300 truncate">
                            {model.api_key.substring(0, 20)}...
                          </code>
                        </div>
                        <button
                          onClick={() => copyToClipboard(model.api_key)}
                          className="p-1 rounded hover:bg-amber-500/20 text-amber-400"
                          title={t('models.card.copyApiKey')}
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Cost */}
                  {model.dph_total > 0 && (
                    <div className="flex items-center gap-2 text-xs">
                      <DollarSign className="w-3.5 h-3.5 text-gray-500" />
                      <span className="text-gray-400">
                        ${model.dph_total.toFixed(2)}/h
                      </span>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="px-4 py-3 border-t border-white/5 flex items-center gap-2 flex-wrap">
                  {isRunning && (
                    <>
                      {/* Chat Arena button for LLM models */}
                      {model.model_type === 'llm' && (
                        <button
                          onClick={() => navigate(`${basePath}/chat-arena?model=${encodeURIComponent(model.model_id)}&endpoint=${encodeURIComponent(model.endpoint_url || '')}`)}
                          className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 text-xs transition-all"
                          title="Usar no Chat Arena"
                        >
                          <Columns className="w-3.5 h-3.5" />
                          Chat Arena
                        </button>
                      )}
                      <button
                        onClick={() => handleStopModel(model.id)}
                        className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-xs transition-all"
                      >
                        <Square className="w-3.5 h-3.5" />
                        {t('models.card.stop')}
                      </button>
                      <a
                        href={`/api/v1/models/${model.id}/logs`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-xs transition-all"
                      >
                        <Terminal className="w-3.5 h-3.5" />
                        {t('models.card.logs')}
                      </a>
                    </>
                  )}
                  {!isDeploying && (
                    <button
                      onClick={() => handleDeleteModel(model.id)}
                      className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-red-500/10 text-red-400 text-xs transition-all"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      {t('models.card.delete')}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
            </div>
          )}
        </>
      )}

      {/* Info Box */}
      <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/20">
        <h4 className="text-sm font-medium text-brand-400 mb-2">{t('models.supportedTypes.title')}</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-400">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
              <span className="font-medium text-gray-300">{t('models.types.llm')}</span>
            </div>
            <span>{t('models.supportedTypes.llmDescription')}</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Mic className="w-3.5 h-3.5 text-purple-400" />
              <span className="font-medium text-gray-300">{t('models.types.speech')}</span>
            </div>
            <span>{t('models.supportedTypes.speechDescription')}</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Image className="w-3.5 h-3.5 text-pink-400" />
              <span className="font-medium text-gray-300">{t('models.types.image')}</span>
            </div>
            <span>{t('models.supportedTypes.imageDescription')}</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Search className="w-3.5 h-3.5 text-amber-400" />
              <span className="font-medium text-gray-300">{t('models.types.embeddings')}</span>
            </div>
            <span>{t('models.supportedTypes.embeddingsDescription')}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Models;

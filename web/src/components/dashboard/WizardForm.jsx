import React, { useState, useEffect, useRef } from 'react';
import {
  Search, Globe, MapPin, X, Cpu, MessageSquare, Lightbulb, Code, Zap,
  Sparkles, Gauge, Activity, Clock, Loader2, AlertCircle, Check, ChevronRight, ChevronLeft,
  Shield, Server, HardDrive, Timer, DollarSign, Database, Filter, Star, TrendingUp,
  ChevronDown, ChevronUp, Info, HelpCircle, Rocket, Hourglass, Settings, Network, Plus, Trash2,
  RefreshCw, ArrowRight
} from 'lucide-react';
import { Label, CardContent } from '../tailadmin-ui';
import { Button } from '../ui/button';
import { WorldMap, GPUSelector } from './';
import { COUNTRY_DATA, PERFORMANCE_TIERS, DEMO_OFFERS } from './constants';
import { apiGet, isDemoMode } from '../../utils/api';

// Componente Tooltip simples
const Tooltip = ({ children, text }) => (
  <span className="relative group inline-flex items-center">
    {children}
    <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-[10px] text-gray-200 bg-gray-800 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
      {text}
      <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
    </span>
  </span>
);

// Tooltips para termos técnicos
const TERM_TOOLTIPS = {
  'warm_pool': 'GPU reservada e pronta para uso imediato',
  'cpu_standby': 'CPU pequena que mantém dados sincronizados',
  'snapshot': 'Backup compactado dos seus dados',
  'serverless': 'Paga apenas quando a GPU está em uso',
  'failover': 'Recuperação automática em caso de falha',
  'rsync': 'Sincronização contínua de arquivos',
  'lz4': 'Compressão rápida de dados',
};

const WizardForm = ({
  // Migration mode props
  migrationMode = false,
  sourceMachine = null,
  targetType = null,
  initialStep = 1,
  // Step 1: Location
  searchCountry,
  selectedLocation,
  onSearchChange,
  onRegionSelect,
  onCountryClick,
  onClearSelection,
  // Step 2: Hardware
  selectedGPU,
  onSelectGPU,
  selectedGPUCategory,
  onSelectGPUCategory,
  selectedTier,
  onSelectTier,
  // Actions
  loading,
  onSubmit,
  // Provisioning (Step 4)
  provisioningCandidates = [],
  provisioningWinner = null,
  isProvisioning = false,
  onCancelProvisioning,
  onCompleteProvisioning,
  currentRound = 1,
  maxRounds = 3,
}) => {
  const tiers = PERFORMANCE_TIERS;
  const countryData = COUNTRY_DATA;
  const [validationErrors, setValidationErrors] = useState([]);
  const [currentStep, setCurrentStep] = useState(initialStep);
  const [failoverStrategy, setFailoverStrategy] = useState('snapshot_only'); // V5: Default é Snapshot Only

  // Set initial step when migration mode changes
  useEffect(() => {
    if (migrationMode && initialStep > 1) {
      setCurrentStep(initialStep);
    }
  }, [migrationMode, initialStep]);

  // Machine selection state
  const [selectionMode, setSelectionMode] = useState('recommended'); // 'recommended' or 'manual'
  const [provisioningStartTime, setProvisioningStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Advanced settings state
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [dockerImage, setDockerImage] = useState('pytorch/pytorch:latest');
  const [exposedPorts, setExposedPorts] = useState([
    { port: '22', protocol: 'TCP' },
    { port: '8888', protocol: 'TCP' },
    { port: '6006', protocol: 'TCP' },
  ]);

  // Track elapsed time during provisioning
  useEffect(() => {
    if (currentStep === 4 && !provisioningWinner) {
      setProvisioningStartTime(Date.now());
      setElapsedTime(0); // Reset timer when round changes
      const interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    } else if (provisioningWinner) {
      // Stop timer when winner found
    } else {
      setElapsedTime(0);
      setProvisioningStartTime(null);
    }
  }, [currentStep, provisioningWinner, currentRound]);

  // Format time as mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Estimate remaining time
  const getETA = () => {
    if (provisioningWinner) return 'Concluído!';
    const activeCandidates = provisioningCandidates.filter(c => c.status !== 'failed');
    if (activeCandidates.length === 0) return 'Sem máquinas ativas';
    const maxProgress = Math.max(...activeCandidates.map(c => c.progress || 0));
    if (maxProgress <= 10 || elapsedTime < 3) return 'Estimando...';
    const estimatedTotal = (elapsedTime / maxProgress) * 100;
    const remaining = Math.max(0, Math.ceil(estimatedTotal - elapsedTime));
    if (remaining < 60) return `~${remaining}s restantes`;
    return `~${Math.ceil(remaining / 60)}min restantes`;
  };

  // Format time ago (e.g., "30 min atrás", "1 dia atrás")
  const getTimeAgo = (date) => {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 60) return `${diffMins} min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays === 1) return 'Ontem';
    if (diffDays < 7) return `${diffDays} dias atrás`;
    return `${Math.floor(diffDays / 7)} semana(s) atrás`;
  };

  const [recommendedMachines, setRecommendedMachines] = useState([]);
  const [loadingMachines, setLoadingMachines] = useState(false);
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [gpuSearchQuery, setGpuSearchQuery] = useState('');
  const [apiError, setApiError] = useState(null);

  // Migration type: 'new' (clean machine) or 'restore' (restore from snapshot)
  const [migrationType, setMigrationType] = useState('restore'); // Default to restore when migrating

  // Snapshot selection for restore
  const [availableSnapshots, setAvailableSnapshots] = useState([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState(null);
  const [loadingSnapshots, setLoadingSnapshots] = useState(false);

  // Fetch ALL snapshots globally - snapshots are stored in B2/R2 and can be restored to any machine
  useEffect(() => {
    const fetchSnapshots = async () => {
      if (!migrationMode || migrationType !== 'restore') {
        setAvailableSnapshots([]);
        setSelectedSnapshot(null);
        return;
      }

      setLoadingSnapshots(true);

      // Mock snapshots for demo/fallback
      const mockSnapshots = [
        {
          id: 'snap_latest',
          name: 'workspace-backup',
          short_id: 'abc123',
          created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
          size_gb: 12.5,
          status: 'ready',
          isLatest: true,
          paths: ['/workspace'],
        },
        {
          id: 'snap_yesterday',
          name: 'daily-backup',
          short_id: 'def456',
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
          size_gb: 11.2,
          status: 'ready',
          paths: ['/workspace'],
        },
        {
          id: 'snap_week',
          name: 'weekly-backup',
          short_id: 'ghi789',
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(), // 1 week ago
          size_gb: 10.8,
          status: 'ready',
          paths: ['/workspace'],
        },
      ];

      // In demo mode, use mock snapshots directly
      if (isDemoMode()) {
        setAvailableSnapshots(mockSnapshots);
        setSelectedSnapshot(mockSnapshots[0]); // Auto-select latest
        setLoadingSnapshots(false);
        return;
      }

      try {
        // Fetch ALL snapshots globally from B2/R2 storage - not filtered by machine
        const response = await apiGet('/api/snapshots');
        if (response.ok) {
          const data = await response.json();
          // API returns { snapshots: [...] } with restic snapshot data
          const snapshots = (data.snapshots || []).map((snap, index) => ({
            id: snap.id || snap.short_id,
            name: snap.tags?.join(', ') || snap.hostname || `Snapshot ${snap.short_id}`,
            short_id: snap.short_id,
            created_at: snap.time,
            size_gb: snap.summary?.total_bytes_processed ? (snap.summary.total_bytes_processed / (1024 * 1024 * 1024)).toFixed(1) : null,
            status: 'ready',
            isLatest: index === 0,
            paths: snap.paths || ['/workspace'],
            hostname: snap.hostname,
          }));

          if (snapshots.length > 0) {
            setAvailableSnapshots(snapshots);
            setSelectedSnapshot(snapshots[0]); // Auto-select latest
          } else {
            // API returned empty, use mock as fallback
            setAvailableSnapshots(mockSnapshots);
            setSelectedSnapshot(mockSnapshots[0]);
          }
        } else {
          // API error, use mock snapshots as fallback for development
          console.log('Snapshots API not available, using mock data');
          setAvailableSnapshots(mockSnapshots);
          setSelectedSnapshot(mockSnapshots[0]);
        }
      } catch (err) {
        console.error('Failed to fetch snapshots:', err);
        // Use mock snapshots as fallback
        setAvailableSnapshots(mockSnapshots);
        setSelectedSnapshot(mockSnapshots[0]);
      } finally {
        setLoadingSnapshots(false);
      }
    };

    fetchSnapshots();
  }, [migrationMode, migrationType]);

  // Lista completa de GPUs disponíveis
  const allGPUs = [
    { name: 'RTX 3060', vram: '12GB', priceRange: '$0.10-0.20/h' },
    { name: 'RTX 3070', vram: '8GB', priceRange: '$0.15-0.25/h' },
    { name: 'RTX 3080', vram: '10GB', priceRange: '$0.20-0.35/h' },
    { name: 'RTX 3090', vram: '24GB', priceRange: '$0.30-0.50/h' },
    { name: 'RTX 4070', vram: '12GB', priceRange: '$0.25-0.40/h' },
    { name: 'RTX 4080', vram: '16GB', priceRange: '$0.40-0.60/h' },
    { name: 'RTX 4090', vram: '24GB', priceRange: '$0.55-0.85/h' },
    { name: 'GTX 1080 Ti', vram: '11GB', priceRange: '$0.08-0.15/h' },
    { name: 'A100 40GB', vram: '40GB', priceRange: '$0.80-1.20/h' },
    { name: 'A100 80GB', vram: '80GB', priceRange: '$1.20-2.00/h' },
    { name: 'H100 80GB', vram: '80GB', priceRange: '$2.00-3.50/h' },
    { name: 'A10', vram: '24GB', priceRange: '$0.35-0.55/h' },
    { name: 'A40', vram: '48GB', priceRange: '$0.50-0.80/h' },
    { name: 'L40', vram: '48GB', priceRange: '$0.70-1.00/h' },
    { name: 'V100', vram: '16GB', priceRange: '$0.40-0.70/h' },
    { name: 'T4', vram: '16GB', priceRange: '$0.20-0.35/h' },
  ];

  // Filtrar GPUs pela busca
  const filteredGPUs = gpuSearchQuery
    ? allGPUs.filter(gpu =>
        gpu.name.toLowerCase().includes(gpuSearchQuery.toLowerCase()) ||
        gpu.vram.toLowerCase().includes(gpuSearchQuery.toLowerCase())
      )
    : allGPUs;

  const COUNTRY_NAMES = {
    'US': 'Estados Unidos',
    'CA': 'Canadá',
    'MX': 'México',
    'GB': 'Reino Unido',
    'FR': 'França',
    'DE': 'Alemanha',
    'ES': 'Espanha',
    'IT': 'Itália',
    'PT': 'Portugal',
    'JP': 'Japão',
    'CN': 'China',
    'KR': 'Coreia do Sul',
    'SG': 'Singapura',
    'IN': 'Índia',
    'BR': 'Brasil',
    'AR': 'Argentina',
    'CL': 'Chile',
    'CO': 'Colômbia',
  };

  const steps = [
    { id: 1, name: 'Região', icon: Globe, description: 'Localização' },
    { id: 2, name: 'Hardware', icon: Cpu, description: 'GPU e performance' },
    { id: 3, name: 'Estratégia', icon: Shield, description: 'Failover' },
    { id: 4, name: 'Provisionar', icon: Rocket, description: 'Conectando' },
  ];

  // Estratégias REAIS de failover - custos são ADICIONAIS ao custo da GPU
  // V5 - Snapshot Only primeiro, removido modal de confirmação
  const failoverOptions = [
    {
      id: 'snapshot_only',
      name: 'Snapshot Only',
      provider: 'GCP + B2',
      icon: Database,
      description: 'Apenas snapshots automáticos. CPU GCP para restore quando necessário.',
      recoveryTime: '2-5 min',
      dataLoss: 'Até 60 min',
      recommended: true,
      available: true,
    },
    {
      id: 'vast_warmpool',
      name: 'VAST.ai Warm Pool',
      provider: 'VAST.ai + GCP + B2',
      icon: Zap,
      description: 'Failover completo com GPU warm, CPU standby e snapshots automáticos.',
      recoveryTime: '30-90 seg',
      dataLoss: 'Zero',
      costHour: '+$0.03/h',
      costMonth: '~$22/mês',
      costDetail: 'CPU GCP $0.01/h + Volume VAST $0.02/h + B2 ~$0.50/mês',
      howItWorks: 'GPU #2 fica parada no mesmo host (volume compartilhado). CPU no GCP (e2-medium spot $0.01/h) faz rsync contínuo. Snapshots LZ4 vão para Backblaze B2 a cada 60min.',
      features: [
        'GPU warm pool no mesmo host',
        'CPU standby GCP (+$0.01/h)',
        'Volume persistente VAST (+$0.02/h)',
        'Snapshots B2 (~$0.50/mês)',
      ],
      requirements: 'Host VAST.ai com 2+ GPUs',
      available: true,
    },
    {
      id: 'cpu_standby_only',
      name: 'CPU Standby Only',
      provider: 'GCP + B2',
      icon: Server,
      description: 'CPU GCP mantém dados sincronizados. Sem GPU warm.',
      recoveryTime: '1-3 min',
      dataLoss: 'Mínima',
      costHour: '+$0.01/h',
      costMonth: '~$8/mês',
      costDetail: 'CPU GCP $0.01/h + B2 ~$0.50/mês',
      howItWorks: 'Snapshots LZ4 automáticos a cada 60min para Backblaze B2. CPU GCP (e2-medium spot $0.01/h) sempre ligada. Quando falhar, nova GPU é provisionada e dados restaurados.',
      features: [
        'Snapshots automáticos (60min)',
        'CPU standby GCP (+$0.01/h)',
        'Storage B2 (~$0.50/mês)',
        'Sem GPU idle',
      ],
      requirements: 'Nenhum extra',
      recommended: false,
      available: true,
    },
    {
      id: 'no_failover',
      name: 'Sem Failover',
      provider: 'Apenas GPU',
      icon: AlertCircle,
      description: 'Sem proteção contra falhas. Se a máquina cair, você perde todos os dados.',
      recoveryTime: 'Manual',
      dataLoss: 'Total',
      costHour: '$0',
      costMonth: '$0',
      costDetail: 'Sem custo extra, mas sem proteção',
      howItWorks: 'Apenas a GPU principal. Sem snapshots, sem backup, sem recuperação automática. Se houver falha de hardware ou interrupção, todos os dados serão perdidos.',
      features: [
        'Sem custo adicional',
        'Sem snapshots',
        'Sem recuperação',
        'Dados perdidos em falha',
      ],
      requirements: 'Nenhum',
      recommended: false,
      available: true,
      danger: true, // Flag para mostrar warning
    },
  ];

  // Fetch recommended machines when tier or location changes
  useEffect(() => {
    const fetchRecommendedMachines = async () => {
      if (!selectedTier) {
        setRecommendedMachines([]);
        return;
      }

      setLoadingMachines(true);
      setApiError(null);

      try {
        // Get tier config for price range and build filter params
        const tier = tiers.find(t => t.name === selectedTier);

        // Map region selection to API-expected codes (US, EU, ASIA)
        // API expects: US, EU, ASIA - not individual country codes
        let regionCode = '';
        if (selectedLocation?.isRegion) {
          const regionName = selectedLocation.name?.toLowerCase();
          if (regionName === 'eua' || regionName === 'usa' || regionName === 'estados unidos') {
            regionCode = 'US';
          } else if (regionName === 'europa' || regionName === 'europe') {
            regionCode = 'EU';
          } else if (regionName === 'ásia' || regionName === 'asia') {
            regionCode = 'ASIA';
          } else if (regionName === 'américa do sul' || regionName === 'south america') {
            regionCode = 'SA';  // Try SA for South America
          }
        } else if (selectedLocation?.codes?.[0]) {
          // For individual country selections, map to their region
          const countryCode = selectedLocation.codes[0];
          const usCountries = ['US', 'CA', 'MX'];
          const euCountries = ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'];
          const asiaCountries = ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'];
          const saCountries = ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'];

          if (usCountries.includes(countryCode)) regionCode = 'US';
          else if (euCountries.includes(countryCode)) regionCode = 'EU';
          else if (asiaCountries.includes(countryCode)) regionCode = 'ASIA';
          else if (saCountries.includes(countryCode)) regionCode = 'SA';
          else regionCode = countryCode;  // Fallback to country code
        }

        // In demo mode, use DEMO_OFFERS instead of real API
        if (isDemoMode()) {
          // Filter demo offers by tier
          let filteredOffers = [...DEMO_OFFERS];

          if (tier?.filter) {
            if (tier.filter.cpu_only) {
              // Filter for CPU-only machines (num_gpus === 0)
              filteredOffers = filteredOffers.filter(o => o.num_gpus === 0);
            }
            if (tier.filter.min_gpu_ram) {
              filteredOffers = filteredOffers.filter(o => o.gpu_ram >= tier.filter.min_gpu_ram);
            }
            if (tier.filter.max_price) {
              filteredOffers = filteredOffers.filter(o => o.dph_total <= tier.filter.max_price);
            }
          }

          // Filter by region if specified
          if (regionCode) {
            filteredOffers = filteredOffers.filter(o =>
              o.geolocation === regionCode ||
              (regionCode === 'US' && ['US', 'CA', 'MX'].includes(o.geolocation)) ||
              (regionCode === 'EU' && ['EU', 'GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'PL', 'CZ', 'AT', 'CH', 'BE', 'SE', 'NO', 'DK', 'FI', 'IE'].includes(o.geolocation))
            );
          }

          // Sort by price
          filteredOffers.sort((a, b) => a.dph_total - b.dph_total);

          // Add metadata and labels
          const labeled = filteredOffers.slice(0, 3).map((offer, idx) => ({
            ...offer,
            provider: 'Vast.ai',
            location: offer.geolocation === 'US' ? 'Estados Unidos' :
                      offer.geolocation === 'EU' ? 'Europa' : offer.geolocation,
            reliability: offer.verified ? 99 : 95,
            label: idx === 0 ? 'Mais econômico' : idx === 1 ? 'Melhor custo-benefício' : 'Mais rápido'
          }));

          if (labeled.length > 0) {
            setRecommendedMachines(labeled);
          } else {
            setApiError('api_empty');
            setRecommendedMachines([]);
          }
          setLoadingMachines(false);
          return;
        }

        // Build query params based on tier filter (for real API)
        const params = new URLSearchParams();
        params.append('limit', '5');
        params.append('order_by', 'dph_total');
        if (regionCode) params.append('region', regionCode);

        // Apply tier-specific filters
        if (tier?.filter) {
          if (tier.filter.cpu_only) {
            params.append('num_gpus', '0');  // CPU-only machines have 0 GPUs
          }
          if (tier.filter.min_gpu_ram) params.append('min_gpu_ram', tier.filter.min_gpu_ram);
          if (tier.filter.max_price) params.append('max_price', tier.filter.max_price);
          if (tier.filter.verified_only) params.append('verified_only', 'true');
        }

        // Fetch offers from API
        const response = await apiGet(`/api/v1/instances/offers?${params}`);

        if (response.ok) {
          const data = await response.json();
          if (data.offers && data.offers.length > 0) {
            // Add labels to first 3 offers
            const labeled = data.offers.slice(0, 3).map((offer, idx) => ({
              ...offer,
              label: idx === 0 ? 'Mais econômico' : idx === 1 ? 'Melhor custo-benefício' : 'Mais rápido'
            }));
            setRecommendedMachines(labeled);
            return;
          }
        }

        // No offers available
        setApiError('api_empty');
        setRecommendedMachines([]);
      } catch (err) {
        console.error('Failed to fetch offers:', err);
        setApiError('api_error');
        setRecommendedMachines([]);
      } finally {
        setLoadingMachines(false);
      }
    };

    fetchRecommendedMachines();
  }, [selectedTier, selectedLocation]);

  // Verifica se os dados do step estão preenchidos
  const isStepDataComplete = (stepId) => {
    // In migration mode, step 1 is always considered complete (location is pre-selected)
    if (stepId === 1) return !!selectedLocation || migrationMode;
    if (stepId === 2) return !!selectedTier;
    if (stepId === 3) return !!failoverStrategy;
    if (stepId === 4) return !!provisioningWinner;
    return false;
  };

  // Verifica se o step já foi passado (usuário avançou além dele)
  const isStepPassed = (stepId) => {
    return currentStep > stepId && isStepDataComplete(stepId);
  };

  // Mantém compatibilidade com código existente
  const isStepComplete = isStepDataComplete;

  const canProceedToStep = (stepId) => {
    if (stepId < currentStep) return true;
    if (stepId === currentStep + 1) return isStepDataComplete(currentStep);
    if (stepId === currentStep) return true;
    return false;
  };

  const goToStep = (stepId) => {
    if (canProceedToStep(stepId)) {
      setCurrentStep(stepId);
    }
  };

  const handleNext = () => {
    console.log('[WizardForm] handleNext called, currentStep:', currentStep);
    console.log('[WizardForm] isStepComplete:', isStepComplete(currentStep));
    console.log('[WizardForm] failoverStrategy:', failoverStrategy);
    if (currentStep < steps.length && isStepComplete(currentStep)) {
      if (currentStep === 3) {
        console.log('[WizardForm] Step 3 -> calling handleStartProvisioning');
        handleStartProvisioning();
      } else {
        console.log('[WizardForm] Advancing to step:', currentStep + 1);
        setCurrentStep(currentStep + 1);
      }
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      // Se está no step 4 (provisioning) e quer voltar, cancelar o provisioning
      if (currentStep === 4 && onCancelProvisioning) {
        onCancelProvisioning();
      }
      setCurrentStep(currentStep - 1);
    }
  };

  // State for payment confirmation and balance
  const [showPaymentConfirm, setShowPaymentConfirm] = useState(false);
  const [userBalance, setUserBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [balanceError, setBalanceError] = useState(null);

  // Fetch user balance when entering step 3
  useEffect(() => {
    if (currentStep === 3) {
      fetchUserBalance();
    }
  }, [currentStep]);

  const fetchUserBalance = async () => {
    setLoadingBalance(true);
    setBalanceError(null);

    try {
      // In demo mode, use mock balance
      if (isDemoMode()) {
        setUserBalance(10.00); // Mock sufficient balance for demo
        setLoadingBalance(false);
        return;
      }

      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/v1/balance', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const balance = data.credit ?? data.balance ?? 0;
        setUserBalance(parseFloat(balance) || 0);
      } else {
        setUserBalance(0);
        setBalanceError('Erro ao buscar saldo');
      }
    } catch (err) {
      console.error('Failed to fetch balance:', err);
      setUserBalance(0);
      setBalanceError('Erro ao buscar saldo');
    } finally {
      setLoadingBalance(false);
    }
  };

  const handleStartProvisioning = () => {
    console.log('[WizardForm] handleStartProvisioning called');
    console.log('[WizardForm] selectedLocation:', selectedLocation);
    console.log('[WizardForm] selectedTier:', selectedTier);
    console.log('[WizardForm] failoverStrategy:', failoverStrategy);
    const errors = [];
    const MIN_BALANCE = 0.10; // Saldo mínimo necessário ($0.10)

    if (!selectedLocation) {
      errors.push('Por favor, selecione uma localização para sua máquina');
    }

    if (!selectedTier) {
      errors.push('Por favor, selecione um tier de performance');
    }

    // Validar saldo mínimo (skip in demo mode)
    console.log('[WizardForm] isDemoMode:'());
    console.log('[WizardForm] userBalance:', userBalance);
    if (!isDemoMode() && userBalance !== null && userBalance < MIN_BALANCE) {
      errors.push(`Saldo insuficiente. Você precisa de pelo menos $${MIN_BALANCE.toFixed(2)} para criar uma máquina. Saldo atual: $${userBalance.toFixed(2)}`);
    }

    console.log('[WizardForm] validation errors:', errors);
    if (errors.length > 0) {
      console.log('[WizardForm] VALIDATION FAILED - returning early');
      setValidationErrors(errors);
      if (!selectedLocation) setCurrentStep(1);
      else if (!selectedTier) setCurrentStep(2);
      return;
    }

    console.log('[WizardForm] Validation passed! Advancing to step 4 and calling onSubmit');
    console.log('[WizardForm] onSubmit function exists:', typeof onSubmit === 'function');
    console.log('[WizardForm] selectedMachine:', selectedMachine);
    setValidationErrors([]);
    // V5: Ir direto para provisioning sem modal de confirmação
    setCurrentStep(4);
    if (typeof onSubmit === 'function') {
      console.log('[WizardForm] Calling onSubmit NOW with selectedMachine');
      // Pass selectedMachine with offer_id, failover strategy, and tier
      onSubmit({
        machine: selectedMachine,
        offerId: selectedMachine?.id,
        failoverStrategy,
        tier: selectedTier,
        region: selectedLocation,
      });
    } else {
      console.error('[WizardForm] ERROR: onSubmit is not a function!');
    }
  };

  const handleConfirmPayment = () => {
    // V5: Mantido para compatibilidade mas não usado mais
    setShowPaymentConfirm(false);
    setCurrentStep(4);
    onSubmit({
      machine: selectedMachine,
      offerId: selectedMachine?.id,
      failoverStrategy,
      tier: selectedTier,
      region: selectedLocation,
    });
  };

  const handleCancelPayment = () => {
    setShowPaymentConfirm(false);
  };

  const selectedFailover = failoverOptions.find(o => o.id === failoverStrategy);

  // Get estimated cost based on selected tier
  const getEstimatedCost = () => {
    const tierData = tiers.find(t => t.name === selectedTier);
    if (!tierData) return { hourly: '0.00', daily: '0.00' };
    // Extract min price from priceRange like "$0.10-0.30/h"
    const match = tierData.priceRange?.match(/\$(\d+\.?\d*)/);
    const minPrice = match ? parseFloat(match[1]) : 0.20;
    return {
      hourly: minPrice.toFixed(2),
      daily: (minPrice * 24).toFixed(2)
    };
  };

  return (
    <CardContent className="p-6 space-y-6">
      {/* Migration Banner */}
      {migrationMode && sourceMachine && (
        <div className="bg-brand-500/20 border border-brand-500/50 rounded-lg p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-brand-500/30 flex items-center justify-center flex-shrink-0">
            <RefreshCw className="w-5 h-5 text-brand-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <p className="font-medium text-white">
                Migrando Instância
              </p>
              <span className="px-2 py-0.5 text-xs bg-brand-500/30 text-brand-300 rounded">
                {targetType === 'cpu' ? 'GPU → CPU' : 'CPU → GPU'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-400 mt-1">
              <span className="flex items-center gap-1">
                <Server className="w-3 h-3" />
                {sourceMachine.gpu_name || 'CPU'}
              </span>
              <ArrowRight className="w-3 h-3 text-brand-400" />
              <span className="flex items-center gap-1">
                {targetType === 'cpu' ? (
                  <><Cpu className="w-3 h-3" /> CPU</>
                ) : (
                  <><Server className="w-3 h-3" /> GPU</>
                )}
              </span>
              <span className="text-gray-500">•</span>
              <span>ID: {sourceMachine.id}</span>
            </div>
          </div>
        </div>
      )}

      {/* Migration Type Selection - Nova do zero vs Restaurar */}
      {migrationMode && sourceMachine && (
        <div className="space-y-3">
          <div>
            <Label className="text-gray-300 text-sm font-medium">Tipo de Migração</Label>
            <p className="text-xs text-gray-500 mt-1">Escolha como deseja configurar a nova máquina</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Option: Restore from snapshot */}
            <button
              onClick={() => setMigrationType('restore')}
              data-testid="migration-type-restore"
              className={`p-4 rounded-lg border text-left transition-all ${
                migrationType === 'restore'
                  ? 'bg-brand-500/10 border-brand-500'
                  : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  migrationType === 'restore' ? 'bg-brand-500/20 text-brand-400' : 'bg-white/5 text-gray-500'
                }`}>
                  <Database className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${migrationType === 'restore' ? 'text-brand-400' : 'text-gray-300'}`}>
                      Restaurar Dados
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                      Recomendado
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Restaura todos os arquivos e configurações do snapshot da máquina anterior
                  </p>
                </div>
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                  migrationType === 'restore' ? 'border-brand-500 bg-brand-500/20' : 'border-white/20'
                }`}>
                  {migrationType === 'restore' && <div className="w-2 h-2 rounded-full bg-brand-400" />}
                </div>
              </div>
            </button>

            {/* Option: New machine from scratch */}
            <button
              onClick={() => setMigrationType('new')}
              data-testid="migration-type-new"
              className={`p-4 rounded-lg border text-left transition-all ${
                migrationType === 'new'
                  ? 'bg-brand-500/10 border-brand-500'
                  : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  migrationType === 'new' ? 'bg-brand-500/20 text-brand-400' : 'bg-white/5 text-gray-500'
                }`}>
                  <Sparkles className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${migrationType === 'new' ? 'text-brand-400' : 'text-gray-300'}`}>
                      Nova do Zero
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Máquina completamente limpa, sem restaurar dados anteriores
                  </p>
                </div>
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                  migrationType === 'new' ? 'border-brand-500 bg-brand-500/20' : 'border-white/20'
                }`}>
                  {migrationType === 'new' && <div className="w-2 h-2 rounded-full bg-brand-400" />}
                </div>
              </div>
            </button>
          </div>

          {/* Warning when selecting "new" */}
          {migrationType === 'new' && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs text-amber-400 font-medium">Atenção</p>
                <p className="text-[10px] text-amber-400/80">
                  A nova máquina será criada sem os dados da máquina anterior.
                  Se você tem arquivos importantes, considere usar "Restaurar Dados".
                </p>
              </div>
            </div>
          )}

          {/* Snapshot selector when restore is selected */}
          {migrationType === 'restore' && (
            <div className="space-y-2">
              <Label className="text-gray-400 text-xs font-medium">Selecione o Snapshot</Label>

              {loadingSnapshots ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-4 h-4 animate-spin text-gray-400 mr-2" />
                  <span className="text-xs text-gray-400">Buscando snapshots...</span>
                </div>
              ) : availableSnapshots.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {availableSnapshots.map((snapshot) => {
                    const isSelected = selectedSnapshot?.id === snapshot.id;
                    const createdDate = new Date(snapshot.created_at);
                    const timeAgo = getTimeAgo(createdDate);

                    return (
                      <button
                        key={snapshot.id}
                        onClick={() => setSelectedSnapshot(snapshot)}
                        data-testid={`snapshot-${snapshot.id}`}
                        className={`w-full p-3 rounded-lg border text-left transition-all ${
                          isSelected
                            ? 'bg-brand-500/10 border-brand-500'
                            : 'bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                            isSelected ? 'border-brand-500 bg-brand-500/20' : 'border-white/20'
                          }`}>
                            {isSelected && <div className="w-2 h-2 rounded-full bg-brand-400" />}
                          </div>

                          <div className={`w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 ${
                            isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-white/5 text-gray-500'
                          }`}>
                            <Database className="w-4 h-4" />
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-medium ${isSelected ? 'text-brand-400' : 'text-gray-300'}`}>
                                {snapshot.name}
                              </span>
                              {snapshot.short_id && (
                                <code className="text-[9px] px-1 py-0.5 rounded bg-white/5 text-gray-500 font-mono">
                                  {snapshot.short_id}
                                </code>
                              )}
                              {snapshot.isLatest && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                                  Mais recente
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
                              <span>{timeAgo}</span>
                              <span>•</span>
                              <span>{typeof snapshot.size_gb === 'number' ? snapshot.size_gb.toFixed(1) : snapshot.size_gb || '?'}GB</span>
                              <span>•</span>
                              {snapshot.paths && (
                                <>
                                  <span className="text-gray-600">{snapshot.paths.join(', ')}</span>
                                  <span>•</span>
                                </>
                              )}
                              <span className={snapshot.status === 'ready' ? 'text-emerald-400' : 'text-amber-400'}>
                                {snapshot.status === 'ready' ? 'Pronto' : 'Processando'}
                              </span>
                            </div>
                          </div>

                          <div className="flex-shrink-0">
                            <Clock className={`w-4 h-4 ${isSelected ? 'text-brand-400' : 'text-gray-600'}`} />
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs text-amber-400 font-medium">Nenhum snapshot disponível</p>
                    <p className="text-[10px] text-amber-400/80">
                      Não há snapshots salvos para esta máquina. A migração será feita com máquina limpa.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Payment Confirmation Modal */}
      {showPaymentConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl animate-scaleIn">
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 mb-4">
                <DollarSign className="w-7 h-7 text-brand-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Confirmar Provisionamento</h3>
              <p className="text-sm text-gray-400">
                Você está prestes a provisionar uma máquina GPU. Verifique os custos estimados abaixo.
              </p>
            </div>

            {/* Balance Display */}
            <div className={`rounded-lg p-3 mb-4 flex items-center justify-between ${
              userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                ? 'bg-red-500/10 border border-red-500/30'
                : 'bg-green-500/10 border border-green-500/30'
            }`}>
              <div className="flex items-center gap-2">
                <DollarSign className={`w-4 h-4 ${
                  userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                    ? 'text-red-400'
                    : 'text-green-400'
                }`} />
                <span className="text-sm text-gray-300">Seu saldo:</span>
              </div>
              <span className={`text-lg font-bold ${
                userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                  ? 'text-red-400'
                  : 'text-green-400'
              }`}>
                ${userBalance?.toFixed(2) || '-.--'}
              </span>
            </div>

            {/* Insufficient balance warning */}
            {userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly) && (
              <div className="flex items-start gap-2 mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs text-red-400 font-medium">Saldo insuficiente</p>
                  <p className="text-[10px] text-red-400/80">
                    Você precisa de pelo menos ${getEstimatedCost().hourly}/h. Adicione créditos antes de continuar.
                  </p>
                </div>
              </div>
            )}

            {/* Cost Summary */}
            <div className="bg-gray-800/50 rounded-lg p-4 mb-6 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">GPU Tier</span>
                <span className="text-sm font-medium text-white">{selectedTier}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Região</span>
                <span className="text-sm font-medium text-white">{selectedLocation?.name || 'Global'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Estratégia</span>
                <span className="text-sm font-medium text-white">{selectedFailover?.name || '-'}</span>
              </div>
              <div className="border-t border-gray-700 my-2" />
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Custo estimado/hora</span>
                <span className="text-lg font-bold text-brand-400">${getEstimatedCost().hourly}/h</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">Custo estimado/dia</span>
                <span className="text-sm text-gray-300">${getEstimatedCost().daily}/dia</span>
              </div>
              {selectedFailover?.costHour && (
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-500">+ Failover</span>
                  <span className="text-gray-400">{selectedFailover.costHour}</span>
                </div>
              )}
            </div>

            {/* Warning */}
            <div className="flex items-start gap-2 mb-6 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-yellow-400/90">
                A cobrança começa assim que a máquina ficar online. Você pode pausar ou destruir a instância a qualquer momento.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <Button
                onClick={handleCancelPayment}
                variant="ghost"
                className="flex-1 text-gray-400 hover:text-white hover:bg-gray-800"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleConfirmPayment}
                disabled={userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)}
                className={`flex-1 ${
                  userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                    ? 'bg-gray-600 cursor-not-allowed opacity-50'
                    : 'bg-brand-500 hover:bg-brand-600'
                } text-white`}
                data-testid="confirm-payment-button"
              >
                <Check className="w-4 h-4 mr-2" />
                {userBalance !== null && userBalance < parseFloat(getEstimatedCost().hourly)
                  ? 'Saldo Insuficiente'
                  : 'Confirmar e Iniciar'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Stepper Progress Bar */}
      <div className="relative">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const StepIcon = step.icon;
            const isPassed = isStepPassed(step.id);
            const isCurrent = currentStep === step.id;
            const isClickable = canProceedToStep(step.id);
            const isSkippedInMigration = migrationMode && step.id === 1;

            return (
              <React.Fragment key={step.id}>
                <button
                  onClick={() => !isSkippedInMigration && goToStep(step.id)}
                  disabled={!isClickable || isSkippedInMigration}
                  className={`relative z-10 flex flex-col items-center gap-2 transition-all ${
                    isSkippedInMigration ? 'opacity-50 cursor-not-allowed' : isClickable ? 'cursor-pointer' : 'cursor-not-allowed'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                    isSkippedInMigration
                      ? 'bg-gray-500/20 border-gray-500 text-gray-400'
                      : isPassed
                        ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                        : isCurrent
                          ? 'bg-brand-500/10 border-brand-400 text-brand-400'
                          : 'bg-white/5 border-white/10 text-gray-500'
                  }`}>
                    {isSkippedInMigration ? (
                      <Check className="w-4 h-4 text-gray-500" />
                    ) : isPassed ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <StepIcon className="w-4 h-4" />
                    )}
                  </div>
                  <div className="text-center">
                    <div className={`text-[10px] font-bold mb-0.5 ${
                      isSkippedInMigration ? 'text-gray-500' : isPassed ? 'text-brand-400' : isCurrent ? 'text-brand-400' : 'text-gray-600'
                    }`}>
                      {isSkippedInMigration ? 'Pulado' : `${step.id}/${steps.length}`}
                    </div>
                    <div className={`text-xs font-medium ${
                      isSkippedInMigration ? 'text-gray-500' : isPassed ? 'text-brand-400' : isCurrent ? 'text-gray-200' : 'text-gray-500'
                    }`}>
                      {step.name}
                    </div>
                    <div className={`text-[10px] ${
                      isCurrent || isPassed ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {step.description}
                    </div>
                  </div>
                </button>

                {index < steps.length - 1 && (
                  <div className="flex-1 h-0.5 mx-3 relative top-[-16px]">
                    <div className="absolute inset-0 bg-white/10 rounded-full" />
                    <div
                      className="absolute inset-y-0 left-0 bg-brand-500 rounded-full transition-all duration-500"
                      style={{ width: isStepPassed(step.id) ? '100%' : '0%' }}
                    />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-400 mb-2">
                Por favor, corrija os seguintes campos:
              </h4>
              <ul className="space-y-1">
                {validationErrors.map((error, idx) => (
                  <li key={idx} className="text-sm text-red-300/80 flex items-start gap-2">
                    <span className="text-red-400/60 mt-1">•</span>
                    <span>{error}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Selection Summary Bar - Shows selections from previous steps */}
      {currentStep > 1 && (
        <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10 mb-4">
          <span className="text-xs text-gray-500 mr-1">Selecionado:</span>

          {/* Location Tag */}
          {selectedLocation && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-brand-500/10 border border-brand-500/30 text-brand-400 rounded-full text-xs font-medium">
              {selectedLocation.isRegion ? <Globe className="w-3 h-3" /> : <MapPin className="w-3 h-3" />}
              <span>{selectedLocation.name}</span>
            </div>
          )}

          {/* Tier Tag - Show if step > 1 and tier selected */}
          {currentStep > 2 && selectedTier && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded-full text-xs font-medium">
              <Cpu className="w-3 h-3" />
              <span>{selectedTier}</span>
            </div>
          )}

          {/* GPU Tag - Show if step > 2 and GPU selected */}
          {currentStep > 2 && selectedGPU && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded-full text-xs font-medium">
              <Server className="w-3 h-3" />
              <span>{selectedGPU}</span>
            </div>
          )}

          {/* Strategy Tag - Show if step > 3 and strategy selected */}
          {currentStep > 3 && failoverStrategy && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-full text-xs font-medium">
              <Shield className="w-3 h-3" />
              <span>{failoverOptions.find(f => f.id === failoverStrategy)?.name || failoverStrategy}</span>
            </div>
          )}
        </div>
      )}

      {/* Step 1: Localização */}
      {currentStep === 1 && (
        <div className="space-y-5 animate-fadeIn">
          <div className="space-y-4">
            <div className="flex flex-col gap-3">
              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
                  <Search className="w-4 h-4 text-gray-500" />
                </div>
                <input
                  type="text"
                  placeholder="Buscar país ou região (ex: Brasil, Europa, Japão...)"
                  className="w-full pl-11 pr-4 py-3 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-white/20 focus:border-white/20 placeholder:text-gray-500 transition-all"
                  value={searchCountry}
                  onChange={(e) => onSearchChange(e.target.value)}
                />
              </div>

              {selectedLocation && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">
                    {selectedLocation.isRegion ? 'Região:' : 'País:'}
                  </span>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 text-gray-200 rounded-full text-sm font-medium">
                    {selectedLocation.isRegion ? <Globe className="w-3.5 h-3.5" /> : <MapPin className="w-3.5 h-3.5" />}
                    <span>{selectedLocation.name}</span>
                    <button
                      onClick={onClearSelection}
                      className="ml-1 p-0.5 rounded-full hover:bg-white/10 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}

              {!selectedLocation && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-gray-500 mr-1 self-center">Regiões:</span>
                  {['eua', 'europa', 'asia', 'america do sul'].map((regionKey) => (
                    <button
                      key={regionKey}
                      data-testid={`region-${regionKey.replace(' ', '-')}`}
                      onClick={() => onRegionSelect(regionKey)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10 hover:border-white/20 hover:text-gray-200 transition-all cursor-pointer"
                    >
                      <Globe className="w-3 h-3" />
                      {countryData[regionKey].name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="h-64 rounded-lg overflow-hidden border border-white/10 bg-dark-surface-card relative">
              <WorldMap
                selectedCodes={selectedLocation?.codes || []}
                onCountryClick={(code) => {
                  if (COUNTRY_NAMES[code]) {
                    onCountryClick({ codes: [code], name: COUNTRY_NAMES[code], isRegion: false });
                  }
                }}
              />
              <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-[#0a0d0a] via-transparent to-transparent opacity-60" />
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Hardware & Performance */}
      {currentStep === 2 && (
        <div className="space-y-5 animate-fadeIn">
          {/* Seção 1: O que você vai fazer? */}
          <div className="space-y-3">
            <div>
              <Label className="text-gray-300 text-sm font-medium">O que você vai fazer?</Label>
              <p className="text-xs text-gray-500 mt-1">Selecione seu objetivo para recomendarmos o hardware ideal</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {[
                { id: 'cpu_only', label: 'Apenas CPU', icon: Server, tier: 'CPU', desc: 'Sem GPU', isCPU: true },
                { id: 'test', label: 'Experimentar', icon: Lightbulb, tier: 'Lento', desc: 'Testes rápidos' },
                { id: 'develop', label: 'Desenvolver', icon: Code, tier: 'Medio', desc: 'Dev diário' },
                { id: 'train', label: 'Treinar modelo', icon: Zap, tier: 'Rapido', desc: 'Fine-tuning' },
                { id: 'production', label: 'Produção', icon: Sparkles, tier: 'Ultra', desc: 'LLMs grandes' }
              ].map((useCase) => {
                const isSelected = selectedTier === useCase.tier;
                const UseCaseIcon = useCase.icon;
                return (
                  <button
                    key={useCase.id}
                    data-testid={`use-case-${useCase.id}`}
                    onClick={() => onSelectTier(useCase.tier)}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-brand-500/10 border-brand-500"
                        : "bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20"
                    }`}
                  >
                    <div className="flex flex-col items-center gap-2 text-center">
                      <div className={`w-8 h-8 rounded-md flex items-center justify-center ${
                        isSelected ? "bg-brand-500/20 text-brand-400" : "bg-white/5 text-gray-500"
                      }`}>
                        <UseCaseIcon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className={`text-xs font-medium ${isSelected ? "text-brand-400" : "text-gray-300"}`}>
                          {useCase.label}
                        </div>
                        <div className={`text-[10px] ${isSelected ? "text-gray-400" : "text-gray-500"}`}>
                          {useCase.desc}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Seção 2: Seleção de GPU */}
          {selectedTier && (
            <div className="space-y-3">
              <div>
                <Label className="text-gray-300 text-sm font-medium">Seleção de GPU</Label>
                <p className="text-xs text-gray-500 mt-1">Escolha uma das máquinas recomendadas</p>
              </div>

              {/* 3 máquinas recomendadas - Layout horizontal */}
              <div>
                {loadingMachines ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400 mr-2" />
                    <span className="text-sm text-gray-400">Buscando máquinas disponíveis...</span>
                  </div>
                ) : recommendedMachines.length > 0 ? (
                  <>
                    {/* Grid horizontal de 3 colunas */}
                    <div className="grid grid-cols-3 gap-3">
                      {recommendedMachines.map((machine, index) => {
                        const isSelected = selectedMachine?.id === machine.id;
                        const labelIcons = {
                          'Mais econômico': DollarSign,
                          'Melhor custo-benefício': TrendingUp,
                          'Mais rápido': Zap,
                        };
                        const LabelIcon = labelIcons[machine.label] || Star;
                        const isCenterCard = index === 1;

                        return (
                          <button
                            key={machine.id}
                            data-testid={`machine-${machine.id}`}
                            data-gpu-name={machine.gpu_name}
                            data-gpu-card="true"
                            data-selected={isSelected ? "true" : "false"}
                            onClick={() => {
                              setSelectedMachine(machine);
                              onSelectGPU(machine.gpu_name);
                              onSelectGPUCategory('any');
                            }}
                            className={`relative p-3 rounded-lg border text-center transition-all cursor-pointer flex flex-col items-center ${
                              isSelected
                                ? "bg-brand-500/10 border-brand-500 ring-2 ring-brand-500/30"
                                : isCenterCard
                                ? "bg-brand-500/5 border-brand-500/30 hover:bg-brand-500/10"
                                : "bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20"
                            }`}
                          >
                            {/* Badge no topo */}
                            <div className={`absolute -top-2.5 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap ${
                              isCenterCard ? "bg-brand-500 text-white" : "bg-white/10 text-gray-400"
                            }`}>
                              <LabelIcon className="w-3 h-3" />
                              {machine.label}
                            </div>

                            {/* GPU Icon */}
                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center mt-3 mb-2 ${
                              isSelected ? "bg-brand-500/20 text-brand-400" : "bg-white/5 text-gray-500"
                            }`}>
                              <Cpu className="w-5 h-5" />
                            </div>

                            {/* GPU Name */}
                            <span className={`text-sm font-semibold ${isSelected ? "text-brand-400" : "text-gray-200"}`}>
                              {machine.gpu_name}
                            </span>

                            {/* Specs */}
                            <div className="flex items-center justify-center gap-1 mt-1">
                              {machine.isCPU ? (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
                                  {machine.cpu_cores} vCPU
                                </span>
                              ) : (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                                  {machine.gpu_ram}GB VRAM
                                </span>
                              )}
                            </div>

                            {/* Location */}
                            <span className="text-[10px] text-gray-500 mt-1">
                              {machine.location}
                            </span>

                            {/* Price */}
                            <span className={`text-lg font-mono font-bold mt-2 ${
                              isCenterCard ? "text-brand-400" : "text-gray-200"
                            }`}>
                              ${machine.dph_total.toFixed(2)}/h
                            </span>

                            {/* Selection indicator */}
                            {isSelected && (
                              <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-brand-500 flex items-center justify-center">
                                <Check className="w-3 h-3 text-white" />
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <div className="text-center py-6 text-gray-500 text-sm">
                    <AlertCircle className="w-5 h-5 mx-auto mb-2 opacity-50" />
                    Nenhuma máquina encontrada para esta configuração
                  </div>
                )}

                {/* Botão expandir busca manual */}
                <button
                  onClick={() => setSelectionMode(selectionMode === 'manual' ? 'recommended' : 'manual')}
                  className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-all flex items-center justify-center gap-1.5"
                  data-testid="toggle-manual-selection"
                >
                  {selectionMode === 'manual' ? (
                    <>
                      <ChevronUp className="w-3.5 h-3.5" />
                      Ocultar opções avançadas
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-3.5 h-3.5" />
                      Ver mais opções
                    </>
                  )}
                </button>

                {/* Busca manual expandida (aparece abaixo) */}
                {selectionMode === 'manual' && (
                  <div className="pt-3 border-t border-white/10 space-y-3">
                    {/* Campo de busca */}
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                      <input
                        type="text"
                        placeholder="Buscar GPU (ex: RTX 4090, A100, H100...)"
                        className="w-full pl-10 pr-4 py-2.5 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all"
                        value={gpuSearchQuery}
                        onChange={(e) => setGpuSearchQuery(e.target.value)}
                        data-testid="gpu-search-input"
                      />
                    </div>

                    {/* Lista de GPUs filtradas */}
                    <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                      {filteredGPUs.length > 0 ? (
                        filteredGPUs.map((gpu) => {
                          const isSelected = selectedGPU === gpu.name;
                          return (
                            <button
                              key={gpu.name}
                              data-testid={`gpu-option-${gpu.name.toLowerCase().replace(/\s+/g, '-')}`}
                              onClick={() => {
                                onSelectGPU(gpu.name);
                                setSelectedMachine(null);
                              }}
                              className={`w-full p-2.5 rounded-lg border text-left transition-all cursor-pointer flex items-center justify-between ${
                                isSelected
                                  ? "bg-brand-500/10 border-brand-500"
                                  : "bg-white/[0.02] border-white/10 hover:bg-white/5 hover:border-white/20"
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                <div className={`w-7 h-7 rounded flex items-center justify-center ${
                                  isSelected ? "bg-brand-500/20 text-brand-400" : "bg-white/5 text-gray-500"
                                }`}>
                                  <Cpu className="w-3.5 h-3.5" />
                                </div>
                                <div>
                                  <span className={`text-sm font-medium ${isSelected ? "text-brand-400" : "text-gray-200"}`}>
                                    {gpu.name}
                                  </span>
                                  <span className="text-[10px] text-gray-500 ml-2">{gpu.vram}</span>
                                </div>
                              </div>
                              <span className="text-xs text-gray-500">{gpu.priceRange}</span>
                            </button>
                          );
                        })
                      ) : (
                        <div className="text-center py-4 text-gray-500 text-xs">
                          Nenhuma GPU encontrada para "{gpuSearchQuery}"
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}


        </div>
      )}

      {/* Step 3: Estratégia de Failover */}
      {currentStep === 3 && (
        <div className="space-y-5 animate-fadeIn">
          <div>
            <div className="flex items-center gap-2">
              <Label className="text-gray-300 text-sm font-medium">Estratégia de Failover (V6)</Label>
              <Tooltip text="Recuperação automática em caso de falha da GPU">
                <HelpCircle className="w-3.5 h-3.5 text-gray-500 hover:text-gray-400 cursor-help" />
              </Tooltip>
            </div>
            <p className="text-xs text-gray-500 mt-1">Como recuperar automaticamente se a máquina falhar?</p>
          </div>


          <div className="space-y-3">
            {failoverOptions.map((option) => {
              const isSelected = failoverStrategy === option.id;
              const OptionIcon = option.icon;
              const isDisabled = option.comingSoon;
              return (
                <button
                  key={option.id}
                  data-testid={`failover-option-${option.id}`}
                  onClick={() => !isDisabled && setFailoverStrategy(option.id)}
                  disabled={isDisabled}
                  className={`w-full p-4 rounded-lg border text-left transition-all ${
                    isDisabled
                      ? "bg-white/[0.02] border-white/5 cursor-not-allowed opacity-60"
                      : isSelected && option.danger
                        ? "bg-red-500/10 border-red-500"
                        : isSelected
                        ? "bg-brand-500/10 border-brand-500"
                        : option.danger
                        ? "bg-white/5 border-white/10 hover:bg-red-500/5 hover:border-red-500/30"
                        : "bg-white/5 border-white/10 hover:bg-white/[0.07] hover:border-white/20"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isDisabled ? "bg-white/5 text-gray-600" : isSelected ? "bg-white/20 text-white" : "bg-white/5 text-gray-500"
                    }`}>
                      <OptionIcon className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className={`text-sm font-medium ${isDisabled ? "text-gray-500" : isSelected ? "text-gray-100" : "text-gray-300"}`}>
                          {option.name}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                          {option.provider}
                        </span>
                        {option.recommended && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                            Recomendado
                          </span>
                        )}
                        {option.danger && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 animate-pulse">
                            ⚠️ Risco
                          </span>
                        )}
                        {option.comingSoon && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
                            Em breve
                          </span>
                        )}
                      </div>
                      <p className={`text-xs mb-3 ${isDisabled ? "text-gray-600" : "text-gray-400"}`}>{option.description}</p>

                      {/* Features list */}
                      {option.features && (
                        <div className="grid grid-cols-2 gap-1 mb-3">
                          {option.features.map((feature, idx) => (
                            <div key={idx} className="flex items-center gap-1.5 text-[10px]">
                              <Check className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                              <span className={isDisabled ? "text-gray-600" : "text-gray-400"}>{feature}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Métricas em grid */}
                      <div className="grid grid-cols-3 gap-2 text-[10px]">
                        <div className="flex items-center gap-1">
                          <Timer className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                          <span className={isDisabled ? "text-gray-600" : "text-gray-500"}>Recovery:</span>
                          <span className={`font-medium ${isDisabled ? "text-gray-600" : isSelected ? 'text-gray-200' : 'text-gray-400'}`}>
                            {option.recoveryTime}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <HardDrive className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                          <span className={isDisabled ? "text-gray-600" : "text-gray-500"}>Perda:</span>
                          <span className={`font-medium ${isDisabled ? "text-gray-600" : option.dataLoss === 'Zero' ? 'text-emerald-400' : 'text-gray-400'}`}>
                            {option.dataLoss}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <DollarSign className={`w-3 h-3 ${isDisabled ? "text-gray-600" : "text-gray-500"}`} />
                          <span className={isDisabled ? "text-gray-600" : "text-gray-500"}>Custo:</span>
                          <span className={`font-medium ${isDisabled ? "text-gray-600" : isSelected ? 'text-gray-200' : 'text-gray-400'}`}>
                            {option.costHour}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                      isDisabled ? "border-white/10" : isSelected ? "border-white/40 bg-white/20" : "border-white/20"
                    }`}>
                      {isSelected && !isDisabled && <div className="w-2 h-2 rounded-full bg-white" />}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Detalhes da estratégia selecionada */}
          {selectedFailover && (
            <div className="p-4 rounded-lg bg-white/5 border border-white/10 space-y-3">
              <h4 className="text-xs font-medium text-gray-300">Como funciona</h4>
              <p className="text-xs text-gray-400">{selectedFailover.howItWorks}</p>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500">Requisitos:</span>
                <span className="text-gray-400">{selectedFailover.requirements}</span>
              </div>

              <div className="pt-3 border-t border-white/10">
                <h4 className="text-xs font-medium text-gray-400 mb-2">Resumo da configuração</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Região</span>
                    <span className="text-gray-300">{selectedLocation?.name || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Performance</span>
                    <span className="text-gray-300">{selectedTier || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Failover</span>
                    <span className="text-gray-300">{selectedFailover.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Custo extra</span>
                    <span className="text-gray-300">{selectedFailover.costHour}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Configurações Avançadas */}
          {failoverStrategy && (
            <div className="space-y-2">
              {/* Botão para expandir/recolher */}
              <button
                onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-all flex items-center justify-center gap-1.5"
                data-testid="toggle-advanced-settings"
              >
                <Settings className="w-3.5 h-3.5" />
                {showAdvancedSettings ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" />
                    Ocultar configurações avançadas
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" />
                    Configurações avançadas
                  </>
                )}
              </button>

              {/* Conteúdo das configurações avançadas */}
              {showAdvancedSettings && (
                <div className="pt-3 border-t border-white/10 space-y-4 animate-fadeIn">
                  {/* Docker Image / Template */}
                  <div className="space-y-2">
                    <Label className="text-gray-300 text-xs font-medium flex items-center gap-1.5">
                      <Code className="w-3.5 h-3.5" />
                      Template Docker
                    </Label>
                    <input
                      type="text"
                      value={dockerImage}
                      onChange={(e) => setDockerImage(e.target.value)}
                      placeholder="pytorch/pytorch:latest"
                      className="w-full px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all font-mono"
                      data-testid="docker-image-input"
                    />
                    <p className="text-[10px] text-gray-500">Imagem Docker que será usada na máquina</p>
                  </div>

                  {/* Exposed Ports */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-gray-300 text-xs font-medium flex items-center gap-1.5">
                        <Network className="w-3.5 h-3.5" />
                        Portas Expostas
                      </Label>
                      <button
                        onClick={() => setExposedPorts([...exposedPorts, { port: '', protocol: 'TCP' }])}
                        className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 transition-all"
                        data-testid="add-port-button"
                      >
                        <Plus className="w-3 h-3" />
                        Adicionar porta
                      </button>
                    </div>

                    <div className="space-y-2">
                      {exposedPorts.map((portConfig, index) => (
                        <div key={index} className="flex items-center gap-2">
                          {/* Port number input */}
                          <input
                            type="text"
                            value={portConfig.port}
                            onChange={(e) => {
                              const newPorts = [...exposedPorts];
                              newPorts[index].port = e.target.value;
                              setExposedPorts(newPorts);
                            }}
                            placeholder="8080"
                            className="flex-1 px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 placeholder:text-gray-500 transition-all font-mono"
                            data-testid={`port-input-${index}`}
                          />

                          {/* Protocol selector */}
                          <select
                            value={portConfig.protocol}
                            onChange={(e) => {
                              const newPorts = [...exposedPorts];
                              newPorts[index].protocol = e.target.value;
                              setExposedPorts(newPorts);
                            }}
                            className="px-3 py-2 text-sm text-gray-200 bg-white/5 border border-white/10 rounded-lg focus:ring-1 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all font-mono"
                            data-testid={`protocol-select-${index}`}
                          >
                            <option value="TCP">TCP</option>
                            <option value="UDP">UDP</option>
                          </select>

                          {/* Remove button */}
                          {exposedPorts.length > 1 && (
                            <button
                              onClick={() => {
                                const newPorts = exposedPorts.filter((_, i) => i !== index);
                                setExposedPorts(newPorts);
                              }}
                              className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all"
                              data-testid={`remove-port-${index}`}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <p className="text-[10px] text-gray-500">Portas que estarão disponíveis para acesso externo. Escolha TCP ou UDP para cada porta.</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Step 4: Provisioning */}
      {currentStep === 4 && (
        <div className="space-y-5 animate-fadeIn">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-500/10 border border-brand-500/30 mb-4">
              {provisioningWinner ? (
                <Check className="w-7 h-7 text-brand-400" />
              ) : (
                <Loader2 className="w-7 h-7 text-brand-400 animate-spin" />
              )}
            </div>
            <h3 className="text-lg font-semibold text-gray-100 mb-1">
              {provisioningWinner ? 'Máquina Conectada!' : 'Provisionando Máquinas...'}
            </h3>
            <p className="text-xs text-gray-400">
              {provisioningWinner
                ? 'Sua máquina está pronta para uso'
                : `Testando ${provisioningCandidates.length} máquinas simultaneamente. A primeira a responder será selecionada.`}
            </p>

            {/* Round indicator and Timer */}
            {!provisioningWinner && provisioningCandidates.length > 0 && (
              <div className="flex items-center justify-center gap-3 mt-3 text-xs flex-wrap">
                {/* Round indicator */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/30">
                  <Rocket className="w-3.5 h-3.5 text-purple-400" />
                  <span data-testid="wizard-round-indicator" className="text-purple-400 font-medium">Round {currentRound}/{maxRounds}</span>
                </div>
                {/* Timer */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span data-testid="wizard-timer" className="text-gray-300 font-mono">{formatTime(elapsedTime)}</span>
                </div>
                {/* ETA */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/30">
                  <Timer className="w-3.5 h-3.5 text-brand-400" />
                  <span className="text-brand-400">{getETA()}</span>
                </div>
              </div>
            )}
          </div>

          {/* Race Track - Grid layout for compact display */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
            {provisioningCandidates.map((candidate, index) => {
              const isWinner = provisioningWinner?.id === candidate.id;
              const isCancelled = provisioningWinner && !isWinner;
              const status = candidate.status;

              return (
                <div
                  key={candidate.id}
                  data-testid={`provisioning-candidate-${index}`}
                  className={`relative overflow-hidden rounded-lg border transition-all ${
                    isWinner
                      ? 'border-brand-500 bg-brand-500/10'
                      : isCancelled
                      ? 'border-white/5 bg-white/[0.02] opacity-50'
                      : status === 'failed'
                      ? 'border-red-500/30 bg-red-500/5'
                      : 'border-white/10 bg-white/5'
                  }`}
                >
                  {/* Progress bar for connecting state */}
                  {status === 'connecting' && !provisioningWinner && (
                    <div
                      className="absolute bottom-0 left-0 h-0.5 bg-brand-500 transition-all duration-300 ease-out"
                      style={{ width: `${candidate.progress || 0}%` }}
                    />
                  )}

                  <div className="p-3 flex items-center gap-3">
                    {/* Position/Status Icon */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center font-bold text-sm ${
                      isWinner
                        ? 'bg-brand-500/20 text-brand-400'
                        : isCancelled
                        ? 'bg-white/5 text-gray-600'
                        : status === 'failed'
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-white/5 text-gray-400'
                    }`}>
                      {isWinner ? (
                        <Check className="w-4 h-4" />
                      ) : isCancelled ? (
                        <X className="w-4 h-4" />
                      ) : status === 'failed' ? (
                        <X className="w-4 h-4" />
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>

                    {/* Machine Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Cpu className={`w-3.5 h-3.5 ${isWinner ? 'text-brand-400' : 'text-gray-500'}`} />
                        <span className={`text-sm font-medium truncate ${isWinner ? 'text-gray-100' : 'text-gray-300'}`}>
                          {candidate.gpu_name}
                        </span>
                        {candidate.num_gpus > 1 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-gray-400">
                            x{candidate.num_gpus}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-500">
                        <span>{candidate.gpu_ram?.toFixed(0)}GB</span>
                        <span>•</span>
                        <span>{candidate.geolocation || candidate.location || 'Unknown'}</span>
                        <span>•</span>
                        <span className="text-brand-400 font-medium">${candidate.dph_total?.toFixed(2)}/h</span>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className="flex-shrink-0">
                      {isWinner ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-brand-500/20 text-brand-400 text-[10px] font-medium">
                          <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                          Conectado
                        </span>
                      ) : isCancelled ? (
                        <span className="text-[10px] text-gray-600">Cancelado</span>
                      ) : status === 'failed' ? (
                        <div className="flex flex-col items-end">
                          <span className="text-[10px] text-red-400">Falhou</span>
                          {candidate.errorMessage && (
                            <span className="text-[9px] text-red-400/70">{candidate.errorMessage}</span>
                          )}
                        </div>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-400">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          {candidate.statusMessage || 'Conectando...'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary when winner is selected */}
          {provisioningWinner && (
            <div className="p-4 rounded-lg bg-brand-500/5 border border-brand-500/20">
              <h4 className="text-xs font-medium text-brand-400 mb-3">Resumo da Instância</h4>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">GPU</span>
                  <span className="text-gray-200">{provisioningWinner.gpu_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">VRAM</span>
                  <span className="text-gray-200">{provisioningWinner.gpu_ram?.toFixed(0)}GB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Localização</span>
                  <span className="text-gray-200">{provisioningWinner.geolocation || provisioningWinner.location}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Custo</span>
                  <span className="text-brand-400 font-medium">${provisioningWinner.dph_total?.toFixed(2)}/h</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Failover</span>
                  <span className="text-gray-200">{selectedFailover?.name || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Custo extra</span>
                  <span className="text-gray-200">{selectedFailover?.costHour || '-'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-4 border-t border-white/10">
        {/* Left button: Voltar or Cancelar */}
        {currentStep === 4 ? (
          <Button
            onClick={() => {
              if (onCancelProvisioning) onCancelProvisioning();
              setCurrentStep(3);
            }}
            variant="ghost"
            className="px-4 py-2 text-gray-400 hover:text-gray-200"
          >
            <X className="w-4 h-4 mr-1" />
            {provisioningWinner ? 'Buscar Outras' : 'Cancelar'}
          </Button>
        ) : currentStep > 1 ? (
          <Button
            onClick={handlePrev}
            variant="ghost"
            className="px-4 py-2 text-gray-400 hover:text-gray-200"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Voltar
          </Button>
        ) : (
          <div></div>
        )}

        {/* Right button: Próximo, Iniciar, or Usar Esta Máquina */}
        {currentStep === 4 ? (
          <button
            onClick={() => provisioningWinner && onCompleteProvisioning && onCompleteProvisioning(provisioningWinner)}
            disabled={!provisioningWinner}
            className="ta-btn ta-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="flex items-center gap-2">
              {provisioningWinner ? (
                <>
                  <Check className="w-4 h-4" />
                  Usar Esta Máquina
                </>
              ) : (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Conectando...
                </>
              )}
            </span>
          </button>
        ) : currentStep < 3 ? (
          <button
            onClick={handleNext}
            disabled={!isStepComplete(currentStep)}
            className="ta-btn ta-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="flex items-center gap-2">
              Próximo
              <ChevronRight className="w-4 h-4" />
            </span>
          </button>
        ) : (
          <button
            onClick={handleNext}
            disabled={!isStepComplete(currentStep) || loading}
            className="ta-btn ta-btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="flex items-center gap-2">
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Iniciando...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Iniciar
                </>
              )}
            </span>
          </button>
        )}
      </div>
    </CardContent>
  );
};

export default WizardForm;

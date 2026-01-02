import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import OnboardingWizard from '../components/onboarding/OnboardingWizard';
import {
  Cpu, Server, Wifi, DollarSign, Shield, HardDrive,
  Activity, Search, RotateCcw, Sliders, Wand2,
  Gauge, Globe, Zap, Monitor, ChevronDown, ChevronLeft, ChevronRight, Sparkles,
  Send, Bot, User, Loader2, Plus, Minus, X, Check, MapPin,
  MessageSquare, Lightbulb, Code, Clock
} from 'lucide-react';

// Dashboard Components
import {
  WorldMap,
  GPUSelector,
  GPUWizardDisplay,
  GPURecommendationCard,
  GPUCarousel,
  TierCard,
  SpeedBars,
  OfferCard,
  FilterSection,
  ProvisioningRaceScreen,
  AdvancedSearchForm,
  WizardForm,
  GPU_OPTIONS,
  GPU_CATEGORIES,
  REGION_OPTIONS,
  CUDA_OPTIONS,
  ORDER_OPTIONS,
  RENTAL_TYPE_OPTIONS,
  PERFORMANCE_TIERS,
  COUNTRY_DATA,
  COUNTRY_NAMES,
  DEMO_OFFERS,
  DEFAULT_FILTERS,
} from '../components/dashboard';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Input,
  Checkbox,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Button,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Label,
  Slider,
  Switch,
  StatCard as MetricCard,
  StatsGrid as MetricsGrid,
  Avatar,
  AvatarImage,
  AvatarFallback,
  Popover,
  PopoverTrigger,
  PopoverContent,
} from '../components/tailadmin-ui';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { SkeletonList } from '../components/Skeleton';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../components/Toast';
import { isDemoMode } from '../utils/api';
const API_BASE = import.meta.env.VITE_API_URL || '';

const regionToApiRegion = { 'EUA': 'US', 'Europa': 'EU', 'Asia': 'ASIA', 'AmericaDoSul': 'SA', 'Global': '' };

export default function Dashboard({ onStatsUpdate }) {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  // Determine base path for routing (demo vs real)
  const basePath = location.pathname.startsWith('/demo-app') ? '/demo-app' : '/app';
  const [user, setUser] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mode, setMode] = useState('wizard');
  const [provisioningMode, setProvisioningMode] = useState(false);
  const [raceCandidates, setRaceCandidates] = useState([]);
  const [raceWinner, setRaceWinner] = useState(null);

  // Migration mode - computed directly from location.state for immediate availability
  const migrationState = location.state?.wizardMode === 'migrate' ? location.state : null;
  const migrationMode = !!migrationState;
  const sourceMachine = migrationState?.sourceMachine || null;
  const targetType = migrationState?.targetType || null;
  const [dashboardStats, setDashboardStats] = useState({
    activeMachines: 0,
    totalMachines: 0,
    dailyCost: 0,
    savings: 0,
    uptime: 0
  });

  // Refs to track intervals and timeouts for cleanup
  const raceIntervalsRef = useRef([]);
  const raceTimeoutsRef = useRef([]);
  const createdInstanceIdsRef = useRef([]);
  const allOffersRef = useRef([]); // Store all offers for multi-round
  const currentRoundRef = useRef(1); // Track current round (max 3)
  const [currentRound, setCurrentRound] = useState(1);
  const MAX_ROUNDS = 3;

  useEffect(() => {
    checkOnboarding();
    fetchDashboardStats();
  }, []);

  // Handle migration mode - set wizard mode and clear navigation state
  useEffect(() => {
    if (migrationMode) {
      console.log('[Dashboard] Migration mode active:', { sourceMachine, targetType });
      setMode('wizard');
      // Pre-select location from source machine if available
      if (sourceMachine?.geolocation) {
        setSelectedLocation({
          codes: [sourceMachine.geolocation],
          name: sourceMachine.geolocation,
          isRegion: false
        });
      }
      // Clear the state to prevent re-triggering on refresh (after a small delay to ensure render)
      setTimeout(() => {
        window.history.replaceState({}, document.title);
      }, 100);
    }
  }, [migrationMode, sourceMachine, targetType]);

  // Cleanup on unmount - destroy any created instances
  useEffect(() => {
    return () => {
      raceIntervalsRef.current.forEach(clearInterval);
      raceTimeoutsRef.current.forEach(clearTimeout);
      raceIntervalsRef.current = [];
      raceTimeoutsRef.current = [];

      // Destroy any created instances if user navigates away during race
      if (createdInstanceIdsRef.current.length > 0) {
        createdInstanceIdsRef.current.forEach(async (created) => {
          try {
            await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
              method: 'DELETE',
              headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
            });
            console.log(`Destroyed instance ${created.instanceId} on unmount`);
          } catch (e) {
            console.error(`Failed to destroy instance ${created.instanceId} on unmount:`, e);
          }
        });
        createdInstanceIdsRef.current = [];
      }
    };
  }, []);

  const fetchDashboardStats = async () => {
    // Skip API call in demo mode - use demo stats directly
    const isDemoMode = localStorage.getItem('demo_mode') === 'true';
    if (isDemoMode) {
      const stats = {
        activeMachines: 2,
        totalMachines: 3,
        dailyCost: '4.80',
        savings: '127',
        uptime: 99.9,
        balance: '4.94'
      };
      setDashboardStats(stats);
      if (onStatsUpdate) onStatsUpdate(stats);
      return;
    }

    try {
      // Fetch instances and balance in parallel
      const [instancesRes, balanceRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/instances`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        }),
        fetch(`${API_BASE}/api/v1/balance`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        }).catch(() => null) // Balance is optional
      ]);

      // Parse balance response
      let balanceValue = '0.00';
      if (balanceRes?.ok) {
        try {
          const balanceData = await balanceRes.json();
          balanceValue = (balanceData.credit || balanceData.balance || 0).toFixed(2);
        } catch {
          // Keep default
        }
      }

      if (instancesRes.ok) {
        let data;
        try {
          const text = await instancesRes.text();
          data = text ? JSON.parse(text) : {};
        } catch {
          data = {};
        }
        const instances = data.instances || [];
        const running = instances.filter(i => i.status === 'running');
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0);

        const stats = {
          activeMachines: running.length,
          totalMachines: instances.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0), // 89% economia estimada
          uptime: running.length > 0 ? 99.9 : 0,
          balance: balanceValue
        };
        setDashboardStats(stats);
        if (onStatsUpdate) onStatsUpdate(stats);
      } else {
        // API failed, use demo mode fallback
        const stats = {
          activeMachines: 2,
          totalMachines: 3,
          dailyCost: '4.80',
          savings: '127',
          uptime: 99.9,
          balance: balanceValue
        };
        setDashboardStats(stats);
        if (onStatsUpdate) onStatsUpdate(stats);
      }
    } catch {
      // Demo mode fallback - silently use demo stats
      const stats = {
        activeMachines: 2,
        totalMachines: 3,
        dailyCost: '4.80',
        savings: '127',
        uptime: 99.9,
        balance: '0.00'
      };
      setDashboardStats(stats);
      if (onStatsUpdate) onStatsUpdate(stats);
    }
  };

  const checkOnboarding = async () => {
    try {
      // Check localStorage first for quick response
      const localOnboardingDone = localStorage.getItem('onboarding_completed');
      if (localOnboardingDone === 'true') {
        setShowOnboarding(false);
        return;
      }

      // Skip API call in demo mode
      const isDemoMode = localStorage.getItem('demo_mode') === 'true';
      if (isDemoMode) {
        setShowOnboarding(false);
        return;
      }

      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });

      // Handle non-OK responses gracefully
      if (!res.ok) {
        setShowOnboarding(false);
        return;
      }

      // Parse JSON safely
      let data;
      try {
        const text = await res.text();
        data = text ? JSON.parse(text) : {};
      } catch {
        setShowOnboarding(false);
        return;
      }

      if (data.authenticated) {
        setUser(data.user);
        // Verificar se o onboarding já foi completado
        const hasCompleted = data.user?.settings?.has_completed_onboarding;
        if (!hasCompleted) {
          setShowOnboarding(true);
        } else {
          // Sync localStorage with server state
          localStorage.setItem('onboarding_completed', 'true');
          setShowOnboarding(false);
        }
      }
    } catch {
      // Em caso de erro, não mostrar o onboarding (silently fail)
      setShowOnboarding(false);
    }
  };

  const handleCompleteOnboarding = async () => {
    try {
      // Mark as completed in localStorage immediately to prevent re-showing
      localStorage.setItem('onboarding_completed', 'true');
      setShowOnboarding(false);

      // Skip API call in demo mode
      const isDemoMode = localStorage.getItem('demo_mode') === 'true';
      if (isDemoMode) return;

      const res = await fetch(`${API_BASE}/api/v1/settings/complete-onboarding`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (res.ok) {
        // Atualizar o estado do usuário localmente
        setUser(prev => ({
          ...prev,
          settings: {
            ...prev?.settings,
            has_completed_onboarding: true
          }
        }));
      }
    } catch {
      // Silently fail - localStorage already updated
    }
  };
  const [activeTab, setActiveTab] = useState('Global');
  const [selectedTier, setSelectedTier] = useState(null);
  const [selectedGPU, setSelectedGPU] = useState('any');
  const [selectedGPUCategory, setSelectedGPUCategory] = useState('any');
  const [searchCountry, setSearchCountry] = useState('');
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showResults, setShowResults] = useState(false);

  // Filtros avançados completos do Vast.ai - Organizados por categoria
  const [advancedFilters, setAdvancedFilters] = useState({
    // GPU
    gpu_name: 'any',
    num_gpus: 1,
    min_gpu_ram: 0,
    gpu_frac: 1,
    gpu_mem_bw: 0,
    gpu_max_power: 0,
    bw_nvlink: 0,
    // CPU & Memória & Armazenamento
    min_cpu_cores: 1,
    min_cpu_ram: 1,
    min_disk: 50,
    cpu_ghz: 0,
    // Performance
    min_dlperf: 0,
    min_pcie_bw: 0,
    total_flops: 0,
    cuda_vers: 'any',
    compute_cap: 0,
    // Rede
    min_inet_down: 100,
    min_inet_up: 50,
    direct_port_count: 0,
    // Preço
    max_price: 5.0,
    rental_type: 'on-demand',
    // Qualidade & Localização
    min_reliability: 0,
    region: 'any',
    verified_only: false,
    datacenter: false,
    // Opções avançadas
    static_ip: false,
    // Ordenação
    order_by: 'dph_total',
    limit: 100
  });

  const tabs = ['EUA', 'Europa', 'Ásia', 'América do Sul', 'Global'];
  const tabIds = ['EUA', 'Europa', 'Asia', 'AmericaDoSul', 'Global'];

  // Country to ISO code and region mapping
  const countryData = {
    // Regiões (selecionam múltiplos países)
    'eua': { codes: ['US', 'CA', 'MX'], name: 'EUA', isRegion: true },
    'europa': { codes: ['GB', 'FR', 'DE', 'ES', 'IT', 'PT', 'NL', 'BE', 'CH', 'AT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'GR', 'HU', 'RO'], name: 'Europa', isRegion: true },
    'asia': { codes: ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW'], name: 'Ásia', isRegion: true },
    'america do sul': { codes: ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'], name: 'América do Sul', isRegion: true },

    // Países individuais - EUA/América do Norte
    'estados unidos': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'usa': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'united states': { codes: ['US'], name: 'Estados Unidos', isRegion: false },
    'canada': { codes: ['CA'], name: 'Canadá', isRegion: false },
    'canadá': { codes: ['CA'], name: 'Canadá', isRegion: false },
    'mexico': { codes: ['MX'], name: 'México', isRegion: false },
    'méxico': { codes: ['MX'], name: 'México', isRegion: false },

    // Países individuais - Europa
    'reino unido': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'uk': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'inglaterra': { codes: ['GB'], name: 'Reino Unido', isRegion: false },
    'franca': { codes: ['FR'], name: 'França', isRegion: false },
    'frança': { codes: ['FR'], name: 'França', isRegion: false },
    'france': { codes: ['FR'], name: 'França', isRegion: false },
    'alemanha': { codes: ['DE'], name: 'Alemanha', isRegion: false },
    'germany': { codes: ['DE'], name: 'Alemanha', isRegion: false },
    'espanha': { codes: ['ES'], name: 'Espanha', isRegion: false },
    'spain': { codes: ['ES'], name: 'Espanha', isRegion: false },
    'italia': { codes: ['IT'], name: 'Itália', isRegion: false },
    'itália': { codes: ['IT'], name: 'Itália', isRegion: false },
    'italy': { codes: ['IT'], name: 'Itália', isRegion: false },
    'portugal': { codes: ['PT'], name: 'Portugal', isRegion: false },
    'holanda': { codes: ['NL'], name: 'Holanda', isRegion: false },
    'netherlands': { codes: ['NL'], name: 'Holanda', isRegion: false },
    'belgica': { codes: ['BE'], name: 'Bélgica', isRegion: false },
    'bélgica': { codes: ['BE'], name: 'Bélgica', isRegion: false },
    'suica': { codes: ['CH'], name: 'Suíça', isRegion: false },
    'suíça': { codes: ['CH'], name: 'Suíça', isRegion: false },
    'austria': { codes: ['AT'], name: 'Áustria', isRegion: false },
    'áustria': { codes: ['AT'], name: 'Áustria', isRegion: false },
    'irlanda': { codes: ['IE'], name: 'Irlanda', isRegion: false },
    'suecia': { codes: ['SE'], name: 'Suécia', isRegion: false },
    'suécia': { codes: ['SE'], name: 'Suécia', isRegion: false },
    'noruega': { codes: ['NO'], name: 'Noruega', isRegion: false },
    'dinamarca': { codes: ['DK'], name: 'Dinamarca', isRegion: false },
    'finlandia': { codes: ['FI'], name: 'Finlândia', isRegion: false },
    'finlândia': { codes: ['FI'], name: 'Finlândia', isRegion: false },
    'polonia': { codes: ['PL'], name: 'Polônia', isRegion: false },
    'polônia': { codes: ['PL'], name: 'Polônia', isRegion: false },

    // Países individuais - Ásia
    'japao': { codes: ['JP'], name: 'Japão', isRegion: false },
    'japão': { codes: ['JP'], name: 'Japão', isRegion: false },
    'japan': { codes: ['JP'], name: 'Japão', isRegion: false },
    'china': { codes: ['CN'], name: 'China', isRegion: false },
    'coreia': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'coréia': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'korea': { codes: ['KR'], name: 'Coreia do Sul', isRegion: false },
    'singapore': { codes: ['SG'], name: 'Singapura', isRegion: false },
    'singapura': { codes: ['SG'], name: 'Singapura', isRegion: false },
    'india': { codes: ['IN'], name: 'Índia', isRegion: false },
    'índia': { codes: ['IN'], name: 'Índia', isRegion: false },
    'tailandia': { codes: ['TH'], name: 'Tailândia', isRegion: false },
    'tailândia': { codes: ['TH'], name: 'Tailândia', isRegion: false },
    'vietnam': { codes: ['VN'], name: 'Vietnã', isRegion: false },
    'vietnã': { codes: ['VN'], name: 'Vietnã', isRegion: false },
    'indonesia': { codes: ['ID'], name: 'Indonésia', isRegion: false },
    'indonésia': { codes: ['ID'], name: 'Indonésia', isRegion: false },
    'malasia': { codes: ['MY'], name: 'Malásia', isRegion: false },
    'malásia': { codes: ['MY'], name: 'Malásia', isRegion: false },
    'filipinas': { codes: ['PH'], name: 'Filipinas', isRegion: false },
    'taiwan': { codes: ['TW'], name: 'Taiwan', isRegion: false },

    // Países individuais - América do Sul
    'brasil': { codes: ['BR'], name: 'Brasil', isRegion: false },
    'brazil': { codes: ['BR'], name: 'Brasil', isRegion: false },
    'argentina': { codes: ['AR'], name: 'Argentina', isRegion: false },
    'chile': { codes: ['CL'], name: 'Chile', isRegion: false },
    'colombia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
    'colômbia': { codes: ['CO'], name: 'Colômbia', isRegion: false },
    'peru': { codes: ['PE'], name: 'Peru', isRegion: false },
    'venezuela': { codes: ['VE'], name: 'Venezuela', isRegion: false },
    'equador': { codes: ['EC'], name: 'Equador', isRegion: false },
    'uruguai': { codes: ['UY'], name: 'Uruguai', isRegion: false },
    'paraguai': { codes: ['PY'], name: 'Paraguai', isRegion: false },
    'bolivia': { codes: ['BO'], name: 'Bolívia', isRegion: false },
    'bolívia': { codes: ['BO'], name: 'Bolívia', isRegion: false },
  };

  // State for selected location (can be country or region)
  const [selectedLocation, setSelectedLocation] = useState(null); // { codes: [], name: '', isRegion: bool }

  // Function to find location data from search query
  const findLocationFromSearch = (query) => {
    if (!query || query.length < 2) return null;
    const normalizedQuery = query.toLowerCase().trim();

    // Check exact match first
    if (countryData[normalizedQuery]) {
      return countryData[normalizedQuery];
    }

    // Check partial match
    for (const [key, data] of Object.entries(countryData)) {
      if (key.includes(normalizedQuery) || normalizedQuery.includes(key)) {
        return data;
      }
    }
    return null;
  };

  // Handle search input change with auto-selection
  const handleSearchChange = (value) => {
    setSearchCountry(value);
    const foundLocation = findLocationFromSearch(value);
    if (foundLocation) {
      setSelectedLocation(foundLocation);
    }
  };

  // Handle region button click
  const handleRegionSelect = (regionKey) => {
    const regionData = countryData[regionKey];
    if (regionData) {
      setSelectedLocation(regionData);
      setSearchCountry('');
    }
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedLocation(null);
    setSearchCountry('');
  };

  // Use imported PERFORMANCE_TIERS from constants
  const tiers = PERFORMANCE_TIERS;

  const getToken = () => localStorage.getItem('auth_token');

  // DEMO_OFFERS imported from constants

  const searchOffers = async (filters) => {
    setLoading(true);
    setError(null);
    setShowResults(true);

    // In demo mode, use demo offers directly
    if (isDemoMode()) {
      await new Promise(r => setTimeout(r, 500)); // Simular delay
      setOffers(DEMO_OFFERS);
      toast.success(`${DEMO_OFFERS.length} máquinas encontradas!`);
      setLoading(false);
      return;
    }

    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });
      const response = await fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      });
      if (!response.ok) throw new Error(`Falha ao buscar ofertas (HTTP ${response.status})`);
      const data = await response.json();
      const realOffers = data.offers || [];

      // Show real offers only - no fallback to demo data
      if (realOffers.length === 0) {
        setOffers([]);
        toast.warning('Nenhuma máquina disponível. Verifique sua API Key VAST.ai.');
      } else {
        setOffers(realOffers);
        toast.success(`${realOffers.length} máquinas encontradas!`);
      }
    } catch (err) {
      // Show error - no fallback to demo data in real mode
      setOffers([]);
      setError(err.message);
      toast.error(`Erro ao buscar ofertas: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleWizardSearch = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      searchOffers({
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      });
    }
  };

  const handleAdvancedSearch = () => {
    const filters = { ...advancedFilters };
    if (filters.gpu_name === 'any') filters.gpu_name = '';
    if (filters.region === 'any') filters.region = '';
    if (filters.cuda_vers === 'any') filters.cuda_vers = '';
    searchOffers(filters);
  };

  const handleAdvancedFilterChange = (key, value) => {
    setAdvancedFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleSelectOffer = (offer) => {
    toast.success(`Máquina ${offer.gpu_name} selecionada!`);
    navigate(`${basePath}/machines`, { state: { selectedOffer: offer } });
  };

  // Start provisioning race with top 5 offers
  const startProvisioningRace = (selectedOffers) => {
    // Take top 5 offers (or less if not available)
    const top5 = selectedOffers.slice(0, 5).map((offer, index) => ({
      ...offer,
      status: 'connecting',
      progress: 0
    }));

    setRaceCandidates(top5);
    setRaceWinner(null);
    setProvisioningMode(true);

    // In demo mode, simulate the race
    if (isDemoMode()) {
      runDemoProvisioningRace(top5);
    } else {
      // Run REAL provisioning race (creates actual instances)
      runRealProvisioningRace(top5);
    }
  };

  // Demo provisioning race - Simulates REAL provisioning phases
  // Phases match real API: creating → connecting → loading → running
  const runDemoProvisioningRace = async (candidates) => {
    // Provisioning phases (same as real API)
    const PHASES = {
      creating: { name: 'creating', minProgress: 0, maxProgress: 15, statusText: 'Criando instância...' },
      connecting: { name: 'connecting', minProgress: 15, maxProgress: 40, statusText: 'Conectando ao host...' },
      loading: { name: 'loading', minProgress: 40, maxProgress: 85, statusText: 'Carregando ambiente...' },
      running: { name: 'running', minProgress: 85, maxProgress: 100, statusText: 'Finalizando...' },
    };

    // Calculate realistic timings for each machine based on specs
    const machineStates = candidates.map((c, index) => {
      // Base boot time: 15-30 seconds (realistic for GPU instances)
      const baseBootTime = 15000 + Math.random() * 15000;

      // Speed modifiers based on machine specs
      const inetModifier = Math.max(0.5, Math.min(1.5, (c.inet_down || 500) / 1000)); // Faster internet = faster
      const verifiedModifier = c.verified ? 0.8 : 1.2; // Verified = 20% faster
      const gpuModifier = (c.gpu_name?.includes('4090') || c.gpu_name?.includes('A100')) ? 0.9 : 1.0;

      // Total boot time for this machine
      const bootTime = baseBootTime * verifiedModifier * gpuModifier / inetModifier;

      // Failure probability based on real-world factors
      const failureChance = c.verified ? 0.05 : 0.20; // 5% verified, 20% unverified
      const willFail = Math.random() < failureChance;

      // Which phase will fail (if failing)
      const failPhases = ['creating', 'connecting', 'loading'];
      const failPhase = willFail ? failPhases[Math.floor(Math.random() * failPhases.length)] : null;

      // Failure reasons (realistic errors)
      const failureReasons = {
        creating: ['Máquina já alugada por outro usuário', 'Oferta expirada', 'Saldo insuficiente no host'],
        connecting: ['Timeout de conexão SSH', 'Host não responde', 'Porta bloqueada por firewall'],
        loading: ['Erro ao baixar imagem Docker', 'Disco cheio no host', 'Falha de inicialização CUDA'],
      };

      return {
        index,
        candidate: c,
        phase: 'creating',
        progress: 0,
        bootTime,
        startTime: Date.now(),
        willFail,
        failPhase,
        failureReason: failPhase ? failureReasons[failPhase][Math.floor(Math.random() * failureReasons[failPhase].length)] : null,
        status: 'creating',
        instanceId: `demo-${c.id}-${Date.now()}`, // Simulated instance ID
      };
    });

    // Update all machines to "creating" status initially
    setRaceCandidates(prev => prev.map((c, i) => ({
      ...c,
      status: 'creating',
      progress: 5,
      instanceId: machineStates[i].instanceId,
    })));

    let winnerFound = false;
    const pollInterval = 200; // Poll every 200ms (realistic)

    // Main race loop - simulates real polling behavior
    while (!winnerFound) {
      await new Promise(r => setTimeout(r, pollInterval));

      const now = Date.now();
      let allDone = true;

      // Update each machine's progress based on elapsed time
      machineStates.forEach((state, i) => {
        if (state.status === 'failed' || state.status === 'ready') return;

        allDone = false;
        const elapsed = now - state.startTime;
        const progressRatio = Math.min(elapsed / state.bootTime, 1.0);

        // Determine current phase based on progress
        let newPhase = 'creating';
        let newProgress = progressRatio * 100;

        if (progressRatio < 0.15) {
          newPhase = 'creating';
          newProgress = progressRatio * 100;
        } else if (progressRatio < 0.40) {
          newPhase = 'connecting';
          newProgress = 15 + ((progressRatio - 0.15) / 0.25) * 25;
        } else if (progressRatio < 0.85) {
          newPhase = 'loading';
          newProgress = 40 + ((progressRatio - 0.40) / 0.45) * 45;
        } else {
          newPhase = 'running';
          newProgress = 85 + ((progressRatio - 0.85) / 0.15) * 15;
        }

        // Check for failure in current phase
        if (state.willFail && state.failPhase === newPhase && newPhase !== state.phase) {
          state.status = 'failed';
          state.progress = newProgress;
        }
        // Check for completion
        else if (progressRatio >= 1.0) {
          state.status = 'ready';
          state.progress = 100;
          state.phase = 'running';
          if (!winnerFound) {
            winnerFound = true;
          }
        } else {
          state.phase = newPhase;
          state.progress = newProgress;
          state.status = newPhase;
        }
      });

      // Update UI
      setRaceCandidates(prev => prev.map((c, i) => {
        const state = machineStates[i];
        return {
          ...c,
          status: state.status,
          progress: Math.round(state.progress),
          instanceId: state.instanceId,
          errorMessage: state.status === 'failed' ? state.failureReason : undefined,
        };
      }));

      // Check if all machines are done (either ready or failed)
      const allCompleted = machineStates.every(s => s.status === 'failed' || s.status === 'ready');
      if (allCompleted) break;

      // Safety timeout (30 seconds max)
      const maxElapsed = Math.max(...machineStates.map(s => now - s.startTime));
      if (maxElapsed > 30000) break;
    }

    // Determine winner (first to reach ready)
    const winnerState = machineStates.find(s => s.status === 'ready');

    if (winnerState) {
      const winner = { ...winnerState.candidate, status: 'ready', progress: 100, instanceId: winnerState.instanceId };
      setRaceWinner(winner);

      // Calculate actual boot time for display
      const bootTimeSeconds = ((Date.now() - winnerState.startTime) / 1000).toFixed(1);
      toast.success(`🏆 ${winner.gpu_name} pronta em ${bootTimeSeconds}s!`);

      // Mark losers as destroyed (like real race)
      setTimeout(() => {
        setRaceCandidates(prev => prev.map((c, i) => {
          if (i === winnerState.index) return c;
          if (c.status === 'ready' || c.status === 'running') {
            return { ...c, status: 'destroyed', progress: 0 };
          }
          return c;
        }));
      }, 500);

      // Navigate after delay
      setTimeout(() => {
        setProvisioningMode(false);
        navigate(`${basePath}/machines`);
      }, 2500);
    } else {
      // All failed
      toast.error('Todas as máquinas falharam. Tente novamente com outras opções.');
      setTimeout(() => {
        setProvisioningMode(false);
      }, 2000);
    }
  };

  // REAL provisioning race with multi-round support
  const runRealProvisioningRaceWithMultiRound = async (candidates, allOffers, round) => {
    // Clear previous race intervals/timeouts
    raceIntervalsRef.current.forEach(clearInterval);
    raceTimeoutsRef.current.forEach(clearTimeout);
    raceIntervalsRef.current = [];
    raceTimeoutsRef.current = [];
    createdInstanceIdsRef.current = [];

    let winnerFound = false;
    let failedCount = 0;

    // Create all instances simultaneously
    const createPromises = candidates.map(async (candidate, index) => {
      try {
        // Update status to "creating"
        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = { ...updated[index], status: 'creating', progress: 10 };
          return updated;
        });

        // Create instance via API
        const res = await fetch(`${API_BASE}/api/v1/instances`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            offer_id: candidate.id,
            disk_size: candidate.disk_space || 20,
            label: `Race-R${round}-${candidate.gpu_name}-${Date.now()}`
          })
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || errorData.message || 'Failed to create instance');
        }

        const data = await res.json();
        const instanceId = data.id || data.instance_id;
        createdInstanceIdsRef.current.push({ index, instanceId, offerId: candidate.id });

        // Update with instance ID and status
        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = {
            ...updated[index],
            instanceId,
            status: 'connecting',
            progress: 30
          };
          return updated;
        });

        return { index, instanceId, success: true };
      } catch (error) {
        failedCount++;
        // Mark as failed with descriptive error message
        let errorMessage = 'Erro desconhecido';
        const errMsg = error.message?.toLowerCase() || '';
        if (errMsg.includes('balance') || errMsg.includes('insufficient') || errMsg.includes('funds')) {
          errorMessage = 'Saldo insuficiente';
        } else if (errMsg.includes('timeout')) {
          errorMessage = 'Timeout de conexão';
        } else if (errMsg.includes('unavailable') || errMsg.includes('not available') || errMsg.includes('already rented')) {
          errorMessage = 'Máquina indisponível';
        } else if (errMsg.includes('network')) {
          errorMessage = 'Erro de rede';
        } else if (errMsg.includes('auth') || errMsg.includes('401') || errMsg.includes('403') || errMsg.includes('unauthorized')) {
          errorMessage = 'Erro de autenticação';
        } else if (errMsg.includes('limit') || errMsg.includes('quota') || errMsg.includes('maximum')) {
          errorMessage = 'Limite de instâncias';
        } else if (errMsg.includes('api_key') || errMsg.includes('api key')) {
          errorMessage = 'API Key inválida';
        } else if (error.message && error.message.length < 40) {
          errorMessage = error.message;
        }

        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = { ...updated[index], status: 'failed', progress: 0, errorMessage };
          return updated;
        });

        return { index, success: false, error };
      }
    });

    // Wait for all creation attempts
    const results = await Promise.all(createPromises);

    // Count actual failures after all promises complete
    const totalFailed = results.filter(r => !r.success).length;
    console.log(`Round ${round}: ${totalFailed}/${candidates.length} failed`);

    // If all failed, try next round after a short delay
    if (totalFailed === candidates.length) {
      console.log(`All machines failed in round ${round}, checking for next round...`);
      toast.warning(`Todas as ${candidates.length} máquinas falharam. Tentando próximo grupo...`);

      setTimeout(() => {
        const hasMoreOffers = allOffers.length > round * 5;
        if (round < MAX_ROUNDS && hasMoreOffers) {
          const nextRound = round + 1;
          toast.info(`Iniciando round ${nextRound}/${MAX_ROUNDS}...`);
          startProvisioningRaceIntegrated(allOffers, nextRound);
        } else {
          toast.error('Todas as tentativas falharam. Verifique sua API Key e saldo.');
        }
      }, 1500);
      return;
    }

    // Poll for status updates every 3 seconds
    const pollInterval = setInterval(async () => {
      if (winnerFound) {
        clearInterval(pollInterval);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/v1/instances`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;

        const data = await res.json();
        const instances = data.instances || [];

        for (const created of createdInstanceIdsRef.current) {
          const instance = instances.find(i => i.id === created.instanceId);
          if (!instance) continue;

          const status = instance.actual_status;
          const candidateIndex = created.index;

          // Update with REAL status from API
          setRaceCandidates(prev => {
            const updated = [...prev];
            if (updated[candidateIndex] && updated[candidateIndex].status !== 'failed') {
              let progress = updated[candidateIndex].progress || 30;
              let statusMessage = 'Conectando...';
              let candidateStatus = 'connecting';

              // Map real API status to progress and message
              switch (status) {
                case 'created':
                  progress = 20;
                  statusMessage = 'Instância criada';
                  break;
                case 'loading':
                  progress = Math.min(progress + 10, 85);
                  statusMessage = 'Carregando ambiente...';
                  break;
                case 'running':
                  progress = 100;
                  statusMessage = 'Pronta!';
                  candidateStatus = 'connected';
                  break;
                case 'exited':
                case 'error':
                case 'destroyed':
                  progress = 0;
                  statusMessage = `Falhou: ${status}`;
                  candidateStatus = 'failed';
                  break;
                default:
                  statusMessage = status || 'Aguardando...';
              }

              updated[candidateIndex] = {
                ...updated[candidateIndex],
                progress,
                status: candidateStatus,
                statusMessage,
                actualStatus: status,
                sshHost: instance.ssh_host,
                sshPort: instance.ssh_port
              };
            }
            return updated;
          });

          // Check for failed states
          if ((status === 'exited' || status === 'error' || status === 'destroyed') && !winnerFound) {
            // Mark as failed but continue checking others
            continue;
          }

          if (status === 'running' && !winnerFound) {
            winnerFound = true;
            clearInterval(pollInterval);

            setRaceCandidates(prev => {
              return prev.map((c, i) => ({
                ...c,
                status: i === candidateIndex ? 'connected' : (c.status === 'failed' ? 'failed' : 'cancelled'),
                progress: i === candidateIndex ? 100 : c.progress
              }));
            });

            const winnerCandidate = candidates[candidateIndex];
            setRaceWinner({
              ...winnerCandidate,
              instanceId: created.instanceId,
              ssh_host: instance.ssh_host,
              ssh_port: instance.ssh_port,
              actual_status: 'running'
            });

            // Destroy losing instances
            for (const other of createdInstanceIdsRef.current) {
              if (other.instanceId !== created.instanceId) {
                try {
                  await fetch(`${API_BASE}/api/v1/instances/${other.instanceId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${getToken()}` }
                  });
                } catch (e) {
                  console.error(`Failed to destroy instance ${other.instanceId}:`, e);
                }
              }
            }

            createdInstanceIdsRef.current = [];
            toast.success(`🏆 ${winnerCandidate.gpu_name} venceu a corrida!`);
            break;
          }
        }

        // Check if all candidates failed
        setRaceCandidates(prev => {
          const allFailed = createdInstanceIdsRef.current.length > 0 &&
            createdInstanceIdsRef.current.every(created => {
              const candidate = prev[created.index];
              return candidate?.status === 'failed';
            });
          if (allFailed && !winnerFound) {
            clearInterval(pollInterval);
            // Will trigger next round via handleAllFailed logic
          }
          return prev;
        });
      } catch (error) {
        console.error('Error polling instance status:', error);
      }
    }, 3000);

    raceIntervalsRef.current.push(pollInterval);

    // Timeout after 3 minutes per round
    const raceTimeout = setTimeout(async () => {
      if (!winnerFound) {
        clearInterval(pollInterval);

        // Clean up created instances
        for (const created of createdInstanceIdsRef.current) {
          try {
            await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
              method: 'DELETE',
              headers: { 'Authorization': `Bearer ${getToken()}` }
            });
          } catch (e) {
            console.error(`Failed to cleanup instance ${created.instanceId}:`, e);
          }
        }
        createdInstanceIdsRef.current = [];

        // Mark all as failed due to timeout
        setRaceCandidates(prev => prev.map(c => ({
          ...c,
          status: c.status === 'failed' ? 'failed' : 'failed',
          errorMessage: c.errorMessage || 'Timeout'
        })));

        // Try next round
        const startedNextRound = checkAndStartNextRound(
          candidates.map(c => ({ ...c, status: 'failed' })),
          allOffers,
          round
        );

        if (!startedNextRound) {
          toast.error(`Tempo esgotado após ${MAX_ROUNDS} tentativas.`);
        }
      }
    }, 3 * 60 * 1000); // 3 minutes per round

    raceTimeoutsRef.current.push(raceTimeout);
  };

  // REAL provisioning race - creates actual instances and monitors which one starts first
  const runRealProvisioningRace = async (candidates) => {
    // Clear previous race intervals/timeouts
    raceIntervalsRef.current.forEach(clearInterval);
    raceTimeoutsRef.current.forEach(clearTimeout);
    raceIntervalsRef.current = [];
    raceTimeoutsRef.current = [];
    createdInstanceIdsRef.current = [];

    let winnerFound = false;

    // Create all instances simultaneously
    const createPromises = candidates.map(async (candidate, index) => {
      try {
        // Update status to "creating"
        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = { ...updated[index], status: 'creating', progress: 10 };
          return updated;
        });

        // Create instance via API
        const res = await fetch(`${API_BASE}/api/v1/instances`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            offer_id: candidate.id,
            disk_size: candidate.disk_space || 20,
            label: `Race-${candidate.gpu_name}-${Date.now()}`
          })
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          const apiError = errorData.detail || errorData.message || errorData.error || '';
          throw new Error(apiError || `Erro HTTP ${res.status}`);
        }

        const data = await res.json();
        const instanceId = data.id || data.instance_id;
        createdInstanceIdsRef.current.push({ index, instanceId, offerId: candidate.id });

        // Update with instance ID and status
        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = {
            ...updated[index],
            instanceId,
            status: 'connecting',
            progress: 30
          };
          return updated;
        });

        return { index, instanceId, success: true };
      } catch (error) {
        // Mark as failed with descriptive error message
        const msg = (error.message || '').toLowerCase();
        let errorMessage = 'Erro desconhecido';

        // Balance/Credit errors
        if (msg.includes('balance') || msg.includes('insufficient') || msg.includes('credit') || msg.includes('saldo')) {
          errorMessage = 'Saldo insuficiente';
        // Machine availability errors
        } else if (msg.includes('unavailable') || msg.includes('not available') || msg.includes('offer not found') || msg.includes('not found')) {
          errorMessage = 'Máquina indisponível';
        } else if (msg.includes('already rented') || msg.includes('busy') || msg.includes('in use')) {
          errorMessage = 'Já está alugada';
        // Connection/Network errors
        } else if (msg.includes('timeout') || msg.includes('timed out')) {
          errorMessage = 'Timeout de conexão';
        } else if (msg.includes('network') || msg.includes('connection') || msg.includes('connect')) {
          errorMessage = 'Erro de rede';
        // Authentication errors
        } else if (msg.includes('auth') || msg.includes('401') || msg.includes('403') || msg.includes('api key') || msg.includes('unauthorized') || msg.includes('forbidden')) {
          errorMessage = 'Erro de autenticação';
        // Limit errors
        } else if (msg.includes('limit') || msg.includes('quota') || msg.includes('exceeded')) {
          errorMessage = 'Limite de instâncias';
        // Disk/Storage errors
        } else if (msg.includes('disk') || msg.includes('storage') || msg.includes('space')) {
          errorMessage = 'Erro de disco';
        // SSH/Docker errors
        } else if (msg.includes('ssh') || msg.includes('docker') || msg.includes('container')) {
          errorMessage = 'Erro de inicialização';
        // HTTP status codes
        } else if (msg.includes('erro http') || msg.includes('500') || msg.includes('502') || msg.includes('503')) {
          errorMessage = 'Servidor indisponível';
        } else if (msg.includes('400') || msg.includes('bad request')) {
          errorMessage = 'Requisição inválida';
        } else if (error.message && error.message.length > 0) {
          // Use the actual message if it's short enough, otherwise truncate
          errorMessage = error.message.length <= 25 ? error.message : error.message.slice(0, 22) + '...';
        }

        setRaceCandidates(prev => {
          const updated = [...prev];
          updated[index] = { ...updated[index], status: 'failed', progress: 0, errorMessage };
          return updated;
        });
        return { index, success: false, error };
      }
    });

    // Wait for all creation attempts
    await Promise.all(createPromises);

    // Poll for status updates every 3 seconds
    const pollInterval = setInterval(async () => {
      if (winnerFound) {
        clearInterval(pollInterval);
        return;
      }

      try {
        // Fetch all instances to check status
        const res = await fetch(`${API_BASE}/api/v1/instances`, {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (!res.ok) return;

        const data = await res.json();
        const instances = data.instances || [];

        // Check each created instance
        for (const created of createdInstanceIdsRef.current) {
          const instance = instances.find(i => i.id === created.instanceId);
          if (!instance) continue;

          const status = instance.actual_status;
          const candidateIndex = created.index;

          // Update with REAL status from API
          setRaceCandidates(prev => {
            const updated = [...prev];
            if (updated[candidateIndex] && updated[candidateIndex].status !== 'failed') {
              let progress = updated[candidateIndex].progress || 30;
              let statusMessage = 'Conectando...';
              let candidateStatus = 'connecting';

              // Map real API status to progress and message
              switch (status) {
                case 'created':
                  progress = 20;
                  statusMessage = 'Instância criada';
                  break;
                case 'loading':
                  progress = Math.min(progress + 10, 85);
                  statusMessage = 'Carregando ambiente...';
                  break;
                case 'running':
                  progress = 100;
                  statusMessage = 'Pronta!';
                  candidateStatus = 'connected';
                  break;
                case 'exited':
                case 'error':
                case 'destroyed':
                  progress = 0;
                  statusMessage = `Falhou: ${status}`;
                  candidateStatus = 'failed';
                  break;
                default:
                  statusMessage = status || 'Aguardando...';
              }

              updated[candidateIndex] = {
                ...updated[candidateIndex],
                progress,
                status: candidateStatus,
                statusMessage,
                actualStatus: status,
                sshHost: instance.ssh_host,
                sshPort: instance.ssh_port
              };
            }
            return updated;
          });

          // Check if this one is running (WINNER!)
          if (status === 'running' && !winnerFound) {
            winnerFound = true;
            clearInterval(pollInterval);

            // Mark winner and cancel others
            setRaceCandidates(prev => {
              return prev.map((c, i) => ({
                ...c,
                status: i === candidateIndex ? 'connected' : (c.status === 'failed' ? 'failed' : 'cancelled'),
                progress: i === candidateIndex ? 100 : c.progress
              }));
            });

            // Set winner with full instance data
            const winnerCandidate = candidates[candidateIndex];
            setRaceWinner({
              ...winnerCandidate,
              instanceId: created.instanceId,
              ssh_host: instance.ssh_host,
              ssh_port: instance.ssh_port,
              actual_status: 'running'
            });

            // Destroy the losing instances to save money
            for (const other of createdInstanceIdsRef.current) {
              if (other.instanceId !== created.instanceId) {
                try {
                  await fetch(`${API_BASE}/api/v1/instances/${other.instanceId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${getToken()}` }
                  });
                  console.log(`Destroyed losing instance ${other.instanceId}`);
                } catch (e) {
                  console.error(`Failed to destroy instance ${other.instanceId}:`, e);
                }
              }
            }

            // Clear the ref after cleanup
            createdInstanceIdsRef.current = [];
            toast.success(`🏆 ${winnerCandidate.gpu_name} venceu a corrida!`);
            break;
          }
        }
      } catch (error) {
        console.error('Error polling instance status:', error);
      }
    }, 3000);

    raceIntervalsRef.current.push(pollInterval);

    // Timeout after 5 minutes - if no winner, pick the first one that's furthest along
    const raceTimeout = setTimeout(async () => {
      if (!winnerFound) {
        clearInterval(pollInterval);
        toast.error('Tempo esgotado. Nenhuma máquina inicializou a tempo.');

        // Clean up all created instances
        for (const created of createdInstanceIdsRef.current) {
          try {
            await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
              method: 'DELETE',
              headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            console.log(`Cleaned up instance ${created.instanceId} after timeout`);
          } catch (e) {
            console.error(`Failed to cleanup instance ${created.instanceId}:`, e);
          }
        }

        createdInstanceIdsRef.current = [];
        setProvisioningMode(false);
      }
    }, 5 * 60 * 1000); // 5 minutes

    raceTimeoutsRef.current.push(raceTimeout);
  };

  const cancelProvisioningRace = async () => {
    // Clean up all intervals and timeouts
    raceIntervalsRef.current.forEach(clearInterval);
    raceTimeoutsRef.current.forEach(clearTimeout);
    raceIntervalsRef.current = [];
    raceTimeoutsRef.current = [];

    // Destroy all created instances to save money
    if (createdInstanceIdsRef.current.length > 0) {
      toast.info('Cancelando e destruindo instâncias criadas...');

      for (const created of createdInstanceIdsRef.current) {
        try {
          await fetch(`${API_BASE}/api/v1/instances/${created.instanceId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
          });
          console.log(`Destroyed instance ${created.instanceId} on cancel`);
        } catch (e) {
          console.error(`Failed to destroy instance ${created.instanceId}:`, e);
        }
      }

      createdInstanceIdsRef.current = [];
      toast.success('Corrida cancelada. Instâncias destruídas.');
    }

    setProvisioningMode(false);
    setRaceCandidates([]);
    setRaceWinner(null);
  };

  const completeProvisioningRace = (winner) => {
    setProvisioningMode(false);
    // Toast já foi mostrado quando o vencedor foi encontrado
    navigate(`${basePath}/machines`, { state: { selectedOffer: winner } });
  };

  // Modified wizard search to start the race
  const handleWizardSearchWithRace = () => {
    const tier = tiers.find(t => t.name === selectedTier);
    if (tier) {
      setLoading(true);

      // Helper to filter DEMO_OFFERS by tier
      const filterDemoOffersByTier = (offers, tierFilter) => {
        return offers.filter(o => {
          if (tierFilter.max_price && o.dph_total > tierFilter.max_price) return false;
          if (tierFilter.min_gpu_ram && o.gpu_ram < tierFilter.min_gpu_ram) return false;
          return true;
        });
      };

      // Skip API call in demo mode - use demo offers directly
      if (isDemoMode()) {
        const filteredDemoOffers = filterDemoOffersByTier(DEMO_OFFERS, tier.filter);
        setOffers(filteredDemoOffers);
        setLoading(false);
        if (filteredDemoOffers.length > 0) {
          startProvisioningRace(filteredDemoOffers);
        } else {
          toast.error('Nenhuma máquina encontrada para este tier. Tente outro.');
        }
        return;
      }

      const params = new URLSearchParams();
      const filters = {
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      };
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });

      fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
        .then(res => res.json())
        .then(data => {
          const realOffers = data.offers || [];
          const filteredDemoOffers = filterDemoOffersByTier(DEMO_OFFERS, tier.filter);
          const offersToUse = realOffers.length > 0 ? realOffers : filteredDemoOffers;
          setOffers(offersToUse);
          setLoading(false);
          // Start the race with top offers
          if (offersToUse.length > 0) {
            startProvisioningRace(offersToUse);
          } else {
            toast.error('Nenhuma máquina encontrada para este tier. Tente outro.');
          }
        })
        .catch(() => {
          const filteredDemoOffers = filterDemoOffersByTier(DEMO_OFFERS, tier.filter);
          setOffers(filteredDemoOffers);
          setLoading(false);
          if (filteredDemoOffers.length > 0) {
            startProvisioningRace(filteredDemoOffers);
          } else {
            toast.error('Nenhuma máquina encontrada para este tier. Tente outro.');
          }
        });
    }
  };

  // Integrated wizard search - starts race within wizard (no overlay)
  const handleWizardSearchWithRaceIntegrated = () => {
    console.log('[WizardRace] selectedTier:', selectedTier);
    console.log('[WizardRace] tiers:', tiers.map(t => t.name));
    const tier = tiers.find(t => t.name === selectedTier);
    console.log('[WizardRace] found tier:', tier?.name);
    if (!tier) {
      console.error('[WizardRace] TIER NOT FOUND! selectedTier was:', selectedTier);
      toast.error('Tier não encontrado. Selecione uma opção.');
      return;
    }
    if (tier) {
      setLoading(true);

      // Helper to filter DEMO_OFFERS by tier
      const filterDemoOffersByTier = (offers, tierFilter) => {
        return offers.filter(o => {
          if (tierFilter.max_price && o.dph_total > tierFilter.max_price) return false;
          if (tierFilter.min_gpu_ram && o.gpu_ram < tierFilter.min_gpu_ram) return false;
          return true;
        });
      };

      // Skip API call in demo mode - use demo offers directly
      // Check both localStorage AND route (/demo-app)
      const isInDemoMode = localStorage.getItem('demo_mode') === 'true' || window.location.pathname.startsWith('/demo-app');
      console.log('[WizardRace] isInDemoMode:', isInDemoMode, 'path:', window.location.pathname);
      console.log('[WizardRace] DEMO_OFFERS count:', DEMO_OFFERS?.length);
      console.log('[WizardRace] tier.filter:', tier.filter);
      if (isInDemoMode) {
        const filteredDemoOffers = filterDemoOffersByTier(DEMO_OFFERS, tier.filter);
        console.log('[WizardRace] filteredDemoOffers count:', filteredDemoOffers.length);
        setOffers(filteredDemoOffers);
        setLoading(false);
        if (filteredDemoOffers.length > 0) {
          console.log('[WizardRace] Starting race with', filteredDemoOffers.length, 'offers');
          startProvisioningRaceIntegrated(filteredDemoOffers, true);
        } else {
          console.error('[WizardRace] No offers after filter!');
          toast.error('Nenhuma máquina encontrada para este tier. Tente outro.');
        }
        return;
      }

      const params = new URLSearchParams();
      const filters = {
        ...tier.filter,
        region: regionToApiRegion[activeTab] || '',
        gpu_name: selectedGPU === 'any' ? '' : selectedGPU
      };
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value);
        }
      });

      fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then(data => {
          const realOffers = data.offers || [];
          console.log('[WizardRace] API returned offers:', realOffers.length);
          setOffers(realOffers);
          setLoading(false);
          // Start the race with REAL offers only - no fallback to demo data
          if (realOffers.length > 0) {
            console.log('[WizardRace] Starting race with', realOffers.length, 'offers');
            startProvisioningRaceIntegrated(realOffers);
          } else {
            console.log('[WizardRace] No offers returned!');
            toast.error('Nenhuma máquina disponível no momento. Verifique sua API Key VAST.ai ou tente outro tier.');
          }
        })
        .catch((err) => {
          setOffers([]);
          setLoading(false);
          // Show error - no fallback to demo data in real mode
          toast.error(`Erro ao buscar ofertas: ${err.message}. Verifique sua conexão e API Key.`);
        });
    }
  };

  // Start provisioning race integrated into wizard (no overlay)
  const startProvisioningRaceIntegrated = (selectedOffers, isDemoRace = false, round = 1) => {
    // Store all offers for potential multi-round
    if (round === 1) {
      allOffersRef.current = selectedOffers;
      currentRoundRef.current = 1;
      setCurrentRound(1);
    }

    // Calculate which 5 offers to use for this round
    const startIndex = (round - 1) * 5;
    const endIndex = startIndex + 5;
    const roundOffers = selectedOffers.slice(startIndex, endIndex);

    if (roundOffers.length === 0) {
      toast.error('Não há mais máquinas disponíveis para tentar.');
      return;
    }

    const top5 = roundOffers.map((offer, index) => ({
      ...offer,
      status: 'connecting',
      progress: 0
    }));

    setRaceCandidates(top5);
    setRaceWinner(null);
    currentRoundRef.current = round;
    setCurrentRound(round);

    // DON'T set provisioningMode to true - wizard handles step 4 display
    // Check if demo mode - run simulated race
    if (isDemoRace || localStorage.getItem('demo_mode') === 'true') {
      runDemoProvisioningRace(top5);
    } else {
      // Run REAL provisioning race with multi-round support
      runRealProvisioningRaceWithMultiRound(top5, selectedOffers, round);
    }
  };

  // Check if all candidates failed and start next round
  const checkAndStartNextRound = (candidates, allOffers, currentRound) => {
    const allFailed = candidates.every(c => c.status === 'failed');
    if (allFailed && currentRound < MAX_ROUNDS) {
      const nextRound = currentRound + 1;
      const hasMoreOffers = allOffers.length > currentRound * 5;
      if (hasMoreOffers) {
        toast.info(`Todas as máquinas falharam. Tentando round ${nextRound}/${MAX_ROUNDS}...`);
        setTimeout(() => {
          startProvisioningRaceIntegrated(allOffers, nextRound);
        }, 1000);
        return true;
      }
    }
    return false;
  };

  const resetAdvancedFilters = () => {
    setAdvancedFilters({
      gpu_name: 'any', num_gpus: 1, min_gpu_ram: 0, gpu_frac: 1, gpu_mem_bw: 0, gpu_max_power: 0, bw_nvlink: 0,
      min_cpu_cores: 1, min_cpu_ram: 1, min_disk: 50, cpu_ghz: 0,
      min_dlperf: 0, min_pcie_bw: 0, total_flops: 0, cuda_vers: 'any', compute_cap: 0,
      min_inet_down: 100, min_inet_up: 50, direct_port_count: 0,
      max_price: 5.0, rental_type: 'on-demand',
      min_reliability: 0, region: 'any', verified_only: false, datacenter: false,
      static_ip: false, order_by: 'dph_total', limit: 100
    });
    toast.info('Filtros resetados');
  };

  return (
    <div className="min-h-screen">
      {showOnboarding && (
        <OnboardingWizard
          user={user}
          onClose={handleCompleteOnboarding}
          onComplete={handleCompleteOnboarding}
        />
      )}

      {/* NOTE: Provisioning Race Screen removed - now integrated into WizardForm step 4 */}

      {/* Deploy Wizard */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8">
        <Card>
          <CardHeader className="pb-6">
            {/* Header com título */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-brand-500" />
              </div>
              <div>
                <CardTitle className="text-lg">Nova Instância GPU</CardTitle>
                <CardDescription className="text-xs">Provisione sua máquina em minutos</CardDescription>
              </div>
            </div>

            {/* Seletor de Modo Compacto */}
            <div className="inline-flex items-center p-1 bg-white/5 rounded-lg border border-white/10">
              <button
                onClick={() => {
                  setMode('wizard');
                  setShowResults(false);
                }}
                data-testid="config-guided"
                className={`px-4 py-2 rounded-md text-xs font-medium transition-all ${
                  mode === 'wizard'
                    ? 'bg-brand-500 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`}
              >
                Guiado
              </button>
              <button
                onClick={() => {
                  setMode('advanced');
                  setShowResults(false);
                }}
                data-testid="config-advanced"
                className={`px-4 py-2 rounded-md text-xs font-medium transition-all ${
                  mode === 'advanced'
                    ? 'bg-brand-500 text-white shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`}
              >
                Avançado
              </button>
            </div>
          </CardHeader>

          {/* WIZARD MODE */}
          {mode === 'wizard' && !showResults && (
            <div id="wizard-form-section" className="animate-fadeIn">
              <WizardForm
                // Migration mode props
                migrationMode={migrationMode}
                sourceMachine={sourceMachine}
                targetType={targetType}
                initialStep={migrationMode ? 2 : 1}
                // Step 1: Location
                searchCountry={searchCountry}
                selectedLocation={selectedLocation}
                onSearchChange={handleSearchChange}
                onRegionSelect={handleRegionSelect}
                onClearSelection={() => setSelectedLocation(null)}
                // Step 2: Hardware
                selectedGPU={selectedGPU}
                onSelectGPU={setSelectedGPU}
                selectedGPUCategory={selectedGPUCategory}
                onSelectGPUCategory={setSelectedGPUCategory}
                selectedTier={selectedTier}
                onSelectTier={setSelectedTier}
                // Actions
                loading={loading}
                onSubmit={handleWizardSearchWithRaceIntegrated}
                // Provisioning (Step 4)
                provisioningCandidates={raceCandidates}
                provisioningWinner={raceWinner}
                isProvisioning={provisioningMode}
                onCancelProvisioning={cancelProvisioningRace}
                onCompleteProvisioning={completeProvisioningRace}
                currentRound={currentRound}
                maxRounds={3}
                WorldMapComponent={WorldMap}
              />
            </div>
          )}

          {/* ADVANCED MODE (MANUAL) */}
          {mode === 'advanced' && !showResults && (
            <div className="animate-fadeIn">
              <AdvancedSearchForm
                filters={advancedFilters}
                onFilterChange={handleAdvancedFilterChange}
                onReset={resetAdvancedFilters}
                onSearch={handleAdvancedSearch}
                onBackToWizard={() => setMode('wizard')}
                loading={loading}
              />
            </div>
          )}

          {/* RESULTS VIEW */}
          {showResults && (
            <CardContent className="pt-6 animate-slideInUp">
              <div className="flex flex-col gap-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-gray-900 dark:text-white text-lg font-semibold">Máquinas Disponíveis</h2>
                    <p className="text-gray-500 text-xs">{offers.length} resultados encontrados</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowResults(false)}
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Voltar
                  </Button>
                </div>

                {/* Sorting Controls */}
                {offers.length > 0 && (
                  <div className="flex items-center gap-4 p-3 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Ordenar por:</span>
                    </div>
                    <Select value={advancedFilters.order_by} onValueChange={(v) => handleAdvancedFilterChange('order_by', v)}>
                      <SelectTrigger className="w-[200px] h-9 bg-gray-900">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ORDER_OPTIONS.map(opt => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="flex items-center gap-2 ml-4">
                      <span className="text-sm text-gray-500 dark:text-gray-400">Limite:</span>
                      <Input
                        type="number"
                        min="10"
                        max="500"
                        value={advancedFilters.limit}
                        onChange={(e) => handleAdvancedFilterChange('limit', parseInt(e.target.value) || 100)}
                        className="w-20 h-9 bg-gray-900"
                      />
                    </div>
                  </div>
                )}
              </div>

              {loading && (
                <SkeletonList count={6} type="offer" />
              )}

              {error && !loading && (
                <ErrorState
                  message={error}
                  onRetry={() => {
                    setError(null);
                    setShowResults(false);
                  }}
                  retryText="Tentar novamente"
                />
              )}

              {!loading && !error && offers.length === 0 && (
                <EmptyState
                  icon="search"
                  title="Nenhuma máquina encontrada"
                  description="Não encontramos ofertas com os filtros selecionados. Tente ajustar os critérios de busca."
                  action={() => setShowResults(false)}
                  actionText="Ajustar filtros"
                />
              )}

              {!loading && offers.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {offers.map((offer, index) => (
                    <div
                      key={offer.id || index}
                      className="animate-scaleIn"
                      style={{ animationDelay: `${index * 0.05}s` }}
                    >
                      <OfferCard offer={offer} onSelect={handleSelectOffer} />
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          )}
        </Card>
      </div>
    </div >
  );
}

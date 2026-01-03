/**
 * useWizardForm Hook
 *
 * Extracts wizard logic from WizardForm component for better testability.
 *
 * Follows best practices:
 * - Single responsibility: Each function does one thing
 * - Pure functions for calculations
 * - Separated state management
 * - Injectable dependencies for mocking
 */
import { useState, useEffect, useCallback, useMemo } from 'react';

// =============================================================================
// CONSTANTS
// =============================================================================

export const WIZARD_STEPS = [
  { id: 1, name: 'Região', description: 'Localização' },
  { id: 2, name: 'Hardware', description: 'GPU e performance' },
  { id: 3, name: 'Estratégia', description: 'Failover' },
  { id: 4, name: 'Provisionar', description: 'Conectando' },
];

export const DEFAULT_DOCKER_IMAGE = 'pytorch/pytorch:latest';

export const DEFAULT_PORTS = [
  { port: '22', protocol: 'TCP' },
  { port: '8080', protocol: 'TCP' },  // code-server (VS Code Online)
  { port: '8888', protocol: 'TCP' },
  { port: '6006', protocol: 'TCP' },
];

export const FAILOVER_STRATEGIES = {
  SNAPSHOT_ONLY: 'snapshot_only',
  VAST_WARMPOOL: 'vast_warmpool',
  CPU_STANDBY: 'cpu_standby_only',
  TENSORDOCK: 'tensordock',
  NO_FAILOVER: 'no_failover',
};

export const MIN_BALANCE = 0.10;

// =============================================================================
// PURE FUNCTIONS (easily testable)
// =============================================================================

/**
 * Format seconds as mm:ss
 */
export function formatTime(seconds) {
  if (typeof seconds !== 'number' || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Calculate ETA based on elapsed time and progress
 */
export function calculateETA(elapsedTime, maxProgress, hasWinner) {
  if (hasWinner) return 'Concluído!';
  if (maxProgress <= 0) return 'Sem máquinas ativas';
  if (maxProgress <= 10 || elapsedTime < 3) return 'Estimando...';

  const estimatedTotal = (elapsedTime / maxProgress) * 100;
  const remaining = Math.max(0, Math.ceil(estimatedTotal - elapsedTime));

  if (remaining < 60) return `~${remaining}s restantes`;
  return `~${Math.ceil(remaining / 60)}min restantes`;
}

/**
 * Check if step data is complete
 */
export function isStepDataComplete(stepId, data) {
  const { selectedLocation, selectedTier, failoverStrategy, provisioningWinner } = data;

  switch (stepId) {
    case 1: return !!selectedLocation;
    case 2: return !!selectedTier;
    case 3: return !!failoverStrategy;
    case 4: return !!provisioningWinner;
    default: return false;
  }
}

/**
 * Check if user can proceed to a specific step
 */
export function canProceedToStep(targetStep, currentStep, stepData) {
  if (targetStep < currentStep) return true;
  if (targetStep === currentStep) return true;
  if (targetStep === currentStep + 1) {
    return isStepDataComplete(currentStep, stepData);
  }
  return false;
}

/**
 * Validate wizard data before provisioning
 */
export function validateWizardData(data, userBalance) {
  const errors = [];

  if (!data.selectedLocation) {
    errors.push('Por favor, selecione uma localização para sua máquina');
  }

  if (!data.selectedTier) {
    errors.push('Por favor, selecione um tier de performance');
  }

  if (userBalance !== null && userBalance < MIN_BALANCE) {
    errors.push(
      `Saldo insuficiente. Você precisa de pelo menos $${MIN_BALANCE.toFixed(2)} para criar uma máquina. Saldo atual: $${userBalance.toFixed(2)}`
    );
  }

  return errors;
}

/**
 * Get estimated cost based on tier
 */
export function getEstimatedCost(tier, tiers) {
  if (!tier || !tiers) return { hourly: '0.00', daily: '0.00' };

  const tierData = tiers.find(t => t.name === tier);
  if (!tierData) return { hourly: '0.00', daily: '0.00' };

  const match = tierData.priceRange?.match(/\$(\d+\.?\d*)/);
  const minPrice = match ? parseFloat(match[1]) : 0.20;

  return {
    hourly: minPrice.toFixed(2),
    daily: (minPrice * 24).toFixed(2),
  };
}

/**
 * Filter GPUs by search query
 */
export function filterGPUs(gpus, query) {
  if (!query || !query.trim()) return gpus;

  const lowerQuery = query.toLowerCase();
  return gpus.filter(gpu =>
    gpu.name.toLowerCase().includes(lowerQuery) ||
    gpu.vram.toLowerCase().includes(lowerQuery)
  );
}

/**
 * Get active candidates (not failed)
 */
export function getActiveCandidates(candidates) {
  return candidates.filter(c => c.status !== 'failed');
}

/**
 * Get max progress from candidates
 */
export function getMaxProgress(candidates) {
  const active = getActiveCandidates(candidates);
  if (active.length === 0) return 0;
  return Math.max(...active.map(c => c.progress || 0));
}

// =============================================================================
// MOCK DATA GENERATORS
// =============================================================================

export function getMockMachinesForTier(tierName) {
  const mockData = {
    'CPU': [
      { id: 'cpu1', gpu_name: 'CPU Only', gpu_ram: 0, num_gpus: 0, cpu_cores: 4, cpu_ram: 16, dph_total: 0.02, reliability: 99.9, location: 'GCP', provider: 'GCP', label: 'Mais econômico', isCPU: true },
      { id: 'cpu2', gpu_name: 'CPU Only', gpu_ram: 0, num_gpus: 0, cpu_cores: 8, cpu_ram: 32, dph_total: 0.04, reliability: 99.9, location: 'GCP', provider: 'GCP', label: 'Melhor custo-benefício', isCPU: true },
      { id: 'cpu3', gpu_name: 'CPU Only', gpu_ram: 0, num_gpus: 0, cpu_cores: 16, cpu_ram: 64, dph_total: 0.08, reliability: 99.9, location: 'GCP', provider: 'GCP', label: 'Mais rápido', isCPU: true },
    ],
    'Lento': [
      { id: 'eco1', gpu_name: 'RTX 3060', gpu_ram: 12, num_gpus: 1, dph_total: 0.15, reliability: 98.5, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
      { id: 'eco2', gpu_name: 'RTX 3070', gpu_ram: 8, num_gpus: 1, dph_total: 0.18, reliability: 99.1, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
      { id: 'eco3', gpu_name: 'GTX 1080 Ti', gpu_ram: 11, num_gpus: 1, dph_total: 0.12, reliability: 97.8, location: 'US-East', provider: 'vast.ai', label: 'Mais rápido' },
    ],
    'Medio': [
      { id: 'med1', gpu_name: 'RTX 3080', gpu_ram: 10, num_gpus: 1, dph_total: 0.25, reliability: 99.2, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
      { id: 'med2', gpu_name: 'RTX 3090', gpu_ram: 24, num_gpus: 1, dph_total: 0.35, reliability: 99.5, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
      { id: 'med3', gpu_name: 'RTX 4070', gpu_ram: 12, num_gpus: 1, dph_total: 0.30, reliability: 99.8, location: 'US-East', provider: 'tensordock', label: 'Mais rápido' },
    ],
    'Rapido': [
      { id: 'rap1', gpu_name: 'RTX 4080', gpu_ram: 16, num_gpus: 1, dph_total: 0.45, reliability: 99.5, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
      { id: 'rap2', gpu_name: 'RTX 4090', gpu_ram: 24, num_gpus: 1, dph_total: 0.65, reliability: 99.7, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
      { id: 'rap3', gpu_name: 'A100 40GB', gpu_ram: 40, num_gpus: 1, dph_total: 0.85, reliability: 99.9, location: 'US-East', provider: 'vast.ai', label: 'Mais rápido' },
    ],
    'Ultra': [
      { id: 'ult1', gpu_name: 'A100 80GB', gpu_ram: 80, num_gpus: 1, dph_total: 1.20, reliability: 99.8, location: 'US-West', provider: 'vast.ai', label: 'Mais econômico' },
      { id: 'ult2', gpu_name: 'H100 80GB', gpu_ram: 80, num_gpus: 1, dph_total: 2.50, reliability: 99.9, location: 'EU-West', provider: 'vast.ai', label: 'Melhor custo-benefício' },
      { id: 'ult3', gpu_name: 'A100 80GB', gpu_ram: 80, num_gpus: 2, dph_total: 2.40, reliability: 99.9, location: 'US-East', provider: 'vast.ai', label: 'Mais rápido' },
    ],
  };
  return mockData[tierName] || mockData['Medio'];
}

// =============================================================================
// MAIN HOOK
// =============================================================================

/**
 * Main wizard form hook
 */
export function useWizardForm(options = {}) {
  const {
    initialStep = 1,
    onSubmit,
    onCancelProvisioning,
    tiers = [],
  } = options;

  // Step state
  const [currentStep, setCurrentStep] = useState(initialStep);
  const [validationErrors, setValidationErrors] = useState([]);

  // Step 1: Location
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [searchCountry, setSearchCountry] = useState('');

  // Step 2: Hardware
  const [selectedTier, setSelectedTier] = useState(null);
  const [selectedGPU, setSelectedGPU] = useState(null);
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [gpuSearchQuery, setGpuSearchQuery] = useState('');
  const [selectionMode, setSelectionMode] = useState('recommended');
  const [recommendedMachines, setRecommendedMachines] = useState([]);
  const [loadingMachines, setLoadingMachines] = useState(false);

  // Step 3: Strategy
  const [failoverStrategy, setFailoverStrategy] = useState(FAILOVER_STRATEGIES.SNAPSHOT_ONLY);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [dockerImage, setDockerImage] = useState(DEFAULT_DOCKER_IMAGE);
  const [exposedPorts, setExposedPorts] = useState(DEFAULT_PORTS);

  // Step 4: Provisioning
  const [provisioningCandidates, setProvisioningCandidates] = useState([]);
  const [provisioningWinner, setProvisioningWinner] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Balance
  const [userBalance, setUserBalance] = useState(null);
  const [loadingBalance, setLoadingBalance] = useState(false);

  // Computed values
  const stepData = useMemo(() => ({
    selectedLocation,
    selectedTier,
    failoverStrategy,
    provisioningWinner,
  }), [selectedLocation, selectedTier, failoverStrategy, provisioningWinner]);

  const maxProgress = useMemo(
    () => getMaxProgress(provisioningCandidates),
    [provisioningCandidates]
  );

  const eta = useMemo(
    () => calculateETA(elapsedTime, maxProgress, !!provisioningWinner),
    [elapsedTime, maxProgress, provisioningWinner]
  );

  const estimatedCost = useMemo(
    () => getEstimatedCost(selectedTier, tiers),
    [selectedTier, tiers]
  );

  // Timer for provisioning
  useEffect(() => {
    if (currentStep === 4 && !provisioningWinner) {
      setElapsedTime(0);
      const interval = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [currentStep, provisioningWinner]);

  // Navigation
  const goToStep = useCallback((stepId) => {
    if (canProceedToStep(stepId, currentStep, stepData)) {
      setCurrentStep(stepId);
    }
  }, [currentStep, stepData]);

  const handleNext = useCallback(() => {
    if (currentStep < WIZARD_STEPS.length && isStepDataComplete(currentStep, stepData)) {
      if (currentStep === 3) {
        // Validate and start provisioning
        const errors = validateWizardData(stepData, userBalance);
        if (errors.length > 0) {
          setValidationErrors(errors);
          return;
        }
        setValidationErrors([]);
        setCurrentStep(4);
        if (onSubmit) onSubmit();
      } else {
        setCurrentStep(currentStep + 1);
      }
    }
  }, [currentStep, stepData, userBalance, onSubmit]);

  const handlePrev = useCallback(() => {
    if (currentStep > 1) {
      if (currentStep === 4 && onCancelProvisioning) {
        onCancelProvisioning();
      }
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep, onCancelProvisioning]);

  // Port management
  const addPort = useCallback(() => {
    setExposedPorts(prev => [...prev, { port: '', protocol: 'TCP' }]);
  }, []);

  const removePort = useCallback((index) => {
    setExposedPorts(prev => prev.filter((_, i) => i !== index));
  }, []);

  const updatePort = useCallback((index, field, value) => {
    setExposedPorts(prev => {
      const newPorts = [...prev];
      newPorts[index] = { ...newPorts[index], [field]: value };
      return newPorts;
    });
  }, []);

  // Clear selection
  const clearLocation = useCallback(() => {
    setSelectedLocation(null);
    setSearchCountry('');
  }, []);

  // Reset wizard
  const reset = useCallback(() => {
    setCurrentStep(1);
    setValidationErrors([]);
    setSelectedLocation(null);
    setSearchCountry('');
    setSelectedTier(null);
    setSelectedGPU(null);
    setSelectedMachine(null);
    setGpuSearchQuery('');
    setSelectionMode('recommended');
    setRecommendedMachines([]);
    setFailoverStrategy(FAILOVER_STRATEGIES.SNAPSHOT_ONLY);
    setShowAdvancedSettings(false);
    setDockerImage(DEFAULT_DOCKER_IMAGE);
    setExposedPorts(DEFAULT_PORTS);
    setProvisioningCandidates([]);
    setProvisioningWinner(null);
    setElapsedTime(0);
  }, []);

  return {
    // Step state
    currentStep,
    steps: WIZARD_STEPS,
    validationErrors,

    // Step 1: Location
    selectedLocation,
    setSelectedLocation,
    searchCountry,
    setSearchCountry,
    clearLocation,

    // Step 2: Hardware
    selectedTier,
    setSelectedTier,
    selectedGPU,
    setSelectedGPU,
    selectedMachine,
    setSelectedMachine,
    gpuSearchQuery,
    setGpuSearchQuery,
    selectionMode,
    setSelectionMode,
    recommendedMachines,
    setRecommendedMachines,
    loadingMachines,
    setLoadingMachines,

    // Step 3: Strategy
    failoverStrategy,
    setFailoverStrategy,
    showAdvancedSettings,
    setShowAdvancedSettings,
    dockerImage,
    setDockerImage,
    exposedPorts,
    addPort,
    removePort,
    updatePort,

    // Step 4: Provisioning
    provisioningCandidates,
    setProvisioningCandidates,
    provisioningWinner,
    setProvisioningWinner,
    elapsedTime,

    // Balance
    userBalance,
    setUserBalance,
    loadingBalance,
    setLoadingBalance,

    // Computed
    stepData,
    maxProgress,
    eta,
    estimatedCost,
    formattedTime: formatTime(elapsedTime),

    // Navigation
    goToStep,
    handleNext,
    handlePrev,
    canProceedToStep: (stepId) => canProceedToStep(stepId, currentStep, stepData),
    isStepComplete: (stepId) => isStepDataComplete(stepId, stepData),

    // Actions
    reset,
  };
}

export default useWizardForm;

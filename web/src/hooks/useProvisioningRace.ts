/**
 * useProvisioningRace Hook
 *
 * Manages the GPU provisioning race logic:
 * - Creates multiple machines in parallel (5 per round)
 * - First machine to become ready wins
 * - Losers are destroyed
 * - Retries up to 3 rounds if all fail
 *
 * Refactored for better testability:
 * - Separated state management from side effects
 * - Injectable API service for mocking
 * - Clear status transitions
 * - Full TypeScript support
 */
import { useState, useRef, useCallback, useEffect, MutableRefObject } from 'react';

// ============================================================================
// Types & Interfaces
// ============================================================================

/** Status of individual machines in the race */
export type MachineStatusType =
  | 'idle'
  | 'creating'
  | 'connecting'
  | 'connected'
  | 'ready'
  | 'failed'
  | 'cancelled';

/** Status of the overall race */
export type RaceStatusType =
  | 'idle'
  | 'searching'
  | 'racing'
  | 'completed'
  | 'failed'
  | 'cancelled';

/** GPU offer from the API */
export interface GpuOffer {
  id: string | number;
  gpu_name: string;
  dph_total: number;
  disk_space?: number;
  geolocation?: string;
  verified?: boolean;
  num_gpus?: number;
  gpu_ram?: number;
  [key: string]: unknown; // Allow additional properties
}

/** Race candidate (offer + race state) */
export interface RaceCandidate extends GpuOffer {
  index: number;
  status: MachineStatusType;
  progress: number;
  errorMessage: string | null;
  instanceId: string | null;
  actualStatus?: string;
}

/** Winner data with connection info */
export interface RaceWinner extends RaceCandidate {
  instanceId: string;
  ssh_host?: string | null;
  ssh_port?: number | null;
  actual_status: string;
}

/** Instance status from API */
export interface InstanceStatus {
  id: string;
  actual_status: string;
  ssh_host?: string | null;
  ssh_port?: number | null;
  [key: string]: unknown;
}

/** Created instance tracking */
export interface CreatedInstance {
  index: number;
  instanceId: string;
  offerId: string | number;
}

/** Race configuration options */
export interface RaceConfig {
  maxCandidates?: number;
  maxRounds?: number;
  pollIntervalMs?: number;
  timeoutMs?: number;
  createDelayMs?: number;
}

/** API service interface for dependency injection */
export interface ApiService {
  createInstance(offer: GpuOffer, label: string): Promise<string>;
  getInstanceStatus(instanceId: string): Promise<InstanceStatus>;
  destroyInstance(instanceId: string): Promise<boolean>;
}

/** Mock API service options */
export interface MockApiServiceOptions {
  createDelay?: number;
  readyDelay?: number;
  failureRate?: number;
  winnerIndex?: number | null;
}

/** Return type of the useProvisioningRace hook */
export interface UseProvisioningRaceReturn {
  // State
  candidates: RaceCandidate[];
  winner: RaceWinner | null;
  raceStatus: RaceStatusType;
  currentRound: number;
  error: string | null;
  elapsedTime: number;
  maxRounds: number;

  // Status checks
  isIdle: boolean;
  isRacing: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isCancelled: boolean;

  // Actions
  startRace: (offers: GpuOffer[]) => void;
  cancelRace: () => Promise<void>;
  completeRace: () => RaceWinner | null;
  reset: () => void;

  // For Redux integration
  getCreatedInstanceIds: () => string[];
}

// ============================================================================
// Constants
// ============================================================================

/** Status constants for machines */
export const MACHINE_STATUS: Record<string, MachineStatusType> = {
  IDLE: 'idle',
  CREATING: 'creating',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  READY: 'ready',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;

/** Race status constants */
export const RACE_STATUS: Record<string, RaceStatusType> = {
  IDLE: 'idle',
  SEARCHING: 'searching',
  RACING: 'racing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;

/** Default configuration */
const DEFAULT_CONFIG: Required<RaceConfig> = {
  maxCandidates: 5,
  maxRounds: 3,
  pollIntervalMs: 3000,
  timeoutMs: 5 * 60 * 1000, // 5 minutes
  createDelayMs: 500, // Delay between creates to avoid rate limiting
};

// ============================================================================
// API Service Factories
// ============================================================================

/**
 * Create default API service for production use
 */
export const createDefaultApiService = (apiBase: string = ''): ApiService => ({
  async createInstance(offer: GpuOffer, label: string): Promise<string> {
    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token');

    const res = await fetch(`${apiBase}/api/v1/instances`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        offer_id: offer.id,
        disk_size: offer.disk_space || 20,
        label,
      }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || error.error || `HTTP ${res.status}`);
    }

    const data = await res.json();
    return data.id || data.instance_id;
  },

  async getInstanceStatus(instanceId: string): Promise<InstanceStatus> {
    const token = localStorage.getItem('auth_token');

    const res = await fetch(`${apiBase}/api/v1/instances/${instanceId}`, {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  },

  async destroyInstance(instanceId: string): Promise<boolean> {
    const token = localStorage.getItem('auth_token');

    const res = await fetch(`${apiBase}/api/v1/instances/${instanceId}`, {
      method: 'DELETE',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });
    return res.ok;
  },
});

/** Mock instance for testing */
interface MockInstance {
  id: string;
  offer: GpuOffer;
  label: string;
  status: string;
  createdAt: number;
  readyAt: number;
}

/** Extended mock API service with test helpers */
export interface MockApiService extends ApiService {
  _forceReady(instanceId: string): void;
  _forceFail(instanceId: string): void;
  _getInstances(): Map<string, MockInstance>;
  _clear(): void;
}

/**
 * Create a mock API service for testing
 */
export const createMockApiService = (options: MockApiServiceOptions = {}): MockApiService => {
  const {
    createDelay = 500,
    readyDelay = 3000,
    failureRate = 0.2,
    winnerIndex = null,
  } = options;

  const instances = new Map<string, MockInstance>();
  let instanceCounter = 1;

  return {
    async createInstance(offer: GpuOffer, label: string): Promise<string> {
      await new Promise(r => setTimeout(r, createDelay));

      // Simulate random failure
      if (Math.random() < failureRate && winnerIndex === null) {
        throw new Error('Simulated creation failure');
      }

      const instanceId = `mock-${instanceCounter++}`;
      instances.set(instanceId, {
        id: instanceId,
        offer,
        label,
        status: 'loading',
        createdAt: Date.now(),
        readyAt: Date.now() + readyDelay + Math.random() * 2000,
      });

      return instanceId;
    },

    async getInstanceStatus(instanceId: string): Promise<InstanceStatus> {
      const instance = instances.get(instanceId);
      if (!instance) {
        throw new Error('Instance not found');
      }

      // Check if instance should be ready
      if (Date.now() >= instance.readyAt) {
        instance.status = 'running';
      }

      return {
        id: instance.id,
        actual_status: instance.status,
        ssh_host: instance.status === 'running' ? `${instanceId}.mock.host` : null,
        ssh_port: instance.status === 'running' ? 22 : null,
      };
    },

    async destroyInstance(instanceId: string): Promise<boolean> {
      instances.delete(instanceId);
      return true;
    },

    // Test helpers
    _forceReady(instanceId: string): void {
      const instance = instances.get(instanceId);
      if (instance) {
        instance.status = 'running';
        instance.readyAt = Date.now();
      }
    },

    _forceFail(instanceId: string): void {
      const instance = instances.get(instanceId);
      if (instance) {
        instance.status = 'exited';
      }
    },

    _getInstances(): Map<string, MockInstance> {
      return instances;
    },

    _clear(): void {
      instances.clear();
      instanceCounter = 1;
    },
  };
};

// ============================================================================
// Main Hook
// ============================================================================

/**
 * Hook for managing GPU provisioning race
 *
 * @param apiService - API service for instance operations
 * @param config - Race configuration options
 * @returns Race state and control functions
 *
 * @example
 * ```tsx
 * const apiService = useMemo(() => createDefaultApiService(''), []);
 * const {
 *   candidates,
 *   winner,
 *   isRacing,
 *   startRace,
 *   cancelRace,
 * } = useProvisioningRace(apiService, {
 *   maxCandidates: 5,
 *   maxRounds: 3,
 *   timeoutMs: 15000,
 * });
 * ```
 */
export function useProvisioningRace(
  apiService: ApiService,
  config: RaceConfig = {}
): UseProvisioningRaceReturn {
  const mergedConfig: Required<RaceConfig> = { ...DEFAULT_CONFIG, ...config };

  // State
  const [candidates, setCandidates] = useState<RaceCandidate[]>([]);
  const [winner, setWinner] = useState<RaceWinner | null>(null);
  const [raceStatus, setRaceStatus] = useState<RaceStatusType>(RACE_STATUS.IDLE);
  const [currentRound, setCurrentRound] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [elapsedTime, setElapsedTime] = useState<number>(0);

  // Refs for cleanup and avoiding stale closures
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const createdInstancesRef = useRef<CreatedInstance[]>([]);
  const allOffersRef = useRef<GpuOffer[]>([]);
  const isCancelledRef = useRef<boolean>(false);
  const hasWinnerRef = useRef<boolean>(false);
  const candidatesRef = useRef<RaceCandidate[]>([]); // For accessing current candidates in callbacks

  // Keep candidatesRef in sync
  useEffect(() => {
    console.log('[useProvisioningRace] candidates state changed:', candidates.length);
    candidatesRef.current = candidates;
  }, [candidates]);

  // Cleanup function
  const cleanup = useCallback((): void => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
      // Destroy any remaining instances
      createdInstancesRef.current.forEach(async ({ instanceId }) => {
        try {
          await apiService.destroyInstance(instanceId);
        } catch (e) {
          console.warn('Failed to cleanup instance:', e);
        }
      });
    };
  }, [cleanup, apiService]);

  // Update candidate status
  const updateCandidate = useCallback((index: number, updates: Partial<RaceCandidate>): void => {
    setCandidates(prev => {
      const updated = [...prev];
      if (updated[index]) {
        updated[index] = { ...updated[index], ...updates };
      }
      return updated;
    });
  }, []);

  // Destroy loser instances
  const destroyLosers = useCallback(async (winnerId: string): Promise<void> => {
    for (const created of createdInstancesRef.current) {
      if (created.instanceId !== winnerId) {
        try {
          await apiService.destroyInstance(created.instanceId);
        } catch (e) {
          console.warn('Failed to destroy loser:', e);
        }
      }
    }
  }, [apiService]);

  // Create a single instance
  const createInstance = useCallback(async (
    offer: GpuOffer,
    index: number,
    round: number
  ): Promise<{ index: number; instanceId?: string; success: boolean; error?: Error }> => {
    console.log('[useProvisioningRace] createInstance called:', index, offer.gpu_name, offer.id);
    try {
      updateCandidate(index, { status: MACHINE_STATUS.CREATING, progress: 10 });

      const label = `Race-R${round}-${offer.gpu_name}-${Date.now()}`;
      console.log('[useProvisioningRace] Calling API to create instance with label:', label);
      const instanceId = await apiService.createInstance(offer, label);
      console.log('[useProvisioningRace] Instance created:', instanceId);

      createdInstancesRef.current.push({ index, instanceId, offerId: offer.id });
      updateCandidate(index, {
        instanceId,
        status: MACHINE_STATUS.CONNECTING,
        progress: 30,
      });

      return { index, instanceId, success: true };
    } catch (err) {
      const error = err as Error;
      let errorMessage = 'Falha ao criar';

      if (error.message?.includes('401') || error.message?.includes('403')) {
        errorMessage = 'API Key inválida';
      } else if (error.message?.includes('402')) {
        errorMessage = 'Saldo insuficiente';
      } else if (error.message?.includes('429')) {
        errorMessage = 'Rate limit';
      } else if (error.message?.length <= 25) {
        errorMessage = error.message;
      }

      updateCandidate(index, {
        status: MACHINE_STATUS.FAILED,
        progress: 0,
        errorMessage,
      });

      return { index, success: false, error };
    }
  }, [apiService, updateCandidate]);

  // Handle all machines failed - destroy current instances and try next round
  const handleAllFailed = useCallback(async (): Promise<void> => {
    const round = currentRound;
    const hasMoreOffers = allOffersRef.current.length > round * mergedConfig.maxCandidates;

    // Destroy all instances from the failed round
    for (const created of createdInstancesRef.current) {
      try {
        await apiService.destroyInstance(created.instanceId);
      } catch (e) {
        console.warn('Failed to destroy failed instance:', e);
      }
    }
    createdInstancesRef.current = [];

    if (round < mergedConfig.maxRounds && hasMoreOffers) {
      // Start next round
      setCurrentRound(round + 1);
      // Note: startRound will be called in a separate effect or we need to restructure
    } else {
      setRaceStatus(RACE_STATUS.FAILED);
      setError('Todas as tentativas falharam');
    }
  }, [currentRound, mergedConfig, apiService]);

  // Poll instance status
  const pollInstances = useCallback(async (): Promise<void> => {
    console.log('[useProvisioningRace] pollInstances called, instances:', createdInstancesRef.current.length);
    if (isCancelledRef.current || hasWinnerRef.current) {
      console.log('[useProvisioningRace] pollInstances skipping - cancelled:', isCancelledRef.current, 'hasWinner:', hasWinnerRef.current);
      return;
    }

    let winnerFound = false;

    for (const created of createdInstancesRef.current) {
      if (isCancelledRef.current || hasWinnerRef.current) break;

      try {
        const instance = await apiService.getInstanceStatus(created.instanceId);
        const status = instance?.actual_status;
        const candidateIndex = created.index;

        // Update progress based on status
        setCandidates(prev => {
          const updated = [...prev];
          if (updated[candidateIndex] && updated[candidateIndex].status !== MACHINE_STATUS.FAILED) {
            let progress = updated[candidateIndex].progress || 30;
            if (status === 'loading') progress = Math.min(progress + 10, 90);
            if (status === 'running') progress = 100;

            updated[candidateIndex] = {
              ...updated[candidateIndex],
              progress,
              actualStatus: status,
            };
          }
          return updated;
        });

        // Check for failure states
        if (status === 'exited' || status === 'error' || status === 'destroyed') {
          updateCandidate(candidateIndex, {
            status: MACHINE_STATUS.FAILED,
            errorMessage: `Status: ${status}`,
          });
          continue;
        }

        // Check for winner
        if (status === 'running' && !winnerFound && !hasWinnerRef.current) {
          winnerFound = true;
          hasWinnerRef.current = true;
          cleanup();

          // Mark winner
          setCandidates(prev => prev.map((c, i) => ({
            ...c,
            status: i === candidateIndex ? MACHINE_STATUS.CONNECTED : MACHINE_STATUS.CANCELLED,
            progress: i === candidateIndex ? 100 : c.progress,
          })));

          // Set winner using ref to get current candidate data
          const currentCandidate = candidatesRef.current[candidateIndex];
          const winnerData: RaceWinner = {
            ...currentCandidate,
            instanceId: created.instanceId,
            ssh_host: instance.ssh_host,
            ssh_port: instance.ssh_port,
            actual_status: 'running',
          };

          setWinner(winnerData);
          setRaceStatus(RACE_STATUS.COMPLETED);

          // Destroy losers
          destroyLosers(created.instanceId);
          return;
        }
      } catch (err) {
        console.warn('Error polling instance:', err);
      }
    }

    // Check if all failed
    const currentCandidates = candidatesRef.current;
    const allFailed = createdInstancesRef.current.every(c => {
      const candidate = currentCandidates[c.index];
      return candidate?.status === MACHINE_STATUS.FAILED;
    });

    if (allFailed && createdInstancesRef.current.length > 0) {
      cleanup();
      handleAllFailed();
    }
  }, [apiService, cleanup, updateCandidate, destroyLosers, handleAllFailed]);

  // Start a round
  const startRound = useCallback(async (round: number): Promise<void> => {
    console.log('[useProvisioningRace] startRound called, round:', round);
    isCancelledRef.current = false;
    hasWinnerRef.current = false;
    createdInstancesRef.current = [];

    // Get offers for this round
    const startIdx = (round - 1) * mergedConfig.maxCandidates;
    const endIdx = startIdx + mergedConfig.maxCandidates;
    const roundOffers = allOffersRef.current.slice(startIdx, endIdx);

    console.log('[useProvisioningRace] roundOffers:', roundOffers.length, 'from', allOffersRef.current.length, 'total offers');

    if (roundOffers.length === 0) {
      console.log('[useProvisioningRace] No offers for round, failing');
      setRaceStatus(RACE_STATUS.FAILED);
      setError('Sem ofertas disponíveis');
      return;
    }

    // Initialize candidates
    const initialCandidates: RaceCandidate[] = roundOffers.map((offer, index) => ({
      ...offer,
      index,
      status: MACHINE_STATUS.IDLE,
      progress: 0,
      errorMessage: null,
      instanceId: null,
    }));

    console.log('[useProvisioningRace] Setting', initialCandidates.length, 'candidates');
    setCandidates(initialCandidates);
    setWinner(null);
    setRaceStatus(RACE_STATUS.RACING);
    console.log('[useProvisioningRace] Round', round, 'initialized, starting instance creation...');

    // Create instances with delay between each
    for (let i = 0; i < roundOffers.length; i++) {
      if (isCancelledRef.current) break;

      if (i > 0) {
        await new Promise(r => setTimeout(r, mergedConfig.createDelayMs));
      }

      createInstance(roundOffers[i], i, round);
    }

    // Start polling
    pollIntervalRef.current = setInterval(pollInstances, mergedConfig.pollIntervalMs);

    // Set timeout for this round - if no winner found, move to next round
    timeoutRef.current = setTimeout(() => {
      if (!hasWinnerRef.current && !isCancelledRef.current) {
        cleanup();
        handleAllFailed();
      }
    }, mergedConfig.timeoutMs);
  }, [mergedConfig, createInstance, pollInstances, cleanup, handleAllFailed]);

  // Effect to handle round changes (for retry logic)
  useEffect(() => {
    if (currentRound > 1 && raceStatus === RACE_STATUS.RACING) {
      // This means we need to start a new round after failure
      startRound(currentRound);
    }
  }, [currentRound]); // Intentionally not including all deps to avoid infinite loops

  // Start the race
  const startRace = useCallback((offers: GpuOffer[]): void => {
    console.log('[useProvisioningRace] startRace called with', offers?.length || 0, 'offers');

    if (!offers || offers.length === 0) {
      console.log('[useProvisioningRace] No offers, failing immediately');
      setError('Sem ofertas disponíveis');
      setRaceStatus(RACE_STATUS.FAILED);
      return;
    }

    // Reset state
    cleanup();
    allOffersRef.current = offers;
    hasWinnerRef.current = false;
    isCancelledRef.current = false;
    setCurrentRound(1);
    setElapsedTime(0);
    setError(null);
    setWinner(null);
    setCandidates([]);
    setRaceStatus(RACE_STATUS.SEARCHING);

    console.log('[useProvisioningRace] State reset, starting timer and first round');

    // Start timer
    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    // Start first round
    startRound(1);
  }, [cleanup, startRound]);

  // Cancel the race
  const cancelRace = useCallback(async (): Promise<void> => {
    isCancelledRef.current = true;
    cleanup();

    // Destroy all created instances
    for (const created of createdInstancesRef.current) {
      try {
        await apiService.destroyInstance(created.instanceId);
      } catch (e) {
        console.warn('Failed to destroy instance:', e);
      }
    }

    createdInstancesRef.current = [];
    setCandidates(prev => prev.map(c => ({
      ...c,
      status: c.status === MACHINE_STATUS.CONNECTED ? c.status : MACHINE_STATUS.CANCELLED,
    })));
    setRaceStatus(RACE_STATUS.CANCELLED);
  }, [cleanup, apiService]);

  // Complete the race (user confirms winner)
  const completeRace = useCallback((): RaceWinner | null => {
    cleanup();
    setRaceStatus(RACE_STATUS.IDLE);
    return winner;
  }, [cleanup, winner]);

  // Reset to initial state
  const reset = useCallback((): void => {
    cleanup();
    setCandidates([]);
    setWinner(null);
    setRaceStatus(RACE_STATUS.IDLE);
    setCurrentRound(1);
    setError(null);
    setElapsedTime(0);
    createdInstancesRef.current = [];
    allOffersRef.current = [];
    isCancelledRef.current = false;
    hasWinnerRef.current = false;
  }, [cleanup]);

  // Get all created instance IDs (for Redux integration)
  const getCreatedInstanceIds = useCallback((): string[] => {
    return createdInstancesRef.current.map(c => c.instanceId).filter(Boolean);
  }, []);

  return {
    // State
    candidates,
    winner,
    raceStatus,
    currentRound,
    error,
    elapsedTime,
    maxRounds: mergedConfig.maxRounds,

    // Status checks
    isIdle: raceStatus === RACE_STATUS.IDLE,
    isRacing: raceStatus === RACE_STATUS.RACING,
    isCompleted: raceStatus === RACE_STATUS.COMPLETED,
    isFailed: raceStatus === RACE_STATUS.FAILED,
    isCancelled: raceStatus === RACE_STATUS.CANCELLED,

    // Actions
    startRace,
    cancelRace,
    completeRace,
    reset,

    // For Redux integration
    getCreatedInstanceIds,
  };
}

export default useProvisioningRace;

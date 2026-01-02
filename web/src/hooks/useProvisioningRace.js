/**
 * useProvisioningRace Hook
 *
 * Manages the GPU provisioning race logic:
 * - Creates multiple machines in parallel
 * - First machine to become ready wins
 * - Losers are destroyed
 *
 * Refactored for better testability:
 * - Separated state management from side effects
 * - Injectable API service for mocking
 * - Clear status transitions
 */
import { useState, useRef, useCallback, useEffect } from 'react';

// Status constants for machines
export const MACHINE_STATUS = {
  IDLE: 'idle',
  CREATING: 'creating',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  READY: 'ready',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
};

// Race status constants
export const RACE_STATUS = {
  IDLE: 'idle',
  SEARCHING: 'searching',
  RACING: 'racing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
};

// Default configuration
const DEFAULT_CONFIG = {
  maxCandidates: 5,
  maxRounds: 3,
  pollIntervalMs: 3000,
  timeoutMs: 5 * 60 * 1000, // 5 minutes
  createDelayMs: 500, // Delay between creates to avoid rate limiting
};

/**
 * Default API service - can be replaced with mock for testing
 */
export const createDefaultApiService = (apiBase = '') => ({
  async createInstance(offer, label) {
    const res = await fetch(`${apiBase}/api/v1/instances/provision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

  async getInstanceStatus(instanceId) {
    const res = await fetch(`${apiBase}/api/v1/instances/${instanceId}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  },

  async destroyInstance(instanceId) {
    const res = await fetch(`${apiBase}/api/v1/instances/${instanceId}`, {
      method: 'DELETE',
    });
    return res.ok;
  },
});

/**
 * Create a mock API service for testing/demo mode
 */
export const createMockApiService = (options = {}) => {
  const {
    createDelay = 500,
    readyDelay = 3000,
    failureRate = 0.2,
    winnerIndex = null, // If set, this index always wins
  } = options;

  const instances = new Map();
  let instanceCounter = 1;

  return {
    async createInstance(offer, label) {
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

    async getInstanceStatus(instanceId) {
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

    async destroyInstance(instanceId) {
      instances.delete(instanceId);
      return true;
    },

    // Test helper: force an instance to be ready
    _forceReady(instanceId) {
      const instance = instances.get(instanceId);
      if (instance) {
        instance.status = 'running';
        instance.readyAt = Date.now();
      }
    },

    // Test helper: force an instance to fail
    _forceFail(instanceId) {
      const instance = instances.get(instanceId);
      if (instance) {
        instance.status = 'exited';
      }
    },

    // Test helper: get all instances
    _getInstances() {
      return instances;
    },

    // Test helper: clear all instances
    _clear() {
      instances.clear();
      instanceCounter = 1;
    },
  };
};

/**
 * Main hook for managing provisioning race
 */
export function useProvisioningRace(apiService, config = {}) {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  // State
  const [candidates, setCandidates] = useState([]);
  const [winner, setWinner] = useState(null);
  const [raceStatus, setRaceStatus] = useState(RACE_STATUS.IDLE);
  const [currentRound, setCurrentRound] = useState(1);
  const [error, setError] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Refs for cleanup
  const pollIntervalRef = useRef(null);
  const timeoutRef = useRef(null);
  const timerRef = useRef(null);
  const createdInstancesRef = useRef([]);
  const allOffersRef = useRef([]);
  const isCancelledRef = useRef(false);

  // Cleanup function
  const cleanup = useCallback(() => {
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
  const updateCandidate = useCallback((index, updates) => {
    setCandidates(prev => {
      const updated = [...prev];
      if (updated[index]) {
        updated[index] = { ...updated[index], ...updates };
      }
      return updated;
    });
  }, []);

  // Create a single instance
  const createInstance = useCallback(async (offer, index, round) => {
    try {
      updateCandidate(index, { status: MACHINE_STATUS.CREATING, progress: 10 });

      const label = `Race-R${round}-${offer.gpu_name}-${Date.now()}`;
      const instanceId = await apiService.createInstance(offer, label);

      createdInstancesRef.current.push({ index, instanceId, offerId: offer.id });
      updateCandidate(index, {
        instanceId,
        status: MACHINE_STATUS.CONNECTING,
        progress: 30,
      });

      return { index, instanceId, success: true };
    } catch (error) {
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

  // Poll instance status
  const pollInstances = useCallback(async () => {
    if (isCancelledRef.current) return;

    let winnerFound = false;

    for (const created of createdInstancesRef.current) {
      if (isCancelledRef.current) break;

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
        if (status === 'running' && !winnerFound) {
          winnerFound = true;
          cleanup();

          // Mark winner
          setCandidates(prev => prev.map((c, i) => ({
            ...c,
            status: i === candidateIndex ? MACHINE_STATUS.CONNECTED : MACHINE_STATUS.CANCELLED,
            progress: i === candidateIndex ? 100 : c.progress,
          })));

          // Set winner
          const winnerData = {
            ...prev => prev[candidateIndex],
            instanceId: created.instanceId,
            ssh_host: instance.ssh_host,
            ssh_port: instance.ssh_port,
            actual_status: 'running',
          };

          setWinner(candidates[candidateIndex] ? {
            ...candidates[candidateIndex],
            instanceId: created.instanceId,
            ssh_host: instance.ssh_host,
            ssh_port: instance.ssh_port,
            actual_status: 'running',
          } : winnerData);

          setRaceStatus(RACE_STATUS.COMPLETED);

          // Destroy losers
          destroyLosers(created.instanceId);
          return;
        }
      } catch (error) {
        console.warn('Error polling instance:', error);
      }
    }

    // Check if all failed
    const allFailed = createdInstancesRef.current.every(c => {
      const candidate = candidates.find((_, i) => i === c.index);
      return candidate?.status === MACHINE_STATUS.FAILED;
    });

    if (allFailed && createdInstancesRef.current.length > 0) {
      cleanup();
      handleAllFailed();
    }
  }, [apiService, candidates, cleanup, updateCandidate]);

  // Destroy loser instances
  const destroyLosers = useCallback(async (winnerId) => {
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

  // Handle all machines failed
  const handleAllFailed = useCallback(() => {
    const round = currentRound;
    const hasMoreOffers = allOffersRef.current.length > round * mergedConfig.maxCandidates;

    if (round < mergedConfig.maxRounds && hasMoreOffers) {
      // Start next round
      setCurrentRound(round + 1);
      startRound(round + 1);
    } else {
      setRaceStatus(RACE_STATUS.FAILED);
      setError('Todas as tentativas falharam');
    }
  }, [currentRound, mergedConfig]);

  // Start a round
  const startRound = useCallback(async (round) => {
    isCancelledRef.current = false;
    createdInstancesRef.current = [];

    // Get offers for this round
    const startIdx = (round - 1) * mergedConfig.maxCandidates;
    const endIdx = startIdx + mergedConfig.maxCandidates;
    const roundOffers = allOffersRef.current.slice(startIdx, endIdx);

    if (roundOffers.length === 0) {
      setRaceStatus(RACE_STATUS.FAILED);
      setError('Sem ofertas disponíveis');
      return;
    }

    // Initialize candidates
    const initialCandidates = roundOffers.map((offer, index) => ({
      ...offer,
      index,
      status: MACHINE_STATUS.IDLE,
      progress: 0,
      errorMessage: null,
      instanceId: null,
    }));

    setCandidates(initialCandidates);
    setWinner(null);
    setRaceStatus(RACE_STATUS.RACING);

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

    // Set timeout
    timeoutRef.current = setTimeout(() => {
      if (!winner && raceStatus === RACE_STATUS.RACING) {
        cleanup();
        handleAllFailed();
      }
    }, mergedConfig.timeoutMs);

  }, [mergedConfig, createInstance, pollInstances, cleanup, winner, raceStatus, handleAllFailed]);

  // Start the race
  const startRace = useCallback((offers) => {
    if (!offers || offers.length === 0) {
      setError('Sem ofertas disponíveis');
      setRaceStatus(RACE_STATUS.FAILED);
      return;
    }

    // Reset state
    cleanup();
    allOffersRef.current = offers;
    setCurrentRound(1);
    setElapsedTime(0);
    setError(null);
    setRaceStatus(RACE_STATUS.SEARCHING);

    // Start timer
    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    // Start first round
    startRound(1);
  }, [cleanup, startRound]);

  // Cancel the race
  const cancelRace = useCallback(async () => {
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
  const completeRace = useCallback(() => {
    cleanup();
    setRaceStatus(RACE_STATUS.IDLE);
    return winner;
  }, [cleanup, winner]);

  // Reset to initial state
  const reset = useCallback(() => {
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
  }, [cleanup]);

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
  };
}

export default useProvisioningRace;

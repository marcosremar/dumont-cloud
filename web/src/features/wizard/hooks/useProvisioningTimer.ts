/**
 * Provisioning Timer Hook
 *
 * Manages elapsed time and ETA calculation during provisioning.
 * Extracted for testability and reuse.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { ProvisioningCandidate } from '../types';

// ============================================================================
// Types
// ============================================================================

export interface UseProvisioningTimerOptions {
  isActive: boolean;
  candidates: ProvisioningCandidate[];
  hasWinner: boolean;
}

export interface UseProvisioningTimerReturn {
  elapsedTime: number;
  formattedTime: string;
  eta: string;
  reset: () => void;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format seconds as mm:ss
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Calculate ETA based on progress
 */
export function calculateETA(
  candidates: ProvisioningCandidate[],
  elapsedTime: number,
  hasWinner: boolean,
): string {
  if (hasWinner) return 'Concluído!';

  const activeCandidates = candidates.filter(c => c.status !== 'failed');
  if (activeCandidates.length === 0) return 'Sem máquinas ativas';

  const maxProgress = Math.max(...activeCandidates.map(c => c.progress ?? 0));

  // Need enough data to estimate
  if (maxProgress <= 10 || elapsedTime < 3) return 'Estimando...';

  const estimatedTotal = (elapsedTime / maxProgress) * 100;
  const remaining = Math.max(0, Math.ceil(estimatedTotal - elapsedTime));

  if (remaining < 60) return `~${remaining}s restantes`;
  return `~${Math.ceil(remaining / 60)}min restantes`;
}

// ============================================================================
// Hook
// ============================================================================

export function useProvisioningTimer(
  options: UseProvisioningTimerOptions,
): UseProvisioningTimerReturn {
  const { isActive, candidates, hasWinner } = options;
  const [elapsedTime, setElapsedTime] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Start/stop timer based on isActive
  useEffect(() => {
    if (isActive && !hasWinner) {
      setElapsedTime(0);
      intervalRef.current = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    } else {
      // Stop timer when not active or winner found
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [isActive, hasWinner]);

  // Reset timer
  const reset = useCallback(() => {
    setElapsedTime(0);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  return {
    elapsedTime,
    formattedTime: formatTime(elapsedTime),
    eta: calculateETA(candidates, elapsedTime, hasWinner),
    reset,
  };
}

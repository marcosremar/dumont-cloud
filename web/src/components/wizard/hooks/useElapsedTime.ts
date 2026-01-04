/**
 * useElapsedTime Hook
 * Tracks elapsed time during provisioning
 */

import { useState, useEffect, useRef } from 'react';

interface UseElapsedTimeOptions {
  running: boolean;
  resetOn?: unknown; // Reset timer when this value changes
}

interface UseElapsedTimeReturn {
  elapsedTime: number;
  reset: () => void;
}

export function useElapsedTime({
  running,
  resetOn,
}: UseElapsedTimeOptions): UseElapsedTimeReturn {
  const [elapsedTime, setElapsedTime] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Reset when resetOn changes
  useEffect(() => {
    setElapsedTime(0);
  }, [resetOn]);

  // Timer effect
  useEffect(() => {
    if (running) {
      setElapsedTime(0);
      intervalRef.current = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [running]);

  const reset = () => {
    setElapsedTime(0);
  };

  return {
    elapsedTime,
    reset,
  };
}

export default useElapsedTime;

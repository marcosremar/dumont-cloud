/**
 * useBalance Hook
 * Fetches and manages user balance
 */

import { useState, useEffect, useCallback } from 'react';

interface UseBalanceOptions {
  enabled?: boolean;
}

interface UseBalanceReturn {
  balance: number | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useBalance({
  enabled = true,
}: UseBalanceOptions = {}): UseBalanceReturn {
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBalance = useCallback(async () => {
    if (!enabled) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/v1/balance', {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (response.ok) {
        const data = await response.json();
        const balanceValue = data.credit ?? data.balance ?? 0;
        setBalance(parseFloat(balanceValue) || 0);
      } else {
        setBalance(0);
        setError('Erro ao buscar saldo');
      }
    } catch (err) {
      console.error('Failed to fetch balance:', err);
      setBalance(0);
      setError('Erro ao buscar saldo');
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    fetchBalance();
  }, [fetchBalance]);

  return {
    balance,
    loading,
    error,
    refetch: fetchBalance,
  };
}

export default useBalance;

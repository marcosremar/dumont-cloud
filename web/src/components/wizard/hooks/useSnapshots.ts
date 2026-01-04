/**
 * useSnapshots Hook
 * Fetches and manages snapshots for restore functionality
 */

import { useState, useEffect, useCallback } from 'react';
import type { Snapshot } from '../types/wizard.types';

interface UseSnapshotsOptions {
  enabled?: boolean;
}

interface UseSnapshotsReturn {
  snapshots: Snapshot[];
  selectedSnapshot: Snapshot | null;
  setSelectedSnapshot: (snapshot: Snapshot | null) => void;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Mock snapshots for fallback
const MOCK_SNAPSHOTS: Snapshot[] = [
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

export function useSnapshots({
  enabled = true,
}: UseSnapshotsOptions = {}): UseSnapshotsReturn {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSnapshots = useCallback(async () => {
    if (!enabled) {
      setSnapshots([]);
      setSelectedSnapshot(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/snapshots', {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (response.ok) {
        const data = await response.json();
        // API returns { snapshots: [...] } with restic snapshot data
        const parsedSnapshots: Snapshot[] = (data.snapshots || []).map(
          (snap: any, index: number) => ({
            id: snap.id || snap.short_id,
            name: snap.tags?.join(', ') || snap.hostname || `Snapshot ${snap.short_id}`,
            short_id: snap.short_id,
            created_at: snap.time,
            size_gb: snap.summary?.total_bytes_processed
              ? parseFloat((snap.summary.total_bytes_processed / (1024 * 1024 * 1024)).toFixed(1))
              : null,
            status: 'ready' as const,
            isLatest: index === 0,
            paths: snap.paths || ['/workspace'],
            hostname: snap.hostname,
          })
        );

        if (parsedSnapshots.length > 0) {
          setSnapshots(parsedSnapshots);
          setSelectedSnapshot(parsedSnapshots[0]); // Auto-select latest
        } else {
          // API returned empty, use mock as fallback
          setSnapshots(MOCK_SNAPSHOTS);
          setSelectedSnapshot(MOCK_SNAPSHOTS[0]);
        }
      } else {
        // API error, use mock snapshots as fallback
        console.log('Snapshots API not available, using mock data');
        setSnapshots(MOCK_SNAPSHOTS);
        setSelectedSnapshot(MOCK_SNAPSHOTS[0]);
      }
    } catch (err) {
      console.error('Failed to fetch snapshots:', err);
      // Use mock snapshots as fallback
      setSnapshots(MOCK_SNAPSHOTS);
      setSelectedSnapshot(MOCK_SNAPSHOTS[0]);
      setError(err instanceof Error ? err.message : 'Failed to fetch snapshots');
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    fetchSnapshots();
  }, [fetchSnapshots]);

  return {
    snapshots,
    selectedSnapshot,
    setSelectedSnapshot,
    loading,
    error,
    refetch: fetchSnapshots,
  };
}

export default useSnapshots;

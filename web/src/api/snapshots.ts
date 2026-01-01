/**
 * Snapshot Status API Client
 *
 * Provides functions to interact with the snapshot configuration and status API endpoints.
 * Uses the same authentication pattern as the existing API utilities.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

// Type definitions
export interface SnapshotInstanceConfig {
  instance_id: string
  interval_minutes: number
  enabled: boolean
  last_snapshot_at: string | null
  next_snapshot_at: string | null
  status: 'success' | 'failed' | 'pending' | 'overdue' | 'disabled'
  last_error: string | null
}

export interface SnapshotStatusResponse {
  total_instances: number
  enabled_count: number
  disabled_count: number
  status_counts: {
    success: number
    failed: number
    pending: number
    overdue: number
  }
  healthy: boolean
  instances: SnapshotInstanceConfig[]
}

export interface SnapshotConfigResponse {
  instance_id: string
  interval_minutes: number
  enabled: boolean
  last_snapshot_at: string | null
  next_snapshot_at: string | null
  status: string
  last_error: string | null
}

export interface SnapshotConfigUpdateRequest {
  interval_minutes?: number
  enabled?: boolean
}

export interface SnapshotConfigUpdateResponse {
  message: string
  config: SnapshotConfigResponse
}

export interface ApiError {
  error: string
  detail?: string
}

/**
 * Get authentication token from storage
 */
function getToken(): string | null {
  return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
}

/**
 * Build headers with authentication
 */
function buildHeaders(contentType?: string): HeadersInit {
  const headers: HeadersInit = {}
  const token = getToken()

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (contentType) {
    headers['Content-Type'] = contentType
  }

  return headers
}

/**
 * Check if response is an error
 */
function isApiError(data: unknown): data is ApiError {
  return typeof data === 'object' && data !== null && 'error' in data
}

/**
 * Get overall snapshot status across all instances
 *
 * @returns Aggregate snapshot status including per-instance details
 * @throws Error if the API request fails
 */
export async function getSnapshotStatus(): Promise<SnapshotStatusResponse> {
  const response = await fetch(`${API_BASE}/api/snapshots/status`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  })

  const data = await response.json()

  if (!response.ok) {
    const errorMessage = isApiError(data)
      ? data.error
      : 'Failed to fetch snapshot status'
    throw new Error(errorMessage)
  }

  return data as SnapshotStatusResponse
}

/**
 * Get snapshot configuration for a specific instance
 *
 * @param instanceId - The ID of the instance
 * @returns Snapshot configuration for the instance
 * @throws Error if the API request fails
 */
export async function getSnapshotConfig(instanceId: string): Promise<SnapshotConfigResponse> {
  if (!instanceId) {
    throw new Error('Instance ID is required')
  }

  const response = await fetch(`${API_BASE}/api/snapshots/config/${encodeURIComponent(instanceId)}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  })

  const data = await response.json()

  if (!response.ok) {
    const errorMessage = isApiError(data)
      ? data.error
      : 'Failed to fetch snapshot configuration'
    throw new Error(errorMessage)
  }

  return data as SnapshotConfigResponse
}

/**
 * Update snapshot configuration for a specific instance
 *
 * @param instanceId - The ID of the instance
 * @param config - Configuration to update (interval_minutes and/or enabled)
 * @returns Updated configuration
 * @throws Error if the API request fails or validation fails
 */
export async function updateSnapshotConfig(
  instanceId: string,
  config: SnapshotConfigUpdateRequest
): Promise<SnapshotConfigUpdateResponse> {
  if (!instanceId) {
    throw new Error('Instance ID is required')
  }

  // Validate interval if provided
  const validIntervals = [5, 15, 30, 60]
  if (config.interval_minutes !== undefined && !validIntervals.includes(config.interval_minutes)) {
    throw new Error(`Invalid interval. Must be one of: ${validIntervals.join(', ')} minutes`)
  }

  const response = await fetch(`${API_BASE}/api/snapshots/config/${encodeURIComponent(instanceId)}`, {
    method: 'POST',
    headers: buildHeaders('application/json'),
    credentials: 'include',
    body: JSON.stringify(config),
  })

  const data = await response.json()

  if (!response.ok) {
    const errorMessage = isApiError(data)
      ? data.error
      : 'Failed to update snapshot configuration'
    throw new Error(errorMessage)
  }

  return data as SnapshotConfigUpdateResponse
}

/**
 * Valid snapshot interval options in minutes
 */
export const SNAPSHOT_INTERVALS = [
  { value: 5, label: '5 minutes' },
  { value: 15, label: '15 minutes (Default)' },
  { value: 30, label: '30 minutes' },
  { value: 60, label: '1 hour' },
] as const

export type SnapshotInterval = typeof SNAPSHOT_INTERVALS[number]['value']

/**
 * Helper to format last snapshot time as relative time
 *
 * @param timestamp - ISO timestamp or null
 * @returns Human-readable relative time string
 */
export function formatSnapshotTime(timestamp: string | null): string {
  if (!timestamp) {
    return 'Never'
  }

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) {
    return 'Just now'
  } else if (diffMins < 60) {
    return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
  } else {
    return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
  }
}

/**
 * Get status badge color based on snapshot status
 *
 * @param status - Snapshot status string
 * @returns Tailwind CSS color class
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'success':
      return 'text-green-500'
    case 'failed':
      return 'text-red-500'
    case 'overdue':
      return 'text-yellow-500'
    case 'pending':
      return 'text-blue-500'
    case 'disabled':
      return 'text-gray-400'
    default:
      return 'text-gray-500'
  }
}

/**
 * Get status badge background color based on snapshot status
 *
 * @param status - Snapshot status string
 * @returns Tailwind CSS background color class
 */
export function getStatusBgColor(status: string): string {
  switch (status) {
    case 'success':
      return 'bg-green-100 dark:bg-green-900/30'
    case 'failed':
      return 'bg-red-100 dark:bg-red-900/30'
    case 'overdue':
      return 'bg-yellow-100 dark:bg-yellow-900/30'
    case 'pending':
      return 'bg-blue-100 dark:bg-blue-900/30'
    case 'disabled':
      return 'bg-gray-100 dark:bg-gray-800'
    default:
      return 'bg-gray-100 dark:bg-gray-800'
  }
}

/**
 * Reservation API Client
 *
 * Provides methods for interacting with the GPU reservation system API.
 * Uses the apiFetch utility for authentication and demo mode handling.
 */

import { apiFetch, apiGet, apiPost, apiDelete } from '../utils/api'

const API_PREFIX = '/api/v1/reservations'

/**
 * Fetch all reservations for the current user
 * @param {Object} options - Query options
 * @param {string} options.status - Filter by status (pending, active, completed, cancelled, failed)
 * @param {number} options.limit - Maximum number of results
 * @param {number} options.offset - Offset for pagination
 * @returns {Promise<{reservations: Array, count: number}>}
 */
export async function fetchReservations({ status, limit, offset } = {}) {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  if (limit) params.append('limit', limit.toString())
  if (offset) params.append('offset', offset.toString())

  const queryString = params.toString()
  const endpoint = queryString ? `${API_PREFIX}?${queryString}` : API_PREFIX

  const response = await apiGet(endpoint)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || error.detail || 'Failed to fetch reservations')
  }

  return response.json()
}

/**
 * Create a new GPU reservation
 * @param {Object} data - Reservation data
 * @param {string} data.gpu_type - GPU type (e.g., 'A100', 'H100')
 * @param {number} data.gpu_count - Number of GPUs (1-8)
 * @param {string} data.start_time - Start time (ISO 8601 format, UTC)
 * @param {string} data.end_time - End time (ISO 8601 format, UTC)
 * @param {string} [data.provider] - Preferred provider (optional)
 * @returns {Promise<Object>} Created reservation
 */
export async function createReservation(data) {
  const response = await apiPost(API_PREFIX, {
    gpu_type: data.gpu_type,
    gpu_count: data.gpu_count || 1,
    start_time: data.start_time,
    end_time: data.end_time,
    provider: data.provider || null,
  })

  if (!response.ok) {
    const error = await response.json()

    // Handle specific error codes
    if (response.status === 409) {
      throw new Error(error.detail || 'GPU not available for the requested time slot')
    }
    if (response.status === 402) {
      throw new Error(error.detail || 'Insufficient credits for this reservation')
    }
    if (response.status === 400) {
      throw new Error(error.detail || 'Invalid reservation data')
    }

    throw new Error(error.error || error.detail || 'Failed to create reservation')
  }

  return response.json()
}

/**
 * Get a specific reservation by ID
 * @param {number} reservationId - Reservation ID
 * @returns {Promise<Object>} Reservation details
 */
export async function getReservation(reservationId) {
  const response = await apiGet(`${API_PREFIX}/${reservationId}`)

  if (!response.ok) {
    const error = await response.json()
    if (response.status === 404) {
      throw new Error('Reservation not found')
    }
    throw new Error(error.error || error.detail || 'Failed to fetch reservation')
  }

  return response.json()
}

/**
 * Cancel a reservation
 * @param {number} reservationId - Reservation ID
 * @param {string} [reason] - Cancellation reason (optional)
 * @returns {Promise<Object>} Cancellation result with refund info
 */
export async function cancelReservation(reservationId, reason = null) {
  const endpoint = `${API_PREFIX}/${reservationId}`

  // Use apiFetch for DELETE with body
  const response = await apiFetch(endpoint, {
    method: 'DELETE',
    body: reason ? { reason } : {},
  })

  if (!response.ok) {
    const error = await response.json()
    if (response.status === 404) {
      throw new Error('Reservation not found')
    }
    if (response.status === 400) {
      throw new Error(error.detail || 'Reservation cannot be cancelled')
    }
    throw new Error(error.error || error.detail || 'Failed to cancel reservation')
  }

  return response.json()
}

/**
 * Check GPU availability for a time range
 * @param {Object} params - Availability check parameters
 * @param {string} params.gpu_type - GPU type (e.g., 'A100', 'H100')
 * @param {number} [params.gpu_count] - Number of GPUs (default: 1)
 * @param {string} params.start_time - Start time (ISO 8601 format, UTC)
 * @param {string} params.end_time - End time (ISO 8601 format, UTC)
 * @returns {Promise<Object>} Availability result
 */
export async function checkAvailability({ gpu_type, gpu_count = 1, start_time, end_time }) {
  const params = new URLSearchParams({
    gpu_type,
    gpu_count: gpu_count.toString(),
    start: start_time,
    end: end_time,
  })

  const response = await apiGet(`${API_PREFIX}/availability?${params.toString()}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || error.detail || 'Failed to check availability')
  }

  return response.json()
}

/**
 * Get pricing estimate for a reservation
 * @param {Object} params - Pricing parameters
 * @param {string} params.gpu_type - GPU type (e.g., 'A100', 'H100')
 * @param {number} [params.gpu_count] - Number of GPUs (default: 1)
 * @param {string} params.start_time - Start time (ISO 8601 format, UTC)
 * @param {string} params.end_time - End time (ISO 8601 format, UTC)
 * @returns {Promise<Object>} Pricing estimate with discount info
 */
export async function getPricingEstimate({ gpu_type, gpu_count = 1, start_time, end_time }) {
  const params = new URLSearchParams({
    gpu_type,
    gpu_count: gpu_count.toString(),
    start: start_time,
    end: end_time,
  })

  const response = await apiGet(`${API_PREFIX}/pricing?${params.toString()}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || error.detail || 'Failed to get pricing estimate')
  }

  return response.json()
}

/**
 * Get user's credit balance
 * @returns {Promise<Object>} Credit balance info
 */
export async function getCreditBalance() {
  const response = await apiGet(`${API_PREFIX}/credits/balance`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || error.detail || 'Failed to get credit balance')
  }

  return response.json()
}

/**
 * Purchase reservation credits
 * @param {number} amount - Amount of credits to purchase
 * @param {string} [description] - Purchase description (optional)
 * @returns {Promise<Object>} Purchase result
 */
export async function purchaseCredits(amount, description = null) {
  const response = await apiPost(`${API_PREFIX}/credits/purchase`, {
    amount,
    description,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || error.detail || 'Failed to purchase credits')
  }

  return response.json()
}

/**
 * Get credit transaction history
 * @param {Object} options - Query options
 * @param {number} options.limit - Maximum number of results
 * @param {number} options.offset - Offset for pagination
 * @returns {Promise<Object>} Credit history
 */
export async function getCreditHistory({ limit, offset } = {}) {
  const params = new URLSearchParams()
  if (limit) params.append('limit', limit.toString())
  if (offset) params.append('offset', offset.toString())

  const queryString = params.toString()
  const endpoint = queryString
    ? `${API_PREFIX}/credits/history?${queryString}`
    : `${API_PREFIX}/credits/history`

  const response = await apiGet(endpoint)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.error || error.detail || 'Failed to get credit history')
  }

  return response.json()
}

/**
 * Reservation API client object with all methods
 */
const reservationApi = {
  fetchReservations,
  createReservation,
  getReservation,
  cancelReservation,
  checkAvailability,
  getPricingEstimate,
  getCreditBalance,
  purchaseCredits,
  getCreditHistory,
}

export default reservationApi

/**
 * Regions API Service - Backend API calls for region operations
 *
 * Provides methods for fetching available regions, pricing, user preferences,
 * and suggested regions based on geolocation.
 */

const API_BASE = typeof process !== 'undefined' && process.env
  ? (process.env.VITE_API_URL || '')
  : (typeof import.meta !== 'undefined' ? (import.meta.env?.VITE_API_URL || '') : '')

/**
 * Get authentication token from localStorage
 * @returns {string|null} The auth token or null if not available
 */
const getToken = () => {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('auth_token')
  }
  return null
}

/**
 * Make an authenticated API request
 * @param {string} endpoint - API endpoint path
 * @param {object} options - Fetch options
 * @returns {Promise<object>} The response data
 */
const apiRequest = async (endpoint, options = {}) => {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  const data = await response.json()

  if (!response.ok) {
    const error = new Error(data.detail || data.message || 'API request failed')
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

/**
 * Fetch available regions with pricing and availability data
 * @returns {Promise<object[]>} List of available regions
 */
const fetchRegions = async () => {
  const data = await apiRequest('/api/v1/regions/available')
  return data.regions || data
}

/**
 * Fetch pricing details for a specific region
 * @param {string} regionId - The region identifier
 * @returns {Promise<object>} Pricing data for the region
 */
const fetchRegionPricing = async (regionId) => {
  if (!regionId) {
    throw new Error('Region ID is required')
  }
  const data = await apiRequest(`/api/v1/regions/${encodeURIComponent(regionId)}/pricing`)
  return data
}

/**
 * Fetch user's region preferences
 * @returns {Promise<object>} User's region preference settings
 */
const fetchUserRegionPreferences = async () => {
  const data = await apiRequest('/api/v1/users/region-preferences')
  return data
}

/**
 * Update user's region preferences
 * @param {object} preferences - The preference settings to update
 * @param {string} preferences.preferred_region - Preferred region ID
 * @param {string[]} [preferences.fallback_regions] - Fallback region IDs (max 5)
 * @param {string} [preferences.data_residency_requirement] - Compliance requirement (EU_GDPR, US_ONLY, APAC_ONLY)
 * @returns {Promise<object>} Updated preferences
 */
const updateUserRegionPreferences = async (preferences) => {
  if (!preferences || !preferences.preferred_region) {
    throw new Error('Preferred region is required')
  }
  const data = await apiRequest('/api/v1/users/region-preferences', {
    method: 'PUT',
    body: JSON.stringify(preferences),
  })
  return data
}

/**
 * Fetch suggested regions based on user's location
 * @returns {Promise<object[]>} List of suggested regions
 */
const fetchSuggestedRegions = async () => {
  const data = await apiRequest('/api/v1/regions/suggested')
  return data.suggested_regions || data
}

/**
 * Fetch EU-compliant regions for GDPR requirements
 * @returns {Promise<object[]>} List of EU regions
 */
const fetchEuRegions = async () => {
  const regions = await fetchRegions()
  return regions.filter(r => r.is_eu === true || (r.compliance_tags && r.compliance_tags.includes('GDPR')))
}

// Export for ES modules
const regionsApi = {
  fetchRegions,
  fetchRegionPricing,
  fetchUserRegionPreferences,
  updateUserRegionPreferences,
  fetchSuggestedRegions,
  fetchEuRegions,
}

// CommonJS exports for Node.js compatibility
if (typeof module !== 'undefined' && module.exports) {
  module.exports = regionsApi
}

export {
  fetchRegions,
  fetchRegionPricing,
  fetchUserRegionPreferences,
  updateUserRegionPreferences,
  fetchSuggestedRegions,
  fetchEuRegions,
}

export default regionsApi

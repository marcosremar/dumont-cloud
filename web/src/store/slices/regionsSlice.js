/**
 * Regions Slice - Manages region data, pricing, and user preferences
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchRegions = createAsyncThunk(
  'regions/fetchRegions',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/regions/available`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch regions')
      }
      return data.regions || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchRegionPricing = createAsyncThunk(
  'regions/fetchRegionPricing',
  async (regionId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/regions/${regionId}/pricing`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch region pricing')
      }
      return { regionId, pricing: data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchUserRegionPreferences = createAsyncThunk(
  'regions/fetchUserRegionPreferences',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/users/region-preferences`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch region preferences')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const updateUserRegionPreferences = createAsyncThunk(
  'regions/updateUserRegionPreferences',
  async (preferences, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/users/region-preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(preferences),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to update region preferences')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchSuggestedRegions = createAsyncThunk(
  'regions/fetchSuggestedRegions',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/regions/suggested`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch suggested regions')
      }
      return data.suggested_regions || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  // Available regions from the API
  available: [],
  // User's selected region for current provisioning
  selected: null,
  // User's persisted preferences
  preferences: {
    preferred_region: null,
    fallback_regions: [],
    data_residency_requirement: null,
  },
  // Pricing data keyed by region ID
  pricing: {},
  // Suggested regions based on user location
  suggested: [],
  // Loading states
  loading: false,
  pricingLoading: false,
  preferencesLoading: false,
  // Error state
  error: null,
  // Last fetch timestamps for cache invalidation
  lastFetch: null,
  lastPricingFetch: {},
}

const regionsSlice = createSlice({
  name: 'regions',
  initialState,
  reducers: {
    setSelectedRegion: (state, action) => {
      state.selected = action.payload
    },
    clearSelectedRegion: (state) => {
      state.selected = null
    },
    clearError: (state) => {
      state.error = null
    },
    clearPricing: (state) => {
      state.pricing = {}
      state.lastPricingFetch = {}
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Regions
      .addCase(fetchRegions.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchRegions.fulfilled, (state, action) => {
        state.loading = false
        state.available = action.payload
        state.lastFetch = Date.now()
      })
      .addCase(fetchRegions.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Region Pricing
      .addCase(fetchRegionPricing.pending, (state) => {
        state.pricingLoading = true
        state.error = null
      })
      .addCase(fetchRegionPricing.fulfilled, (state, action) => {
        state.pricingLoading = false
        const { regionId, pricing } = action.payload
        state.pricing[regionId] = pricing
        state.lastPricingFetch[regionId] = Date.now()
      })
      .addCase(fetchRegionPricing.rejected, (state, action) => {
        state.pricingLoading = false
        state.error = action.payload
      })
      // Fetch User Region Preferences
      .addCase(fetchUserRegionPreferences.pending, (state) => {
        state.preferencesLoading = true
        state.error = null
      })
      .addCase(fetchUserRegionPreferences.fulfilled, (state, action) => {
        state.preferencesLoading = false
        state.preferences = {
          preferred_region: action.payload.preferred_region || null,
          fallback_regions: action.payload.fallback_regions || [],
          data_residency_requirement: action.payload.data_residency_requirement || null,
        }
        // Auto-select preferred region if no selection made
        if (!state.selected && action.payload.preferred_region) {
          state.selected = action.payload.preferred_region
        }
      })
      .addCase(fetchUserRegionPreferences.rejected, (state, action) => {
        state.preferencesLoading = false
        state.error = action.payload
      })
      // Update User Region Preferences
      .addCase(updateUserRegionPreferences.pending, (state) => {
        state.preferencesLoading = true
        state.error = null
      })
      .addCase(updateUserRegionPreferences.fulfilled, (state, action) => {
        state.preferencesLoading = false
        state.preferences = {
          preferred_region: action.payload.preferred_region || null,
          fallback_regions: action.payload.fallback_regions || [],
          data_residency_requirement: action.payload.data_residency_requirement || null,
        }
      })
      .addCase(updateUserRegionPreferences.rejected, (state, action) => {
        state.preferencesLoading = false
        state.error = action.payload
      })
      // Fetch Suggested Regions
      .addCase(fetchSuggestedRegions.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSuggestedRegions.fulfilled, (state, action) => {
        state.loading = false
        state.suggested = action.payload
      })
      .addCase(fetchSuggestedRegions.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const {
  setSelectedRegion,
  clearSelectedRegion,
  clearError,
  clearPricing,
} = regionsSlice.actions

// Selectors
export const selectRegions = (state) => state.regions.available
export const selectSelectedRegion = (state) => state.regions.selected
export const selectRegionPreferences = (state) => state.regions.preferences
export const selectRegionPricing = (state) => state.regions.pricing
export const selectSuggestedRegions = (state) => state.regions.suggested
export const selectRegionsLoading = (state) => state.regions.loading
export const selectPricingLoading = (state) => state.regions.pricingLoading
export const selectPreferencesLoading = (state) => state.regions.preferencesLoading
export const selectRegionsError = (state) => state.regions.error
export const selectEuRegions = (state) =>
  state.regions.available.filter(r => r.is_eu === true || r.compliance_tags?.includes('GDPR'))
export const selectRegionById = (state, regionId) =>
  state.regions.available.find(r => r.id === regionId)
export const selectPricingForRegion = (state, regionId) =>
  state.regions.pricing[regionId] || null

export default regionsSlice.reducer

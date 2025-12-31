/**
 * Instances Slice - Manages GPU instances/machines state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchInstances = createAsyncThunk(
  'instances/fetchInstances',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch instances')
      }
      return data.instances || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchOffers = createAsyncThunk(
  'instances/fetchOffers',
  async (filters = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== 'any' && value !== '' && value !== null && value !== undefined && value !== false && value !== 0) {
          params.append(key, value)
        }
      })
      const res = await fetch(`${API_BASE}/api/v1/instances/offers?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch offers')
      }
      return data.offers || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const createInstance = createAsyncThunk(
  'instances/createInstance',
  async (instanceConfig, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(instanceConfig),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to create instance')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const startInstance = createAsyncThunk(
  'instances/startInstance',
  async (instanceId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances/${instanceId}/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to start instance')
      }
      return { instanceId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const stopInstance = createAsyncThunk(
  'instances/stopInstance',
  async (instanceId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances/${instanceId}/stop`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to stop instance')
      }
      return { instanceId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const destroyInstance = createAsyncThunk(
  'instances/destroyInstance',
  async (instanceId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/instances/${instanceId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to destroy instance')
      }
      return instanceId
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchMachineReliability = createAsyncThunk(
  'instances/fetchMachineReliability',
  async (machineIds = [], { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      if (Array.isArray(machineIds) && machineIds.length > 0) {
        machineIds.forEach(id => params.append('machine_id', id))
      }
      const queryString = params.toString()
      const url = queryString
        ? `${API_BASE}/api/v1/reliability/machines?${queryString}`
        : `${API_BASE}/api/v1/reliability/machines`

      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch machine reliability')
      }
      // Expected response: { reliability: { machine_id: reliabilityData, ... } }
      return data.reliability || data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const submitMachineRating = createAsyncThunk(
  'instances/submitMachineRating',
  async ({ machineId, rating, comment = '' }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/reliability/machines/${machineId}/rate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ rating, comment }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to submit rating')
      }
      return { machineId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  instances: [],
  offers: [],
  selectedOffer: null,
  stats: {
    activeMachines: 0,
    totalMachines: 0,
    dailyCost: 0,
    savings: 0,
    uptime: 0,
  },
  filters: {
    gpu_name: 'any',
    num_gpus: 1,
    min_gpu_ram: 0,
    min_cpu_cores: 1,
    min_cpu_ram: 1,
    min_disk: 50,
    max_price: 5.0,
    region: 'any',
    order_by: 'dph_total',
    limit: 100,
  },
  loading: false,
  offersLoading: false,
  error: null,
  lastFetch: null,
  // Reliability scoring state
  reliabilityData: {},        // Map of machine_id -> reliability data
  sortByReliability: false,   // Whether to sort by reliability score
  reliabilityThreshold: 70,   // Minimum reliability score threshold (0-100)
  excludeBelowThreshold: true, // Whether to exclude machines below threshold
  reliabilityLoading: false,  // Loading state for reliability data
  // Rating submission state
  ratingSubmitting: false,    // Loading state for rating submission
  ratingError: null,          // Error state for rating submission
}

const instancesSlice = createSlice({
  name: 'instances',
  initialState,
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload }
    },
    resetFilters: (state) => {
      state.filters = initialState.filters
    },
    setSelectedOffer: (state, action) => {
      state.selectedOffer = action.payload
    },
    clearSelectedOffer: (state) => {
      state.selectedOffer = null
    },
    updateInstanceStatus: (state, action) => {
      const { instanceId, status } = action.payload
      const instance = state.instances.find(i => i.id === instanceId)
      if (instance) {
        instance.status = status
      }
    },
    calculateStats: (state) => {
      const running = state.instances.filter(i => i.status === 'running')
      const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0)
      state.stats = {
        activeMachines: running.length,
        totalMachines: state.instances.length,
        dailyCost: (totalCost * 24).toFixed(2),
        savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
        uptime: running.length > 0 ? 99.9 : 0,
      }
    },
    clearError: (state) => {
      state.error = null
    },
    // Reliability scoring reducers
    setReliabilityData: (state, action) => {
      // action.payload: { machineId: reliabilityData } or { [machineId]: reliabilityData, ... }
      state.reliabilityData = { ...state.reliabilityData, ...action.payload }
    },
    updateMachineReliability: (state, action) => {
      const { machineId, data } = action.payload
      state.reliabilityData[machineId] = data
    },
    clearReliabilityData: (state) => {
      state.reliabilityData = {}
    },
    toggleReliabilitySort: (state) => {
      state.sortByReliability = !state.sortByReliability
    },
    setSortByReliability: (state, action) => {
      state.sortByReliability = action.payload
    },
    setReliabilityThreshold: (state, action) => {
      state.reliabilityThreshold = action.payload
    },
    toggleThresholdExclusion: (state) => {
      state.excludeBelowThreshold = !state.excludeBelowThreshold
    },
    setExcludeBelowThreshold: (state, action) => {
      state.excludeBelowThreshold = action.payload
    },
    setReliabilityLoading: (state, action) => {
      state.reliabilityLoading = action.payload
    },
    clearRatingError: (state) => {
      state.ratingError = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Instances
      .addCase(fetchInstances.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchInstances.fulfilled, (state, action) => {
        state.loading = false
        state.instances = action.payload
        state.lastFetch = Date.now()
        // Recalculate stats
        const running = action.payload.filter(i => i.status === 'running')
        const totalCost = running.reduce((acc, i) => acc + (i.dph_total || 0), 0)
        state.stats = {
          activeMachines: running.length,
          totalMachines: action.payload.length,
          dailyCost: (totalCost * 24).toFixed(2),
          savings: ((totalCost * 24 * 0.89) * 30).toFixed(0),
          uptime: running.length > 0 ? 99.9 : 0,
        }
      })
      .addCase(fetchInstances.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Offers
      .addCase(fetchOffers.pending, (state) => {
        state.offersLoading = true
        state.error = null
      })
      .addCase(fetchOffers.fulfilled, (state, action) => {
        state.offersLoading = false
        state.offers = action.payload
      })
      .addCase(fetchOffers.rejected, (state, action) => {
        state.offersLoading = false
        state.error = action.payload
      })
      // Create Instance
      .addCase(createInstance.pending, (state) => {
        state.loading = true
      })
      .addCase(createInstance.fulfilled, (state, action) => {
        state.loading = false
        state.instances.push(action.payload)
      })
      .addCase(createInstance.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Start Instance
      .addCase(startInstance.fulfilled, (state, action) => {
        const instance = state.instances.find(i => i.id === action.payload.instanceId)
        if (instance) {
          instance.status = 'running'
        }
      })
      // Stop Instance
      .addCase(stopInstance.fulfilled, (state, action) => {
        const instance = state.instances.find(i => i.id === action.payload.instanceId)
        if (instance) {
          instance.status = 'stopped'
        }
      })
      // Destroy Instance
      .addCase(destroyInstance.fulfilled, (state, action) => {
        state.instances = state.instances.filter(i => i.id !== action.payload)
      })
      // Fetch Machine Reliability
      .addCase(fetchMachineReliability.pending, (state) => {
        state.reliabilityLoading = true
      })
      .addCase(fetchMachineReliability.fulfilled, (state, action) => {
        state.reliabilityLoading = false
        // Merge new reliability data with existing
        state.reliabilityData = { ...state.reliabilityData, ...action.payload }
      })
      .addCase(fetchMachineReliability.rejected, (state, action) => {
        state.reliabilityLoading = false
        state.error = action.payload
      })
      // Submit Machine Rating
      .addCase(submitMachineRating.pending, (state) => {
        state.ratingSubmitting = true
        state.ratingError = null
      })
      .addCase(submitMachineRating.fulfilled, (state, action) => {
        state.ratingSubmitting = false
        // Update reliability data with new rating info if returned
        const { machineId, ...ratingData } = action.payload
        if (machineId && state.reliabilityData[machineId]) {
          state.reliabilityData[machineId] = {
            ...state.reliabilityData[machineId],
            ...ratingData,
          }
        }
      })
      .addCase(submitMachineRating.rejected, (state, action) => {
        state.ratingSubmitting = false
        state.ratingError = action.payload
      })
  },
})

export const {
  setFilters,
  resetFilters,
  setSelectedOffer,
  clearSelectedOffer,
  updateInstanceStatus,
  calculateStats,
  clearError,
  // Reliability scoring actions
  setReliabilityData,
  updateMachineReliability,
  clearReliabilityData,
  toggleReliabilitySort,
  setSortByReliability,
  setReliabilityThreshold,
  toggleThresholdExclusion,
  setExcludeBelowThreshold,
  setReliabilityLoading,
  clearRatingError,
} = instancesSlice.actions

// Selectors
export const selectInstances = (state) => state.instances.instances
export const selectOffers = (state) => state.instances.offers
export const selectSelectedOffer = (state) => state.instances.selectedOffer
export const selectInstanceStats = (state) => state.instances.stats
export const selectInstanceFilters = (state) => state.instances.filters
export const selectInstancesLoading = (state) => state.instances.loading
export const selectOffersLoading = (state) => state.instances.offersLoading
export const selectInstancesError = (state) => state.instances.error
export const selectRunningInstances = (state) =>
  state.instances.instances.filter(i => i.status === 'running')

// Reliability scoring selectors
export const selectReliabilityData = (state) => state.instances.reliabilityData
export const selectSortByReliability = (state) => state.instances.sortByReliability
export const selectReliabilityThreshold = (state) => state.instances.reliabilityThreshold
export const selectExcludeBelowThreshold = (state) => state.instances.excludeBelowThreshold
export const selectReliabilityLoading = (state) => state.instances.reliabilityLoading
export const selectMachineReliability = (machineId) => (state) =>
  state.instances.reliabilityData[machineId] || null

// Rating submission selectors
export const selectRatingSubmitting = (state) => state.instances.ratingSubmitting
export const selectRatingError = (state) => state.instances.ratingError

// Derived selector: filter offers based on reliability settings
export const selectFilteredOffersByReliability = (state) => {
  const offers = state.instances.offers
  const reliabilityData = state.instances.reliabilityData
  const threshold = state.instances.reliabilityThreshold
  const excludeBelow = state.instances.excludeBelowThreshold
  const sortByReliability = state.instances.sortByReliability

  let filteredOffers = [...offers]

  // Filter by reliability threshold if enabled
  if (excludeBelow) {
    filteredOffers = filteredOffers.filter(offer => {
      const reliability = reliabilityData[offer.machine_id]
      // If no reliability data, show the offer (don't exclude for insufficient data)
      if (!reliability) return true
      return (reliability.overall_score || reliability.reliability_score || 0) >= threshold
    })
  }

  // Sort by reliability if enabled
  if (sortByReliability) {
    filteredOffers.sort((a, b) => {
      const reliabilityA = reliabilityData[a.machine_id]
      const reliabilityB = reliabilityData[b.machine_id]
      const scoreA = reliabilityA ? (reliabilityA.overall_score || reliabilityA.reliability_score || 0) : 0
      const scoreB = reliabilityB ? (reliabilityB.overall_score || reliabilityB.reliability_score || 0) : 0
      return scoreB - scoreA // Descending order (highest first)
    })
  }

  return filteredOffers
}

export default instancesSlice.reducer

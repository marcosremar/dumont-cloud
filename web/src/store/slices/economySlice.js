/**
 * Economy Slice - Manages cost savings state for dashboard economy widget
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Polling configuration
const POLL_INTERVAL_ACTIVE = 30000 // 30 seconds when instances are active
const POLL_INTERVAL_IDLE = 60000 // 60 seconds when idle

// Polling interval reference (managed outside Redux for cleanup)
let pollingIntervalId = null

// Async thunks
export const fetchSavings = createAsyncThunk(
  'economy/fetchSavings',
  async (provider = 'AWS', { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/economy/savings?provider=${provider}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch savings')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchSavingsHistory = createAsyncThunk(
  'economy/fetchSavingsHistory',
  async ({ provider = 'AWS', days = 30 } = {}, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/economy/savings/history?provider=${provider}&days=${days}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch savings history')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchRealtimeSavings = createAsyncThunk(
  'economy/fetchRealtimeSavings',
  async (provider = 'AWS', { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/economy/savings/realtime?provider=${provider}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch realtime savings')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchActiveSession = createAsyncThunk(
  'economy/fetchActiveSession',
  async (provider = 'AWS', { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/economy/active-session?provider=${provider}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch active session')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchProviderPricing = createAsyncThunk(
  'economy/fetchProviderPricing',
  async (provider = 'AWS', { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/economy/pricing?provider=${provider}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch provider pricing')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

/**
 * Start polling for economy data updates
 * Uses adaptive intervals: 30s when instances are active, 60s when idle
 */
export const startEconomyPolling = createAsyncThunk(
  'economy/startPolling',
  async (_, { dispatch, getState }) => {
    // Clear any existing polling interval
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId)
      pollingIntervalId = null
    }

    const poll = async () => {
      const state = getState()
      const provider = state.economy.selectedProvider
      const hasActiveInstances = state.economy.activeSession.activeInstances > 0

      // Fetch active session data first to check for active instances
      await dispatch(fetchActiveSession(provider))

      // If there are active instances, also fetch realtime savings
      if (hasActiveInstances) {
        await dispatch(fetchRealtimeSavings(provider))
      }
    }

    // Do initial poll
    await poll()

    // Set up polling interval based on active instance state
    const getPollingInterval = () => {
      const state = getState()
      const hasActiveInstances = state.economy.activeSession.activeInstances > 0
      return hasActiveInstances ? POLL_INTERVAL_ACTIVE : POLL_INTERVAL_IDLE
    }

    // Create adaptive polling that adjusts interval based on active instances
    const scheduleNextPoll = () => {
      const interval = getPollingInterval()
      pollingIntervalId = setTimeout(async () => {
        const state = getState()
        // Only continue polling if we're still in polling mode
        if (state.economy.isPolling) {
          await poll()
          scheduleNextPoll()
        }
      }, interval)
    }

    scheduleNextPoll()
    return { started: true }
  }
)

/**
 * Stop polling for economy data updates
 */
export const stopEconomyPolling = createAsyncThunk(
  'economy/stopPolling',
  async () => {
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId)
      clearTimeout(pollingIntervalId)
      pollingIntervalId = null
    }
    return { stopped: true }
  }
)

const initialState = {
  // Savings data
  lifetimeSavings: 0,
  currentSessionSavings: 0,
  hourlyComparison: {
    dumontRate: 0,
    providerRate: 0,
    savingsPerHour: 0,
  },
  projections: {
    monthly: 0,
    yearly: 0,
  },
  // Provider selection
  selectedProvider: 'AWS',
  availableProviders: ['AWS', 'GCP', 'Azure'],
  // History data
  savingsHistory: [],
  // Active session data
  activeSession: {
    activeInstances: 0,
    currentCostDumont: 0,
    currentCostProvider: 0,
    sessionSavings: 0,
    sessionDuration: 0,
  },
  // Pricing data
  providerPricing: {},
  // Loading states
  loading: false,
  historyLoading: false,
  realtimeLoading: false,
  pricingLoading: false,
  // Error state
  error: null,
  // Polling state
  isPolling: false,
  pollingInterval: 30000, // 30 seconds
  // Last fetch timestamp
  lastFetch: null,
  lastRealtimeFetch: null,
}

const economySlice = createSlice({
  name: 'economy',
  initialState,
  reducers: {
    setProvider: (state, action) => {
      state.selectedProvider = action.payload
    },
    startPolling: (state) => {
      state.isPolling = true
    },
    stopPolling: (state) => {
      state.isPolling = false
    },
    setPollingInterval: (state, action) => {
      state.pollingInterval = action.payload
    },
    updateRealtimeSavings: (state, action) => {
      const { currentSessionSavings, hourlyComparison, activeSession } = action.payload
      if (currentSessionSavings !== undefined) {
        state.currentSessionSavings = currentSessionSavings
      }
      if (hourlyComparison) {
        state.hourlyComparison = { ...state.hourlyComparison, ...hourlyComparison }
      }
      if (activeSession) {
        state.activeSession = { ...state.activeSession, ...activeSession }
      }
      state.lastRealtimeFetch = Date.now()
    },
    clearError: (state) => {
      state.error = null
    },
    resetEconomy: () => initialState,
  },
  extraReducers: (builder) => {
    builder
      // Fetch Savings
      .addCase(fetchSavings.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSavings.fulfilled, (state, action) => {
        state.loading = false
        state.lifetimeSavings = action.payload.lifetime_savings || 0
        // API returns current_session_savings (not current_session)
        state.currentSessionSavings = action.payload.current_session_savings || 0
        state.hourlyComparison = {
          dumontRate: action.payload.hourly_comparison?.dumont_rate || 0,
          providerRate: action.payload.hourly_comparison?.provider_rate || 0,
          savingsPerHour: action.payload.hourly_comparison?.savings_per_hour || 0,
        }
        state.projections = {
          monthly: action.payload.projections?.monthly || 0,
          yearly: action.payload.projections?.yearly || 0,
        }
        // Update active instances count from savings response
        if (action.payload.active_instances_count !== undefined) {
          state.activeSession.activeInstances = action.payload.active_instances_count
        }
        state.lastFetch = Date.now()
      })
      .addCase(fetchSavings.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Savings History
      .addCase(fetchSavingsHistory.pending, (state) => {
        state.historyLoading = true
        state.error = null
      })
      .addCase(fetchSavingsHistory.fulfilled, (state, action) => {
        state.historyLoading = false
        state.savingsHistory = action.payload.history || []
      })
      .addCase(fetchSavingsHistory.rejected, (state, action) => {
        state.historyLoading = false
        state.error = action.payload
      })
      // Fetch Realtime Savings
      .addCase(fetchRealtimeSavings.pending, (state) => {
        state.realtimeLoading = true
      })
      .addCase(fetchRealtimeSavings.fulfilled, (state, action) => {
        state.realtimeLoading = false
        // API returns totals.total_savings for current session savings
        const totals = action.payload.totals || {}
        state.currentSessionSavings = totals.total_savings ?? state.currentSessionSavings
        // Update hourly comparison from realtime data
        if (totals.avg_savings_rate_per_hour !== undefined) {
          state.hourlyComparison = {
            ...state.hourlyComparison,
            savingsPerHour: totals.avg_savings_rate_per_hour,
          }
        }
        // API returns totals.instances_count (number), not active_instances (array)
        if (totals.instances_count !== undefined) {
          state.activeSession.activeInstances = totals.instances_count
        }
        state.lastRealtimeFetch = Date.now()
      })
      .addCase(fetchRealtimeSavings.rejected, (state, action) => {
        state.realtimeLoading = false
        state.error = action.payload
      })
      // Fetch Active Session
      .addCase(fetchActiveSession.pending, (state) => {
        state.realtimeLoading = true
      })
      .addCase(fetchActiveSession.fulfilled, (state, action) => {
        state.realtimeLoading = false
        state.activeSession = {
          // API returns instances_count (number) and active_instances (array)
          activeInstances: action.payload.instances_count || 0,
          currentCostDumont: action.payload.current_cost_dumont || 0,
          currentCostProvider: action.payload.current_cost_provider || 0,
          sessionSavings: action.payload.session_savings || 0,
          sessionDuration: action.payload.session_hours ? action.payload.session_hours * 3600 : 0,
        }
        state.lastRealtimeFetch = Date.now()
      })
      .addCase(fetchActiveSession.rejected, (state, action) => {
        state.realtimeLoading = false
        state.error = action.payload
      })
      // Fetch Provider Pricing
      .addCase(fetchProviderPricing.pending, (state) => {
        state.pricingLoading = true
        state.error = null
      })
      .addCase(fetchProviderPricing.fulfilled, (state, action) => {
        state.pricingLoading = false
        state.providerPricing = action.payload
      })
      .addCase(fetchProviderPricing.rejected, (state, action) => {
        state.pricingLoading = false
        state.error = action.payload
      })
      // Start Economy Polling
      .addCase(startEconomyPolling.pending, (state) => {
        state.isPolling = true
      })
      .addCase(startEconomyPolling.fulfilled, (state) => {
        state.isPolling = true
      })
      .addCase(startEconomyPolling.rejected, (state) => {
        state.isPolling = false
      })
      // Stop Economy Polling
      .addCase(stopEconomyPolling.fulfilled, (state) => {
        state.isPolling = false
      })
  },
})

export const {
  setProvider,
  startPolling,
  stopPolling,
  setPollingInterval,
  updateRealtimeSavings,
  clearError,
  resetEconomy,
} = economySlice.actions

// Selectors
export const selectLifetimeSavings = (state) => state.economy.lifetimeSavings
export const selectCurrentSessionSavings = (state) => state.economy.currentSessionSavings
export const selectHourlyComparison = (state) => state.economy.hourlyComparison
export const selectProjections = (state) => state.economy.projections
export const selectSelectedProvider = (state) => state.economy.selectedProvider
export const selectAvailableProviders = (state) => state.economy.availableProviders
export const selectSavingsHistory = (state) => state.economy.savingsHistory
export const selectActiveSession = (state) => state.economy.activeSession
export const selectProviderPricing = (state) => state.economy.providerPricing
export const selectEconomyLoading = (state) => state.economy.loading
export const selectHistoryLoading = (state) => state.economy.historyLoading
export const selectRealtimeLoading = (state) => state.economy.realtimeLoading
export const selectPricingLoading = (state) => state.economy.pricingLoading
export const selectEconomyError = (state) => state.economy.error
export const selectIsPolling = (state) => state.economy.isPolling
export const selectPollingInterval = (state) => state.economy.pollingInterval
export const selectLastFetch = (state) => state.economy.lastFetch

// Computed selectors
export const selectHasActiveInstances = (state) => state.economy.activeSession.activeInstances > 0
export const selectSavingsRate = (state) => state.economy.hourlyComparison.savingsPerHour

export default economySlice.reducer

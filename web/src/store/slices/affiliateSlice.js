/**
 * Affiliate Slice - Manages affiliate dashboard and payout state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks

/**
 * Fetch affiliate dashboard summary (combines all stats)
 */
export const fetchAffiliateDashboard = createAsyncThunk(
  'affiliate/fetchDashboard',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/affiliate/dashboard`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch affiliate dashboard')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch affiliate stats for a specific period
 */
export const fetchAffiliateStats = createAsyncThunk(
  'affiliate/fetchStats',
  async (period = '30d', { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/affiliate/stats?period=${period}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch affiliate stats')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch daily metrics for charts
 */
export const fetchDailyMetrics = createAsyncThunk(
  'affiliate/fetchDailyMetrics',
  async ({ startDate, endDate } = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

      const url = `${API_BASE}/api/affiliate/metrics${params.toString() ? `?${params}` : ''}`
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch daily metrics')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch payout history
 */
export const fetchPayoutHistory = createAsyncThunk(
  'affiliate/fetchPayoutHistory',
  async ({ limit = 20, offset = 0 } = {}, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/affiliate/payouts?limit=${limit}&offset=${offset}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch payout history')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Request a payout
 */
export const requestPayout = createAsyncThunk(
  'affiliate/requestPayout',
  async (payoutData, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/affiliate/payouts/request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payoutData),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to request payout')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Export affiliate data to CSV
 */
export const exportAffiliateData = createAsyncThunk(
  'affiliate/exportData',
  async ({ startDate, endDate } = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

      const url = `${API_BASE}/api/affiliate/export${params.toString() ? `?${params}` : ''}`
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })

      if (!res.ok) {
        const data = await res.json()
        return rejectWithValue(data.error || 'Failed to export data')
      }

      // Get CSV data as blob
      const blob = await res.blob()
      return { blob, filename: `affiliate-data-${new Date().toISOString().split('T')[0]}.csv` }
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

const initialState = {
  // Dashboard summary
  dashboard: {
    totalClicks: 0,
    totalSignups: 0,
    totalConversions: 0,
    conversionRate: 0,
    totalEarnings: 0,
    pendingEarnings: 0,
    paidEarnings: 0,
    lifetimeValue: 0,
  },

  // Period-specific stats
  stats: {
    period: '30d',
    clicks: 0,
    signups: 0,
    conversions: 0,
    earnings: 0,
  },

  // Daily metrics for charts
  dailyMetrics: [],

  // Payout history
  payouts: [],
  payoutsTotalCount: 0,

  // Pending payout request
  pendingPayoutRequest: null,

  // Loading states
  loading: false,
  statsLoading: false,
  metricsLoading: false,
  payoutsLoading: false,
  exportLoading: false,
  requestingPayout: false,

  // Error states
  error: null,
  statsError: null,
  metricsError: null,
  payoutsError: null,
  exportError: null,
  payoutRequestError: null,

  // Last fetch timestamp
  lastFetch: null,
}

const affiliateSlice = createSlice({
  name: 'affiliate',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
      state.statsError = null
      state.metricsError = null
      state.payoutsError = null
      state.exportError = null
      state.payoutRequestError = null
    },
    setStatsPeriod: (state, action) => {
      state.stats.period = action.payload
    },
    resetAffiliateState: (state) => {
      // Reset to initial state on logout
      Object.assign(state, initialState)
    },
    clearPayoutRequest: (state) => {
      state.pendingPayoutRequest = null
      state.payoutRequestError = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Dashboard
      .addCase(fetchAffiliateDashboard.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchAffiliateDashboard.fulfilled, (state, action) => {
        state.loading = false
        state.dashboard = {
          totalClicks: action.payload.total_clicks || 0,
          totalSignups: action.payload.total_signups || 0,
          totalConversions: action.payload.total_conversions || 0,
          conversionRate: action.payload.conversion_rate || 0,
          totalEarnings: action.payload.total_earnings || 0,
          pendingEarnings: action.payload.pending_earnings || 0,
          paidEarnings: action.payload.paid_earnings || 0,
          lifetimeValue: action.payload.lifetime_value || 0,
        }
        state.lastFetch = Date.now()
        state.error = null
      })
      .addCase(fetchAffiliateDashboard.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })

      // Fetch Stats
      .addCase(fetchAffiliateStats.pending, (state) => {
        state.statsLoading = true
        state.statsError = null
      })
      .addCase(fetchAffiliateStats.fulfilled, (state, action) => {
        state.statsLoading = false
        state.stats = {
          period: action.payload.period || state.stats.period,
          clicks: action.payload.clicks || 0,
          signups: action.payload.signups || 0,
          conversions: action.payload.conversions || 0,
          earnings: action.payload.earnings || 0,
        }
        state.statsError = null
      })
      .addCase(fetchAffiliateStats.rejected, (state, action) => {
        state.statsLoading = false
        state.statsError = action.payload
      })

      // Fetch Daily Metrics
      .addCase(fetchDailyMetrics.pending, (state) => {
        state.metricsLoading = true
        state.metricsError = null
      })
      .addCase(fetchDailyMetrics.fulfilled, (state, action) => {
        state.metricsLoading = false
        state.dailyMetrics = action.payload.metrics || []
        state.metricsError = null
      })
      .addCase(fetchDailyMetrics.rejected, (state, action) => {
        state.metricsLoading = false
        state.metricsError = action.payload
      })

      // Fetch Payout History
      .addCase(fetchPayoutHistory.pending, (state) => {
        state.payoutsLoading = true
        state.payoutsError = null
      })
      .addCase(fetchPayoutHistory.fulfilled, (state, action) => {
        state.payoutsLoading = false
        state.payouts = action.payload.payouts || []
        state.payoutsTotalCount = action.payload.total_count || 0
        state.payoutsError = null
      })
      .addCase(fetchPayoutHistory.rejected, (state, action) => {
        state.payoutsLoading = false
        state.payoutsError = action.payload
      })

      // Request Payout
      .addCase(requestPayout.pending, (state) => {
        state.requestingPayout = true
        state.payoutRequestError = null
      })
      .addCase(requestPayout.fulfilled, (state, action) => {
        state.requestingPayout = false
        state.pendingPayoutRequest = action.payload
        // Update pending/paid earnings if returned
        if (action.payload.updated_earnings) {
          state.dashboard.pendingEarnings = action.payload.updated_earnings.pending || state.dashboard.pendingEarnings
        }
        state.payoutRequestError = null
      })
      .addCase(requestPayout.rejected, (state, action) => {
        state.requestingPayout = false
        state.payoutRequestError = action.payload
      })

      // Export Data
      .addCase(exportAffiliateData.pending, (state) => {
        state.exportLoading = true
        state.exportError = null
      })
      .addCase(exportAffiliateData.fulfilled, (state) => {
        state.exportLoading = false
        state.exportError = null
      })
      .addCase(exportAffiliateData.rejected, (state, action) => {
        state.exportLoading = false
        state.exportError = action.payload
      })
  },
})

export const {
  clearError,
  setStatsPeriod,
  resetAffiliateState,
  clearPayoutRequest,
} = affiliateSlice.actions

// Selectors
export const selectAffiliateDashboard = (state) => state.affiliate.dashboard
export const selectAffiliateStats = (state) => state.affiliate.stats
export const selectDailyMetrics = (state) => state.affiliate.dailyMetrics
export const selectPayouts = (state) => state.affiliate.payouts
export const selectPayoutsTotalCount = (state) => state.affiliate.payoutsTotalCount

export const selectAffiliateLoading = (state) => state.affiliate.loading
export const selectStatsLoading = (state) => state.affiliate.statsLoading
export const selectMetricsLoading = (state) => state.affiliate.metricsLoading
export const selectPayoutsLoading = (state) => state.affiliate.payoutsLoading
export const selectExportLoading = (state) => state.affiliate.exportLoading
export const selectRequestingPayout = (state) => state.affiliate.requestingPayout

export const selectAffiliateError = (state) => state.affiliate.error
export const selectStatsError = (state) => state.affiliate.statsError
export const selectMetricsError = (state) => state.affiliate.metricsError
export const selectPayoutsError = (state) => state.affiliate.payoutsError
export const selectExportError = (state) => state.affiliate.exportError
export const selectPayoutRequestError = (state) => state.affiliate.payoutRequestError

export const selectPendingPayoutRequest = (state) => state.affiliate.pendingPayoutRequest
export const selectLastFetch = (state) => state.affiliate.lastFetch

export default affiliateSlice.reducer

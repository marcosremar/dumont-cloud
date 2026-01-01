/**
 * Reservation Slice - Manages GPU reservation state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')

const getAuthHeaders = () => {
  const token = getToken()
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

// Async thunks
export const fetchReservations = createAsyncThunk(
  'reservations/fetchReservations',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/reservations`, {
        credentials: 'include',
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch reservations')
      }
      return data.reservations || data || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchReservationStats = createAsyncThunk(
  'reservations/fetchStats',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/reservations/stats`, {
        credentials: 'include',
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch stats')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const createReservation = createAsyncThunk(
  'reservations/createReservation',
  async (reservationData, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/reservations`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify(reservationData),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to create reservation')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const cancelReservation = createAsyncThunk(
  'reservations/cancelReservation',
  async (reservationId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/reservations/${reservationId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to cancel reservation')
      }
      return { reservationId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const checkAvailability = createAsyncThunk(
  'reservations/checkAvailability',
  async ({ gpu_type, gpu_count, start_time, end_time }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        gpu_type,
        gpu_count: gpu_count.toString(),
        start_time,
        end_time,
      })
      const res = await fetch(`${API_BASE}/api/reservations/availability?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to check availability')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchPricing = createAsyncThunk(
  'reservations/fetchPricing',
  async ({ gpu_type, gpu_count, start_time, end_time }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        gpu_type,
        gpu_count: gpu_count.toString(),
        start_time,
        end_time,
      })
      const res = await fetch(`${API_BASE}/api/reservations/pricing?${params}`, {
        credentials: 'include',
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch pricing')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  reservations: [],
  stats: {
    total_reservations: 0,
    active_reservations: 0,
    pending_reservations: 0,
    total_credits_used: 0,
    total_hours_reserved: 0,
    average_discount: 0,
  },
  availability: null,
  pricing: null,
  selectedReservation: null,
  loading: false,
  statsLoading: false,
  createLoading: false,
  availabilityLoading: false,
  pricingLoading: false,
  error: null,
  lastFetch: null,
}

const reservationSlice = createSlice({
  name: 'reservations',
  initialState,
  reducers: {
    setSelectedReservation: (state, action) => {
      state.selectedReservation = action.payload
    },
    clearSelectedReservation: (state) => {
      state.selectedReservation = null
    },
    clearAvailability: (state) => {
      state.availability = null
    },
    clearPricing: (state) => {
      state.pricing = null
    },
    clearError: (state) => {
      state.error = null
    },
    updateReservationStatus: (state, action) => {
      const { reservationId, status } = action.payload
      const reservation = state.reservations.find(r => r.id === reservationId)
      if (reservation) {
        reservation.status = status
      }
    },
    // For demo/offline mode
    setDemoReservations: (state, action) => {
      state.reservations = action.payload
      state.loading = false
    },
    setDemoStats: (state, action) => {
      state.stats = action.payload
      state.statsLoading = false
    },
    addDemoReservation: (state, action) => {
      state.reservations.push(action.payload)
    },
    removeDemoReservation: (state, action) => {
      state.reservations = state.reservations.filter(r => r.id !== action.payload)
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Reservations
      .addCase(fetchReservations.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchReservations.fulfilled, (state, action) => {
        state.loading = false
        state.reservations = action.payload
        state.lastFetch = Date.now()
      })
      .addCase(fetchReservations.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Stats
      .addCase(fetchReservationStats.pending, (state) => {
        state.statsLoading = true
      })
      .addCase(fetchReservationStats.fulfilled, (state, action) => {
        state.statsLoading = false
        state.stats = action.payload
      })
      .addCase(fetchReservationStats.rejected, (state, action) => {
        state.statsLoading = false
        // Stats are optional, don't set global error
      })
      // Create Reservation
      .addCase(createReservation.pending, (state) => {
        state.createLoading = true
        state.error = null
      })
      .addCase(createReservation.fulfilled, (state, action) => {
        state.createLoading = false
        state.reservations.push(action.payload)
        // Clear availability and pricing after successful creation
        state.availability = null
        state.pricing = null
      })
      .addCase(createReservation.rejected, (state, action) => {
        state.createLoading = false
        state.error = action.payload
      })
      // Cancel Reservation
      .addCase(cancelReservation.pending, (state) => {
        state.loading = true
      })
      .addCase(cancelReservation.fulfilled, (state, action) => {
        state.loading = false
        state.reservations = state.reservations.filter(
          r => r.id !== action.payload.reservationId
        )
      })
      .addCase(cancelReservation.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Check Availability
      .addCase(checkAvailability.pending, (state) => {
        state.availabilityLoading = true
      })
      .addCase(checkAvailability.fulfilled, (state, action) => {
        state.availabilityLoading = false
        state.availability = action.payload
      })
      .addCase(checkAvailability.rejected, (state, action) => {
        state.availabilityLoading = false
        state.availability = { available: false, error: action.payload }
      })
      // Fetch Pricing
      .addCase(fetchPricing.pending, (state) => {
        state.pricingLoading = true
      })
      .addCase(fetchPricing.fulfilled, (state, action) => {
        state.pricingLoading = false
        state.pricing = action.payload
      })
      .addCase(fetchPricing.rejected, (state, action) => {
        state.pricingLoading = false
        state.pricing = null
      })
  },
})

export const {
  setSelectedReservation,
  clearSelectedReservation,
  clearAvailability,
  clearPricing,
  clearError,
  updateReservationStatus,
  setDemoReservations,
  setDemoStats,
  addDemoReservation,
  removeDemoReservation,
} = reservationSlice.actions

// Selectors
export const selectReservations = (state) => state.reservations.reservations
export const selectReservationStats = (state) => state.reservations.stats
export const selectSelectedReservation = (state) => state.reservations.selectedReservation
export const selectAvailability = (state) => state.reservations.availability
export const selectPricing = (state) => state.reservations.pricing
export const selectReservationsLoading = (state) => state.reservations.loading
export const selectStatsLoading = (state) => state.reservations.statsLoading
export const selectCreateLoading = (state) => state.reservations.createLoading
export const selectAvailabilityLoading = (state) => state.reservations.availabilityLoading
export const selectPricingLoading = (state) => state.reservations.pricingLoading
export const selectReservationsError = (state) => state.reservations.error

// Computed selectors
export const selectActiveReservations = (state) =>
  state.reservations.reservations.filter(r => r.status === 'active')

export const selectPendingReservations = (state) =>
  state.reservations.reservations.filter(r => r.status === 'pending')

export const selectCompletedReservations = (state) =>
  state.reservations.reservations.filter(r => r.status === 'completed')

export const selectUpcomingReservations = (state) => {
  const now = new Date()
  return state.reservations.reservations.filter(r => {
    const startTime = new Date(r.start_time)
    return startTime > now && (r.status === 'active' || r.status === 'pending')
  })
}

export default reservationSlice.reducer

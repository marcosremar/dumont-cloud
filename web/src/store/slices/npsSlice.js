/**
 * NPS Slice - Manages NPS survey state and admin dashboard data
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

/**
 * Get authorization headers with current token
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token')
  return {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
  }
}

// Async thunks

/**
 * Check if NPS survey should be shown to the user
 */
export const checkShouldShow = createAsyncThunk(
  'nps/checkShouldShow',
  async ({ triggerType }, { rejectWithValue }) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/nps/should-show?trigger_type=${encodeURIComponent(triggerType)}`,
        {
          headers: getAuthHeaders(),
        }
      )
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to check survey status')
      }
      return { ...data, triggerType }
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Submit NPS survey response
 */
export const submitNPS = createAsyncThunk(
  'nps/submitNPS',
  async ({ score, comment, triggerType }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nps/submit`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          score,
          comment: comment || null,
          trigger_type: triggerType,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to submit survey')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Record survey dismissal
 */
export const dismissNPS = createAsyncThunk(
  'nps/dismissNPS',
  async ({ triggerType }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nps/dismiss`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          trigger_type: triggerType,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to dismiss survey')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch NPS trends for admin dashboard
 */
export const fetchTrends = createAsyncThunk(
  'nps/fetchTrends',
  async ({ startDate, endDate } = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

      const queryString = params.toString()
      const url = `${API_BASE}/api/v1/nps/trends${queryString ? `?${queryString}` : ''}`

      const res = await fetch(url, {
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch trends')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch detractor responses for follow-up
 */
export const fetchDetractors = createAsyncThunk(
  'nps/fetchDetractors',
  async ({ pendingOnly = true, limit = 50, offset = 0 } = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        pending_only: pendingOnly.toString(),
        limit: limit.toString(),
        offset: offset.toString(),
      })

      const res = await fetch(`${API_BASE}/api/v1/nps/detractors?${params}`, {
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch detractors')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Update follow-up status for a response
 */
export const updateFollowup = createAsyncThunk(
  'nps/updateFollowup',
  async ({ responseId, followupCompleted, followupNotes }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nps/responses/${responseId}/followup`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          followup_completed: followupCompleted,
          followup_notes: followupNotes || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to update follow-up status')
      }
      return { responseId, followupCompleted, followupNotes, ...data }
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch survey configurations
 */
export const fetchConfig = createAsyncThunk(
  'nps/fetchConfig',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nps/config`, {
        headers: getAuthHeaders(),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch config')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

const initialState = {
  // Survey modal state
  isOpen: false,
  triggerType: null,
  score: null,
  comment: '',

  // Should-show check state
  shouldShow: false,
  shouldShowReason: null,
  shouldShowLoading: false,

  // Submission state
  submitting: false,
  submitSuccess: false,
  submitError: null,

  // Admin dashboard - trends
  trends: null,
  trendsLoading: false,
  trendsError: null,

  // Admin dashboard - detractors
  detractors: [],
  detractorsTotal: 0,
  detractorsLoading: false,
  detractorsError: null,

  // Config
  config: [],
  configLoading: false,
  configError: null,

  // General error state
  error: null,
}

const npsSlice = createSlice({
  name: 'nps',
  initialState,
  reducers: {
    /**
     * Open the NPS survey modal
     */
    openSurvey: (state, action) => {
      state.isOpen = true
      state.triggerType = action.payload?.triggerType || null
      state.score = null
      state.comment = ''
      state.submitSuccess = false
      state.submitError = null
    },

    /**
     * Close the NPS survey modal
     */
    closeSurvey: (state) => {
      state.isOpen = false
      state.score = null
      state.comment = ''
      state.submitSuccess = false
      state.submitError = null
    },

    /**
     * Set the selected score
     */
    setScore: (state, action) => {
      state.score = action.payload
    },

    /**
     * Set the comment text
     */
    setComment: (state, action) => {
      state.comment = action.payload
    },

    /**
     * Clear all errors
     */
    clearError: (state) => {
      state.error = null
      state.submitError = null
      state.trendsError = null
      state.detractorsError = null
      state.configError = null
    },

    /**
     * Reset survey state (after submission/dismissal)
     */
    resetSurvey: (state) => {
      state.isOpen = false
      state.triggerType = null
      state.score = null
      state.comment = ''
      state.shouldShow = false
      state.shouldShowReason = null
      state.submitSuccess = false
      state.submitError = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Check Should Show
      .addCase(checkShouldShow.pending, (state) => {
        state.shouldShowLoading = true
        state.error = null
      })
      .addCase(checkShouldShow.fulfilled, (state, action) => {
        state.shouldShowLoading = false
        state.shouldShow = action.payload.should_show
        state.shouldShowReason = action.payload.reason || null
        state.triggerType = action.payload.triggerType
        if (action.payload.should_show) {
          state.isOpen = true
        }
      })
      .addCase(checkShouldShow.rejected, (state, action) => {
        state.shouldShowLoading = false
        state.shouldShow = false
        state.error = action.payload
      })

      // Submit NPS
      .addCase(submitNPS.pending, (state) => {
        state.submitting = true
        state.submitError = null
      })
      .addCase(submitNPS.fulfilled, (state) => {
        state.submitting = false
        state.submitSuccess = true
        state.isOpen = false
        state.shouldShow = false
        state.score = null
        state.comment = ''
      })
      .addCase(submitNPS.rejected, (state, action) => {
        state.submitting = false
        state.submitError = action.payload
      })

      // Dismiss NPS
      .addCase(dismissNPS.pending, (state) => {
        state.submitting = true
      })
      .addCase(dismissNPS.fulfilled, (state) => {
        state.submitting = false
        state.isOpen = false
        state.shouldShow = false
        state.score = null
        state.comment = ''
      })
      .addCase(dismissNPS.rejected, (state, action) => {
        state.submitting = false
        // Still close the modal even if dismissal fails to record
        state.isOpen = false
        state.error = action.payload
      })

      // Fetch Trends
      .addCase(fetchTrends.pending, (state) => {
        state.trendsLoading = true
        state.trendsError = null
      })
      .addCase(fetchTrends.fulfilled, (state, action) => {
        state.trendsLoading = false
        state.trends = action.payload
      })
      .addCase(fetchTrends.rejected, (state, action) => {
        state.trendsLoading = false
        state.trendsError = action.payload
      })

      // Fetch Detractors
      .addCase(fetchDetractors.pending, (state) => {
        state.detractorsLoading = true
        state.detractorsError = null
      })
      .addCase(fetchDetractors.fulfilled, (state, action) => {
        state.detractorsLoading = false
        state.detractors = action.payload.detractors || []
        state.detractorsTotal = action.payload.count || 0
      })
      .addCase(fetchDetractors.rejected, (state, action) => {
        state.detractorsLoading = false
        state.detractorsError = action.payload
      })

      // Update Follow-up
      .addCase(updateFollowup.fulfilled, (state, action) => {
        // Update the detractor in the list if present
        const index = state.detractors.findIndex(
          d => d.id === action.payload.responseId
        )
        if (index !== -1) {
          state.detractors[index] = {
            ...state.detractors[index],
            followup_completed: action.payload.followupCompleted,
            followup_notes: action.payload.followupNotes,
          }
        }
      })

      // Fetch Config
      .addCase(fetchConfig.pending, (state) => {
        state.configLoading = true
        state.configError = null
      })
      .addCase(fetchConfig.fulfilled, (state, action) => {
        state.configLoading = false
        state.config = action.payload.configs || []
      })
      .addCase(fetchConfig.rejected, (state, action) => {
        state.configLoading = false
        state.configError = action.payload
      })
  },
})

// Export actions
export const {
  openSurvey,
  closeSurvey,
  setScore,
  setComment,
  clearError,
  resetSurvey,
} = npsSlice.actions

// Selectors
export const selectNPSIsOpen = (state) => state.nps.isOpen
export const selectNPSTriggerType = (state) => state.nps.triggerType
export const selectNPSScore = (state) => state.nps.score
export const selectNPSComment = (state) => state.nps.comment
export const selectNPSShouldShow = (state) => state.nps.shouldShow
export const selectNPSShouldShowLoading = (state) => state.nps.shouldShowLoading
export const selectNPSSubmitting = (state) => state.nps.submitting
export const selectNPSSubmitSuccess = (state) => state.nps.submitSuccess
export const selectNPSSubmitError = (state) => state.nps.submitError
export const selectNPSTrends = (state) => state.nps.trends
export const selectNPSTrendsLoading = (state) => state.nps.trendsLoading
export const selectNPSTrendsError = (state) => state.nps.trendsError
export const selectNPSDetractors = (state) => state.nps.detractors
export const selectNPSDetractorsTotal = (state) => state.nps.detractorsTotal
export const selectNPSDetractorsLoading = (state) => state.nps.detractorsLoading
export const selectNPSDetractorsError = (state) => state.nps.detractorsError
export const selectNPSConfig = (state) => state.nps.config
export const selectNPSConfigLoading = (state) => state.nps.configLoading
export const selectNPSError = (state) => state.nps.error

export default npsSlice.reducer

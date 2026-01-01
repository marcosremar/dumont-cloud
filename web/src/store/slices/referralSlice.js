/**
 * Referral Slice - Manages referral code and referral program state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks

/**
 * Fetch or create the user's referral code with stats
 */
export const fetchReferralCode = createAsyncThunk(
  'referral/fetchReferralCode',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/referral/code`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch referral code')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Validate a referral code (public endpoint for signup form)
 */
export const validateReferralCode = createAsyncThunk(
  'referral/validateReferralCode',
  async (code, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/referral/validate/${code}`)
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Invalid referral code')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Apply a referral code during signup
 */
export const applyReferralCode = createAsyncThunk(
  'referral/applyReferralCode',
  async (code, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/referral/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ code }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to apply referral code')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Fetch user's referral statistics
 */
export const fetchReferralStats = createAsyncThunk(
  'referral/fetchReferralStats',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/referral/stats`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch referral stats')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Track a click on a referral link
 */
export const trackReferralClick = createAsyncThunk(
  'referral/trackReferralClick',
  async (code, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/referral/click/${code}`, {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to track click')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

/**
 * Check if the current user was referred by someone
 */
export const fetchMyReferrer = createAsyncThunk(
  'referral/fetchMyReferrer',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/referral/my-referrer`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.error || 'Failed to fetch referrer info')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

const initialState = {
  // User's referral code
  referralCode: null,
  referralUrl: null,
  codeCreatedAt: null,

  // Referral statistics
  stats: {
    totalReferrals: 0,
    activeReferrals: 0,
    convertedReferrals: 0,
    pendingCredits: 0,
    earnedCredits: 0,
    conversionRate: 0,
  },

  // Code validation state (for signup form)
  validatedCode: null,
  validatedCodeInfo: null,

  // Applied referral code state
  appliedCode: null,
  welcomeCredit: 0,

  // Referrer info (if user was referred)
  referrer: null,
  wasReferred: false,

  // Loading states
  loading: false,
  validating: false,
  applying: false,

  // Error states
  error: null,
  validationError: null,
  applyError: null,
}

const referralSlice = createSlice({
  name: 'referral',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
      state.validationError = null
      state.applyError = null
    },
    clearValidation: (state) => {
      state.validatedCode = null
      state.validatedCodeInfo = null
      state.validationError = null
    },
    setReferralCodeFromUrl: (state, action) => {
      // Used when a referral code is extracted from URL params
      state.validatedCode = action.payload
    },
    resetReferralState: (state) => {
      // Reset to initial state on logout
      Object.assign(state, initialState)
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Referral Code
      .addCase(fetchReferralCode.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchReferralCode.fulfilled, (state, action) => {
        state.loading = false
        state.referralCode = action.payload.referral_code
        state.referralUrl = action.payload.referral_url
        state.codeCreatedAt = action.payload.created_at
        // Update stats if included in response
        if (action.payload.stats) {
          state.stats = {
            totalReferrals: action.payload.stats.total_referrals || 0,
            activeReferrals: action.payload.stats.active_referrals || 0,
            convertedReferrals: action.payload.stats.converted_referrals || 0,
            pendingCredits: action.payload.stats.pending_credits || 0,
            earnedCredits: action.payload.stats.earned_credits || 0,
            conversionRate: action.payload.stats.conversion_rate || 0,
          }
        }
        state.error = null
      })
      .addCase(fetchReferralCode.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })

      // Validate Referral Code
      .addCase(validateReferralCode.pending, (state) => {
        state.validating = true
        state.validationError = null
      })
      .addCase(validateReferralCode.fulfilled, (state, action) => {
        state.validating = false
        state.validatedCode = action.payload.code
        state.validatedCodeInfo = {
          valid: action.payload.valid,
          welcomeCredit: action.payload.welcome_credit || 10,
        }
        state.validationError = null
      })
      .addCase(validateReferralCode.rejected, (state, action) => {
        state.validating = false
        state.validatedCode = null
        state.validatedCodeInfo = null
        state.validationError = action.payload
      })

      // Apply Referral Code
      .addCase(applyReferralCode.pending, (state) => {
        state.applying = true
        state.applyError = null
      })
      .addCase(applyReferralCode.fulfilled, (state, action) => {
        state.applying = false
        state.appliedCode = action.payload.code
        state.welcomeCredit = action.payload.welcome_credit || 10
        state.wasReferred = true
        state.applyError = null
      })
      .addCase(applyReferralCode.rejected, (state, action) => {
        state.applying = false
        state.applyError = action.payload
      })

      // Fetch Referral Stats
      .addCase(fetchReferralStats.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchReferralStats.fulfilled, (state, action) => {
        state.loading = false
        state.stats = {
          totalReferrals: action.payload.total_referrals || 0,
          activeReferrals: action.payload.active_referrals || 0,
          convertedReferrals: action.payload.converted_referrals || 0,
          pendingCredits: action.payload.pending_credits || 0,
          earnedCredits: action.payload.earned_credits || 0,
          conversionRate: action.payload.conversion_rate || 0,
        }
        state.error = null
      })
      .addCase(fetchReferralStats.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })

      // Track Referral Click (no state change needed, fire and forget)
      .addCase(trackReferralClick.fulfilled, () => {
        // Click tracked successfully, no state update needed
      })

      // Fetch My Referrer
      .addCase(fetchMyReferrer.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchMyReferrer.fulfilled, (state, action) => {
        state.loading = false
        state.wasReferred = action.payload.was_referred
        state.referrer = action.payload.referrer || null
      })
      .addCase(fetchMyReferrer.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const {
  clearError,
  clearValidation,
  setReferralCodeFromUrl,
  resetReferralState,
} = referralSlice.actions

// Selectors
export const selectReferralCode = (state) => state.referral.referralCode
export const selectReferralUrl = (state) => state.referral.referralUrl
export const selectReferralStats = (state) => state.referral.stats
export const selectReferralLoading = (state) => state.referral.loading
export const selectReferralError = (state) => state.referral.error

export const selectValidatedCode = (state) => state.referral.validatedCode
export const selectValidatedCodeInfo = (state) => state.referral.validatedCodeInfo
export const selectValidating = (state) => state.referral.validating
export const selectValidationError = (state) => state.referral.validationError

export const selectAppliedCode = (state) => state.referral.appliedCode
export const selectWelcomeCredit = (state) => state.referral.welcomeCredit
export const selectApplying = (state) => state.referral.applying
export const selectApplyError = (state) => state.referral.applyError

export const selectWasReferred = (state) => state.referral.wasReferred
export const selectReferrer = (state) => state.referral.referrer

export default referralSlice.reducer

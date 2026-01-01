/**
 * Email Preferences Slice - Manages email report settings state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchEmailPreferences = createAsyncThunk(
  'emailPreferences/fetchEmailPreferences',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/email-preferences`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch email preferences')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const updateEmailPreferences = createAsyncThunk(
  'emailPreferences/updateEmailPreferences',
  async (preferences, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/email-preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(preferences),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to update email preferences')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const sendTestEmail = createAsyncThunk(
  'emailPreferences/sendTestEmail',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/email-preferences/test-email`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to send test email')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const subscribeToEmails = createAsyncThunk(
  'emailPreferences/subscribeToEmails',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/email-preferences/subscribe`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to resubscribe')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  preferences: {
    frequency: 'weekly',
    timezone: 'UTC',
    unsubscribed: false,
  },
  loading: false,
  updating: false,
  sendingTest: false,
  error: null,
  testEmailSent: false,
}

const emailPreferencesSlice = createSlice({
  name: 'emailPreferences',
  initialState,
  reducers: {
    clearEmailPreferencesError: (state) => {
      state.error = null
    },
    clearTestEmailSent: (state) => {
      state.testEmailSent = false
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Preferences
      .addCase(fetchEmailPreferences.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchEmailPreferences.fulfilled, (state, action) => {
        state.loading = false
        state.preferences = {
          frequency: action.payload.frequency || 'weekly',
          timezone: action.payload.timezone || 'UTC',
          unsubscribed: action.payload.unsubscribed || false,
        }
        state.error = null
      })
      .addCase(fetchEmailPreferences.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Update Preferences
      .addCase(updateEmailPreferences.pending, (state) => {
        state.updating = true
        state.error = null
      })
      .addCase(updateEmailPreferences.fulfilled, (state, action) => {
        state.updating = false
        state.preferences = {
          frequency: action.payload.frequency || state.preferences.frequency,
          timezone: action.payload.timezone || state.preferences.timezone,
          unsubscribed: action.payload.unsubscribed ?? state.preferences.unsubscribed,
        }
        state.error = null
      })
      .addCase(updateEmailPreferences.rejected, (state, action) => {
        state.updating = false
        state.error = action.payload
      })
      // Send Test Email
      .addCase(sendTestEmail.pending, (state) => {
        state.sendingTest = true
        state.testEmailSent = false
        state.error = null
      })
      .addCase(sendTestEmail.fulfilled, (state) => {
        state.sendingTest = false
        state.testEmailSent = true
        state.error = null
      })
      .addCase(sendTestEmail.rejected, (state, action) => {
        state.sendingTest = false
        state.testEmailSent = false
        state.error = action.payload
      })
      // Subscribe to Emails
      .addCase(subscribeToEmails.pending, (state) => {
        state.updating = true
        state.error = null
      })
      .addCase(subscribeToEmails.fulfilled, (state, action) => {
        state.updating = false
        state.preferences = {
          ...state.preferences,
          unsubscribed: false,
          frequency: action.payload.frequency || state.preferences.frequency,
        }
        state.error = null
      })
      .addCase(subscribeToEmails.rejected, (state, action) => {
        state.updating = false
        state.error = action.payload
      })
  },
})

export const { clearEmailPreferencesError, clearTestEmailSent } = emailPreferencesSlice.actions

// Selectors
export const selectEmailPreferences = (state) => state.emailPreferences.preferences
export const selectEmailPreferencesLoading = (state) => state.emailPreferences.loading
export const selectEmailPreferencesUpdating = (state) => state.emailPreferences.updating
export const selectEmailPreferencesError = (state) => state.emailPreferences.error
export const selectEmailFrequency = (state) => state.emailPreferences.preferences.frequency
export const selectEmailTimezone = (state) => state.emailPreferences.preferences.timezone
export const selectIsUnsubscribed = (state) => state.emailPreferences.preferences.unsubscribed
export const selectSendingTestEmail = (state) => state.emailPreferences.sendingTest
export const selectTestEmailSent = (state) => state.emailPreferences.testEmailSent

export default emailPreferencesSlice.reducer

/**
 * Webhooks Slice - Manages webhook configurations and delivery logs state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchWebhooks = createAsyncThunk(
  'webhooks/fetchWebhooks',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch webhooks')
      }
      return data.webhooks || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchWebhook = createAsyncThunk(
  'webhooks/fetchWebhook',
  async (webhookId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks/${webhookId}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch webhook')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const createWebhook = createAsyncThunk(
  'webhooks/createWebhook',
  async (webhookConfig, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(webhookConfig),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to create webhook')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const updateWebhook = createAsyncThunk(
  'webhooks/updateWebhook',
  async ({ webhookId, updates }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks/${webhookId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify(updates),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to update webhook')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const deleteWebhook = createAsyncThunk(
  'webhooks/deleteWebhook',
  async (webhookId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks/${webhookId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      if (!res.ok) {
        const data = await res.json()
        return rejectWithValue(data.detail || 'Failed to delete webhook')
      }
      return webhookId
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const testWebhook = createAsyncThunk(
  'webhooks/testWebhook',
  async (webhookId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks/${webhookId}/test`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to test webhook')
      }
      return { webhookId, ...data }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchWebhookLogs = createAsyncThunk(
  'webhooks/fetchWebhookLogs',
  async (webhookId, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks/${webhookId}/logs`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch webhook logs')
      }
      return { webhookId, logs: data.logs || [] }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchEventTypes = createAsyncThunk(
  'webhooks/fetchEventTypes',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/webhooks/events/types`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch event types')
      }
      return data.events || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  webhooks: [],
  selectedWebhook: null,
  logs: {},  // Map of webhookId -> logs array
  eventTypes: [],
  loading: false,
  logsLoading: false,
  testingWebhookId: null,
  error: null,
  lastFetch: null,
}

const webhooksSlice = createSlice({
  name: 'webhooks',
  initialState,
  reducers: {
    setSelectedWebhook: (state, action) => {
      state.selectedWebhook = action.payload
    },
    clearSelectedWebhook: (state) => {
      state.selectedWebhook = null
    },
    clearError: (state) => {
      state.error = null
    },
    clearLogs: (state, action) => {
      const webhookId = action.payload
      if (webhookId) {
        delete state.logs[webhookId]
      } else {
        state.logs = {}
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Webhooks
      .addCase(fetchWebhooks.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchWebhooks.fulfilled, (state, action) => {
        state.loading = false
        state.webhooks = action.payload
        state.lastFetch = Date.now()
      })
      .addCase(fetchWebhooks.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Single Webhook
      .addCase(fetchWebhook.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchWebhook.fulfilled, (state, action) => {
        state.loading = false
        state.selectedWebhook = action.payload
        // Also update in webhooks array if exists
        const index = state.webhooks.findIndex(w => w.id === action.payload.id)
        if (index !== -1) {
          state.webhooks[index] = action.payload
        }
      })
      .addCase(fetchWebhook.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Create Webhook
      .addCase(createWebhook.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createWebhook.fulfilled, (state, action) => {
        state.loading = false
        state.webhooks.push(action.payload)
      })
      .addCase(createWebhook.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Update Webhook
      .addCase(updateWebhook.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(updateWebhook.fulfilled, (state, action) => {
        state.loading = false
        const index = state.webhooks.findIndex(w => w.id === action.payload.id)
        if (index !== -1) {
          state.webhooks[index] = action.payload
        }
        if (state.selectedWebhook?.id === action.payload.id) {
          state.selectedWebhook = action.payload
        }
      })
      .addCase(updateWebhook.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Delete Webhook
      .addCase(deleteWebhook.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(deleteWebhook.fulfilled, (state, action) => {
        state.loading = false
        state.webhooks = state.webhooks.filter(w => w.id !== action.payload)
        if (state.selectedWebhook?.id === action.payload) {
          state.selectedWebhook = null
        }
        // Clear logs for deleted webhook
        delete state.logs[action.payload]
      })
      .addCase(deleteWebhook.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Test Webhook
      .addCase(testWebhook.pending, (state, action) => {
        state.testingWebhookId = action.meta.arg
        state.error = null
      })
      .addCase(testWebhook.fulfilled, (state) => {
        state.testingWebhookId = null
      })
      .addCase(testWebhook.rejected, (state, action) => {
        state.testingWebhookId = null
        state.error = action.payload
      })
      // Fetch Webhook Logs
      .addCase(fetchWebhookLogs.pending, (state) => {
        state.logsLoading = true
        state.error = null
      })
      .addCase(fetchWebhookLogs.fulfilled, (state, action) => {
        state.logsLoading = false
        state.logs[action.payload.webhookId] = action.payload.logs
      })
      .addCase(fetchWebhookLogs.rejected, (state, action) => {
        state.logsLoading = false
        state.error = action.payload
      })
      // Fetch Event Types
      .addCase(fetchEventTypes.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchEventTypes.fulfilled, (state, action) => {
        state.loading = false
        state.eventTypes = action.payload
      })
      .addCase(fetchEventTypes.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const {
  setSelectedWebhook,
  clearSelectedWebhook,
  clearError,
  clearLogs,
} = webhooksSlice.actions

// Selectors
export const selectWebhooks = (state) => state.webhooks.webhooks
export const selectSelectedWebhook = (state) => state.webhooks.selectedWebhook
export const selectWebhookLogs = (webhookId) => (state) => state.webhooks.logs[webhookId] || []
export const selectEventTypes = (state) => state.webhooks.eventTypes
export const selectWebhooksLoading = (state) => state.webhooks.loading
export const selectLogsLoading = (state) => state.webhooks.logsLoading
export const selectTestingWebhookId = (state) => state.webhooks.testingWebhookId
export const selectWebhooksError = (state) => state.webhooks.error
export const selectEnabledWebhooks = (state) =>
  state.webhooks.webhooks.filter(w => w.enabled)

export default webhooksSlice.reducer

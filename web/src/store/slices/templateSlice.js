/**
 * Templates Slice - Manages template marketplace state
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

const getToken = () => localStorage.getItem('auth_token')

// Async thunks
export const fetchTemplates = createAsyncThunk(
  'templates/fetchTemplates',
  async (filters = {}, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '' && value !== false) {
          params.append(key, value)
        }
      })
      const queryString = params.toString()
      const url = queryString
        ? `${API_BASE}/api/templates?${queryString}`
        : `${API_BASE}/api/templates`
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch templates')
      }
      return data.templates || data || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchTemplateBySlug = createAsyncThunk(
  'templates/fetchTemplateBySlug',
  async (slug, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/templates/${slug}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch template')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const fetchTemplateOffers = createAsyncThunk(
  'templates/fetchTemplateOffers',
  async (slug, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/templates/${slug}/offers`, {
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch template offers')
      }
      return data.offers || []
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

export const deployTemplate = createAsyncThunk(
  'templates/deployTemplate',
  async ({ slug, gpuId, options = {} }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/api/templates/${slug}/deploy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ offer_id: gpuId, ...options }),
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to deploy template')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)

const initialState = {
  templates: [],
  selectedTemplate: null,
  offers: [],
  selectedOffer: null,
  filters: {
    min_vram: null,
    category: null,
    verified_only: false,
  },
  deployment: {
    status: 'idle', // idle, deploying, succeeded, failed
    result: null,
    error: null,
  },
  loading: false,
  offersLoading: false,
  error: null,
  lastFetch: null,
}

const templateSlice = createSlice({
  name: 'templates',
  initialState,
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload }
    },
    resetFilters: (state) => {
      state.filters = initialState.filters
    },
    setSelectedTemplate: (state, action) => {
      state.selectedTemplate = action.payload
    },
    clearSelectedTemplate: (state) => {
      state.selectedTemplate = null
      state.offers = []
      state.selectedOffer = null
    },
    setSelectedOffer: (state, action) => {
      state.selectedOffer = action.payload
    },
    clearSelectedOffer: (state) => {
      state.selectedOffer = null
    },
    resetDeployment: (state) => {
      state.deployment = initialState.deployment
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Templates
      .addCase(fetchTemplates.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTemplates.fulfilled, (state, action) => {
        state.loading = false
        state.templates = action.payload
        state.lastFetch = Date.now()
      })
      .addCase(fetchTemplates.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Template By Slug
      .addCase(fetchTemplateBySlug.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTemplateBySlug.fulfilled, (state, action) => {
        state.loading = false
        state.selectedTemplate = action.payload
      })
      .addCase(fetchTemplateBySlug.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
      // Fetch Template Offers
      .addCase(fetchTemplateOffers.pending, (state) => {
        state.offersLoading = true
        state.error = null
      })
      .addCase(fetchTemplateOffers.fulfilled, (state, action) => {
        state.offersLoading = false
        state.offers = action.payload
      })
      .addCase(fetchTemplateOffers.rejected, (state, action) => {
        state.offersLoading = false
        state.error = action.payload
      })
      // Deploy Template
      .addCase(deployTemplate.pending, (state) => {
        state.deployment.status = 'deploying'
        state.deployment.error = null
        state.deployment.result = null
      })
      .addCase(deployTemplate.fulfilled, (state, action) => {
        state.deployment.status = 'succeeded'
        state.deployment.result = action.payload
      })
      .addCase(deployTemplate.rejected, (state, action) => {
        state.deployment.status = 'failed'
        state.deployment.error = action.payload
      })
  },
})

export const {
  setFilters,
  resetFilters,
  setSelectedTemplate,
  clearSelectedTemplate,
  setSelectedOffer,
  clearSelectedOffer,
  resetDeployment,
  clearError,
} = templateSlice.actions

// Selectors
export const selectTemplates = (state) => state.templates.templates
export const selectSelectedTemplate = (state) => state.templates.selectedTemplate
export const selectTemplateOffers = (state) => state.templates.offers
export const selectSelectedOffer = (state) => state.templates.selectedOffer
export const selectTemplateFilters = (state) => state.templates.filters
export const selectTemplatesLoading = (state) => state.templates.loading
export const selectOffersLoading = (state) => state.templates.offersLoading
export const selectTemplatesError = (state) => state.templates.error
export const selectDeployment = (state) => state.templates.deployment
export const selectDeploymentStatus = (state) => state.templates.deployment.status
export const selectDeploymentResult = (state) => state.templates.deployment.result

// Derived selectors
export const selectTemplatesByCategory = (state, category) =>
  state.templates.templates.filter(t => t.category === category)

export const selectVerifiedTemplates = (state) =>
  state.templates.templates.filter(t => t.verified)

export default templateSlice.reducer

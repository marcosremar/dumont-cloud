/**
 * Currency Slice - Manages currency state for multi-currency pricing
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

const API_BASE = import.meta.env.VITE_API_URL || ''

// Supported currencies
export const SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'BRL']

// Async thunks
export const fetchExchangeRates = createAsyncThunk(
  'currency/fetchExchangeRates',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/v1/currency/rates`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      })
      const data = await res.json()
      if (!res.ok) {
        return rejectWithValue(data.detail || 'Failed to fetch exchange rates')
      }
      return data
    } catch (error) {
      return rejectWithValue(error.message || 'Connection error')
    }
  }
)

export const fetchUserCurrencyPreference = createAsyncThunk(
  'currency/fetchUserCurrencyPreference',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('auth_token')
      if (!token) {
        // Return localStorage preference if not authenticated
        const stored = localStorage.getItem('preferredCurrency')
        return { currency: stored || 'USD' }
      }
      const res = await fetch(`${API_BASE}/api/v1/currency/preference`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      const data = await res.json()
      if (!res.ok) {
        // Fallback to localStorage if API fails
        const stored = localStorage.getItem('preferredCurrency')
        return { currency: stored || 'USD' }
      }
      return data
    } catch (error) {
      // Fallback to localStorage on error
      const stored = localStorage.getItem('preferredCurrency')
      return { currency: stored || 'USD' }
    }
  }
)

export const setUserCurrencyPreference = createAsyncThunk(
  'currency/setUserCurrencyPreference',
  async (currency, { rejectWithValue }) => {
    try {
      // Validate currency
      if (!SUPPORTED_CURRENCIES.includes(currency)) {
        return rejectWithValue('Invalid currency code')
      }

      // Always save to localStorage
      localStorage.setItem('preferredCurrency', currency)

      const token = localStorage.getItem('auth_token')
      if (!token) {
        // Not authenticated, just use localStorage
        return { currency }
      }

      const res = await fetch(`${API_BASE}/api/v1/currency/preference`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ currency }),
      })
      const data = await res.json()
      if (!res.ok) {
        // Still return success since localStorage was updated
        return { currency }
      }
      return data
    } catch (error) {
      // Still return success since localStorage was updated
      return { currency }
    }
  }
)

// Get initial currency from localStorage or default to USD
const getInitialCurrency = () => {
  const stored = localStorage.getItem('preferredCurrency')
  if (stored && SUPPORTED_CURRENCIES.includes(stored)) {
    return stored
  }
  return 'USD'
}

const initialState = {
  selectedCurrency: getInitialCurrency(),
  exchangeRates: {},
  lastUpdated: null,
  isStale: false,
  loading: false,
  error: null,
  initialized: false,
}

const currencySlice = createSlice({
  name: 'currency',
  initialState,
  reducers: {
    setCurrency: (state, action) => {
      const currency = action.payload
      if (SUPPORTED_CURRENCIES.includes(currency)) {
        state.selectedCurrency = currency
        localStorage.setItem('preferredCurrency', currency)
      }
    },
    setExchangeRates: (state, action) => {
      state.exchangeRates = action.payload.rates
      state.lastUpdated = action.payload.timestamp
      state.isStale = action.payload.isStale || false
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Exchange Rates
      .addCase(fetchExchangeRates.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchExchangeRates.fulfilled, (state, action) => {
        state.loading = false
        state.exchangeRates = action.payload.rates || {}
        state.lastUpdated = action.payload.updated_at || new Date().toISOString()
        state.isStale = action.payload.is_stale || false
        state.initialized = true
        state.error = null
      })
      .addCase(fetchExchangeRates.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
        state.initialized = true
      })
      // Fetch User Currency Preference
      .addCase(fetchUserCurrencyPreference.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchUserCurrencyPreference.fulfilled, (state, action) => {
        state.loading = false
        const currency = action.payload.currency
        if (SUPPORTED_CURRENCIES.includes(currency)) {
          state.selectedCurrency = currency
          localStorage.setItem('preferredCurrency', currency)
        }
      })
      .addCase(fetchUserCurrencyPreference.rejected, (state) => {
        state.loading = false
        // Keep current selection on failure
      })
      // Set User Currency Preference
      .addCase(setUserCurrencyPreference.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(setUserCurrencyPreference.fulfilled, (state, action) => {
        state.loading = false
        const currency = action.payload.currency
        if (SUPPORTED_CURRENCIES.includes(currency)) {
          state.selectedCurrency = currency
        }
        state.error = null
      })
      .addCase(setUserCurrencyPreference.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  },
})

export const { setCurrency, setExchangeRates, clearError } = currencySlice.actions

// Selectors
export const selectSelectedCurrency = (state) => state.currency.selectedCurrency
export const selectExchangeRates = (state) => state.currency.exchangeRates
export const selectExchangeRate = (currency) => (state) => {
  if (currency === 'USD') return 1
  return state.currency.exchangeRates[currency] || 1
}
export const selectCurrencyLastUpdated = (state) => state.currency.lastUpdated
export const selectCurrencyIsStale = (state) => state.currency.isStale
export const selectCurrencyLoading = (state) => state.currency.loading
export const selectCurrencyError = (state) => state.currency.error
export const selectCurrencyInitialized = (state) => state.currency.initialized

export default currencySlice.reducer

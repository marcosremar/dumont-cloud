/**
 * Tests for regionsSlice
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { configureStore } from '@reduxjs/toolkit'
import regionsReducer, {
  fetchRegions,
  fetchRegionPricing,
  fetchUserRegionPreferences,
  updateUserRegionPreferences,
  fetchSuggestedRegions,
  setSelectedRegion,
  clearSelectedRegion,
  clearError,
  clearPricing,
  selectRegions,
  selectSelectedRegion,
  selectRegionPreferences,
  selectRegionPricing,
  selectSuggestedRegions,
  selectRegionsLoading,
  selectPricingLoading,
  selectPreferencesLoading,
  selectRegionsError,
  selectEuRegions,
  selectRegionById,
  selectPricingForRegion,
} from './regionsSlice'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(() => 'mock_token'),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
global.localStorage = mockLocalStorage

// Helper to create a test store
const createTestStore = (preloadedState = {}) => {
  return configureStore({
    reducer: {
      regions: regionsReducer,
    },
    preloadedState,
  })
}

describe('regionsSlice', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockReset()
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const store = createTestStore()
      const state = store.getState().regions

      expect(state.available).toEqual([])
      expect(state.selected).toBeNull()
      expect(state.preferences).toEqual({
        preferred_region: null,
        fallback_regions: [],
        data_residency_requirement: null,
      })
      expect(state.pricing).toEqual({})
      expect(state.suggested).toEqual([])
      expect(state.loading).toBe(false)
      expect(state.pricingLoading).toBe(false)
      expect(state.preferencesLoading).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('reducers', () => {
    it('should handle setSelectedRegion', () => {
      const store = createTestStore()
      store.dispatch(setSelectedRegion('eu-west'))
      expect(store.getState().regions.selected).toBe('eu-west')
    })

    it('should handle clearSelectedRegion', () => {
      const store = createTestStore({
        regions: { ...createTestStore().getState().regions, selected: 'eu-west' },
      })
      store.dispatch(clearSelectedRegion())
      expect(store.getState().regions.selected).toBeNull()
    })

    it('should handle clearError', () => {
      const store = createTestStore({
        regions: { ...createTestStore().getState().regions, error: 'Some error' },
      })
      store.dispatch(clearError())
      expect(store.getState().regions.error).toBeNull()
    })

    it('should handle clearPricing', () => {
      const store = createTestStore({
        regions: {
          ...createTestStore().getState().regions,
          pricing: { 'eu-west': { compute_price: 0.5 } },
          lastPricingFetch: { 'eu-west': Date.now() },
        },
      })
      store.dispatch(clearPricing())
      expect(store.getState().regions.pricing).toEqual({})
      expect(store.getState().regions.lastPricingFetch).toEqual({})
    })
  })

  describe('fetchRegions thunk', () => {
    it('should handle fetchRegions.pending', () => {
      const store = createTestStore()
      store.dispatch({ type: fetchRegions.pending.type })
      expect(store.getState().regions.loading).toBe(true)
      expect(store.getState().regions.error).toBeNull()
    })

    it('should handle fetchRegions.fulfilled', async () => {
      const mockRegions = [
        { id: 'eu-west', name: 'EU West', is_eu: true },
        { id: 'us-east', name: 'US East', is_eu: false },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ regions: mockRegions }),
      })

      const store = createTestStore()
      await store.dispatch(fetchRegions())

      const state = store.getState().regions
      expect(state.loading).toBe(false)
      expect(state.available).toEqual(mockRegions)
      expect(state.lastFetch).toBeDefined()
    })

    it('should handle fetchRegions.rejected', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'API Error' }),
      })

      const store = createTestStore()
      await store.dispatch(fetchRegions())

      const state = store.getState().regions
      expect(state.loading).toBe(false)
      expect(state.error).toBe('API Error')
    })

    it('should handle fetch error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const store = createTestStore()
      await store.dispatch(fetchRegions())

      const state = store.getState().regions
      expect(state.loading).toBe(false)
      expect(state.error).toBe('Network error')
    })
  })

  describe('fetchRegionPricing thunk', () => {
    it('should handle fetchRegionPricing.pending', () => {
      const store = createTestStore()
      store.dispatch({ type: fetchRegionPricing.pending.type })
      expect(store.getState().regions.pricingLoading).toBe(true)
    })

    it('should handle fetchRegionPricing.fulfilled', async () => {
      const mockPricing = {
        compute_price: 0.5,
        storage_price: 0.1,
        currency: 'USD',
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPricing),
      })

      const store = createTestStore()
      await store.dispatch(fetchRegionPricing('eu-west'))

      const state = store.getState().regions
      expect(state.pricingLoading).toBe(false)
      expect(state.pricing['eu-west']).toEqual(mockPricing)
      expect(state.lastPricingFetch['eu-west']).toBeDefined()
    })

    it('should handle fetchRegionPricing.rejected', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Pricing error' }),
      })

      const store = createTestStore()
      await store.dispatch(fetchRegionPricing('eu-west'))

      const state = store.getState().regions
      expect(state.pricingLoading).toBe(false)
      expect(state.error).toBe('Pricing error')
    })
  })

  describe('fetchUserRegionPreferences thunk', () => {
    it('should handle fetchUserRegionPreferences.fulfilled', async () => {
      const mockPreferences = {
        preferred_region: 'eu-west',
        fallback_regions: ['us-east', 'us-west'],
        data_residency_requirement: 'EU_GDPR',
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPreferences),
      })

      const store = createTestStore()
      await store.dispatch(fetchUserRegionPreferences())

      const state = store.getState().regions
      expect(state.preferencesLoading).toBe(false)
      expect(state.preferences).toEqual(mockPreferences)
      // Auto-select preferred region when no selection made
      expect(state.selected).toBe('eu-west')
    })

    it('should not auto-select if region already selected', async () => {
      const mockPreferences = {
        preferred_region: 'eu-west',
        fallback_regions: [],
        data_residency_requirement: null,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPreferences),
      })

      const store = createTestStore({
        regions: {
          ...createTestStore().getState().regions,
          selected: 'us-east',
        },
      })
      await store.dispatch(fetchUserRegionPreferences())

      const state = store.getState().regions
      // Should keep existing selection
      expect(state.selected).toBe('us-east')
    })
  })

  describe('updateUserRegionPreferences thunk', () => {
    it('should handle updateUserRegionPreferences.fulfilled', async () => {
      const updatedPreferences = {
        preferred_region: 'us-west',
        fallback_regions: ['eu-west'],
        data_residency_requirement: 'US_ONLY',
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(updatedPreferences),
      })

      const store = createTestStore()
      await store.dispatch(updateUserRegionPreferences(updatedPreferences))

      const state = store.getState().regions
      expect(state.preferencesLoading).toBe(false)
      expect(state.preferences).toEqual(updatedPreferences)
    })
  })

  describe('fetchSuggestedRegions thunk', () => {
    it('should handle fetchSuggestedRegions.fulfilled', async () => {
      const mockSuggested = [
        { id: 'eu-west', name: 'EU West', distance_km: 100 },
        { id: 'eu-central', name: 'EU Central', distance_km: 500 },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ suggested_regions: mockSuggested }),
      })

      const store = createTestStore()
      await store.dispatch(fetchSuggestedRegions())

      const state = store.getState().regions
      expect(state.loading).toBe(false)
      expect(state.suggested).toEqual(mockSuggested)
    })
  })

  describe('selectors', () => {
    const mockState = {
      regions: {
        available: [
          { id: 'eu-west', name: 'EU West', is_eu: true, compliance_tags: ['GDPR'] },
          { id: 'us-east', name: 'US East', is_eu: false },
          { id: 'eu-central', name: 'EU Central', is_eu: true },
        ],
        selected: 'eu-west',
        preferences: {
          preferred_region: 'eu-west',
          fallback_regions: ['eu-central'],
          data_residency_requirement: 'EU_GDPR',
        },
        pricing: {
          'eu-west': { compute_price: 0.5 },
          'us-east': { compute_price: 0.4 },
        },
        suggested: [{ id: 'eu-west', name: 'EU West' }],
        loading: false,
        pricingLoading: false,
        preferencesLoading: false,
        error: null,
        lastFetch: Date.now(),
        lastPricingFetch: {},
      },
    }

    it('selectRegions should return available regions', () => {
      expect(selectRegions(mockState)).toEqual(mockState.regions.available)
    })

    it('selectSelectedRegion should return selected region', () => {
      expect(selectSelectedRegion(mockState)).toBe('eu-west')
    })

    it('selectRegionPreferences should return preferences', () => {
      expect(selectRegionPreferences(mockState)).toEqual(mockState.regions.preferences)
    })

    it('selectRegionPricing should return all pricing data', () => {
      expect(selectRegionPricing(mockState)).toEqual(mockState.regions.pricing)
    })

    it('selectSuggestedRegions should return suggested regions', () => {
      expect(selectSuggestedRegions(mockState)).toEqual(mockState.regions.suggested)
    })

    it('selectRegionsLoading should return loading state', () => {
      expect(selectRegionsLoading(mockState)).toBe(false)
    })

    it('selectPricingLoading should return pricing loading state', () => {
      expect(selectPricingLoading(mockState)).toBe(false)
    })

    it('selectPreferencesLoading should return preferences loading state', () => {
      expect(selectPreferencesLoading(mockState)).toBe(false)
    })

    it('selectRegionsError should return error state', () => {
      expect(selectRegionsError(mockState)).toBeNull()
    })

    it('selectEuRegions should return only EU regions', () => {
      const euRegions = selectEuRegions(mockState)
      expect(euRegions).toHaveLength(2)
      expect(euRegions.every((r) => r.is_eu === true || r.compliance_tags?.includes('GDPR'))).toBe(
        true
      )
    })

    it('selectRegionById should return correct region', () => {
      expect(selectRegionById(mockState, 'eu-west')).toEqual(mockState.regions.available[0])
      expect(selectRegionById(mockState, 'nonexistent')).toBeUndefined()
    })

    it('selectPricingForRegion should return pricing for specific region', () => {
      expect(selectPricingForRegion(mockState, 'eu-west')).toEqual({ compute_price: 0.5 })
      expect(selectPricingForRegion(mockState, 'nonexistent')).toBeNull()
    })
  })
})

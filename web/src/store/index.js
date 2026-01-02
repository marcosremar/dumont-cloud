/**
 * Redux Store Configuration
 * Central state management for DumontCloud
 */
import { configureStore } from '@reduxjs/toolkit'
import authSlice from './slices/authSlice'
import userSlice from './slices/userSlice'
import instancesSlice from './slices/instancesSlice'
import uiSlice from './slices/uiSlice'
import npsSlice from './slices/npsSlice'
import currencySlice from './slices/currencySlice'
import regionsSlice from './slices/regionsSlice'
import economySlice from './slices/economySlice'
import templateSlice from './slices/templateSlice'
import affiliateSlice from './slices/affiliateSlice'
import referralSlice from './slices/referralSlice'
import emailPreferencesSlice from './slices/emailPreferencesSlice'
import webhooksSlice from './slices/webhooksSlice'

export const store = configureStore({
  reducer: {
    auth: authSlice,
    user: userSlice,
    instances: instancesSlice,
    ui: uiSlice,
    nps: npsSlice,
    currency: currencySlice,
    regions: regionsSlice,
    economy: economySlice,
    templates: templateSlice,
    affiliate: affiliateSlice,
    referral: referralSlice,
    emailPreferences: emailPreferencesSlice,
    webhooks: webhooksSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serialization check
        ignoredActions: ['instances/setSelectedOffer'],
      },
    }),
  devTools: import.meta.env.DEV,
})

// Infer the `RootState` and `AppDispatch` types from the store itself
export const RootState = store.getState
export const AppDispatch = store.dispatch

export default store

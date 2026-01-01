/**
 * Redux Store Configuration
 * Central state management for DumontCloud
 */
import { configureStore } from '@reduxjs/toolkit'
import authSlice from './slices/authSlice'
import userSlice from './slices/userSlice'
import instancesSlice from './slices/instancesSlice'
import uiSlice from './slices/uiSlice'
import economySlice from './slices/economySlice'
import templateReducer from './slices/templateSlice'
import emailPreferencesSlice from './slices/emailPreferencesSlice'
import npsSlice from './slices/npsSlice'
import webhooksSlice from './slices/webhooksSlice'
import referralSlice from './slices/referralSlice'
import affiliateSlice from './slices/affiliateSlice'
import currencySlice from './slices/currencySlice'
import reservationSlice from './reservationSlice'
import regionsSlice from './slices/regionsSlice'

export const store = configureStore({
  reducer: {
    auth: authSlice,
    user: userSlice,
    instances: instancesSlice,
    ui: uiSlice,
    economy: economySlice,
    templates: templateReducer,
    emailPreferences: emailPreferencesSlice,
    nps: npsSlice,
    webhooks: webhooksSlice,
    referral: referralSlice,
    affiliate: affiliateSlice,
    currency: currencySlice,
    reservations: reservationSlice,
    regions: regionsSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serialization check
        ignoredActions: ['instances/setSelectedOffer', 'affiliate/exportData/fulfilled'],
      },
    }),
  devTools: import.meta.env.DEV,
})

// Infer the `RootState` and `AppDispatch` types from the store itself
export const RootState = store.getState
export const AppDispatch = store.dispatch

export default store

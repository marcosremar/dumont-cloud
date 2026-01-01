import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import HttpBackend from 'i18next-http-backend'

// Initialize i18next with React integration and HTTP backend for lazy loading translations
i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    // Get language from localStorage or default to English
    lng: localStorage.getItem('language') || 'en',
    fallbackLng: 'en',

    // Supported languages
    supportedLngs: ['en', 'es'],

    // Don't load missing keys from fallback when running
    load: 'languageOnly',

    // React already handles XSS protection, disable escaping to avoid double-escaping
    interpolation: {
      escapeValue: false,
    },

    // HTTP backend configuration for loading translation files
    backend: {
      loadPath: '/locales/{{lng}}/translation.json',
    },

    // Debug mode - disabled in production
    debug: import.meta.env.DEV,

    // React Suspense integration
    react: {
      useSuspense: false, // Disable suspense to avoid loading states on language switch
    },
  })

export default i18n

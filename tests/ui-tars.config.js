/**
 * UI-TARS Configuration
 *
 * AI-powered testing framework using ByteDance's UI-TARS
 * with OpenRouter API (much cheaper than proprietary solutions)
 */

module.exports = {
  // OpenRouter API configuration
  model: {
    baseURL: 'https://openrouter.ai/api/v1',
    apiKey: process.env.OPENROUTER_API_KEY,
    // Using Google Gemini 3 Flash Preview (latest, fastest)
    model: 'google/gemini-3-flash-preview',
  },

  // Browser configuration
  browser: {
    headless: true,   // Run in headless mode (faster)
    slowMo: 0,        // No slow down in headless
  },

  // Timeouts
  timeouts: {
    action: 30000,    // 30s for AI actions
    assertion: 10000  // 10s for AI assertions
  }
};

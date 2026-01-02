/**
 * Midscene.js Configuration with Z.ai GLM-4V-Plus
 *
 * Using GLM-4V-Plus - Ultra cheap Chinese vision model
 * Even cheaper than OpenRouter Gemini
 */

module.exports = {
  // AI Model configuration using Z.ai
  aiConfig: {
    // Z.ai endpoint (OpenAI-compatible)
    apiUrl: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',

    // API key from environment
    apiKey: process.env.ZAI_API_KEY,

    // Model to use (GLM-4V - vision model)
    model: 'glm-4v',

    // Optional: Additional headers
    headers: {
      'Content-Type': 'application/json'
    }
  },

  // Browser configuration
  browserConfig: {
    headless: true,     // Run in headless mode
    slowMo: 0,          // No slow down
  },

  // Timeouts
  timeouts: {
    action: 30000,      // 30s for AI actions
    assertion: 10000,   // 10s for assertions
    navigation: 30000   // 30s for navigation
  },

  // Screenshot settings
  screenshot: {
    enabled: true,
    quality: 80,        // 80% quality to save bandwidth
  },

  // Logging
  logging: {
    level: 'info',      // info, debug, warn, error
    verbose: false
  }
};

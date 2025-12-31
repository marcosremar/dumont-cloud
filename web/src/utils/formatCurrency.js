/**
 * Currency Formatting Utility
 *
 * Provides currency formatting and conversion functions for multi-currency pricing.
 * Uses native Intl.NumberFormat for consistent locale-aware formatting.
 */

// Supported currencies with their configuration
export const CURRENCY_CONFIG = {
  USD: { code: 'USD', symbol: '$', locale: 'en-US', exponent: 2 },
  EUR: { code: 'EUR', symbol: '€', locale: 'de-DE', exponent: 2 },
  GBP: { code: 'GBP', symbol: '£', locale: 'en-GB', exponent: 2 },
  BRL: { code: 'BRL', symbol: 'R$', locale: 'pt-BR', exponent: 2 },
}

// List of supported currency codes
export const SUPPORTED_CURRENCIES = Object.keys(CURRENCY_CONFIG)

/**
 * Format a price in the specified currency
 *
 * @param {number} amountInCents - Amount in cents (integer)
 * @param {string} currencyCode - ISO 4217 currency code (USD, EUR, GBP, BRL)
 * @param {Object} options - Optional formatting options
 * @param {boolean} options.showSymbol - Include currency symbol (default: true)
 * @param {boolean} options.showCode - Include currency code after amount (default: false)
 * @returns {string} Formatted price string
 */
export function formatPrice(amountInCents, currencyCode = 'USD', options = {}) {
  const { showSymbol = true, showCode = false } = options

  // Validate currency code
  const config = CURRENCY_CONFIG[currencyCode]
  if (!config) {
    // Fallback to USD for invalid currency codes
    return formatPrice(amountInCents, 'USD', options)
  }

  // Convert cents to decimal amount
  const amount = amountInCents / Math.pow(10, config.exponent)

  // Handle edge cases
  if (!Number.isFinite(amount)) {
    return showSymbol ? `${config.symbol}0.00` : '0.00'
  }

  try {
    const formatter = new Intl.NumberFormat(config.locale, {
      style: 'currency',
      currency: currencyCode,
      currencyDisplay: showSymbol ? 'symbol' : 'code',
      minimumFractionDigits: config.exponent,
      maximumFractionDigits: config.exponent,
    })

    let formatted = formatter.format(amount)

    // If showCode is true and showSymbol is true, append code
    if (showCode && showSymbol) {
      formatted = `${formatted} ${currencyCode}`
    }

    return formatted
  } catch (error) {
    // Fallback formatting if Intl fails
    const fixed = Math.abs(amount).toFixed(config.exponent)
    const sign = amount < 0 ? '-' : ''
    return showSymbol ? `${sign}${config.symbol}${fixed}` : `${sign}${fixed}`
  }
}

/**
 * Format a decimal amount (not cents) in the specified currency
 *
 * @param {number} amount - Amount as decimal (e.g., 10.50)
 * @param {string} currencyCode - ISO 4217 currency code
 * @param {Object} options - Optional formatting options
 * @returns {string} Formatted price string
 */
export function formatAmount(amount, currencyCode = 'USD', options = {}) {
  const config = CURRENCY_CONFIG[currencyCode] || CURRENCY_CONFIG.USD
  const amountInCents = Math.round(amount * Math.pow(10, config.exponent))
  return formatPrice(amountInCents, currencyCode, options)
}

/**
 * Convert price from one currency to another
 *
 * @param {number} baseAmountInCents - Amount in cents in the source currency
 * @param {string} fromCurrency - Source currency code
 * @param {string} toCurrency - Target currency code
 * @param {number} exchangeRate - Exchange rate from source to target currency
 * @returns {number} Converted amount in cents (rounded to nearest cent)
 */
export function convertPrice(baseAmountInCents, fromCurrency, toCurrency, exchangeRate) {
  // Same currency, no conversion needed
  if (fromCurrency === toCurrency) {
    return baseAmountInCents
  }

  // Validate input
  if (!Number.isFinite(baseAmountInCents) || !Number.isFinite(exchangeRate)) {
    return baseAmountInCents
  }

  // Validate non-negative rate
  if (exchangeRate <= 0) {
    return baseAmountInCents
  }

  // Convert and round using banker's rounding (round half to even)
  const convertedAmount = baseAmountInCents * exchangeRate
  return bankersRound(convertedAmount)
}

/**
 * Convert and format price in one step
 *
 * @param {number} baseAmountInCents - Amount in cents in USD (base currency)
 * @param {string} toCurrency - Target currency code
 * @param {number} exchangeRate - Exchange rate from USD to target currency
 * @param {Object} options - Formatting options
 * @returns {string} Formatted converted price
 */
export function convertAndFormatPrice(baseAmountInCents, toCurrency, exchangeRate, options = {}) {
  const convertedCents = convertPrice(baseAmountInCents, 'USD', toCurrency, exchangeRate)
  return formatPrice(convertedCents, toCurrency, options)
}

/**
 * Banker's rounding (round half to even)
 * Minimizes cumulative rounding errors
 *
 * @param {number} value - Value to round
 * @returns {number} Rounded integer
 */
function bankersRound(value) {
  const floor = Math.floor(value)
  const decimal = value - floor

  // Standard rounding for clear cases
  if (decimal < 0.5) {
    return floor
  }
  if (decimal > 0.5) {
    return floor + 1
  }

  // Exactly 0.5 - round to nearest even number
  return floor % 2 === 0 ? floor : floor + 1
}

/**
 * Get the currency symbol for a currency code
 *
 * @param {string} currencyCode - ISO 4217 currency code
 * @returns {string} Currency symbol
 */
export function getCurrencySymbol(currencyCode) {
  const config = CURRENCY_CONFIG[currencyCode]
  return config ? config.symbol : '$'
}

/**
 * Get the currency configuration
 *
 * @param {string} currencyCode - ISO 4217 currency code
 * @returns {Object|null} Currency configuration or null if not found
 */
export function getCurrencyConfig(currencyCode) {
  return CURRENCY_CONFIG[currencyCode] || null
}

/**
 * Check if a currency code is supported
 *
 * @param {string} currencyCode - ISO 4217 currency code
 * @returns {boolean} True if supported
 */
export function isSupportedCurrency(currencyCode) {
  return SUPPORTED_CURRENCIES.includes(currencyCode)
}

/**
 * Parse a formatted price string to cents
 * Note: This is a best-effort parser and may not handle all locales perfectly
 *
 * @param {string} formattedPrice - Formatted price string
 * @param {string} currencyCode - Currency code for determining decimal places
 * @returns {number|null} Amount in cents, or null if parsing failed
 */
export function parsePrice(formattedPrice, currencyCode = 'USD') {
  if (!formattedPrice || typeof formattedPrice !== 'string') {
    return null
  }

  const config = CURRENCY_CONFIG[currencyCode] || CURRENCY_CONFIG.USD

  // Remove currency symbols, spaces, and thousands separators
  // Keep only digits, decimal points, commas, and minus sign
  let cleaned = formattedPrice
    .replace(/[^\d.,-]/g, '')
    .trim()

  // Handle negative values
  const isNegative = cleaned.startsWith('-')
  cleaned = cleaned.replace(/-/g, '')

  // Normalize decimal separator (handle both . and , as decimal separator)
  // If both exist, the last one is likely the decimal separator
  const lastDot = cleaned.lastIndexOf('.')
  const lastComma = cleaned.lastIndexOf(',')

  if (lastComma > lastDot) {
    // European format: 1.234,56
    cleaned = cleaned.replace(/\./g, '').replace(',', '.')
  } else {
    // US format: 1,234.56
    cleaned = cleaned.replace(/,/g, '')
  }

  const parsed = parseFloat(cleaned)

  if (!Number.isFinite(parsed)) {
    return null
  }

  const cents = Math.round(parsed * Math.pow(10, config.exponent))
  return isNegative ? -cents : cents
}

// Default export for convenience
export default {
  formatPrice,
  formatAmount,
  convertPrice,
  convertAndFormatPrice,
  getCurrencySymbol,
  getCurrencyConfig,
  isSupportedCurrency,
  parsePrice,
  CURRENCY_CONFIG,
  SUPPORTED_CURRENCIES,
}

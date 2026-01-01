/**
 * CurrencySelector Component
 *
 * Dropdown component for selecting the display currency.
 * Supports USD, EUR, GBP, and BRL currencies.
 * Persists selection to Redux state and localStorage/backend.
 */
import { useCallback } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select'
import {
  selectSelectedCurrency,
  selectCurrencyLoading,
  setUserCurrencyPreference,
  SUPPORTED_CURRENCIES,
} from '../store/slices/currencySlice'
import { CURRENCY_CONFIG } from '../utils/formatCurrency'

// Currency display information
const CURRENCY_OPTIONS = SUPPORTED_CURRENCIES.map((code) => ({
  code,
  symbol: CURRENCY_CONFIG[code]?.symbol || code,
  name: getCurrencyName(code),
}))

/**
 * Get the full name of a currency
 */
function getCurrencyName(code) {
  const names = {
    USD: 'US Dollar',
    EUR: 'Euro',
    GBP: 'British Pound',
    BRL: 'Brazilian Real',
  }
  return names[code] || code
}

/**
 * CurrencySelector - Dropdown for selecting display currency
 *
 * @param {Object} props - Component props
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.compact - Use compact display (symbol only)
 * @param {boolean} props.showLabel - Show "Currency" label
 */
const CurrencySelector = ({
  className = '',
  compact = false,
  showLabel = false,
}) => {
  const dispatch = useDispatch()
  const selectedCurrency = useSelector(selectSelectedCurrency)
  const loading = useSelector(selectCurrencyLoading)

  const handleCurrencyChange = useCallback(
    (currency) => {
      if (currency && SUPPORTED_CURRENCIES.includes(currency)) {
        dispatch(setUserCurrencyPreference(currency))
      }
    },
    [dispatch]
  )

  const selectedOption = CURRENCY_OPTIONS.find(
    (opt) => opt.code === selectedCurrency
  )

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {showLabel && (
        <label className="text-sm text-gray-500 dark:text-gray-400">
          Currency:
        </label>
      )}
      <Select
        value={selectedCurrency}
        onValueChange={handleCurrencyChange}
        disabled={loading}
      >
        <SelectTrigger
          className={`${
            compact ? 'w-[70px]' : 'w-[130px]'
          } h-9 text-sm bg-white dark:bg-dark-surface-secondary`}
          aria-label="Select currency"
        >
          <SelectValue>
            {selectedOption && (
              <span className="flex items-center gap-1.5">
                <span className="font-medium">{selectedOption.symbol}</span>
                {!compact && (
                  <span className="text-gray-600 dark:text-gray-400">
                    {selectedOption.code}
                  </span>
                )}
              </span>
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {CURRENCY_OPTIONS.map((option) => (
            <SelectItem
              key={option.code}
              value={option.code}
              className="cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <span className="w-6 font-medium">{option.symbol}</span>
                <span>{option.code}</span>
                {!compact && (
                  <span className="text-gray-500 dark:text-gray-400 text-xs">
                    - {option.name}
                  </span>
                )}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export default CurrencySelector

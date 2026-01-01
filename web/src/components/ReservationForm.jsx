import { useState, useEffect, useRef, useCallback } from 'react'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.css'
import { Portuguese } from 'flatpickr/dist/l10n/pt.js'
import { addHours, addDays } from 'date-fns'
import { Cpu, Clock, Calendar, DollarSign, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

const API_BASE = ''

// GPU options for reservations (datacenter-focused)
const GPU_OPTIONS = [
  { value: 'RTX 4090', label: 'RTX 4090', vram: '24GB', priceRange: '$0.50-$0.80/h' },
  { value: 'RTX 4080', label: 'RTX 4080', vram: '16GB', priceRange: '$0.35-$0.50/h' },
  { value: 'RTX 3090', label: 'RTX 3090', vram: '24GB', priceRange: '$0.30-$0.45/h' },
  { value: 'RTX 3080', label: 'RTX 3080', vram: '12GB', priceRange: '$0.20-$0.35/h' },
  { value: 'RTX A6000', label: 'RTX A6000', vram: '48GB', priceRange: '$0.80-$1.20/h' },
  { value: 'RTX A5000', label: 'RTX A5000', vram: '24GB', priceRange: '$0.50-$0.70/h' },
  { value: 'RTX A4000', label: 'RTX A4000', vram: '16GB', priceRange: '$0.30-$0.45/h' },
  { value: 'A100', label: 'A100', vram: '40-80GB', priceRange: '$1.50-$3.00/h' },
  { value: 'H100', label: 'H100', vram: '80GB', priceRange: '$2.50-$4.50/h' },
  { value: 'L40', label: 'L40', vram: '48GB', priceRange: '$1.00-$1.50/h' },
  { value: 'L40S', label: 'L40S', vram: '48GB', priceRange: '$1.20-$1.80/h' },
]

// GPU count options
const GPU_COUNT_OPTIONS = [1, 2, 4, 8]

/**
 * ReservationForm - Form component for creating GPU reservations
 *
 * Features:
 * - GPU type selector with VRAM and pricing info
 * - GPU count selector (1, 2, 4, 8)
 * - Flatpickr datetime pickers for start/end times
 * - Real-time pricing estimate
 * - Availability checking
 * - Form validation
 */
export default function ReservationForm({
  onSubmit,
  onCancel,
  initialStartTime,
  initialEndTime,
  loading = false,
}) {
  // Form state
  const [gpuType, setGpuType] = useState('RTX 4090')
  const [gpuCount, setGpuCount] = useState(1)
  const [startTime, setStartTime] = useState(initialStartTime || addHours(new Date(), 1))
  const [endTime, setEndTime] = useState(initialEndTime || addHours(new Date(), 5))

  // UI state
  const [checkingAvailability, setCheckingAvailability] = useState(false)
  const [availability, setAvailability] = useState(null)
  const [pricing, setPricing] = useState(null)
  const [pricingLoading, setPricingLoading] = useState(false)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Flatpickr refs
  const startPickerRef = useRef(null)
  const endPickerRef = useRef(null)
  const startInputRef = useRef(null)
  const endInputRef = useRef(null)

  // Initialize Flatpickr for start date
  useEffect(() => {
    if (startInputRef.current) {
      startPickerRef.current = flatpickr(startInputRef.current, {
        enableTime: true,
        time_24hr: true,
        dateFormat: 'Y-m-d H:i',
        minDate: 'today',
        maxDate: addDays(new Date(), 365),
        defaultDate: startTime,
        locale: Portuguese,
        onChange: (selectedDates) => {
          if (selectedDates[0]) {
            setStartTime(selectedDates[0])
            // Auto-adjust end time if it's before start
            if (selectedDates[0] >= endTime) {
              const newEnd = addHours(selectedDates[0], 4)
              setEndTime(newEnd)
              if (endPickerRef.current) {
                endPickerRef.current.setDate(newEnd)
              }
            }
          }
        },
      })
    }

    return () => {
      if (startPickerRef.current) {
        startPickerRef.current.destroy()
      }
    }
  }, [])

  // Initialize Flatpickr for end date
  useEffect(() => {
    if (endInputRef.current) {
      endPickerRef.current = flatpickr(endInputRef.current, {
        enableTime: true,
        time_24hr: true,
        dateFormat: 'Y-m-d H:i',
        minDate: addHours(startTime, 1),
        maxDate: addDays(new Date(), 395), // 30 days max reservation
        defaultDate: endTime,
        locale: Portuguese,
        onChange: (selectedDates) => {
          if (selectedDates[0]) {
            setEndTime(selectedDates[0])
          }
        },
      })
    }

    return () => {
      if (endPickerRef.current) {
        endPickerRef.current.destroy()
      }
    }
  }, [startTime])

  // Update end picker min date when start changes
  useEffect(() => {
    if (endPickerRef.current) {
      endPickerRef.current.set('minDate', addHours(startTime, 1))
    }
  }, [startTime])

  // Fetch pricing estimate when parameters change
  const fetchPricing = useCallback(async () => {
    if (!gpuType || !startTime || !endTime) return

    setPricingLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        gpu_type: gpuType,
        start: startTime.toISOString(),
        end: endTime.toISOString(),
        gpu_count: gpuCount.toString(),
      })

      const res = await fetch(`${API_BASE}/api/reservations/pricing?${params}`, {
        credentials: 'include',
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to fetch pricing')
      }

      const data = await res.json()
      setPricing(data)
    } catch (e) {
      setPricing(null)
    } finally {
      setPricingLoading(false)
    }
  }, [gpuType, gpuCount, startTime, endTime])

  // Check availability
  const checkAvailability = useCallback(async () => {
    if (!gpuType || !startTime || !endTime) return

    setCheckingAvailability(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        gpu_type: gpuType,
        start: startTime.toISOString(),
        end: endTime.toISOString(),
        gpu_count: gpuCount.toString(),
      })

      const res = await fetch(`${API_BASE}/api/reservations/availability?${params}`, {
        credentials: 'include',
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to check availability')
      }

      const data = await res.json()
      setAvailability(data)
    } catch (e) {
      setAvailability(null)
    } finally {
      setCheckingAvailability(false)
    }
  }, [gpuType, gpuCount, startTime, endTime])

  // Debounced fetch on parameter changes
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchPricing()
      checkAvailability()
    }, 500)

    return () => clearTimeout(timer)
  }, [fetchPricing, checkAvailability])

  // Calculate duration in hours
  const durationHours = Math.max(0, (endTime - startTime) / (1000 * 60 * 60))

  // Validate form
  const isValid = () => {
    if (!gpuType) return false
    if (!startTime || !endTime) return false
    if (startTime >= endTime) return false
    if (durationHours < 1) return false
    if (durationHours > 720) return false // 30 days max
    if (availability && !availability.available) return false
    return true
  }

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!isValid()) {
      setError('Por favor, preencha todos os campos corretamente')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      if (onSubmit) {
        await onSubmit({
          gpu_type: gpuType,
          gpu_count: gpuCount,
          start_time: startTime.toISOString(),
          end_time: endTime.toISOString(),
        })
      }
    } catch (e) {
      setError(e.message || 'Falha ao criar reserva')
    } finally {
      setSubmitting(false)
    }
  }

  // Get selected GPU info
  const selectedGpu = GPU_OPTIONS.find(g => g.value === gpuType)

  return (
    <form onSubmit={handleSubmit} className="reservation-form">
      {/* GPU Selection */}
      <div className="form-section">
        <label className="ta-input-label flex items-center gap-2">
          <Cpu className="w-4 h-4 text-green-400" />
          Tipo de GPU
        </label>
        <select
          className="ta-select"
          value={gpuType}
          onChange={(e) => setGpuType(e.target.value)}
          disabled={loading || submitting}
        >
          {GPU_OPTIONS.map((gpu) => (
            <option key={gpu.value} value={gpu.value}>
              {gpu.label} ({gpu.vram}) - {gpu.priceRange}
            </option>
          ))}
        </select>
        {selectedGpu && (
          <p className="ta-input-helper">
            VRAM: {selectedGpu.vram} | Preco estimado: {selectedGpu.priceRange}
          </p>
        )}
      </div>

      {/* GPU Count */}
      <div className="form-section">
        <label className="ta-input-label">Quantidade de GPUs</label>
        <div className="gpu-count-selector">
          {GPU_COUNT_OPTIONS.map((count) => (
            <button
              key={count}
              type="button"
              className={`gpu-count-btn ${gpuCount === count ? 'active' : ''}`}
              onClick={() => setGpuCount(count)}
              disabled={loading || submitting}
            >
              {count}x
            </button>
          ))}
        </div>
      </div>

      {/* Date/Time Selection */}
      <div className="form-section">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Start Time */}
          <div>
            <label className="ta-input-label flex items-center gap-2">
              <Calendar className="w-4 h-4 text-green-400" />
              Inicio
            </label>
            <div className="relative">
              <input
                ref={startInputRef}
                type="text"
                className="ta-input flatpickr-input"
                placeholder="Selecione data e hora"
                disabled={loading || submitting}
                readOnly
              />
              <Clock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>
          </div>

          {/* End Time */}
          <div>
            <label className="ta-input-label flex items-center gap-2">
              <Calendar className="w-4 h-4 text-green-400" />
              Fim
            </label>
            <div className="relative">
              <input
                ref={endInputRef}
                type="text"
                className="ta-input flatpickr-input"
                placeholder="Selecione data e hora"
                disabled={loading || submitting}
                readOnly
              />
              <Clock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Duration display */}
        <div className="mt-3 flex items-center gap-2 text-sm text-gray-400">
          <Clock className="w-4 h-4" />
          <span>
            Duracao: {durationHours.toFixed(1)} hora{durationHours !== 1 ? 's' : ''}
            {durationHours > 24 && ` (${(durationHours / 24).toFixed(1)} dias)`}
          </span>
        </div>
      </div>

      {/* Availability Status */}
      {(checkingAvailability || availability) && (
        <div className="form-section">
          <div className={`availability-status ${
            checkingAvailability ? 'checking' :
            availability?.available ? 'available' : 'unavailable'
          }`}>
            {checkingAvailability ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Verificando disponibilidade...</span>
              </>
            ) : availability?.available ? (
              <>
                <CheckCircle className="w-4 h-4" />
                <span>GPU disponivel para reserva</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4" />
                <span>{availability?.message || 'GPU nao disponivel neste horario'}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Pricing Preview */}
      {(pricingLoading || pricing) && (
        <div className="form-section">
          <div className="pricing-preview">
            <div className="pricing-header">
              <DollarSign className="w-5 h-5 text-green-400" />
              <span>Estimativa de Custo</span>
              {pricingLoading && <Loader2 className="w-4 h-4 animate-spin ml-auto" />}
            </div>

            {pricing && (
              <div className="pricing-details">
                <div className="pricing-row">
                  <span className="pricing-label">Preco Spot</span>
                  <span className="pricing-value line-through text-gray-500">
                    ${pricing.total_spot_cost?.toFixed(2)}
                  </span>
                </div>
                <div className="pricing-row">
                  <span className="pricing-label">Desconto Reserva</span>
                  <span className="pricing-value text-green-400">
                    -{pricing.discount_rate}%
                  </span>
                </div>
                <div className="pricing-row highlight">
                  <span className="pricing-label">Total (Reserva)</span>
                  <span className="pricing-value text-lg text-white">
                    ${pricing.total_reserved_cost?.toFixed(2)}
                  </span>
                </div>
                <div className="pricing-row savings">
                  <span className="pricing-label">Voce economiza</span>
                  <span className="pricing-value text-green-400">
                    ${pricing.savings?.toFixed(2)}
                  </span>
                </div>
                <div className="pricing-row credits">
                  <span className="pricing-label">Creditos necessarios</span>
                  <span className="pricing-value">
                    {pricing.credits_required?.toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="form-section">
          <div className="error-message">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Form Actions */}
      <div className="form-actions">
        {onCancel && (
          <button
            type="button"
            className="ta-btn ta-btn-ghost"
            onClick={onCancel}
            disabled={loading || submitting}
          >
            Cancelar
          </button>
        )}
        <button
          type="submit"
          className="ta-btn ta-btn-primary"
          disabled={loading || submitting || !isValid()}
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Criando Reserva...
            </>
          ) : (
            <>
              <Calendar className="w-4 h-4" />
              Criar Reserva
            </>
          )}
        </button>
      </div>

      {/* Form Styles */}
      <style>{`
        .reservation-form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .form-section {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .gpu-count-selector {
          display: flex;
          gap: 0.5rem;
        }

        .gpu-count-btn {
          flex: 1;
          padding: 0.625rem 1rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: #9ca3af;
          background-color: rgba(31, 41, 55, 0.5);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 0.5rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .gpu-count-btn:hover:not(:disabled) {
          background-color: rgba(55, 65, 81, 0.5);
          color: #e5e7eb;
        }

        .gpu-count-btn.active {
          background-color: rgba(74, 222, 128, 0.15);
          border-color: #4ade80;
          color: #4ade80;
        }

        .gpu-count-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .availability-status {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          border-radius: 0.5rem;
          font-size: 0.875rem;
        }

        .availability-status.checking {
          background-color: rgba(59, 130, 246, 0.1);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .availability-status.available {
          background-color: rgba(74, 222, 128, 0.1);
          color: #4ade80;
          border: 1px solid rgba(74, 222, 128, 0.3);
        }

        .availability-status.unavailable {
          background-color: rgba(239, 68, 68, 0.1);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .pricing-preview {
          background-color: rgba(31, 41, 55, 0.5);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 0.5rem;
          overflow: hidden;
        }

        .pricing-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          background-color: rgba(17, 24, 39, 0.5);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          font-size: 0.875rem;
          font-weight: 500;
          color: #e5e7eb;
        }

        .pricing-details {
          padding: 0.75rem 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .pricing-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.875rem;
        }

        .pricing-label {
          color: #9ca3af;
        }

        .pricing-value {
          color: #e5e7eb;
          font-family: monospace;
        }

        .pricing-row.highlight {
          padding-top: 0.5rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          margin-top: 0.25rem;
        }

        .pricing-row.highlight .pricing-label {
          font-weight: 500;
          color: #e5e7eb;
        }

        .pricing-row.savings {
          padding-top: 0.5rem;
        }

        .pricing-row.credits {
          padding-top: 0.5rem;
          border-top: 1px dashed rgba(255, 255, 255, 0.1);
          margin-top: 0.25rem;
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          background-color: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 0.5rem;
          color: #f87171;
          font-size: 0.875rem;
        }

        .form-actions {
          display: flex;
          justify-content: flex-end;
          gap: 0.75rem;
          padding-top: 1rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Flatpickr dark theme overrides */
        .flatpickr-calendar {
          background: #1f2937;
          border-color: #374151;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
        }

        .flatpickr-calendar.arrowTop:after {
          border-bottom-color: #1f2937;
        }

        .flatpickr-calendar.arrowBottom:after {
          border-top-color: #1f2937;
        }

        .flatpickr-months {
          background: #111827;
          border-bottom: 1px solid #374151;
        }

        .flatpickr-month {
          background: transparent;
          color: #e5e7eb;
        }

        .flatpickr-current-month .flatpickr-monthDropdown-months {
          background: #1f2937;
          color: #e5e7eb;
        }

        .flatpickr-current-month input.cur-year {
          color: #e5e7eb;
        }

        .flatpickr-months .flatpickr-prev-month,
        .flatpickr-months .flatpickr-next-month {
          color: #9ca3af;
          fill: #9ca3af;
        }

        .flatpickr-months .flatpickr-prev-month:hover,
        .flatpickr-months .flatpickr-next-month:hover {
          color: #e5e7eb;
          fill: #e5e7eb;
        }

        .flatpickr-weekdays {
          background: #111827;
        }

        .flatpickr-weekday {
          color: #9ca3af;
          font-weight: 500;
        }

        .flatpickr-days {
          border: none;
        }

        .flatpickr-day {
          color: #e5e7eb;
          border-radius: 0.375rem;
        }

        .flatpickr-day:hover {
          background: #374151;
          border-color: #374151;
        }

        .flatpickr-day.today {
          border-color: #4ade80;
        }

        .flatpickr-day.selected {
          background: #4ade80;
          border-color: #4ade80;
          color: #052e16;
        }

        .flatpickr-day.selected:hover {
          background: #22c55e;
          border-color: #22c55e;
        }

        .flatpickr-day.flatpickr-disabled {
          color: #4b5563;
        }

        .flatpickr-time {
          background: #111827;
          border-top: 1px solid #374151;
        }

        .flatpickr-time input {
          color: #e5e7eb;
          background: transparent;
        }

        .flatpickr-time .flatpickr-time-separator {
          color: #9ca3af;
        }

        .flatpickr-time .flatpickr-am-pm {
          color: #e5e7eb;
          background: transparent;
        }

        .numInputWrapper:hover {
          background: #374151;
        }

        .numInputWrapper span {
          border-color: #4b5563;
        }

        .numInputWrapper span:hover {
          background: #4b5563;
        }
      `}</style>
    </form>
  )
}

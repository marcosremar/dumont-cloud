import { useState, useMemo, useCallback } from 'react'
import { Calendar, dateFnsLocalizer } from 'react-big-calendar'
import { format, parse, startOfWeek, getDay, addHours } from 'date-fns'
import { enUS, ptBR } from 'date-fns/locale'
import { X, Clock, Cpu, DollarSign, Calendar as CalendarIcon, Trash2 } from 'lucide-react'
import 'react-big-calendar/lib/css/react-big-calendar.css'

// Date-fns localizer configuration
const locales = {
  'en-US': enUS,
  'pt-BR': ptBR,
}

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: (date) => startOfWeek(date, { weekStartsOn: 0 }),
  getDay,
  locales,
})

// Status colors for reservations
const STATUS_COLORS = {
  pending: { bg: '#fbbf24', border: '#d97706', text: '#78350f' }, // Yellow
  active: { bg: '#22c55e', border: '#16a34a', text: '#052e16' },  // Green
  completed: { bg: '#6b7280', border: '#4b5563', text: '#f3f4f6' }, // Gray
  cancelled: { bg: '#ef4444', border: '#dc2626', text: '#fef2f2' }, // Red
  failed: { bg: '#f97316', border: '#ea580c', text: '#fff7ed' },   // Orange
}

// GPU type colors for visual distinction
const GPU_COLORS = {
  'RTX 4090': '#76ff03',
  'RTX 4080': '#00e676',
  'RTX 3090': '#1de9b6',
  'RTX 3080': '#00bcd4',
  'RTX A6000': '#40c4ff',
  'RTX A5000': '#448aff',
  'RTX A4000': '#536dfe',
  'A100': '#7c4dff',
  'H100': '#e040fb',
  default: '#4ade80',
}

/**
 * ReservationCalendar - Calendar component for GPU reservations
 *
 * Uses react-big-calendar with date-fns localizer for displaying
 * and managing GPU reservations with slot selection.
 */
export default function ReservationCalendar({
  reservations = [],
  onSelectSlot,
  onSelectEvent,
  onCancelReservation,
  loading = false,
  minDate = new Date(),
  maxDate = addHours(new Date(), 24 * 365), // 1 year ahead
}) {
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [view, setView] = useState('week')
  const [date, setDate] = useState(new Date())

  // Transform reservations to calendar events
  const events = useMemo(() => {
    return reservations.map((reservation) => {
      const gpuColor = GPU_COLORS[reservation.gpu_type] || GPU_COLORS.default
      const statusColor = STATUS_COLORS[reservation.status] || STATUS_COLORS.pending

      return {
        id: reservation.id,
        title: `${reservation.gpu_type}${reservation.gpu_count > 1 ? ` x${reservation.gpu_count}` : ''}`,
        start: new Date(reservation.start_time),
        end: new Date(reservation.end_time),
        resource: reservation,
        // Style based on status
        style: {
          backgroundColor: statusColor.bg,
          borderColor: statusColor.border,
          color: statusColor.text,
          borderLeft: `4px solid ${gpuColor}`,
        },
      }
    })
  }, [reservations])

  // Handle slot selection (click on empty time slot)
  const handleSelectSlot = useCallback((slotInfo) => {
    // Don't allow selecting past dates
    if (slotInfo.start < new Date()) {
      return
    }

    if (onSelectSlot) {
      onSelectSlot({
        start: slotInfo.start,
        end: slotInfo.end,
        slots: slotInfo.slots,
      })
    }
  }, [onSelectSlot])

  // Handle event click
  const handleSelectEvent = useCallback((event) => {
    setSelectedEvent(event)
    if (onSelectEvent) {
      onSelectEvent(event.resource)
    }
  }, [onSelectEvent])

  // Close event modal
  const handleCloseModal = useCallback(() => {
    setSelectedEvent(null)
  }, [])

  // Cancel reservation from modal
  const handleCancelFromModal = useCallback(() => {
    if (selectedEvent && onCancelReservation) {
      onCancelReservation(selectedEvent.resource)
      setSelectedEvent(null)
    }
  }, [selectedEvent, onCancelReservation])

  // Custom event component styling
  const eventStyleGetter = useCallback((event) => {
    return {
      style: event.style,
    }
  }, [])

  // Custom toolbar component
  const CustomToolbar = useCallback(({ label, onNavigate, onView }) => {
    return (
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate('PREV')}
            className="ta-btn ta-btn-sm ta-btn-ghost"
          >
            &larr;
          </button>
          <button
            onClick={() => onNavigate('TODAY')}
            className="ta-btn ta-btn-sm ta-btn-ghost"
          >
            Hoje
          </button>
          <button
            onClick={() => onNavigate('NEXT')}
            className="ta-btn ta-btn-sm ta-btn-ghost"
          >
            &rarr;
          </button>
        </div>

        <span className="text-lg font-semibold text-white">{label}</span>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onView('day')}
            className={`ta-btn ta-btn-sm ${view === 'day' ? 'ta-btn-primary' : 'ta-btn-ghost'}`}
          >
            Dia
          </button>
          <button
            onClick={() => onView('week')}
            className={`ta-btn ta-btn-sm ${view === 'week' ? 'ta-btn-primary' : 'ta-btn-ghost'}`}
          >
            Semana
          </button>
          <button
            onClick={() => onView('month')}
            className={`ta-btn ta-btn-sm ${view === 'month' ? 'ta-btn-primary' : 'ta-btn-ghost'}`}
          >
            Mes
          </button>
        </div>
      </div>
    )
  }, [view])

  // Format duration
  const formatDuration = (start, end) => {
    const hours = Math.round((new Date(end) - new Date(start)) / (1000 * 60 * 60) * 10) / 10
    return hours === 1 ? '1 hora' : `${hours} horas`
  }

  return (
    <div className="reservation-calendar relative">
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-10 rounded-lg">
          <div className="flex items-center gap-3 text-white">
            <div className="spinner" />
            <span>Carregando reservas...</span>
          </div>
        </div>
      )}

      {/* Calendar */}
      <div className="bg-gray-800/30 rounded-lg border border-gray-700 p-4">
        <Calendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          style={{ height: 600 }}
          view={view}
          onView={setView}
          date={date}
          onNavigate={setDate}
          selectable
          onSelectSlot={handleSelectSlot}
          onSelectEvent={handleSelectEvent}
          eventPropGetter={eventStyleGetter}
          components={{
            toolbar: CustomToolbar,
          }}
          messages={{
            next: 'Proximo',
            previous: 'Anterior',
            today: 'Hoje',
            month: 'Mes',
            week: 'Semana',
            day: 'Dia',
            agenda: 'Agenda',
            date: 'Data',
            time: 'Hora',
            event: 'Reserva',
            noEventsInRange: 'Nenhuma reserva neste periodo.',
            showMore: (count) => `+${count} mais`,
          }}
          min={new Date(0, 0, 0, 6, 0, 0)} // 6 AM
          max={new Date(0, 0, 0, 23, 59, 59)} // 11:59 PM
          step={30}
          timeslots={2}
          popup
        />
      </div>

      {/* Legend */}
      <div className="mt-4 p-3 bg-gray-800/30 rounded-lg border border-gray-700">
        <p className="text-xs text-gray-400 mb-2">Status das Reservas:</p>
        <div className="flex flex-wrap gap-4">
          {Object.entries(STATUS_COLORS).map(([status, colors]) => (
            <div key={status} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: colors.bg, border: `1px solid ${colors.border}` }}
              />
              <span className="text-xs text-gray-400 capitalize">{status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Event Detail Modal */}
      {selectedEvent && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={handleCloseModal}
        >
          <div
            className="bg-gray-800 rounded-lg border border-gray-700 max-w-md w-full shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <CalendarIcon className="w-5 h-5 text-green-400" />
                Detalhes da Reserva
              </h3>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {/* GPU Info */}
              <div className="flex items-center gap-3 p-3 bg-gray-900/50 rounded-lg">
                <Cpu className="w-8 h-8 text-green-400" />
                <div>
                  <p className="text-white font-semibold">
                    {selectedEvent.resource.gpu_type}
                    {selectedEvent.resource.gpu_count > 1 && (
                      <span className="text-gray-400"> x{selectedEvent.resource.gpu_count}</span>
                    )}
                  </p>
                  <p className="text-sm text-gray-400">
                    ID: {selectedEvent.resource.id}
                  </p>
                </div>
                <div className={`ml-auto px-2 py-1 rounded text-xs font-medium capitalize`}
                  style={{
                    backgroundColor: STATUS_COLORS[selectedEvent.resource.status]?.bg,
                    color: STATUS_COLORS[selectedEvent.resource.status]?.text,
                  }}
                >
                  {selectedEvent.resource.status}
                </div>
              </div>

              {/* Time Info */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-900/50 rounded-lg">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                    <Clock className="w-4 h-4" />
                    Inicio
                  </div>
                  <p className="text-white">
                    {format(selectedEvent.start, 'dd/MM/yyyy HH:mm')}
                  </p>
                </div>
                <div className="p-3 bg-gray-900/50 rounded-lg">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                    <Clock className="w-4 h-4" />
                    Fim
                  </div>
                  <p className="text-white">
                    {format(selectedEvent.end, 'dd/MM/yyyy HH:mm')}
                  </p>
                </div>
              </div>

              {/* Duration */}
              <div className="p-3 bg-gray-900/50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">Duracao</span>
                  <span className="text-white">
                    {formatDuration(selectedEvent.start, selectedEvent.end)}
                  </span>
                </div>
              </div>

              {/* Credits/Pricing */}
              {(selectedEvent.resource.credits_used || selectedEvent.resource.reserved_price_per_hour) && (
                <div className="p-3 bg-gray-900/50 rounded-lg space-y-2">
                  {selectedEvent.resource.credits_used && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400 text-sm flex items-center gap-2">
                        <DollarSign className="w-4 h-4" />
                        Creditos Usados
                      </span>
                      <span className="text-green-400 font-mono">
                        {selectedEvent.resource.credits_used}
                      </span>
                    </div>
                  )}
                  {selectedEvent.resource.discount_rate && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400 text-sm">Desconto</span>
                      <span className="text-green-400 font-medium">
                        {selectedEvent.resource.discount_rate}%
                      </span>
                    </div>
                  )}
                  {selectedEvent.resource.reserved_price_per_hour && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400 text-sm">Preco/Hora</span>
                      <span className="text-white font-mono">
                        ${selectedEvent.resource.reserved_price_per_hour.toFixed(3)}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 border-t border-gray-700 flex justify-end gap-2">
              <button
                onClick={handleCloseModal}
                className="ta-btn ta-btn-ghost"
              >
                Fechar
              </button>
              {selectedEvent.resource.status === 'pending' || selectedEvent.resource.status === 'active' ? (
                <button
                  onClick={handleCancelFromModal}
                  className="ta-btn ta-btn-danger flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Cancelar Reserva
                </button>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Custom styles for react-big-calendar dark theme */}
      <style>{`
        .reservation-calendar .rbc-calendar {
          color: #e5e7eb;
          font-family: inherit;
        }

        .reservation-calendar .rbc-header {
          background-color: #1f2937;
          border-color: #374151;
          padding: 8px;
          font-weight: 600;
          color: #9ca3af;
        }

        .reservation-calendar .rbc-month-view,
        .reservation-calendar .rbc-time-view {
          border-color: #374151;
        }

        .reservation-calendar .rbc-day-bg {
          background-color: #111827;
        }

        .reservation-calendar .rbc-day-bg.rbc-today {
          background-color: rgba(74, 222, 128, 0.1);
        }

        .reservation-calendar .rbc-off-range-bg {
          background-color: #0d1117;
        }

        .reservation-calendar .rbc-date-cell {
          color: #9ca3af;
          padding: 4px 8px;
        }

        .reservation-calendar .rbc-date-cell.rbc-now {
          color: #4ade80;
          font-weight: 600;
        }

        .reservation-calendar .rbc-event {
          border-radius: 4px;
          padding: 2px 6px;
          font-size: 12px;
          font-weight: 500;
        }

        .reservation-calendar .rbc-event:focus {
          outline: 2px solid #4ade80;
          outline-offset: 2px;
        }

        .reservation-calendar .rbc-event-label {
          font-size: 11px;
        }

        .reservation-calendar .rbc-time-header-content {
          border-color: #374151;
        }

        .reservation-calendar .rbc-timeslot-group {
          border-color: #374151;
        }

        .reservation-calendar .rbc-time-slot {
          border-color: #1f2937;
        }

        .reservation-calendar .rbc-time-content {
          border-color: #374151;
        }

        .reservation-calendar .rbc-time-gutter {
          background-color: #1f2937;
          color: #9ca3af;
          font-size: 12px;
        }

        .reservation-calendar .rbc-current-time-indicator {
          background-color: #ef4444;
          height: 2px;
        }

        .reservation-calendar .rbc-current-time-indicator::before {
          content: '';
          position: absolute;
          left: -6px;
          top: -4px;
          width: 10px;
          height: 10px;
          background-color: #ef4444;
          border-radius: 50%;
        }

        .reservation-calendar .rbc-allday-cell {
          background-color: #1f2937;
        }

        .reservation-calendar .rbc-month-row {
          border-color: #374151;
        }

        .reservation-calendar .rbc-show-more {
          color: #4ade80;
          font-weight: 500;
          background-color: transparent;
        }

        .reservation-calendar .rbc-overlay {
          background-color: #1f2937;
          border-color: #374151;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
        }

        .reservation-calendar .rbc-overlay-header {
          border-color: #374151;
          color: #e5e7eb;
        }

        .reservation-calendar .rbc-agenda-view table {
          border-color: #374151;
        }

        .reservation-calendar .rbc-agenda-time-cell,
        .reservation-calendar .rbc-agenda-date-cell {
          color: #9ca3af;
        }

        .reservation-calendar .rbc-selected-cell {
          background-color: rgba(74, 222, 128, 0.2);
        }

        .reservation-calendar .rbc-slot-selection {
          background-color: rgba(74, 222, 128, 0.3);
          border: 2px dashed #4ade80;
        }
      `}</style>
    </div>
  )
}

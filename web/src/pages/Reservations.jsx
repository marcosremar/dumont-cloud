import { useState, useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Calendar,
  Plus,
  Clock,
  Cpu,
  DollarSign,
  TrendingUp,
  X,
  AlertCircle,
  Loader2
} from 'lucide-react'
import { Button } from '../components/tailadmin-ui'
import ReservationCalendar from '../components/ReservationCalendar'
import ReservationForm from '../components/ReservationForm'

const API_BASE = ''

// Demo reservations data
const DEMO_RESERVATIONS = [
  {
    id: 1,
    gpu_type: 'RTX 4090',
    gpu_count: 2,
    start_time: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(), // 2 hours from now
    end_time: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(), // 6 hours from now
    status: 'pending',
    credits_used: 45.50,
    discount_rate: 15,
    reserved_price_per_hour: 0.68,
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    gpu_type: 'A100',
    gpu_count: 1,
    start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // Tomorrow
    end_time: new Date(Date.now() + 32 * 60 * 60 * 1000).toISOString(), // Tomorrow + 8h
    status: 'active',
    credits_used: 120.00,
    discount_rate: 18,
    reserved_price_per_hour: 2.46,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    gpu_type: 'H100',
    gpu_count: 4,
    start_time: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(), // 2 days ago
    end_time: new Date(Date.now() - 40 * 60 * 60 * 1000).toISOString(), // 2 days ago + 8h
    status: 'completed',
    credits_used: 280.00,
    discount_rate: 20,
    reserved_price_per_hour: 3.50,
    created_at: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
  },
]

export default function Reservations() {
  const location = useLocation()
  const isDemo = location.pathname.startsWith('/demo-app')

  // State
  const [reservations, setReservations] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)

  // Initial slot selection from calendar
  const [selectedSlot, setSelectedSlot] = useState(null)

  // Load reservations
  const loadReservations = useCallback(async () => {
    try {
      if (isDemo) {
        setReservations(DEMO_RESERVATIONS)
        setLoading(false)
        return
      }

      const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/reservations`, {
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Falha ao carregar reservas')
      }

      const data = await res.json()
      setReservations(data.reservations || data || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [isDemo])

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      if (isDemo) {
        setStats({
          total_reservations: 3,
          active_reservations: 1,
          pending_reservations: 1,
          total_credits_used: 445.50,
          total_hours_reserved: 24,
          average_discount: 17.7,
        })
        return
      }

      const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/reservations/stats`, {
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })

      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      // Stats are optional, don't show error
    }
  }, [isDemo])

  // Initial load
  useEffect(() => {
    loadReservations()
    loadStats()
  }, [loadReservations, loadStats])

  // Handle slot selection from calendar
  const handleSelectSlot = useCallback((slotInfo) => {
    setSelectedSlot(slotInfo)
    setShowCreateModal(true)
  }, [])

  // Handle reservation click from calendar
  const handleSelectEvent = useCallback((reservation) => {
    // Event details are shown in the calendar modal
  }, [])

  // Handle reservation cancellation
  const handleCancelReservation = useCallback(async (reservation) => {
    if (!confirm(`Cancelar reserva de ${reservation.gpu_type}?`)) {
      return
    }

    try {
      if (isDemo) {
        setReservations(prev => prev.filter(r => r.id !== reservation.id))
        return
      }

      const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/reservations/${reservation.id}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Falha ao cancelar reserva')
      }

      // Reload reservations
      loadReservations()
      loadStats()
    } catch (e) {
      setError(e.message)
    }
  }, [isDemo, loadReservations, loadStats])

  // Handle create reservation
  const handleCreateReservation = useCallback(async (formData) => {
    setCreateLoading(true)
    setError(null)

    try {
      if (isDemo) {
        // Add demo reservation
        const newReservation = {
          id: Date.now(),
          ...formData,
          status: 'pending',
          credits_used: Math.random() * 100 + 20,
          discount_rate: 15,
          reserved_price_per_hour: 0.75,
          created_at: new Date().toISOString(),
        }
        setReservations(prev => [...prev, newReservation])
        setShowCreateModal(false)
        setSelectedSlot(null)
        return
      }

      const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
      const res = await fetch(`${API_BASE}/api/reservations`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(formData)
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Falha ao criar reserva')
      }

      // Success - reload and close modal
      await loadReservations()
      await loadStats()
      setShowCreateModal(false)
      setSelectedSlot(null)
    } catch (e) {
      throw e // Let the form handle the error display
    } finally {
      setCreateLoading(false)
    }
  }, [isDemo, loadReservations, loadStats])

  // Close create modal
  const handleCloseModal = useCallback(() => {
    setShowCreateModal(false)
    setSelectedSlot(null)
  }, [])

  // Loading state
  if (loading) {
    return (
      <div className="page-container">
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-green-400" />
            <span className="text-gray-400">Carregando reservas...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-primary">
                <Calendar className="w-5 h-5" />
              </div>
              Reservas de GPU
            </h1>
            <p className="page-subtitle">
              Agende GPUs com desconto garantido de 10-20%
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
            icon={Plus}
          >
            Nova Reserva
          </Button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-400 text-sm">{error}</p>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Reservas Ativas</span>
              <Clock className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {stats.active_reservations || 0}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {stats.pending_reservations || 0} pendentes
            </div>
          </div>

          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Horas Reservadas</span>
              <Cpu className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {stats.total_hours_reserved || 0}h
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Total acumulado
            </div>
          </div>

          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Creditos Usados</span>
              <DollarSign className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              ${(stats.total_credits_used || 0).toFixed(2)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Em reservas
            </div>
          </div>

          <div className="p-4 rounded-xl bg-dark-surface-card border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Desconto Medio</span>
              <TrendingUp className="w-4 h-4 text-brand-400" />
            </div>
            <div className="text-2xl font-bold text-green-400">
              {(stats.average_discount || 0).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Economia vs spot
            </div>
          </div>
        </div>
      )}

      {/* Calendar */}
      <div className="mb-6">
        <ReservationCalendar
          reservations={reservations}
          onSelectSlot={handleSelectSlot}
          onSelectEvent={handleSelectEvent}
          onCancelReservation={handleCancelReservation}
          loading={loading}
        />
      </div>

      {/* Info text */}
      <div className="text-center text-sm text-gray-500 mb-6">
        Clique em um horario vazio no calendario para criar uma nova reserva
      </div>

      {/* Create Reservation Modal */}
      {showCreateModal && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={handleCloseModal}
        >
          <div
            className="bg-gray-800 rounded-lg border border-gray-700 max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700 sticky top-0 bg-gray-800 z-10">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Calendar className="w-5 h-5 text-green-400" />
                Nova Reserva de GPU
              </h3>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4">
              <ReservationForm
                onSubmit={handleCreateReservation}
                onCancel={handleCloseModal}
                initialStartTime={selectedSlot?.start}
                initialEndTime={selectedSlot?.end}
                loading={createLoading}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

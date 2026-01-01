import { createContext, useContext, useState, useCallback, useMemo } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'

const ToastContext = createContext(null)

// Variants - dark background with colored accent
const variants = {
  success: {
    icon: CheckCircle,
    accent: 'bg-green-500',
    iconColor: 'text-green-400',
    textColor: 'text-white'
  },
  error: {
    icon: AlertCircle,
    accent: 'bg-red-500',
    iconColor: 'text-red-400',
    textColor: 'text-white'
  },
  warning: {
    icon: AlertTriangle,
    accent: 'bg-yellow-500',
    iconColor: 'text-yellow-400',
    textColor: 'text-white'
  },
  info: {
    icon: Info,
    accent: 'bg-blue-500',
    iconColor: 'text-blue-400',
    textColor: 'text-white'
  }
}

function ToastItem({ id, message, type = 'info', isExiting = false, onClose }) {
  const variant = variants[type] || variants.info
  const Icon = variant.icon
  const animationClass = isExiting ? 'animate-toast-out' : 'animate-toast-in'

  return (
    <div
      className={`toast flex items-stretch bg-gray-900 rounded-lg shadow-2xl shadow-black/50 overflow-hidden ${animationClass} border border-gray-700`}
      style={{ minWidth: '320px', maxWidth: '500px' }}
      role="alert"
      aria-live="polite"
    >
      {/* Color accent bar on left */}
      <div className={`w-1.5 ${variant.accent} flex-shrink-0`} />

      {/* Content */}
      <div className="flex items-center gap-3 px-4 py-3.5 flex-1">
        <Icon className={`w-5 h-5 ${variant.iconColor} flex-shrink-0`} />
        <p className={`flex-1 text-sm font-medium ${variant.textColor}`}>{message}</p>
        <button
          onClick={() => onClose(id)}
          className="text-gray-500 hover:text-white transition-colors p-1 rounded hover:bg-gray-800"
          aria-label="Fechar notificacao"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

const EXIT_ANIMATION_DURATION = 300

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    // First, mark the toast as exiting to trigger exit animation
    setToasts(prev => prev.map(toast =>
      toast.id === id ? { ...toast, isExiting: true } : toast
    ))

    // After animation completes, actually remove from DOM
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id))
    }, EXIT_ANIMATION_DURATION)
  }, [])

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }, [removeToast])

  const toast = useMemo(() => ({
    success: (message, duration) => addToast(message, 'success', duration),
    error: (message, duration) => addToast(message, 'error', duration),
    warning: (message, duration) => addToast(message, 'warning', duration),
    info: (message, duration) => addToast(message, 'info', duration),
    remove: removeToast
  }), [addToast, removeToast])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* Toast Container - TOP CENTER */}
      <div className="toast-container fixed top-4 left-1/2 -translate-x-1/2 z-[99999] flex flex-col items-center gap-3 pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem
              id={t.id}
              message={t.message}
              type={t.type}
              isExiting={t.isExiting}
              onClose={removeToast}
            />
          </div>
        ))}
      </div>
      <style>{`
        @keyframes toast-in {
          0% {
            opacity: 0;
            transform: translateY(-100%) scale(0.95);
          }
          100% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .animate-toast-in {
          animation: toast-in 0.3s ease-out;
        }
        @keyframes toast-out {
          0% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
          100% {
            opacity: 0;
            transform: translateY(-100%) scale(0.95);
          }
        }
        .animate-toast-out {
          animation: toast-out 0.3s ease-in forwards;
        }
      `}</style>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

export default ToastProvider

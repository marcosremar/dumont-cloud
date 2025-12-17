import { useState, useEffect } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export function ErrorState({
  message,
  onRetry,
  retryText = 'Tentar novamente',
  autoRetry = false,
  autoRetryDelay = 5000
}) {
  const [countdown, setCountdown] = useState(autoRetry ? Math.ceil(autoRetryDelay / 1000) : 0)
  const [isRetrying, setIsRetrying] = useState(false)

  useEffect(() => {
    if (!autoRetry || countdown <= 0) return

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          handleRetry()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [autoRetry])

  const handleRetry = async () => {
    if (!onRetry) return
    setIsRetrying(true)
    try {
      await onRetry()
    } finally {
      setIsRetrying(false)
      if (autoRetry) {
        setCountdown(Math.ceil(autoRetryDelay / 1000))
      }
    }
  }

  return (
    <div className="error-state flex flex-col items-center justify-center py-8 px-4">
      <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <AlertCircle className="w-7 h-7 text-red-400" />
      </div>

      <h3 className="text-white font-medium text-sm mb-1">Algo deu errado</h3>
      <p className="text-gray-400 text-sm text-center mb-4 max-w-xs">
        {message || 'Ocorreu um erro ao carregar os dados.'}
      </p>

      <div className="flex items-center gap-3">
        <button
          onClick={handleRetry}
          disabled={isRetrying}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-300 text-sm font-medium transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
          {isRetrying ? 'Tentando...' : retryText}
        </button>
      </div>

      {autoRetry && countdown > 0 && !isRetrying && (
        <p className="text-gray-500 text-xs mt-3">
          Tentando novamente em {countdown}s...
        </p>
      )}
    </div>
  )
}

export default ErrorState

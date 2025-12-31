import { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Clock,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  FileText
} from 'lucide-react'
import {
  fetchWebhookLogs,
  selectWebhookLogs,
  selectLogsLoading,
} from '../store/slices/webhooksSlice'

// Status indicator component for log entries
function StatusIndicator({ statusCode }) {
  if (!statusCode) {
    return (
      <div className="flex items-center gap-1.5">
        <XCircle size={14} className="text-red-400" />
        <span className="text-red-400 text-xs font-medium">Failed</span>
      </div>
    )
  }

  if (statusCode >= 200 && statusCode < 300) {
    return (
      <div className="flex items-center gap-1.5">
        <CheckCircle size={14} className="text-green-400" />
        <span className="text-green-400 text-xs font-medium">{statusCode}</span>
      </div>
    )
  }

  if (statusCode >= 400) {
    return (
      <div className="flex items-center gap-1.5">
        <XCircle size={14} className="text-red-400" />
        <span className="text-red-400 text-xs font-medium">{statusCode}</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <AlertTriangle size={14} className="text-yellow-400" />
      <span className="text-yellow-400 text-xs font-medium">{statusCode}</span>
    </div>
  )
}

// Format relative time for display
function formatRelativeTime(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString()
}

// Individual log row component
function LogRow({ log, compact = false }) {
  const [showDetails, setShowDetails] = useState(false)

  const statusClass = log.status_code >= 200 && log.status_code < 300
    ? 'border-l-green-500/50'
    : log.status_code >= 400 || !log.status_code
      ? 'border-l-red-500/50'
      : 'border-l-yellow-500/50'

  return (
    <div
      className={`bg-white/5 rounded-lg border-l-2 ${statusClass} transition-colors hover:bg-white/[0.07] ${compact ? 'p-2' : 'p-3'}`}
    >
      <div className="flex items-start gap-3">
        {/* Status and event info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-xs font-medium bg-brand-500/20 text-brand-400`}>
              {log.event_type}
            </span>
            <StatusIndicator statusCode={log.status_code} />
            {log.attempt > 1 && (
              <span className="px-2 py-0.5 rounded text-xs bg-orange-500/20 text-orange-400">
                Attempt {log.attempt}
              </span>
            )}
          </div>

          {/* Timestamp */}
          <div className="flex items-center gap-1.5 mt-1.5 text-gray-500 text-xs">
            <Clock size={12} />
            <span title={new Date(log.created_at).toLocaleString()}>
              {formatRelativeTime(log.created_at)}
            </span>
            <span className="text-gray-600 mx-1">-</span>
            <span className="text-gray-500">
              {new Date(log.created_at).toLocaleTimeString()}
            </span>
          </div>

          {/* Error message if present */}
          {log.error && (
            <div
              className="mt-2 text-red-400 text-xs cursor-pointer"
              onClick={() => setShowDetails(!showDetails)}
            >
              <div className="flex items-start gap-1.5">
                <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
                <span className={showDetails ? '' : 'truncate'}>
                  {log.error}
                </span>
              </div>
            </div>
          )}

          {/* Response details if expanded and available */}
          {showDetails && log.response && (
            <div className="mt-2 p-2 bg-black/30 rounded text-xs text-gray-400 font-mono overflow-x-auto">
              <pre className="whitespace-pre-wrap break-all">{log.response}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Empty state component
function EmptyLogs() {
  return (
    <div className="text-center py-8">
      <FileText className="w-10 h-10 text-gray-600 mx-auto mb-3" />
      <div className="text-gray-400 text-sm font-medium mb-1">No delivery logs yet</div>
      <p className="text-gray-500 text-xs">
        Logs will appear here when webhook deliveries are attempted
      </p>
    </div>
  )
}

// Loading state component
function LoadingLogs() {
  return (
    <div className="flex items-center justify-center py-8 text-gray-400">
      <RefreshCw size={18} className="animate-spin mr-2" />
      <span className="text-sm">Loading delivery logs...</span>
    </div>
  )
}

// Main WebhookLogViewer component
export default function WebhookLogViewer({
  webhookId,
  maxHeight = 'max-h-80',
  showTitle = true,
  compact = false,
  autoRefresh = false,
  refreshInterval = 30000
}) {
  const dispatch = useDispatch()
  const logs = useSelector(selectWebhookLogs(webhookId))
  const logsLoading = useSelector(selectLogsLoading)
  const [page, setPage] = useState(0)
  const pageSize = compact ? 5 : 10

  // Fetch logs on mount and optionally auto-refresh
  useEffect(() => {
    if (webhookId) {
      dispatch(fetchWebhookLogs(webhookId))

      if (autoRefresh) {
        const interval = setInterval(() => {
          dispatch(fetchWebhookLogs(webhookId))
        }, refreshInterval)
        return () => clearInterval(interval)
      }
    }
  }, [dispatch, webhookId, autoRefresh, refreshInterval])

  // Manual refresh handler
  const handleRefresh = () => {
    if (webhookId) {
      dispatch(fetchWebhookLogs(webhookId))
    }
  }

  // Pagination
  const totalPages = Math.ceil(logs.length / pageSize)
  const paginatedLogs = logs.slice(page * pageSize, (page + 1) * pageSize)

  // Reset page when logs change
  useEffect(() => {
    if (page >= totalPages && totalPages > 0) {
      setPage(0)
    }
  }, [logs.length, totalPages, page])

  if (logsLoading && logs.length === 0) {
    return <LoadingLogs />
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      {showTitle && (
        <div className="flex items-center justify-between">
          <div className="text-gray-400 text-sm font-medium">
            Delivery Logs
            {logs.length > 0 && (
              <span className="text-gray-500 font-normal ml-2">
                ({logs.length} {logs.length === 1 ? 'entry' : 'entries'})
              </span>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={logsLoading}
            className="p-1.5 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
            title="Refresh logs"
          >
            <RefreshCw size={14} className={logsLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      )}

      {/* Logs list */}
      {logs.length === 0 ? (
        <EmptyLogs />
      ) : (
        <>
          <div className={`space-y-2 overflow-y-auto ${maxHeight}`}>
            {paginatedLogs.map((log, index) => (
              <LogRow
                key={log.id || `${webhookId}-${index}`}
                log={log}
                compact={compact}
              />
            ))}
          </div>

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2 border-t border-white/5">
              <div className="text-gray-500 text-xs">
                Page {page + 1} of {totalPages}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-1 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="p-1 rounded hover:bg-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// Export a simple inline version for use in WebhookRow expansion
export function WebhookLogsInline({ webhookId }) {
  return (
    <WebhookLogViewer
      webhookId={webhookId}
      maxHeight="max-h-64"
      showTitle={true}
      compact={false}
    />
  )
}

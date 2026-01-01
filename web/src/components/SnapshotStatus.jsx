import { useState, useEffect, useCallback } from 'react'
import { Camera, Clock, CheckCircle, AlertCircle, AlertTriangle, Pause, RefreshCw } from 'lucide-react'
import {
  getSnapshotStatus,
  formatSnapshotTime,
  getStatusColor,
  getStatusBgColor
} from '../api/snapshots'

/**
 * SnapshotStatus - Dashboard component showing snapshot health overview
 *
 * Displays aggregate snapshot status across all instances with:
 * - Overall health indicator
 * - Status counts (success, failed, overdue, pending)
 * - Per-instance last snapshot timestamps
 */
export default function SnapshotStatus({ refreshInterval = 30000 }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getSnapshotStatus()
      setStatus(data)
      setError(null)
      setLastRefresh(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()

    // Set up polling if interval is provided
    if (refreshInterval > 0) {
      const interval = setInterval(fetchStatus, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [fetchStatus, refreshInterval])

  const handleRefresh = () => {
    setLoading(true)
    fetchStatus()
  }

  // Loading skeleton
  if (loading && !status) {
    return (
      <div className="snapshot-status-card skeleton">
        <style jsx>{skeletonStyles}</style>
      </div>
    )
  }

  // Error state
  if (error && !status) {
    return (
      <div className="snapshot-status-card">
        <div className="card-header">
          <h3>
            <Camera size={18} className="icon-purple" />
            Snapshot Status
          </h3>
        </div>
        <div className="error-state">
          <AlertCircle size={24} className="icon-red" />
          <p>{error}</p>
          <button onClick={handleRefresh} className="retry-btn">
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
        <style jsx>{cardStyles}</style>
      </div>
    )
  }

  // No data or no instances
  if (!status || status.total_instances === 0) {
    return (
      <div className="snapshot-status-card">
        <div className="card-header">
          <h3>
            <Camera size={18} className="icon-purple" />
            Snapshot Status
          </h3>
        </div>
        <div className="empty-state">
          <Camera size={32} className="icon-muted" />
          <p>No instances configured</p>
        </div>
        <style jsx>{cardStyles}</style>
      </div>
    )
  }

  const { healthy, status_counts, enabled_count, disabled_count, instances } = status

  return (
    <div className="snapshot-status-card">
      <div className="card-header">
        <h3>
          <Camera size={18} className="icon-purple" />
          Snapshot Status
        </h3>
        <div className="header-actions">
          <button
            onClick={handleRefresh}
            className="refresh-btn"
            disabled={loading}
            title="Refresh status"
          >
            <RefreshCw size={14} className={loading ? 'spinning' : ''} />
          </button>
          <HealthBadge healthy={healthy} />
        </div>
      </div>

      {/* Status Summary */}
      <div className="stats-grid">
        <StatusBox
          icon={CheckCircle}
          count={status_counts.success}
          label="Success"
          color="green"
        />
        <StatusBox
          icon={AlertCircle}
          count={status_counts.failed}
          label="Failed"
          color="red"
        />
        <StatusBox
          icon={AlertTriangle}
          count={status_counts.overdue}
          label="Overdue"
          color="yellow"
        />
        <StatusBox
          icon={Clock}
          count={status_counts.pending}
          label="Pending"
          color="blue"
        />
      </div>

      {/* Instance List */}
      {instances && instances.length > 0 && (
        <div className="instances-list">
          <div className="list-header">
            <span>Instance</span>
            <span>Last Snapshot</span>
          </div>
          {instances.slice(0, 5).map((instance) => (
            <InstanceRow key={instance.instance_id} instance={instance} />
          ))}
          {instances.length > 5 && (
            <div className="more-instances">
              +{instances.length - 5} more instances
            </div>
          )}
        </div>
      )}

      {/* Footer with counts */}
      <div className="card-footer">
        <span className="footer-stat">
          <CheckCircle size={12} className="icon-green" />
          {enabled_count} enabled
        </span>
        <span className="footer-stat">
          <Pause size={12} className="icon-muted" />
          {disabled_count} disabled
        </span>
        {lastRefresh && (
          <span className="footer-stat last-refresh">
            Updated {formatSnapshotTime(lastRefresh.toISOString())}
          </span>
        )}
      </div>

      <style jsx>{cardStyles}</style>
    </div>
  )
}

/**
 * Health indicator badge
 */
function HealthBadge({ healthy }) {
  if (healthy) {
    return (
      <span className="health-badge health-good">
        <CheckCircle size={12} />
        Healthy
      </span>
    )
  }
  return (
    <span className="health-badge health-warning">
      <AlertTriangle size={12} />
      Attention
    </span>
  )
}

/**
 * Status count box
 */
function StatusBox({ icon: Icon, count, label, color }) {
  const colorClasses = {
    green: 'status-box-green',
    red: 'status-box-red',
    yellow: 'status-box-yellow',
    blue: 'status-box-blue'
  }

  return (
    <div className={`status-box ${colorClasses[color]}`}>
      <Icon size={16} />
      <div className="status-info">
        <span className="status-count">{count}</span>
        <span className="status-label">{label}</span>
      </div>
    </div>
  )
}

/**
 * Instance status row
 */
function InstanceRow({ instance }) {
  const statusIcon = getStatusIcon(instance.status)
  const colorClass = getStatusColor(instance.status)
  const bgClass = getStatusBgColor(instance.status)

  return (
    <div className={`instance-row ${bgClass}`}>
      <div className="instance-info">
        <span className={`status-dot ${colorClass}`}>
          {statusIcon}
        </span>
        <span className="instance-id">{instance.instance_id}</span>
      </div>
      <div className="instance-timestamp">
        <Clock size={12} className="icon-muted" />
        <span>{formatSnapshotTime(instance.last_snapshot_at)}</span>
      </div>
    </div>
  )
}

/**
 * Get appropriate icon for status
 */
function getStatusIcon(status) {
  switch (status) {
    case 'success':
      return <CheckCircle size={12} />
    case 'failed':
      return <AlertCircle size={12} />
    case 'overdue':
      return <AlertTriangle size={12} />
    case 'pending':
      return <Clock size={12} />
    case 'disabled':
      return <Pause size={12} />
    default:
      return <Clock size={12} />
  }
}

// Skeleton loading styles
const skeletonStyles = `
  .snapshot-status-card {
    background: #1c211c;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
    min-height: 280px;
  }
  .skeleton {
    position: relative;
    overflow: hidden;
  }
  .skeleton::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
    animation: shimmer 1.5s infinite;
  }
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
`

// Main card styles
const cardStyles = `
  .snapshot-status-card {
    background: #1c211c;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .card-header h3 {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    margin: 0;
    color: #fff;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: none;
    background: #30363d;
    border-radius: 6px;
    color: #9ca3af;
    cursor: pointer;
    transition: all 0.2s;
  }

  .refresh-btn:hover {
    background: #3d444d;
    color: #fff;
  }

  .refresh-btn:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .spinning {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .icon-purple { color: #a855f7; }
  .icon-muted { color: #4b5563; }
  .icon-green { color: #22c55e; }
  .icon-red { color: #ef4444; }
  .icon-yellow { color: #eab308; }
  .icon-blue { color: #3b82f6; }

  .health-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 500;
  }

  .health-good {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  .health-warning {
    background: rgba(234, 179, 8, 0.15);
    color: #eab308;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }

  @media (max-width: 640px) {
    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  .status-box {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #30363d;
    background: #161a16;
  }

  .status-box-green { border-color: rgba(34, 197, 94, 0.3); }
  .status-box-green svg { color: #22c55e; }

  .status-box-red { border-color: rgba(239, 68, 68, 0.3); }
  .status-box-red svg { color: #ef4444; }

  .status-box-yellow { border-color: rgba(234, 179, 8, 0.3); }
  .status-box-yellow svg { color: #eab308; }

  .status-box-blue { border-color: rgba(59, 130, 246, 0.3); }
  .status-box-blue svg { color: #3b82f6; }

  .status-info {
    display: flex;
    flex-direction: column;
  }

  .status-count {
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }

  .status-label {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    margin-top: 2px;
  }

  .instances-list {
    border: 1px solid #30363d;
    border-radius: 8px;
    overflow: hidden;
  }

  .list-header {
    display: flex;
    justify-content: space-between;
    padding: 8px 12px;
    background: #161a16;
    font-size: 10px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .instance-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    border-top: 1px solid #30363d;
    transition: background 0.2s;
  }

  .instance-row:hover {
    background: #1f251f;
  }

  .instance-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .status-dot {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .instance-id {
    font-size: 13px;
    color: #fff;
    font-family: ui-monospace, monospace;
  }

  .instance-timestamp {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #9ca3af;
  }

  .more-instances {
    padding: 8px 12px;
    text-align: center;
    font-size: 12px;
    color: #6b7280;
    border-top: 1px solid #30363d;
    background: #161a16;
  }

  .card-footer {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-top: 12px;
    border-top: 1px solid #30363d;
    font-size: 11px;
  }

  .footer-stat {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #6b7280;
  }

  .last-refresh {
    margin-left: auto;
    font-style: italic;
  }

  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 32px 16px;
    text-align: center;
  }

  .error-state p {
    color: #ef4444;
    font-size: 13px;
    margin: 0;
  }

  .retry-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: 1px solid #30363d;
    background: transparent;
    border-radius: 6px;
    color: #9ca3af;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .retry-btn:hover {
    background: #30363d;
    color: #fff;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 32px 16px;
    text-align: center;
  }

  .empty-state p {
    color: #6b7280;
    font-size: 13px;
    margin: 0;
  }
`

// Named exports for flexibility
export { HealthBadge, StatusBox, InstanceRow }

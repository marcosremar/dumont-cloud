import React, { useState, useEffect, useCallback } from 'react';
import { apiGet, isDemoMode } from '../utils/api';
import {
  Clock,
  User,
  ChevronLeft,
  ChevronRight,
  Filter,
  Activity,
  UserPlus,
  UserMinus,
  Shield,
  Settings,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import {
  Table,
  Badge,
  Button,
  SelectCompound as Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from './tailadmin-ui';
import { EmptyState } from './EmptyState';
import { SkeletonList } from './Skeleton';

// Demo audit log data
const DEMO_AUDIT_LOGS = [
  {
    id: 1,
    team_id: 1,
    user_id: 'admin@dumont.cloud',
    action: 'member_added',
    resource_type: 'team_member',
    resource_id: '2',
    details: { email: 'developer@dumont.cloud', role: 'Developer' },
    status: 'success',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 2,
    team_id: 1,
    user_id: 'admin@dumont.cloud',
    action: 'role_changed',
    resource_type: 'team_member',
    resource_id: '3',
    details: { email: 'viewer@dumont.cloud', from_role: 'Developer', to_role: 'Viewer' },
    status: 'success',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    team_id: 1,
    user_id: 'developer@dumont.cloud',
    action: 'gpu_provisioned',
    resource_type: 'instance',
    resource_id: 'inst-12345',
    details: { gpu_type: 'RTX 4090', provider: 'vast.ai' },
    status: 'success',
    ip_address: '10.0.0.50',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 4,
    team_id: 1,
    user_id: 'admin@dumont.cloud',
    action: 'invitation_sent',
    resource_type: 'team_invitation',
    resource_id: '1',
    details: { email: 'newuser@dumont.cloud', role: 'Developer' },
    status: 'success',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 5,
    team_id: 1,
    user_id: 'viewer@dumont.cloud',
    action: 'gpu_provisioned',
    resource_type: 'instance',
    resource_id: 'inst-67890',
    details: { gpu_type: 'RTX 3090', error: 'Permission denied' },
    status: 'denied',
    ip_address: '10.0.0.75',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 6,
    team_id: 1,
    user_id: 'admin@dumont.cloud',
    action: 'quota_updated',
    resource_type: 'team_quota',
    resource_id: '1',
    details: { max_concurrent_instances: 10, max_monthly_budget_usd: 5000 },
    status: 'success',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 7,
    team_id: 1,
    user_id: 'admin@dumont.cloud',
    action: 'member_removed',
    resource_type: 'team_member',
    resource_id: '5',
    details: { email: 'former@dumont.cloud', role: 'Developer' },
    status: 'success',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 96 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 8,
    team_id: 1,
    user_id: 'developer@dumont.cloud',
    action: 'gpu_terminated',
    resource_type: 'instance',
    resource_id: 'inst-12345',
    details: { gpu_type: 'RTX 4090', runtime_hours: 24 },
    status: 'success',
    ip_address: '10.0.0.50',
    user_agent: 'Mozilla/5.0',
    timestamp: new Date(Date.now() - 100 * 60 * 60 * 1000).toISOString(),
  },
];

// Action icon mapping
const getActionIcon = (action) => {
  switch (action) {
    case 'member_added':
    case 'invitation_sent':
    case 'invitation_accepted':
      return UserPlus;
    case 'member_removed':
    case 'invitation_revoked':
      return UserMinus;
    case 'role_changed':
      return Shield;
    case 'quota_updated':
    case 'team_updated':
    case 'settings_changed':
      return Settings;
    case 'gpu_provisioned':
    case 'gpu_terminated':
      return Activity;
    default:
      return Activity;
  }
};

// Action label mapping
const getActionLabel = (action) => {
  const labels = {
    member_added: 'Member Added',
    member_removed: 'Member Removed',
    role_changed: 'Role Changed',
    invitation_sent: 'Invitation Sent',
    invitation_accepted: 'Invitation Accepted',
    invitation_revoked: 'Invitation Revoked',
    gpu_provisioned: 'GPU Provisioned',
    gpu_terminated: 'GPU Terminated',
    quota_updated: 'Quota Updated',
    team_created: 'Team Created',
    team_updated: 'Team Updated',
    settings_changed: 'Settings Changed',
  };
  return labels[action] || action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Status badge variant
const getStatusVariant = (status) => {
  switch (status) {
    case 'success':
      return 'success';
    case 'denied':
    case 'failed':
      return 'error';
    case 'pending':
      return 'warning';
    default:
      return 'gray';
  }
};

// Status icon
const getStatusIcon = (status) => {
  switch (status) {
    case 'success':
      return CheckCircle;
    case 'denied':
    case 'failed':
      return XCircle;
    case 'pending':
      return AlertTriangle;
    default:
      return Activity;
  }
};

export default function AuditLogTable({ teamId, compact = false }) {
  const isDemo = isDemoMode();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = compact ? 5 : 10;

  // Filter state
  const [actionFilter, setActionFilter] = useState('all');

  const fetchAuditLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (isDemo) {
        await new Promise(r => setTimeout(r, 500));
        let filteredLogs = [...DEMO_AUDIT_LOGS];

        // Apply action filter
        if (actionFilter !== 'all') {
          filteredLogs = filteredLogs.filter(log => log.action === actionFilter);
        }

        // Sort by timestamp descending
        filteredLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        // Paginate
        const startIndex = (page - 1) * pageSize;
        const paginatedLogs = filteredLogs.slice(startIndex, startIndex + pageSize);

        setLogs(paginatedLogs);
        setTotalCount(filteredLogs.length);
        setTotalPages(Math.ceil(filteredLogs.length / pageSize));
        setLoading(false);
        return;
      }

      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: ((page - 1) * pageSize).toString(),
      });

      if (actionFilter !== 'all') {
        params.append('action', actionFilter);
      }

      const res = await apiGet(`/api/v1/teams/${teamId}/audit-logs?${params}`);

      if (!res.ok) {
        throw new Error('Failed to fetch audit logs');
      }

      const data = await res.json();
      setLogs(data.logs || []);
      setTotalCount(data.total || 0);
      setTotalPages(Math.ceil((data.total || 0) / pageSize));
    } catch (err) {
      setError(err.message);
      if (isDemo) {
        setLogs(DEMO_AUDIT_LOGS.slice(0, pageSize));
        setTotalCount(DEMO_AUDIT_LOGS.length);
        setTotalPages(Math.ceil(DEMO_AUDIT_LOGS.length / pageSize));
      }
    } finally {
      setLoading(false);
    }
  }, [teamId, page, pageSize, actionFilter, isDemo]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  // Reset to page 1 when filter changes
  useEffect(() => {
    setPage(1);
  }, [actionFilter]);

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    }
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    }
    if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    }

    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDetails = (action, details) => {
    if (!details) return null;

    switch (action) {
      case 'member_added':
      case 'member_removed':
        return details.email ? `${details.email} (${details.role})` : null;
      case 'role_changed':
        return details.from_role && details.to_role
          ? `${details.from_role} → ${details.to_role}`
          : null;
      case 'invitation_sent':
        return details.email ? `${details.email} as ${details.role}` : null;
      case 'gpu_provisioned':
      case 'gpu_terminated':
        return details.gpu_type || null;
      case 'quota_updated':
        const changes = [];
        if (details.max_concurrent_instances) {
          changes.push(`Instances: ${details.max_concurrent_instances}`);
        }
        if (details.max_monthly_budget_usd) {
          changes.push(`Budget: $${details.max_monthly_budget_usd}`);
        }
        return changes.length > 0 ? changes.join(', ') : null;
      default:
        return null;
    }
  };

  const columns = [
    {
      header: 'Timestamp',
      accessor: 'timestamp',
      render: (value) => (
        <div className="flex items-center gap-2 text-gray-400">
          <Clock className="w-4 h-4" />
          <span className="text-sm">{formatTimestamp(value)}</span>
        </div>
      ),
    },
    {
      header: 'Actor',
      accessor: 'user_id',
      render: (value) => (
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
            <User className="w-4 h-4 text-brand-500" />
          </div>
          <span className="text-white text-sm font-medium">{value}</span>
        </div>
      ),
    },
    {
      header: 'Action',
      accessor: 'action',
      render: (value, row) => {
        const ActionIcon = getActionIcon(value);
        return (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
              <ActionIcon className="w-4 h-4 text-gray-400" />
            </div>
            <div>
              <p className="text-white text-sm font-medium">{getActionLabel(value)}</p>
              {formatDetails(value, row.details) && (
                <p className="text-gray-500 text-xs">{formatDetails(value, row.details)}</p>
              )}
            </div>
          </div>
        );
      },
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (value) => {
        const StatusIcon = getStatusIcon(value);
        return (
          <div className="flex items-center gap-2">
            <StatusIcon className={`w-4 h-4 ${
              value === 'success' ? 'text-success-500' :
              value === 'denied' || value === 'failed' ? 'text-error-500' :
              'text-warning-500'
            }`} />
            <Badge variant={getStatusVariant(value)} size="sm">
              {value?.charAt(0).toUpperCase() + value?.slice(1) || 'Unknown'}
            </Badge>
          </div>
        );
      },
    },
  ];

  // Compact columns for compact mode
  const compactColumns = [
    {
      header: 'Time',
      accessor: 'timestamp',
      render: (value) => (
        <span className="text-gray-400 text-sm">{formatTimestamp(value)}</span>
      ),
    },
    {
      header: 'Actor',
      accessor: 'user_id',
      render: (value) => (
        <span className="text-white text-sm">{value}</span>
      ),
    },
    {
      header: 'Action',
      accessor: 'action',
      render: (value) => (
        <span className="text-gray-300 text-sm">{getActionLabel(value)}</span>
      ),
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (value) => (
        <Badge variant={getStatusVariant(value)} size="sm">
          {value?.charAt(0).toUpperCase() + value?.slice(1) || 'Unknown'}
        </Badge>
      ),
    },
  ];

  const actionOptions = [
    { value: 'all', label: 'All Actions' },
    { value: 'member_added', label: 'Member Added' },
    { value: 'member_removed', label: 'Member Removed' },
    { value: 'role_changed', label: 'Role Changed' },
    { value: 'invitation_sent', label: 'Invitation Sent' },
    { value: 'gpu_provisioned', label: 'GPU Provisioned' },
    { value: 'gpu_terminated', label: 'GPU Terminated' },
    { value: 'quota_updated', label: 'Quota Updated' },
  ];

  if (loading) {
    return (
      <div className="p-6">
        <SkeletonList count={compact ? 3 : 5} type="machine" />
      </div>
    );
  }

  return (
    <div>
      {/* Filter Bar */}
      {!compact && (
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-gray-400" />
            <div className="w-48">
              <Select
                value={actionFilter}
                onValueChange={setActionFilter}
              >
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Filter by action" />
                </SelectTrigger>
                <SelectContent>
                  {actionOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <span className="text-sm text-gray-400">
            {totalCount} log{totalCount !== 1 ? 's' : ''} total
          </span>
        </div>
      )}

      {/* Table */}
      {logs.length === 0 ? (
        <div className="p-6">
          <EmptyState
            icon="activity"
            title="No audit logs yet"
            description="Audit logs will appear here as team members perform actions."
          />
        </div>
      ) : (
        <Table
          columns={compact ? compactColumns : columns}
          data={logs}
          emptyMessage="No audit logs found"
        />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between">
          <span className="text-sm text-gray-400">
            Page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              icon={ChevronLeft}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon={ChevronRight}
              iconPosition="right"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

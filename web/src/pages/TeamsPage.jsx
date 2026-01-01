import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost, isDemoMode } from '../utils/api';
import {
  Users,
  Plus,
  Shield,
  Settings,
  ChevronRight,
  Building2,
  UserPlus,
  Activity
} from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Table,
  Badge,
  StatCard,
  StatsGrid,
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  Input,
} from '../components/tailadmin-ui';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { SkeletonList } from '../components/Skeleton';
import { useToast } from '../components/Toast';

// Demo data for teams
const DEMO_TEAMS = [
  {
    id: 1,
    name: 'Engineering',
    slug: 'engineering',
    description: 'Core engineering team',
    member_count: 8,
    user_role: 'Admin',
    status: 'active',
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 2,
    name: 'Data Science',
    slug: 'data-science',
    description: 'ML and data analytics team',
    member_count: 5,
    user_role: 'Developer',
    status: 'active',
    created_at: '2024-02-20T14:30:00Z',
  },
  {
    id: 3,
    name: 'Research',
    slug: 'research',
    description: 'Research and development',
    member_count: 3,
    user_role: 'Viewer',
    status: 'active',
    created_at: '2024-03-10T09:15:00Z',
  },
];

export default function TeamsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const isDemo = isDemoMode();

  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDescription, setNewTeamDescription] = useState('');

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      setLoading(true);
      setError(null);

      if (isDemo) {
        // Simulate loading delay
        await new Promise(r => setTimeout(r, 500));
        setTeams(DEMO_TEAMS);
        setLoading(false);
        return;
      }

      const res = await apiGet('/api/v1/teams');
      if (!res.ok) {
        throw new Error('Failed to fetch teams');
      }
      const data = await res.json();
      setTeams(data.teams || data || []);
    } catch (err) {
      setError(err.message);
      // Fallback to demo data on error
      if (isDemo) {
        setTeams(DEMO_TEAMS);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async () => {
    if (!newTeamName.trim()) {
      toast.error('Team name is required');
      return;
    }

    setCreating(true);
    try {
      if (isDemo) {
        await new Promise(r => setTimeout(r, 1000));
        const newTeam = {
          id: Date.now(),
          name: newTeamName,
          slug: newTeamName.toLowerCase().replace(/\s+/g, '-'),
          description: newTeamDescription,
          member_count: 1,
          user_role: 'Admin',
          status: 'active',
          created_at: new Date().toISOString(),
        };
        setTeams(prev => [newTeam, ...prev]);
        toast.success(`Team "${newTeamName}" created successfully!`);
        setCreateModalOpen(false);
        setNewTeamName('');
        setNewTeamDescription('');
        return;
      }

      const res = await apiPost('/api/v1/teams', {
        name: newTeamName,
        description: newTeamDescription,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Failed to create team');
      }

      toast.success(`Team "${newTeamName}" created successfully!`);
      setCreateModalOpen(false);
      setNewTeamName('');
      setNewTeamDescription('');
      fetchTeams();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleTeamClick = (team) => {
    navigate(`/app/teams/${team.id}`);
  };

  const getRoleBadgeVariant = (role) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return 'primary';
      case 'developer':
        return 'success';
      case 'viewer':
        return 'gray';
      default:
        return 'gray';
    }
  };

  const getStatusBadgeVariant = (status) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'warning';
      case 'deleted':
        return 'error';
      default:
        return 'gray';
    }
  };

  // Calculate stats
  const totalTeams = teams.length;
  const adminTeams = teams.filter(t => t.user_role?.toLowerCase() === 'admin').length;
  const totalMembers = teams.reduce((acc, t) => acc + (t.member_count || 0), 0);

  const tableColumns = [
    {
      header: 'Team',
      accessor: 'name',
      render: (value, row) => (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
            <Building2 className="w-5 h-5 text-brand-500" />
          </div>
          <div>
            <p className="font-medium text-white">{value}</p>
            <p className="text-xs text-gray-400">{row.slug}</p>
          </div>
        </div>
      ),
    },
    {
      header: 'Members',
      accessor: 'member_count',
      render: (value) => (
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-gray-400" />
          <span>{value || 0}</span>
        </div>
      ),
    },
    {
      header: 'Your Role',
      accessor: 'user_role',
      render: (value) => (
        <Badge variant={getRoleBadgeVariant(value)} dot>
          {value || 'Member'}
        </Badge>
      ),
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (value) => (
        <Badge variant={getStatusBadgeVariant(value)}>
          {value || 'Active'}
        </Badge>
      ),
    },
    {
      header: '',
      accessor: 'actions',
      render: (_, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleTeamClick(row);
          }}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
        >
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </button>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="page-container">
        <div className="ta-card p-6">
          <SkeletonList count={4} type="machine" />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <div className="stat-card-icon stat-card-icon-primary">
                <Users className="w-5 h-5" />
              </div>
              Teams
            </h1>
            <p className="page-subtitle">Manage your teams and team members</p>
          </div>
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setCreateModalOpen(true)}
            data-testid="create-team-button"
          >
            Create Team
          </Button>
        </div>
      </div>

      {/* Stats Summary */}
      <StatsGrid columns={3} className="mb-6">
        <StatCard
          title="Total Teams"
          value={totalTeams}
          icon={Building2}
          iconColor="primary"
        />
        <StatCard
          title="Admin Access"
          value={adminTeams}
          icon={Shield}
          iconColor="success"
          subtitle="Teams you manage"
        />
        <StatCard
          title="Total Members"
          value={totalMembers}
          icon={UserPlus}
          iconColor="warning"
        />
      </StatsGrid>

      {/* Teams Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Your Teams</CardTitle>
          {teams.length > 0 && (
            <span className="text-sm text-gray-400">{teams.length} teams</span>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {error && !isDemo ? (
            <div className="p-6">
              <ErrorState
                message={error}
                onRetry={fetchTeams}
                retryText="Try again"
              />
            </div>
          ) : teams.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon="users"
                title="No teams yet"
                description="Create your first team to start collaborating with others."
                action={() => setCreateModalOpen(true)}
                actionText="Create Team"
              />
            </div>
          ) : (
            <Table
              columns={tableColumns}
              data={teams}
              onRowClick={handleTeamClick}
              emptyMessage="No teams found"
            />
          )}
        </CardContent>
      </Card>

      {/* Create Team Modal */}
      <AlertDialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-brand-500" />
              Create New Team
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4 pt-4">
                <Input
                  label="Team Name"
                  placeholder="e.g., Engineering"
                  value={newTeamName}
                  onChange={(e) => setNewTeamName(e.target.value)}
                  disabled={creating}
                  data-testid="team-name-input"
                />
                <Input
                  label="Description (optional)"
                  placeholder="e.g., Core engineering team"
                  value={newTeamDescription}
                  onChange={(e) => setNewTeamDescription(e.target.value)}
                  disabled={creating}
                  data-testid="team-description-input"
                />
                <div className="p-3 rounded-lg border border-brand-500/20 bg-brand-500/5">
                  <div className="flex items-center gap-2 text-brand-400 text-sm">
                    <Shield className="w-4 h-4" />
                    <span>You will be the Admin of this team</span>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={creating} onClick={() => {
              setCreateModalOpen(false);
              setNewTeamName('');
              setNewTeamDescription('');
            }}>
              Cancel
            </AlertDialogCancel>
            <Button
              variant="primary"
              onClick={handleCreateTeam}
              loading={creating}
              disabled={creating || !newTeamName.trim()}
              data-testid="confirm-create-team"
            >
              Create Team
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { apiGet, apiPost, apiPut, apiDelete, isDemoMode } from '../utils/api';
import {
  Users,
  UserPlus,
  Shield,
  ArrowLeft,
  Mail,
  Clock,
  Trash2,
  AlertCircle,
  Activity,
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
  SelectCompound as Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  PageHeader,
  Tabs,
  TabsList,
  TabsTrigger,
} from '../components/tailadmin-ui';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { SkeletonList } from '../components/Skeleton';
import { useToast } from '../components/Toast';
import InviteMemberModal from '../components/InviteMemberModal';
import AuditLogTable from '../components/AuditLogTable';

// Demo data for team details
const DEMO_TEAM = {
  id: 1,
  name: 'Engineering',
  slug: 'engineering',
  description: 'Core engineering team',
  owner_user_id: 'admin@dumont.cloud',
  is_active: true,
  member_count: 4,
  user_role: 'Admin',
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  members: [
    {
      id: 1,
      user_id: 'admin@dumont.cloud',
      team_id: 1,
      role_id: 1,
      role_name: 'Admin',
      invited_by_user_id: null,
      joined_at: '2024-01-15T10:00:00Z',
      is_active: true,
    },
    {
      id: 2,
      user_id: 'developer@dumont.cloud',
      team_id: 1,
      role_id: 2,
      role_name: 'Developer',
      invited_by_user_id: 'admin@dumont.cloud',
      joined_at: '2024-01-20T14:30:00Z',
      is_active: true,
    },
    {
      id: 3,
      user_id: 'viewer@dumont.cloud',
      team_id: 1,
      role_id: 3,
      role_name: 'Viewer',
      invited_by_user_id: 'admin@dumont.cloud',
      joined_at: '2024-02-01T09:15:00Z',
      is_active: true,
    },
    {
      id: 4,
      user_id: 'test@test.com',
      team_id: 1,
      role_id: 2,
      role_name: 'Developer',
      invited_by_user_id: 'admin@dumont.cloud',
      joined_at: '2024-02-05T11:00:00Z',
      is_active: true,
    },
  ],
  quota: null,
};

const DEMO_ROLES = [
  { id: 1, name: 'Admin', display_name: 'Admin', description: 'Full control', is_system: true },
  { id: 2, name: 'Developer', display_name: 'Developer', description: 'Limited provisioning', is_system: true },
  { id: 3, name: 'Viewer', display_name: 'Viewer', description: 'Read-only access', is_system: true },
];

const DEMO_INVITATIONS = [
  {
    id: 1,
    team_id: 1,
    email: 'pending@dumont.cloud',
    role_id: 2,
    role_name: 'Developer',
    invited_by_user_id: 'admin@dumont.cloud',
    token: 'abc123',
    expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'pending',
    created_at: new Date().toISOString(),
  },
];

export default function TeamDetailsPage() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const isDemo = isDemoMode();

  // Tab state - initialize from URL hash
  const getInitialTab = () => {
    const hash = location.hash.replace('#', '');
    return hash === 'audit' ? 'audit' : 'members';
  };
  const [activeTab, setActiveTab] = useState(getInitialTab);

  const [team, setTeam] = useState(null);
  const [roles, setRoles] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Invite modal state
  const [inviteModalOpen, setInviteModalOpen] = useState(false);

  // Role change state
  const [changingRole, setChangingRole] = useState(null);

  // Remove member modal state
  const [removeMemberModalOpen, setRemoveMemberModalOpen] = useState(false);
  const [memberToRemove, setMemberToRemove] = useState(null);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    fetchTeamDetails();
  }, [teamId]);

  // Update URL hash when tab changes
  useEffect(() => {
    const newHash = activeTab === 'members' ? '' : `#${activeTab}`;
    if (location.hash !== newHash) {
      window.history.replaceState(null, '', `${location.pathname}${newHash}`);
    }
  }, [activeTab, location.pathname, location.hash]);

  // Handle tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const fetchTeamDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      if (isDemo) {
        await new Promise(r => setTimeout(r, 500));
        setTeam(DEMO_TEAM);
        setRoles(DEMO_ROLES);
        setInvitations(DEMO_INVITATIONS);
        setLoading(false);
        return;
      }

      // Fetch team details, roles, and invitations in parallel
      const [teamRes, rolesRes, invitationsRes] = await Promise.all([
        apiGet(`/api/v1/teams/${teamId}`),
        apiGet(`/api/v1/teams/${teamId}/roles?include_system=true`),
        apiGet(`/api/v1/teams/${teamId}/invitations?status=pending`),
      ]);

      if (!teamRes.ok) {
        throw new Error('Failed to fetch team details');
      }

      const teamData = await teamRes.json();
      setTeam(teamData);

      if (rolesRes.ok) {
        const rolesData = await rolesRes.json();
        setRoles(rolesData.roles || []);
      }

      if (invitationsRes.ok) {
        const invData = await invitationsRes.json();
        setInvitations(invData.invitations || []);
      }
    } catch (err) {
      setError(err.message);
      if (isDemo) {
        setTeam(DEMO_TEAM);
        setRoles(DEMO_ROLES);
        setInvitations(DEMO_INVITATIONS);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInviteSuccess = (invitation, message) => {
    if (isDemo && invitation) {
      setInvitations(prev => [invitation, ...prev]);
    } else {
      fetchTeamDetails();
    }
    toast.success(message);
  };

  const handleInviteError = (message) => {
    toast.error(message);
  };

  const handleRoleChange = async (memberId, memberEmail, newRoleId) => {
    setChangingRole(memberId);
    try {
      if (isDemo) {
        await new Promise(r => setTimeout(r, 500));
        const selectedRole = roles.find(r => r.id === parseInt(newRoleId));
        setTeam(prev => ({
          ...prev,
          members: prev.members.map(m =>
            m.id === memberId
              ? { ...m, role_id: parseInt(newRoleId), role_name: selectedRole?.display_name || selectedRole?.name }
              : m
          ),
        }));
        toast.success(`Role updated successfully`);
        return;
      }

      const res = await apiPut(`/api/v1/teams/${teamId}/members/${memberEmail}/role`, {
        role_id: parseInt(newRoleId),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Failed to update role');
      }

      toast.success(`Role updated successfully`);
      fetchTeamDetails();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setChangingRole(null);
    }
  };

  const handleRemoveMember = async () => {
    if (!memberToRemove) return;

    setRemoving(true);
    try {
      if (isDemo) {
        await new Promise(r => setTimeout(r, 500));
        setTeam(prev => ({
          ...prev,
          members: prev.members.filter(m => m.id !== memberToRemove.id),
          member_count: prev.member_count - 1,
        }));
        toast.success(`${memberToRemove.user_id} has been removed from the team`);
        setRemoveMemberModalOpen(false);
        setMemberToRemove(null);
        return;
      }

      const res = await apiDelete(`/api/v1/teams/${teamId}/members/${memberToRemove.user_id}`);

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Failed to remove member');
      }

      toast.success(`${memberToRemove.user_id} has been removed from the team`);
      setRemoveMemberModalOpen(false);
      setMemberToRemove(null);
      fetchTeamDetails();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRemoving(false);
    }
  };

  const handleRevokeInvitation = async (invitationId) => {
    try {
      if (isDemo) {
        await new Promise(r => setTimeout(r, 500));
        setInvitations(prev => prev.filter(i => i.id !== invitationId));
        toast.success('Invitation revoked');
        return;
      }

      const res = await apiDelete(`/api/v1/teams/${teamId}/invitations/${invitationId}`);

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Failed to revoke invitation');
      }

      toast.success('Invitation revoked');
      fetchTeamDetails();
    } catch (err) {
      toast.error(err.message);
    }
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

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const isAdmin = team?.user_role?.toLowerCase() === 'admin';

  const memberColumns = [
    {
      header: 'Member',
      accessor: 'user_id',
      render: (value, row) => (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
            <span className="text-brand-500 font-medium text-sm">
              {value?.charAt(0)?.toUpperCase() || '?'}
            </span>
          </div>
          <div>
            <p className="font-medium text-white">{value}</p>
            {row.invited_by_user_id && (
              <p className="text-xs text-gray-400">Invited by {row.invited_by_user_id}</p>
            )}
          </div>
        </div>
      ),
    },
    {
      header: 'Role',
      accessor: 'role_name',
      render: (value, row) => {
        if (isAdmin && row.user_id !== team?.owner_user_id) {
          return (
            <div className="relative w-36">
              <Select
                value={String(row.role_id)}
                onValueChange={(newRoleId) => handleRoleChange(row.id, row.user_id, newRoleId)}
              >
                <SelectTrigger
                  className="h-9 text-sm"
                  disabled={changingRole === row.id}
                >
                  <SelectValue placeholder="Select role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={String(role.id)}>
                      {role.display_name || role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        }
        return (
          <Badge variant={getRoleBadgeVariant(value)} dot>
            {value || 'Member'}
          </Badge>
        );
      },
    },
    {
      header: 'Joined',
      accessor: 'joined_at',
      render: (value) => (
        <div className="flex items-center gap-2 text-gray-400">
          <Clock className="w-4 h-4" />
          <span>{formatDate(value)}</span>
        </div>
      ),
    },
    {
      header: '',
      accessor: 'actions',
      render: (_, row) => {
        // Cannot remove team owner or yourself
        if (!isAdmin || row.user_id === team?.owner_user_id) return null;

        return (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMemberToRemove(row);
              setRemoveMemberModalOpen(true);
            }}
            className="p-2 hover:bg-error-500/10 rounded-lg transition-colors text-gray-400 hover:text-error-500"
            title="Remove member"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        );
      },
    },
  ];

  const invitationColumns = [
    {
      header: 'Email',
      accessor: 'email',
      render: (value) => (
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-gray-400" />
          <span className="text-white">{value}</span>
        </div>
      ),
    },
    {
      header: 'Role',
      accessor: 'role_name',
      render: (value) => (
        <Badge variant={getRoleBadgeVariant(value)}>
          {value || 'Member'}
        </Badge>
      ),
    },
    {
      header: 'Expires',
      accessor: 'expires_at',
      render: (value) => (
        <span className="text-gray-400">{formatDate(value)}</span>
      ),
    },
    {
      header: '',
      accessor: 'actions',
      render: (_, row) => {
        if (!isAdmin) return null;
        return (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleRevokeInvitation(row.id);
            }}
            className="p-2 hover:bg-error-500/10 rounded-lg transition-colors text-gray-400 hover:text-error-500"
            title="Revoke invitation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        );
      },
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

  if (error && !team) {
    return (
      <div className="page-container">
        <div className="ta-card p-6">
          <ErrorState
            message={error}
            onRetry={fetchTeamDetails}
            retryText="Try again"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Page Header with Breadcrumb */}
      <PageHeader
        title={team?.name || 'Team Details'}
        subtitle={team?.description || 'Manage team members and settings'}
        breadcrumbs={[
          { label: 'Teams', href: '/app/teams' },
          { label: team?.name || 'Team' },
        ]}
        actions={
          isAdmin && (
            <Button
              variant="primary"
              icon={UserPlus}
              onClick={() => setInviteModalOpen(true)}
              data-testid="invite-member-button"
            >
              Invite Member
            </Button>
          )
        }
      />

      {/* Back Button */}
      <div className="mb-6">
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate('/app/teams')}
          className="text-gray-400 hover:text-white"
        >
          Back to Teams
        </Button>
      </div>

      {/* Stats Summary */}
      <StatsGrid columns={3} className="mb-6">
        <StatCard
          title="Total Members"
          value={team?.member_count || team?.members?.length || 0}
          icon={Users}
          iconColor="primary"
        />
        <StatCard
          title="Your Role"
          value={team?.user_role || 'Member'}
          icon={Shield}
          iconColor="success"
        />
        <StatCard
          title="Pending Invites"
          value={invitations.length}
          icon={Mail}
          iconColor="warning"
        />
      </StatsGrid>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="mb-6">
        <TabsList className="mb-6">
          <TabsTrigger value="members" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Members
          </TabsTrigger>
          <TabsTrigger value="audit" className="flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Audit Log
          </TabsTrigger>
        </TabsList>

        {/* Members Tab Content */}
        {activeTab === 'members' && (
          <>
            {/* Members Table */}
            <Card className="mb-6">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-brand-500" />
                  Team Members
                </CardTitle>
                {team?.members?.length > 0 && (
                  <span className="text-sm text-gray-400">
                    {team.members.length} member{team.members.length !== 1 ? 's' : ''}
                  </span>
                )}
              </CardHeader>
              <CardContent className="p-0">
                {team?.members?.length === 0 ? (
                  <div className="p-6">
                    <EmptyState
                      icon="users"
                      title="No members yet"
                      description="Invite team members to start collaborating."
                      action={isAdmin ? () => setInviteModalOpen(true) : undefined}
                      actionText={isAdmin ? 'Invite Member' : undefined}
                    />
                  </div>
                ) : (
                  <Table
                    columns={memberColumns}
                    data={team?.members || []}
                    emptyMessage="No members found"
                  />
                )}
              </CardContent>
            </Card>

            {/* Pending Invitations */}
            {isAdmin && invitations.length > 0 && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Mail className="w-5 h-5 text-warning-500" />
                    Pending Invitations
                  </CardTitle>
                  <span className="text-sm text-gray-400">
                    {invitations.length} pending
                  </span>
                </CardHeader>
                <CardContent className="p-0">
                  <Table
                    columns={invitationColumns}
                    data={invitations}
                    emptyMessage="No pending invitations"
                  />
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Audit Log Tab Content */}
        {activeTab === 'audit' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-brand-500" />
                Audit Log
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <AuditLogTable teamId={teamId} />
            </CardContent>
          </Card>
        )}
      </Tabs>

      {/* Invite Member Modal */}
      <InviteMemberModal
        open={inviteModalOpen}
        onOpenChange={setInviteModalOpen}
        teamId={teamId}
        roles={roles}
        onSuccess={handleInviteSuccess}
        onError={handleInviteError}
      />

      {/* Remove Member Confirmation Modal */}
      <AlertDialog open={removeMemberModalOpen} onOpenChange={setRemoveMemberModalOpen}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-error-500">
              <AlertCircle className="w-5 h-5" />
              Remove Team Member
            </AlertDialogTitle>
            <AlertDialogDescription>
              <p className="text-gray-400 mt-2">
                Are you sure you want to remove <span className="text-white font-medium">{memberToRemove?.user_id}</span> from the team?
              </p>
              <p className="text-gray-500 text-sm mt-2">
                This action cannot be undone. The member will lose access to all team resources.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={removing} onClick={() => {
              setRemoveMemberModalOpen(false);
              setMemberToRemove(null);
            }}>
              Cancel
            </AlertDialogCancel>
            <Button
              variant="error"
              onClick={handleRemoveMember}
              loading={removing}
              disabled={removing}
              data-testid="confirm-remove-member"
            >
              Remove Member
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

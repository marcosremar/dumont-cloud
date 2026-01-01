import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiGet, apiPost, isDemoMode } from '../utils/api';
import {
  Shield,
  ArrowLeft,
  Check,
  AlertCircle,
} from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Input,
  PageHeader,
} from '../components/tailadmin-ui';
import { ErrorState } from '../components/ErrorState';
import { SkeletonList } from '../components/Skeleton';
import { useToast } from '../components/Toast';

// Demo data for permissions
const DEMO_PERMISSIONS = [
  { id: 1, name: 'gpu.provision', display_name: 'GPU Provisioning', description: 'Provision new GPU instances', category: 'GPU' },
  { id: 2, name: 'gpu.delete', display_name: 'GPU Deletion', description: 'Delete GPU instances', category: 'GPU' },
  { id: 3, name: 'gpu.view', display_name: 'GPU View', description: 'View GPU instances and details', category: 'GPU' },
  { id: 4, name: 'cost.view', display_name: 'Cost View', description: 'View all team costs', category: 'Cost' },
  { id: 5, name: 'cost.view_own', display_name: 'View Own Costs', description: 'View own usage costs', category: 'Cost' },
  { id: 6, name: 'cost.export', display_name: 'Cost Export', description: 'Export cost reports', category: 'Cost' },
  { id: 7, name: 'team.invite', display_name: 'Invite Members', description: 'Invite new team members', category: 'Team' },
  { id: 8, name: 'team.remove', display_name: 'Remove Members', description: 'Remove team members', category: 'Team' },
  { id: 9, name: 'team.manage', display_name: 'Manage Team', description: 'Full team management access', category: 'Team' },
  { id: 10, name: 'settings.view', display_name: 'View Settings', description: 'View team settings', category: 'Settings' },
  { id: 11, name: 'settings.manage', display_name: 'Manage Settings', description: 'Modify team settings', category: 'Settings' },
  { id: 12, name: 'audit.view', display_name: 'View Audit Logs', description: 'View team audit logs', category: 'Audit' },
];

const DEMO_TEAM = {
  id: 1,
  name: 'Engineering',
  slug: 'engineering',
};

export default function CreateRolePage() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const isDemo = isDemoMode();

  const [team, setTeam] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Form state
  const [roleName, setRoleName] = useState('');
  const [roleDescription, setRoleDescription] = useState('');
  const [selectedPermissions, setSelectedPermissions] = useState([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchData();
  }, [teamId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (isDemo) {
        await new Promise(r => setTimeout(r, 500));
        setTeam(DEMO_TEAM);
        setPermissions(DEMO_PERMISSIONS);
        setLoading(false);
        return;
      }

      // Fetch team details and permissions in parallel
      const [teamRes, permissionsRes] = await Promise.all([
        apiGet(`/api/v1/teams/${teamId}`),
        apiGet('/api/v1/permissions'),
      ]);

      if (!teamRes.ok) {
        throw new Error('Failed to fetch team details');
      }

      const teamData = await teamRes.json();
      setTeam(teamData);

      if (permissionsRes.ok) {
        const permData = await permissionsRes.json();
        setPermissions(permData.permissions || permData || []);
      }
    } catch (err) {
      setError(err.message);
      if (isDemo) {
        setTeam(DEMO_TEAM);
        setPermissions(DEMO_PERMISSIONS);
      }
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionToggle = (permissionName) => {
    setSelectedPermissions(prev => {
      if (prev.includes(permissionName)) {
        return prev.filter(p => p !== permissionName);
      } else {
        return [...prev, permissionName];
      }
    });
  };

  const handleSelectAll = (category) => {
    const categoryPermissions = permissions
      .filter(p => p.category === category)
      .map(p => p.name);

    const allSelected = categoryPermissions.every(p => selectedPermissions.includes(p));

    if (allSelected) {
      setSelectedPermissions(prev => prev.filter(p => !categoryPermissions.includes(p)));
    } else {
      setSelectedPermissions(prev => [...new Set([...prev, ...categoryPermissions])]);
    }
  };

  const handleCreateRole = async () => {
    if (!roleName.trim()) {
      toast.error('Role name is required');
      return;
    }

    if (selectedPermissions.length === 0) {
      toast.error('Please select at least one permission');
      return;
    }

    setCreating(true);
    try {
      if (isDemo) {
        await new Promise(r => setTimeout(r, 1000));
        toast.success(`Role "${roleName}" created successfully!`);
        navigate(`/app/teams/${teamId}`);
        return;
      }

      const res = await apiPost(`/api/v1/teams/${teamId}/roles`, {
        name: roleName,
        description: roleDescription,
        permissions: selectedPermissions,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Failed to create role');
      }

      toast.success(`Role "${roleName}" created successfully!`);
      navigate(`/app/teams/${teamId}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  // Group permissions by category
  const groupedPermissions = permissions.reduce((acc, perm) => {
    const category = perm.category || 'Other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(perm);
    return acc;
  }, {});

  const getCategoryIcon = (category) => {
    switch (category?.toLowerCase()) {
      case 'gpu':
        return 'primary';
      case 'cost':
        return 'warning';
      case 'team':
        return 'success';
      case 'settings':
        return 'gray';
      case 'audit':
        return 'error';
      default:
        return 'gray';
    }
  };

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
            onRetry={fetchData}
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
        title="Create Custom Role"
        subtitle="Define permissions for a new team role"
        breadcrumbs={[
          { label: 'Teams', href: '/app/teams' },
          { label: team?.name || 'Team', href: `/app/teams/${teamId}` },
          { label: 'Create Role' },
        ]}
      />

      {/* Back Button */}
      <div className="mb-6">
        <Button
          variant="ghost"
          icon={ArrowLeft}
          onClick={() => navigate(`/app/teams/${teamId}`)}
          className="text-gray-400 hover:text-white"
        >
          Back to Team
        </Button>
      </div>

      {/* Role Name Input */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-brand-500" />
            Role Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            label="Role Name"
            placeholder="e.g., DevOps Engineer"
            value={roleName}
            onChange={(e) => setRoleName(e.target.value)}
            disabled={creating}
            data-testid="role-name-input"
          />
          <Input
            label="Description (optional)"
            placeholder="e.g., Infrastructure management and deployment access"
            value={roleDescription}
            onChange={(e) => setRoleDescription(e.target.value)}
            disabled={creating}
            data-testid="role-description-input"
          />
        </CardContent>
      </Card>

      {/* Permissions Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Check className="w-5 h-5 text-success-500" />
            Permissions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-400 text-sm mb-6">
            Select the permissions this role should have. Users with this role will be able to perform the selected actions.
          </p>

          <div className="space-y-6">
            {Object.entries(groupedPermissions).map(([category, categoryPermissions]) => {
              const allSelected = categoryPermissions.every(p =>
                selectedPermissions.includes(p.name)
              );
              const someSelected = categoryPermissions.some(p =>
                selectedPermissions.includes(p.name)
              );

              return (
                <div key={category} className="border border-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full bg-${getCategoryIcon(category)}-500`} />
                      <h3 className="font-medium text-white">{category}</h3>
                      <span className="text-xs text-gray-500">
                        ({categoryPermissions.length} permissions)
                      </span>
                    </div>
                    <button
                      onClick={() => handleSelectAll(category)}
                      className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
                      type="button"
                    >
                      {allSelected ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {categoryPermissions.map((permission) => {
                      const isSelected = selectedPermissions.includes(permission.name);

                      return (
                        <label
                          key={permission.id || permission.name}
                          className={`
                            flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                            ${isSelected
                              ? 'border-brand-500 bg-brand-500/10'
                              : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
                            }
                          `}
                        >
                          <div className="pt-0.5">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handlePermissionToggle(permission.name)}
                              disabled={creating}
                              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-brand-500 focus:ring-brand-500 focus:ring-offset-0"
                              data-testid={`permission-${permission.name}`}
                            />
                          </div>
                          <div className="flex-1">
                            <p className={`font-medium text-sm ${isSelected ? 'text-white' : 'text-gray-300'}`}>
                              {permission.display_name || permission.name}
                            </p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {permission.description}
                            </p>
                            <code className="text-xs text-gray-600 mt-1 block">
                              {permission.name}
                            </code>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {selectedPermissions.length > 0 && (
            <div className="mt-6 p-3 rounded-lg border border-brand-500/20 bg-brand-500/5">
              <div className="flex items-center gap-2 text-brand-400 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>
                  {selectedPermissions.length} permission{selectedPermissions.length !== 1 ? 's' : ''} selected
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex items-center justify-end gap-4">
        <Button
          variant="ghost"
          onClick={() => navigate(`/app/teams/${teamId}`)}
          disabled={creating}
        >
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={handleCreateRole}
          loading={creating}
          disabled={creating || !roleName.trim() || selectedPermissions.length === 0}
          data-testid="create-role-button"
        >
          Create Role
        </Button>
      </div>
    </div>
  );
}

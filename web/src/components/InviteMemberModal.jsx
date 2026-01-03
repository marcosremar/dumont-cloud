import React, { useState } from 'react';
import { UserPlus, Mail } from 'lucide-react';
import { apiPost } from '../utils/api';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  Button,
  Input,
  SelectCompound as Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from './tailadmin-ui';

/**
 * InviteMemberModal - Modal for inviting team members
 *
 * @param {boolean} open - Whether the modal is open
 * @param {function} onOpenChange - Callback when open state changes
 * @param {number} teamId - The team ID to invite member to
 * @param {Array} roles - Available roles for selection
 * @param {function} onSuccess - Callback when invitation is sent successfully
 * @param {function} onError - Callback when invitation fails
 */
export default function InviteMemberModal({
  open,
  onOpenChange,
  teamId,
  roles = [],
  onSuccess,
  onError,
}) {
  const [email, setEmail] = useState('');
  const [roleId, setRoleId] = useState('');
  const [loading, setLoading] = useState(false);

  const handleClose = () => {
    setEmail('');
    setRoleId('');
    onOpenChange(false);
  };

  const handleSubmit = async () => {
    if (!email.trim()) {
      onError?.('Email is required');
      return;
    }
    if (!roleId) {
      onError?.('Please select a role');
      return;
    }

    setLoading(true);
    try {
      if (isDemo) {
        // Simulate API delay in demo mode
        await new Promise((r) => setTimeout(r, 1000));
        const selectedRole = roles.find((r) => r.id === parseInt(roleId));
        const newInvitation = {
          id: Date.now(),
          team_id: parseInt(teamId),
          email: email,
          role_id: parseInt(roleId),
          role_name: selectedRole?.display_name || selectedRole?.name,
          invited_by_user_id: 'demo@dumont.cloud',
          token: 'demo-token',
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          status: 'pending',
          created_at: new Date().toISOString(),
        };
        onSuccess?.(newInvitation, `Invitation sent to ${email}`);
        handleClose();
        return;
      }

      const res = await apiPost(`/api/v1/teams/${teamId}/invitations`, {
        email: email,
        role_id: parseInt(roleId),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Failed to send invitation');
      }

      const data = await res.json().catch(() => null);
      onSuccess?.(data, `Invitation sent to ${email}`);
      handleClose();
    } catch (err) {
      onError?.(err.message);
    } finally {
      setLoading(false);
    }
  };

  const isSubmitDisabled = loading || !email.trim() || !roleId;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-brand-500" />
            Invite Team Member
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4 pt-4">
              <Input
                label="Email Address"
                type="email"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                data-testid="invite-email-input"
              />
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Role
                </label>
                <Select
                  value={roleId}
                  onValueChange={setRoleId}
                >
                  <SelectTrigger data-testid="invite-role-select" disabled={loading}>
                    <SelectValue placeholder="Select a role" />
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
              <div className="p-3 rounded-lg border border-brand-500/20 bg-brand-500/5">
                <div className="flex items-start gap-2 text-brand-400 text-sm">
                  <Mail className="w-4 h-4 mt-0.5" />
                  <span>
                    An invitation link will be sent to the email address. The link expires in 7 days.
                  </span>
                </div>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading} onClick={handleClose}>
            Cancel
          </AlertDialogCancel>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={loading}
            disabled={isSubmitDisabled}
            data-testid="confirm-invite"
          >
            Send Invitation
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

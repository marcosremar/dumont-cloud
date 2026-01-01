import { useState, useEffect } from 'react';
import { Camera, Clock, Save, Info, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  getSnapshotConfig,
  updateSnapshotConfig,
  SNAPSHOT_INTERVALS,
  formatSnapshotTime,
} from '../api/snapshots';

/**
 * SnapshotConfigModal - Modal for configuring per-instance snapshot settings
 *
 * Allows users to:
 * - Enable/disable periodic snapshots
 * - Configure snapshot interval (5min, 15min, 30min, 60min)
 * - View last snapshot timestamp and status
 *
 * @param {Object} props
 * @param {Object} props.instance - Instance object with id and name
 * @param {boolean} props.isOpen - Whether the modal is open
 * @param {Function} props.onClose - Callback when modal closes
 * @param {Function} props.onSave - Callback after successful save with updated config
 */
export default function SnapshotConfigModal({ instance, isOpen, onClose, onSave }) {
  const [config, setConfig] = useState({
    enabled: true,
    interval_minutes: 15,
    last_snapshot_at: null,
    status: 'pending',
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Load configuration when modal opens
  useEffect(() => {
    if (isOpen && instance?.id) {
      loadConfig();
    }
  }, [isOpen, instance?.id]);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSnapshotConfig(instance.id);
      setConfig({
        enabled: data.enabled,
        interval_minutes: data.interval_minutes,
        last_snapshot_at: data.last_snapshot_at,
        status: data.status,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const response = await updateSnapshotConfig(instance.id, {
        enabled: config.enabled,
        interval_minutes: config.interval_minutes,
      });

      if (onSave) {
        onSave(response.config);
      }

      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleIntervalChange = (value) => {
    setConfig({
      ...config,
      interval_minutes: parseInt(value, 10),
    });
  };

  const handleEnabledChange = (checked) => {
    setConfig({
      ...config,
      enabled: checked,
    });
  };

  // Get status display info
  const getStatusInfo = () => {
    switch (config.status) {
      case 'success':
        return { color: 'text-green-400', label: 'Success' };
      case 'failed':
        return { color: 'text-red-400', label: 'Failed' };
      case 'overdue':
        return { color: 'text-yellow-400', label: 'Overdue' };
      case 'pending':
        return { color: 'text-blue-400', label: 'Pending' };
      case 'disabled':
        return { color: 'text-gray-400', label: 'Disabled' };
      default:
        return { color: 'text-gray-400', label: 'Unknown' };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Camera className="w-5 h-5 text-brand-400" />
            Snapshot Configuration
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            {instance?.name || instance?.id}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Error display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-start gap-2">
              <Info className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Loading state */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
              <span className="ml-2 text-gray-400">Loading configuration...</span>
            </div>
          ) : (
            <>
              {/* Enable/Disable Toggle */}
              <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
                <div className="space-y-0.5 flex-1">
                  <Label className="text-base font-medium text-white flex items-center gap-2">
                    <Camera className="w-4 h-4 text-brand-400" />
                    Periodic Snapshots
                  </Label>
                  <p className="text-sm text-gray-400">
                    Automatically create snapshots at regular intervals
                  </p>
                </div>
                <Switch
                  checked={config.enabled}
                  onCheckedChange={handleEnabledChange}
                />
              </div>

              {/* Interval Selection */}
              {config.enabled && (
                <div className="space-y-3">
                  <Label className="text-base font-medium flex items-center gap-2">
                    <Clock className="w-4 h-4 text-brand-400" />
                    Snapshot Interval
                  </Label>
                  <Select
                    value={String(config.interval_minutes)}
                    onValueChange={handleIntervalChange}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select interval" />
                    </SelectTrigger>
                    <SelectContent>
                      {SNAPSHOT_INTERVALS.map((interval) => (
                        <SelectItem
                          key={interval.value}
                          value={String(interval.value)}
                        >
                          {interval.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-400 flex items-start gap-2">
                    <Info className="w-3 h-3 mt-0.5 text-brand-400 flex-shrink-0" />
                    Snapshots protect your data from spot instance interruptions
                  </p>
                </div>
              )}

              {/* Last Snapshot Status */}
              <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700/50 space-y-3">
                <h4 className="text-sm font-medium text-gray-300">Last Snapshot</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-gray-500 block">Status</span>
                    <span className={`text-sm font-medium ${statusInfo.color}`}>
                      {statusInfo.label}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">Time</span>
                    <span className="text-sm text-gray-300">
                      {formatSnapshotTime(config.last_snapshot_at)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Info about savings */}
              {config.enabled && (
                <div className="bg-brand-500/10 border border-brand-500/30 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-brand-400 mt-0.5 flex-shrink-0" />
                    <div className="text-xs text-gray-300">
                      <p className="mb-1">
                        <strong className="text-brand-400">Automatic Protection</strong>
                      </p>
                      <p>
                        Snapshots are automatically stored in cloud storage and can be used
                        to restore your instance data after interruptions.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={saving}
            className="text-gray-400 hover:text-white"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={loading || saving}
            className="bg-brand-500 hover:bg-brand-600 text-white gap-2"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Configuration
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

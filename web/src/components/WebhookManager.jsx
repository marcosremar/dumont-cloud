import { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Webhook,
  Plus,
  Trash2,
  Edit2,
  Play,
  X,
  Check,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  RefreshCw,
  Eye,
  EyeOff,
  Copy
} from 'lucide-react'
import { useToast } from './Toast'
import { Card, Alert, Button } from './tailadmin-ui'
import {
  fetchWebhooks,
  fetchEventTypes,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  testWebhook,
  fetchWebhookLogs,
  selectWebhooks,
  selectEventTypes,
  selectWebhooksLoading,
  selectTestingWebhookId,
  selectWebhookLogs,
  selectLogsLoading,
} from '../store/slices/webhooksSlice'

// Available webhook events
const WEBHOOK_EVENTS = [
  { id: 'instance.started', label: 'Instance Started', description: 'When a GPU instance starts' },
  { id: 'instance.stopped', label: 'Instance Stopped', description: 'When a GPU instance stops' },
  { id: 'snapshot.completed', label: 'Snapshot Completed', description: 'When a snapshot finishes' },
  { id: 'failover.triggered', label: 'Failover Triggered', description: 'When failover occurs' },
  { id: 'cost.threshold', label: 'Cost Threshold', description: 'When cost exceeds threshold' },
]

function WebhookForm({ webhook, onSave, onCancel, loading }) {
  const [name, setName] = useState(webhook?.name || '')
  const [url, setUrl] = useState(webhook?.url || '')
  const [secret, setSecret] = useState(webhook?.secret || '')
  const [events, setEvents] = useState(webhook?.events || [])
  const [enabled, setEnabled] = useState(webhook?.enabled !== false)
  const [showSecret, setShowSecret] = useState(false)

  const handleToggleEvent = (eventId) => {
    if (events.includes(eventId)) {
      setEvents(events.filter(e => e !== eventId))
    } else {
      setEvents([...events, eventId])
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name.trim() || !url.trim() || events.length === 0) {
      return
    }
    onSave({
      name: name.trim(),
      url: url.trim(),
      secret: secret.trim() || null,
      events,
      enabled,
    })
  }

  const isValid = name.trim() && url.trim() && events.length > 0

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="form-group">
        <label className="form-label text-gray-300 block mb-2">Name</label>
        <input
          type="text"
          className="form-input w-full"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Webhook"
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label text-gray-300 block mb-2">URL</label>
        <input
          type="url"
          className="form-input w-full"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/webhook"
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label text-gray-300 block mb-2">
          Secret (Optional)
          <span className="text-gray-500 text-xs ml-2">For HMAC-SHA256 signature</span>
        </label>
        <div className="relative">
          <input
            type={showSecret ? 'text' : 'password'}
            className="form-input w-full pr-10"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder="Optional secret for signature verification"
          />
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-300"
            onClick={() => setShowSecret(!showSecret)}
          >
            {showSecret ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label text-gray-300 block mb-2">Events</label>
        <div className="space-y-2">
          {WEBHOOK_EVENTS.map(event => (
            <label
              key={event.id}
              className="flex items-center gap-3 p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors"
            >
              <input
                type="checkbox"
                checked={events.includes(event.id)}
                onChange={() => handleToggleEvent(event.id)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-brand-500 focus:ring-brand-500"
              />
              <div className="flex-1">
                <div className="text-white text-sm font-medium">{event.label}</div>
                <div className="text-gray-500 text-xs">{event.description}</div>
              </div>
            </label>
          ))}
        </div>
        {events.length === 0 && (
          <p className="text-red-400 text-xs mt-2">Select at least one event</p>
        )}
      </div>

      <div className="form-group">
        <label className="flex items-center gap-3 cursor-pointer">
          <div className="relative">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500"></div>
          </div>
          <span className="text-gray-300 text-sm">Enabled</span>
        </label>
      </div>

      <div className="flex gap-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 py-2.5 px-4 rounded-lg font-medium transition-all bg-gray-700 hover:bg-gray-600 text-gray-300"
          disabled={loading}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading || !isValid}
          className="flex-1 py-2.5 px-4 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Check size={16} />
              {webhook ? 'Update' : 'Create'}
            </>
          )}
        </button>
      </div>
    </form>
  )
}

function WebhookLogs({ webhookId }) {
  const dispatch = useDispatch()
  const logs = useSelector(selectWebhookLogs(webhookId))
  const logsLoading = useSelector(selectLogsLoading)

  useEffect(() => {
    if (webhookId) {
      dispatch(fetchWebhookLogs(webhookId))
    }
  }, [dispatch, webhookId])

  if (logsLoading) {
    return (
      <div className="flex items-center justify-center py-4 text-gray-400">
        <RefreshCw size={16} className="animate-spin mr-2" />
        Loading logs...
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <div className="text-center py-4 text-gray-500 text-sm">
        No delivery logs yet
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {logs.map((log, index) => (
        <div
          key={log.id || index}
          className="flex items-start gap-3 p-3 bg-white/5 rounded-lg text-sm"
        >
          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
            log.status_code >= 200 && log.status_code < 300
              ? 'bg-green-500'
              : log.status_code >= 400
                ? 'bg-red-500'
                : 'bg-yellow-500'
          }`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-white font-medium">{log.event_type}</span>
              <span className={`px-2 py-0.5 rounded text-xs ${
                log.status_code >= 200 && log.status_code < 300
                  ? 'bg-green-500/20 text-green-400'
                  : log.status_code >= 400
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {log.status_code || 'Failed'}
              </span>
              {log.attempt > 1 && (
                <span className="text-gray-500 text-xs">Attempt {log.attempt}</span>
              )}
            </div>
            <div className="text-gray-500 text-xs mt-1 flex items-center gap-2">
              <Clock size={12} />
              {new Date(log.created_at).toLocaleString()}
            </div>
            {log.error && (
              <div className="text-red-400 text-xs mt-1 truncate">{log.error}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function WebhookRow({ webhook, onEdit, onDelete, onTest }) {
  const [expanded, setExpanded] = useState(false)
  const testingWebhookId = useSelector(selectTestingWebhookId)
  const isTesting = testingWebhookId === webhook.id

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <div className="flex items-center gap-4 p-4 bg-white/5">
        <div className={`w-3 h-3 rounded-full flex-shrink-0 ${webhook.enabled ? 'bg-green-500' : 'bg-gray-500'}`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-white font-medium">{webhook.name}</span>
            {!webhook.enabled && (
              <span className="px-2 py-0.5 rounded text-xs bg-gray-600 text-gray-400">Disabled</span>
            )}
          </div>
          <div className="text-gray-500 text-sm truncate">{webhook.url}</div>
          <div className="flex gap-1.5 mt-1.5 flex-wrap">
            {webhook.events?.map(event => (
              <span
                key={event}
                className="px-2 py-0.5 rounded text-xs bg-brand-500/20 text-brand-400"
              >
                {event}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => onTest(webhook.id)}
            disabled={isTesting || !webhook.enabled}
            className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Test webhook"
          >
            {isTesting ? <RefreshCw size={18} className="animate-spin" /> : <Play size={18} />}
          </button>
          <button
            onClick={() => onEdit(webhook)}
            className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Edit webhook"
          >
            <Edit2 size={18} />
          </button>
          <button
            onClick={() => onDelete(webhook)}
            className="p-2 rounded-lg hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
            title="Delete webhook"
          >
            <Trash2 size={18} />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="View logs"
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-white/10 p-4 bg-black/20">
          <div className="text-gray-400 text-sm font-medium mb-2">Delivery Logs</div>
          <WebhookLogs webhookId={webhook.id} />
        </div>
      )}
    </div>
  )
}

export default function WebhookManager() {
  const dispatch = useDispatch()
  const toast = useToast()
  const webhooks = useSelector(selectWebhooks)
  const loading = useSelector(selectWebhooksLoading)
  const [showForm, setShowForm] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState(null)
  const [deletingWebhook, setDeletingWebhook] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    dispatch(fetchWebhooks())
    dispatch(fetchEventTypes())
  }, [dispatch])

  const handleCreate = () => {
    setEditingWebhook(null)
    setShowForm(true)
  }

  const handleEdit = (webhook) => {
    setEditingWebhook(webhook)
    setShowForm(true)
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingWebhook(null)
  }

  const handleSave = async (data) => {
    setSaving(true)
    try {
      if (editingWebhook) {
        await dispatch(updateWebhook({ webhookId: editingWebhook.id, updates: data })).unwrap()
        toast.success('Webhook updated successfully')
      } else {
        await dispatch(createWebhook(data)).unwrap()
        toast.success('Webhook created successfully')
      }
      setShowForm(false)
      setEditingWebhook(null)
    } catch (error) {
      toast.error(error || 'Failed to save webhook')
    }
    setSaving(false)
  }

  const handleDelete = async (webhook) => {
    setDeletingWebhook(webhook)
  }

  const confirmDelete = async () => {
    if (!deletingWebhook) return
    try {
      await dispatch(deleteWebhook(deletingWebhook.id)).unwrap()
      toast.success('Webhook deleted')
      setDeletingWebhook(null)
    } catch (error) {
      toast.error(error || 'Failed to delete webhook')
    }
  }

  const handleTest = async (webhookId) => {
    try {
      const result = await dispatch(testWebhook(webhookId)).unwrap()
      if (result.success) {
        toast.success('Test webhook sent successfully')
      } else {
        toast.error(result.error || 'Test webhook failed')
      }
      // Refresh logs after test
      dispatch(fetchWebhookLogs(webhookId))
    } catch (error) {
      toast.error(error || 'Failed to send test webhook')
    }
  }

  if (loading && webhooks.length === 0) {
    return (
      <Card className="border-white/10 bg-dark-surface-card">
        <div className="flex items-center justify-center py-12">
          <RefreshCw size={24} className="animate-spin text-gray-400" />
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card
        className="border-white/10 bg-dark-surface-card"
        header={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-brand-500/10">
                <Webhook className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Webhooks</h3>
                <p className="text-gray-500 text-sm mt-1">
                  HTTP callbacks for infrastructure events
                </p>
              </div>
            </div>
            {!showForm && (
              <Button
                onClick={handleCreate}
                className="bg-brand-500 hover:bg-brand-600 text-white"
              >
                <Plus size={16} className="mr-2" />
                Add Webhook
              </Button>
            )}
          </div>
        }
      >
        {showForm ? (
          <div className="p-4">
            <div className="text-white font-medium mb-4">
              {editingWebhook ? 'Edit Webhook' : 'New Webhook'}
            </div>
            <WebhookForm
              webhook={editingWebhook}
              onSave={handleSave}
              onCancel={handleCancel}
              loading={saving}
            />
          </div>
        ) : webhooks.length === 0 ? (
          <div className="text-center py-12">
            <Webhook className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <div className="text-gray-400 mb-2">No webhooks configured</div>
            <p className="text-gray-600 text-sm mb-4">
              Create webhooks to receive notifications when events occur
            </p>
            <Button
              onClick={handleCreate}
              className="bg-brand-500/20 hover:bg-brand-500/30 text-brand-300 border border-brand-500/30"
            >
              <Plus size={16} className="mr-2" />
              Create your first webhook
            </Button>
          </div>
        ) : (
          <div className="space-y-3 p-4">
            {webhooks.map(webhook => (
              <WebhookRow
                key={webhook.id}
                webhook={webhook}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onTest={handleTest}
              />
            ))}
          </div>
        )}
      </Card>

      {/* Info Card */}
      <Card className="border-white/10 bg-dark-surface-card">
        <div className="p-4">
          <div className="text-white font-medium mb-3">Webhook Payload Format</div>
          <div className="bg-black/30 rounded-lg p-4 font-mono text-sm text-gray-400 overflow-x-auto">
            <pre>{`{
  "event": "instance.started",
  "data": {
    "instance_id": "...",
    "timestamp": "2025-01-01T00:00:00Z",
    ...
  },
  "timestamp": "2025-01-01T00:00:00Z"
}`}</pre>
          </div>
          <div className="mt-3 text-gray-500 text-sm">
            <p className="mb-2">
              <strong className="text-gray-400">Security:</strong> If a secret is configured,
              requests include an <code className="bg-white/10 px-1 rounded">X-Webhook-Signature</code> header
              with HMAC-SHA256 signature.
            </p>
            <p>
              <strong className="text-gray-400">Retries:</strong> Failed deliveries retry up to 3 times
              with exponential backoff (2s, 4s, 8s).
            </p>
          </div>
        </div>
      </Card>

      {/* Delete Confirmation Modal */}
      {deletingWebhook && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-dark-surface-card border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-red-500/20">
                <AlertCircle className="w-5 h-5 text-red-400" />
              </div>
              <div className="text-white font-semibold">Delete Webhook</div>
            </div>
            <p className="text-gray-400 mb-6">
              Are you sure you want to delete <strong className="text-white">{deletingWebhook.name}</strong>?
              This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeletingWebhook(null)}
                className="flex-1 py-2.5 px-4 rounded-lg font-medium transition-all bg-gray-700 hover:bg-gray-600 text-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 py-2.5 px-4 rounded-lg font-semibold transition-all bg-red-500 hover:bg-red-600 text-white"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Brain,
  Plus,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Search,
  ChevronDown,
  Copy,
  MoreHorizontal,
  FileText,
  Trash2,
  Play,
  Square,
  Rocket,
  Download,
  Eye,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import MethodSelectionModal from '../components/MethodSelectionModal';
import FineTuningModal from '../components/FineTuningModal';

// Status badge configurations (matching Fireworks.ai)
const STATUS_CONFIG = {
  pending: { color: 'bg-yellow-500/20 text-yellow-400', label: 'Pending' },
  uploading: { color: 'bg-cyan-500/20 text-cyan-400', label: 'Uploading' },
  queued: { color: 'bg-orange-500/20 text-orange-400', label: 'Queued' },
  running: { color: 'bg-purple-500/20 text-purple-400', label: 'Running' },
  completed: { color: 'bg-green-500/20 text-green-400', label: 'Completed' },
  failed: { color: 'bg-red-500/20 text-red-400', label: 'Failed' },
  cancelled: { color: 'bg-gray-500/20 text-gray-400', label: 'Cancelled' },
};

// Format date/time like Fireworks.ai
function formatDateTime(dateStr) {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Copy to clipboard helper
function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}

// Status Badge Component
function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const isRunning = ['running', 'uploading'].includes(status);

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {isRunning && <Loader2 className="w-3 h-3 animate-spin" />}
      {config.label}
    </span>
  );
}

// Copy Button Component
function CopyButton({ text, className = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    copyToClipboard(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={`p-1 rounded hover:bg-white/10 transition-colors ${className}`}
      title="Copy to clipboard"
    >
      {copied ? (
        <CheckCircle className="w-3.5 h-3.5 text-green-400" />
      ) : (
        <Copy className="w-3.5 h-3.5 text-gray-400" />
      )}
    </button>
  );
}

// Job Row Actions Menu
function JobActionsMenu({ job, onViewLogs, onCancel, onDeploy, onDownload, onDelete }) {
  const [isOpen, setIsOpen] = useState(false);
  const isRunning = ['pending', 'uploading', 'queued', 'running'].includes(job.status);
  const isCompleted = job.status === 'completed';
  const canDelete = !isRunning;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-1.5 rounded hover:bg-white/10 transition-colors"
      >
        <MoreHorizontal className="w-4 h-4 text-gray-400" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-8 w-48 bg-[#1e2330] border border-white/10 rounded-lg shadow-xl z-20 py-1">
            <button
              onClick={() => { onViewLogs(job); setIsOpen(false); }}
              className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-white/5 flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              View Logs
            </button>
            {isCompleted && (
              <>
                <button
                  onClick={() => { onDeploy(job); setIsOpen(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-green-400 hover:bg-white/5 flex items-center gap-2"
                >
                  <Rocket className="w-4 h-4" />
                  Deploy
                </button>
                <button
                  onClick={() => { onDownload(job); setIsOpen(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-cyan-400 hover:bg-white/5 flex items-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              </>
            )}
            {isRunning && (
              <button
                onClick={() => { onCancel(job.id); setIsOpen(false); }}
                className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-white/5 flex items-center gap-2"
              >
                <Square className="w-4 h-4" />
                Cancel
              </button>
            )}
            {canDelete && (
              <button
                onClick={() => { onDelete(job.id); setIsOpen(false); }}
                className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-white/5 flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Logs Modal Component
function LogsModal({ job, isOpen, onClose }) {
  const [logs, setLogs] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen && job) {
      fetchLogs();
    }
  }, [isOpen, job]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${job.id}/logs?tail=200`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setLogs(data.logs || 'No logs available');
    } catch (err) {
      setLogs('Failed to fetch logs: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#1a1f2e] rounded-xl border border-white/10 w-full max-w-4xl max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <h3 className="text-lg font-semibold text-white">Logs: {job.name}</h3>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={fetchLogs}>
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
            </div>
          ) : (
            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
              {logs}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

// Deploy Modal Component
function DeployModal({ job, isOpen, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedGpu, setSelectedGpu] = useState('RTX4090');
  const [instanceName, setInstanceName] = useState('');

  useEffect(() => {
    if (job) {
      setInstanceName(`inference-${job.name?.slice(0, 20) || 'model'}`);
    }
  }, [job]);

  const GPU_OPTIONS = [
    { id: 'RTX4090', name: 'RTX 4090', vram: '24GB', price: '~$0.35/hr' },
    { id: 'A100', name: 'A100 40GB', vram: '40GB', price: '~$1.50/hr' },
    { id: 'A100-80GB', name: 'A100 80GB', vram: '80GB', price: '~$2.00/hr' },
    { id: 'H100', name: 'H100 80GB', vram: '80GB', price: '~$3.50/hr' },
  ];

  const handleDeploy = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${job.id}/deploy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          gpu_type: selectedGpu,
          instance_name: instanceName,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to deploy model');
      }
      onSuccess(data);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#1a1f2e] rounded-xl border border-white/10 w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Rocket className="w-5 h-5 text-green-400" />
            Deploy Model
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="bg-[#0f1219] rounded-lg p-4 border border-white/5">
            <div className="flex items-center gap-3 mb-2">
              <Brain className="w-5 h-5 text-purple-400" />
              <span className="text-white font-medium">{job?.name}</span>
            </div>
            <div className="text-sm text-gray-400">
              Base: {job?.base_model?.split('/').pop() || 'Unknown'}
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Instance Name</label>
            <input
              type="text"
              value={instanceName}
              onChange={(e) => setInstanceName(e.target.value)}
              className="w-full bg-[#0f1219] border border-white/10 rounded-lg px-4 py-2.5 text-white focus:border-purple-500 outline-none"
              placeholder="my-inference-instance"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Select GPU</label>
            <div className="grid grid-cols-2 gap-3">
              {GPU_OPTIONS.map((gpu) => (
                <button
                  key={gpu.id}
                  onClick={() => setSelectedGpu(gpu.id)}
                  className={`p-3 rounded-lg border transition-all text-left ${
                    selectedGpu === gpu.id
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="font-medium text-white">{gpu.name}</div>
                  <div className="text-xs text-gray-400">{gpu.vram} • {gpu.price}</div>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <Button variant="ghost" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button
              onClick={handleDeploy}
              disabled={loading || !instanceName}
              className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Rocket className="w-4 h-4 mr-2" />
              )}
              Deploy
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main Page Component
export default function FineTuning() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showMethodModal, setShowMethodModal] = useState(false);
  const [showFineTuneModal, setShowFineTuneModal] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState('supervised');
  const [selectedJob, setSelectedJob] = useState(null);
  const [showLogs, setShowLogs] = useState(false);
  const [showDeploy, setShowDeploy] = useState(false);

  // Filters (like Fireworks.ai)
  const [activeTab, setActiveTab] = useState('supervised');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  // Fetch jobs
  const fetchJobs = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch('/api/v1/finetune/jobs', {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  // Cancel job
  const handleCancel = async (jobId) => {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    try {
      const token = localStorage.getItem('auth_token');
      await fetch(`/api/v1/finetune/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      fetchJobs();
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
  };

  // Delete job
  const handleDelete = async (jobId) => {
    if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) return;
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${jobId}`, {
        method: 'DELETE',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      if (res.ok) {
        fetchJobs();
      } else {
        const data = await res.json();
        alert(data.detail || 'Failed to delete job');
      }
    } catch (err) {
      console.error('Failed to delete job:', err);
      alert('Failed to delete job: ' + err.message);
    }
  };

  // View logs
  const handleViewLogs = (job) => {
    setSelectedJob(job);
    setShowLogs(true);
  };

  // Deploy model
  const handleDeploy = (job) => {
    setSelectedJob(job);
    setShowDeploy(true);
  };

  // Download model
  const handleDownload = async (job) => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${job.id}/download`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (data.download_url) {
        window.open(data.download_url, '_blank');
      } else if (data.message) {
        alert(data.message);
      }
    } catch (err) {
      alert('Failed to download: ' + err.message);
    }
  };

  // Handle method selection and open wizard
  const handleMethodSelect = (method) => {
    setSelectedMethod(method);
    setShowMethodModal(false);
    setShowFineTuneModal(true);
  };

  // Filter jobs based on search and status
  const filteredJobs = jobs.filter(job => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        job.name?.toLowerCase().includes(query) ||
        job.id?.toLowerCase().includes(query) ||
        job.base_model?.toLowerCase().includes(query) ||
        job.dataset_path?.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }

    // Status filter
    if (statusFilter !== 'all') {
      if (statusFilter === 'running') {
        if (!['pending', 'uploading', 'queued', 'running'].includes(job.status)) return false;
      } else if (job.status !== statusFilter) {
        return false;
      }
    }

    return true;
  });

  return (
    <div className="min-h-screen bg-[#0a0d0a] p-6">
      {/* Header - Like Fireworks.ai */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Brain className="w-9 h-9 flex-shrink-0" style={{ color: '#4caf50' }} />
            <div className="flex flex-col justify-center">
              <h1 className="text-2xl font-bold text-white leading-tight">Fine-Tuning Jobs</h1>
              <p className="text-gray-400 mt-0.5">View your past fine-tuning jobs and create new ones.</p>
            </div>
          </div>
          <Button
            onClick={() => setShowMethodModal(true)}
            className="bg-purple-600 hover:bg-purple-700 text-white gap-2"
          >
            <Plus className="w-4 h-4" />
            Fine-tune a Model
          </Button>
        </div>
      </div>

      {/* Search and Filters - Like Fireworks.ai */}
      <div className="mb-6 space-y-4">
        {/* Search input */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by id, name, dataset, or created by"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#111411] border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-white placeholder-gray-500 focus:border-purple-500 outline-none"
          />
        </div>

        {/* Tabs and Status Filter */}
        <div className="flex items-center justify-between">
          {/* Tabs - Like Fireworks.ai */}
          <div className="flex border-b border-white/10">
            {[
              { id: 'supervised', label: 'Supervised' },
              { id: 'reinforcement', label: 'Reinforcement' },
              { id: 'preference', label: 'Preference' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
                  activeTab === tab.id
                    ? 'text-white'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-500" />
                )}
              </button>
            ))}
          </div>

          {/* Status Filter Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowStatusDropdown(!showStatusDropdown)}
              className="flex items-center gap-2 px-4 py-2 bg-[#111411] border border-white/10 rounded-lg text-sm text-gray-300 hover:border-white/20"
            >
              {statusFilter === 'all' ? 'All' : STATUS_CONFIG[statusFilter]?.label || statusFilter}
              <ChevronDown className="w-4 h-4" />
            </button>

            {showStatusDropdown && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowStatusDropdown(false)}
                />
                <div className="absolute right-0 top-10 w-40 bg-[#1e2330] border border-white/10 rounded-lg shadow-xl z-20 py-1">
                  {['all', 'running', 'completed', 'failed'].map(status => (
                    <button
                      key={status}
                      onClick={() => { setStatusFilter(status); setShowStatusDropdown(false); }}
                      className={`w-full px-4 py-2 text-left text-sm hover:bg-white/5 ${
                        statusFilter === status ? 'text-purple-400' : 'text-gray-300'
                      }`}
                    >
                      {status === 'all' ? 'All' : STATUS_CONFIG[status]?.label || status}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Jobs Table - Like Fireworks.ai */}
      <div className="bg-[#111411] rounded-xl border border-white/10 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-16">
            <Brain className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No Fine-Tuning Jobs</h3>
            <p className="text-gray-400 mb-4">
              {searchQuery || statusFilter !== 'all'
                ? 'No jobs match your filters.'
                : "You haven't created any fine-tuning jobs yet."}
            </p>
            {!searchQuery && statusFilter === 'all' && (
              <Button
                onClick={() => setShowMethodModal(true)}
                className="bg-purple-600 hover:bg-purple-700 text-white"
              >
                <Plus className="w-4 h-4 mr-2" />
                Fine-tune a Model
              </Button>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Fine-tuning jobs</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Base model</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Dataset</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Created by</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Create time</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Status</th>
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {filteredJobs.map(job => (
                <tr
                  key={job.id}
                  className="border-b border-white/5 hover:bg-white/[0.02] cursor-pointer"
                  onClick={() => navigate(`/app/finetune/${job.id}`)}
                >
                  {/* Job Name & ID */}
                  <td className="px-4 py-4">
                    <div>
                      <div className="text-white font-medium">{job.name || job.id}</div>
                      <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                        <span className="font-mono">{job.id?.slice(0, 20)}...</span>
                        <CopyButton text={job.id} />
                      </div>
                    </div>
                  </td>

                  {/* Base Model */}
                  <td className="px-4 py-4">
                    <div>
                      <div className="text-gray-300 text-sm">{job.base_model?.split('/').pop() || 'Unknown'}</div>
                      <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                        <span className="font-mono truncate max-w-[150px]">{job.base_model}</span>
                        <CopyButton text={job.base_model} />
                      </div>
                    </div>
                  </td>

                  {/* Dataset */}
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1">
                      <span className="text-gray-300 text-sm truncate max-w-[150px]">
                        {job.dataset_path?.split('/').pop() || 'N/A'}
                      </span>
                      {job.dataset_path && <CopyButton text={job.dataset_path} />}
                    </div>
                  </td>

                  {/* Created By */}
                  <td className="px-4 py-4">
                    <span className="text-gray-400 text-sm">{job.created_by || 'system'}</span>
                  </td>

                  {/* Create Time */}
                  <td className="px-4 py-4">
                    <span className="text-gray-400 text-sm">{formatDateTime(job.created_at)}</span>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-4">
                    <StatusBadge status={job.status} />
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                    <JobActionsMenu
                      job={job}
                      onViewLogs={handleViewLogs}
                      onCancel={handleCancel}
                      onDeploy={handleDeploy}
                      onDownload={handleDownload}
                      onDelete={handleDelete}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Method Selection Modal */}
      <MethodSelectionModal
        isOpen={showMethodModal}
        onClose={() => setShowMethodModal(false)}
        onSelect={handleMethodSelect}
      />

      {/* Fine-Tuning Wizard Modal */}
      <FineTuningModal
        isOpen={showFineTuneModal}
        onClose={() => setShowFineTuneModal(false)}
        method={selectedMethod}
        onSuccess={(job) => {
          fetchJobs();
          setShowFineTuneModal(false);
        }}
      />

      {/* Logs Modal */}
      <LogsModal
        job={selectedJob}
        isOpen={showLogs}
        onClose={() => setShowLogs(false)}
      />

      {/* Deploy Modal */}
      <DeployModal
        job={selectedJob}
        isOpen={showDeploy}
        onClose={() => setShowDeploy(false)}
        onSuccess={(data) => {
          alert(`Deployment started! Instance: ${data.instance_name || 'Creating...'}`);
          fetchJobs();
        }}
      />
    </div>
  );
}

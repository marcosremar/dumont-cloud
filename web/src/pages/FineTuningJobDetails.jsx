import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Brain,
  ChevronLeft,
  Copy,
  CheckCircle,
  Loader2,
  Rocket,
  MoreHorizontal,
  FileText,
  Download,
  Trash2,
  Square,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';

// Status configurations
const STATUS_CONFIG = {
  pending: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Pending' },
  uploading: { color: 'text-cyan-400', bg: 'bg-cyan-500/20', label: 'Uploading' },
  queued: { color: 'text-orange-400', bg: 'bg-orange-500/20', label: 'Queued' },
  running: { color: 'text-purple-400', bg: 'bg-purple-500/20', label: 'Running', spin: true },
  completed: { color: 'text-green-400', bg: 'bg-green-500/20', label: 'Completed' },
  failed: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'Failed' },
  cancelled: { color: 'text-gray-400', bg: 'bg-gray-500/20', label: 'Cancelled' },
};

// Copy to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}

// Copy Button Component
function CopyButton({ text, className = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
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

// Format date
function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function FineTuningJobDetails() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const [logs, setLogs] = useState('');
  const [showLogs, setShowLogs] = useState(false);

  // Fetch job details
  const fetchJob = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${jobId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });

      if (!res.ok) {
        throw new Error('Job not found');
      }

      const data = await res.json();
      setJob(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch logs
  const fetchLogs = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${jobId}/logs?tail=500`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setLogs(data.logs || 'No logs available');
    } catch (err) {
      setLogs('Failed to fetch logs: ' + err.message);
    }
  };

  useEffect(() => {
    fetchJob();
    const interval = setInterval(fetchJob, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [jobId]);

  // Cancel job
  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    try {
      const token = localStorage.getItem('auth_token');
      await fetch(`/api/v1/finetune/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      fetchJob();
    } catch (err) {
      alert('Failed to cancel job: ' + err.message);
    }
    setShowActionsMenu(false);
  };

  // Delete job
  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) return;
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${jobId}`, {
        method: 'DELETE',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      if (res.ok) {
        navigate('/fine-tuning');
      } else {
        const data = await res.json();
        alert(data.detail || 'Failed to delete job');
      }
    } catch (err) {
      alert('Failed to delete job: ' + err.message);
    }
    setShowActionsMenu(false);
  };

  // Download model
  const handleDownload = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/v1/finetune/jobs/${jobId}/download`, {
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
    setShowActionsMenu(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0d0a] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0d0a] flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Job Not Found</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          <Button onClick={() => navigate('/app/finetune')} className="bg-purple-600 hover:bg-purple-700">
            Back to Jobs
          </Button>
        </div>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const isRunning = ['pending', 'uploading', 'queued', 'running'].includes(job.status);
  const isCompleted = job.status === 'completed';
  const canDelete = !isRunning;
  const progressPercent = job.progress_percent || 0;
  const currentEpoch = (job.current_epoch || 0) + 1;
  const totalEpochs = job.config?.epochs || 1;

  return (
    <div className="min-h-screen bg-[#0a0d0a] p-6">
      {/* Breadcrumb */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/app/finetune')}
          className="flex items-center gap-1 text-gray-400 hover:text-white transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Fine-Tuning Jobs
        </button>
      </div>

      {/* Header - Like Fireworks.ai */}
      <div className="bg-[#111411] rounded-xl border border-white/10 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            {/* Job Name */}
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Brain className="w-6 h-6 text-purple-400" />
              {job.name || job.id}
            </h1>

            {/* Job ID with copy */}
            <div className="flex items-center gap-2 mt-2">
              <span className="text-sm text-gray-500 font-mono">{job.id}</span>
              <CopyButton text={job.id} />
            </div>

            {/* Progress Bar (for running jobs) */}
            {isRunning && (
              <div className="mt-4 w-96">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-gray-400">Progress</span>
                  <span className="text-purple-400">
                    {progressPercent.toFixed(1)}% • Epoch {currentEpoch}/{totalEpochs}
                  </span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            {/* Actions Menu */}
            <div className="relative">
              <button
                onClick={() => setShowActionsMenu(!showActionsMenu)}
                className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-gray-300 hover:bg-white/10 transition-colors flex items-center gap-2"
              >
                Actions
                <MoreHorizontal className="w-4 h-4" />
              </button>

              {showActionsMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowActionsMenu(false)} />
                  <div className="absolute right-0 top-12 w-48 bg-[#1e2330] border border-white/10 rounded-lg shadow-xl z-20 py-1">
                    <button
                      onClick={() => { setShowLogs(true); fetchLogs(); setShowActionsMenu(false); }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-white/5 flex items-center gap-2"
                    >
                      <FileText className="w-4 h-4" />
                      View Logs
                    </button>
                    <button
                      onClick={fetchJob}
                      className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-white/5 flex items-center gap-2"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Refresh
                    </button>
                    {isCompleted && (
                      <button
                        onClick={handleDownload}
                        className="w-full px-4 py-2 text-left text-sm text-cyan-400 hover:bg-white/5 flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Download
                      </button>
                    )}
                    {isRunning && (
                      <button
                        onClick={handleCancel}
                        className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-white/5 flex items-center gap-2"
                      >
                        <Square className="w-4 h-4" />
                        Cancel
                      </button>
                    )}
                    {canDelete && (
                      <button
                        onClick={handleDelete}
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

            {/* Deploy Button */}
            {isCompleted && (
              <Button className="bg-purple-600 hover:bg-purple-700 text-white gap-2">
                <Rocket className="w-4 h-4" />
                Deploy
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left: Training Metrics Chart */}
        <div className="col-span-2 bg-[#111411] rounded-xl border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Training Metrics</h2>

          {job.loss || job.training_metrics?.length > 0 ? (
            <div className="space-y-4">
              {/* Current Loss */}
              {job.loss && (
                <div className="p-4 bg-white/5 rounded-lg">
                  <div className="text-sm text-gray-400">Current Loss</div>
                  <div className="text-2xl font-bold text-white">{job.loss.toFixed(4)}</div>
                </div>
              )}

              {/* Placeholder for chart */}
              <div className="h-64 flex items-center justify-center border border-dashed border-white/10 rounded-lg">
                <p className="text-gray-500">Training metrics chart will appear here</p>
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-3">
                  <FileText className="w-6 h-6 text-gray-500" />
                </div>
                <p className="text-gray-400">No data</p>
                <p className="text-sm text-gray-500 mt-1">Training metrics will appear once training starts</p>
              </div>
            </div>
          )}
        </div>

        {/* Right: Job Details */}
        <div className="space-y-6">
          {/* Job Details Section */}
          <div className="bg-[#111411] rounded-xl border border-white/10 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Job Details</h2>

            <div className="space-y-4">
              {/* Output Model */}
              <div className="flex justify-between items-start">
                <span className="text-sm text-gray-400">Output Model</span>
                <div className="flex items-center gap-1">
                  <span className="text-sm text-purple-400 font-mono">{job.name}</span>
                  <CopyButton text={job.name} />
                </div>
              </div>

              {/* Base Model */}
              <div className="flex justify-between items-start">
                <span className="text-sm text-gray-400">Base Model</span>
                <div className="flex items-center gap-1 max-w-[200px]">
                  <span className="text-sm text-white truncate">{job.base_model?.split('/').pop()}</span>
                  <CopyButton text={job.base_model} />
                </div>
              </div>

              {/* Type */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Type</span>
                <span className="text-sm text-white">Conversation</span>
              </div>

              {/* State */}
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400">State</span>
                <span className={`flex items-center gap-1.5 text-sm ${statusConfig.color}`}>
                  {statusConfig.spin && <Loader2 className="w-3 h-3 animate-spin" />}
                  {statusConfig.label}
                </span>
              </div>

              {/* Created On */}
              <div className="flex justify-between items-start">
                <span className="text-sm text-gray-400">Created On</span>
                <span className="text-sm text-white text-right">{formatDate(job.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Configuration Section */}
          <div className="bg-[#111411] rounded-xl border border-white/10 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Configuration</h2>

            <div className="space-y-4">
              {/* Dataset */}
              <div className="flex justify-between items-start">
                <span className="text-sm text-gray-400">Dataset</span>
                <div className="flex items-center gap-1 max-w-[180px]">
                  <span className="text-sm text-cyan-400 truncate">{job.dataset_path?.split('/').pop() || 'N/A'}</span>
                  {job.dataset_path && <CopyButton text={job.dataset_path} />}
                </div>
              </div>

              {/* Evaluation Dataset */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Evaluation Dataset</span>
                <span className="text-sm text-white">{job.eval_dataset || 'N/A'}</span>
              </div>

              {/* Epochs */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Epochs</span>
                <span className="text-sm text-white">{job.config?.epochs || 1}</span>
              </div>

              {/* LoRA Rank */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">LoRA Rank</span>
                <span className="text-sm text-white">{job.config?.lora_rank || 8}</span>
              </div>

              {/* Learning Rate */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Learning Rate</span>
                <span className="text-sm text-white">{job.config?.learning_rate || 0.0001}</span>
              </div>

              {/* Max Context Length */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Max Context Length</span>
                <span className="text-sm text-white">{job.config?.max_seq_length || 'Not set'}</span>
              </div>

              {/* GPU Type */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">GPU Type</span>
                <span className="text-sm text-white">{job.gpu_type || 'A100'}</span>
              </div>

              {/* Turbo Mode */}
              <div className="flex justify-between">
                <span className="text-sm text-gray-400">Turbo Mode</span>
                <span className="text-sm text-white">{job.config?.turbo_mode ? 'On' : 'Off'}</span>
              </div>
            </div>
          </div>

          {/* Deployments Section */}
          <div className="bg-[#111411] rounded-xl border border-white/10 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Deployments</h2>

            {job.deployments?.length > 0 ? (
              <div className="space-y-3">
                {job.deployments.map((deployment, idx) => (
                  <div key={idx} className="p-3 bg-white/5 rounded-lg">
                    <div className="text-sm text-white">{deployment.name}</div>
                    <div className="text-xs text-gray-500">{deployment.status}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No current deployments.</p>
            )}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {job.status === 'failed' && job.error_message && (
        <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-red-400 font-medium">Job Failed</h3>
              <p className="text-sm text-red-400/80 mt-1">{job.error_message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Logs Modal */}
      {showLogs && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-[#1a1f2e] rounded-xl border border-white/10 w-full max-w-4xl max-h-[80vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Logs: {job.name}</h3>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={fetchLogs}>
                  <RefreshCw className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setShowLogs(false)}>
                  Close
                </Button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                {logs || 'Loading...'}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

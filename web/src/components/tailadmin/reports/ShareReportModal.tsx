import { FC, useState, useRef, useCallback, useEffect } from "react";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import Select from "../form/Select";
import Label from "../form/Label";
import { apiPost } from "../../../utils/api";

// Format options for social media
const FORMAT_OPTIONS = [
  { value: "twitter", label: "Twitter (1200x675)" },
  { value: "linkedin", label: "LinkedIn (1200x627)" },
  { value: "generic", label: "Generic (1200x630)" },
];

// Format dimensions for preview aspect ratio
const FORMAT_DIMENSIONS: Record<string, { width: number; height: number }> = {
  twitter: { width: 1200, height: 675 },
  linkedin: { width: 1200, height: 627 },
  generic: { width: 1200, height: 630 },
};

// Metric configuration
interface MetricsConfig {
  monthly_savings: boolean;
  annual_savings: boolean;
  percentage_saved: boolean;
  provider_comparison: boolean;
}

// Savings data structure
interface SavingsData {
  monthly_savings?: number;
  annual_savings?: number;
  percentage_saved?: number;
  provider_comparison?: {
    aws?: number;
    gcp?: number;
    azure?: number;
  };
}

interface ShareReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  savingsData?: SavingsData;
}

// Toggle Switch Component (inline to avoid dependency issues)
const ToggleSwitch: FC<{
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}> = ({ label, checked, onChange, disabled = false }) => {
  const handleToggle = () => {
    if (!disabled) {
      onChange(!checked);
    }
  };

  return (
    <label
      className={`flex cursor-pointer select-none items-center gap-3 text-sm font-medium ${
        disabled ? "text-gray-400" : "text-gray-700 dark:text-gray-400"
      }`}
      onClick={handleToggle}
    >
      <div className="relative">
        <div
          className={`block transition duration-150 ease-linear h-6 w-11 rounded-full ${
            disabled
              ? "bg-gray-100 pointer-events-none dark:bg-gray-800"
              : checked
              ? "bg-brand-500"
              : "bg-gray-200 dark:bg-white/10"
          }`}
        ></div>
        <div
          className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-theme-sm duration-150 ease-linear transform ${
            checked ? "translate-x-full" : "translate-x-0"
          }`}
        ></div>
      </div>
      {label}
    </label>
  );
};

// Format number as currency with abbreviation for large numbers
const formatCurrency = (value: number | undefined): string => {
  if (value === undefined || value === null) return "$0";
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(2)}`;
};

// Format percentage
const formatPercentage = (value: number | undefined): string => {
  if (value === undefined || value === null) return "0%";
  return `${value.toFixed(0)}%`;
};

const ShareReportModal: FC<ShareReportModalProps> = ({
  isOpen,
  onClose,
  savingsData,
}) => {
  // State for format and metrics configuration
  const [format, setFormat] = useState<string>("twitter");
  const [metrics, setMetrics] = useState<MetricsConfig>({
    monthly_savings: true,
    annual_savings: true,
    percentage_saved: true,
    provider_comparison: true,
  });

  // State for generation/download
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Ref for the preview element (for html2canvas)
  const previewRef = useRef<HTMLDivElement>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setGeneratedUrl(null);
      setError(null);
    }
  }, [isOpen]);

  // Handle metric toggle
  const handleMetricToggle = useCallback(
    (metric: keyof MetricsConfig) => (checked: boolean) => {
      setMetrics((prev) => ({ ...prev, [metric]: checked }));
    },
    []
  );

  // Handle format change
  const handleFormatChange = useCallback((value: string) => {
    setFormat(value);
    setGeneratedUrl(null); // Reset generated URL when format changes
  }, []);

  // Generate shareable report via API
  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const response = await apiPost("/api/v1/reports/generate", {
        format,
        metrics,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to generate report");
      }

      const data = await response.json();
      const shareableUrl = `${window.location.origin}/reports/${data.shareable_id}`;
      setGeneratedUrl(shareableUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setIsGenerating(false);
    }
  };

  // Download image using html2canvas
  const handleDownload = async () => {
    if (!previewRef.current) return;

    setIsDownloading(true);
    setError(null);

    try {
      // Dynamically import html2canvas to avoid SSR issues
      const html2canvas = (await import("html2canvas")).default;

      const canvas = await html2canvas(previewRef.current, {
        useCORS: true,
        scale: 2, // High-DPI support
        backgroundColor: "#1a1a2e",
        logging: false,
      });

      // Convert canvas to blob and download
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = `dumont-savings-report-${format}.png`;
          link.click();
          URL.revokeObjectURL(url);
        }
      }, "image/png");
    } catch (err) {
      setError("Failed to download image. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  };

  // Copy shareable URL to clipboard
  const handleCopyUrl = async () => {
    if (generatedUrl) {
      try {
        await navigator.clipboard.writeText(generatedUrl);
        // Could add a toast notification here
      } catch {
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = generatedUrl;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
    }
  };

  // Get current format dimensions
  const dimensions = FORMAT_DIMENSIONS[format] || FORMAT_DIMENSIONS.generic;
  const aspectRatio = dimensions.width / dimensions.height;

  // Default savings data for preview
  const defaultSavings: SavingsData = {
    monthly_savings: 644.80,
    annual_savings: 7737.60,
    percentage_saved: 72,
    provider_comparison: {
      aws: 892.30,
      gcp: 756.80,
      azure: 823.40,
    },
  };

  const displayData = savingsData || defaultSavings;

  // Check if there's any savings data available
  const hasSavingsData =
    displayData.monthly_savings !== undefined ||
    displayData.annual_savings !== undefined;

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-[900px] m-4">
      <div className="relative w-full max-w-[900px] overflow-hidden rounded-3xl bg-white p-4 dark:bg-gray-900 lg:p-8">
        {/* Header */}
        <div className="mb-6 pr-12">
          <h4 className="mb-2 text-2xl font-semibold text-gray-800 dark:text-white/90">
            Share Your Savings Report
          </h4>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Create a shareable image of your cost savings to showcase on social
            media.
          </p>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left Column - Configuration */}
          <div className="space-y-6">
            {/* Format Selector */}
            <div>
              <Label>Image Format</Label>
              <Select
                options={FORMAT_OPTIONS}
                defaultValue={format}
                onChange={handleFormatChange}
                placeholder="Select format"
              />
              <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                {format === "twitter" && "Optimized for Twitter/X posts"}
                {format === "linkedin" && "Optimized for LinkedIn posts"}
                {format === "generic" && "Standard format for any platform"}
              </p>
            </div>

            {/* Metric Toggles */}
            <div>
              <Label>Metrics to Include</Label>
              <div className="mt-3 space-y-4">
                <ToggleSwitch
                  label="Monthly Savings"
                  checked={metrics.monthly_savings}
                  onChange={handleMetricToggle("monthly_savings")}
                />
                <ToggleSwitch
                  label="Annual Savings"
                  checked={metrics.annual_savings}
                  onChange={handleMetricToggle("annual_savings")}
                />
                <ToggleSwitch
                  label="Savings Percentage"
                  checked={metrics.percentage_saved}
                  onChange={handleMetricToggle("percentage_saved")}
                />
                <ToggleSwitch
                  label="Provider Comparison"
                  checked={metrics.provider_comparison}
                  onChange={handleMetricToggle("provider_comparison")}
                />
              </div>
            </div>

            {/* Generated URL Display */}
            {generatedUrl && (
              <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 dark:border-brand-800 dark:bg-brand-900/20">
                <Label className="text-brand-700 dark:text-brand-300">
                  Shareable URL
                </Label>
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={generatedUrl}
                    className="flex-1 rounded-lg border border-brand-200 bg-white px-3 py-2 text-sm text-gray-800 dark:border-brand-700 dark:bg-gray-800 dark:text-white"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCopyUrl}
                    className="shrink-0"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                    Copy
                  </Button>
                </div>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
                {error}
              </div>
            )}
          </div>

          {/* Right Column - Preview */}
          <div>
            <Label>Preview</Label>
            <div
              className="mt-2 overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700"
              style={{
                aspectRatio: aspectRatio,
              }}
            >
              {/* Preview Content */}
              <div
                ref={previewRef}
                className="flex h-full w-full flex-col items-center justify-center p-6"
                style={{
                  background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
                }}
              >
                {/* Logo/Header */}
                <div className="mb-4 text-center">
                  <h3 className="text-lg font-bold text-white">
                    Dumont Cloud Savings
                  </h3>
                  <p className="text-xs text-gray-400">
                    GPU Cloud Cost Comparison
                  </p>
                </div>

                {/* Metrics Display */}
                <div className="flex flex-wrap justify-center gap-3">
                  {metrics.monthly_savings && (
                    <div className="rounded-lg bg-white/10 px-4 py-3 text-center backdrop-blur-sm">
                      <p className="text-xs font-medium text-gray-400">
                        Monthly Savings
                      </p>
                      <p className="text-xl font-bold text-emerald-400">
                        {formatCurrency(displayData.monthly_savings)}
                      </p>
                    </div>
                  )}

                  {metrics.annual_savings && (
                    <div className="rounded-lg bg-white/10 px-4 py-3 text-center backdrop-blur-sm">
                      <p className="text-xs font-medium text-gray-400">
                        Annual Savings
                      </p>
                      <p className="text-xl font-bold text-emerald-400">
                        {formatCurrency(displayData.annual_savings)}
                      </p>
                    </div>
                  )}

                  {metrics.percentage_saved && (
                    <div className="rounded-lg bg-white/10 px-4 py-3 text-center backdrop-blur-sm">
                      <p className="text-xs font-medium text-gray-400">
                        Saved vs AWS
                      </p>
                      <p className="text-xl font-bold text-emerald-400">
                        {formatPercentage(displayData.percentage_saved)}
                      </p>
                    </div>
                  )}
                </div>

                {/* Provider Comparison */}
                {metrics.provider_comparison &&
                  displayData.provider_comparison && (
                    <div className="mt-4 w-full max-w-xs">
                      <p className="mb-2 text-center text-xs font-medium text-gray-400">
                        vs. Major Cloud Providers
                      </p>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between rounded bg-orange-500/20 px-3 py-1.5">
                          <span className="text-xs text-orange-300">AWS</span>
                          <span className="text-xs font-bold text-orange-400">
                            {formatCurrency(
                              displayData.provider_comparison.aws
                            )}{" "}
                            /mo
                          </span>
                        </div>
                        <div className="flex items-center justify-between rounded bg-blue-500/20 px-3 py-1.5">
                          <span className="text-xs text-blue-300">GCP</span>
                          <span className="text-xs font-bold text-blue-400">
                            {formatCurrency(
                              displayData.provider_comparison.gcp
                            )}{" "}
                            /mo
                          </span>
                        </div>
                        <div className="flex items-center justify-between rounded bg-sky-500/20 px-3 py-1.5">
                          <span className="text-xs text-sky-300">Azure</span>
                          <span className="text-xs font-bold text-sky-400">
                            {formatCurrency(
                              displayData.provider_comparison.azure
                            )}{" "}
                            /mo
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                {/* No metrics selected message */}
                {!metrics.monthly_savings &&
                  !metrics.annual_savings &&
                  !metrics.percentage_saved &&
                  !metrics.provider_comparison && (
                    <p className="text-center text-sm text-gray-400">
                      Select at least one metric to display
                    </p>
                  )}

                {/* Footer */}
                <div className="mt-4 text-center">
                  <p className="text-[10px] text-gray-500">
                    dumontcloud.com
                  </p>
                </div>
              </div>
            </div>

            {/* Dimension Info */}
            <p className="mt-2 text-center text-xs text-gray-500 dark:text-gray-400">
              {dimensions.width} x {dimensions.height}px
            </p>
          </div>
        </div>

        {/* No Data Warning */}
        {!hasSavingsData && (
          <div className="mt-6 rounded-xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-700 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">
            <p className="font-medium">No savings data available</p>
            <p className="mt-1 text-xs">
              Generate your first instance to see your actual savings. Preview
              shows sample data.
            </p>
          </div>
        )}

        {/* Footer Actions */}
        <div className="mt-6 flex flex-col gap-3 border-t border-gray-200 pt-6 dark:border-gray-700 sm:flex-row sm:items-center sm:justify-end">
          <Button size="sm" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleDownload}
            disabled={isDownloading}
            startIcon={
              isDownloading ? (
                <svg
                  className="h-4 w-4 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              ) : (
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
              )
            }
          >
            {isDownloading ? "Downloading..." : "Download Image"}
          </Button>
          <Button
            size="sm"
            onClick={handleGenerate}
            disabled={
              isGenerating ||
              (!metrics.monthly_savings &&
                !metrics.annual_savings &&
                !metrics.percentage_saved &&
                !metrics.provider_comparison)
            }
            startIcon={
              isGenerating ? (
                <svg
                  className="h-4 w-4 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              ) : (
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
                  />
                </svg>
              )
            }
          >
            {isGenerating
              ? "Generating..."
              : generatedUrl
              ? "Regenerate"
              : "Generate Shareable Link"}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default ShareReportModal;

// Hook to use the ShareReportModal
export const useShareReportModal = () => {
  const [isOpen, setIsOpen] = useState(false);

  const openModal = useCallback(() => setIsOpen(true), []);
  const closeModal = useCallback(() => setIsOpen(false), []);

  return { isOpen, openModal, closeModal };
};

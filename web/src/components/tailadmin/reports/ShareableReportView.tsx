import { FC, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import PageMeta from "../common/PageMeta";
import Badge from "../ui/badge/Badge";
import { ArrowUpIcon } from "../../../icons";

// Report data from API
interface ReportData {
  shareable_id: string;
  format: string;
  savings_data: SavingsData;
  image_url?: string; // Generated image for social media og:image
  created_at: string;
}

interface SavingsData {
  monthly_savings?: number;
  annual_savings?: number;
  percentage_saved?: number;
  provider_comparison?: {
    aws?: number;
    gcp?: number;
    azure?: number;
  };
  time_period?: string;
}

interface MetricsConfig {
  monthly_savings: boolean;
  annual_savings: boolean;
  percentage_saved: boolean;
  provider_comparison: boolean;
}

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

// Format date for display
const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
};

// Loading spinner component
const LoadingSpinner: FC = () => (
  <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div className="text-center">
      <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-brand-500 border-t-transparent"></div>
      <p className="text-gray-500 dark:text-gray-400">Loading report...</p>
    </div>
  </div>
);

// Error state component
const ErrorState: FC<{ message: string }> = ({ message }) => (
  <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 dark:bg-gray-900">
    <div className="text-center">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
        <svg
          className="h-8 w-8 text-red-600 dark:text-red-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h2 className="mb-2 text-xl font-semibold text-gray-800 dark:text-white">
        {message}
      </h2>
      <p className="mb-6 text-gray-500 dark:text-gray-400">
        This report may have expired or been removed.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 rounded-lg bg-brand-500 px-6 py-3 font-medium text-white transition hover:bg-brand-600"
      >
        Create Your Own Savings Report
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
            d="M14 5l7 7m0 0l-7 7m7-7H3"
          />
        </svg>
      </Link>
    </div>
  </div>
);

// Metric card component
const MetricCard: FC<{
  label: string;
  value: string;
  icon?: React.ReactNode;
  colorClass?: string;
}> = ({ label, value, icon, colorClass = "text-emerald-500" }) => (
  <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
    {icon && (
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
        {icon}
      </div>
    )}
    <div>
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <h4
        className={`mt-2 text-2xl font-bold md:text-3xl ${colorClass} dark:brightness-110`}
      >
        {value}
      </h4>
    </div>
  </div>
);

// Provider comparison row component
const ProviderRow: FC<{
  name: string;
  cost: number | undefined;
  colorClass: string;
  bgClass: string;
}> = ({ name, cost, colorClass, bgClass }) => (
  <div
    className={`flex items-center justify-between rounded-lg px-4 py-3 ${bgClass}`}
  >
    <span className={`text-sm font-medium ${colorClass}`}>{name}</span>
    <span className={`text-sm font-bold ${colorClass}`}>
      {formatCurrency(cost)}/mo
    </span>
  </div>
);

// Savings Icon
const SavingsIcon: FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

// Percentage Icon
const PercentageIcon: FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
    />
  </svg>
);

const ShareableReportView: FC = () => {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      if (!id) {
        setError("Report not found");
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`/api/v1/reports/${id}`);

        if (!response.ok) {
          if (response.status === 404) {
            setError("Report not found");
          } else {
            setError("Failed to load report");
          }
          setLoading(false);
          return;
        }

        const data = await response.json();
        setReport(data);
      } catch {
        setError("Failed to load report");
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [id]);

  // Show loading state
  if (loading) {
    return <LoadingSpinner />;
  }

  // Show error state
  if (error || !report) {
    return (
      <>
        <PageMeta
          title="Report Not Found | Dumont Cloud"
          description="This savings report may have expired or been removed."
        />
        <ErrorState message={error || "Report not found"} />
      </>
    );
  }

  const { savings_data } = report;
  const currentUrl = `${window.location.origin}/reports/${id}`;
  const reportTitle = `Saving ${formatCurrency(savings_data.annual_savings || 0)}/year with Dumont Cloud`;
  const reportDescription = `I'm saving ${formatPercentage(savings_data.percentage_saved)}  on GPU cloud costs compared to major providers. Check out my savings report!`;

  // Determine which metrics are available
  const hasMonthly = savings_data.monthly_savings !== undefined;
  const hasAnnual = savings_data.annual_savings !== undefined;
  const hasPercentage = savings_data.percentage_saved !== undefined;
  const hasComparison = savings_data.provider_comparison !== undefined;

  return (
    <>
      {/* Social Media Meta Tags */}
      <PageMeta
        title={`${reportTitle} | Dumont Cloud`}
        description={reportDescription}
        ogTitle={reportTitle}
        ogDescription={reportDescription}
        ogImage={report.image_url}
        ogUrl={currentUrl}
        ogType="article"
        twitterCard="summary_large_image"
        twitterSite="@dumontcloud"
      />

      {/* Main Container - No navbar, read-only view */}
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <header className="border-b border-gray-200 bg-white px-4 py-6 dark:border-gray-800 dark:bg-gray-900/50">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500">
                  <svg
                    className="h-6 w-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-gray-800 dark:text-white">
                    Dumont Cloud
                  </h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    GPU Cloud Savings Report
                  </p>
                </div>
              </div>
              <Badge color="success">
                <ArrowUpIcon />
                Verified Savings
              </Badge>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="px-4 py-8">
          <div className="mx-auto max-w-4xl">
            {/* Report Header */}
            <div className="mb-8 text-center">
              <h2 className="mb-2 text-3xl font-bold text-gray-800 dark:text-white md:text-4xl">
                Cost Savings Report
              </h2>
              <p className="text-gray-500 dark:text-gray-400">
                Generated on {formatDate(report.created_at)}
              </p>
            </div>

            {/* Metrics Grid */}
            <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6 lg:grid-cols-3">
              {hasMonthly && (
                <MetricCard
                  label="Monthly Savings"
                  value={formatCurrency(savings_data.monthly_savings)}
                  icon={
                    <SavingsIcon className="h-6 w-6 text-gray-800 dark:text-white/90" />
                  }
                />
              )}

              {hasAnnual && (
                <MetricCard
                  label="Annual Savings"
                  value={formatCurrency(savings_data.annual_savings)}
                  icon={
                    <SavingsIcon className="h-6 w-6 text-gray-800 dark:text-white/90" />
                  }
                />
              )}

              {hasPercentage && (
                <MetricCard
                  label="Saved vs Competition"
                  value={formatPercentage(savings_data.percentage_saved)}
                  icon={
                    <PercentageIcon className="h-6 w-6 text-gray-800 dark:text-white/90" />
                  }
                />
              )}
            </div>

            {/* Provider Comparison */}
            {hasComparison && savings_data.provider_comparison && (
              <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
                <h3 className="mb-4 text-lg font-semibold text-gray-800 dark:text-white">
                  Comparison with Major Cloud Providers
                </h3>
                <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
                  Monthly cost for equivalent GPU compute on other platforms
                </p>
                <div className="space-y-3">
                  {savings_data.provider_comparison.aws !== undefined && (
                    <ProviderRow
                      name="Amazon Web Services (AWS)"
                      cost={savings_data.provider_comparison.aws}
                      colorClass="text-orange-600 dark:text-orange-400"
                      bgClass="bg-orange-50 dark:bg-orange-900/20"
                    />
                  )}
                  {savings_data.provider_comparison.gcp !== undefined && (
                    <ProviderRow
                      name="Google Cloud Platform (GCP)"
                      cost={savings_data.provider_comparison.gcp}
                      colorClass="text-blue-600 dark:text-blue-400"
                      bgClass="bg-blue-50 dark:bg-blue-900/20"
                    />
                  )}
                  {savings_data.provider_comparison.azure !== undefined && (
                    <ProviderRow
                      name="Microsoft Azure"
                      cost={savings_data.provider_comparison.azure}
                      colorClass="text-sky-600 dark:text-sky-400"
                      bgClass="bg-sky-50 dark:bg-sky-900/20"
                    />
                  )}
                </div>
              </div>
            )}

            {/* Time Period */}
            {savings_data.time_period && (
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Savings calculated for: {savings_data.time_period}
                </p>
              </div>
            )}

            {/* Call to Action */}
            <div className="mt-10 rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50 to-brand-100 p-6 text-center dark:border-brand-800 dark:from-brand-900/20 dark:to-brand-900/10 md:p-8">
              <h3 className="mb-2 text-xl font-bold text-gray-800 dark:text-white">
                Start Saving on GPU Cloud Today
              </h3>
              <p className="mb-6 text-gray-600 dark:text-gray-300">
                Join thousands of developers and ML teams who are reducing
                their cloud costs with Dumont Cloud.
              </p>
              <Link
                to="/"
                className="inline-flex items-center gap-2 rounded-lg bg-brand-500 px-6 py-3 font-medium text-white transition hover:bg-brand-600"
              >
                Get Started Free
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
                    d="M14 5l7 7m0 0l-7 7m7-7H3"
                  />
                </svg>
              </Link>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-200 bg-white px-4 py-6 dark:border-gray-800 dark:bg-gray-900/50">
          <div className="mx-auto max-w-4xl text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              &copy; {new Date().getFullYear()} Dumont Cloud. All rights
              reserved.
            </p>
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
              This is a verified savings report. Data shown is anonymized and
              does not include personal information.
            </p>
          </div>
        </footer>
      </div>
    </>
  );
};

export default ShareableReportView;

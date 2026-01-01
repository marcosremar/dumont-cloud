-- Migration: Add economy widget tables for cost savings tracking
-- Date: 2025-12-31
-- Description: Creates tables for storing savings history snapshots and
--              provider pricing data for AWS/GCP/Azure comparison.

-- ============================================================================
-- Table: savings_history
-- Purpose: Store periodic savings snapshots for each user to track
--          lifetime and historical cost savings over time.
-- ============================================================================

CREATE TABLE IF NOT EXISTS savings_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,

    -- Snapshot timestamp
    snapshot_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Comparison provider (AWS, GCP, Azure)
    provider VARCHAR(20) NOT NULL DEFAULT 'AWS',

    -- Aggregated savings for the period
    period_type VARCHAR(20) NOT NULL DEFAULT 'daily',  -- 'daily', 'weekly', 'monthly'

    -- GPU usage details for this period
    gpu_type VARCHAR(100) NOT NULL,
    hours_used FLOAT NOT NULL DEFAULT 0.0,

    -- Cost data
    cost_dumont FLOAT NOT NULL DEFAULT 0.0,
    cost_provider FLOAT NOT NULL DEFAULT 0.0,
    savings_amount FLOAT NOT NULL DEFAULT 0.0,
    savings_percentage FLOAT NOT NULL DEFAULT 0.0,

    -- Reference to usage record (optional)
    usage_record_id INTEGER REFERENCES usage_records(id),

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_savings_history_user_id ON savings_history(user_id);
CREATE INDEX IF NOT EXISTS idx_savings_history_snapshot_date ON savings_history(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_savings_history_user_provider ON savings_history(user_id, provider);
CREATE INDEX IF NOT EXISTS idx_savings_history_user_period ON savings_history(user_id, snapshot_date, period_type);

-- Add comments for documentation
COMMENT ON TABLE savings_history IS 'Tracks historical cost savings per user for economy widget';
COMMENT ON COLUMN savings_history.user_id IS 'User identifier';
COMMENT ON COLUMN savings_history.provider IS 'Cloud provider used for comparison (AWS, GCP, Azure)';
COMMENT ON COLUMN savings_history.period_type IS 'Aggregation period: daily, weekly, or monthly';
COMMENT ON COLUMN savings_history.savings_amount IS 'Absolute savings in USD';
COMMENT ON COLUMN savings_history.savings_percentage IS 'Percentage savings compared to provider';

-- ============================================================================
-- Table: provider_pricing
-- Purpose: Store cloud provider GPU pricing data for comparison calculations.
--          Updated periodically to reflect current market rates.
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_pricing (
    id SERIAL PRIMARY KEY,

    -- Provider identification
    provider VARCHAR(20) NOT NULL,  -- 'AWS', 'GCP', 'Azure', 'Dumont'

    -- GPU details
    gpu_type VARCHAR(100) NOT NULL,
    gpu_name VARCHAR(200),  -- Display name (e.g., "NVIDIA A100 80GB")
    vram_gb INTEGER,

    -- Pricing (per hour in USD)
    price_per_hour FLOAT NOT NULL,

    -- Instance type (for cloud providers)
    instance_type VARCHAR(100),  -- e.g., 'p4d.24xlarge' for AWS

    -- Region (pricing can vary by region)
    region VARCHAR(50) DEFAULT 'us-east-1',

    -- Pricing type
    pricing_type VARCHAR(30) DEFAULT 'on-demand',  -- 'on-demand', 'spot', 'reserved'

    -- Validity period
    effective_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP,  -- NULL means currently active

    -- Metadata
    source VARCHAR(200),  -- Where pricing was sourced from
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Unique constraint for active pricing per provider/gpu/region/pricing_type
CREATE UNIQUE INDEX IF NOT EXISTS idx_provider_pricing_unique_active
    ON provider_pricing(provider, gpu_type, region, pricing_type)
    WHERE is_active = true;

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_provider_pricing_provider ON provider_pricing(provider);
CREATE INDEX IF NOT EXISTS idx_provider_pricing_gpu_type ON provider_pricing(gpu_type);
CREATE INDEX IF NOT EXISTS idx_provider_pricing_active ON provider_pricing(is_active);
CREATE INDEX IF NOT EXISTS idx_provider_pricing_provider_gpu ON provider_pricing(provider, gpu_type) WHERE is_active = true;

-- Add comments for documentation
COMMENT ON TABLE provider_pricing IS 'Cloud provider GPU pricing for cost comparison calculations';
COMMENT ON COLUMN provider_pricing.provider IS 'Cloud provider name: AWS, GCP, Azure, or Dumont';
COMMENT ON COLUMN provider_pricing.price_per_hour IS 'Hourly rate in USD';
COMMENT ON COLUMN provider_pricing.pricing_type IS 'Pricing tier: on-demand, spot, or reserved';
COMMENT ON COLUMN provider_pricing.is_active IS 'Whether this pricing record is currently active';

-- ============================================================================
-- Seed initial provider pricing data
-- These are baseline prices for common GPU types
-- ============================================================================

-- AWS pricing (approximate on-demand rates as of 2024)
INSERT INTO provider_pricing (provider, gpu_type, gpu_name, vram_gb, price_per_hour, instance_type, region, pricing_type, source)
VALUES
    ('AWS', 'RTX 4090', 'NVIDIA RTX 4090', 24, 4.50, 'g6.xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
    ('AWS', 'A100', 'NVIDIA A100 80GB', 80, 8.50, 'p4d.24xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
    ('AWS', 'A10G', 'NVIDIA A10G', 24, 1.50, 'g5.xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
    ('AWS', 'H100', 'NVIDIA H100 80GB', 80, 12.00, 'p5.48xlarge', 'us-east-1', 'on-demand', 'AWS public pricing'),
    ('AWS', 'RTX 3090', 'NVIDIA RTX 3090', 24, 3.50, 'g4dn.xlarge', 'us-east-1', 'on-demand', 'AWS public pricing')
ON CONFLICT DO NOTHING;

-- GCP pricing (approximate on-demand rates)
INSERT INTO provider_pricing (provider, gpu_type, gpu_name, vram_gb, price_per_hour, instance_type, region, pricing_type, source)
VALUES
    ('GCP', 'RTX 4090', 'NVIDIA RTX 4090', 24, 4.20, 'n1-standard-8', 'us-central1', 'on-demand', 'GCP public pricing'),
    ('GCP', 'A100', 'NVIDIA A100 80GB', 80, 7.80, 'a2-highgpu-1g', 'us-central1', 'on-demand', 'GCP public pricing'),
    ('GCP', 'A10G', 'NVIDIA A10G', 24, 1.35, 'n1-standard-4', 'us-central1', 'on-demand', 'GCP public pricing'),
    ('GCP', 'H100', 'NVIDIA H100 80GB', 80, 11.00, 'a3-highgpu-8g', 'us-central1', 'on-demand', 'GCP public pricing'),
    ('GCP', 'RTX 3090', 'NVIDIA RTX 3090', 24, 3.20, 'n1-standard-8', 'us-central1', 'on-demand', 'GCP public pricing')
ON CONFLICT DO NOTHING;

-- Azure pricing (approximate on-demand rates)
INSERT INTO provider_pricing (provider, gpu_type, gpu_name, vram_gb, price_per_hour, instance_type, region, pricing_type, source)
VALUES
    ('Azure', 'RTX 4090', 'NVIDIA RTX 4090', 24, 4.80, 'NC24ads_A100_v4', 'eastus', 'on-demand', 'Azure public pricing'),
    ('Azure', 'A100', 'NVIDIA A100 80GB', 80, 9.00, 'NC96ads_A100_v4', 'eastus', 'on-demand', 'Azure public pricing'),
    ('Azure', 'A10G', 'NVIDIA A10G', 24, 1.60, 'NC8as_T4_v3', 'eastus', 'on-demand', 'Azure public pricing'),
    ('Azure', 'H100', 'NVIDIA H100 80GB', 80, 13.00, 'NC96ads_H100_v5', 'eastus', 'on-demand', 'Azure public pricing'),
    ('Azure', 'RTX 3090', 'NVIDIA RTX 3090', 24, 3.80, 'NC12s_v3', 'eastus', 'on-demand', 'Azure public pricing')
ON CONFLICT DO NOTHING;

-- Dumont pricing (competitive rates)
INSERT INTO provider_pricing (provider, gpu_type, gpu_name, vram_gb, price_per_hour, instance_type, region, pricing_type, source)
VALUES
    ('Dumont', 'RTX 4090', 'NVIDIA RTX 4090', 24, 1.14, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
    ('Dumont', 'A100', 'NVIDIA A100 80GB', 80, 2.50, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
    ('Dumont', 'A10G', 'NVIDIA A10G', 24, 0.50, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
    ('Dumont', 'H100', 'NVIDIA H100 80GB', 80, 4.50, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing'),
    ('Dumont', 'RTX 3090', 'NVIDIA RTX 3090', 24, 0.89, 'standard', 'global', 'on-demand', 'Dumont Cloud pricing')
ON CONFLICT DO NOTHING;

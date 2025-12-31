-- Migration: Create cost optimization tables
-- Date: 2025-12-31
-- Description: Creates the usage_metrics table for 30-day GPU utilization tracking
--              to support cost optimization recommendations.

-- Create usage_metrics table for storing historical GPU usage data
CREATE TABLE IF NOT EXISTS usage_metrics (
    id SERIAL PRIMARY KEY,

    -- Identification
    user_id VARCHAR(100) NOT NULL,
    instance_id VARCHAR(100) NOT NULL,
    gpu_type VARCHAR(100) NOT NULL,

    -- Utilization metrics (percentages 0-100)
    gpu_utilization FLOAT,          -- GPU compute utilization %
    memory_utilization FLOAT,       -- GPU memory utilization %

    -- Runtime and cost
    runtime_hours FLOAT DEFAULT 0.0,    -- Hours of runtime in this period
    cost_usd FLOAT DEFAULT 0.0,         -- Cost in USD for this period

    -- Flexible extra data storage (JSONB for efficient querying)
    extra_data JSONB,               -- {"idle_minutes": 45, "peak_utilization": 98, ...}

    -- Timestamp for historical tracking
    timestamp TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create indexes for efficient querying

-- Individual column indexes
CREATE INDEX IF NOT EXISTS idx_usage_metrics_user_id
    ON usage_metrics(user_id);

CREATE INDEX IF NOT EXISTS idx_usage_metrics_instance_id
    ON usage_metrics(instance_id);

CREATE INDEX IF NOT EXISTS idx_usage_metrics_gpu_type
    ON usage_metrics(gpu_type);

CREATE INDEX IF NOT EXISTS idx_usage_metrics_timestamp
    ON usage_metrics(timestamp);

-- Composite index for efficient 30-day queries by user and instance
CREATE INDEX IF NOT EXISTS idx_user_instance_timestamp
    ON usage_metrics(user_id, instance_id, timestamp);

-- Composite index for GPU type analysis by user
CREATE INDEX IF NOT EXISTS idx_user_gpu_timestamp
    ON usage_metrics(user_id, gpu_type, timestamp);

-- Add comments for documentation
COMMENT ON TABLE usage_metrics IS 'Historical GPU usage metrics for 30-day pattern analysis to generate cost optimization recommendations';

COMMENT ON COLUMN usage_metrics.user_id IS 'User identifier for the usage record';
COMMENT ON COLUMN usage_metrics.instance_id IS 'Instance identifier for the usage record';
COMMENT ON COLUMN usage_metrics.gpu_type IS 'Type of GPU being used (e.g., RTX 4090, RTX 4070)';
COMMENT ON COLUMN usage_metrics.gpu_utilization IS 'GPU compute utilization percentage (0-100)';
COMMENT ON COLUMN usage_metrics.memory_utilization IS 'GPU memory utilization percentage (0-100)';
COMMENT ON COLUMN usage_metrics.runtime_hours IS 'Hours of runtime during this measurement period';
COMMENT ON COLUMN usage_metrics.cost_usd IS 'Cost in USD for this measurement period';
COMMENT ON COLUMN usage_metrics.extra_data IS 'Additional metrics as JSONB (idle_minutes, peak_utilization, etc.)';
COMMENT ON COLUMN usage_metrics.timestamp IS 'When this usage data was recorded';

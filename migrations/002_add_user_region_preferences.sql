-- Migration: Add user_region_preferences table
-- Date: 2025-12-31
-- Description: Creates table for storing user region preferences for GPU provisioning.
--              Supports preferred region, fallback regions, and data residency requirements.

-- Create user_region_preferences table
CREATE TABLE IF NOT EXISTS user_region_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    preferred_region VARCHAR(100) NOT NULL,
    fallback_regions JSONB,
    data_residency_requirement VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_region_preferences_user_id ON user_region_preferences (user_id);
CREATE INDEX IF NOT EXISTS idx_user_region_residency ON user_region_preferences (user_id, data_residency_requirement);

-- Add comments for documentation
COMMENT ON TABLE user_region_preferences IS 'User preferences for GPU region selection and failover';
COMMENT ON COLUMN user_region_preferences.user_id IS 'Unique user identifier';
COMMENT ON COLUMN user_region_preferences.preferred_region IS 'Primary preferred region for GPU provisioning';
COMMENT ON COLUMN user_region_preferences.fallback_regions IS 'Ordered list of fallback regions as JSON array';
COMMENT ON COLUMN user_region_preferences.data_residency_requirement IS 'Data residency requirement (e.g., EU_GDPR, US_ONLY)';
COMMENT ON COLUMN user_region_preferences.created_at IS 'Timestamp when preference was created';
COMMENT ON COLUMN user_region_preferences.updated_at IS 'Timestamp when preference was last updated';

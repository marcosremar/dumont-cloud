-- Migration: Create NPS (Net Promoter Score) system tables
-- Date: 2025-12-31
-- Description: Creates tables for NPS survey responses, configuration,
--              and user interaction tracking for rate limiting

-- ============================================================================
-- Table: nps_responses
-- Description: Stores NPS survey responses with scores, comments, and follow-up tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS nps_responses (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,

    -- Score and feedback
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 10),
    comment TEXT,

    -- Survey context
    trigger_type VARCHAR(50) NOT NULL,

    -- Categorization (calculated from score: 0-6 = detractor, 7-8 = passive, 9-10 = promoter)
    category VARCHAR(20) NOT NULL CHECK (category IN ('detractor', 'passive', 'promoter')),

    -- Follow-up tracking for detractors
    needs_followup BOOLEAN DEFAULT FALSE,
    followup_completed BOOLEAN DEFAULT FALSE,
    followup_notes TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for nps_responses
CREATE INDEX IF NOT EXISTS idx_nps_responses_user_id ON nps_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_nps_responses_trigger_type ON nps_responses(trigger_type);
CREATE INDEX IF NOT EXISTS idx_nps_responses_created_at ON nps_responses(created_at);
CREATE INDEX IF NOT EXISTS idx_nps_responses_needs_followup ON nps_responses(needs_followup);

-- Composite indexes for frequent queries
CREATE INDEX IF NOT EXISTS idx_nps_user_trigger ON nps_responses(user_id, trigger_type);
CREATE INDEX IF NOT EXISTS idx_nps_category_date ON nps_responses(category, created_at);
CREATE INDEX IF NOT EXISTS idx_nps_followup ON nps_responses(needs_followup, followup_completed);

-- Comments for documentation
COMMENT ON TABLE nps_responses IS 'Stores NPS survey responses from users';
COMMENT ON COLUMN nps_responses.user_id IS 'User identifier who submitted the response';
COMMENT ON COLUMN nps_responses.score IS 'NPS score from 0-10';
COMMENT ON COLUMN nps_responses.comment IS 'Optional text feedback from user';
COMMENT ON COLUMN nps_responses.trigger_type IS 'What triggered the survey: first_deployment, monthly, issue_resolution';
COMMENT ON COLUMN nps_responses.category IS 'NPS category: detractor (0-6), passive (7-8), promoter (9-10)';
COMMENT ON COLUMN nps_responses.needs_followup IS 'Flag for detractor responses requiring follow-up';
COMMENT ON COLUMN nps_responses.followup_completed IS 'Whether follow-up has been completed';
COMMENT ON COLUMN nps_responses.followup_notes IS 'Notes from follow-up interaction';

-- ============================================================================
-- Table: nps_survey_config
-- Description: Configuration for NPS survey triggers and frequency
-- ============================================================================
CREATE TABLE IF NOT EXISTS nps_survey_config (
    id SERIAL PRIMARY KEY,
    trigger_type VARCHAR(50) NOT NULL UNIQUE,

    -- Configuration settings
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    frequency_days INTEGER NOT NULL DEFAULT 30,

    -- Customization
    title VARCHAR(200),
    description VARCHAR(500),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for nps_survey_config
CREATE INDEX IF NOT EXISTS idx_nps_survey_config_trigger_type ON nps_survey_config(trigger_type);

-- Comments for documentation
COMMENT ON TABLE nps_survey_config IS 'Configuration for NPS survey triggers';
COMMENT ON COLUMN nps_survey_config.trigger_type IS 'Type of trigger: first_deployment, monthly, issue_resolution';
COMMENT ON COLUMN nps_survey_config.enabled IS 'Whether this trigger is active';
COMMENT ON COLUMN nps_survey_config.frequency_days IS 'Minimum days between surveys for this trigger';
COMMENT ON COLUMN nps_survey_config.title IS 'Custom survey title for this trigger';
COMMENT ON COLUMN nps_survey_config.description IS 'Custom description/context for this trigger';

-- Insert default configurations
INSERT INTO nps_survey_config (trigger_type, enabled, frequency_days, title, description, created_at, updated_at)
VALUES
    ('first_deployment', TRUE, 0, 'How was your first deployment?', 'We would love to hear about your experience with your first deployment.', NOW(), NOW()),
    ('monthly', TRUE, 30, 'How likely are you to recommend us?', 'Your feedback helps us improve our service.', NOW(), NOW()),
    ('issue_resolution', TRUE, 7, 'How was your support experience?', 'Let us know how we did resolving your issue.', NOW(), NOW())
ON CONFLICT (trigger_type) DO NOTHING;

-- ============================================================================
-- Table: nps_user_interactions
-- Description: Tracks user interactions with NPS surveys for rate limiting
-- ============================================================================
CREATE TABLE IF NOT EXISTS nps_user_interactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,

    -- Interaction type
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('shown', 'dismissed', 'submitted')),

    -- Survey context
    trigger_type VARCHAR(50) NOT NULL,

    -- Reference to response (if submitted)
    response_id INTEGER REFERENCES nps_responses(id) ON DELETE SET NULL,

    -- Additional metadata (JSON string)
    interaction_metadata VARCHAR(1000),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for nps_user_interactions
CREATE INDEX IF NOT EXISTS idx_nps_user_interactions_user_id ON nps_user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_nps_user_interactions_interaction_type ON nps_user_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_nps_user_interactions_trigger_type ON nps_user_interactions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_nps_user_interactions_created_at ON nps_user_interactions(created_at);

-- Composite indexes for rate limiting queries
CREATE INDEX IF NOT EXISTS idx_nps_interaction_user_type ON nps_user_interactions(user_id, interaction_type);
CREATE INDEX IF NOT EXISTS idx_nps_interaction_user_trigger ON nps_user_interactions(user_id, trigger_type, created_at);
CREATE INDEX IF NOT EXISTS idx_nps_interaction_date ON nps_user_interactions(interaction_type, created_at);

-- Comments for documentation
COMMENT ON TABLE nps_user_interactions IS 'Tracks user interactions with NPS surveys for rate limiting';
COMMENT ON COLUMN nps_user_interactions.user_id IS 'User identifier';
COMMENT ON COLUMN nps_user_interactions.interaction_type IS 'Type of interaction: shown, dismissed, submitted';
COMMENT ON COLUMN nps_user_interactions.trigger_type IS 'Survey trigger type associated with this interaction';
COMMENT ON COLUMN nps_user_interactions.response_id IS 'Reference to nps_responses if interaction was a submission';
COMMENT ON COLUMN nps_user_interactions.interaction_metadata IS 'JSON string with additional data (e.g., dismiss reason)';

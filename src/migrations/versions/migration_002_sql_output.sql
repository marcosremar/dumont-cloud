-- Generated migration SQL for verification
-- Run with: python3 -m alembic upgrade head --sql
-- To apply: python3 -m alembic upgrade head

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001

CREATE TABLE users (
    id SERIAL NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT 'false' NOT NULL,
    verification_token VARCHAR(255),
    verification_token_expires_at TIMESTAMP WITHOUT TIME ZONE,
    is_trial BOOLEAN DEFAULT 'true' NOT NULL,
    trial_gpu_seconds_remaining INTEGER DEFAULT '7200' NOT NULL,
    trial_started_at TIMESTAMP WITHOUT TIME ZONE,
    trial_notified_75 BOOLEAN DEFAULT 'false' NOT NULL,
    trial_notified_90 BOOLEAN DEFAULT 'false' NOT NULL,
    trial_notified_100 BOOLEAN DEFAULT 'false' NOT NULL,
    vast_api_key VARCHAR(255),
    settings TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_is_trial ON users (is_trial);

CREATE INDEX ix_users_verification_token ON users (verification_token);

CREATE INDEX idx_user_trial_status ON users (is_trial, is_verified);

CREATE INDEX idx_user_verification ON users (verification_token, verification_token_expires_at);

INSERT INTO alembic_version (version_num) VALUES ('001') RETURNING alembic_version.version_num;

-- Running upgrade 001 -> 002

CREATE TABLE email_verification_tokens (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    token VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_email_verification_tokens_user_id ON email_verification_tokens (user_id);

CREATE UNIQUE INDEX ix_email_verification_tokens_token ON email_verification_tokens (token);

CREATE INDEX idx_token_expiration ON email_verification_tokens (token, expires_at);

UPDATE alembic_version SET version_num='002' WHERE alembic_version.version_num = '001';

COMMIT;

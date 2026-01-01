"""Create users table with trial support

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000+00:00

Creates the users table with:
- Basic user fields (email, hashed_password)
- Email verification fields (is_verified, verification_token, verification_token_expires_at)
- Trial management fields (is_trial, trial_gpu_seconds_remaining, trial_started_at)
- Trial notification tracking (trial_notified_75, trial_notified_90, trial_notified_100)
- VAST.ai integration (vast_api_key)
- User settings (settings as JSON Text)
- Timestamps (created_at, updated_at)
- Indexes for performance on email and trial status queries

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),

        # Email verification
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('verification_token_expires_at', sa.DateTime(), nullable=True),

        # Trial management
        sa.Column('is_trial', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('trial_gpu_seconds_remaining', sa.Integer(), nullable=False, server_default='7200'),
        sa.Column('trial_started_at', sa.DateTime(), nullable=True),

        # Trial notification flags (prevent duplicate emails)
        sa.Column('trial_notified_75', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('trial_notified_90', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('trial_notified_100', sa.Boolean(), nullable=False, server_default='false'),

        # VAST.ai integration
        sa.Column('vast_api_key', sa.String(255), nullable=True),

        # User settings (JSON stored as Text)
        sa.Column('settings', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Create indexes
    # Primary index on id is created automatically

    # Unique index on email for fast lookups and uniqueness
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Index on is_trial for filtering trial users
    op.create_index('ix_users_is_trial', 'users', ['is_trial'])

    # Index on verification_token for token lookup
    op.create_index('ix_users_verification_token', 'users', ['verification_token'])

    # Composite index for common trial status queries
    op.create_index('idx_user_trial_status', 'users', ['is_trial', 'is_verified'])

    # Composite index for verification token queries
    op.create_index('idx_user_verification', 'users', ['verification_token', 'verification_token_expires_at'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_user_verification', table_name='users')
    op.drop_index('idx_user_trial_status', table_name='users')
    op.drop_index('ix_users_verification_token', table_name='users')
    op.drop_index('ix_users_is_trial', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Drop table
    op.drop_table('users')

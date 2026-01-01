"""Create email_verification_tokens table

Revision ID: 002
Revises: 001
Create Date: 2026-01-01 00:01:00.000000+00:00

Creates the email_verification_tokens table with:
- Token reference to user (foreign key with CASCADE delete)
- Token string (unique, indexed)
- Expiration tracking (expires_at)
- Composite index for efficient token lookup with expiration check
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create email_verification_tokens table
    op.create_table(
        'email_verification_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )

    # Create indexes
    # Index on user_id for foreign key lookups
    op.create_index('ix_email_verification_tokens_user_id', 'email_verification_tokens', ['user_id'])

    # Unique index on token for fast lookups
    op.create_index('ix_email_verification_tokens_token', 'email_verification_tokens', ['token'], unique=True)

    # Composite index for efficient token lookup with expiration check
    op.create_index('idx_token_expiration', 'email_verification_tokens', ['token', 'expires_at'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_token_expiration', table_name='email_verification_tokens')
    op.drop_index('ix_email_verification_tokens_token', table_name='email_verification_tokens')
    op.drop_index('ix_email_verification_tokens_user_id', table_name='email_verification_tokens')

    # Drop table
    op.drop_table('email_verification_tokens')

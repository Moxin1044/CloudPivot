"""add token_version to users

Revision ID: 002_add_token_version
Revises: 001_rename_net_cols
Create Date: 2026-05-17 04:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_token_version'
down_revision = '001_rename_net_cols'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')

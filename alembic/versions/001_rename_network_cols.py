"""rename network columns mbps to kbps

Revision ID: 001_rename_net_cols
Revises: 
Create Date: 2026-05-17 03:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_rename_net_cols'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('host_metrics', 'network_in_mbps', new_column_name='network_in_kbps')
    op.alter_column('host_metrics', 'network_out_mbps', new_column_name='network_out_kbps')


def downgrade() -> None:
    op.alter_column('host_metrics', 'network_in_kbps', new_column_name='network_in_mbps')
    op.alter_column('host_metrics', 'network_out_kbps', new_column_name='network_out_mbps')

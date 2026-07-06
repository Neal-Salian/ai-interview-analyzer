"""Add zoom meeting URL columns to sessions

Revision ID: d8f3a9b7c1e2
Revises: 6741af1c4dc3
Create Date: 2026-06-25 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f3a9b7c1e2'
down_revision: Union[str, Sequence[str], None] = '6741af1c4dc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('zoom_join_url', sa.String(), nullable=True))
    op.add_column('sessions', sa.Column('zoom_start_url', sa.String(), nullable=True))
    op.add_column('sessions', sa.Column('zoom_password', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'zoom_password')
    op.drop_column('sessions', 'zoom_start_url')
    op.drop_column('sessions', 'zoom_join_url')

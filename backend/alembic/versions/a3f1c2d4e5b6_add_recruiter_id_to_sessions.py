"""add recruiter_id to sessions

Revision ID: a3f1c2d4e5b6
Revises: <your_current_head_revision>
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a3f1c2d4e5b6'
down_revision = "a1b2c3d4e5f6"  # replace with your current head: run `alembic heads` to find it
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'sessions',
        sa.Column(
            'recruiter_id',
            UUID(as_uuid=True),
            sa.ForeignKey('recruiters.id', ondelete='SET NULL'),
            nullable=True,  # nullable so existing rows don't break
        )
    )
    op.create_index('ix_sessions_recruiter_id', 'sessions', ['recruiter_id'])


def downgrade():
    op.drop_index('ix_sessions_recruiter_id', table_name='sessions')
    op.drop_column('sessions', 'recruiter_id')
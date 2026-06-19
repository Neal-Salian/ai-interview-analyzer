"""add panel members and recruiter_id to sessions

Revision ID: b7e2d3f4a1c9
Revises: <your_current_head>
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'b7e2d3f4a1c9'
down_revision = 'a3f1c2d4e5b6'
branch_labels = None
depends_on = None


def upgrade():
    # panel_members table
    op.create_table(
        'panel_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),       # e.g. "Technical Lead", "HR"
        sa.Column('notify_invite', sa.Boolean(), default=True),
        sa.Column('notify_report', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('panel_members')
"""add password reset tokens and panel members table

Revision ID: c9d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'c9d4e5f6a7b8'
down_revision = 'b7e2d3f4a1c9'  # update to your current head: run `alembic heads`
branch_labels = None
depends_on = None


def upgrade():
    # Password reset tokens on recruiters
    op.add_column('recruiters', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('recruiters', sa.Column('reset_token_expiry', sa.DateTime(), nullable=True))

    # panel_members table
    op.create_table(
        'panel_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True),
                  sa.ForeignKey('sessions.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('notify_invite', sa.Boolean(), default=True),
        sa.Column('notify_report', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('panel_members')
    op.drop_column('recruiters', 'reset_token_expiry')
    op.drop_column('recruiters', 'reset_token')
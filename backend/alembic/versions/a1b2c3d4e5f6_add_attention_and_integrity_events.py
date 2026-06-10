"""add_attention_and_integrity_events

Revision ID: a1b2c3d4e5f6
Revises: ffa91a50f083
Create Date: 2026-06-10 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ffa91a50f083'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add attention_events and integrity_events tables."""
    op.create_table('attention_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('direction', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('yaw', sa.Float(), nullable=True),
        sa.Column('pitch', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_attention_events_session_id'),
        'attention_events', ['session_id'], unique=False
    )

    op.create_table('integrity_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_integrity_events_session_id'),
        'integrity_events', ['session_id'], unique=False
    )


def downgrade() -> None:
    """Remove attention_events and integrity_events tables."""
    op.drop_index(op.f('ix_integrity_events_session_id'), table_name='integrity_events')
    op.drop_table('integrity_events')
    op.drop_index(op.f('ix_attention_events_session_id'), table_name='attention_events')
    op.drop_table('attention_events')

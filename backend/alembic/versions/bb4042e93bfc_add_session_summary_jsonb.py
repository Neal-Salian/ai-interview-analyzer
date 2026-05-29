"""add_session_summary_jsonb

Revision ID: bb4042e93bfc
Revises: cd887836b37d
Create Date: 2026-05-26 14:16:37.809235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'bb4042e93bfc'
down_revision: Union[str, Sequence[str], None] = 'cd887836b37d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "sessions",
        sa.Column("session_summary", JSONB, nullable=True),
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sessions", "session_summary")
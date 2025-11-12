"""add parts column to messages

Revision ID: 20251103_151604
Revises: ab71638bf1be
Create Date: 2025-11-03 15:16:04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251103_151604'
down_revision: Union[str, Sequence[str], None] = 'ab71638bf1be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add parts column to messages table for storing structured message parts."""
    # Add parts column as nullable JSON
    op.add_column('messages', sa.Column('parts', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove parts column from messages table."""
    # Drop parts column
    op.drop_column('messages', 'parts')

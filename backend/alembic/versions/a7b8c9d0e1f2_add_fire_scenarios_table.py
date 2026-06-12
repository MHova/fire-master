"""add fire_scenarios table

Revision ID: a7b8c9d0e1f2
Revises: e2dded77e6df
Create Date: 2026-04-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'e2dded77e6df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('fire_scenarios',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('overrides', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('fire_scenarios')

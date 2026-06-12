"""add_category_mappings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create category_mappings table."""
    op.create_table('category_mappings',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('raw_category', sa.String(), nullable=False),
        sa.Column('normalized_category', sa.String(), nullable=False),
        sa.Column('parent_category', sa.String(), nullable=False),
        sa.Column('is_discretionary', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_income', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_transfer', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('monarch_category_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('raw_category'),
    )
    op.create_index('ix_category_mappings_parent', 'category_mappings', ['parent_category'], unique=False)
    op.create_index('ix_category_mappings_normalized', 'category_mappings', ['normalized_category'], unique=False)


def downgrade() -> None:
    """Drop category_mappings table."""
    op.drop_index('ix_category_mappings_normalized', table_name='category_mappings')
    op.drop_index('ix_category_mappings_parent', table_name='category_mappings')
    op.drop_table('category_mappings')

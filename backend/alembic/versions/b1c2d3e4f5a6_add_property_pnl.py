"""add property pnl: properties, property_rules, transaction classification columns

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-05-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'properties',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('value_cents', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('loan_balance_cents', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('purchase_price_cents', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('potential_monthly_rental_cents', sa.BigInteger(), nullable=True),
        sa.Column('potential_monthly_rental_full_cents', sa.BigInteger(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('notes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )

    op.create_table(
        'property_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('match_type', sa.String(), server_default=sa.text("'merchant_substring'"), nullable=False),
        sa.Column('pattern', sa.String(), nullable=False),
        sa.Column('expense_category', sa.String(), nullable=True),
        sa.Column('require_tx_category', sa.String(), nullable=True),
        sa.Column('rule_kind', sa.String(), server_default=sa.text("'expense'"), nullable=False),
        sa.Column('priority', sa.Integer(), server_default=sa.text('100'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_property_rules_priority', 'property_rules', ['priority'])

    op.add_column('transactions', sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('transactions', sa.Column('property_category', sa.String(), nullable=True))
    op.add_column('transactions', sa.Column('property_source', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_transactions_property_id', 'transactions', 'properties',
        ['property_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('ix_transactions_property_id', 'transactions', ['property_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_transactions_property_id', table_name='transactions')
    op.drop_constraint('fk_transactions_property_id', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'property_source')
    op.drop_column('transactions', 'property_category')
    op.drop_column('transactions', 'property_id')
    op.drop_index('ix_property_rules_priority', table_name='property_rules')
    op.drop_table('property_rules')
    op.drop_table('properties')

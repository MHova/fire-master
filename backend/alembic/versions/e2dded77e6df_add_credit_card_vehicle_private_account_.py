"""add credit_card vehicle private account types

Revision ID: e2dded77e6df
Revises: 588da15b2e4d
Create Date: 2026-03-30 18:10:05.186160

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e2dded77e6df'
down_revision: Union[str, Sequence[str], None] = '588da15b2e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'credit_card'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'vehicle'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'private'")


def downgrade() -> None:
    pass  # PostgreSQL doesn't support removing enum values

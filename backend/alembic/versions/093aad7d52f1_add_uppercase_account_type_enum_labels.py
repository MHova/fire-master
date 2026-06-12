"""add uppercase account_type enum labels

SQLAlchemy persists Python enum member NAMES (CREDIT_CARD, VEHICLE, PRIVATE),
but the original migration added these three labels in lowercase — so on a
database built purely from the migration chain, inserting any credit card,
vehicle, or private-equity account fails (e.g. the first Monarch sync that
includes a credit card). Databases that pre-date this migration may already
carry the uppercase labels (added out-of-band); ADD VALUE IF NOT EXISTS makes
this a no-op there. The lowercase labels remain as dead labels — PostgreSQL
cannot drop enum values without a type rebuild, and nothing ever wrote them.

Revision ID: 093aad7d52f1
Revises: 909fc9d47628
Create Date: 2026-06-12 11:55:35.575600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '093aad7d52f1'
down_revision: Union[str, Sequence[str], None] = '909fc9d47628'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the enum labels the ORM actually writes (no-op where they exist)."""
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'CREDIT_CARD'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'VEHICLE'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'PRIVATE'")


def downgrade() -> None:
    """No-op: PostgreSQL cannot remove enum values without a type rebuild,
    and removing them would break rows written while upgraded."""
    pass

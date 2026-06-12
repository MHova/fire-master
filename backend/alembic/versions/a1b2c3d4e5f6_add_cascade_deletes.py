"""add cascade deletes to foreign keys

Revision ID: a1b2c3d4e5f6
Revises: 795027c04928
Create Date: 2026-03-14 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "795027c04928"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # transactions.account_id FK
    op.drop_constraint("transactions_account_id_fkey", "transactions", type_="foreignkey")
    op.create_foreign_key(
        "transactions_account_id_fkey",
        "transactions",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # balance_snapshots.account_id FK
    op.drop_constraint("balance_snapshots_account_id_fkey", "balance_snapshots", type_="foreignkey")
    op.create_foreign_key(
        "balance_snapshots_account_id_fkey",
        "balance_snapshots",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert balance_snapshots FK
    op.drop_constraint("balance_snapshots_account_id_fkey", "balance_snapshots", type_="foreignkey")
    op.create_foreign_key(
        "balance_snapshots_account_id_fkey",
        "balance_snapshots",
        "accounts",
        ["account_id"],
        ["id"],
    )

    # Revert transactions FK
    op.drop_constraint("transactions_account_id_fkey", "transactions", type_="foreignkey")
    op.create_foreign_key(
        "transactions_account_id_fkey",
        "transactions",
        "accounts",
        ["account_id"],
        ["id"],
    )

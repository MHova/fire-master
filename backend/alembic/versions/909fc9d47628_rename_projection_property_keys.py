"""rename projection property keys

Renames the user-facing base-config projection keys from the legacy
single-property names to role-based names, in BOTH the base config
(fire_config.custom_assumptions) and every scenario's overrides
(fire_scenarios.overrides). Values are moved verbatim — this migration
contains no data, only key renames.

Idempotent: each statement only fires when the old key exists and the
new key does not, so re-runs and empty databases are no-ops.

Revision ID: 909fc9d47628
Revises: b1c2d3e4f5a6
Create Date: 2026-06-11 22:26:29.340546

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '909fc9d47628'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KEY_PAIRS = [
    ("miami_purchase_price", "primary_property_purchase_price"),
    ("miami_agent_fee_pct", "primary_property_agent_fee_pct"),
    ("miami_mortgage_pi", "primary_property_mortgage_pi"),
    ("miami_cost_basis", "primary_property_cost_basis"),
    ("miami_ltcg_rate", "primary_property_ltcg_rate"),
]

# (table, jsonb column, path to the "projection" object inside that column)
TARGETS = [
    ("fire_config", "custom_assumptions", "{projection}"),
    ("fire_scenarios", "overrides", "{custom_assumptions,projection}"),
]


def _rename_sql(table: str, column: str, path: str, old: str, new: str) -> str:
    """Move <path>.<old> to <path>.<new>, only if old exists and new doesn't."""
    obj = f"{column} #> '{path}'"
    return f"""
        UPDATE {table}
        SET {column} = jsonb_set(
            {column},
            '{path}',
            ({obj}) - '{old}' || jsonb_build_object('{new}', {column} #> '{path[:-1]},{old}}}')
        )
        WHERE jsonb_exists({obj}, '{old}')
          AND NOT jsonb_exists({obj}, '{new}')
    """


def upgrade() -> None:
    """Rename legacy projection keys to role-based names."""
    for table, column, path in TARGETS:
        for old, new in KEY_PAIRS:
            op.execute(sa.text(_rename_sql(table, column, path, old, new)))


def downgrade() -> None:
    """Mirror: rename role-based keys back to the legacy names."""
    for table, column, path in TARGETS:
        for old, new in KEY_PAIRS:
            op.execute(sa.text(_rename_sql(table, column, path, new, old)))

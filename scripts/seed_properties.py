"""Seed properties + classification rules from config/properties.json into the database.

Imports the per-property facts (value, loan, rental potential, notes) into the `properties`
table, flattens every merchant list / merchant_rule / exclusion into `property_rules`, creates
the synthetic "Manual / Off-Monarch" account, inserts any configured `manual_income` entries
(income that never hit a synced account) as manual transactions, then reclassifies all
transactions. Start from config/properties.example.json if you don't have a config yet.

Idempotent: properties upsert by `key`; rules are fully rebuilt on each run (this is the
bootstrap importer — hand-edit rules in the UI afterward, not here).

Usage:
    cd backend && uv run python ../scripts/seed_properties.py
"""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import delete, select

from app.core.database import async_session_factory
from app.engines.property_pnl import PropertyPnLEngine
from app.models.account import Account
from app.models.enums import AccountType, DataSource
from app.models.property import Property
from app.models.property_rule import PropertyRule
from app.models.transaction import Transaction

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "properties.json").read_text())

MANUAL_ACCOUNT_NAME = "Manual / Off-Monarch"

# Per-property merchant-list name -> (canonical expense category, require_tx_category, priority)
LIST_MAP = {
    "mortgage_merchants": ("Mortgage", None, 50),
    "hoa_merchants": ("HOA / Condo Fees", None, 50),
    "assessment_merchants": ("Assessments", None, 50),
    "insurance_merchants": ("Insurance", None, 50),
    "utility_merchants": ("Utilities", None, 50),
    "repair_merchants": ("Repairs / Maintenance", None, 50),
    "tax_merchants": ("Property Tax", None, 50),
    "moorage_merchants": ("Moorage", "Rent", 60),
}

# merchant_rules short category key -> canonical expense category
RULE_CAT_MAP = {
    "hoa": "HOA / Condo Fees",
    "hoa_or_assessment": "HOA / Condo Fees",
    "assessment": "Assessments",
    "mortgage": "Mortgage",
    "insurance": "Insurance",
    "moorage": "Moorage",
    "property_tax": "Property Tax",
    "utilities": "Utilities",
    "repairs": "Repairs / Maintenance",
}


def _dollars(value) -> int:
    return int(round(value * 100)) if value is not None else None


async def main():
    async with async_session_factory() as session:
        props_cfg = CONFIG["properties"]

        # 1. Upsert properties by key.
        result = await session.execute(select(Property))
        existing = {p.key: p for p in result.scalars().all()}
        prop_by_key: dict[str, Property] = {}
        order = 0
        for key, c in props_cfg.items():
            cap_gains = CONFIG.get("capital_gains", {}).get(key, {})
            extra = {"capital_gains": cap_gains}
            if c.get("potential_rental_notes"):
                extra["potential_rental_notes"] = c["potential_rental_notes"]
            fields = dict(
                name=c["name"],
                address=c.get("address"),
                color=c.get("color"),
                value_cents=_dollars(c.get("value", 0)),
                loan_balance_cents=_dollars(c.get("loan_balance", 0)),
                purchase_price_cents=_dollars(c.get("purchase_price", 0)),
                potential_monthly_rental_cents=_dollars(c.get("potential_monthly_rental")),
                potential_monthly_rental_full_cents=_dollars(c.get("potential_monthly_rental_full")),
                display_order=order,
                is_active=True,
                notes=c.get("notes", []),
                extra_data=extra,
            )
            if key in existing:
                prop = existing[key]
                for f, v in fields.items():
                    setattr(prop, f, v)
                print(f"  UPDATE property '{key}'")
            else:
                prop = Property(key=key, **fields)
                session.add(prop)
                print(f"  CREATE property '{key}'")
            prop_by_key[key] = prop
            order += 1

        await session.flush()  # assign IDs

        # 2. Rebuild rules from scratch.
        await session.execute(delete(PropertyRule))
        rule_count = 0

        # 2a. Global exclusions (priority 0).
        for exc_list in CONFIG.get("exclusions", {}).values():
            if isinstance(exc_list, list):
                for pattern in exc_list:
                    session.add(PropertyRule(
                        property_id=None, pattern=pattern, rule_kind="exclusion", priority=0,
                    ))
                    rule_count += 1

        # 2b. merchant_rules (priority 10) — explicit patterns from config.
        for pattern, rule in CONFIG.get("merchant_rules", {}).items():
            if not isinstance(rule, dict):
                continue
            prop = prop_by_key.get(rule["property"])
            if prop is None:
                continue
            cat = RULE_CAT_MAP.get(rule.get("category"), None)
            req = rule.get("require_tx_category")
            priority = 60 if rule.get("category") == "moorage" else 10
            session.add(PropertyRule(
                property_id=prop.id, pattern=pattern, expense_category=cat,
                require_tx_category=req, rule_kind="expense", priority=priority,
                notes=rule.get("notes"),
            ))
            rule_count += 1

        # 2c. Per-property merchant lists (expense) + rental income.
        for key, c in props_cfg.items():
            prop = prop_by_key[key]
            for list_name, (cat, req, priority) in LIST_MAP.items():
                for pattern in c.get(list_name, []):
                    session.add(PropertyRule(
                        property_id=prop.id, pattern=pattern, expense_category=cat,
                        require_tx_category=req, rule_kind="expense", priority=priority,
                    ))
                    rule_count += 1
            for pattern in c.get("rental_income_merchants", []):
                session.add(PropertyRule(
                    property_id=prop.id, pattern=pattern, rule_kind="income", priority=20,
                ))
                rule_count += 1

        print(f"  Built {rule_count} rules")

        # 3. Synthetic MANUAL account for off-Monarch entries.
        result = await session.execute(
            select(Account).where(Account.name == MANUAL_ACCOUNT_NAME)
        )
        manual_acct = result.scalar_one_or_none()
        if manual_acct is None:
            manual_acct = Account(
                name=MANUAL_ACCOUNT_NAME,
                account_type=AccountType.OTHER,
                current_balance=0,
                is_asset=False,
                include_in_net_worth=False,
                source=DataSource.MANUAL,
            )
            session.add(manual_acct)
            await session.flush()
            print(f"  CREATE account '{MANUAL_ACCOUNT_NAME}'")

        # 4. Off-platform income from config -> manual income transactions.
        # A property may carry a "manual_income" list for income that never hit a
        # synced account (e.g. rent paid into an account outside Monarch).
        # Idempotent by (manual account, property, merchant).
        for key, c in props_cfg.items():
            prop = prop_by_key.get(key)
            if prop is None:
                continue
            for entry in c.get("manual_income", []):
                merchant = entry["merchant"]
                exists = await session.execute(
                    select(Transaction).where(
                        Transaction.account_id == manual_acct.id,
                        Transaction.property_id == prop.id,
                        Transaction.merchant == merchant,
                    )
                )
                if exists.scalar_one_or_none() is None:
                    category = entry.get("category", "Rental Income")
                    session.add(Transaction(
                        account_id=manual_acct.id,
                        external_id=None,
                        date=date.fromisoformat(entry["date"]),
                        amount=int(entry["amount_cents"]),
                        category=category,
                        merchant=merchant,
                        source=DataSource.MANUAL,
                        property_id=prop.id,
                        property_category=category,
                        property_source="manual",
                        notes=entry.get("notes"),
                    ))
                    print(f"  CREATE manual txn: {merchant}")

        await session.commit()

        # 5. Classify all existing transactions by the freshly seeded rules.
        counts = await PropertyPnLEngine(session).reclassify()
        await session.commit()
        print(f"  Reclassify: {counts}")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

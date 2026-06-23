"""Seed a complete demo financial life so a fresh install renders every page alive.

Creates the synthetic demo persona (the same one the test suite verifies): a
52-year-old who was just laid off and is bridging to penalty-free retirement
account access at 59½. Three properties — a Coastal Condo (primary residence,
mortgaged), a Mountain House (secondary home, under contract to sell), and a
River House (rented out) — plus retirement accounts, startup equity, severance
runway, and a SEPP/72(t) bridge plan.

What it seeds:
  - 17 accounts with FIRE-role enrichment (cash, 401(k)/IRAs, real estate,
    mortgages, private equity, vehicles)
  - ~2 years of weekly balance history per account + net worth history
  - 6 income sources (ended salary, severance, unemployment, three rentals)
  - 10 future cashflow events (severance lump, property sale, equity vests …)
  - The FIRE config for the persona: SEPP bridge starting month 12, a
    property_sales plan (sell the Mountain House in ~6 months, downsize out of
    the Coastal Condo at month 60), Social Security at 62

All dates are anchored to TODAY at seed time, so the story is always "just laid
off, severance ending soon, sale closing in ~6 months" — re-running the script
re-anchors the timeline. Demo rows are manual-source (external_id = NULL), so a
later real Monarch sync ignores them completely: try the app on demo data first,
connect Monarch when ready, then remove the demo with --remove.

Safety: refuses to run if Monarch-synced accounts exist (you have real data;
seeding a fake persona on top would only confuse things). Override with --force
(data rows only — an already-configured FIRE config is never overwritten unless
you also pass --with-config).

Idempotent: upserts by name, rebuilds demo balance history, recomputes net worth
snapshots.

Usage:
    cd backend && uv run python ../scripts/seed_demo.py            # seed
    cd backend && uv run python ../scripts/seed_demo.py --remove   # remove demo rows
"""

import argparse
import asyncio
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dateutil.relativedelta import relativedelta
from sqlalchemy import delete, select

from app.core.database import async_session_factory
from app.engines.net_worth import NetWorthEngine
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.cashflow_event import CashflowEvent
from app.models.enums import AccountType, DataSource, IncomeType
from app.models.fire_config import FireConfig
from app.models.income_source import IncomeSource
from app.models.net_worth_snapshot import NetWorthSnapshot

DEMO_MARKER = {"demo_seed": True}
HISTORY_WEEKS = 104  # ~2 years of weekly balance snapshots


# ---------------------------------------------------------------------------
# Persona — accounts (balances in cents; buckets match the projection engine's
# fire_role taxonomy: liquid / retirement / real-estate / illiquid / other)
# ---------------------------------------------------------------------------
# (name, account_type, institution, fire_role, balance_cents, is_asset,
#  history_start_factor, wiggle_amplitude)
#
# history_start_factor = balance 2 years ago as a fraction of today's balance
# (>1 = the asset has been depreciating). wiggle_amplitude adds a deterministic
# sine wobble so charts look like markets, not CAD drawings.
ACCOUNTS = [
    ("Everyday Checking",        AccountType.CHECKING,  "Harborview Bank",     "operating_account",        1_800_000,  True,  0.85, 0.06),
    ("High-Yield Savings",       AccountType.SAVINGS,   "Harborview Bank",     "cash_reserve",             5_800_000,  True,  0.60, 0.01),
    ("Crypto Portfolio",         AccountType.CRYPTO,    "Coinvault",           "speculative",              1_700_000,  True,  0.62, 0.10),
    ("Employer 401(k)",          AccountType.FOUR_OH_ONE_K, "Meridian Retirement", "retirement_core",     29_700_000,  True,  0.82, 0.02),
    ("Rollover IRA (bridge)",    AccountType.IRA,       "Cascade Brokerage",   "retirement_bridge",       40_200_000,  True,  0.82, 0.02),
    ("Roth IRA",                 AccountType.ROTH_IRA,  "Cascade Brokerage",   "retirement_supplemental", 16_500_000,  True,  0.82, 0.02),
    ("HSA",                      AccountType.HSA,       "Lakeshore Health",    "tax_free_reserve",           600_000,  True,  0.70, 0.02),
    ("Coastal Condo",            AccountType.REAL_ESTATE, None,                "primary_residence",       51_000_000,  True,  0.962, 0.004),
    ("Coastal Condo Mortgage",   AccountType.REAL_ESTATE, "Lender A",          "primary_mortgage",        32_500_000,  False, None, None),
    ("Mountain House",           AccountType.REAL_ESTATE, None,                "sell_candidate",          39_800_000,  True,  0.962, 0.004),
    ("Mountain House Mortgage",  AccountType.REAL_ESTATE, "Lender B",          "sell_with_property",      26_700_000,  False, None, None),
    ("River House",              AccountType.REAL_ESTATE, None,                "income_producing",        39_600_000,  True,  0.962, 0.004),
    ("Startup A Equity",         AccountType.PRIVATE,   None,                  "illiquid_private",         7_800_000,  True,  1.0,  0.0),
    ("Startup B Equity",         AccountType.PRIVATE,   None,                  "illiquid_private",         2_200_000,  True,  1.0,  0.0),
    ("Startup C Equity",         AccountType.PRIVATE,   None,                  "illiquid_private",         2_800_000,  True,  1.0,  0.0),
    ("Pickup Truck",             AccountType.VEHICLE,   None,                  "depreciating",             4_200_000,  True,  1.24, 0.0),
    ("Boat",                     AccountType.OTHER,     None,                  "depreciating",             2_300_000,  True,  1.13, 0.0),
]

# Mortgages amortize linearly back in time: balance N months ago was higher by
# N × monthly principal. (name → monthly principal paydown, cents)
MORTGAGE_MONTHLY_PRINCIPAL = {
    "Coastal Condo Mortgage": 134_000,   # $3,100 P&I @ ~6.5% on $325K
    "Mountain House Mortgage": 24_000,   # $1,800 P&I @ ~7% on $267K
}


# ---------------------------------------------------------------------------
# Persona — income sources (annual amounts in cents; end offsets in days from
# the seed anchor). The salary just ended — that's the story.
# ---------------------------------------------------------------------------
# (name, income_type, annual_amount_cents, end_offset_days or None)
INCOME_SOURCES = [
    ("Employer Salary (ended)",  IncomeType.SALARY, 25_000_000, -21),
    ("Employer Severance",       IncomeType.OTHER,   8_200_000,  16),
    ("State Unemployment",       IncomeType.OTHER,   1_440_000,  77),
    ("Coastal Condo Rental",     IncomeType.RENTAL,    410_000, None),
    ("Mountain House Rental",    IncomeType.RENTAL,    870_000,  77),
    ("River House Rental",       IncomeType.RENTAL,  3_960_000, None),
]


# ---------------------------------------------------------------------------
# Persona — cashflow events (amounts in cents; offsets from the seed anchor).
# "Mountain House Sale Proceeds" is deliberately BOTH an event and a
# property_sales entry: the Runway page consumes the event, while the wealth
# projection suppresses it (suppress_cashflow_match) because the generic sale
# path computes the proceeds itself. That's the supported pattern.
# ---------------------------------------------------------------------------
# (name, event_type, amount_cents, offset_days or ("months", n), probability,
#  is_recurring, recurrence, end_offset_days)
CASHFLOW_EVENTS = [
    ("Coastal Condo Special Assessment", "expense",    450_000, -13, 1.0,  True,  "monthly", 139),
    ("Boat Payment",                     "expense",    500_000,  14, 1.0,  False, None, None),
    ("Remaining Severance",              "income",   3_000_000,  16, 1.0,  False, None, None),
    ("Prior-Year Tax Refund",            "income",   4_000_000,  78, 0.9,  False, None, None),
    ("Mountain House Sale Proceeds",     "income",  10_400_000, 184, 0.85, False, None, None),
    ("Overseas Payout",                  "income",  11_400_000, 474, 0.5,  False, None, None),
    ("Auto loan payoff savings",         "income",      87_000, 443, 1.0,  True,  "monthly", None),
    ("Startup A vests (1.5x)",           "income",   7_800_000, ("months", 60), 0.7, False, None, None),
    ("Startup B vests (1.5x)",           "income",   2_200_000, ("months", 72), 0.6, False, None, None),
    ("Startup C vests (2x)",             "income",   4_500_000, ("months", 84), 0.5, False, None, None),
]


def build_demo_config_values(anchor: date) -> dict:
    """FIRE config for the demo persona, anchored to the seed date.

    Age ~52.75, retiring now, bridging to 59½ on severance + SEPP/72(t) + an
    overseas pension drawdown. Uses the generic property_sales mechanism (the
    documented path): sell the Mountain House in ~6 months, downsize out of the
    Coastal Condo at month 60, proceeds compound in a taxable brokerage pool.
    """
    dob = anchor.replace(day=1) - relativedelta(months=633)  # age 52y 9mo
    return dict(
        date_of_birth=dob,
        target_retirement_age=53,
        life_expectancy=90,
        fire_variant="regular",
        safe_withdrawal_rate=4.0,
        expected_annual_return=7.0,
        expected_inflation_rate=3.0,
        target_annual_spending=15_300_000,  # $153,000/yr = $12,750/mo (cents)
        social_security_monthly=465_000,  # $4,650/mo at full retirement age (cents)
        social_security_start_age=67,
        pension_monthly=None,
        pension_start_age=None,
        healthcare_monthly_cost=60_000,  # $600/mo pre-Medicare (cents)
        medicare_start_age=65,
        rmd_start_age=73,
        target_legacy=0,
        custom_assumptions={
            "demo_persona": True,  # sentinel: lets re-runs (and --remove) recognize this config
            "sepp_bridge": True,
            "bridge_end_age": 59.5,
            "penalty_free_age": 59.5,
            "rule_of_55_eligible": False,
            "rental_occupancy_rate": 1.0,
            # Occupancy haircut (when a scenario lowers the rate) applies only
            # to the income property's rental source
            "occupancy_source_match": ["river house"],
            "tax": {
                "filing_status": "single",
                "household_size": 1,
                "cost_basis_pct": 0.6,
                "state": "CO",
                "state_tax_rate": 4.4,
            },
            # SEPP/72(t): fixed draws from the Rollover IRA starting month 12
            "sepp": {
                "ira_a_balance": 402_000,
                "ira_b_balance": 165_000,
                "sepp_monthly": 2_100,
                "sepp_start_month": 12,
                "ira_growth_rate": 0.06,
            },
            # Overseas pension cash-out: $1,900/mo net starting month 12
            "rrsp": {
                "monthly_net": 1_900,
                "start_month": 12,
                "total_available": 205_000,
            },
            # Sale proceeds land in a taxable brokerage pool (6.5% real),
            # drawn before retirement accounts when cash runs thin
            "taxable_pool": {"starting_balance": 0, "return_rate": 0.065},
            # The documented property-sale mechanism (dollars, not cents)
            "property_sales": [
                {
                    "key": "mountain_house",
                    "re_bucket": "secondary",
                    "sale_month": 6,
                    "value": 398_000,
                    "cost_basis": 385_000,
                    "agent_fee_pct": 0.06,
                    "ltcg_rate": 0.15,
                    "state_tax_rate": 0.05,
                    "section_121_exclusion": 0,  # not the primary residence
                    "current_mortgage_balance": 267_000,
                    "mortgage_rate": 0.07,
                    "mortgage_pi": 1_800,
                    "monthly_cost": 2_400,
                    "in_base_burn": False,  # carry cost sits outside the spending target while held
                    "post_sale_rent": 0,
                    "monthly_income": 0,  # its rental source ends before the sale
                    "proceeds_to": "taxable",
                    # The projection owns this sale — ignore the planned
                    # "Mountain House Sale Proceeds" cashflow event (the Runway
                    # page still uses it)
                    "suppress_cashflow_match": "mountain house",
                },
                {
                    "key": "coastal_condo",
                    "re_bucket": "primary",
                    "sale_month": 60,
                    "value": 510_000,
                    "cost_basis": 510_000,
                    "agent_fee_pct": 0.06,
                    "ltcg_rate": 0.15,
                    "state_tax_rate": 0.0,
                    "section_121_exclusion": 250_000,  # single-filer §121
                    "current_mortgage_balance": 325_000,
                    "mortgage_rate": 0.065,
                    "mortgage_pi": 3_100,
                    "monthly_cost": 6_150,
                    "in_base_burn": True,  # all-in cost is inside the spending target
                    "post_sale_rent": 2_500,
                    "monthly_income": 340,  # condo rental that ends at sale
                    "proceeds_to": "taxable",
                },
            ],
            # Projection assumptions (all REAL, after-inflation rates)
            "projection": {
                "surplus_investment_rate": 0.04,
                "cash_reserve_months": 12,
                "cash_savings_rate_early": 0.01,
                "cash_savings_rate_late": 0.0,
                "cash_savings_cutover_month": 60,
                "re_appreciation_rate": 0.01,
                "primary_property_purchase_price": 510_000,
                "primary_property_agent_fee_pct": 0.06,
                "primary_property_mortgage_pi": 3_100,
                "primary_property_cost_basis": 510_000,
                "primary_property_ltcg_rate": 0.15,
                "ss_early_reduction": 0.70,
                "ss_claim_age": 62,
                "spending_phase_slow": 0.85,
                "spending_phase_floor": 0.75,
                "spending_phase_slow_age": 70,
                "spending_phase_floor_age": 80,
                "ira_b_draw_threshold_months": 12,
            },
        },
    )


# ---------------------------------------------------------------------------
# Balance history generation (deterministic — no randomness, same input same DB)
# ---------------------------------------------------------------------------

def _history_balances(name: str, end_balance: int, start_factor: float,
                      amplitude: float, weeks: int) -> list[int]:
    """Weekly balances from `weeks` ago to today, geometric drift + sine wobble."""
    phase = sum(ord(c) for c in name) % 7
    out = []
    for i in range(weeks + 1):
        t = i / weeks
        drift = end_balance * (start_factor ** (1 - t))
        wobble = 1 + amplitude * math.sin(0.9 * i + phase)
        out.append(int(drift * wobble))
    out[-1] = end_balance  # today's snapshot must equal the live balance
    return out


def _mortgage_balances(end_balance: int, monthly_principal: int, weeks: int) -> list[int]:
    """Mortgage balance declines ~linearly; it was higher in the past."""
    weekly_principal = monthly_principal * 12 / 52
    return [int(end_balance + weekly_principal * (weeks - i)) for i in range(weeks + 1)]


# ---------------------------------------------------------------------------
# Seed / remove
# ---------------------------------------------------------------------------

async def _demo_rows(session, model):
    result = await session.execute(
        select(model).where(model.custom_data["demo_seed"].as_boolean() == True)  # noqa: E712
    )
    return result.scalars().all()


async def seed(force: bool, with_config: bool) -> None:
    anchor = date.today()

    async with async_session_factory() as session:
        # --- Guard: never seed a fake persona on top of real data ---
        result = await session.execute(
            select(Account).where(Account.source == DataSource.MONARCH).limit(1)
        )
        if result.scalar_one_or_none() is not None and not force:
            print("Monarch-synced accounts found — this database holds REAL data.")
            print("Seeding the demo persona on top would only confuse things.")
            print("(Use --force to seed demo data rows anyway, e.g. on a throwaway DB.)")
            sys.exit(1)

        # --- Accounts (upsert by name) ---
        names = [a[0] for a in ACCOUNTS]
        result = await session.execute(select(Account).where(Account.name.in_(names)))
        existing = {a.name: a for a in result.scalars().all()}

        accounts_by_name: dict[str, Account] = {}
        created = updated = 0
        for name, acct_type, institution, role, balance, is_asset, _, _ in ACCOUNTS:
            acct = existing.get(name)
            if acct is None:
                acct = Account(name=name, account_type=acct_type, source=DataSource.MANUAL)
                session.add(acct)
                created += 1
            else:
                updated += 1
            acct.institution = institution
            acct.current_balance = balance
            acct.is_asset = is_asset
            acct.include_in_net_worth = True
            acct.fire_role = role
            acct.custom_data = {**(acct.custom_data or {}), **DEMO_MARKER}
            accounts_by_name[name] = acct
        await session.flush()  # assign ids
        print(f"  Accounts: {created} created, {updated} updated")

        # --- Balance history (rebuild: delete + insert, dates re-anchor to today) ---
        demo_ids = [a.id for a in accounts_by_name.values()]
        await session.execute(
            delete(BalanceSnapshot).where(BalanceSnapshot.account_id.in_(demo_ids))
        )
        snap_count = 0
        for name, _, _, _, balance, _, start_factor, amplitude in ACCOUNTS:
            if name in MORTGAGE_MONTHLY_PRINCIPAL:
                balances = _mortgage_balances(
                    balance, MORTGAGE_MONTHLY_PRINCIPAL[name], HISTORY_WEEKS
                )
            else:
                balances = _history_balances(
                    name, balance, start_factor, amplitude, HISTORY_WEEKS
                )
            acct_id = accounts_by_name[name].id
            for i, bal in enumerate(balances):
                session.add(BalanceSnapshot(
                    account_id=acct_id,
                    date=anchor - timedelta(weeks=HISTORY_WEEKS - i),
                    balance=bal,
                    source=DataSource.MANUAL,
                ))
                snap_count += 1
        await session.flush()
        print(f"  Balance snapshots: {snap_count} ({HISTORY_WEEKS} weeks × {len(ACCOUNTS)} accounts)")

        # --- Income sources (upsert by name) ---
        src_names = [s[0] for s in INCOME_SOURCES]
        result = await session.execute(
            select(IncomeSource).where(IncomeSource.name.in_(src_names))
        )
        existing_src = {s.name: s for s in result.scalars().all()}
        for name, itype, annual, end_offset in INCOME_SOURCES:
            src = existing_src.get(name)
            if src is None:
                src = IncomeSource(name=name, income_type=itype, annual_amount=annual)
                session.add(src)
            src.income_type = itype
            src.annual_amount = annual
            src.frequency = "monthly"
            src.end_date = anchor + timedelta(days=end_offset) if end_offset is not None else None
            src.is_active = True
            src.is_taxable = True
            src.custom_data = {**(src.custom_data or {}), **DEMO_MARKER}
        print(f"  Income sources: {len(INCOME_SOURCES)}")

        # --- Cashflow events (upsert by name; drop stale demo events) ---
        ev_names = [e[0] for e in CASHFLOW_EVENTS]
        for stale in await _demo_rows(session, CashflowEvent):
            if stale.name not in ev_names:
                await session.delete(stale)
        result = await session.execute(
            select(CashflowEvent).where(CashflowEvent.name.in_(ev_names))
        )
        existing_ev = {e.name: e for e in result.scalars().all()}
        for name, etype, amount, offset, prob, recurring, recurrence, end_offset in CASHFLOW_EVENTS:
            if isinstance(offset, tuple):
                ev_date = anchor + relativedelta(months=offset[1])
            else:
                ev_date = anchor + timedelta(days=offset)
            ev = existing_ev.get(name)
            if ev is None:
                ev = CashflowEvent(name=name, event_type=etype, amount_cents=amount, date=ev_date)
                session.add(ev)
            ev.event_type = etype
            ev.amount_cents = amount
            ev.date = ev_date
            ev.probability = prob
            ev.is_recurring = recurring
            ev.recurrence = recurrence
            ev.end_date = anchor + timedelta(days=end_offset) if end_offset is not None else None
            ev.status = "planned"
            ev.custom_data = {**(ev.custom_data or {}), **DEMO_MARKER}
        print(f"  Cashflow events: {len(CASHFLOW_EVENTS)}")

        # --- FIRE config ---
        result = await session.execute(select(FireConfig).limit(1))
        config = result.scalar_one_or_none()
        is_starter = (
            config is not None
            and config.date_of_birth == date(1976, 1, 1)
            and config.target_annual_spending == 12_000_000
        )  # fingerprint of scripts/seed_config.py's untouched starter persona
        is_demo = bool(config and (config.custom_assumptions or {}).get("demo_persona"))
        if config is None or config.date_of_birth is None or is_starter or is_demo or with_config:
            if config is None:
                config = FireConfig()
                session.add(config)
            for field, value in build_demo_config_values(anchor).items():
                setattr(config, field, value)
            print("  FIRE config: demo persona written")
        else:
            print("  FIRE config: already customized — left untouched"
                  " (pass --with-config to overwrite with the demo persona)")

        # --- Net worth history (recompute from balance snapshots) ---
        if not force:
            # Fresh-install path: stale aggregate rows from a previous anchor
            # would linger (upsert is by date), so rebuild from scratch.
            await session.execute(delete(NetWorthSnapshot))
        nw_count = await NetWorthEngine(session).backfill_snapshots()
        print(f"  Net worth snapshots: {nw_count} recomputed")

        await session.commit()

    print(f"""
Done. The demo persona is live (anchored to {anchor}).

  Open the app: Dashboard, Retirement, Runway, and Config are all populated.
  Optional: seed example what-if scenarios too →  uv run python ../scripts/seed_scenarios.py
  Going live with your own data later? Connect Monarch (see docs/MONARCH_SETUP.md),
  then remove the demo rows:  uv run python ../scripts/seed_demo.py --remove
""")


async def seed_if_empty() -> None:
    """First-run auto-seed used by the migrate step: seed the demo persona ONLY when the
    database has no accounts and SEED_DEMO is not 'false'. No-op otherwise. Never raises —
    a seeding hiccup must not block the stack from starting."""
    if os.environ.get("SEED_DEMO", "true").strip().lower() == "false":
        print("SEED_DEMO=false — skipping first-run demo auto-seed.")
        return
    try:
        async with async_session_factory() as session:
            existing = await session.execute(select(Account).limit(1))
            if existing.scalar_one_or_none() is not None:
                print("Database already has accounts — skipping demo auto-seed.")
                return
        await seed(force=False, with_config=False)
    except Exception as exc:  # noqa: BLE001 — must never block stack startup
        print(f"Demo auto-seed skipped (non-fatal): {exc}")


async def remove() -> None:
    from app.ingestion.demo_data import clear_demo_data

    async with async_session_factory() as session:
        summary = await clear_demo_data(session)
        print(f"  Accounts removed: {summary['accounts']} (and their balance history)")
        print(f"  Income sources removed: {summary['income_sources']}")
        print(f"  Cashflow events removed: {summary['cashflow_events']}")
        if summary["net_worth_snapshots"]:
            print(f"  Net worth snapshots: {summary['net_worth_snapshots']} recomputed from remaining data")
        else:
            print("  Net worth snapshots: cleared (no balance history left)")

        result = await session.execute(select(FireConfig).limit(1))
        config = result.scalar_one_or_none()
        if config is not None and (config.custom_assumptions or {}).get("demo_persona"):
            print("\n  NOTE: the FIRE config still holds the demo persona's plan.")
            print("  Replace it with your own numbers under Settings -> Plan (or run seed_config.py")
            print("  after clearing it) — projections reflect the demo until you do.")

        await session.commit()
    print("\nDemo data removed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remove", action="store_true", help="delete previously seeded demo rows")
    parser.add_argument("--force", action="store_true",
                        help="seed data rows even if Monarch accounts exist (demo/testing only)")
    parser.add_argument("--with-config", action="store_true",
                        help="overwrite an already-customized FIRE config with the demo persona")
    parser.add_argument("--if-empty", action="store_true",
                        help="first-run auto-seed: seed only if the DB has no accounts and "
                             "SEED_DEMO != false; no-op otherwise (used by the migrate step)")
    args = parser.parse_args()

    if args.remove:
        asyncio.run(remove())
    elif args.if_empty:
        asyncio.run(seed_if_empty())
    else:
        asyncio.run(seed(force=args.force, with_config=args.with_config))

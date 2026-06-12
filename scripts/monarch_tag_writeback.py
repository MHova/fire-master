"""Mirror FIREMaster property classifications into Monarch as TAGS.

Property is an axis orthogonal to category, so we represent "which property" as a Monarch
tag (multi-valued, sits alongside the category) rather than a category (single-valued —
would force a combinatorial "Property-A Utilities / Property-B Utilities" mess).

This BOOTSTRAPS the back-catalog and creates the tags. Going forward Monarch is step one:
new transactions get tagged in Monarch directly. Our P&L is independent (it keys off our
own property_id), so this writeback is purely for your Monarch views.

SAFE BY DEFAULT:
  - Dry run unless --live. Dry run only READS (your tags + the window's transactions) and
    prints the exact plan.
  - Tags MERGE: each transaction's current Monarch tags are read and the property tag is
    unioned in, so we never clobber existing tags. (No reconcile/removal — by design.)
  - --undo removes just the property tag again (full reversibility).
  - Writes are throttled; a single failed transaction is logged and skipped, not fatal.

Usage (from backend/):
  uv run python ../scripts/monarch_tag_writeback.py                       # dry run, ALL properties, all history
  uv run python ../scripts/monarch_tag_writeback.py --property "Rental Condo" --live   # stage one property
  uv run python ../scripts/monarch_tag_writeback.py --live                # apply all
  uv run python ../scripts/monarch_tag_writeback.py --undo --live         # remove the property tags again
"""

import argparse
import asyncio
import os
import sys
from datetime import date

from dotenv import load_dotenv
from monarchmoney import MonarchMoney
from sqlalchemy import select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import async_session_factory  # noqa: E402
from app.models.property import Property  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402

DEFAULT_START = "2018-01-01"
DEFAULT_END = "2026-12-31"
PAGE = 1000           # transactions per read page
WRITE_SLEEP = 0.25    # throttle between writes (gentle on the unofficial API)
READ_SLEEP = 0.2      # throttle between read pages


async def load_targets(property_filter: str, start: str, end: str):
    """[(Property, [rows])] for all active properties (or one named), classified in window."""
    async with async_session_factory() as db:
        pq = select(Property).where(Property.is_active.is_(True))
        if property_filter and property_filter.lower() != "all":
            pq = pq.where(Property.name == property_filter)
        props = (await db.execute(pq.order_by(Property.name))).scalars().all()
        if not props:
            print(f"!! No matching property for {property_filter!r}", file=sys.stderr)
            sys.exit(1)
        out = []
        for p in props:
            rows = (
                await db.execute(
                    select(
                        Transaction.external_id,
                        Transaction.date,
                        Transaction.merchant,
                        Transaction.amount,
                        Transaction.property_category,
                    )
                    .where(
                        Transaction.property_id == p.id,
                        Transaction.date >= date.fromisoformat(start),
                        Transaction.date <= date.fromisoformat(end),
                        Transaction.external_id.isnot(None),
                    )
                    .order_by(Transaction.date)
                )
            ).all()
            out.append((p, rows))
        return out


def _tag_index(resp) -> dict:
    items = resp.get("householdTransactionTags") or resp.get("tags") or []
    return {t.get("name"): t.get("id") for t in items}


async def read_current_tags(mm, start: str, end: str) -> dict:
    """external_id -> [current tag_ids], paginated across the whole window (read-only)."""
    current: dict[str, list] = {}
    offset = 0
    for _ in range(100):  # safety cap = 100k txns
        resp = await mm.get_transactions(limit=PAGE, offset=offset, start_date=start, end_date=end)
        results = resp.get("allTransactions", {}).get("results", []) or resp.get("results", [])
        for tx in results:
            current[tx["id"]] = [t["id"] for t in (tx.get("tags") or [])]
        print(f"  …read {len(current)} transactions")
        if len(results) < PAGE:
            break
        offset += PAGE
        await asyncio.sleep(READ_SLEEP)
    return current


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="actually write to Monarch")
    ap.add_argument("--undo", action="store_true", help="remove the property tag instead of adding")
    ap.add_argument("--property", default="all", help='property name or "all"')
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    args = ap.parse_args()

    load_dotenv()
    mode = ("UNDO" if args.undo else "APPLY") + (" [LIVE]" if args.live else " [DRY RUN]")
    print(f"=== Monarch property-tag writeback — {mode} ===")
    print(f"Scope: {args.property}   Window: {args.start} .. {args.end}\n")

    targets = await load_targets(args.property, args.start, args.end)
    n_rows = sum(len(rows) for _, rows in targets)
    if not n_rows:
        print("No classified transactions with a Monarch id in scope. Nothing to do.")
        return

    mm = MonarchMoney()
    mm.load_session(os.environ.get("MONARCH_SESSION_FILE", ".monarch_session"))

    name2id = _tag_index(await mm.get_transaction_tags())
    print(f"Existing Monarch tags: {list(name2id) or '(none)'}\n")

    print(f"Reading current tags across the window ({n_rows} target txns)…")
    current = await read_current_tags(mm, args.start, args.end)
    print()

    # --- LIVE: ensure each property's tag exists up front ---
    if args.live and not args.undo:
        for p, rows in targets:
            if rows and p.name not in name2id:
                created = await mm.create_transaction_tag(name=p.name, color=p.color or "#00d4aa")
                name2id[p.name] = (created.get("createTransactionTag", {}) or {}).get("tag", {}).get("id")
                print(f"Created tag {p.name!r} -> {name2id[p.name]}")
        print()

    grand_add = grand_already = grand_missing_tag = 0
    failures: list[str] = []

    for p, rows in targets:
        tag_id = name2id.get(p.name)
        add = already = 0
        for r in rows:
            cur = set(current.get(r.external_id, []))
            if args.undo:
                changed = bool(tag_id) and tag_id in cur
            else:
                changed = (tag_id is None) or (tag_id not in cur)
            if args.undo and not changed:
                continue
            if not args.undo and (tag_id is not None) and not changed:
                already += 1
                continue
            add += 1

            if args.live:
                if tag_id is None:
                    grand_missing_tag += 1
                    continue
                new = (cur - {tag_id}) if args.undo else (cur | {tag_id})
                try:
                    await mm.set_transaction_tags(transaction_id=r.external_id, tag_ids=list(new))
                    await asyncio.sleep(WRITE_SLEEP)
                except Exception as e:  # isolate per-txn failures
                    failures.append(f"{p.name} {r.date} {r.merchant}: {e}")

        verb = "to untag" if args.undo else "to tag"
        extra = f", {already} already tagged" if (not args.undo and already) else ""
        tagstate = "exists" if tag_id else ("WILL CREATE" if args.live else "missing (dry run)")
        print(f"  {p.name:<14} tag:{tagstate:<22} {add} {verb}{extra}  ({len(rows)} classified)")
        grand_add += add
        grand_already += already

    print("\n" + "-" * 60)
    action = "untagged" if args.undo else "tagged"
    if args.live:
        ok = grand_add - len(failures) - grand_missing_tag
        print(f"LIVE: {ok} transactions {action}.")
        if grand_already:
            print(f"      {grand_already} already correct (skipped).")
        if failures:
            print(f"      {len(failures)} FAILED:")
            for f in failures[:20]:
                print(f"        - {f}")
        print("\nOpen Monarch, filter by a property tag, and verify.")
    else:
        print(f"DRY RUN — nothing written. {grand_add} writes planned"
              f"{f', {grand_already} already tagged' if grand_already else ''}.")
        print("Re-run with --live (optionally --property \"Rental Condo\" to stage one) to apply.")


if __name__ == "__main__":
    asyncio.run(main())

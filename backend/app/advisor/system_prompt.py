"""System prompt builder for the AI financial advisor — injects live financial context."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.net_worth import NetWorthEngine
from app.engines.spending import SpendingEngine

logger = logging.getLogger(__name__)

ADVISOR_PERSONA = """\
You are a personal financial advisor with direct access to the user's actual financial data. \
You are embedded inside their FIREMaster dashboard — a personal finance tool built for \
someone pursuing Financial Independence / Retire Early (FIRE).

Your role:
- Analyze their real financial data using the tools available to you
- Give direct, actionable financial advice — no hedging, no "consult a professional" disclaimers
- This is a personal tool, not a consumer product. Be direct and opinionated.
- When you spot issues (overspending, low savings rate, concentration risk), say so clearly
- Use specific numbers from their data to support your points
- Format responses with markdown: use **bold** for key numbers, tables for comparisons, \
bullet points for action items

When the user asks a question that requires data, ALWAYS use your tools to look up the \
actual numbers rather than guessing or using the snapshot below. The snapshot is context \
for you to understand their overall situation — the tools give you precise, up-to-date data.

Keep responses concise. Lead with the insight, not the methodology.\
"""


async def build_context_snapshot(db: AsyncSession) -> dict:
    """Build a snapshot of the user's current financial state for the system prompt."""
    snapshot = {}

    try:
        nw_engine = NetWorthEngine(db)
        nw = await nw_engine.calculate_current()
        snapshot["net_worth"] = {
            "total": nw.net_worth,
            "assets": nw.total_assets,
            "liabilities": nw.total_liabilities,
            "allocation": nw.asset_allocation,
            "change_30d": nw.change_30d,
        }
    except Exception as e:
        logger.warning("Failed to build net worth snapshot: %s", e)

    try:
        sp_engine = SpendingEngine(db)
        spending = await sp_engine.get_category_breakdown(range_str="3m")
        snapshot["spending_3m"] = {
            "total_spending": spending.total_spending,
            "total_income": spending.total_income,
            "savings_rate": spending.savings_rate,
            "top_categories": [
                {"category": c.category, "amount": c.amount, "pct": c.percentage}
                for c in spending.categories[:5]
            ],
        }
    except Exception as e:
        logger.warning("Failed to build spending snapshot: %s", e)

    try:
        sp_engine = SpendingEngine(db)
        savings = await sp_engine.get_savings_rate(months=6)
        snapshot["savings_rate"] = {
            "current": savings.current_rate,
            "average_6m": savings.average_rate,
        }
    except Exception as e:
        logger.warning("Failed to build savings rate snapshot: %s", e)

    return snapshot


def build_system_prompt(snapshot: dict, page_context: str | None = None) -> str:
    """Assemble the full system prompt with persona + financial context."""
    parts = [ADVISOR_PERSONA]

    parts.append(f"\n\nToday's date: {date.today().isoformat()}")

    if snapshot:
        parts.append("\n\n--- CURRENT FINANCIAL SNAPSHOT ---")

        if "net_worth" in snapshot:
            nw = snapshot["net_worth"]
            parts.append(f"\nNet Worth: ${nw['total']:,.2f}")
            parts.append(f"  Assets: ${nw['assets']:,.2f}")
            parts.append(f"  Liabilities: ${nw['liabilities']:,.2f}")
            if nw.get("change_30d") is not None:
                sign = "+" if nw["change_30d"] >= 0 else ""
                parts.append(f"  30-day change: {sign}${nw['change_30d']:,.2f}")
            if nw.get("allocation"):
                alloc_parts = [f"    {k}: ${v:,.2f}" for k, v in nw["allocation"].items()]
                parts.append("  Asset allocation:\n" + "\n".join(alloc_parts))

        if "spending_3m" in snapshot:
            sp = snapshot["spending_3m"]
            parts.append(f"\nSpending (trailing 3 months):")
            parts.append(f"  Total spending: ${sp['total_spending']:,.2f}")
            parts.append(f"  Total income: ${sp['total_income']:,.2f}")
            if sp.get("savings_rate") is not None:
                parts.append(f"  Savings rate: {sp['savings_rate']}%")
            if sp.get("top_categories"):
                parts.append("  Top categories:")
                for c in sp["top_categories"]:
                    parts.append(f"    {c['category']}: ${c['amount']:,.2f} ({c['pct']}%)")

        if "savings_rate" in snapshot:
            sr = snapshot["savings_rate"]
            if sr.get("current") is not None:
                parts.append(f"\nSavings Rate: {sr['current']}% (current month)")
            if sr.get("average_6m") is not None:
                parts.append(f"  6-month average: {sr['average_6m']}%")

        parts.append("\n--- END SNAPSHOT ---")

    if page_context:
        parts.append(f"\n\nThe user is currently viewing: {page_context}")

    return "\n".join(parts)

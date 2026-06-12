"""Generate the Expense Scrub HTML report from transaction data.

Usage: cd backend && uv run python ../scripts/report_expense_scrub.py [YEAR]
Output: reports/expense-scrub-{YEAR}.html
"""

import asyncio
import sys
import os
from datetime import date
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.database import async_session_factory
from app.models.transaction import Transaction
from app.models.category_mapping import CategoryMapping
from sqlalchemy import select, func, extract, or_, and_


# ---------------------------------------------------------------------------
#  Classification overrides — edit these to reclassify categories
# ---------------------------------------------------------------------------
FIXED = {
    "Mortgage & Rent", "Auto Payment", "Groceries",
    "Insurance", "Utilities", "Taxes",
    "Mobile Phone", "Internet & Cable", "Medical", "Dentist",
}

SEMI = {
    "L Support", "Child Support",
    "Home Improvement", "Gas & Fuel", "Taxi & Ride Shares",
    "Parking & Tolls", "Education", "Business Services",
    "Home Supplies", "Miscellaneous", "Financial Fees",
    "Fees & Charges", "Public Transportation",
}

# Everything else is DISCRETIONARY


def classify(cat: str) -> str:
    if cat in FIXED:
        return "fixed"
    if cat in SEMI:
        return "semi"
    return "cut"


BADGE_MAP = {
    "fixed": ("Fixed", "badge-fixed"),
    "semi": ("Semi", "badge-semi"),
    "cut": ("Cut", "badge-cut"),
}

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year

# Net refunds (returns, credits) against expenses — except tax refunds,
# which aren't a reduction in spending.
TAX_CATEGORIES = {"Taxes"}

# Include: all expenses (amount < 0) OR non-tax refunds (amount > 0)
_expense_or_nontax_refund = or_(
    Transaction.amount < 0,
    and_(Transaction.amount > 0, CategoryMapping.normalized_category.notin_(TAX_CATEGORIES)),
)


async def fetch_data():
    async with async_session_factory() as db:
        # Category breakdown
        result = await db.execute(
            select(
                CategoryMapping.normalized_category,
                CategoryMapping.parent_category,
                CategoryMapping.is_discretionary,
                func.sum(-Transaction.amount).label("total_cents"),
                func.count().label("tx_count"),
            )
            .join(CategoryMapping, Transaction.category == CategoryMapping.raw_category)
            .where(
                Transaction.date >= date(YEAR, 1, 1),
                Transaction.date <= date(YEAR, 12, 31),
                CategoryMapping.is_income == False,
                CategoryMapping.is_transfer == False,
                Transaction.hide_from_reports == False,
                _expense_or_nontax_refund,
            )
            .group_by(
                CategoryMapping.normalized_category,
                CategoryMapping.parent_category,
                CategoryMapping.is_discretionary,
            )
            .order_by(func.sum(-Transaction.amount).desc())
        )
        categories = [
            {
                "name": r.normalized_category,
                "parent": r.parent_category,
                "db_discretionary": r.is_discretionary,
                "cents": int(r.total_cents),
                "txns": r.tx_count,
                "classification": classify(r.normalized_category),
            }
            for r in result.all()
        ]

        # Monthly totals
        monthly = []
        for year in [2024, YEAR]:
            result = await db.execute(
                select(
                    extract("month", Transaction.date).label("month_num"),
                    func.sum(-Transaction.amount).label("total_cents"),
                )
                .join(CategoryMapping, Transaction.category == CategoryMapping.raw_category)
                .where(
                    Transaction.date >= date(year, 1, 1),
                    Transaction.date <= date(year, 12, 31),
                    CategoryMapping.is_income == False,
                    CategoryMapping.is_transfer == False,
                    Transaction.hide_from_reports == False,
                    _expense_or_nontax_refund,
                )
                .group_by(extract("month", Transaction.date))
                .order_by(extract("month", Transaction.date))
            )
            for r in result.all():
                monthly.append({
                    "year": year,
                    "month": int(r.month_num),
                    "cents": int(r.total_cents),
                })

        # Parent category summary
        result = await db.execute(
            select(
                CategoryMapping.parent_category,
                func.sum(-Transaction.amount).label("total_cents"),
                func.count().label("tx_count"),
            )
            .join(CategoryMapping, Transaction.category == CategoryMapping.raw_category)
            .where(
                Transaction.date >= date(YEAR, 1, 1),
                Transaction.date <= date(YEAR, 12, 31),
                CategoryMapping.is_income == False,
                CategoryMapping.is_transfer == False,
                Transaction.hide_from_reports == False,
                _expense_or_nontax_refund,
            )
            .group_by(CategoryMapping.parent_category)
            .order_by(func.sum(-Transaction.amount).desc())
        )
        parents = [
            {"name": r.parent_category, "cents": int(r.total_cents), "txns": r.tx_count}
            for r in result.all()
        ]

    return categories, monthly, parents


def fmt(cents: int) -> str:
    """Format cents as dollar string."""
    return f"${cents / 100:,.0f}"


def fmt_k(cents: int) -> str:
    """Format cents as compact dollar string."""
    v = cents / 100
    if abs(v) >= 1000:
        return f"${v/1000:.1f}K"
    return f"${v:,.0f}"


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def generate_html(categories, monthly, parents):
    total_cents = sum(c["cents"] for c in categories)
    fixed_cents = sum(c["cents"] for c in categories if c["classification"] == "fixed")
    semi_cents = sum(c["cents"] for c in categories if c["classification"] == "semi")
    cut_cents = sum(c["cents"] for c in categories if c["classification"] == "cut")

    # Monthly bars for the target year
    year_monthly = [m for m in monthly if m["year"] == YEAR]
    num_months = len(year_monthly) or 12  # actual months with data
    max_monthly = max(m["cents"] for m in year_monthly) if year_monthly else 1

    # Build monthly bars HTML
    monthly_bars = ""
    for m in year_monthly:
        height = int(m["cents"] / max_monthly * 200)
        color = "#00d4aa" if m["cents"] / 100 < 17000 else ("#ff4d6acc" if m["cents"] / 100 > 25000 else "#ff4d6a88")
        monthly_bars += f"""
    <div class="month-bar">
      <div class="month-bar-fill" style="height: {height}px; background: linear-gradient(to top, {color}, {color});"></div>
      <div class="month-value">{fmt_k(m['cents'])}</div>
      <div class="month-label">{MONTH_NAMES[m['month']-1]}</div>
    </div>"""

    # Spike detection
    spike_month = max(year_monthly, key=lambda m: m["cents"])
    spike_html = ""
    if spike_month["cents"] / 100 > 25000:
        spike_html = f"""
  <div class="callout" style="margin-top: 20px;">
    <h4>{MONTH_NAMES[spike_month['month']-1]} spike: {fmt(spike_month['cents'])}</h4>
    <p>Investigate — this is well above average. Could be a one-time large purchase, insurance renewal, or property-related payment.</p>
  </div>"""

    # Parent category table rows
    parent_rows = ""
    for p in parents:
        pct = p["cents"] / total_cents * 100 if total_cents else 0
        bar_width = pct / (parents[0]["cents"] / total_cents * 100) * 100 if parents else 0
        color = "#ff4d6a" if pct > 15 else ("#ffc04d" if pct > 5 else "#4d8eff")
        parent_rows += f"""
      <tr>
        <td class="cat-name">{p['name']}</td>
        <td class="mono" style="color:{color}">{fmt(p['cents'])}</td>
        <td class="mono">{fmt(p['cents'] // num_months)}</td>
        <td class="mono">{pct:.1f}%</td>
        <td><div class="bar-container"><div class="bar-fill" style="width: {bar_width:.0f}%; background: linear-gradient(90deg, {color}, {color}88);"></div></div></td>
        <td class="mono" style="color: #8888a0;">{p['txns']}</td>
      </tr>"""

    # Detailed category rows grouped by classification
    detail_rows = ""
    for cls, label, color in [
        ("fixed", "FIXED / NON-DISCRETIONARY", "#ff4d6a"),
        ("semi", "SEMI-DISCRETIONARY", "#ffc04d"),
        ("cut", "FULLY DISCRETIONARY — CUT TARGET", "#00d4aa"),
    ]:
        group = [c for c in categories if c["classification"] == cls]
        group_total = sum(c["cents"] for c in group)
        detail_rows += f"""
      <tr class="parent-row"><td colspan="6" class="cat-name" style="color:{color}; padding-top:16px;">
        {label} — {fmt(group_total)}/yr ({fmt(group_total // num_months)}/mo)
      </td></tr>"""
        for c in group:
            badge_text, badge_cls = BADGE_MAP[cls]
            detail_rows += f"""
      <tr>
        <td>{c['name']}</td>
        <td style="color:#8888a0">{c['parent']}</td>
        <td class="mono" style="color:{color}">{fmt(c['cents'])}</td>
        <td class="mono">{fmt(c['cents'] // num_months)}</td>
        <td><span class="badge {badge_cls}">{badge_text}</span></td>
        <td class="mono" style="color:#8888a0">{c['txns']} txns</td>
      </tr>"""

    # Survival mode calculation
    survival_fixed = fixed_cents // num_months // 100
    survival_semi = semi_cents // num_months // 100 // 2  # cut 50%
    survival_disc = 500  # $500/mo floor
    survival_total = survival_fixed + survival_semi + survival_disc
    savings_vs_current = total_cents // num_months // 100 - survival_total

    # Top 5 cuts
    cuts = sorted([c for c in categories if c["classification"] == "cut"], key=lambda c: -c["cents"])[:5]

    top5_rows = ""
    top5_savings = 0
    for c in cuts:
        target = 600000 if "Restaurant" in c["name"] else (120000 if "Entertainment" in c["name"] or "Sports" in c["name"] else 0)
        saving = c["cents"] - target
        top5_savings += saving
        top5_rows += f"""
        <tr>
          <td>{c['name']}</td>
          <td class="mono">{fmt(c['cents'])}</td>
          <td class="mono">{fmt(target)}</td>
          <td class="mono green">{fmt(saving)}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FIRE Master — Expense Scrub {YEAR}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0a0a0f; color: #e8e8f0; font-family: 'Inter', sans-serif; padding: 40px; min-height: 100vh; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 8px; }}
  .subtitle {{ color: #8888a0; font-size: 14px; margin-bottom: 32px; }}
  .hero-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px; }}
  .stat-card {{ background: #151520; border: 1px solid rgba(42,42,62,0.5); border-radius: 8px; padding: 16px; }}
  .stat-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; color: #8888a0; margin-bottom: 6px; }}
  .stat-value {{ font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; }}
  .stat-sub {{ font-size: 11px; color: #8888a0; margin-top: 4px; }}
  .green {{ color: #00d4aa; }} .red {{ color: #ff4d6a; }} .blue {{ color: #4d8eff; }} .yellow {{ color: #ffc04d; }}
  .section {{ background: #151520; border: 1px solid rgba(42,42,62,0.5); border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
  .section-title {{ font-size: 14px; font-weight: 600; color: #8888a0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #8888a0; padding: 8px 12px; border-bottom: 2px solid rgba(42,42,62,0.5); font-weight: 500; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid rgba(42,42,62,0.25); vertical-align: middle; }}
  tr:hover {{ background: rgba(255,255,255,0.02); }}
  .mono {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }}
  .badge-fixed {{ background: rgba(255,77,106,0.12); color: #ff4d6a; }}
  .badge-semi {{ background: rgba(255,192,77,0.12); color: #ffc04d; }}
  .badge-cut {{ background: rgba(0,212,170,0.12); color: #00d4aa; }}
  .bar-container {{ height: 20px; background: rgba(42,42,62,0.3); border-radius: 4px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; }}
  .summary-row {{ background: rgba(0,212,170,0.04); border-top: 2px solid rgba(42,42,62,0.5); }}
  .summary-row td {{ font-weight: 700; padding-top: 12px; padding-bottom: 12px; }}
  .monthly-grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 8px; margin-top: 16px; }}
  .month-bar {{ display: flex; flex-direction: column; align-items: center; gap: 4px; }}
  .month-bar-fill {{ width: 100%; border-radius: 4px 4px 0 0; min-height: 4px; }}
  .month-label {{ font-size: 10px; color: #8888a0; }}
  .month-value {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .callout {{ background: rgba(255,77,106,0.06); border-left: 3px solid #ff4d6a; padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 20px 0; }}
  .callout-green {{ background: rgba(0,212,170,0.06); border-left-color: #00d4aa; }}
  .callout h4 {{ font-size: 13px; font-weight: 600; margin-bottom: 6px; }}
  .callout p {{ font-size: 12px; color: #8888a0; line-height: 1.6; }}
  .parent-row td {{ background: rgba(77,142,255,0.04); }}
  .parent-row .cat-name {{ font-weight: 600; font-size: 13px; }}
</style>
</head>
<body>
<div class="container">

<h1>Expense Scrub — {YEAR}</h1>
<p class="subtitle">Every dollar categorized. What's fixed, what's cuttable, and what the floor looks like. Auto-generated from FIRE Master DB.</p>

<div class="hero-grid">
  <div class="stat-card"><div class="stat-label">Total {YEAR} Spend</div><div class="stat-value red">{fmt(total_cents)}</div></div>
  <div class="stat-card"><div class="stat-label">Monthly Average</div><div class="stat-value red">{fmt(total_cents // num_months)}</div></div>
  <div class="stat-card"><div class="stat-label">Fixed / Non-Discretionary</div><div class="stat-value yellow">{fmt(fixed_cents)}</div><div class="stat-sub">{fixed_cents * 100 // total_cents}% of total</div></div>
  <div class="stat-card"><div class="stat-label">Discretionary</div><div class="stat-value green">{fmt(cut_cents)}</div><div class="stat-sub">{cut_cents * 100 // total_cents}% — cuttable</div></div>
  <div class="stat-card"><div class="stat-label">Target Floor</div><div class="stat-value blue">~${survival_total:,}/mo</div><div class="stat-sub">${survival_total * 12:,}/yr with cuts</div></div>
</div>

<div class="section">
  <div class="section-title">Monthly Spending — {YEAR}</div>
  <div class="monthly-grid">{monthly_bars}
  </div>
  {spike_html}
</div>

<div class="section">
  <div class="section-title">Spending by Parent Category — {YEAR}</div>
  <table>
    <thead><tr><th style="width:25%">Category</th><th style="width:10%">Annual</th><th style="width:10%">Monthly</th><th style="width:8%">% of Total</th><th style="width:35%">Distribution</th><th style="width:12%">Txns</th></tr></thead>
    <tbody>{parent_rows}
    </tbody>
  </table>
</div>

<div class="section">
  <div class="section-title">Detailed Category Scrub — Every Line Item</div>
  <table>
    <thead><tr><th>Category</th><th>Parent</th><th>Annual</th><th>Monthly</th><th>Type</th><th>Detail</th></tr></thead>
    <tbody>{detail_rows}
      <tr class="summary-row">
        <td colspan="2"><strong>TOTAL</strong></td>
        <td class="mono red">{fmt(total_cents)}</td>
        <td class="mono red">{fmt(total_cents // num_months)}</td>
        <td colspan="2"></td>
      </tr>
    </tbody>
  </table>
</div>

<div class="two-col">
  <div class="section">
    <div class="section-title">Scenario: Survival Mode</div>
    <table>
      <tr><td>Fixed costs</td><td class="mono" style="text-align:right">${survival_fixed:,}/mo</td></tr>
      <tr><td>Semi-discretionary (50% cut)</td><td class="mono" style="text-align:right">${survival_semi:,}/mo</td></tr>
      <tr><td>Discretionary ($500/mo floor)</td><td class="mono" style="text-align:right">${survival_disc:,}/mo</td></tr>
      <tr class="summary-row"><td><strong>Survival burn rate</strong></td><td class="mono green" style="text-align:right"><strong>${survival_total:,}/mo</strong></td></tr>
      <tr><td style="color:#8888a0">Savings vs current</td><td class="mono green" style="text-align:right">${savings_vs_current:,}/mo (${savings_vs_current * 12:,}/yr)</td></tr>
    </table>
    <div class="callout callout-green" style="margin-top: 16px;">
      <h4>Impact on runway</h4>
      <p>At ${survival_total:,}/mo burn + $3,333/mo rental income, net drain = ${survival_total - 3333:,}/mo. From $120K cash + severance, runway = ~{120000 // (survival_total - 3333):.0f} months.</p>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Top 5 Cuts by Impact</div>
    <table>
      <thead><tr><th>Category</th><th>{YEAR} Spend</th><th>Target</th><th>Savings</th></tr></thead>
      <tbody>{top5_rows}
        <tr class="summary-row"><td><strong>Top 5</strong></td><td></td><td></td><td class="mono green"><strong>{fmt(top5_savings)}</strong></td></tr>
      </tbody>
    </table>
  </div>
</div>

<div class="section" style="border-left: 3px solid #4d8eff;">
  <div class="section-title" style="color: #4d8eff;">Key Insight: Housing is {parents[0]['cents'] * 100 // total_cents}% of All Spending</div>
  <p style="color: #8888a0; line-height: 1.8; font-size: 13px;">
    {fmt(parents[0]['cents'])}/yr goes to mortgage, HOA, and rent across three properties. This is the <strong>single largest lever</strong>.
    The expense scrub can save ~${savings_vs_current:,}/mo from lifestyle cuts, but a property sale removes $2,000-5,300/mo from the fixed base.
    <strong>Combined, they could cut the burn from {fmt(total_cents // num_months)}/mo to under $10,000/mo.</strong>
  </p>
</div>

<p style="color: #8888a0; font-size: 11px; text-align: center; margin-top: 32px;">
  Auto-generated from FIRE Master transaction data — {YEAR} calendar year — {date.today().isoformat()}<br>
  Edit classifications in scripts/report_expense_scrub.py (FIXED, SEMI sets) and re-run.
</p>

</div>
</body>
</html>"""


async def main():
    categories, monthly, parents = await fetch_data()
    html = generate_html(categories, monthly, parents)

    out = Path(__file__).resolve().parent.parent / "reports" / f"expense-scrub-{YEAR}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(f"Generated: {out}")
    print(f"  {len(categories)} categories, {sum(c['cents'] for c in categories)/100:,.0f} total")


if __name__ == "__main__":
    asyncio.run(main())

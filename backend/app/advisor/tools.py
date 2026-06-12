"""Tool definitions for the AI financial advisor — maps Claude tools to existing engines."""

import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.net_worth import NetWorthEngine
from app.engines.spending import SpendingEngine
from app.models.category_mapping import CategoryMapping
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_net_worth_summary",
        "description": (
            "Get the user's current net worth including total assets, total liabilities, "
            "asset allocation by account type, and changes over 1 day and 30 days. "
            "Use this when the user asks about their net worth, wealth, or financial position."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_spending_analysis",
        "description": (
            "Get spending breakdown by category for a date range. Shows each category's total "
            "spending, percentage of total, and transaction count. Also includes total income, "
            "total spending, net savings, and savings rate for the period. "
            "Use this when the user asks about spending, expenses, budgets, or where their money goes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "range": {
                    "type": "string",
                    "description": "Time range: 'month' (current month), '3m', '6m', 'ytd', '1y', or 'all'",
                    "enum": ["month", "3m", "6m", "ytd", "1y", "all"],
                    "default": "3m",
                },
                "group_by_parent": {
                    "type": "boolean",
                    "description": "If true, group by parent category instead of detailed category",
                    "default": False,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_spending_trends",
        "description": (
            "Get monthly spending trends for the top categories over time. Shows how spending "
            "in each category has changed month-over-month. Also includes total spending trend. "
            "Use this when the user asks about spending trends, changes over time, or spending patterns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {
                    "type": "integer",
                    "description": "Number of months of history to analyze (default 12)",
                    "default": 12,
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top categories to include (default 8)",
                    "default": 8,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_savings_rate",
        "description": (
            "Get monthly savings rate time series showing income, spending, savings amount, "
            "and savings rate percentage for each month. Includes current and average savings rate. "
            "Use this when the user asks about savings, savings rate, or income vs expenses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {
                    "type": "integer",
                    "description": "Number of months of history (default 24)",
                    "default": 24,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recurring_expenses",
        "description": (
            "Get a list of detected recurring expenses (subscriptions, bills, memberships) "
            "with merchant name, average amount, frequency, and estimated annual cost. "
            "Use this when the user asks about subscriptions, recurring bills, or fixed expenses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "search_transactions",
        "description": (
            "Search transactions by category, merchant, date range, or amount range. "
            "Returns matching transactions with date, amount, merchant, and category. "
            "Use this when the user asks about specific purchases, merchants, or wants to find transactions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by normalized category name (case-insensitive partial match)",
                },
                "merchant": {
                    "type": "string",
                    "description": "Filter by merchant name (case-insensitive partial match)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
                "min_amount": {
                    "type": "number",
                    "description": "Minimum transaction amount in dollars (positive = expense)",
                },
                "max_amount": {
                    "type": "number",
                    "description": "Maximum transaction amount in dollars (positive = expense)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results to return (default 25, max 100)",
                    "default": 25,
                },
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executors — each maps to an existing engine method
# ---------------------------------------------------------------------------

async def execute_get_net_worth_summary(db: AsyncSession, _input: dict) -> dict:
    engine = NetWorthEngine(db)
    result = await engine.calculate_current()
    return {
        "net_worth": result.net_worth,
        "total_assets": result.total_assets,
        "total_liabilities": result.total_liabilities,
        "asset_allocation": result.asset_allocation,
        "change_1d": result.change_1d,
        "change_30d": result.change_30d,
    }


async def execute_get_spending_analysis(db: AsyncSession, _input: dict) -> dict:
    engine = SpendingEngine(db)
    result = await engine.get_category_breakdown(
        range_str=_input.get("range", "3m"),
        group_by_parent=_input.get("group_by_parent", False),
    )
    return {
        "total_spending": result.total_spending,
        "total_income": result.total_income,
        "net_savings": result.net_savings,
        "savings_rate": result.savings_rate,
        "start_date": str(result.start_date),
        "end_date": str(result.end_date),
        "categories": [
            {
                "category": c.category,
                "parent_category": c.parent_category,
                "amount": c.amount,
                "percentage": c.percentage,
                "transaction_count": c.transaction_count,
            }
            for c in result.categories[:20]  # Cap to avoid token bloat
        ],
    }


async def execute_get_spending_trends(db: AsyncSession, _input: dict) -> dict:
    engine = SpendingEngine(db)
    result = await engine.get_trends(
        months=_input.get("months", 12),
        top_n=_input.get("top_n", 8),
    )
    return {
        "months": result.months,
        "total_trend": [{"month": p.month, "amount": p.amount} for p in result.total_trend],
        "categories": [
            {
                "category": ct.category,
                "total": ct.total,
                "points": [{"month": p.month, "amount": p.amount} for p in ct.points],
            }
            for ct in result.categories
        ],
    }


async def execute_get_savings_rate(db: AsyncSession, _input: dict) -> dict:
    engine = SpendingEngine(db)
    result = await engine.get_savings_rate(months=_input.get("months", 24))
    return {
        "current_rate": result.current_rate,
        "average_rate": result.average_rate,
        "months": result.months,
        "points": [
            {
                "month": p.month,
                "income": p.income,
                "spending": p.spending,
                "savings": p.savings,
                "savings_rate": p.savings_rate,
            }
            for p in result.points
        ],
    }


async def execute_get_recurring_expenses(db: AsyncSession, _input: dict) -> dict:
    engine = SpendingEngine(db)
    result = await engine.get_recurring()
    return {
        "total_monthly": result.total_monthly,
        "total_annual": result.total_annual,
        "expenses": [
            {
                "merchant": e.merchant,
                "category": e.category,
                "average_amount": e.average_amount,
                "frequency": e.frequency,
                "last_date": str(e.last_date),
                "occurrence_count": e.occurrence_count,
                "estimated_annual": e.estimated_annual,
            }
            for e in result.expenses[:30]  # Cap to avoid token bloat
        ],
    }


async def execute_search_transactions(db: AsyncSession, _input: dict) -> dict:
    limit = min(_input.get("limit", 25), 100)

    query = (
        select(
            Transaction.date,
            Transaction.amount,
            Transaction.merchant,
            Transaction.category,
            CategoryMapping.normalized_category,
        )
        .outerjoin(CategoryMapping, Transaction.category == CategoryMapping.raw_category)
    )

    filters = []

    if _input.get("category"):
        filters.append(
            CategoryMapping.normalized_category.ilike(f"%{_input['category']}%")
        )

    if _input.get("merchant"):
        filters.append(
            Transaction.merchant.ilike(f"%{_input['merchant']}%")
        )

    if _input.get("start_date"):
        filters.append(Transaction.date >= date.fromisoformat(_input["start_date"]))

    if _input.get("end_date"):
        filters.append(Transaction.date <= date.fromisoformat(_input["end_date"]))

    if _input.get("min_amount") is not None:
        # User thinks in positive dollars for expenses; DB stores as negative cents
        min_cents = int(_input["min_amount"] * 100)
        filters.append(Transaction.amount <= -min_cents)

    if _input.get("max_amount") is not None:
        max_cents = int(_input["max_amount"] * 100)
        filters.append(Transaction.amount >= -max_cents)

    # Exclude transfers
    filters.append(
        (CategoryMapping.is_transfer == False) | (CategoryMapping.is_transfer.is_(None))
    )

    if filters:
        query = query.where(*filters)

    query = query.order_by(Transaction.date.desc()).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return {
        "count": len(rows),
        "transactions": [
            {
                "date": str(r.date),
                "amount": round(abs(r.amount) / 100, 2),
                "type": "expense" if r.amount < 0 else "income",
                "merchant": r.merchant,
                "category": r.normalized_category or r.category,
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Tool executor registry
# ---------------------------------------------------------------------------

TOOL_EXECUTORS: dict[str, callable] = {
    "get_net_worth_summary": execute_get_net_worth_summary,
    "get_spending_analysis": execute_get_spending_analysis,
    "get_spending_trends": execute_get_spending_trends,
    "get_savings_rate": execute_get_savings_rate,
    "get_recurring_expenses": execute_get_recurring_expenses,
    "search_transactions": execute_search_transactions,
}

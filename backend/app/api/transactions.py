"""Transactions ledger — a Monarch-like browser over every transaction.

This is the general home for classification. Listing lives here; the mutating actions
(assign-to-property / clear override) are reused from properties.py
(`PUT/DELETE /api/properties/transactions/{tx_id}`) so there is one source of truth for
how a transaction gets stamped with property_id/property_category/property_source.
"""

from datetime import date as date_cls
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transactions import LedgerResponse, LedgerTransaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _d(cents) -> float:
    # cents may be an int (per-row amount) or a Decimal (SQL SUM) — Decimal / float
    # raises TypeError, so coerce to float first.
    return round(float(cents or 0) / 100.0, 2)


@router.get("", response_model=LedgerResponse)
async def list_transactions(
    q: str | None = Query(None, description="case-insensitive merchant substring search"),
    tx_type: str = Query("all", alias="type", pattern="^(all|income|expense)$"),
    classification: str = Query("all", pattern="^(all|unclassified|classified)$"),
    property_id: UUID | None = None,
    account_id: UUID | None = None,
    date_from: date_cls | None = None,
    date_to: date_cls | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable feed of every transaction.

    `classification=unclassified` surfaces the blind spot the Tracker can't show:
    transactions with no property assigned (property_id IS NULL), including income.
    """
    conditions = []
    if q:
        conditions.append(Transaction.merchant.ilike(f"%{q}%"))
    if tx_type == "income":
        conditions.append(Transaction.amount >= 0)
    elif tx_type == "expense":
        conditions.append(Transaction.amount < 0)
    if classification == "unclassified":
        conditions.append(Transaction.property_id.is_(None))
    elif classification == "classified":
        conditions.append(Transaction.property_id.isnot(None))
    if property_id:
        conditions.append(Transaction.property_id == property_id)
    if account_id:
        conditions.append(Transaction.account_id == account_id)
    if date_from:
        conditions.append(Transaction.date >= date_from)
    if date_to:
        conditions.append(Transaction.date <= date_to)

    # Count + income/expense totals over the FULL filtered set (not just this page).
    totals_q = select(
        func.count(),
        func.coalesce(
            func.sum(case((Transaction.amount >= 0, Transaction.amount), else_=0)), 0
        ),
        func.coalesce(
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)), 0
        ),
    ).where(*conditions)
    total_count, income_cents, expense_cents = (await db.execute(totals_q)).one()

    rows = (
        await db.execute(
            select(Transaction, Account.name.label("account_name"))
            .join(Account, Transaction.account_id == Account.id, isouter=True)
            .where(*conditions)
            .order_by(Transaction.date.desc(), Transaction.amount.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    transactions = [
        LedgerTransaction(
            id=str(t.id),
            date=t.date.isoformat(),
            merchant=t.merchant,
            account_name=account_name,
            category=t.category,
            amount=_d(t.amount),
            property_id=str(t.property_id) if t.property_id else None,
            property_category=t.property_category,
            property_source=t.property_source,
            hide_from_reports=t.hide_from_reports,
        )
        for t, account_name in rows
    ]

    return LedgerResponse(
        transactions=transactions,
        total_count=int(total_count or 0),
        total_income=_d(income_cents),
        total_expense=_d(expense_cents),
    )

"""Schemas for the transactions ledger — the Monarch-like all-transactions browser.

The ledger is the general surface for *seeing* every transaction and classifying it
(currently: assigning to a property via the existing override plumbing in properties.py).
It deliberately does NOT filter to expenses the way the Spending Tracker does, so income
transactions (which the Tracker can never show) are reachable here.
"""

from pydantic import BaseModel


class LedgerTransaction(BaseModel):
    id: str
    date: str
    merchant: str | None
    account_name: str | None
    category: str | None  # raw Monarch category
    amount: float  # signed dollars: positive = income, negative = expense
    property_id: str | None
    property_category: str | None
    property_source: str | None  # 'rule' | 'manual' | None
    hide_from_reports: bool


class LedgerResponse(BaseModel):
    transactions: list[LedgerTransaction]
    total_count: int
    total_income: float  # signed sum of positive amounts over the full filtered set
    total_expense: float  # signed sum of negative amounts over the full filtered set

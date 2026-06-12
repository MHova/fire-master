"""Cash flow projection engine — monthly runway projection from events, burn rate, and income."""

import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.cashflow_event import CashflowEvent
from app.models.category_mapping import CategoryMapping
from app.models.transaction import Transaction
from app.schemas.cashflow import MonthlyProjectionPoint, RunwayResponse

logger = logging.getLogger(__name__)


def _cents_to_dollars(cents: int) -> float:
    return float(cents) / 100


class CashflowEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_current_cash(self) -> float:
        """Sum of checking + savings account balances (liquid cash)."""
        from app.models.enums import AccountType

        result = await self.db.execute(
            select(func.sum(Account.current_balance)).where(
                Account.include_in_net_worth == True,
                Account.is_asset == True,
                Account.account_type.in_([AccountType.CHECKING, AccountType.SAVINGS]),
            )
        )
        total_cents = result.scalar() or 0
        return _cents_to_dollars(int(total_cents))

    async def get_trailing_monthly_burn(self, months: int = 3) -> float:
        """Average monthly spending over the last N months from transaction data."""
        start = date.today() - timedelta(days=months * 30)

        result = await self.db.execute(
            select(func.sum(-Transaction.amount).label("total_cents"))
            .join(CategoryMapping, Transaction.category == CategoryMapping.raw_category)
            .where(
                Transaction.date >= start,
                CategoryMapping.is_income == False,
                CategoryMapping.is_transfer == False,
                Transaction.amount < 0,
            )
        )
        total_cents = result.scalar() or 0
        return _cents_to_dollars(int(total_cents)) / months

    async def get_trailing_monthly_income(self, months: int = 3) -> float:
        """Average monthly income over the last N months from transaction data."""
        start = date.today() - timedelta(days=months * 30)

        result = await self.db.execute(
            select(func.sum(Transaction.amount).label("total_cents"))
            .join(CategoryMapping, Transaction.category == CategoryMapping.raw_category)
            .where(
                Transaction.date >= start,
                CategoryMapping.is_income == True,
            )
        )
        total_cents = result.scalar() or 0
        return _cents_to_dollars(int(total_cents)) / months

    async def get_active_events(self) -> list[CashflowEvent]:
        """All non-cancelled, non-completed events."""
        result = await self.db.execute(
            select(CashflowEvent)
            .where(CashflowEvent.status.in_(["planned", "confirmed"]))
            .order_by(CashflowEvent.date)
        )
        return list(result.scalars().all())

    def _expand_events_to_months(
        self,
        events: list[CashflowEvent],
        start_month: date,
        num_months: int,
    ) -> dict[str, list[tuple[str, float, str, bool]]]:
        """Expand events into month -> [(name, amount, type, is_start)].

        is_start is True for one-off events and for the first month of a
        recurring event. Consumers use it to label the chart only on the
        start month so recurring events don't stamp a label every tick.
        """
        monthly: dict[str, list[tuple[str, float, str, bool]]] = {}

        for i in range(num_months):
            month_date = start_month + relativedelta(months=i)
            month_key = month_date.strftime("%Y-%m")
            monthly.setdefault(month_key, [])

        for event in events:
            amount = _cents_to_dollars(event.amount_cents) * event.probability
            if event.event_type == "expense":
                amount = -amount

            if not event.is_recurring:
                month_key = event.date.strftime("%Y-%m")
                if month_key in monthly:
                    monthly[month_key].append((event.name, amount, event.event_type, True))
            else:
                end = event.end_date or (start_month + relativedelta(months=num_months))
                current = event.date
                first = True
                while current <= end:
                    month_key = current.strftime("%Y-%m")
                    if month_key in monthly:
                        monthly[month_key].append((event.name, amount, event.event_type, first))
                    first = False

                    if event.recurrence == "monthly":
                        current += relativedelta(months=1)
                    elif event.recurrence == "quarterly":
                        current += relativedelta(months=3)
                    elif event.recurrence == "annual":
                        current += relativedelta(years=1)
                    else:
                        break

        return monthly

    async def project_runway(
        self,
        months: int = 24,
        income_override: float | None = None,
        burn_override: float | None = None,
    ) -> RunwayResponse:
        """Project monthly cash balance forward.

        If income_override / burn_override are provided, use those as the
        go-forward monthly baseline instead of trailing averages. Events
        still layer on top.
        """
        current_cash = await self.get_current_cash()
        trailing_burn = await self.get_trailing_monthly_burn(months=3)
        trailing_income = await self.get_trailing_monthly_income(months=3)

        # Use overrides when provided, trailing averages otherwise
        monthly_burn = burn_override if burn_override is not None else trailing_burn
        monthly_income = income_override if income_override is not None else trailing_income

        events = await self.get_active_events()

        today = date.today()
        start_month = today.replace(day=1)

        event_map = self._expand_events_to_months(events, start_month, months)

        projection: list[MonthlyProjectionPoint] = []
        cash = current_cash
        cash_zero_date: date | None = None

        for i in range(months):
            month_date = start_month + relativedelta(months=i)
            month_key = month_date.strftime("%Y-%m")

            starting_cash = cash

            # Start with baseline
            month_expenses = monthly_burn
            month_income = monthly_income

            # Layer events on top — label only start months (one-offs + recurring starts)
            event_names: list[str] = []
            for name, amount, etype, is_start in event_map.get(month_key, []):
                if is_start:
                    event_names.append(name)
                if amount > 0:
                    month_income += amount
                else:
                    month_expenses += abs(amount)

            net = month_income - month_expenses
            cash = starting_cash + net

            if cash <= 0 and cash_zero_date is None:
                if net < 0:
                    days_into_month = int(starting_cash / (abs(net) / 30))
                    days_into_month = max(0, min(30, days_into_month))
                    cash_zero_date = month_date + timedelta(days=days_into_month)

            projection.append(MonthlyProjectionPoint(
                month=month_key,
                starting_cash=round(starting_cash, 2),
                income=round(month_income, 2),
                expenses=round(month_expenses, 2),
                net=round(net, 2),
                ending_cash=round(cash, 2),
                events=event_names,
            ))

        net_monthly = monthly_income - monthly_burn
        months_remaining: float | None = None
        if net_monthly < 0 and current_cash > 0:
            months_remaining = round(current_cash / abs(net_monthly), 1)

        return RunwayResponse(
            current_cash=round(current_cash, 2),
            monthly_burn=round(monthly_burn, 2),
            monthly_income=round(monthly_income, 2),
            net_monthly=round(net_monthly, 2),
            months_remaining=months_remaining,
            cash_zero_date=cash_zero_date,
            trailing_burn=round(trailing_burn, 2),
            trailing_income=round(trailing_income, 2),
            projection=projection,
        )

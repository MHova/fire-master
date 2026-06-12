"""Net worth calculation engine — current value, historical time-series, and snapshot computation."""

import logging
from datetime import date, timedelta

from sqlalchemy import case, distinct, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.enums import DataSource
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.schemas.net_worth import (
    NetWorthCurrentResponse,
    NetWorthHistoryPoint,
    NetWorthHistoryResponse,
)

logger = logging.getLogger(__name__)


def _cents_to_dollars(cents: int) -> float:
    return cents / 100


# Maps the underlying account_type to a debt-side category. Real estate
# accounts on the liability side are mortgages (the asset/loan share an
# account_type in the source data), and vehicle loans should read as such.
_DEBT_CATEGORY_OVERRIDES = {
    "real_estate": "mortgage",
    "VEHICLE": "auto_loan",
}


def _debt_category(account_type_value: str) -> str:
    return _DEBT_CATEGORY_OVERRIDES.get(account_type_value, account_type_value)


class NetWorthEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_current(self) -> NetWorthCurrentResponse:
        """Calculate current net worth from account balances."""
        result = await self.db.execute(
            select(Account).where(Account.include_in_net_worth == True)
        )
        accounts = result.scalars().all()

        total_assets = 0
        total_liabilities = 0
        allocation: dict[str, int] = {}
        liability_allocation: dict[str, int] = {}

        for acct in accounts:
            balance = abs(acct.current_balance)
            if acct.is_asset:
                total_assets += balance
                type_key = acct.account_type.value
                allocation[type_key] = allocation.get(type_key, 0) + balance
            else:
                total_liabilities += balance
                # Mortgages get split per account so users can see each
                # property's loan separately. Other liabilities (credit cards,
                # auto loans) stay bucketed by category.
                if acct.account_type.value == "real_estate":
                    debt_key = acct.name
                else:
                    debt_key = _debt_category(acct.account_type.value)
                liability_allocation[debt_key] = (
                    liability_allocation.get(debt_key, 0) + balance
                )

        net_worth = total_assets - total_liabilities

        # Calculate changes from snapshots
        change_1d = await self._get_change(net_worth, days=1)
        change_30d = await self._get_change(net_worth, days=30)

        return NetWorthCurrentResponse(
            net_worth=_cents_to_dollars(net_worth),
            total_assets=_cents_to_dollars(total_assets),
            total_liabilities=_cents_to_dollars(total_liabilities),
            asset_allocation={k: _cents_to_dollars(v) for k, v in allocation.items()},
            liability_allocation={
                k: _cents_to_dollars(v) for k, v in liability_allocation.items()
            },
            change_1d=_cents_to_dollars(change_1d) if change_1d is not None else None,
            change_30d=_cents_to_dollars(change_30d) if change_30d is not None else None,
        )

    async def _get_change(self, current_net_worth: int, days: int) -> int | None:
        """Calculate net worth change vs. N days ago."""
        target_date = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(NetWorthSnapshot.net_worth)
            .where(NetWorthSnapshot.date <= target_date)
            .order_by(NetWorthSnapshot.date.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return current_net_worth - row

    async def get_history(
        self,
        range_str: str = "1y",
        interval: str = "daily",
    ) -> NetWorthHistoryResponse:
        """Get historical net worth data points."""
        range_map = {
            "30d": 30,
            "90d": 90,
            "1y": 365,
            "3y": 365 * 3,
            "5y": 365 * 5,
            "all": 365 * 50,
        }
        days = range_map.get(range_str, 365)
        start_date = date.today() - timedelta(days=days)

        query = (
            select(NetWorthSnapshot)
            .where(NetWorthSnapshot.date >= start_date)
            .order_by(NetWorthSnapshot.date)
        )
        result = await self.db.execute(query)
        snapshots = result.scalars().all()

        points = [
            NetWorthHistoryPoint(
                date=s.date,
                net_worth=_cents_to_dollars(s.net_worth),
                total_assets=_cents_to_dollars(s.total_assets),
                total_liabilities=_cents_to_dollars(s.total_liabilities),
            )
            for s in snapshots
        ]

        # Auto-downsample large datasets for chart performance
        if len(points) > 365 * 3:
            points = _downsample(points, 7)  # weekly for 3y+
        elif interval == "weekly" and len(points) > 52:
            points = _downsample(points, 7)
        elif interval == "monthly" and len(points) > 12:
            points = _downsample(points, 30)

        return NetWorthHistoryResponse(points=points, range=range_str, interval=interval)

    async def compute_snapshot(self, snapshot_date: date) -> None:
        """Compute and upsert a net worth snapshot for a given date from balance_snapshots."""
        # Get the latest balance snapshot for each account on or before the target date
        subq = (
            select(
                BalanceSnapshot.account_id,
                func.max(BalanceSnapshot.date).label("max_date"),
            )
            .where(BalanceSnapshot.date <= snapshot_date)
            .group_by(BalanceSnapshot.account_id)
            .subquery()
        )

        result = await self.db.execute(
            select(BalanceSnapshot, Account)
            .join(Account, BalanceSnapshot.account_id == Account.id)
            .join(
                subq,
                (BalanceSnapshot.account_id == subq.c.account_id)
                & (BalanceSnapshot.date == subq.c.max_date),
            )
            .where(Account.include_in_net_worth == True)
        )
        rows = result.all()

        total_assets = 0
        total_liabilities = 0
        breakdown: dict[str, int] = {}

        for snapshot, account in rows:
            balance = abs(snapshot.balance)
            if account.is_asset:
                total_assets += balance
                # Only include assets in breakdown
                type_key = account.account_type.value
                breakdown[type_key] = breakdown.get(type_key, 0) + balance
            else:
                total_liabilities += balance

        net_worth = total_assets - total_liabilities

        stmt = insert(NetWorthSnapshot).values(
            date=snapshot_date,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=net_worth,
            breakdown=breakdown,
        ).on_conflict_do_update(
            index_elements=["date"],
            set_={
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "net_worth": net_worth,
                "breakdown": breakdown,
            },
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def backfill_snapshots(self) -> int:
        """Build historical net worth snapshots from all balance_snapshot dates."""
        result = await self.db.execute(
            select(distinct(BalanceSnapshot.date)).order_by(BalanceSnapshot.date)
        )
        dates = [row[0] for row in result.all()]

        count = 0
        for d in dates:
            await self.compute_snapshot(d)
            count += 1

        await self.db.flush()
        logger.info("Backfilled %d net worth snapshots", count)
        return count

    async def import_monarch_net_worth(self, client) -> int:
        """Import Monarch's own aggregate net worth history and recompute today's breakdown."""
        from app.ingestion.monarch_client import MonarchClient

        snapshots = await client.get_aggregate_snapshots()

        def _dollars_to_cents(amount: float) -> int:
            return int(round(amount * 100))

        rows = []
        for snap in snapshots:
            d = snap.get("date")
            if isinstance(d, str):
                d = date.fromisoformat(d)
            rows.append({
                "date": d,
                "net_worth": _dollars_to_cents(snap.get("balance", 0)),
                "total_assets": 0,
                "total_liabilities": 0,
                "breakdown": {},
            })

        # Batch upsert
        for i in range(0, len(rows), 500):
            chunk = rows[i : i + 500]
            stmt = insert(NetWorthSnapshot).values(chunk).on_conflict_do_update(
                index_elements=["date"],
                set_={
                    "net_worth": insert(NetWorthSnapshot).excluded.net_worth,
                },
            )
            await self.db.execute(stmt)

        # Recompute today with full asset/liability breakdown
        await self.compute_snapshot(date.today())

        await self.db.flush()
        logger.info("Imported %d Monarch net worth snapshots", len(rows))
        return len(rows)


def _downsample(points: list[NetWorthHistoryPoint], interval_days: int) -> list[NetWorthHistoryPoint]:
    """Keep one data point per interval."""
    if not points:
        return points
    result = [points[0]]
    for p in points[1:]:
        if (p.date - result[-1].date).days >= interval_days:
            result.append(p)
    # Always include the last point
    if result[-1].date != points[-1].date:
        result.append(points[-1])
    return result

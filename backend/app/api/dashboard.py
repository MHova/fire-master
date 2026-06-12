from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.engines.net_worth import NetWorthEngine
from app.models.account import Account
from app.schemas.account import AccountResponse
from app.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = NetWorthEngine(db)
    net_worth = await engine.calculate_current()

    result = await db.execute(
        select(Account).order_by(Account.is_asset.desc(), Account.current_balance.desc())
    )
    accounts = result.scalars().all()

    # Get last sync time
    result = await db.execute(select(func.max(Account.last_synced_at)))
    last_synced = result.scalar_one_or_none()

    return DashboardSummaryResponse(
        net_worth=net_worth,
        accounts=[AccountResponse.from_model(a) for a in accounts],
        last_synced_at=last_synced,
        account_count=len(accounts),
    )

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.engines.net_worth import NetWorthEngine
from app.schemas.net_worth import NetWorthCurrentResponse, NetWorthHistoryResponse

router = APIRouter(prefix="/api/net-worth", tags=["net-worth"])


@router.get("/current", response_model=NetWorthCurrentResponse)
async def get_current_net_worth(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = NetWorthEngine(db)
    return await engine.calculate_current()


@router.get("/history", response_model=NetWorthHistoryResponse)
async def get_net_worth_history(
    range: str = Query("1y", pattern="^(30d|90d|1y|3y|5y|all)$"),
    interval: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = NetWorthEngine(db)
    return await engine.get_history(range_str=range, interval=interval)

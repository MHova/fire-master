from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.engines.asset_hub import AssetHubEngine
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.schemas.account import AccountDetailResponse, AccountEnrichmentUpdate, AccountResponse
from app.schemas.assets import AssetHubResponse

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).order_by(Account.is_asset.desc(), Account.current_balance.desc())
    )
    accounts = result.scalars().all()
    return [AccountResponse.from_model(a) for a in accounts]


@router.get("/asset-hub", response_model=AssetHubResponse)
async def get_asset_hub(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified Asset Hub: all active accounts + physical assets as tiles."""
    engine = AssetHubEngine(db)
    return await engine.get_asset_hub()


@router.get("/{account_id}/history")
async def account_history(
    account_id: UUID,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = select(BalanceSnapshot).where(BalanceSnapshot.account_id == account_id)
    if start_date:
        query = query.where(BalanceSnapshot.date >= start_date)
    if end_date:
        query = query.where(BalanceSnapshot.date <= end_date)
    query = query.order_by(BalanceSnapshot.date)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    return [
        {"date": s.date.isoformat(), "balance": s.balance / 100}
        for s in snapshots
    ]


@router.get("/{account_id}/detail", response_model=AccountDetailResponse)
async def get_account_detail(
    account_id: UUID,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full account detail: enrichment + balance history + recent transactions."""
    engine = AssetHubEngine(db)
    detail = await engine.get_account_detail(account_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Account not found")

    account = detail["account"]
    resp = AccountResponse.from_model(account)
    return AccountDetailResponse(
        **resp.model_dump(),
        balance_history=detail["balance_history"],
        recent_transactions=detail["recent_transactions"],
    )


@router.patch("/{account_id}/enrichment", response_model=AccountResponse)
async def update_account_enrichment(
    account_id: UUID,
    data: AccountEnrichmentUpdate,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update enrichment fields (notes, tags, fire_role, etc.) for an account."""
    engine = AssetHubEngine(db)
    account = await engine.update_account_enrichment(account_id, data)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.commit()
    return AccountResponse.from_model(account)

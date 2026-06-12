"""Spending analysis API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.engines.spending import SpendingEngine
from app.schemas.spending import (
    HeatmapResponse,
    RecurringExpensesResponse,
    SavingsRateResponse,
    SpendingAnalysisResponse,
    SpendingTrendsResponse,
    TrackerCategoryItem,
    TrackerDailyResponse,
    TrackerSummaryResponse,
    TrackerTransactionsResponse,
)

router = APIRouter(prefix="/api/spending", tags=["spending"])


@router.get("/analysis", response_model=SpendingAnalysisResponse)
async def get_spending_analysis(
    range: str = Query("1y", pattern="^(month|3m|6m|ytd|1y|all)$"),
    group_by_parent: bool = Query(False),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_category_breakdown(range_str=range, group_by_parent=group_by_parent)


@router.get("/trends", response_model=SpendingTrendsResponse)
async def get_spending_trends(
    months: int = Query(12, ge=1, le=120),
    top_n: int = Query(8, ge=1, le=30),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_trends(months=months, top_n=top_n)


@router.get("/savings-rate", response_model=SavingsRateResponse)
async def get_savings_rate(
    months: int = Query(24, ge=1, le=120),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_savings_rate(months=months)


@router.get("/recurring", response_model=RecurringExpensesResponse)
async def get_recurring_expenses(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_recurring()


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_spending_heatmap(
    months: int = Query(12, ge=1, le=60),
    top_n: int = Query(15, ge=1, le=30),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_heatmap(months=months, top_n=top_n)


# ---------------------------------------------------------------------------
#  Spending Tracker — running budget tracker since layoff
# ---------------------------------------------------------------------------


@router.get("/tracker", response_model=TrackerSummaryResponse)
async def get_tracker_summary(
    monthly_target: float = Query(5000.0, ge=100, le=50000),
    exclude_planned: bool = Query(False),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_tracker_summary(
        monthly_target=monthly_target, exclude_planned=exclude_planned,
    )


@router.get("/tracker/daily", response_model=TrackerDailyResponse)
async def get_tracker_daily(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    monthly_target: float = Query(5000.0, ge=100, le=50000),
    exclude_planned: bool = Query(False),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_tracker_daily(
        month=month, monthly_target=monthly_target, exclude_planned=exclude_planned,
    )


@router.get("/tracker/categories", response_model=list[TrackerCategoryItem])
async def get_tracker_categories(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    exclude_planned: bool = Query(False),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Category breakdown for a single month (defaults to current month)."""
    engine = SpendingEngine(db)
    return await engine.get_tracker_categories(
        month=month, exclude_planned=exclude_planned,
    )


@router.get("/tracker/transactions", response_model=TrackerTransactionsResponse)
async def get_tracker_transactions(
    category: str | None = Query(None),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    exclude_planned: bool = Query(False),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = SpendingEngine(db)
    return await engine.get_tracker_transactions(
        category=category, month=month, limit=limit, offset=offset,
        exclude_planned=exclude_planned,
    )

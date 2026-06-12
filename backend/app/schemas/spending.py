"""Pydantic response models for spending analysis API."""

from datetime import date

from pydantic import BaseModel


class CategoryBreakdownItem(BaseModel):
    category: str
    parent_category: str
    amount: float  # dollars (positive = spending)
    percentage: float
    transaction_count: int


class SpendingAnalysisResponse(BaseModel):
    categories: list[CategoryBreakdownItem]
    total_spending: float
    total_income: float
    net_savings: float
    savings_rate: float | None  # percentage, None if no income
    start_date: date
    end_date: date
    group_by_parent: bool


class TrendPoint(BaseModel):
    month: str  # "2025-01"
    amount: float


class CategoryTrend(BaseModel):
    category: str
    points: list[TrendPoint]
    total: float


class SpendingTrendsResponse(BaseModel):
    categories: list[CategoryTrend]
    total_trend: list[TrendPoint]
    months: int


class SavingsRatePoint(BaseModel):
    month: str
    income: float
    spending: float
    savings: float
    savings_rate: float | None


class SavingsRateResponse(BaseModel):
    points: list[SavingsRatePoint]
    current_rate: float | None
    average_rate: float | None
    months: int


class RecurringExpense(BaseModel):
    merchant: str
    category: str
    average_amount: float
    frequency: str  # "monthly", "weekly", etc.
    last_date: date
    occurrence_count: int
    estimated_annual: float


class RecurringExpensesResponse(BaseModel):
    expenses: list[RecurringExpense]
    total_monthly: float
    total_annual: float


class HeatmapCell(BaseModel):
    month: str
    category: str
    amount: float


class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell]
    categories: list[str]
    months: list[str]


class CategoryMappingResponse(BaseModel):
    id: str
    raw_category: str
    normalized_category: str
    parent_category: str
    is_discretionary: bool
    is_income: bool
    is_transfer: bool
    monarch_category_id: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, m) -> "CategoryMappingResponse":
        return cls(
            id=str(m.id),
            raw_category=m.raw_category,
            normalized_category=m.normalized_category,
            parent_category=m.parent_category,
            is_discretionary=m.is_discretionary,
            is_income=m.is_income,
            is_transfer=m.is_transfer,
            monarch_category_id=m.monarch_category_id,
        )


class CategoryMappingUpdate(BaseModel):
    normalized_category: str | None = None
    parent_category: str | None = None
    is_discretionary: bool | None = None
    is_income: bool | None = None
    is_transfer: bool | None = None


# ---------------------------------------------------------------------------
#  Spending Tracker — running budget tracker since layoff (March 24, 2026)
# ---------------------------------------------------------------------------


class TrackerCategoryItem(BaseModel):
    category: str
    parent_category: str
    amount: float
    percentage: float
    transaction_count: int
    is_discretionary: bool


class TrackerMonthSummary(BaseModel):
    month: str  # "2026-04"
    total: float
    target: float
    delta: float  # target - total (positive = under budget)
    daily_average: float
    status: str  # "under_pace" | "on_pace" | "over_pace"


class PlannedExclusion(BaseModel):
    event_name: str
    event_amount: float
    matched_transaction_id: str
    matched_amount: float
    matched_merchant: str | None
    matched_date: str


class TrackerSummaryResponse(BaseModel):
    current_month: str
    start_date: str
    monthly_target: float

    # This month
    spent_so_far: float
    days_elapsed: int
    days_remaining: int
    days_in_month: int
    daily_average: float
    projected_total: float
    budget_remaining: float
    status: str  # "under_pace" | "on_pace" | "over_pace"

    # Context
    pre_layoff_avg: float
    savings_vs_old: float
    runway_days_added: float

    # Category breakdown this month
    categories: list[TrackerCategoryItem]

    # Monthly history since start
    months: list[TrackerMonthSummary]

    # Planned event exclusions
    exclude_planned: bool = False
    planned_exclusions: list[PlannedExclusion] = []


class TrackerDailyPoint(BaseModel):
    day: int
    date: str
    daily_amount: float
    cumulative: float
    target_pace: float


class TrackerDailyResponse(BaseModel):
    month: str
    days: list[TrackerDailyPoint]
    monthly_target: float


class TrackerTransaction(BaseModel):
    id: str
    date: str
    merchant: str | None
    amount: float
    category: str
    parent_category: str
    is_discretionary: bool


class TrackerTransactionsResponse(BaseModel):
    transactions: list[TrackerTransaction]
    total_count: int
    total_amount: float

import datetime as _dt
from uuid import UUID

from pydantic import BaseModel, computed_field

from app.models.enums import AssetCategory, AspirationPriority, AspirationStatus
from app.schemas.account import AccountResponse


# --- Physical Asset Schemas ---


class PhysicalAssetCreate(BaseModel):
    name: str
    asset_category: AssetCategory
    subcategory: str | None = None
    purchase_date: _dt.datetime | None = None
    purchase_price: int | None = None
    current_value: int = 0
    valuation_method: str | None = None
    linked_account_id: UUID | None = None
    external_ref: dict | None = None
    cost_tracking_categories: list[str] | None = None
    details: dict | None = None
    photos: list[str] | None = None
    notes: str | None = None
    tags: list[str] | None = None
    fire_role: str | None = None
    custom_data: dict | None = None


class PhysicalAssetUpdate(BaseModel):
    name: str | None = None
    subcategory: str | None = None
    current_value: int | None = None
    valuation_method: str | None = None
    linked_account_id: UUID | None = None
    external_ref: dict | None = None
    cost_tracking_categories: list[str] | None = None
    details: dict | None = None
    photos: list[str] | None = None
    notes: str | None = None
    tags: list[str] | None = None
    fire_role: str | None = None
    custom_data: dict | None = None


class PhysicalAssetTileResponse(BaseModel):
    id: UUID
    name: str
    asset_category: AssetCategory
    subcategory: str | None
    current_value_cents: int
    equity_cents: int | None = None
    fire_role: str | None = None
    tags: list[str] | None = None
    has_notes: bool = False
    value_change_30d: float | None = None

    @computed_field
    @property
    def current_value(self) -> float:
        return self.current_value_cents / 100

    @computed_field
    @property
    def equity(self) -> float | None:
        if self.equity_cents is None:
            return None
        return self.equity_cents / 100

    model_config = {"from_attributes": True}


class PhysicalAssetResponse(PhysicalAssetTileResponse):
    purchase_date: _dt.datetime | None = None
    purchase_price: int | None = None
    valuation_method: str | None = None
    last_valued_at: _dt.datetime | None = None
    linked_account_id: UUID | None = None
    external_ref: dict | None = None
    cost_tracking_categories: list[str] | None = None
    details: dict | None = None
    photos: list[str] | None = None
    notes: str | None = None
    custom_data: dict | None = None
    is_active: bool = True
    created_at: _dt.datetime | None = None
    updated_at: _dt.datetime | None = None
    valuation_history: list[dict] = []
    cost_of_ownership: dict | None = None


# --- Asset Valuation Schemas ---


class AssetValuationCreate(BaseModel):
    value: int
    source: str | None = None
    confidence: str | None = None
    date: _dt.date | None = None


class AssetValuationResponse(BaseModel):
    id: UUID
    asset_id: UUID
    date: _dt.date
    value_cents: int
    source: str | None
    confidence: str | None

    @computed_field
    @property
    def value(self) -> float:
        return self.value_cents / 100

    model_config = {"from_attributes": True}


# --- Aspiration Schemas ---


class AspirationCreate(BaseModel):
    name: str
    description: str | None = None
    estimated_cost: int
    target_date: _dt.date | None = None
    priority: AspirationPriority = AspirationPriority.NICE_TO_HAVE
    category: str | None = None
    linked_asset_id: UUID | None = None
    funding_source: str | None = None
    financing_terms: dict | None = None
    ongoing_cost_delta: int | None = None
    notes: str | None = None


class AspirationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    estimated_cost: int | None = None
    target_date: _dt.date | None = None
    priority: AspirationPriority | None = None
    category: str | None = None
    linked_asset_id: UUID | None = None
    funding_source: str | None = None
    financing_terms: dict | None = None
    ongoing_cost_delta: int | None = None
    status: AspirationStatus | None = None
    notes: str | None = None


class AspirationResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    estimated_cost_cents: int
    target_date: _dt.date | None
    priority: AspirationPriority
    category: str | None
    linked_asset_id: UUID | None
    funding_source: str | None
    financing_terms: dict | None
    ongoing_cost_delta_cents: int | None
    fire_impact_days: int | None
    status: AspirationStatus
    notes: str | None
    created_at: _dt.datetime
    updated_at: _dt.datetime

    @computed_field
    @property
    def estimated_cost(self) -> float:
        return self.estimated_cost_cents / 100

    model_config = {"from_attributes": True}


# --- Unified Asset Hub Response ---


class AccountTileResponse(BaseModel):
    id: UUID
    name: str
    account_type: str
    institution: str | None
    balance_cents: int
    is_asset: bool
    fire_role: str | None = None
    tags: list[str] | None = None
    has_enrichment: bool = False
    value_change_30d: float | None = None

    @computed_field
    @property
    def balance(self) -> float:
        return self.balance_cents / 100

    model_config = {"from_attributes": True}


class AssetHubResponse(BaseModel):
    accounts: list[AccountTileResponse]
    physical_assets: list[PhysicalAssetTileResponse]
    total_net_worth: float
    total_assets: float
    total_liabilities: float
    total_physical_assets: float

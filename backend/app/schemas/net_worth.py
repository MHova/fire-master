from datetime import date

from pydantic import BaseModel


class NetWorthCurrentResponse(BaseModel):
    net_worth: float
    total_assets: float
    total_liabilities: float
    asset_allocation: dict[str, float]
    liability_allocation: dict[str, float] = {}
    change_1d: float | None = None
    change_30d: float | None = None


class NetWorthHistoryPoint(BaseModel):
    date: date
    net_worth: float
    total_assets: float
    total_liabilities: float


class NetWorthHistoryResponse(BaseModel):
    points: list[NetWorthHistoryPoint]
    range: str
    interval: str

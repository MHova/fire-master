from datetime import datetime

from pydantic import BaseModel

from app.schemas.account import AccountResponse
from app.schemas.net_worth import NetWorthCurrentResponse


class DashboardSummaryResponse(BaseModel):
    net_worth: NetWorthCurrentResponse
    accounts: list[AccountResponse]
    last_synced_at: datetime | None
    account_count: int

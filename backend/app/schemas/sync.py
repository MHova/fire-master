from datetime import datetime

from pydantic import BaseModel


class SyncStatusResponse(BaseModel):
    status: str  # idle, syncing, completed, error
    last_sync_at: datetime | None = None
    accounts_synced: int = 0
    transactions_synced: int = 0
    snapshots_synced: int = 0
    error_message: str | None = None


class SyncTriggerResponse(BaseModel):
    message: str
    task_id: str | None = None

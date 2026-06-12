import json

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.redis import get_redis, SYNC_STATUS_KEY
from app.schemas.sync import SyncStatusResponse, SyncTriggerResponse

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/monarch", response_model=SyncTriggerResponse)
async def trigger_monarch_sync(
    full_history: bool = False,
    _user: str = Depends(get_current_user),
):
    from app.tasks.sync_tasks import run_monarch_sync

    task = run_monarch_sync.delay(full_history=full_history)
    return SyncTriggerResponse(message="Monarch sync started", task_id=task.id)


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(_user: str = Depends(get_current_user)):
    r = get_redis()
    raw = r.get(SYNC_STATUS_KEY)
    if not raw:
        return SyncStatusResponse(status="idle")
    data = json.loads(raw)
    return SyncStatusResponse(**data)

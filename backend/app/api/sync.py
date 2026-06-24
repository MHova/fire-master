import json

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.redis import get_redis, SYNC_STATUS_KEY
from app.schemas.sync import SyncStatusResponse, SyncTriggerResponse

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/monarch", response_model=SyncTriggerResponse)
async def trigger_monarch_sync(
    full_history: bool = False,
    _user: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    # Demo lock: never enqueue a real sync (the Celery task enforces this too).
    if settings.DEMO_MODE:
        return SyncTriggerResponse(message="Monarch sync is disabled in demo mode.")

    from app.tasks.sync_tasks import run_monarch_sync

    task = run_monarch_sync.delay(full_history=full_history)
    return SyncTriggerResponse(message="Monarch sync started", task_id=task.id)


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    _user: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    r = get_redis()
    raw = r.get(SYNC_STATUS_KEY)
    if not raw:
        return SyncStatusResponse(status="idle", demo_mode=settings.DEMO_MODE)
    data = json.loads(raw)
    data["demo_mode"] = settings.DEMO_MODE
    return SyncStatusResponse(**data)

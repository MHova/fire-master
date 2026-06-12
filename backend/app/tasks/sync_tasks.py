"""Celery tasks for Monarch sync and net worth snapshot computation."""

import asyncio
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.redis import get_redis, SYNC_STATUS_KEY
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _set_sync_status(status: dict):
    """Write sync status to Redis."""
    r = get_redis()
    r.set(SYNC_STATUS_KEY, json.dumps(status), ex=86400)


async def _run_monarch_sync_async(full_history: bool = False):
    """Async implementation of the Monarch sync."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    from app.ingestion.monarch_client import MonarchClient
    from app.ingestion.monarch_sync import MonarchSyncService
    from app.ingestion.category_sync import CategorySyncService
    from app.engines.net_worth import NetWorthEngine

    _set_sync_status({
        "status": "syncing",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    try:
        client = MonarchClient(settings.MONARCH_SESSION_FILE)
        await client.connect()

        async with session_factory() as db:
            # Sync categories before transactions so mappings are ready
            cat_sync = CategorySyncService(db, client)
            try:
                categories_synced = await cat_sync.sync_from_monarch()
                logger.info("Synced %d categories", categories_synced)
            except Exception as e:
                logger.warning("Monarch category API sync failed, falling back to transaction backfill: %s", e)
                categories_synced = await cat_sync.sync_from_transactions()

            sync_service = MonarchSyncService(db, client)
            result = await sync_service.run_full_sync(full_history=full_history)

            # Backfill any new categories from freshly synced transactions
            await cat_sync.sync_from_transactions()

            # Import Monarch's aggregate net worth history
            nw_engine = NetWorthEngine(db)
            await nw_engine.import_monarch_net_worth(client)
            await db.commit()

        status = {
            "status": "completed" if result.success else "error",
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "accounts_synced": result.accounts_synced,
            "transactions_synced": result.transactions_synced,
            "snapshots_synced": result.snapshots_synced,
            "error_message": "; ".join(result.errors) if result.errors else None,
        }
        _set_sync_status(status)
        return status

    except Exception as e:
        logger.exception("Monarch sync failed")
        _set_sync_status({
            "status": "error",
            "error_message": str(e),
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
        })
        raise
    finally:
        await engine.dispose()


async def _compute_daily_snapshot_async():
    """Async implementation of daily snapshot computation."""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    from app.engines.net_worth import NetWorthEngine

    try:
        async with session_factory() as db:
            nw_engine = NetWorthEngine(db)
            await nw_engine.compute_snapshot(date.today())
            await db.commit()
            logger.info("Daily net worth snapshot computed for %s", date.today())
    finally:
        await engine.dispose()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_monarch_sync(self, full_history: bool = False):
    """Celery task: sync all data from Monarch Money."""
    try:
        return asyncio.run(_run_monarch_sync_async(full_history=full_history))
    except Exception as exc:
        logger.error("Monarch sync task failed (attempt %d): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def compute_daily_snapshot():
    """Celery task: compute today's net worth snapshot."""
    asyncio.run(_compute_daily_snapshot_async())

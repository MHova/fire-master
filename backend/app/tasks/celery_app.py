from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "fire_master",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    beat_schedule={
        "monarch-sync-every-4-hours": {
            "task": "app.tasks.sync_tasks.run_monarch_sync",
            "schedule": crontab(minute=0, hour="*/4"),
        },
        "compute-daily-net-worth-snapshot": {
            "task": "app.tasks.sync_tasks.compute_daily_snapshot",
            "schedule": crontab(minute=30, hour=0),
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])

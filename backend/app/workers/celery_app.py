"""
Celery application configuration
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "secdash",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.scan_tasks",
        "app.workers.notification_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.SCAN_TIMEOUT,
    task_soft_time_limit=settings.SCAN_TIMEOUT - 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    # Weekly vulnerability report
    "weekly-vulnerability-report": {
        "task": "app.workers.notification_tasks.send_weekly_report",
        "schedule": crontab(day_of_week="monday", hour=9, minute=0),
    },
    # Cleanup old scan results
    "cleanup-old-scans": {
        "task": "app.workers.scan_tasks.cleanup_old_scans",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f"Request: {self.request!r}")
    return {"status": "success", "message": "Celery is working!"}

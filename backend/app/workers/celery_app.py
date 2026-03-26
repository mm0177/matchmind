from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "matchmaking",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.persona_worker",
        "app.workers.match_worker",
        "app.workers.notification_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# ─── Periodic schedule ────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Run persona extraction every night at 01:00 UTC
    "persona-extraction-nightly": {
        "task": "app.workers.persona_worker.run_persona_extraction_all",
        "schedule": crontab(hour=1, minute=0),
    },
    # Run matching every night at 02:00 UTC (after extraction finishes)
    "matching-daily": {
        "task": "app.workers.match_worker.run_matching",
        "schedule": crontab(hour=2, minute=0),
    },
    # Send daily prompt reminder at 09:00 UTC
    "daily-prompt-reminders": {
        "task": "app.workers.notification_worker.send_daily_prompt_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    # Nudge inactive users at 18:00 UTC (evening reminder)
    "nudge-inactive-users": {
        "task": "app.workers.notification_worker.nudge_inactive_users",
        "schedule": crontab(hour=18, minute=0),
    },
}

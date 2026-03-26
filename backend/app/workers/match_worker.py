"""
Match Worker — daily Celery task.
Runs the full matching algorithm after persona extraction completes.
"""
import asyncio
import logging

from app.workers.celery_app import celery_app
from app.matching.engine import run_daily_matching

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    name="app.workers.match_worker.run_matching",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def run_matching(self):
    """Run the daily matching job and trigger notifications for new matches."""
    try:
        match_run = _run_async(run_daily_matching())
        logger.info(
            f"Match run {match_run.id}: {match_run.total_matches} matches "
            f"for {match_run.total_users} users."
        )
        # Trigger notification worker for pending matches
        from app.workers.notification_worker import notify_pending_matches
        notify_pending_matches.delay(str(match_run.id))
        return str(match_run.id)
    except Exception as exc:
        logger.error(f"Matching task failed: {exc}")
        raise self.retry(exc=exc)

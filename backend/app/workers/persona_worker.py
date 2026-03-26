"""
Persona Worker — nightly Celery task.
Runs persona extraction for all active users who have chatted recently.
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import select, and_

from app.workers.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.auth.models import User
from app.chat.models import UserDayProgress
from app.persona.extractor import extract_persona_for_user
from app.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _get_active_users_with_progress():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User, UserDayProgress)
            .join(UserDayProgress, UserDayProgress.user_id == User.id)
            .where(
                and_(
                    User.is_active == True,
                    UserDayProgress.current_day >= 1,
                )
            )
        )
        return [(row.User.id, row.UserDayProgress.current_day) for row in result]


@celery_app.task(name="app.workers.persona_worker.run_persona_extraction_all", bind=True, max_retries=3)
def run_persona_extraction_all(self):
    """Extract personas for all active users."""
    try:
        users = _run_async(_get_active_users_with_progress())
        logger.info(f"Persona extraction: processing {len(users)} users.")
        for user_id, day in users:
            try:
                _run_async(extract_persona_for_user(user_id, date.today()))
                logger.info(f"Extracted persona for user {user_id} (day {day})")
            except Exception as exc:
                logger.error(f"Failed extraction for user {user_id}: {exc}")
    except Exception as exc:
        logger.error(f"Persona extraction task failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="app.workers.persona_worker.run_persona_extraction_for_user")
def run_persona_extraction_for_user(user_id: str):
    """Extract persona for a single user (can be triggered immediately after chat)."""
    import uuid
    _run_async(extract_persona_for_user(uuid.UUID(user_id), date.today()))

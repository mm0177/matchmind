"""
Notification Worker — sends match notifications and daily prompt reminders.
"""
import asyncio
import logging
from uuid import UUID

from sqlalchemy import select, and_

from app.workers.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.auth.models import User
from app.chat.models import UserDayProgress
from app.matching.models import Match
from app.notifications.service import notify_match, notify_daily_prompt, notify_nudge_inactive
from app.chat.daily_prompts import get_day_plan

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _notify_pending_matches_async(run_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match).where(
                and_(Match.run_id == UUID(run_id), Match.status == "pending")
            )
        )
        pending = list(result.scalars().all())
        logger.info(f"Sending notifications for {len(pending)} pending matches.")

        for match in pending:
            user_a_result = await db.execute(select(User).where(User.id == match.user_a_id))
            user_b_result = await db.execute(select(User).where(User.id == match.user_b_id))
            user_a = user_a_result.scalar_one_or_none()
            user_b = user_b_result.scalar_one_or_none()

            if not user_a or not user_b:
                continue

            reason = match.score_breakdown.get("user_reason", "high overall compatibility")
            await notify_match(db, user_a, user_b, match.score, reason)

            match.status = "notified"

        await db.commit()


async def _send_daily_prompt_reminders_async():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User, UserDayProgress)
            .join(UserDayProgress, UserDayProgress.user_id == User.id)
            .where(and_(User.is_active == True, UserDayProgress.current_day <= 10))
        )
        rows = result.all()
        logger.info(f"Sending daily prompt reminders to {len(rows)} users.")
        for row in rows:
            user = row.User
            progress = row.UserDayProgress
            plan = get_day_plan(progress.current_day)
            await notify_daily_prompt(db, user, progress.current_day, plan["theme"])


@celery_app.task(name="app.workers.notification_worker.notify_pending_matches", bind=True)
def notify_pending_matches(self, run_id: str):
    try:
        _run_async(_notify_pending_matches_async(run_id))
    except Exception as exc:
        logger.error(f"notify_pending_matches failed: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="app.workers.notification_worker.send_daily_prompt_reminders", bind=True)
def send_daily_prompt_reminders(self):
    try:
        _run_async(_send_daily_prompt_reminders_async())
    except Exception as exc:
        logger.error(f"send_daily_prompt_reminders failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def _nudge_inactive_users_async():
    """Find users who have an active journey but haven't chatted today, and email them."""
    from datetime import date, datetime, timezone
    from app.chat.models import ChatMessage

    today = date.today()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    async with AsyncSessionLocal() as db:
        # Get all active users with journey in progress (day 1-10)
        result = await db.execute(
            select(User, UserDayProgress)
            .join(UserDayProgress, UserDayProgress.user_id == User.id)
            .where(and_(
                User.is_active == True,
                UserDayProgress.current_day >= 1,
                UserDayProgress.current_day <= 10,
            ))
        )
        rows = result.all()
        logger.info(f"Nudge inactive check: {len(rows)} users in active journeys.")

        nudged = 0
        for row in rows:
            user = row.User
            progress = row.UserDayProgress

            # Check if user has sent ANY messages today
            msg_count_result = await db.execute(
                select(select(ChatMessage.id).where(
                    ChatMessage.user_id == user.id,
                    ChatMessage.role == "user",
                    ChatMessage.created_at >= today_start,
                ).exists())
            )
            chatted_today = msg_count_result.scalar()

            if not chatted_today:
                plan = get_day_plan(progress.current_day)
                await notify_nudge_inactive(db, user, progress.current_day, plan["theme"])
                nudged += 1

        logger.info(f"Nudge inactive: emailed {nudged} inactive users.")


@celery_app.task(name="app.workers.notification_worker.nudge_inactive_users", bind=True)
def nudge_inactive_users(self):
    """Email users who haven't chatted today."""
    try:
        _run_async(_nudge_inactive_users_async())
    except Exception as exc:
        logger.error(f"nudge_inactive_users failed: {exc}")
        raise self.retry(exc=exc, countdown=60)

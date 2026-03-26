import logging
from uuid import UUID

import sendgrid
from sendgrid.helpers.mail import Mail

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.notifications.models import Notification
from app.auth.models import User
from app.config import settings

logger = logging.getLogger(__name__)


# ─── In-app notifications ─────────────────────────────────────────────────────

async def create_in_app_notification(
    db: AsyncSession,
    user_id: UUID,
    notification_type: str,
    title: str,
    body: str,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def get_user_notifications(
    db: AsyncSession, user_id: UUID, unread_only: bool = False
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)
    q = q.order_by(Notification.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_notification_read(db: AsyncSession, notification_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.is_read = True
    await db.commit()
    return True


# ─── Email notifications ──────────────────────────────────────────────────────

async def send_email_notification(to_email: str, subject: str, body_html: str) -> bool:
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping email.")
        return False
    try:
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
            to_emails=to_email,
            subject=subject,
            html_content=body_html,
        )
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}: status {response.status_code}")
        return response.status_code in (200, 202)
    except Exception as exc:
        logger.error(f"Email send failed: {exc}")
        return False


# ─── High-level notification helpers ─────────────────────────────────────────

async def notify_match(
    db: AsyncSession,
    user_a: User,
    user_b: User,
    score: float,
    reason: str,
) -> None:
    """Create in-app + email notifications for both users in a new match."""
    title = "You have a new match!"
    body_a = f"We found someone you should meet. {reason}"
    body_b = f"We found someone you should meet. {reason}"

    await create_in_app_notification(db, user_a.id, "match", title, body_a)
    await create_in_app_notification(db, user_b.id, "match", title, body_b)

    html_template = """
    <html><body>
    <h2>You have a new match on MatchMind!</h2>
    <p>{body}</p>
    <p>Log in to see who it is.</p>
    <br><small>To stop receiving these emails, update your notification settings.</small>
    </body></html>
    """
    await send_email_notification(user_a.email, title, html_template.format(body=body_a))
    await send_email_notification(user_b.email, title, html_template.format(body=body_b))


async def notify_daily_prompt(
    db: AsyncSession,
    user: User,
    day_number: int,
    theme: str,
) -> None:
    """Remind the user to continue their daily conversation."""
    title = f"Day {day_number}: {theme}"
    body = f"Your Day {day_number} conversation is ready — today's theme is '{theme}'. Come chat!"

    await create_in_app_notification(db, user.id, "daily_prompt", title, body)

    html = f"""
    <html><body>
    <h2>{title}</h2>
    <p>{body}</p>
    <p>Log in to MatchMind to continue.</p>
    </body></html>
    """
    await send_email_notification(user.email, title, html)


async def notify_nudge_inactive(
    db: AsyncSession,
    user: User,
    day_number: int,
    theme: str,
) -> None:
    """Email the user that they haven't chatted today. No in-app notif — email only."""
    subject = f"Don't break your streak! Day {day_number} is waiting 💬"
    html = f"""
    <html><body style="font-family: -apple-system, sans-serif; color: #e2e8f0; background: #0f172a; padding: 32px;">
    <div style="max-width: 480px; margin: auto; background: #1e293b; border-radius: 16px; padding: 32px; border: 1px solid #334155;">
        <h2 style="color: #a78bfa; margin-top: 0;">Hey {user.display_name}! 👋</h2>
        <p>You haven't chatted today, and Day {day_number} is ready for you.</p>
        <p>Today's theme: <strong style="color: #c4b5fd;">{theme}</strong></p>
        <p>The more days you complete, the better your match will be. Don't let your progress slip!</p>
        <div style="margin-top: 24px; text-align: center;">
            <a href="http://localhost:3000/chat"
               style="display: inline-block; background: #7c3aed; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                Continue Day {day_number} →
            </a>
        </div>
        <p style="margin-top: 24px; font-size: 12px; color: #64748b;">
            You're on Day {day_number} of 10 — {10 - day_number} days left until matching!
        </p>
    </div>
    </body></html>
    """
    await send_email_notification(user.email, subject, html)
    logger.info(f"Nudge inactive email sent to {user.email} (Day {day_number})")

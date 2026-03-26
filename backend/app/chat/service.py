import re
import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.chat.models import ChatSession, ChatMessage, UserDayProgress
from app.chat.daily_prompts import build_system_prompt, get_day_plan, DAILY_PROMPT_PLAN
from app.llm.base import LLMMessage
from app.llm.client import get_llm_client
from app.persona.models import PersonaSnapshot, UserEntity
from app.config import settings


# ─── Low-effort detection ─────────────────────────────────────────────────────
_LOW_EFFORT_RE = re.compile(
    r"^(ye+s*|no+|o+k+|okay+|yep+|yup+|ya+h*|yeah+|nah+|nope+"
    r"|sure+|not sure|not really|idk|i ?dk|i don'?t know|maybe+"
    r"|hm+|uhh*|umm*|correct|fine|good|great|nice|thanks|thank you"
    r"|cool+|alright|right|true|false|lol+|haha+|ha+|k+|mhm+"
    r"|dunno|i see|i guess|whatever|same|wow|ah+|oh+|eh+"
    r"|well|yea+|like|ikr|tbh|i think so|kinda|sort of|kind of"
    r")[\.\!\?\,]*$",
    re.IGNORECASE,
)

# Absolute cap on total messages (low-effort + real) per day to prevent abuse
_ABSOLUTE_MSG_CAP = 30


def _is_low_effort(text: str) -> bool:
    """Return True if the message is too short / matches a low-effort pattern."""
    words = text.split()
    return len(words) <= 4 and bool(_LOW_EFFORT_RE.match(text.strip()))


# ─── Session management ───────────────────────────────────────────────────────

async def get_or_create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str = "New Chat",
) -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
    )
    return list(result.scalars().all())


async def get_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[ChatSession]:
    result = await db.execute(
        select(ChatSession).where(
            and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


# ─── Day progress management ──────────────────────────────────────────────────

async def get_or_create_day_progress(
    db: AsyncSession, user_id: uuid.UUID
) -> UserDayProgress:
    result = await db.execute(
        select(UserDayProgress).where(UserDayProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()
    if not progress:
        progress = UserDayProgress(user_id=user_id, current_day=1, themes_covered=[])
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
    return progress


async def maybe_advance_day(db: AsyncSession, progress: UserDayProgress) -> bool:
    """
    Advance the current_day counter ONLY when:
    1. The user last chatted on a different calendar day, AND
    2. The user completed their exchange quota for the current day.

    If the user skipped days (e.g. didn't open the app for 3 days), the day
    still only advances by 1 — they must complete each day's conversation
    before moving on.
    """
    today = date.today()
    max_exchanges: int = settings.MAX_EXCHANGES_PER_DAY

    if progress.last_active_date and progress.last_active_date < today:
        # Check whether user finished their substantive exchanges for the current day
        all_msgs = await db.execute(
            select(ChatMessage.content).where(
                ChatMessage.user_id == progress.user_id,
                ChatMessage.role == "user",
                ChatMessage.day_number == progress.current_day,
            )
        )
        exchanges_done = sum(
            1 for (txt,) in all_msgs.all() if not _is_low_effort(txt)
        )

        if exchanges_done >= max_exchanges and progress.current_day < 10:
            # Completed previous day → advance
            progress.current_day += 1
            if progress.current_day not in (progress.themes_covered or []):
                progress.themes_covered = list(progress.themes_covered or []) + [progress.current_day]

        # Always update last_active_date so we don't re-check tomorrow
        progress.last_active_date = today
        await db.commit()
        return exchanges_done >= max_exchanges

    if not progress.last_active_date:
        progress.last_active_date = today
        if 1 not in (progress.themes_covered or []):
            progress.themes_covered = [1]
        await db.commit()
    return False


# ─── Persona gap analysis ─────────────────────────────────────────────────────

async def get_user_entities(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    """Load extracted entities for a user, returning dicts for prompt injection."""
    result = await db.execute(
        select(UserEntity)
        .where(UserEntity.user_id == user_id)
        .order_by(UserEntity.created_at.asc())
    )
    entities = list(result.scalars().all())
    return [
        {
            "label": e.label,
            "relationship": e.relationship,
            "emotional_weight": e.emotional_weight,
            "context_note": e.context_note,
        }
        for e in entities
    ]


async def get_low_confidence_traits(
    db: AsyncSession, user_id: uuid.UUID, threshold: float = 0.4
) -> list[str]:
    """Return trait names where confidence is below the threshold."""
    result = await db.execute(
        select(PersonaSnapshot)
        .where(PersonaSnapshot.user_id == user_id)
        .order_by(PersonaSnapshot.version.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return []

    low = []
    checks = [
        ("openness", snapshot.openness_confidence),
        ("conscientiousness", snapshot.conscientiousness_confidence),
        ("extraversion", snapshot.extraversion_confidence),
        ("agreeableness", snapshot.agreeableness_confidence),
        ("neuroticism", snapshot.neuroticism_confidence),
    ]
    for name, conf in checks:
        if conf is None or conf < threshold:
            low.append(name)
    return low


async def is_religion_profile_missing(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """True when latest snapshot is missing any religious profile field."""
    result = await db.execute(
        select(PersonaSnapshot)
        .where(PersonaSnapshot.user_id == user_id)
        .order_by(PersonaSnapshot.version.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        return True

    aff = (snapshot.religion_affiliation or "").strip()
    obs = (snapshot.religion_observance_level or "").strip()
    req = (snapshot.religion_partner_requirement or "").strip()
    return not (aff and obs and req)


# ─── Core send-message flow ───────────────────────────────────────────────────

async def get_message_history(
    db: AsyncSession, session_id: uuid.UUID
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())


async def get_todays_messages_all_sessions(
    db: AsyncSession, user_id: uuid.UUID, day_number: int
) -> list[ChatMessage]:
    """Return all messages for this user on the given day_number across every session.
    Filtering by day_number (not just timestamp) ensures that when a user tests
    multiple days on the same calendar day via dev tools, the LLM context only
    contains messages belonging to the current day — not previous dev-set days.
    """
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.day_number == day_number,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())


async def send_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> ChatMessage:
    """
    1. Retrieve day progress
    2. Maybe advance the day
    3. Build system prompt (with low-confidence trait hints)
    4. Load message history → call LLM → save both user+assistant messages
    5. Return assistant's ChatMessage
    """
    progress = await get_or_create_day_progress(db, user_id)
    await maybe_advance_day(db, progress)

    day = progress.current_day
    low_confidence = await get_low_confidence_traits(db, user_id)
    religion_profile_missing = await is_religion_profile_missing(db, user_id)
    entities = await get_user_entities(db, user_id)

    # Count how many user messages have been sent on the current day_number (all sessions)
    # Using day_number (not timestamp) so jumping days via dev tools gives a fresh counter.
    count_result = await db.execute(
        select(func.count()).where(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.day_number == day,
        )
    )
    total_messages: int = count_result.scalar_one() or 0
    max_exchanges: int = settings.MAX_EXCHANGES_PER_DAY

    # Count only substantive (non-low-effort) user messages toward the exchange quota.
    # Low-effort messages like "hmm", "ok", "i see" don't consume exchange slots,
    # so the user keeps their full quota for meaningful conversation.
    all_user_msgs = await db.execute(
        select(ChatMessage.content).where(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.day_number == day,
        )
    )
    substantive_count = sum(
        1 for (txt,) in all_user_msgs.all() if not _is_low_effort(txt)
    )
    exchanges_used = substantive_count

    # Hard stop — day is over (substantive quota hit OR absolute message cap reached)
    if exchanges_used >= max_exchanges or total_messages >= _ABSOLUTE_MSG_CAP:
        if day >= 10:
            closing_text = (
                "And that's a wrap on our 10-day journey together! 🎉 "
                "Thank you for sharing so openly — it really helps me find someone "
                "who truly complements who you are. Your match results will be ready soon. "
                "Take care, and I'm rooting for you! 💛"
            )
        else:
            closing_text = (
                f"We've covered a lot today! ✨ That wraps up Day {day}. "
                "Come back tomorrow and we'll pick up where we left off."
            )
        closing = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=closing_text,
            day_number=day,
        )
        db.add(closing)
        await db.commit()
        await db.refresh(closing)
        return closing

    system_prompt = build_system_prompt(
        day,
        low_confidence or None,
        religion_profile_missing=religion_profile_missing,
        exchanges_used=exchanges_used,
        max_exchanges=max_exchanges,
        entities=entities or None,
    )

    # Load all messages for today's day across every session so the LLM has full
    # context and never re-asks questions already answered on this day.
    # We filter by day_number so messages from other days tested on the same
    # calendar date (via dev tools) are NOT included in the context.
    history = await get_todays_messages_all_sessions(db, user_id, day)

    # Build LLM message list
    llm_messages: list[LLMMessage] = [LLMMessage("system", system_prompt)]
    for msg in history:
        if msg.role in ("user", "assistant"):
            llm_messages.append(LLMMessage(msg.role, msg.content))

    # Append the new user message
    llm_messages.append(LLMMessage("user", content))

    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=content,
        day_number=day,
    )
    db.add(user_msg)
    await db.flush()

    # Call the LLM
    llm = get_llm_client()
    assistant_text = await llm.chat_completion(llm_messages, temperature=0.5, max_tokens=300)

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=assistant_text,
        day_number=day,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return assistant_msg

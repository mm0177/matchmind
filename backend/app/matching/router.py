"""
Matches Router — endpoints for users to view matches and chat with matched partners.
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.router import get_current_user
from app.auth.models import User
from app.matching.models import Match, MatchConversation, MatchMessage
from app.matching.schemas import MatchDetailResponse, MatchMessageOut, SendMatchMessageRequest

router = APIRouter(prefix="/matches", tags=["matches"])


def _compute_age(birth_date: date | None) -> int | None:
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


@router.get("", response_model=list[MatchDetailResponse])
async def get_my_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all matches for the authenticated user — name and age only."""
    uid = current_user.id
    result = await db.execute(
        select(Match)
        .where(or_(Match.user_a_id == uid, Match.user_b_id == uid))
        .order_by(Match.created_at.desc())
    )
    rows = result.scalars().all()

    matches_out = []
    for m in rows:
        partner_id = m.user_b_id if m.user_a_id == uid else m.user_a_id
        partner = await db.get(User, partner_id)
        if not partner:
            continue

        # Get or create conversation for this match
        conv_result = await db.execute(
            select(MatchConversation).where(MatchConversation.match_id == m.id)
        )
        conv = conv_result.scalar_one_or_none()
        if not conv:
            conv = MatchConversation(
                match_id=m.id,
                user_a_id=m.user_a_id,
                user_b_id=m.user_b_id,
            )
            db.add(conv)
            await db.flush()

        matches_out.append(
            MatchDetailResponse(
                id=m.id,
                partner_display_name=partner.display_name,
                partner_age=_compute_age(partner.birth_date),
                conversation_id=conv.id,
                status=m.status,
                created_at=m.created_at,
            )
        )

    # Mark as seen
    for m in rows:
        if m.status in ("pending", "notified"):
            m.status = "seen"
    await db.commit()

    return matches_out


# ─── Match Chat endpoints ─────────────────────────────────────────────────────

@router.get("/{conversation_id}/messages", response_model=list[MatchMessageOut])
async def get_match_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages in a match conversation. Only participants can access."""
    conv = await db.get(MatchConversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(status_code=403, detail="Not a participant")

    result = await db.execute(
        select(MatchMessage)
        .where(MatchMessage.conversation_id == conversation_id)
        .order_by(MatchMessage.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/{conversation_id}/messages", response_model=MatchMessageOut, status_code=201)
async def send_match_message(
    conversation_id: uuid.UUID,
    body: SendMatchMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a match conversation. Only participants can send."""
    conv = await db.get(MatchConversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.id not in (conv.user_a_id, conv.user_b_id):
        raise HTTPException(status_code=403, detail="Not a participant")
    if not conv.is_active:
        raise HTTPException(status_code=400, detail="Conversation is closed")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    msg = MatchMessage(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

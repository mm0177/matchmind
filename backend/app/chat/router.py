import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.auth.router import get_current_user
from app.auth.models import User
from app.chat import service
from app.chat.models import UserDayProgress
from app.chat.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SendMessageRequest,
    MessageResponse,
    DayStatusResponse,
)
from app.chat.daily_prompts import get_day_plan, DAILY_PROMPT_PLAN
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await service.get_or_create_session(db, current_user.id, title=body.title or "New Chat")
    return session


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.list_sessions(db, current_user.id)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    messages = await service.get_message_history(db, session_id)
    return messages


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if not session.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is closed")

    assistant_msg = await service.send_message(db, session_id, current_user.id, body.content)
    return assistant_msg


@router.get("/day-status", response_model=DayStatusResponse)
async def get_day_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = await service.get_or_create_day_progress(db, current_user.id)
    plan = get_day_plan(progress.current_day)
    return DayStatusResponse(
        current_day=progress.current_day,
        theme=plan["theme"],
        goal=plan["goal"],
        is_complete=progress.current_day >= 10 and len(progress.themes_covered or []) >= 10,
        days_covered=list(progress.themes_covered or []),
    )


# ─── DEV / TESTING endpoints (only available when DEV_MODE=true) ──────────────

def _require_dev():
    if not settings.DEV_MODE:
        raise HTTPException(status_code=403, detail="Only available in dev mode")


@router.post("/dev/set-day/{day_number}", tags=["dev"])
async def dev_set_day(
    day_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Jump to any day instantly for testing. DEV_MODE only."""
    _require_dev()
    if day_number < 1 or day_number > 10:
        raise HTTPException(status_code=400, detail="day_number must be 1–10")

    result = await db.execute(
        select(UserDayProgress).where(UserDayProgress.user_id == current_user.id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = UserDayProgress(
            user_id=current_user.id,
            current_day=day_number,
            last_active_date=date.today(),
            themes_covered=list(range(1, day_number + 1)),
        )
        db.add(progress)
    else:
        progress.current_day = day_number
        progress.last_active_date = date.today()
        progress.themes_covered = list(range(1, day_number + 1))

    await db.commit()

    plan = DAILY_PROMPT_PLAN.get(day_number, DAILY_PROMPT_PLAN[10])
    return {
        "message": f"Day set to {day_number}",
        "theme": plan["theme"],
        "goal": plan["goal"],
        "target_traits": plan["target_traits"],
        "sample_prompts": plan["sample_prompts"],
    }


@router.get("/dev/day-preview/{day_number}", tags=["dev"])
async def dev_day_preview(
    day_number: int,
    _: User = Depends(get_current_user),
):
    """Preview theme, goal, and sample questions for any day. DEV_MODE only."""
    _require_dev()
    if day_number < 1 or day_number > 10:
        raise HTTPException(status_code=400, detail="day_number must be 1–10")

    plan = DAILY_PROMPT_PLAN.get(day_number, DAILY_PROMPT_PLAN[10])
    return {
        "day": day_number,
        "theme": plan["theme"],
        "goal": plan["goal"],
        "target_traits": plan["target_traits"],
        "sample_prompts": plan["sample_prompts"],
        "system_context": plan["system_context"],
    }


@router.get("/dev/all-days", tags=["dev"])
async def dev_all_days(_: User = Depends(get_current_user)):
    """See the full 10-day plan at a glance. DEV_MODE only."""
    _require_dev()
    return {
        str(day): {
            "theme": plan["theme"],
            "goal": plan["goal"],
            "target_traits": plan["target_traits"],
        }
        for day, plan in DAILY_PROMPT_PLAN.items()
    }


@router.post("/dev/trigger-extraction", tags=["dev"])
async def dev_trigger_extraction(
    current_user: User = Depends(get_current_user),
):
    """Run persona extraction right now (skips midnight wait). DEV_MODE only."""
    _require_dev()
    from app.persona.extractor import extract_persona_for_user
    from app.persona.models import UserEntity
    from app.db.database import get_db as _get_db

    snapshot = await extract_persona_for_user(current_user.id, date.today())
    if not snapshot:
        return {"message": "No messages found — chat first, then trigger extraction"}

    # Check if this was a cached (no-new-messages) return vs fresh extraction
    # by comparing snapshot created_at with now — if it's more than 30s old, it was cached
    from datetime import datetime, timezone, timedelta
    is_cached = snapshot.created_at < (datetime.now(timezone.utc) - timedelta(seconds=30))
    message = (
        "No new messages since last extraction — returning existing snapshot (v"
        f"{snapshot.version}). Chat more to generate a new version."
        if is_cached
        else "Extraction complete"
    )

    # Fetch entities for this user
    from sqlalchemy.ext.asyncio import AsyncSession as _AS
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as _db:
        from sqlalchemy import select as _sel
        ent_result = await _db.execute(
            _sel(UserEntity)
            .where(UserEntity.user_id == current_user.id)
            .order_by(UserEntity.created_at.asc())
        )
        entities = list(ent_result.scalars().all())

    return {
        "message": message,
        "snapshot_version": snapshot.version,
        "overall_confidence": snapshot.overall_confidence,
        "mbti_label": snapshot.mbti_label,
        "big_five": {
            "openness": snapshot.openness,
            "conscientiousness": snapshot.conscientiousness,
            "extraversion": snapshot.extraversion,
            "agreeableness": snapshot.agreeableness,
            "neuroticism": snapshot.neuroticism,
        },
        "communication": {
            "directness": snapshot.comm_directness,
            "humor": snapshot.comm_humor,
            "formality": snapshot.comm_formality,
            "empathy": snapshot.comm_empathy,
        },
        "relationship": {
            "attachment_style": snapshot.attachment_style,
            "conflict_style": snapshot.conflict_style,
            "pace": snapshot.relationship_pace,
            "religious_profile": {
                "affiliation": snapshot.religion_affiliation,
                "observance_level": snapshot.religion_observance_level,
                "partner_requirement": snapshot.religion_partner_requirement,
            },
            "dealbreakers": snapshot.dealbreakers,
            "must_haves": snapshot.must_haves,
        },
        "authenticity": {
            "overall": snapshot.authenticity_score,
            "social_desirability": snapshot.social_desirability_score,
            "specificity": snapshot.specificity_score,
            "self_awareness": snapshot.self_awareness_score,
            "consistency": snapshot.consistency_score_llm,
        },
        "financial": {
            "scarcity_response": snapshot.fin_scarcity_response,
            "wealth_vision": snapshot.fin_wealth_vision,
            "risk_tolerance": snapshot.fin_risk_tolerance,
        },
        "self_perception": {
            "self_perception_gap": snapshot.self_perception_gap,
            "empathy_vs_apathy": snapshot.empathy_vs_apathy,
        },
        "entities": [
            {
                "label": e.label,
                "relationship": e.relationship,
                "emotional_weight": e.emotional_weight,
                "context_note": e.context_note,
                "day_extracted": e.day_extracted,
            }
            for e in entities
        ],
        "has_embedding": snapshot.embedding is not None and len(snapshot.embedding) > 0,
    }


@router.post("/dev/trigger-matching", tags=["dev"])
async def dev_trigger_matching(
    _: User = Depends(get_current_user),
):
    """Run the matching engine right now (skips 02:00 wait). DEV_MODE only."""
    _require_dev()
    from app.matching.engine import run_daily_matching

    match_run = await run_daily_matching()
    return {
        "message": "Matching complete",
        "run_date": str(match_run.run_date),
        "total_users_eligible": match_run.total_users,
        "total_matches_created": match_run.total_matches,
        "algorithm_ver": match_run.algorithm_ver,
    }


@router.post("/dev/make-me-matchable", tags=["dev"])
async def dev_make_matchable(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set is_verified=true, is_matchable=true instantly. DEV_MODE only."""
    _require_dev()
    current_user.is_verified = True
    current_user.is_matchable = True
    await db.commit()
    return {"message": f"{current_user.display_name} is now verified and matchable"}

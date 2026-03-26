"""
Persona Extractor — runs async after each day's chat sessions.
Analyzes all user messages, updates persona_snapshots and persona_facts.
"""
import json
import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.chat.models import ChatMessage, UserDayProgress
from app.persona.models import PersonaSnapshot, PersonaFact, UserEntity
from app.persona.schemas import PersonaExtractionResult
from app.persona.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.llm.base import LLMMessage
from app.llm.client import get_llm_client, get_embedding_client

logger = logging.getLogger(__name__)


async def _get_recent_messages(
    db: AsyncSession, user_id: UUID, since: date
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= since,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())


async def _get_latest_snapshot(
    db: AsyncSession, user_id: UUID
) -> PersonaSnapshot | None:
    result = await db.execute(
        select(PersonaSnapshot)
        .where(PersonaSnapshot.user_id == user_id)
        .order_by(PersonaSnapshot.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_user_day(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(UserDayProgress).where(UserDayProgress.user_id == user_id)
    )
    progress = result.scalar_one_or_none()
    return progress.current_day if progress else 1


async def _get_user_entities(db: AsyncSession, user_id: UUID) -> list[UserEntity]:
    """Load all previously extracted entities for a user."""
    result = await db.execute(
        select(UserEntity)
        .where(UserEntity.user_id == user_id)
        .order_by(UserEntity.created_at.asc())
    )
    return list(result.scalars().all())


def _entities_to_json(entities: list[UserEntity]) -> str:
    if not entities:
        return "[]"
    data = [
        {
            "label": e.label,
            "relationship": e.relationship,
            "emotional_weight": e.emotional_weight,
            "context_note": e.context_note,
        }
        for e in entities
    ]
    return json.dumps(data, indent=2)


def _snapshot_to_json(snapshot: PersonaSnapshot | None) -> str:
    if not snapshot:
        return "{}"
    data = {
        "version": snapshot.version,
        "overall_confidence": snapshot.overall_confidence,
        "big_five": {
            "openness": {"score": snapshot.openness, "confidence": snapshot.openness_confidence},
            "conscientiousness": {"score": snapshot.conscientiousness, "confidence": snapshot.conscientiousness_confidence},
            "extraversion": {"score": snapshot.extraversion, "confidence": snapshot.extraversion_confidence},
            "agreeableness": {"score": snapshot.agreeableness, "confidence": snapshot.agreeableness_confidence},
            "neuroticism": {"score": snapshot.neuroticism, "confidence": snapshot.neuroticism_confidence},
        },
        "mbti_derived": snapshot.mbti_label,
        "communication_style": {
            "directness": snapshot.comm_directness,
            "humor": snapshot.comm_humor,
            "formality": snapshot.comm_formality,
            "empathy": snapshot.comm_empathy,
        },
        "values": {
            "family": snapshot.val_family,
            "career": snapshot.val_career,
            "adventure": snapshot.val_adventure,
            "spirituality": snapshot.val_spirituality,
            "creativity": snapshot.val_creativity,
            "stability": snapshot.val_stability,
        },
        "relationship": {
            "attachment_style": snapshot.attachment_style,
            "conflict_style": snapshot.conflict_style,
            "pace_preference": snapshot.relationship_pace,
            "dealbreakers": snapshot.dealbreakers,
            "must_haves": snapshot.must_haves,
        },
        "religious_profile": {
            "affiliation": snapshot.religion_affiliation,
            "observance_level": snapshot.religion_observance_level,
            "partner_requirement": snapshot.religion_partner_requirement,
        },
        "consistency_flags": snapshot.consistency_flags,
        "financial": {
            "scarcity_response": snapshot.fin_scarcity_response,
            "wealth_vision": snapshot.fin_wealth_vision,
            "risk_tolerance": snapshot.fin_risk_tolerance,
        },
        "self_perception": {
            "self_perception_gap": snapshot.self_perception_gap,
            "empathy_vs_apathy": snapshot.empathy_vs_apathy,
        },
    }
    return json.dumps(data, indent=2)


async def extract_persona_for_user(user_id: UUID, target_date: date | None = None) -> PersonaSnapshot | None:
    """
    Main extraction entry point.
    1. Fetch user messages from the last 3 days
    2. Load previous snapshot
    3. Call LLM for structured persona update
    4. Validate with Pydantic, persist snapshot + facts
    5. Generate embedding and store
    """
    if target_date is None:
        target_date = date.today()

    since = target_date - timedelta(days=3)

    async with AsyncSessionLocal() as db:
        messages = await _get_recent_messages(db, user_id, since)
        if not messages:
            logger.info(f"No messages found for user {user_id} since {since}. Skipping.")
            return None

        prev_snapshot = await _get_latest_snapshot(db, user_id)

        # ── Guard: skip if no new messages since last extraction ──────────
        # This prevents the feedback loop where re-running extraction on
        # the same messages causes scores to drift upward each version.
        if prev_snapshot is not None:
            latest_msg_time = max(m.created_at for m in messages)
            if latest_msg_time <= prev_snapshot.created_at:
                logger.info(
                    f"No new messages for user {user_id} since last extraction "
                    f"(v{prev_snapshot.version} at {prev_snapshot.created_at}). "
                    f"Returning existing snapshot."
                )
                return prev_snapshot

        current_day = await _get_user_day(db, user_id)
        existing_entities = await _get_user_entities(db, user_id)

        prev_json = _snapshot_to_json(prev_snapshot)
        prev_version = prev_snapshot.version if prev_snapshot else 0

        transcript = "\n".join(
            [f"[{m.created_at.isoformat()}] (msg_id:{m.id}) {m.content}" for m in messages]
        )

        user_prompt = EXTRACTION_USER_PROMPT.format(
            version=prev_version,
            previous_persona=prev_json,
            current_day=current_day,
            new_messages=transcript,
            previous_entities=_entities_to_json(existing_entities),
        )

        llm = get_llm_client()
        llm_messages = [
            LLMMessage("system", EXTRACTION_SYSTEM_PROMPT),
            LLMMessage("user", user_prompt),
        ]

        try:
            raw = await llm.structured_extraction(llm_messages, temperature=0.2)
            persona_data = PersonaExtractionResult.model_validate(raw)
        except Exception as exc:
            logger.error(f"Persona extraction failed for user {user_id}: {exc}")
            return None

        # Persist snapshot
        new_version = prev_version + 1
        bf = persona_data.big_five
        cs = persona_data.communication_style
        v = persona_data.values
        r = persona_data.relationship
        rel = persona_data.religious_profile
        prev_rel_affiliation = prev_snapshot.religion_affiliation if prev_snapshot else None
        prev_rel_observance = prev_snapshot.religion_observance_level if prev_snapshot else None
        prev_rel_partner_req = prev_snapshot.religion_partner_requirement if prev_snapshot else None

        # Preserve previously inferred religion fields when the current extraction
        # does not provide new evidence and returns nulls.
        religion_affiliation = (rel.affiliation if rel and rel.affiliation else prev_rel_affiliation)
        religion_observance_level = (
            rel.observance_level if rel and rel.observance_level else prev_rel_observance
        )
        religion_partner_requirement = (
            rel.partner_requirement if rel and rel.partner_requirement else prev_rel_partner_req
        )

        snapshot = PersonaSnapshot(
            user_id=user_id,
            snapshot_date=target_date,
            version=new_version,
            overall_confidence=persona_data.overall_confidence,
            openness=bf.openness.score,
            openness_confidence=bf.openness.confidence,
            conscientiousness=bf.conscientiousness.score,
            conscientiousness_confidence=bf.conscientiousness.confidence,
            extraversion=bf.extraversion.score,
            extraversion_confidence=bf.extraversion.confidence,
            agreeableness=bf.agreeableness.score,
            agreeableness_confidence=bf.agreeableness.confidence,
            neuroticism=bf.neuroticism.score,
            neuroticism_confidence=bf.neuroticism.confidence,
            mbti_label=persona_data.mbti_derived,
            comm_directness=cs.directness,
            comm_humor=cs.humor,
            comm_formality=cs.formality,
            comm_empathy=cs.empathy,
            val_family=v.family,
            val_career=v.career,
            val_adventure=v.adventure,
            val_spirituality=v.spirituality,
            val_creativity=v.creativity,
            val_stability=v.stability,
            attachment_style=r.attachment_style,
            conflict_style=r.conflict_style,
            relationship_pace=r.pace_preference,
            religion_affiliation=religion_affiliation,
            religion_observance_level=religion_observance_level,
            religion_partner_requirement=religion_partner_requirement,
            dealbreakers=r.dealbreakers,
            must_haves=r.must_haves,
            consistency_flags=[f.model_dump() for f in persona_data.consistency_flags],
        )
        # ── Financial character scores ────────────────────────────────────────
        fin = persona_data.financial
        if fin is not None:
            snapshot.fin_scarcity_response = fin.scarcity_response
            snapshot.fin_wealth_vision = fin.wealth_vision
            snapshot.fin_risk_tolerance = fin.risk_tolerance

        # ── Self-perception scores ────────────────────────────────────────────
        sp = persona_data.self_perception
        if sp is not None:
            snapshot.self_perception_gap = sp.self_perception_gap
            snapshot.empathy_vs_apathy = sp.empathy_vs_apathy
        # ── Authenticity scores ──────────────────────────────────────────────
        auth = persona_data.authenticity
        if auth is not None:
            snapshot.social_desirability_score = auth.social_desirability
            snapshot.specificity_score = auth.specificity
            snapshot.self_awareness_score = auth.self_awareness
            snapshot.consistency_score_llm = auth.consistency
            # Composite authenticity = weighted average of sub-scores
            snapshot.authenticity_score = round(
                0.30 * auth.social_desirability
                + 0.25 * auth.specificity
                + 0.25 * auth.self_awareness
                + 0.20 * auth.consistency,
                4,
            )
            # Penalise overall_confidence when authenticity is low
            # e.g. authenticity 0.4 → multiplier 0.7 (scales linearly from 0.5 at 0.0 to 1.0 at 1.0)
            auth_multiplier = 0.5 + 0.5 * snapshot.authenticity_score
            snapshot.overall_confidence = round(
                snapshot.overall_confidence * auth_multiplier, 4
            )

        db.add(snapshot)
        await db.flush()  # get snapshot.id

        # Generate embedding via local LM Studio (bge-small-en-v1.5)
        embedding_client = get_embedding_client()
        if embedding_client is not None:
            try:
                fin_part = ""
                if fin is not None:
                    fin_part = (
                        f" fin_scarcity={fin.scarcity_response:.2f}"
                        f" fin_wealth_vision={fin.wealth_vision:.2f}"
                        f" fin_risk={fin.risk_tolerance:.2f}"
                    )
                sp_part = ""
                if sp is not None:
                    sp_part = (
                        f" self_perception_gap={sp.self_perception_gap:.2f}"
                        f" empathy_vs_apathy={sp.empathy_vs_apathy:.2f}"
                    )
                summary_text = (
                    f"openness={bf.openness.score:.2f} conscientiousness={bf.conscientiousness.score:.2f} "
                    f"extraversion={bf.extraversion.score:.2f} agreeableness={bf.agreeableness.score:.2f} "
                    f"neuroticism={bf.neuroticism.score:.2f} "
                    f"family={v.family:.2f} career={v.career:.2f} adventure={v.adventure:.2f} "
                    f"empathy={cs.empathy:.2f} humor={cs.humor:.2f} "
                    f"attachment={r.attachment_style} conflict={r.conflict_style} "
                    f"must_haves={' '.join(r.must_haves)} dealbreakers={' '.join(r.dealbreakers)}"
                    f"{fin_part}{sp_part}"
                )
                snapshot.embedding = await embedding_client.embed_text(summary_text)
            except Exception as exc:
                logger.warning(f"Embedding skipped for user {user_id}: {exc}")

        # Persist persona facts with evidence
        evidence_ids = [str(m.id) for m in messages]

        # ── Numeric traits ──────────────────────────────────────────────────
        numeric_facts = [
            ("big_five",           "openness",          bf.openness.score,          bf.openness.confidence),
            ("big_five",           "conscientiousness", bf.conscientiousness.score,  bf.conscientiousness.confidence),
            ("big_five",           "extraversion",      bf.extraversion.score,       bf.extraversion.confidence),
            ("big_five",           "agreeableness",     bf.agreeableness.score,      bf.agreeableness.confidence),
            ("big_five",           "neuroticism",       bf.neuroticism.score,        bf.neuroticism.confidence),
            ("values",             "family",            v.family,                    None),
            ("values",             "career",            v.career,                    None),
            ("values",             "adventure",         v.adventure,                 None),
            ("values",             "spirituality",      v.spirituality,              None),
            ("values",             "creativity",        v.creativity,                None),
            ("values",             "stability",         v.stability,                 None),
            ("communication_style", "directness",       cs.directness,               None),
            ("communication_style", "humor",            cs.humor,                    None),
            ("communication_style", "formality",        cs.formality,                None),
            ("communication_style", "empathy",          cs.empathy,                  None),
        ]
        for category, key, score, confidence in numeric_facts:
            db.add(PersonaFact(
                user_id=user_id,
                snapshot_id=snapshot.id,
                category=category,
                key=key,
                value=str(round(float(score), 4)),
                confidence=float(confidence) if confidence is not None else 0.0,
                evidence_message_ids=evidence_ids,
            ))

        # ── String / categorical traits ──────────────────────────────────────
        string_facts = [
            ("identity",      "mbti_label",        persona_data.mbti_derived   or ""),
            ("relationship",  "attachment_style",  r.attachment_style          or ""),
            ("relationship",  "conflict_style",    r.conflict_style            or ""),
            ("relationship",  "pace_preference",   r.pace_preference           or ""),
        ]
        for category, key, value in string_facts:
            if value:
                db.add(PersonaFact(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    category=category,
                    key=key,
                    value=value,
                    confidence=0.0,
                    evidence_message_ids=evidence_ids,
                ))

        # ── List traits (stored as JSON strings) ─────────────────────────────
        list_facts = [
            ("relationship", "dealbreakers", r.dealbreakers or []),
            ("relationship", "must_haves",   r.must_haves   or []),
        ]
        for category, key, lst in list_facts:
            if lst:
                db.add(PersonaFact(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    category=category,
                    key=key,
                    value=json.dumps(lst),
                    confidence=0.0,
                    evidence_message_ids=evidence_ids,
                ))

        # ── Consistency flags ────────────────────────────────────────────────
        if persona_data.consistency_flags:
            db.add(PersonaFact(
                user_id=user_id,
                snapshot_id=snapshot.id,
                category="meta",
                key="consistency_flags",
                value=json.dumps([f.model_dump() for f in persona_data.consistency_flags]),
                confidence=0.0,
                evidence_message_ids=evidence_ids,
            ))

        # ── Financial character facts ────────────────────────────────────────
        if fin is not None:
            for key, score in [
                ("scarcity_response", fin.scarcity_response),
                ("wealth_vision",     fin.wealth_vision),
                ("risk_tolerance",    fin.risk_tolerance),
            ]:
                db.add(PersonaFact(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    category="financial",
                    key=key,
                    value=str(round(float(score), 4)),
                    confidence=0.0,
                    evidence_message_ids=evidence_ids,
                ))

        # ── Self-perception facts ─────────────────────────────────────────────
        if sp is not None:
            for key, score in [
                ("self_perception_gap", sp.self_perception_gap),
                ("empathy_vs_apathy",  sp.empathy_vs_apathy),
            ]:
                db.add(PersonaFact(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    category="self_perception",
                    key=key,
                    value=str(round(float(score), 4)),
                    confidence=0.0,
                    evidence_message_ids=evidence_ids,
                ))

        # ── Authenticity facts ───────────────────────────────────────────────
        if auth is not None:
            auth_facts = [
                ("authenticity", "social_desirability", auth.social_desirability),
                ("authenticity", "specificity",         auth.specificity),
                ("authenticity", "self_awareness",      auth.self_awareness),
                ("authenticity", "consistency",          auth.consistency),
            ]
            for category, key, score in auth_facts:
                db.add(PersonaFact(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    category=category,
                    key=key,
                    value=str(round(float(score), 4)),
                    confidence=0.0,
                    evidence_message_ids=evidence_ids,
                ))
            if auth.flags:
                db.add(PersonaFact(
                    user_id=user_id,
                    snapshot_id=snapshot.id,
                    category="authenticity",
                    key="flags",
                    value=json.dumps(auth.flags),
                    confidence=0.0,
                    evidence_message_ids=evidence_ids,
                ))

        # ── Persist extracted entities ────────────────────────────────────────
        if persona_data.entities:
            existing_labels = {e.label.lower() for e in existing_entities}
            for ent in persona_data.entities:
                if ent.label.lower() not in existing_labels:
                    db.add(UserEntity(
                        user_id=user_id,
                        label=ent.label,
                        relationship=ent.relationship,
                        emotional_weight=ent.emotional_weight,
                        context_note=ent.context_note,
                        day_extracted=current_day,
                    ))
                    existing_labels.add(ent.label.lower())

        await db.commit()
        await db.refresh(snapshot)
        logger.info(f"Persona v{new_version} saved for user {user_id} (confidence={persona_data.overall_confidence:.2f})")
        return snapshot

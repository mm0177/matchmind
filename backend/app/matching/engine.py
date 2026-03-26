"""
Matching Engine — runs daily for all matchable users.

Hybrid pipeline:
  Stage 1: Hard filters + embedding cosine similarity (fast, free, narrows candidates)
  Stage 2: LLM deep compatibility analysis (nuanced, relationship-science-aware)
"""
import logging
from datetime import date
from uuid import UUID

import numpy as np
from sqlalchemy import select, and_, or_

from app.db.database import AsyncSessionLocal
from app.auth.models import User
from app.persona.models import PersonaSnapshot
from app.matching.models import MatchRun, Match
from app.matching.filters import apply_hard_filters
from app.matching.llm_scorer import llm_score_pair
from app.config import settings

logger = logging.getLogger(__name__)

# Minimum embedding similarity to pass to Stage 2 (LLM scoring)
_STAGE1_EMBEDDING_THRESHOLD = 0.40
# Maximum matches to create per user per run
_MAX_MATCHES_PER_USER = 5


# ─── Compatibility sub-scores ─────────────────────────────────────────────────

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Cosine similarity between two embedding vectors, mapped to [0, 1].
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.5
    raw = float(np.dot(a, b) / (norm_a * norm_b))
    return round((raw + 1.0) / 2.0, 4)


# ─── Main daily matching job ──────────────────────────────────────────────────

async def run_daily_matching() -> MatchRun:
    """
    Hybrid matching pipeline:
      1. Find matchable users with sufficient persona confidence
      2. Stage 1: Hard filters + embedding cosine → candidate pairs
      3. Stage 2: LLM deep analysis for each candidate pair
      4. Store matches above threshold, cap per user
    """
    async with AsyncSessionLocal() as db:
        # Fetch matchable, verified users
        users_result = await db.execute(
            select(User).where(
                and_(User.is_matchable == True, User.is_verified == True, User.is_active == True)
            )
        )
        matchable_users = list(users_result.scalars().all())

        # Get their latest persona snapshot with sufficient confidence
        user_personas: dict[str, tuple[User, PersonaSnapshot]] = {}
        for user in matchable_users:
            snap_result = await db.execute(
                select(PersonaSnapshot)
                .where(PersonaSnapshot.user_id == user.id)
                .order_by(PersonaSnapshot.version.desc())
                .limit(1)
            )
            snap = snap_result.scalar_one_or_none()
            if snap and snap.overall_confidence >= settings.MIN_PERSONA_CONFIDENCE:
                user_personas[str(user.id)] = (user, snap)

        logger.info(f"Running matching for {len(user_personas)} eligible users.")

        match_run = MatchRun(
            run_date=date.today(),
            total_users=len(user_personas),
            algorithm_ver="v2.0",
        )
        db.add(match_run)
        await db.flush()

        # Load existing match pairs so we skip them
        existing_result = await db.execute(select(Match))
        existing_pairs: set[frozenset] = set()
        for m in existing_result.scalars().all():
            existing_pairs.add(frozenset([str(m.user_a_id), str(m.user_b_id)]))

        user_ids = list(user_personas.keys())

        # ── Stage 1: Hard filters + embedding cosine ──────────────────────
        stage1_candidates: list[tuple[str, str, float | None]] = []

        for i in range(len(user_ids)):
            for j in range(i + 1, len(user_ids)):
                uid_a, uid_b = user_ids[i], user_ids[j]

                # Skip already-matched pairs
                if frozenset([uid_a, uid_b]) in existing_pairs:
                    continue

                user_a, persona_a = user_personas[uid_a]
                user_b, persona_b = user_personas[uid_b]

                if not apply_hard_filters(user_a, persona_a, user_b, persona_b):
                    continue

                # Compute embedding similarity for pre-filtering
                has_embeddings = (
                    persona_a.embedding is not None and
                    persona_b.embedding is not None and
                    len(persona_a.embedding) > 0 and
                    len(persona_b.embedding) > 0
                )
                embed_sim = cosine_similarity(persona_a.embedding, persona_b.embedding) if has_embeddings else None

                # If we have embeddings, apply threshold; otherwise let LLM decide
                if embed_sim is not None and embed_sim < _STAGE1_EMBEDDING_THRESHOLD:
                    continue

                stage1_candidates.append((uid_a, uid_b, embed_sim))

        logger.info(f"Stage 1: {len(stage1_candidates)} candidate pairs passed filters.")

        # ── Stage 2: LLM deep analysis ────────────────────────────────────
        # Track match count per user to enforce cap
        user_match_count: dict[str, int] = {uid: 0 for uid in user_ids}
        matches_created = 0

        for uid_a, uid_b, embed_sim in stage1_candidates:
            # Enforce per-user cap
            if user_match_count[uid_a] >= _MAX_MATCHES_PER_USER:
                continue
            if user_match_count[uid_b] >= _MAX_MATCHES_PER_USER:
                continue

            user_a, persona_a = user_personas[uid_a]
            user_b, persona_b = user_personas[uid_b]

            # Call LLM for deep scoring
            llm_result = await llm_score_pair(persona_a, persona_b, embed_sim)

            if llm_result is None:
                logger.warning(f"LLM scoring failed for pair ({uid_a}, {uid_b}), skipping.")
                continue

            score = llm_result["overall_score"]

            # Authenticity penalty
            auth_a = persona_a.authenticity_score
            auth_b = persona_b.authenticity_score
            auth_penalty = 1.0
            if auth_a is not None and auth_a < 0.5:
                auth_penalty *= (0.5 + auth_a)
            if auth_b is not None and auth_b < 0.5:
                auth_penalty *= (0.5 + auth_b)
            penalized_score = round(score * auth_penalty, 4)

            if penalized_score >= settings.MIN_MATCH_SCORE:
                match = Match(
                    run_id=match_run.id,
                    user_a_id=user_a.id,
                    user_b_id=user_b.id,
                    score=penalized_score,
                    score_breakdown={
                        "llm_overall": score,
                        "auth_penalty": round(auth_penalty, 4),
                        "embedding_similarity": embed_sim,
                        "emotional": llm_result.get("emotional_compatibility"),
                        "intellectual": llm_result.get("intellectual_compatibility"),
                        "values": llm_result.get("values_alignment"),
                        "lifestyle": llm_result.get("lifestyle_compatibility"),
                        "communication": llm_result.get("communication_compatibility"),
                        "financial": llm_result.get("financial_compatibility"),
                        "conflict_handling": llm_result.get("conflict_handling"),
                        "long_term_stability": llm_result.get("long_term_stability"),
                        "strengths": llm_result.get("strengths", []),
                        "risks": llm_result.get("risks", []),
                        "analysis_summary": llm_result.get("analysis_summary", ""),
                    },
                    status="pending",
                )
                db.add(match)
                user_match_count[uid_a] += 1
                user_match_count[uid_b] += 1
                matches_created += 1

        match_run.total_matches = matches_created
        await db.commit()

        logger.info(f"Match run complete: {matches_created} matches created (v2.0 hybrid).")
        return match_run

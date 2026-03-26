"""
LLM-powered compatibility scoring.

Stage 2 of the hybrid matching pipeline:
  Stage 1 (hard filters + embedding cosine) narrows candidates cheaply.
  Stage 2 sends surviving pairs to the LLM for nuanced, relationship-science-aware analysis.

All scores/analysis are stored in DB only — never shown to the user.
"""

import json
import logging
from app.llm.base import LLMMessage
from app.llm.client import get_llm_client
from app.persona.models import PersonaSnapshot

logger = logging.getLogger(__name__)


def _persona_summary(p: PersonaSnapshot) -> str:
    """Build a concise text summary of a persona for the LLM prompt."""
    lines: list[str] = []

    # Big Five
    big5 = {
        "openness": p.openness,
        "conscientiousness": p.conscientiousness,
        "extraversion": p.extraversion,
        "agreeableness": p.agreeableness,
        "neuroticism": p.neuroticism,
    }
    big5_str = ", ".join(f"{k}={v:.2f}" for k, v in big5.items() if v is not None)
    if big5_str:
        lines.append(f"Big Five: {big5_str}")

    if p.mbti_label:
        lines.append(f"MBTI: {p.mbti_label}")

    # Communication
    comm = {
        "directness": p.comm_directness,
        "humor": p.comm_humor,
        "formality": p.comm_formality,
        "empathy": p.comm_empathy,
    }
    comm_str = ", ".join(f"{k}={v:.2f}" for k, v in comm.items() if v is not None)
    if comm_str:
        lines.append(f"Communication style: {comm_str}")

    # Values
    vals = {
        "family": p.val_family,
        "career": p.val_career,
        "adventure": p.val_adventure,
        "spirituality": p.val_spirituality,
        "creativity": p.val_creativity,
        "stability": p.val_stability,
    }
    vals_str = ", ".join(f"{k}={v:.2f}" for k, v in vals.items() if v is not None)
    if vals_str:
        lines.append(f"Values: {vals_str}")

    # Relationship
    if p.attachment_style:
        lines.append(f"Attachment style: {p.attachment_style}")
    if p.conflict_style:
        lines.append(f"Conflict style: {p.conflict_style}")
    if p.relationship_pace:
        lines.append(f"Relationship pace: {p.relationship_pace}")
    if p.religion_affiliation:
        lines.append(f"Religion affiliation: {p.religion_affiliation}")
    if p.religion_observance_level:
        lines.append(f"Religion observance level: {p.religion_observance_level}")
    if p.religion_partner_requirement:
        lines.append(f"Religion partner requirement: {p.religion_partner_requirement}")
    if p.dealbreakers:
        lines.append(f"Dealbreakers: {', '.join(p.dealbreakers)}")
    if p.must_haves:
        lines.append(f"Must-haves: {', '.join(p.must_haves)}")

    # Financial
    fin = {
        "scarcity_response": p.fin_scarcity_response,
        "wealth_vision": p.fin_wealth_vision,
        "risk_tolerance": p.fin_risk_tolerance,
    }
    fin_str = ", ".join(f"{k}={v:.2f}" for k, v in fin.items() if v is not None)
    if fin_str:
        lines.append(f"Financial attitudes: {fin_str}")

    # Self-perception
    sp = {
        "self_perception_gap": p.self_perception_gap,
        "empathy_vs_apathy": p.empathy_vs_apathy,
    }
    sp_str = ", ".join(f"{k}={v:.2f}" for k, v in sp.items() if v is not None)
    if sp_str:
        lines.append(f"Self-perception: {sp_str}")

    # Authenticity
    if p.authenticity_score is not None:
        lines.append(f"Authenticity score: {p.authenticity_score:.2f}")

    return "\n".join(lines)


_SYSTEM_PROMPT = """\
You are an expert relationship psychologist and compatibility analyst.
You will receive personality profiles of two people (Person A and Person B) extracted from their 10-day conversational journey. Each profile includes Big Five personality traits, communication style, core values, attachment style, conflict resolution style, financial attitudes, self-perception metrics, and authenticity scores.

Your task is to perform a DEEP compatibility analysis using real relationship science principles:

RELATIONSHIP SCIENCE RULES YOU MUST APPLY:
1. SIMILAR ≠ ALWAYS COMPATIBLE:
   - Two highly neurotic people amplify each other's anxiety spirals → penalize
   - Two conflict-avoidant people let issues fester → penalize
   - Two highly agreeable people may lack honest communication → slight concern
   
2. COMPLEMENTARY TRAITS CAN BE STRENGTHS:
   - Secure + Anxious attachment: secure partner can ground the anxious one → moderate-good
   - One organized (high C) + one creative (high O, low C): can balance each other → good if both flexible
   - One introvert + one extrovert: extrovert brings introvert into social world → good if respectful of boundaries
   
3. DEALBREAKER ASYMMETRY:
   - If A's dealbreaker directly conflicts with B's core trait/value → fatal, score very low
   - Must-have mismatches are softer but still significant
   
4. ATTACHMENT SCIENCE:
   - Secure + Secure = best long-term stability
   - Secure + Anxious = good if secure is patient
   - Secure + Avoidant = possible if avoidant is self-aware
   - Anxious + Avoidant = toxic pursuit-withdrawal cycle → very low score
   - Anxious + Anxious = emotional rollercoaster → low score
   - Avoidant + Avoidant = emotional desert → low score
   
5. FINANCIAL COMPATIBILITY:
   - Divergent risk tolerance → arguments about money (top predictor of divorce)
   - One scarcity-panic + one risk-seeker = major friction
   - Similar financial values matter MORE than similar income
   
6. COMMUNICATION COMPATIBILITY:
   - High empathy mismatch: one deeply empathetic + one apathetic = frustration
   - Directness mismatch: one very direct + one very indirect = miscommunication
   - Humor alignment matters for daily happiness
   
7. CONFLICT RESOLUTION:
   - Collaborative + Collaborative = best
   - Collaborative + Competitive = workable if competitive respects process
   - Avoidant + Avoidant = issues never get resolved → serious risk
   - Competitive + Competitive = power struggles
   
8. AUTHENTICITY FACTOR:
   - If either person has low authenticity (<0.4), their profile may be artificially inflated
   - Apply skepticism to their trait similarity — it may not reflect who they really are

OUTPUT FORMAT — respond with ONLY valid JSON, no markdown, no extra text:
{
  "overall_score": <float 0.0 to 1.0>,
  "emotional_compatibility": <float 0.0 to 1.0>,
  "intellectual_compatibility": <float 0.0 to 1.0>,
  "values_alignment": <float 0.0 to 1.0>,
  "lifestyle_compatibility": <float 0.0 to 1.0>,
  "communication_compatibility": <float 0.0 to 1.0>,
  "financial_compatibility": <float 0.0 to 1.0>,
  "conflict_handling": <float 0.0 to 1.0>,
  "long_term_stability": <float 0.0 to 1.0>,
  "strengths": ["<str>", "<str>", ...],
  "risks": ["<str>", "<str>", ...],
  "analysis_summary": "<2-3 sentence internal analysis note>"
}

CRITICAL RULES:
- Be HONEST. Do not inflate scores to be kind. Real relationship science matters.
- A pair with an anxious-avoidant attachment dynamic should score below 0.40 overall.
- Financial incompatibility alone can cap the overall score at 0.65 max.
- If BOTH have low authenticity (<0.4), cap overall score at 0.50.
- The overall_score is NOT a simple average of sub-scores. Weight them by relationship importance.
- Typical score distribution: most pairs should be 0.35-0.75. Scores above 0.85 should be rare and truly exceptional.
"""


async def llm_score_pair(
    persona_a: PersonaSnapshot,
    persona_b: PersonaSnapshot,
    embedding_sim: float | None = None,
) -> dict | None:
    """
    Send two persona profiles to the LLM for deep compatibility analysis.
    Returns the parsed JSON response, or None on failure.
    """
    summary_a = _persona_summary(persona_a)
    summary_b = _persona_summary(persona_b)

    user_prompt = f"PERSON A PROFILE:\n{summary_a}\n\nPERSON B PROFILE:\n{summary_b}"
    if embedding_sim is not None:
        user_prompt += f"\n\nEmbedding cosine similarity (holistic persona overlap): {embedding_sim:.4f}"

    messages = [
        LLMMessage("system", _SYSTEM_PROMPT),
        LLMMessage("user", user_prompt),
    ]

    try:
        llm = get_llm_client()
        result = await llm.structured_extraction(
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        # Validate required fields
        if "overall_score" not in result:
            logger.warning("LLM match scoring returned no overall_score")
            return None
        # Clamp score to valid range
        result["overall_score"] = max(0.0, min(1.0, float(result["overall_score"])))
        return result
    except Exception as e:
        logger.error(f"LLM match scoring failed: {e}")
        return None

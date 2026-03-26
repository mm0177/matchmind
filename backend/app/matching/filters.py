"""
Hard filters applied before scoring a pair.
Returns True if the pair is eligible for scoring.
"""
from datetime import date
from app.auth.models import User
from app.persona.models import PersonaSnapshot


def _age(user: User) -> int | None:
    """Return user's current age, or None if birth_date is not set."""
    if not user.birth_date:
        return None
    today = date.today()
    bd = user.birth_date
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))


def apply_hard_filters(
    user_a: User,
    persona_a: PersonaSnapshot,
    user_b: User,
    persona_b: PersonaSnapshot,
) -> bool:
    """
    Returns False if the pair should be excluded entirely.
    Checks:
      - Not the same user
      - Gender preference compatibility (if set)
      - Dealbreaker cross-match
    """
    """
    Returns False if the pair should be excluded from scoring.
    Checks:
    - Same user
    - Gender preference mismatch
    - Cross-dealbreaker conflict (if A's dealbreakers appear in B's must-haves and vice versa)
    """
    if user_a.id == user_b.id:
        return False

    # Gender preference filter
    if user_a.preferred_gender and user_b.gender:
        if user_a.preferred_gender.lower() not in (user_b.gender.lower(), "any", "all"):
            return False
    if user_b.preferred_gender and user_a.gender:
        if user_b.preferred_gender.lower() not in (user_a.gender.lower(), "any", "all"):
            return False

    # Geography filter (conditional):
    # - If BOTH users opted into long-distance, ignore location.
    # - Otherwise apply a locality check using available location granularity.
    if not (user_a.is_open_to_long_distance and user_b.is_open_to_long_distance):
        if user_a.location and user_b.location:
            parts_a = [p.strip().lower() for p in user_a.location.split(",")]
            parts_b = [p.strip().lower() for p in user_b.location.split(",")]
            state_a = parts_a[-1] if len(parts_a) >= 2 else parts_a[0]
            state_b = parts_b[-1] if len(parts_b) >= 2 else parts_b[0]
            if state_a != state_b:
                return False

    # Religion filter (conditional hard filter)
    req_a = (persona_a.religion_partner_requirement or "").strip().lower()
    req_b = (persona_b.religion_partner_requirement or "").strip().lower()
    aff_a = (persona_a.religion_affiliation or "").strip().lower()
    aff_b = (persona_b.religion_affiliation or "").strip().lower()

    if req_a == "strict_same" and aff_a and aff_b and aff_a != aff_b:
        return False
    if req_b == "strict_same" and aff_a and aff_b and aff_a != aff_b:
        return False

    # Age preference filter
    age_a = _age(user_a)
    age_b = _age(user_b)

    # A's age must fall within B's preferred range (if B specified one)
    if age_a is not None:
        if user_b.age_pref_min is not None and age_a < user_b.age_pref_min:
            return False
        if user_b.age_pref_max is not None and age_a > user_b.age_pref_max:
            return False

    # B's age must fall within A's preferred range (if A specified one)
    if age_b is not None:
        if user_a.age_pref_min is not None and age_b < user_a.age_pref_min:
            return False
        if user_a.age_pref_max is not None and age_b > user_a.age_pref_max:
            return False

    # Dealbreaker cross-check
    a_dealbreakers = set(d.lower() for d in (persona_a.dealbreakers or []))
    b_must_haves = set(m.lower() for m in (persona_b.must_haves or []))

    b_dealbreakers = set(d.lower() for d in (persona_b.dealbreakers or []))
    a_must_haves = set(m.lower() for m in (persona_a.must_haves or []))

    # If any of B's must-haves are A's dealbreakers, incompatible
    if a_dealbreakers & b_must_haves:
        return False
    if b_dealbreakers & a_must_haves:
        return False

    return True

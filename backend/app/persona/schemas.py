from typing import Optional
from pydantic import BaseModel, Field


class BigFiveTrait(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)


class BigFiveModel(BaseModel):
    openness: BigFiveTrait
    conscientiousness: BigFiveTrait
    extraversion: BigFiveTrait
    agreeableness: BigFiveTrait
    neuroticism: BigFiveTrait


class CommunicationStyle(BaseModel):
    directness: float = Field(ge=0.0, le=1.0)
    humor: float = Field(ge=0.0, le=1.0)
    formality: float = Field(ge=0.0, le=1.0)
    empathy: float = Field(ge=0.0, le=1.0)


class Values(BaseModel):
    family: float = Field(ge=0.0, le=1.0)
    career: float = Field(ge=0.0, le=1.0)
    adventure: float = Field(ge=0.0, le=1.0)
    spirituality: float = Field(ge=0.0, le=1.0)
    creativity: float = Field(ge=0.0, le=1.0)
    stability: float = Field(ge=0.0, le=1.0)


class RelationshipProfile(BaseModel):
    attachment_style: Optional[str] = None      # secure | anxious | avoidant
    conflict_style: Optional[str] = None        # collaborative | competitive | avoidant
    pace_preference: Optional[str] = None       # slow | moderate | fast
    dealbreakers: list[str] = []
    must_haves: list[str] = []


class ReligiousProfileModel(BaseModel):
    affiliation: Optional[str] = Field(
        default=None,
        description="Specific faith/denomination/philosophical stance (e.g. Hindu, Christian, Atheist)",
    )
    observance_level: Optional[str] = Field(
        default=None,
        description="cultural | moderate | strict | secular",
    )
    partner_requirement: Optional[str] = Field(
        default=None,
        description="strict_same | open_to_learning | irrelevant",
    )


class ConsistencyFlag(BaseModel):
    trait: str
    note: str
    messages: list[str] = []


class AuthenticityAnalysis(BaseModel):
    social_desirability: float = Field(ge=0.0, le=1.0, description="1.0 = no social desirability bias detected; 0.0 = heavy impression management")
    specificity: float = Field(ge=0.0, le=1.0, description="1.0 = rich specific examples; 0.0 = only vague generalities")
    self_awareness: float = Field(ge=0.0, le=1.0, description="1.0 = acknowledges flaws + nuance; 0.0 = one-dimensional self-portrayal")
    consistency: float = Field(ge=0.0, le=1.0, description="1.0 = fully consistent across days; 0.0 = contradicts previous answers")
    flags: list[str] = Field(default=[], description="Short strings flagging specific authenticity concerns")


class FinancialProfile(BaseModel):
    """Financial character — how the user relates to money, risk, and resources."""
    scarcity_response: float = Field(ge=0.0, le=1.0, description="0=panic/freeze, 0.5=shut_down/passivity, 1.0=strategize/adapt")
    wealth_vision: float = Field(ge=0.0, le=1.0, description="0=luxury/consumption, 0.5=freedom/retirement, 1.0=legacy/purpose")
    risk_tolerance: float = Field(ge=0.0, le=1.0, description="0=risk_averse (play not to lose), 1.0=risk_seeking (play to win)")


class SelfPerceptionProfile(BaseModel):
    """Self-perception and complex index — how accurately the user sees themselves."""
    self_perception_gap: float = Field(ge=0.0, le=1.0, description="0=strong inferiority complex, 0.5=balanced/realistic, 1.0=strong superiority complex")
    empathy_vs_apathy: float = Field(ge=0.0, le=1.0, description="0=apathetic/self-centered in conflicts, 1.0=deeply empathetic/others-centered")


class ExtractedEntity(BaseModel):
    """A person or relationship the user mentioned in their messages."""
    label: str = Field(description="Short descriptor, e.g. 'younger brother', 'college best friend', 'demanding boss'")
    relationship: str = Field(description="family | friend | colleague | ex_partner | other")
    emotional_weight: str = Field(default="medium", description="high | medium | low")
    context_note: Optional[str] = Field(default=None, description="Brief context from the chat about this person")


class PersonaExtractionResult(BaseModel):
    overall_confidence: float = Field(ge=0.0, le=1.0)
    big_five: BigFiveModel
    mbti_derived: Optional[str] = None
    communication_style: CommunicationStyle
    values: Values
    relationship: RelationshipProfile
    religious_profile: Optional[ReligiousProfileModel] = None
    consistency_flags: list[ConsistencyFlag] = []
    authenticity: Optional[AuthenticityAnalysis] = None
    financial: Optional[FinancialProfile] = None
    self_perception: Optional[SelfPerceptionProfile] = None
    entities: Optional[list[ExtractedEntity]] = None

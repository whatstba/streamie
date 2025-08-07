"""
Pydantic models for Mix Coordinator Agent and transition planning.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class TransitionType(str, Enum):
    """Types of DJ transitions"""

    SMOOTH_BLEND = "smooth_blend"
    QUICK_CUT = "quick_cut"
    EFFECTS_TRANSITION = "effects_transition"
    BEATMATCH_BLEND = "beatmatch_blend"
    SCRATCH_CUT = "scratch_cut"
    FADE_TO_SILENCE = "fade_to_silence"


class EnergyTrajectory(str, Enum):
    """Energy flow patterns for DJ sets"""

    BUILDING = "building"
    PEAK = "peak"
    COOLING_DOWN = "cooling_down"
    MAINTAINING = "maintaining"
    WAVE = "wave"


class EffectType(str, Enum):
    """Available transition effects"""

    FILTER_SWEEP = "filter_sweep"
    ECHO = "echo"
    REVERB = "reverb"
    DELAY = "delay"
    GATE = "gate"
    FLANGER = "flanger"
    EQ_SWEEP = "eq_sweep"
    SCRATCH = "scratch"


class EQAdjustment(BaseModel):
    """EQ adjustment parameters"""

    low: float = Field(default=0.0, ge=-1.0, le=1.0)
    mid: float = Field(default=0.0, ge=-1.0, le=1.0)
    high: float = Field(default=0.0, ge=-1.0, le=1.0)

    @field_validator("low", "mid", "high")
    def validate_range(cls, v):
        return max(-1.0, min(1.0, v))


class TransitionEffect(BaseModel):
    """Effect configuration for transitions"""

    type: EffectType
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    duration: Optional[float] = None  # If None, uses transition duration
    start_at: float = Field(default=0.0, ge=0.0)  # Offset from transition start
    parameters: Dict[str, float] = Field(default_factory=dict)
    reason: Optional[str] = None


class TransitionPoint(BaseModel):
    """Specific point in tracks for transitioning"""

    type: str  # e.g., "outro_start_to_intro_end"
    deck_a_time: float  # Time in seconds on source deck
    deck_b_time: float  # Time in seconds on target deck
    confidence: float = Field(ge=0.0, le=1.0)
    musical_reason: Optional[str] = None


class MixDecision(BaseModel):
    """Complete mix decision from coordinator"""

    action: TransitionType
    source_deck: str = Field(pattern="^[A-D]$")
    target_deck: str = Field(pattern="^[A-D]$")
    duration: float = Field(gt=0.0, le=60.0)  # Transition duration in seconds
    effects: List[TransitionEffect] = Field(default_factory=list)
    eq_adjustments: Dict[str, EQAdjustment] = Field(default_factory=dict)
    transition_point: Optional[TransitionPoint] = None
    tempo_adjust_curve: Optional[List[Dict[str, float]]] = (
        None  # Time-based tempo adjustments
    )
    crossfader_curve: Optional[List[Dict[str, float]]] = (
        None  # Time-based crossfader positions
    )
    decision_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("effects")
    def limit_effects(cls, v):
        # Limit to 2 effects max as per requirements
        return v[:2] if len(v) > 2 else v

    @field_validator("source_deck", "target_deck")
    def validate_deck_ids(cls, v):
        if v not in ["A", "B", "C", "D"]:
            raise ValueError(f"Invalid deck ID: {v}")
        return v


class TransitionState(BaseModel):
    """Current state of an active transition"""

    mix_decision: MixDecision
    started_at: datetime
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    is_active: bool = True
    effects_applied: List[str] = Field(default_factory=list)
    current_phase: str = "preparing"  # preparing, executing, completing


class TrackCompatibility(BaseModel):
    """Compatibility analysis between two tracks"""

    overall: float = Field(ge=0.0, le=1.0)
    bpm: float = Field(ge=0.0, le=1.0)
    key: float = Field(ge=0.0, le=1.0)
    energy: float = Field(ge=0.0, le=1.0)
    genre: float = Field(ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


class MixPlanRequest(BaseModel):
    """Request for mix coordination"""

    session_id: str
    energy_trajectory: Optional[EnergyTrajectory] = None
    manual_override: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None  # e.g., min/max transition time


class MixPlanResponse(BaseModel):
    """Response from mix coordinator"""

    mix_decision: Optional[MixDecision]
    compatibility: TrackCompatibility
    alternative_plans: List[MixDecision] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MixHistory(BaseModel):
    """Historical record of mix decisions"""

    session_id: str
    decisions: List[MixDecision] = Field(default_factory=list)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)

    def add_decision(self, decision: MixDecision):
        """Add a new decision to history"""
        self.decisions.append(decision)

    def get_recent_decisions(self, count: int = 5) -> List[MixDecision]:
        """Get most recent mix decisions"""
        return self.decisions[-count:] if self.decisions else []


class DJSessionState(BaseModel):
    """Complete DJ session state for LangGraph"""

    # Session identification
    session_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)

    # Energy and mood
    energy_trajectory: EnergyTrajectory = EnergyTrajectory.BUILDING
    genre_focus: Optional[str] = None

    # Current state
    current_mix_plan: Optional[MixDecision] = None
    transition_state: Optional[TransitionState] = None

    # History and learning
    mix_history: List[MixDecision] = Field(default_factory=list)

    # Performance tracking
    performance_metrics: Dict[str, float] = Field(default_factory=dict)

    # User preferences
    user_preferences: Dict[str, Any] = Field(default_factory=dict)

    # Control
    should_continue: bool = True
    auto_mix_enabled: bool = True

    # Analysis cache (filepath -> analysis results)
    analysis_cache: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

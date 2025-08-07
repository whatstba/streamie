"""
Effect Models - Data structures for tracking active effects and their states.
"""

from datetime import datetime
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
import uuid

from models.mix_models import EffectType


from enum import Enum


class AutomationCurve(str, Enum):
    """Types of parameter automation curves"""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    S_CURVE = "s_curve"
    LOGARITHMIC = "logarithmic"


class EffectParameter(BaseModel):
    """Individual effect parameter with metadata"""

    name: str
    value: float
    min_value: float = 0.0
    max_value: float = 1.0
    unit: Optional[str] = None  # Hz, ms, %, etc.
    automation_enabled: bool = False


class ActiveEffect(BaseModel):
    """Represents an active effect instance on a deck"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    deck_id: str = Field(pattern="^[A-D]$")
    effect_type: EffectType
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # seconds, None means infinite
    intensity: float = Field(ge=0.0, le=1.0, default=0.5)

    # Effect-specific parameters
    parameters: Dict[str, float] = Field(default_factory=dict)
    initial_parameters: Dict[str, float] = Field(default_factory=dict)
    target_parameters: Optional[Dict[str, float]] = None

    # Automation settings
    automation_curve: AutomationCurve = AutomationCurve.LINEAR
    automation_active: bool = True

    # State tracking
    is_active: bool = True
    is_bypassed: bool = False

    # Transition context (if part of a mix transition)
    transition_id: Optional[str] = None

    def get_elapsed_time(self) -> float:
        """Get elapsed time since effect started"""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def get_remaining_time(self) -> Optional[float]:
        """Get remaining time for effect"""
        if self.duration is None:
            return None
        elapsed = self.get_elapsed_time()
        return max(0, self.duration - elapsed)

    def get_progress(self) -> float:
        """Get effect progress (0-1)"""
        if self.duration is None or self.duration == 0:
            return 0.0
        return min(1.0, self.get_elapsed_time() / self.duration)


class EffectState(BaseModel):
    """Current state snapshot of an active effect"""

    effect_id: str
    deck_id: str
    effect_type: EffectType
    current_parameters: Dict[str, float]
    elapsed_time: float
    remaining_time: Optional[float]
    automation_progress: float = Field(ge=0.0, le=1.0)
    is_active: bool
    is_bypassed: bool
    intensity: float

    # Performance metrics
    cpu_usage: Optional[float] = None  # For future audio processing

    @classmethod
    def from_active_effect(cls, effect: ActiveEffect) -> "EffectState":
        """Create state snapshot from active effect"""
        return cls(
            effect_id=effect.id,
            deck_id=effect.deck_id,
            effect_type=effect.effect_type,
            current_parameters=effect.parameters.copy(),
            elapsed_time=effect.get_elapsed_time(),
            remaining_time=effect.get_remaining_time(),
            automation_progress=effect.get_progress(),
            is_active=effect.is_active,
            is_bypassed=effect.is_bypassed,
            intensity=effect.intensity,
        )


class EffectPreset(BaseModel):
    """Predefined effect configuration"""

    name: str
    effect_type: EffectType
    description: Optional[str] = None
    intensity: float = 0.5
    parameters: Dict[str, float] = Field(default_factory=dict)
    duration: Optional[float] = None
    automation_curve: AutomationCurve = AutomationCurve.LINEAR

    # Use case hints
    genre_hints: List[str] = Field(default_factory=list)
    energy_hints: List[str] = Field(default_factory=list)  # building, peak, etc.
    bpm_range: Optional[tuple[float, float]] = None


class DeckEffectChain(BaseModel):
    """All effects currently active on a deck"""

    deck_id: str = Field(pattern="^[A-D]$")
    effects: List[ActiveEffect] = Field(default_factory=list)
    bypass_all: bool = False

    def add_effect(self, effect: ActiveEffect) -> None:
        """Add effect to chain"""
        self.effects.append(effect)

    def remove_effect(self, effect_id: str) -> bool:
        """Remove effect from chain"""
        initial_count = len(self.effects)
        self.effects = [e for e in self.effects if e.id != effect_id]
        return len(self.effects) < initial_count

    def get_active_effects(self) -> List[ActiveEffect]:
        """Get only active (non-bypassed) effects"""
        if self.bypass_all:
            return []
        return [e for e in self.effects if e.is_active and not e.is_bypassed]

    def clear_inactive(self) -> int:
        """Remove inactive effects and return count removed"""
        initial_count = len(self.effects)
        self.effects = [e for e in self.effects if e.is_active]
        return initial_count - len(self.effects)


class EffectEvent(BaseModel):
    """Event log entry for effect lifecycle tracking"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    effect_id: str
    deck_id: str
    event_type: str  # started, updated, stopped, bypassed, resumed
    parameters: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

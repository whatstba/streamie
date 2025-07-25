"""
DJ Effect Types - Standardized effect definitions for the DJ system
"""
from enum import Enum
from typing import Dict, Any, Optional


class DJEffectType(Enum):
    """Supported DJ transition effects"""
    FILTER_SWEEP = "filter_sweep"  # Low-pass filter sweep
    ECHO = "echo"                  # Delay with feedback
    REVERB = "reverb"              # Room simulation
    DELAY = "delay"                # Long delay effect
    GATE = "gate"                  # Rhythmic volume cuts
    SCRATCH = "scratch"            # DJ scratch effect
    FLANGER = "flanger"            # Short delay with LFO
    EQ_SWEEP = "eq_sweep"          # Sweeping EQ boost
    
    # Legacy mapping
    FILTER = "filter"              # Maps to FILTER_SWEEP


# Effect descriptions for AI prompts
EFFECT_DESCRIPTIONS = {
    DJEffectType.FILTER_SWEEP: "Low-pass filter that sweeps from low to high frequencies",
    DJEffectType.ECHO: "Echo/delay effect with feedback (250ms default)",
    DJEffectType.REVERB: "Room reverb simulation for spacious sound",
    DJEffectType.DELAY: "Long delay effect (500ms default) for rhythmic echoes",
    DJEffectType.GATE: "Rhythmic volume cuts synchronized to beat",
    DJEffectType.SCRATCH: "DJ scratch effect with pitch shifting",
    DJEffectType.FLANGER: "Flanging effect with LFO modulation",
    DJEffectType.EQ_SWEEP: "Sweeping EQ boost across frequency spectrum",
}

# Effect intensity recommendations
EFFECT_INTENSITY_GUIDE = {
    DJEffectType.FILTER_SWEEP: {"min": 0.2, "max": 0.8, "recommended": 0.5},
    DJEffectType.ECHO: {"min": 0.2, "max": 0.7, "recommended": 0.4},
    DJEffectType.REVERB: {"min": 0.2, "max": 0.9, "recommended": 0.5},
    DJEffectType.DELAY: {"min": 0.2, "max": 0.7, "recommended": 0.4},
    DJEffectType.GATE: {"min": 0.3, "max": 0.9, "recommended": 0.6},
    DJEffectType.SCRATCH: {"min": 0.2, "max": 0.8, "recommended": 0.5},
    DJEffectType.FLANGER: {"min": 0.2, "max": 0.8, "recommended": 0.5},
    DJEffectType.EQ_SWEEP: {"min": 0.2, "max": 0.8, "recommended": 0.5},
}


def validate_effect_type(effect_type: str) -> Optional[DJEffectType]:
    """Validate and normalize effect type string"""
    if not effect_type:
        return None
        
    # Normalize the string
    normalized = effect_type.lower().strip()
    
    # Handle legacy "filter" -> "filter_sweep"
    if normalized == "filter":
        return DJEffectType.FILTER_SWEEP
        
    # Try to match enum
    for effect in DJEffectType:
        if effect.value == normalized:
            return effect
            
    return None


def get_effect_list_for_prompt() -> str:
    """Get formatted effect list for AI prompts"""
    lines = ["Available DJ transition effects:"]
    for effect in DJEffectType:
        if effect == DJEffectType.FILTER:  # Skip legacy
            continue
        desc = EFFECT_DESCRIPTIONS.get(effect, "")
        guide = EFFECT_INTENSITY_GUIDE.get(effect, {})
        rec_intensity = guide.get("recommended", 0.5)
        lines.append(f"- {effect.value}: {desc} (recommended intensity: {rec_intensity})")
    return "\n".join(lines)
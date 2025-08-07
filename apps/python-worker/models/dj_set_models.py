"""
DJ Set Models - Data structures for pre-planned DJ sets with transitions.
"""

from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from utils.dj_llm import TransitionEffect


class DJSetTrack(BaseModel):
    """A track in a DJ set with timing and mixing information"""

    order: int = Field(description="Position in the set (1-based)")
    filepath: str = Field(description="Path to the audio file")
    deck: str = Field(description="Target deck: A, B, C, or D")
    start_time: float = Field(description="When to start playing in set time (seconds)")
    end_time: float = Field(description="When to transition out (seconds)")
    fade_in_time: float = Field(description="When to start fading in (seconds)")
    fade_out_time: float = Field(description="When to start fading out (seconds)")

    # Track metadata
    title: Optional[str] = None
    artist: Optional[str] = None
    bpm: float = Field(description="Beats per minute")
    key: Optional[str] = Field(description="Musical key")
    energy_level: float = Field(description="Energy level 0-1", ge=0, le=1)

    # Mixing information
    mixing_note: str = Field(description="How to mix this track")
    tempo_adjust: float = Field(default=0.0, description="Tempo adjustment -0.5 to 0.5")
    gain_adjust: float = Field(default=1.0, description="Gain adjustment")

    # EQ settings for this track
    eq_low: float = Field(default=0.0, description="Low EQ adjustment")
    eq_mid: float = Field(default=0.0, description="Mid EQ adjustment")
    eq_high: float = Field(default=0.0, description="High EQ adjustment")
    
    # Hot cue information
    hot_cue_in_offset: float = Field(default=0.0, description="Offset in seconds to start of hot cue in point")
    hot_cue_out_offset: float = Field(default=0.0, description="Offset in seconds to hot cue out point")


class DJSetTransition(BaseModel):
    """A transition between two tracks in a DJ set"""

    from_track_order: int = Field(description="Source track order number")
    to_track_order: int = Field(description="Target track order number")
    from_deck: str = Field(description="Source deck")
    to_deck: str = Field(description="Target deck")

    # Timing
    start_time: float = Field(
        description="When transition starts (set time in seconds)"
    )
    duration: float = Field(description="Transition duration in seconds")

    # Transition details
    type: str = Field(
        description="Transition type: smooth_blend, energy_shift, creative_cut, breakdown"
    )
    effects: List[TransitionEffect] = Field(
        description="Effects to apply during transition"
    )
    crossfade_curve: str = Field(
        default="s-curve", description="Crossfade curve: linear, s-curve, exponential"
    )

    # Mixing parameters
    technique_notes: str = Field(description="Professional mixing technique to use")
    risk_level: str = Field(description="Risk level: safe, moderate, adventurous")
    compatibility_score: float = Field(
        description="Track compatibility 0-1", ge=0, le=1
    )

    # Cue points (as percentages of track duration)
    outro_cue: float = Field(description="Outro cue point for from_track (0-1)")
    intro_cue: float = Field(description="Intro cue point for to_track (0-1)")


class DJSet(BaseModel):
    """A complete DJ set with all tracks and transitions pre-planned"""

    id: str = Field(description="Unique identifier for the set")
    name: str = Field(description="Name of the DJ set")
    vibe_description: str = Field(description="Original vibe request")

    # Set metadata
    total_duration: float = Field(description="Total duration in seconds")
    track_count: int = Field(description="Number of tracks in the set")
    energy_pattern: str = Field(
        description="Energy progression: steady, building, wave"
    )

    # Set content
    tracks: List[DJSetTrack] = Field(description="All tracks in order with timing")
    transitions: List[DJSetTransition] = Field(
        description="All transitions between tracks"
    )

    # Analysis data
    energy_graph: List[float] = Field(
        description="Energy levels throughout the set (0-1)"
    )
    key_moments: List[Dict[str, str]] = Field(description="Key moments in the set")
    mixing_style: str = Field(description="Overall mixing approach")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    ai_insights: Optional[Dict] = Field(
        default=None, description="AI-generated insights about the set"
    )


class DJSetPlaybackState(BaseModel):
    """Current playback state of a DJ set"""

    set_id: str
    is_playing: bool = False
    is_paused: bool = False

    # Timing
    elapsed_time: float = Field(description="Elapsed time since set start (seconds)")
    current_track_order: int = Field(description="Currently playing track order number")
    next_track_order: Optional[int] = Field(description="Next track to play")

    # Deck states
    active_decks: List[str] = Field(description="Currently active decks")
    primary_deck: str = Field(description="Primary deck (loudest)")

    # Transition state
    in_transition: bool = False
    transition_progress: float = Field(
        default=0.0, description="Transition progress 0-1"
    )
    next_transition_in: Optional[float] = Field(
        description="Seconds until next transition"
    )

    # Audio state
    master_volume: float = Field(default=1.0)
    crossfader_position: float = Field(
        default=0.0, description="Crossfader position -1 to 1"
    )

    # Timestamps
    started_at: Optional[datetime] = None
    last_update: datetime = Field(default_factory=datetime.now)
    
    # Backend timing reference (for accurate elapsed time tracking)
    backend_start_time: Optional[float] = None

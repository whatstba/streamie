"""
DJ LLM Service - Intelligent DJ personas for music curation and mixing.
"""

from typing import List, Dict, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import logging
from functools import lru_cache
import json

logger = logging.getLogger("DJLLMService")
logger.setLevel(logging.DEBUG)


# Pydantic models for structured outputs
class VibeAnalysis(BaseModel):
    """Analysis of user's vibe request"""

    energy_level: float = Field(description="Target energy level 0-1", ge=0, le=1)
    energy_progression: str = Field(
        description="Energy pattern: steady, building, cooling, wave"
    )
    mood_keywords: List[str] = Field(description="Key mood descriptors")
    genre_preferences: List[str] = Field(
        description="Suggested genres that match the vibe"
    )
    bpm_range: Dict[str, float] = Field(description="Suggested BPM range {min, max}")
    mixing_style: str = Field(
        description="Suggested mixing approach: smooth, aggressive, creative"
    )


class TrackEvaluation(BaseModel):
    """Evaluation of a track for playlist inclusion"""

    score: float = Field(description="Suitability score 0-1", ge=0, le=1)
    reasoning: str = Field(description="Why this track fits or doesn't fit")
    energy_match: float = Field(
        description="How well energy matches vibe 0-1", ge=0, le=1
    )
    suggested_position: Optional[int] = Field(
        description="Suggested position in playlist (1-based)"
    )
    mixing_notes: str = Field(description="How to mix this track")


class TransitionEffect(BaseModel):
    """Individual transition effect with required fields"""
    type: str = Field(description="Effect type: filter, echo, scratch")
    start_at: float = Field(description="Start time in seconds from transition start", ge=0)
    duration: float = Field(description="Effect duration in seconds", ge=0.1)
    intensity: float = Field(description="Effect intensity 0-1", ge=0, le=1)


class TransitionPlan(BaseModel):
    """Detailed transition plan between two tracks"""

    compatibility_score: float = Field(
        description="Overall compatibility 0-1", ge=0, le=1
    )
    transition_type: str = Field(
        description="Type: smooth_blend, energy_shift, creative_cut, breakdown"
    )
    effects: List[TransitionEffect] = Field(
        description="List of effects with timing and parameters"
    )
    crossfade_duration: float = Field(
        description="Suggested crossfade time in seconds", ge=1, le=10
    )
    cue_points: Dict[str, float] = Field(
        description="Suggested cue points {outro_start, intro_start}"
    )
    technique_notes: str = Field(description="Professional mixing technique to use")
    risk_level: str = Field(description="Risk level: safe, moderate, adventurous")


class PlaylistFinalization(BaseModel):
    """Finalized playlist with professional ordering and notes"""

    tracks: List[Dict[str, Any]] = Field(
        description="Ordered list of tracks with mixing notes"
    )
    overall_flow: str = Field(description="Description of the energy and mood journey")
    key_moments: List[Dict[str, str]] = Field(
        description="Key moments in the set with timestamps"
    )
    mixing_style: str = Field(description="Overall mixing approach for the set")
    set_duration: float = Field(description="Total estimated set duration in minutes")
    energy_graph: List[float] = Field(
        description="Energy levels throughout the set (0-1)"
    )


class DJLLMService:
    """Service for AI-powered DJ intelligence"""

    def __init__(self):
        # Initialize different models for different tasks
        self.vibe_analyst = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)
        self.playlist_finalizer = ChatOpenAI(model="o4-mini", temperature=1)
        self.transition_master = ChatOpenAI(model="gpt-4.1-mini", temperature=1)
        self.track_evaluator = ChatOpenAI(model="gpt-4.1-mini", temperature=1)

        # JSON output parsers
        self.vibe_parser = JsonOutputParser(pydantic_object=VibeAnalysis)
        self.track_parser = JsonOutputParser(pydantic_object=TrackEvaluation)
        self.transition_parser = JsonOutputParser(pydantic_object=TransitionPlan)
        self.playlist_parser = JsonOutputParser(pydantic_object=PlaylistFinalization)

    async def analyze_vibe(
        self, vibe_description: str, context: Optional[Dict] = None
    ) -> VibeAnalysis:
        """Analyze vibe description like a professional DJ"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a world-class DJ with deep understanding of music, energy, and crowd dynamics.
Analyze the vibe request and provide detailed guidance for track selection.

Consider:
- Energy levels and progression throughout the set
- Mood and emotional journey
- Genre compatibility and crossover potential
- BPM ranges that work for the vibe
- Professional mixing techniques

Output your analysis as JSON matching this schema:
{format_instructions}""",
                ),
                (
                    "human",
                    """Analyze this vibe request: "{vibe_description}"
            
Context: {context}""",
                ),
            ]
        )

        chain = prompt | self.vibe_analyst | self.vibe_parser

        try:
            result = await chain.ainvoke(
                {
                    "vibe_description": vibe_description,
                    "context": json.dumps(context or {}),
                    "format_instructions": self.vibe_parser.get_format_instructions(),
                }
            )
            # Ensure we return a VibeAnalysis instance, not a dict
            if isinstance(result, dict):
                vibe_analysis = VibeAnalysis(**result)
            else:
                vibe_analysis = result
            logger.info(
                f"🎵 Vibe Analysis: Energy={vibe_analysis.energy_level:.2f}, BPM={vibe_analysis.bpm_range}"
            )
            return vibe_analysis
        except Exception as e:
            logger.error(f"❌ Vibe analysis failed: {e}")
            # Fallback to basic analysis
            return VibeAnalysis(
                energy_level=0.5,
                energy_progression="steady",
                mood_keywords=vibe_description.lower().split(),
                genre_preferences=[],  # Empty list to avoid filtering when genres don't match
                bpm_range={"min": 100, "max": 140},  # Wider range for better results
                mixing_style="smooth",
            )

    async def evaluate_track(
        self,
        track: Dict,
        vibe_analysis: VibeAnalysis,
        playlist_context: Optional[List[Dict]] = None,
    ) -> TrackEvaluation:
        """Evaluate a track's fit for the playlist"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert DJ evaluating tracks for a curated playlist.
Consider the track's musical elements, energy, mood, and how it fits the overall vibe.
Think about mixing compatibility, energy flow, and the journey you're creating.

Output your evaluation as JSON matching this schema:
{format_instructions}""",
                ),
                (
                    "human",
                    """Evaluate this track for the playlist:
Track: {track_info}

Target Vibe: {vibe_info}

Current Playlist: {playlist_context}""",
                ),
            ]
        )

        chain = prompt | self.track_evaluator | self.track_parser

        # Prepare track info
        track_info = {
            "title": track.get("title", "Unknown"),
            "artist": track.get("artist", "Unknown"),
            "bpm": track.get("bpm"),
            "key": track.get("musical_key"),
            "energy": track.get("energy_level"),
            "genre": track.get("genre"),
            "duration": track.get("duration"),
        }

        try:
            result = await chain.ainvoke(
                {
                    "track_info": json.dumps(track_info),
                    "vibe_info": json.dumps(vibe_analysis.model_dump()),
                    "playlist_context": json.dumps(
                        [
                            {
                                "title": t.get("title"),
                                "bpm": t.get("bpm"),
                                "position": i + 1,
                            }
                            for i, t in enumerate(playlist_context or [])
                        ]
                    ),
                    "format_instructions": self.track_parser.get_format_instructions(),
                }
            )
            # Ensure we return a TrackEvaluation instance, not a dict
            if isinstance(result, dict):
                return TrackEvaluation(**result)
            return result
        except Exception as e:
            logger.error(f"❌ Track evaluation failed: {e}")
            # Basic fallback
            return TrackEvaluation(
                score=0.5,
                reasoning="Evaluation failed, using default score",
                energy_match=0.5,
                suggested_position=None,
                mixing_notes="Standard mix",
            )

    async def plan_transition(
        self, from_track: Dict, to_track: Dict, dj_style: str = "smooth"
    ) -> TransitionPlan:
        """Plan a professional transition between tracks"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a master DJ planning transitions between tracks.
Consider BPM compatibility, key matching, energy levels, and create a detailed transition plan.
Think like a professional: phrasing, harmonic mixing, effects timing, and crowd energy.

Your transition should be musically intelligent and technically precise.

IMPORTANT: Each effect in the effects array MUST include ALL of these fields:
- type: Effect type (filter, echo, scratch)
- start_at: Start time in seconds (e.g., 0, 2.5, 4)
- duration: Duration in seconds (e.g., 3, 5, 8)
- intensity: Effect intensity from 0 to 1 (e.g., 0.3, 0.7, 1.0)

Output your plan as JSON matching this schema:
{format_instructions}""",
                ),
                (
                    "human",
                    """Plan a transition between these tracks:

FROM: {from_track}
TO: {to_track}

DJ Style: {dj_style}""",
                ),
            ]
        )

        chain = prompt | self.transition_master | self.transition_parser

        # Prepare track info
        from_info = {
            "title": from_track.get("title"),
            "bpm": from_track.get("bpm"),
            "key": from_track.get("musical_key"),
            "energy": from_track.get("energy_level"),
            "genre": from_track.get("genre"),
        }

        to_info = {
            "title": to_track.get("title"),
            "bpm": to_track.get("bpm"),
            "key": to_track.get("musical_key"),
            "energy": to_track.get("energy_level"),
            "genre": to_track.get("genre"),
        }

        try:
            result = await chain.ainvoke(
                {
                    "from_track": json.dumps(from_info),
                    "to_track": json.dumps(to_info),
                    "dj_style": dj_style,
                    "format_instructions": self.transition_parser.get_format_instructions(),
                }
            )
            # Ensure we return a TransitionPlan instance, not a dict
            if isinstance(result, dict):
                return TransitionPlan(**result)
            return result
        except Exception as e:
            logger.error(f"❌ Transition planning failed: {e}")
            # Fallback to basic transition
            return TransitionPlan(
                compatibility_score=0.7,
                transition_type="smooth_blend",
                effects=[
                    TransitionEffect(type="filter", start_at=0, duration=8, intensity=0.7)
                ],
                crossfade_duration=8.0,
                cue_points={"outro_start": 0, "intro_start": 0},
                technique_notes="Basic crossfade",
                risk_level="safe",
            )

    async def design_transition_effects(
        self,
        transition_type: str,
        bpm_difference: float,
        energy_change: float,
        duration: float = 8.0,
        track_context: Optional[Dict] = None,
    ) -> Dict:
        """Design detailed transition effects using AI intelligence"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a master DJ designing transition effects between tracks.
Your effects should be musical, creative, and technically sound.

Consider:
- The transition type and what it means musically
- BPM difference and how to handle it smoothly
- Energy changes and crowd dynamics
- Effect timing relative to musical structure
- Creative variations to keep sets interesting

Available effects:
- filter: Low/high pass sweeps (intensity 0-1 affects frequency range)
- echo: Delay/echo effects (intensity affects feedback amount)
- scratch: Vinyl scratch effect (intensity affects scratch depth)

Output a JSON object with:
- profile: The transition style name
- effects: Array of 1-2 effect objects (MAXIMUM 2 EFFECTS) where EACH effect MUST have ALL FOUR FIELDS:
  * type: string (must be one of: filter, echo, or scratch) - REQUIRED
  * start_at: number (seconds from start, e.g., 0, 2, 4) - REQUIRED
  * duration: number (seconds, e.g., 4, 6, 8) - REQUIRED
  * intensity: number (must be between 0.2 and 0.5 for smooth transitions) - REQUIRED
- crossfade_curve: Type of curve (linear, s-curve, exponential)
- reasoning: Why these effects work for this transition

IMPORTANT RULES:
- Use ONLY 1-2 effects per transition (never more than 2)
- Keep intensity values low (0.2-0.5) for smooth, natural sound
- Space effects at least 2 seconds apart to avoid overlapping
- Prefer single effects for smoother transitions
- Every effect MUST include all four fields: type, start_at, duration, and intensity.""",
                ),
                (
                    "human",
                    """Design effects for this transition:

Transition Type: {transition_type}
BPM Difference: {bpm_difference}
Energy Change: {energy_change}
Duration: {duration} seconds (make effects prominent and noticeable!)

Additional Context: {context}""",
                ),
            ]
        )

        try:
            result = await self.transition_master.ainvoke(
                prompt.format(
                    transition_type=transition_type,
                    bpm_difference=bpm_difference,
                    energy_change=energy_change,
                    duration=duration,
                    context=json.dumps(track_context or {}),
                )
            )

            # Parse the JSON response
            import re

            json_match = re.search(r"\{[\s\S]*\}", result.content)
            if json_match:
                effect_plan = json.loads(json_match.group())
                
                # Validate and ensure all effects have required fields
                if "effects" in effect_plan:
                    for i, effect in enumerate(effect_plan["effects"]):
                        # Ensure all required fields exist with defaults if needed
                        if "type" not in effect:
                            effect["type"] = "filter"
                        if "start_at" not in effect:
                            effect["start_at"] = i * 2.0  # Stagger effects
                        if "duration" not in effect:
                            effect["duration"] = 4.0
                        if "intensity" not in effect:
                            effect["intensity"] = 0.5
                            
                        # Validate ranges
                        effect["intensity"] = max(0, min(1, float(effect.get("intensity", 0.5))))
                        effect["start_at"] = max(0, float(effect.get("start_at", 0)))
                        effect["duration"] = max(0.1, float(effect.get("duration", 4.0)))
                
                logger.info(f"🎛️ AI Effect Design: {effect_plan}")
                return effect_plan
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            logger.error(f"❌ Effect design failed: {e}")
            # Intelligent fallback based on parameters
            if bpm_difference > 10:
                return {
                    "profile": "tempo_blend",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 0.0,
                            "duration": 6.0,
                            "intensity": 0.4,
                        },
                        {
                            "type": "echo",
                            "start_at": 4.0,
                            "duration": 3.0,
                            "intensity": 0.3,
                        },
                    ],
                    "crossfade_curve": "s-curve",
                    "reasoning": "Tempo blend with gentle filter sweep and echo for BPM difference",
                }
            elif abs(energy_change) > 0.3:
                return {
                    "profile": "energy_shift",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 0.0,
                            "duration": max(duration * 0.8, 6.0),
                            "intensity": 0.4 if energy_change > 0 else 0.3,
                        }
                    ],
                    "crossfade_curve": "exponential",
                    "reasoning": "Energy transition with gentle filter sweep",
                }
            else:
                return {
                    "profile": "smooth_blend",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 2.0,
                            "duration": 4.0,
                            "intensity": 0.3,
                        }
                    ],
                    "crossfade_curve": "s-curve",
                    "reasoning": "Smooth transition with subtle filter",
                }

    @lru_cache(maxsize=100)
    def estimate_energy_from_features(
        self, bpm: Optional[float], genre: Optional[str]
    ) -> float:
        """Quick energy estimation when full analysis isn't available"""
        if not bpm:
            return 0.5

        # More nuanced than the static version
        if genre:
            genre_lower = genre.lower()
            if any(g in genre_lower for g in ["ambient", "downtempo", "chill"]):
                return min(0.3 + (bpm - 60) / 200, 0.5)
            elif any(g in genre_lower for g in ["techno", "hardstyle", "dnb"]):
                return min(0.6 + (bpm - 120) / 100, 1.0)

        # Default BPM-based estimation
        if bpm < 100:
            return bpm / 200
        elif bpm < 128:
            return 0.5 + (bpm - 100) / 56
        else:
            return min(0.8 + (bpm - 128) / 40, 1.0)

    async def finalize_playlist(
        self,
        track_list: List[Dict],
        vibe: str,
        transitions: Optional[List[Dict]] = None,
    ) -> PlaylistFinalization:
        """Finalize playlist with professional ordering and flow analysis"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a world-class DJ finalizing a curated playlist.
Analyze the track order, energy flow, and create a professional set structure.

Consider:
- Opening impact and closing statement
- Energy peaks and valleys throughout the set
- Key mixing moments and transitions
- Overall narrative and emotional journey
- Track order optimization for maximum impact

Output your analysis as JSON matching this schema:
{format_instructions}""",
                ),
                (
                    "human",
                    """Finalize this playlist:

Tracks: {tracks}

Vibe: {vibe}

Transitions: {transitions}""",
                ),
            ]
        )

        chain = prompt | self.playlist_finalizer | self.playlist_parser

        try:
            # Prepare track info
            track_info = []
            total_duration = 0
            for i, track in enumerate(track_list):
                duration = track.get("duration", 300)  # Default 5 min
                total_duration += duration
                track_info.append(
                    {
                        "position": i + 1,
                        "title": track.get("title", "Unknown"),
                        "artist": track.get("artist", "Unknown"),
                        "bpm": track.get("bpm"),
                        "key": track.get("musical_key"),
                        "energy": track.get("energy_level"),
                        "duration": duration,
                        "filepath": track.get("filepath"),
                    }
                )

            result = await chain.ainvoke(
                {
                    "tracks": json.dumps(track_info),
                    "vibe": vibe,
                    "transitions": json.dumps(transitions or []),
                    "format_instructions": self.playlist_parser.get_format_instructions(),
                }
            )

            # Ensure we return a PlaylistFinalization instance, not a dict
            if isinstance(result, dict):
                playlist_result = PlaylistFinalization(**result)
            else:
                playlist_result = result

            logger.info(
                f"🎯 Playlist Finalized: {len(playlist_result.tracks)} tracks, {playlist_result.set_duration:.1f} min"
            )
            return playlist_result

        except Exception as e:
            logger.error(f"❌ Playlist finalization failed: {e}")
            # Basic fallback
            tracks_with_notes = []
            energy_levels = []

            for i, track in enumerate(track_list):
                energy = track.get("energy_level", 0.5 + i * 0.1)
                energy_levels.append(energy)
                tracks_with_notes.append(
                    {
                        "filepath": track.get("filepath"),
                        "order": i + 1,
                        "mixing_note": f"Track {i + 1} - Standard mix",
                        "energy": energy,
                    }
                )

            return PlaylistFinalization(
                tracks=tracks_with_notes,
                overall_flow="Progressive energy build",
                key_moments=[
                    {"position": 1, "description": "Opening - Set the mood"},
                    {"position": len(track_list) // 2, "description": "Peak time"},
                    {"position": len(track_list), "description": "Closing"},
                ],
                mixing_style="smooth",
                set_duration=total_duration / 60,
                energy_graph=energy_levels,
            )

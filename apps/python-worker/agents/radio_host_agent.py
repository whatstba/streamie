"""Radio Host Agent for AI-powered radio mode functionality."""

import time
import random
from typing import Dict, List, Optional, Literal, TypedDict
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from utils.logger_config import setup_logger

logger = setup_logger(__name__)


class ContentType(str, Enum):
    """Types of content the radio host can generate."""

    TRACK_INTRO = "track_intro"
    ENCOURAGEMENT = "encouragement"
    TRIVIA = "trivia"
    GOOD_NEWS = "good_news"
    TRANSITION_COMMENT = "transition_comment"
    SESSION_WRAP = "session_wrap"


class PersonaConfig(BaseModel):
    """Configuration for a radio host persona."""

    id: str
    name: str
    description: str
    voice: Dict[str, str]  # model, voice, instructions
    personality: Dict[str, str]  # accent, emotional_range, tone, etc.
    content: Dict[str, List[str]]  # topics, intro_style, etc.


class VoiceSegment(BaseModel):
    """A voice segment to be played by the radio host."""

    id: str = Field(default_factory=lambda: f"seg_{int(time.time() * 1000)}")
    content_type: ContentType
    script: str
    persona_id: str
    voice_config: Dict[str, str]
    instructions: str
    created_at: float = Field(default_factory=time.time)
    played_at: Optional[float] = None
    duration_estimate: float = 0.0  # Estimated duration in seconds


class RadioHostState(TypedDict):
    """State for the radio host agent."""

    mode_enabled: bool
    current_persona: Dict  # PersonaConfig as dict
    last_spoke_at: float
    tracks_since_last: int
    next_content_type: Optional[str]
    voice_queue: List[Dict]  # List of VoiceSegment as dicts
    playlist_context: Dict  # Current playlist mood, energy, etc.
    current_track: Optional[Dict]  # Current track info
    next_track: Optional[Dict]  # Next track info
    session_start: float
    total_segments: int
    error: Optional[str]


# Preset personas
PRESET_PERSONAS = {
    "lo_fi_study": PersonaConfig(
        id="lo_fi_study",
        name="Lo-fi Study Pal",
        description="Soft ASMR tone, mindfulness cues",
        voice={
            "model": "gpt-4o-mini-tts",
            "voice": "shimmer",
            "instructions": (
                "Speak in a soft ASMR tone with a slow, relaxed pace. "
                "Whisper gently during transitions. "
                "Use calming intonation with minimal emotional range."
            ),
        },
        personality={
            "accent": "neutral",
            "emotional_range": "chill",
            "tone": "asmr-soft",
            "speech_speed": "slow",
            "whisper_mode": "true",
        },
        content={
            "topics": ["mindfulness", "focus", "calm", "study"],
            "intro_style": "gentle_whisper",
            "sign_off_style": "peaceful",
        },
    ),
    "festival_hype": PersonaConfig(
        id="festival_hype",
        name="Festival Hype",
        description="High energy, crowd excitement",
        voice={
            "model": "gpt-4o-mini-tts",
            "voice": "nova",
            "instructions": (
                "Speak with high energy and excitement! Fast speech, "
                "hype intonation, occasional 'Yeah!' or 'Let's go!' "
                "Sound like you're pumping up a festival crowd."
            ),
        },
        personality={
            "accent": "american",
            "emotional_range": "hype",
            "tone": "energetic",
            "speech_speed": "fast",
            "whisper_mode": "false",
        },
        content={
            "topics": ["party", "energy", "crowd", "festival"],
            "intro_style": "high_energy",
            "sign_off_style": "pump_up",
        },
    ),
    "world_citizen": PersonaConfig(
        id="world_citizen",
        name="World Citizen",
        description="Global news, cultural insights",
        voice={
            "model": "gpt-4o-mini-tts",
            "voice": "fable",
            "instructions": (
                "Speak with a warm, worldly tone. Occasionally hint at "
                "different accents (British, Nigerian, French) subtly. "
                "Balanced emotional range with storytelling quality."
            ),
        },
        personality={
            "accent": "international",
            "emotional_range": "balanced",
            "tone": "warm",
            "speech_speed": "normal",
            "whisper_mode": "false",
        },
        content={
            "topics": ["culture", "world", "news", "connection"],
            "intro_style": "worldly",
            "sign_off_style": "inclusive",
        },
    ),
    "retro_radio": PersonaConfig(
        id="retro_radio",
        name="Retro Radio Host",
        description="Classic AM radio style",
        voice={
            "model": "gpt-4o-mini-tts",
            "voice": "echo",
            "instructions": (
                "Channel classic AM radio host energy. Slightly theatrical, "
                "clear enunciation, occasional dad jokes. Think 1970s "
                "smooth radio personality with vintage charm."
            ),
        },
        personality={
            "accent": "american_classic",
            "emotional_range": "balanced",
            "tone": "playful",
            "speech_speed": "normal",
            "whisper_mode": "false",
        },
        content={
            "topics": ["nostalgia", "classics", "humor", "vintage"],
            "intro_style": "classic_radio",
            "sign_off_style": "signature",
        },
    ),
    "mindful_mentor": PersonaConfig(
        id="mindful_mentor",
        name="Mindful Mentor",
        description="Calming presence, meditation prompts",
        voice={
            "model": "gpt-4o-mini-tts",
            "voice": "sage",
            "instructions": (
                "Speak calmly and thoughtfully. Gentle pacing with "
                "mindful pauses. Soothing tone that encourages "
                "reflection and presence. Never rushed."
            ),
        },
        personality={
            "accent": "neutral",
            "emotional_range": "chill",
            "tone": "warm",
            "speech_speed": "slow",
            "whisper_mode": "false",
        },
        content={
            "topics": ["mindfulness", "reflection", "wisdom", "peace"],
            "intro_style": "thoughtful",
            "sign_off_style": "inspiring",
        },
    ),
}


class RadioHostAgent:
    """Agent for managing radio host functionality."""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(RadioHostState)

        # Add nodes
        workflow.add_node("check_timing", self.check_timing)
        workflow.add_node("select_content_type", self.select_content_type)
        workflow.add_node("generate_content", self.generate_content)
        workflow.add_node("prepare_voice", self.prepare_voice)
        workflow.add_node("queue_segment", self.queue_segment)
        workflow.add_node("error_handler", self.error_handler)

        # Add edges
        workflow.set_entry_point("check_timing")

        workflow.add_conditional_edges(
            "check_timing",
            self.should_speak,
            {"speak": "select_content_type", "wait": END, "error": "error_handler"},
        )

        workflow.add_edge("select_content_type", "generate_content")
        workflow.add_edge("generate_content", "prepare_voice")
        workflow.add_edge("prepare_voice", "queue_segment")
        workflow.add_edge("queue_segment", END)
        workflow.add_edge("error_handler", END)

        return workflow.compile()

    def check_timing(self, state: RadioHostState) -> RadioHostState:
        """Check if it's appropriate to speak now."""
        try:
            current_time = time.time()
            time_since_last = current_time - state["last_spoke_at"]

            logger.info(
                f"Checking timing: {time_since_last:.1f}s since last, "
                f"{state['tracks_since_last']} tracks since last"
            )

            return state

        except Exception as e:
            logger.error(f"Error in check_timing: {e}")
            state["error"] = str(e)
            return state

    def should_speak(self, state: RadioHostState) -> Literal["speak", "wait", "error"]:
        """Determine if the host should speak now."""
        if state.get("error"):
            return "error"

        if not state["mode_enabled"]:
            return "wait"

        current_time = time.time()
        time_since_last = current_time - state["last_spoke_at"]

        # Minimum silence period (60s)
        if time_since_last < 60:
            return "wait"

        # Track-based trigger (every 2-3 tracks)
        if state["tracks_since_last"] >= random.randint(2, 3):
            return "speak"

        # Time-based trigger (every 5 minutes max)
        if time_since_last >= 300:
            return "speak"

        # Energy shift detection
        if self._detect_energy_shift(state):
            return "speak"

        # Random chance (5%)
        if random.random() < 0.05:
            return "speak"

        return "wait"

    def select_content_type(self, state: RadioHostState) -> RadioHostState:
        """Select appropriate content type based on context."""
        try:
            # If there's a preset next content type, use it
            if state.get("next_content_type"):
                return state

            # Session wrap if it's been a while
            if time.time() - state["session_start"] > 3600:  # 1 hour
                state["next_content_type"] = ContentType.SESSION_WRAP
                return state

            # Energy shift comment
            if self._detect_energy_shift(state):
                state["next_content_type"] = ContentType.TRANSITION_COMMENT
                return state

            # Weight the content types
            weights = {
                ContentType.TRACK_INTRO: 40,
                ContentType.ENCOURAGEMENT: 25,
                ContentType.TRIVIA: 20,
                ContentType.GOOD_NEWS: 10,
                ContentType.TRANSITION_COMMENT: 5,
            }

            content_types = list(weights.keys())
            probabilities = list(weights.values())

            selected = random.choices(content_types, weights=probabilities)[0]
            state["next_content_type"] = selected

            logger.info(f"Selected content type: {selected}")
            return state

        except Exception as e:
            logger.error(f"Error selecting content type: {e}")
            state["error"] = str(e)
            return state

    def generate_content(self, state: RadioHostState) -> RadioHostState:
        """Generate content based on selected type and persona."""
        try:
            persona = PersonaConfig(**state["current_persona"])
            content_type = state["next_content_type"]

            # Build context for content generation
            context = {
                "current_track": state.get("current_track", {}),
                "next_track": state.get("next_track", {}),
                "playlist_mood": state["playlist_context"].get("mood", ""),
                "energy_level": state["playlist_context"].get("energy", "medium"),
                "time_of_day": datetime.now().strftime("%H:%M"),
                "tracks_played": state["tracks_since_last"],
            }

            # Generate script using LLM
            script = self._generate_script(persona, content_type, context)

            # Create voice segment
            segment = VoiceSegment(
                content_type=content_type,
                script=script,
                persona_id=persona.id,
                voice_config=persona.voice,
                instructions=persona.voice["instructions"],
                duration_estimate=len(script.split()) / 150 * 60,  # Rough estimate
            )

            state["voice_queue"].append(segment.dict())

            logger.info(f"Generated {content_type} script: {script[:50]}...")
            return state

        except Exception as e:
            logger.error(f"Error generating content: {e}")
            state["error"] = str(e)
            return state

    def prepare_voice(self, state: RadioHostState) -> RadioHostState:
        """Prepare voice configuration for TTS."""
        try:
            if not state["voice_queue"]:
                return state

            # Get the latest segment
            segment = state["voice_queue"][-1]

            # Enhance instructions based on context
            is_downtempo = state["playlist_context"].get("energy", "medium") == "low"
            persona = PersonaConfig(**state["current_persona"])

            if is_downtempo and persona.personality.get("whisper_mode") == "true":
                segment["instructions"] += " Whisper softly for this downtempo section."

            # Add any dynamic adjustments
            if state["playlist_context"].get("transition_active"):
                segment["instructions"] += (
                    " Acknowledge the smooth transition happening."
                )

            return state

        except Exception as e:
            logger.error(f"Error preparing voice: {e}")
            state["error"] = str(e)
            return state

    def queue_segment(self, state: RadioHostState) -> RadioHostState:
        """Queue the segment and update state."""
        try:
            # Update timing information
            state["last_spoke_at"] = time.time()
            state["tracks_since_last"] = 0
            state["total_segments"] += 1
            state["next_content_type"] = None

            logger.info(f"Queued segment #{state['total_segments']}")
            return state

        except Exception as e:
            logger.error(f"Error queueing segment: {e}")
            state["error"] = str(e)
            return state

    def error_handler(self, state: RadioHostState) -> RadioHostState:
        """Handle errors gracefully."""
        logger.error(f"Radio host error: {state.get('error', 'Unknown error')}")
        state["error"] = None  # Clear error for next run
        return state

    def _detect_energy_shift(self, state: RadioHostState) -> bool:
        """Detect if there's been a significant energy shift."""
        current = state.get("current_track", {})
        previous = state["playlist_context"].get("previous_track", {})

        if not current or not previous:
            return False

        current_bpm = current.get("bpm", 0)
        previous_bpm = previous.get("bpm", 0)

        if abs(current_bpm - previous_bpm) > 20:
            return True

        current_energy = current.get("energy_level", 0.5)
        previous_energy = previous.get("energy_level", 0.5)

        if abs(current_energy - previous_energy) > 0.3:
            return True

        return False

    def _generate_script(
        self, persona: PersonaConfig, content_type: str, context: Dict
    ) -> str:
        """Generate script using LLM based on persona and context."""

        # Content templates by persona
        templates = self._get_content_templates(persona.id)
        template = templates.get(content_type, {})

        # Build prompt
        system_prompt = f"""You are {persona.name}, a radio DJ with this personality:
{persona.description}

Your speaking style:
- Tone: {persona.personality["tone"]}
- Emotional range: {persona.personality["emotional_range"]}
- Topics you love: {", ".join(persona.content["topics"])}

Generate a {content_type} radio segment (20-30 seconds when spoken).
Keep it natural, engaging, and true to your personality.
"""

        user_prompt = f"""Context:
- Current track: {context["current_track"].get("title", "Unknown")} by {context["current_track"].get("artist", "Unknown")}
- BPM: {context["current_track"].get("bpm", "Unknown")}
- Playlist mood: {context["playlist_mood"]}
- Energy level: {context["energy_level"]}
- Time: {context["time_of_day"]}

Generate a {content_type} segment following this style:
{template.get("style", "Be yourself")}

Example opener: {template.get("example", "")}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.llm.invoke(messages)
        return response.content.strip()

    def _get_content_templates(self, persona_id: str) -> Dict:
        """Get content templates for a persona."""
        templates = {
            "lo_fi_study": {
                ContentType.TRACK_INTRO: {
                    "style": "Whisper gently, be minimal and calming",
                    "example": "~whispers~ Hey there... settling into...",
                },
                ContentType.ENCOURAGEMENT: {
                    "style": "Soft reminders about breathing and focus",
                    "example": "~gentle reminder~ You're doing great...",
                },
            },
            "festival_hype": {
                ContentType.TRACK_INTRO: {
                    "style": "Maximum energy! Get the crowd pumped!",
                    "example": "YOOO! GET READY!",
                },
                ContentType.ENCOURAGEMENT: {
                    "style": "Hype them up! Make them feel invincible!",
                    "example": "YOU'RE CRUSHING IT!",
                },
            },
            "world_citizen": {
                ContentType.TRACK_INTRO: {
                    "style": "Worldly and inclusive, mention global connections",
                    "example": "Coming up, we have...",
                },
                ContentType.GOOD_NEWS: {
                    "style": "Share positive global stories",
                    "example": "Something beautiful from...",
                },
            },
            "retro_radio": {
                ContentType.TRACK_INTRO: {
                    "style": "Classic radio announcer, slight theatricality",
                    "example": "Ladies and gentlemen...",
                },
                ContentType.TRIVIA: {
                    "style": "Fun facts with vintage charm",
                    "example": "Did you know, back in...",
                },
            },
            "mindful_mentor": {
                ContentType.TRACK_INTRO: {
                    "style": "Thoughtful and present, invite reflection",
                    "example": "Let's welcome this moment with...",
                },
                ContentType.ENCOURAGEMENT: {
                    "style": "Gentle wisdom and affirmation",
                    "example": "Remember, you are exactly where...",
                },
            },
        }

        return templates.get(persona_id, {})

    def process_track_change(
        self, current_track: Dict, next_track: Optional[Dict], playlist_context: Dict
    ) -> List[VoiceSegment]:
        """Process a track change event and generate appropriate content."""

        # Initialize state if needed
        state = self._initialize_state(playlist_context)

        # Update track information
        state["current_track"] = current_track
        state["next_track"] = next_track
        state["tracks_since_last"] += 1
        state["playlist_context"] = playlist_context

        # Run the graph
        result = self.graph.invoke(state)

        # Extract any new voice segments
        new_segments = []
        for segment_dict in result.get("voice_queue", []):
            if segment_dict.get("created_at", 0) > state["last_spoke_at"]:
                new_segments.append(VoiceSegment(**segment_dict))

        return new_segments

    def _initialize_state(self, playlist_context: Dict) -> RadioHostState:
        """Initialize or retrieve radio host state."""
        # In production, this would retrieve from a session store
        return {
            "mode_enabled": True,
            "current_persona": PRESET_PERSONAS["world_citizen"].dict(),
            "last_spoke_at": time.time() - 120,  # Start ready to speak
            "tracks_since_last": 0,
            "next_content_type": None,
            "voice_queue": [],
            "playlist_context": playlist_context,
            "current_track": None,
            "next_track": None,
            "session_start": time.time(),
            "total_segments": 0,
            "error": None,
        }

    def set_persona(self, persona_id: str) -> PersonaConfig:
        """Set the active persona."""
        if persona_id not in PRESET_PERSONAS:
            raise ValueError(f"Unknown persona: {persona_id}")

        return PRESET_PERSONAS[persona_id]

    def get_available_personas(self) -> Dict[str, PersonaConfig]:
        """Get all available personas."""
        return PRESET_PERSONAS

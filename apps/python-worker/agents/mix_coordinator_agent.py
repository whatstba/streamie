"""
Mix Coordinator Agent - Makes high-level mixing decisions using LangGraph.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Annotated, TypedDict
from datetime import datetime
import operator
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from models.mix_models import (
    MixDecision,
    TransitionType,
    EQAdjustment,
    TransitionEffect,
    TrackCompatibility,
    TransitionPoint,
    EnergyTrajectory,
    DJSessionState,
    TransitionState,
    EffectType,
)
from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager
from services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🎛️ [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class MixCoordinatorState(TypedDict):
    """State for mix coordination workflow"""

    # Core state
    decks: Dict[str, Dict[str, Any]]
    mixer: Dict[str, Any]
    analysis_cache: Dict[str, Dict[str, Any]]

    # Decision making
    current_mix_plan: Optional[Dict[str, Any]]
    compatibility_scores: Optional[Dict[str, Any]]
    transition_points: Optional[List[Dict[str, Any]]]

    # History and context
    mix_history: Annotated[List[Dict[str, Any]], operator.add]
    energy_trajectory: str
    session_metrics: Dict[str, float]

    # Messages for LangGraph
    messages: Annotated[List[BaseMessage], operator.add]

    # Control flow
    should_mix: bool
    mix_approved: bool


class MixCoordinatorAgent:
    """Agent responsible for high-level mix coordination decisions."""

    def __init__(
        self,
        deck_manager: DeckManager,
        mixer_manager: MixerManager,
        analysis_service: AnalysisService,
    ):
        logger.info("🎛️ Initializing MixCoordinatorAgent...")
        self.deck_manager = deck_manager
        self.mixer_manager = mixer_manager
        self.analysis_service = analysis_service

        # Initialize LLM for decision making
        logger.info("🎛️ Creating LLM client...")
        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3, max_tokens=1000)

        # Create the workflow graph
        logger.info("🎛️ Creating workflow graph...")
        self.workflow = self._create_workflow()
        logger.info("🎛️ MixCoordinatorAgent initialized successfully")

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow for mix coordination."""
        workflow = StateGraph(MixCoordinatorState)

        # Add nodes
        workflow.add_node("analyze_decks", self._analyze_decks)
        workflow.add_node("evaluate_compatibility", self._evaluate_compatibility)
        workflow.add_node("generate_mix_plan", self._generate_mix_plan)
        workflow.add_node("validate_plan", self._validate_plan)

        # Define edges
        workflow.add_edge(START, "analyze_decks")
        workflow.add_edge("analyze_decks", "evaluate_compatibility")
        workflow.add_edge("evaluate_compatibility", "generate_mix_plan")
        workflow.add_edge("generate_mix_plan", "validate_plan")

        # Conditional edge based on validation
        def route_after_validation(state):
            if state.get("mix_approved", False):
                return END
            return "generate_mix_plan"  # Retry with feedback

        workflow.add_conditional_edges(
            "validate_plan",
            route_after_validation,
            {END: END, "generate_mix_plan": "generate_mix_plan"},
        )

        return workflow.compile()

    async def _analyze_decks(self, state: MixCoordinatorState) -> Dict[str, Any]:
        """Analyze current deck states and determine if mixing is needed."""
        logger.info("🎛️ Analyzing deck states for mixing opportunities")

        decks = state.get("decks", {})
        mixer = state.get("mixer", {})

        # Find playing decks
        playing_decks = []
        loaded_decks = []

        for deck_id, deck_state in decks.items():
            if deck_state.get("is_playing"):
                playing_decks.append((deck_id, deck_state))
            elif deck_state.get("track_filepath"):
                loaded_decks.append((deck_id, deck_state))

        # Determine if we should plan a mix
        should_mix = False
        mix_scenario = None

        if len(playing_decks) == 1 and loaded_decks:
            # One deck playing, others available for mixing
            should_mix = True
            mix_scenario = "single_deck_transition"
        elif len(playing_decks) >= 2:
            # Multiple decks playing, might need to clean up
            should_mix = True
            mix_scenario = "multi_deck_blend"

        # Get analysis data for all relevant decks
        analysis_cache = state.get("analysis_cache", {})

        for deck_id, deck_state in playing_decks + loaded_decks:
            filepath = deck_state.get("track_filepath")
            if filepath and filepath not in analysis_cache:
                # Fetch from analysis service
                try:
                    analysis = await self.analysis_service.get_cached_analysis(filepath)
                    if analysis:
                        analysis_cache[filepath] = analysis
                except Exception as e:
                    logger.error(f"Failed to get analysis for {filepath}: {e}")

        return {
            "should_mix": should_mix,
            "messages": [
                AIMessage(
                    content=f"Mix scenario: {mix_scenario or 'none'}. "
                    f"Playing: {[d[0] for d in playing_decks]}, "
                    f"Loaded: {[d[0] for d in loaded_decks]}"
                )
            ],
            "analysis_cache": analysis_cache,
        }

    async def _evaluate_compatibility(
        self, state: MixCoordinatorState
    ) -> Dict[str, Any]:
        """Evaluate compatibility between potential mix candidates."""
        if not state.get("should_mix"):
            return {"compatibility_scores": {}, "transition_points": []}

        logger.info("🎛️ Evaluating track compatibility for mixing")

        decks = state.get("decks", {})
        analysis_cache = state.get("analysis_cache", {})

        # Find best mixing candidates
        playing_decks = [(k, v) for k, v in decks.items() if v.get("is_playing")]
        available_decks = [
            (k, v)
            for k, v in decks.items()
            if v.get("track_filepath") and not v.get("is_playing")
        ]

        if not playing_decks or not available_decks:
            return {"compatibility_scores": {}, "transition_points": []}

        # For now, use first playing deck as source
        source_deck_id, source_deck = playing_decks[0]
        source_analysis = analysis_cache.get(source_deck.get("track_filepath"), {})

        compatibility_scores = {}
        all_transition_points = {}

        # Evaluate each available deck as target
        for target_deck_id, target_deck in available_decks:
            target_analysis = analysis_cache.get(target_deck.get("track_filepath"), {})

            if source_analysis and target_analysis:
                # Calculate compatibility
                compatibility = self._calculate_compatibility(
                    source_analysis, target_analysis
                )
                compatibility_scores[f"{source_deck_id}_to_{target_deck_id}"] = (
                    compatibility
                )

                # Find transition points
                transition_points = self._find_transition_points(
                    source_analysis, target_analysis, source_deck, target_deck
                )
                all_transition_points[f"{source_deck_id}_to_{target_deck_id}"] = (
                    transition_points
                )

        return {
            "compatibility_scores": compatibility_scores,
            "transition_points": all_transition_points,
            "messages": [
                AIMessage(
                    content=f"Evaluated {len(compatibility_scores)} mixing options"
                )
            ],
        }

    def _calculate_compatibility(self, source: Dict, target: Dict) -> Dict[str, float]:
        """Calculate detailed compatibility between tracks."""
        compatibility = {
            "overall": 0.0,
            "bpm": 0.0,
            "key": 0.0,
            "energy": 0.0,
            "genre": 0.0,
        }

        # BPM compatibility
        bpm_a = source.get("bpm", 120)
        bpm_b = target.get("bpm", 120)
        if bpm_a and bpm_b:
            bpm_diff_percent = abs(bpm_a - bpm_b) / bpm_a * 100
            if bpm_diff_percent <= 5:
                compatibility["bpm"] = 1.0
            elif bpm_diff_percent <= 10:
                compatibility["bpm"] = 0.7
            else:
                compatibility["bpm"] = max(0, 1 - bpm_diff_percent / 50)

        # Key compatibility (simplified)
        key_a = source.get("camelot_key", "8A")
        key_b = target.get("camelot_key", "8A")
        if key_a == key_b:
            compatibility["key"] = 1.0
        elif key_a and key_b:
            # Simple Camelot wheel logic
            try:
                num_a = int(key_a[:-1])
                letter_a = key_a[-1]
                num_b = int(key_b[:-1])
                letter_b = key_b[-1]

                if letter_a == letter_b and abs(num_a - num_b) == 1:
                    compatibility["key"] = 0.9
                elif num_a == num_b and letter_a != letter_b:
                    compatibility["key"] = 0.85
                else:
                    compatibility["key"] = 0.5
            except Exception:
                compatibility["key"] = 0.5

        # Energy compatibility
        energy_a = source.get("energy_level", 0.5)
        energy_b = target.get("energy_level", 0.5)
        energy_diff = abs(energy_a - energy_b)
        compatibility["energy"] = 1.0 - min(energy_diff, 1.0)

        # Genre (simplified)
        genre_a = source.get("genre", "")
        genre_b = target.get("genre", "")
        compatibility["genre"] = 1.0 if genre_a == genre_b else 0.6

        # Overall score
        compatibility["overall"] = (
            compatibility["bpm"] * 0.4
            + compatibility["key"] * 0.3
            + compatibility["energy"] * 0.2
            + compatibility["genre"] * 0.1
        )

        return compatibility

    def _find_transition_points(
        self, source: Dict, target: Dict, source_deck: Dict, target_deck: Dict
    ) -> List[Dict]:
        """Find optimal transition points between tracks."""
        points = []

        # Get beat grids
        source_beats = source.get("beat_times", [])
        target_beats = target.get("beat_times", [])

        if (
            source_beats
            and target_beats
            and len(source_beats) > 64
            and len(target_beats) > 64
        ):
            # Find phrase boundaries (every 16 bars = 64 beats)
            source_phrases = [source_beats[i] for i in range(64, len(source_beats), 64)]
            target_phrases = [
                target_beats[i] for i in range(0, min(192, len(target_beats)), 64)
            ]

            # Create transition points at phrase boundaries
            for i, source_time in enumerate(source_phrases[-3:]):  # Last 3 phrases
                for j, target_time in enumerate(target_phrases[:3]):  # First 3 phrases
                    points.append(
                        {
                            "type": "phrase_aligned",
                            "deck_a_time": source_time,
                            "deck_b_time": target_time,
                            "confidence": 0.8 - (i * 0.1) - (j * 0.1),
                            "musical_reason": f"Phrase {i + 1} to phrase {j + 1}",
                        }
                    )

        # Sort by confidence
        points.sort(key=lambda x: x["confidence"], reverse=True)
        return points[:5]  # Top 5 options

    async def _generate_mix_plan(self, state: MixCoordinatorState) -> Dict[str, Any]:
        """Generate mix plan using LLM."""
        if not state.get("should_mix"):
            return {"current_mix_plan": None, "mix_approved": True}

        logger.info("🎛️ Generating mix plan with AI")

        compatibility_scores = state.get("compatibility_scores", {})
        transition_points = state.get("transition_points", {})
        energy_trajectory = state.get("energy_trajectory", "building")
        mixer_state = state.get("mixer", {})

        if not compatibility_scores:
            return {"current_mix_plan": None, "mix_approved": True}

        # Find best mix option
        best_option = max(
            compatibility_scores.items(), key=lambda x: x[1].get("overall", 0)
        )
        mix_key = best_option[0]
        compatibility = best_option[1]

        # Parse deck IDs
        source_deck_id, target_deck_id = mix_key.split("_to_")

        # Get deck states
        decks = state.get("decks", {})
        source_deck = decks.get(source_deck_id, {})
        target_deck = decks.get(target_deck_id, {})

        # Get analysis data
        analysis_cache = state.get("analysis_cache", {})
        source_analysis = analysis_cache.get(source_deck.get("track_filepath"), {})
        target_analysis = analysis_cache.get(target_deck.get("track_filepath"), {})

        # Create prompt for LLM
        prompt = f"""As a professional DJ, create a mix plan for transitioning between two tracks.

Source Track (Deck {source_deck_id}):
- BPM: {source_analysis.get("bpm", "unknown")}
- Key: {source_analysis.get("key", "unknown")} ({source_analysis.get("camelot_key", "unknown")})
- Energy: {source_analysis.get("energy_level", 0.5):.2f}
- Genre: {source_analysis.get("genre", "unknown")}

Target Track (Deck {target_deck_id}):
- BPM: {target_analysis.get("bpm", "unknown")}
- Key: {target_analysis.get("key", "unknown")} ({target_analysis.get("camelot_key", "unknown")})
- Energy: {target_analysis.get("energy_level", 0.5):.2f}
- Genre: {target_analysis.get("genre", "unknown")}

Compatibility Scores:
- Overall: {compatibility.get("overall", 0):.2f}
- BPM: {compatibility.get("bpm", 0):.2f}
- Key: {compatibility.get("key", 0):.2f}
- Energy: {compatibility.get("energy", 0):.2f}

Current Mixer State:
- Crossfader: {mixer_state.get("crossfader", 0):.2f}
- Energy Trajectory: {energy_trajectory}

Available transition points: {len(transition_points.get(mix_key, []))}

Create a JSON mix plan with:
1. "action": one of ["smooth_blend", "quick_cut", "effects_transition", "beatmatch_blend"]
2. "duration": transition time in seconds (8-32 typically)
3. "effects": array of max 2 effects, each with:
   - "type": one of ["filter_sweep", "echo", "reverb", "delay", "eq_sweep"]
   - "intensity": 0.2-0.5 (keep it subtle)
   - "start_at": when to start effect (0-duration)
   - "duration": effect duration (optional)
4. "eq_adjustments": for source and target decks:
   - "{source_deck_id}": {{"low": -1 to 1, "mid": -1 to 1, "high": -1 to 1}}
   - "{target_deck_id}": {{"low": -1 to 1, "mid": -1 to 1, "high": -1 to 1}}
5. "reasoning": brief explanation of the mix strategy

Consider the compatibility scores and energy trajectory when deciding.
Low compatibility may need more effects and longer transitions.
Keep effects subtle (intensity 0.2-0.5) for natural sound."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # Parse JSON from response
            json_str = response.content
            # Extract JSON if wrapped in markdown
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            mix_plan_data = json.loads(json_str.strip())

            # Create MixDecision object
            mix_decision = MixDecision(
                action=TransitionType(mix_plan_data.get("action", "smooth_blend")),
                source_deck=source_deck_id,
                target_deck=target_deck_id,
                duration=mix_plan_data.get("duration", 16.0),
                effects=[
                    TransitionEffect(
                        type=EffectType(effect.get("type")),
                        intensity=effect.get("intensity", 0.3),
                        start_at=effect.get("start_at", 0.0),
                        duration=effect.get("duration"),
                    )
                    for effect in mix_plan_data.get("effects", [])
                ],
                eq_adjustments={
                    deck_id: EQAdjustment(**eq_data)
                    for deck_id, eq_data in mix_plan_data.get(
                        "eq_adjustments", {}
                    ).items()
                },
                decision_confidence=compatibility.get("overall", 0.5),
                reasoning=mix_plan_data.get("reasoning", ""),
            )

            # Add best transition point if available
            points = transition_points.get(mix_key, [])
            if points:
                best_point = points[0]
                mix_decision.transition_point = TransitionPoint(**best_point)

            logger.info(
                f"🎛️ Generated mix plan: {mix_decision.action} for {mix_decision.duration}s"
            )

            return {
                "current_mix_plan": mix_decision.dict(),
                "messages": [
                    AIMessage(content=f"Mix plan created: {mix_decision.reasoning}")
                ],
            }

        except Exception as e:
            logger.error(f"Failed to generate mix plan: {e}")
            # Fallback plan
            fallback_decision = MixDecision(
                action=TransitionType.SMOOTH_BLEND,
                source_deck=source_deck_id,
                target_deck=target_deck_id,
                duration=16.0,
                effects=[],
                eq_adjustments={
                    source_deck_id: EQAdjustment(low=-0.3, mid=0, high=-0.2),
                    target_deck_id: EQAdjustment(low=0, mid=0, high=0),
                },
                decision_confidence=0.5,
                reasoning="Fallback plan due to generation error",
            )

            return {
                "current_mix_plan": fallback_decision.dict(),
                "messages": [AIMessage(content=f"Using fallback plan: {str(e)}")],
            }

    async def _validate_plan(self, state: MixCoordinatorState) -> Dict[str, Any]:
        """Validate the generated mix plan."""
        mix_plan = state.get("current_mix_plan")

        if not mix_plan:
            return {"mix_approved": True}

        logger.info("🎛️ Validating mix plan")

        # Basic validation checks
        warnings = []

        # Check duration
        if mix_plan["duration"] < 4:
            warnings.append("Duration too short, may sound abrupt")
        elif mix_plan["duration"] > 60:
            warnings.append("Duration too long, may lose energy")

        # Check effects
        if len(mix_plan.get("effects", [])) > 2:
            warnings.append("Too many effects, limiting to 2")
            mix_plan["effects"] = mix_plan["effects"][:2]

        # Validate effect intensities
        for effect in mix_plan.get("effects", []):
            if effect.get("intensity", 0) > 0.7:
                effect["intensity"] = 0.5
                warnings.append(f"Reduced {effect['type']} intensity for subtlety")

        # For now, always approve with warnings logged
        if warnings:
            logger.warning(f"Mix plan warnings: {', '.join(warnings)}")

        return {
            "mix_approved": True,
            "current_mix_plan": mix_plan,
            "messages": [
                AIMessage(content=f"Plan validated. Warnings: {len(warnings)}")
            ],
        }

    async def coordinate_mix(
        self, session_state: Dict[str, Any]
    ) -> Optional[MixDecision]:
        """Main entry point to coordinate a mix decision."""
        logger.info("🎛️ Starting mix coordination")

        # Prepare initial state
        initial_state = MixCoordinatorState(
            decks=session_state.get("decks", {}),
            mixer=session_state.get("mixer", {}),
            analysis_cache=session_state.get("analysis_cache", {}),
            mix_history=session_state.get("mix_history", []),
            energy_trajectory=session_state.get("energy_trajectory", "building"),
            session_metrics=session_state.get("performance_metrics", {}),
            messages=[],
            should_mix=False,
            mix_approved=False,
            compatibility_scores=None,
            transition_points=None,
            current_mix_plan=None,
        )

        # Run the workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            # Extract mix plan
            mix_plan_dict = final_state.get("current_mix_plan")
            if mix_plan_dict:
                # Convert dict back to MixDecision
                mix_decision = MixDecision(**mix_plan_dict)
                logger.info(f"🎛️ Mix coordination complete: {mix_decision.action}")
                return mix_decision
            else:
                logger.info("🎛️ No mix needed at this time")
                return None

        except Exception as e:
            logger.error(f"Mix coordination failed: {e}")
            return None

    async def get_alternative_plans(
        self, session_state: Dict[str, Any], count: int = 3
    ) -> List[MixDecision]:
        """Generate alternative mix plans for user selection."""
        # This could be extended to generate multiple options
        # For now, return empty list
        return []

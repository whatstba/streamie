"""
DJ Set Service - Generate and manage pre-planned DJ sets with transitions.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import uuid
from models.dj_set_models import DJSet, DJSetTrack, DJSetTransition, DJSetPlaybackState
from agents.dj_agent import DJAgent
from utils.dj_llm import DJLLMService, TransitionPlan, TransitionEffect
from utils.sqlite_db import get_sqlite_db
import sqlite3
import os
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler for DJ set logs
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🎛️ [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class DJSetService:
    """Service for generating and managing DJ sets"""

    def __init__(self):
        self.dj_agent = DJAgent()
        self.llm_service = DJLLMService()
        self.db = get_sqlite_db()

        # Store active playback states in memory
        self._playback_states: Dict[str, DJSetPlaybackState] = {}
        
        # Store generated DJ sets in memory (for now)
        self._dj_sets: Dict[str, DJSet] = {}

        logger.info("🎛️ DJSetService initialized")

    async def generate_dj_set(
        self,
        vibe_description: str,
        duration_minutes: int = 30,
        energy_pattern: str = "wave",
        name: Optional[str] = None,
        track_length_seconds: Optional[int] = None,
    ) -> DJSet:
        """Generate a complete DJ set with pre-planned transitions"""
        
        start_time = datetime.now()
        logger.info(
            f"🎵 Generating DJ set: '{vibe_description}' ({duration_minutes} min)"
        )
        logger.info(f"   Energy pattern: {energy_pattern}")
        if track_length_seconds:
            logger.info(f"   Track length limit: {track_length_seconds} seconds")
        logger.info(f"   Started at: {start_time.isoformat()}")

        # Let the AI determine the optimal number of tracks based on the vibe and duration
        # The AI will consider factors like energy pattern, mixing style, and genre
        # to intelligently decide track count rather than using a fixed formula
        track_count = None  # Let the AI decide based on context

        # Generate playlist using DJ agent
        logger.info(f"📋 Generating AI-optimized playlist for {duration_minutes} minutes...")
        logger.info(f"   Thread ID: djset-{datetime.now().timestamp()}")
        
        playlist_start = datetime.now()
        playlist_result = await self.dj_agent.generate_playlist(
            vibe_description=vibe_description,
            duration_minutes=duration_minutes,  # Pass duration instead of track count
            energy_pattern=energy_pattern,
            thread_id=f"djset-{datetime.now().timestamp()}",
        )
        playlist_duration = (datetime.now() - playlist_start).total_seconds()
        
        if not playlist_result["success"]:
            logger.error(f"❌ Playlist generation failed after {playlist_duration:.1f}s")
            logger.error(f"   Error: {playlist_result.get('error')}")
            logger.error(f"   Full result: {playlist_result}")
            raise Exception(
                f"Failed to generate playlist: {playlist_result.get('error')}"
            )

        # Get the finalized playlist
        finalized_playlist = playlist_result.get("finalized_playlist", [])
        if not finalized_playlist:
            logger.error("❌ No tracks in generated playlist")
            logger.error(f"   Playlist result keys: {list(playlist_result.keys())}")
            raise Exception("No tracks in generated playlist")

        logger.info(f"✅ Generated playlist with {len(finalized_playlist)} tracks in {playlist_duration:.1f}s")
        
        # Log track titles for debugging
        for i, track in enumerate(finalized_playlist[:5]):  # First 5 tracks
            logger.info(f"   Track {i+1}: {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')}")
        if len(finalized_playlist) > 5:
            logger.info(f"   ... and {len(finalized_playlist) - 5} more tracks")

        # Load full track information from database
        logger.info("📚 Loading track metadata from database...")
        metadata_start = datetime.now()
        tracks_with_metadata = await self._load_track_metadata(finalized_playlist)
        metadata_duration = (datetime.now() - metadata_start).total_seconds()
        logger.info(f"✅ Loaded metadata for {len(tracks_with_metadata)} tracks in {metadata_duration:.1f}s")

        # Get transitions from the AI-generated playlist
        logger.info(f"🔄 Extracting AI-planned transitions from playlist result...")
        transitions_start = datetime.now()
        
        # The DJ agent should have already planned transitions in the playlist result
        ai_transitions = playlist_result.get("transitions", [])
        if not ai_transitions:
            logger.warning("⚠️ No transitions found in AI playlist result, this is unexpected")
            # TODO: Could call dj_agent to plan transitions here, but this shouldn't happen
            transitions = []
        else:
            logger.info(f"✅ Found {len(ai_transitions)} AI-planned transitions")
            transitions = ai_transitions
            
        transitions_duration = (datetime.now() - transitions_start).total_seconds()
        logger.info(f"✅ Extracted transitions in {transitions_duration:.1f}s")

        # Calculate exact timing for the entire set
        logger.info("⏱️ Calculating set timing and deck assignments...")
        timing_start = datetime.now()
        dj_set_tracks, dj_set_transitions = await self._calculate_set_timing(
            tracks_with_metadata, transitions, duration_minutes * 60, track_length_seconds
        )
        timing_duration = (datetime.now() - timing_start).total_seconds()
        logger.info(f"✅ Calculated timing for {len(dj_set_tracks)} tracks in {timing_duration:.1f}s")

        # Create the DJ set object
        set_id = str(uuid.uuid4())
        set_name = name or f"DJ Set - {vibe_description[:30]}"

        # Calculate total actual duration
        if dj_set_tracks:
            total_duration = max(t.end_time for t in dj_set_tracks)
        else:
            total_duration = 0

        # Extract energy graph from AI insights
        ai_insights = playlist_result.get("ai_insights", {})
        energy_graph = ai_insights.get("energy_graph", [])

        # If no energy graph provided, create a default one
        if not energy_graph and dj_set_tracks:
            # Create steady energy level for all tracks
            energy_graph = [0.5] * len(dj_set_tracks)

        dj_set = DJSet(
            id=set_id,
            name=set_name,
            vibe_description=vibe_description,
            total_duration=total_duration,
            track_count=len(dj_set_tracks),
            energy_pattern=energy_pattern,
            tracks=dj_set_tracks,
            transitions=dj_set_transitions,
            energy_graph=energy_graph,
            key_moments=ai_insights.get("key_moments", []),
            mixing_style=ai_insights.get("mixing_style", "smooth"),
            ai_insights=ai_insights,
        )

        logger.info(f"🎉 DJ Set created: {set_name} ({total_duration / 60:.1f} min)")
        
        # Store the DJ set in memory
        self._dj_sets[set_id] = dj_set
        
        # Pre-render the audio immediately after generation
        logger.info(f"🎵 Pre-rendering audio for DJ set: {set_name}")
        try:
            from services.service_manager import service_manager
            audio_prerenderer = await service_manager.get_audio_prerenderer()
            await audio_prerenderer.prerender_dj_set(dj_set)
            logger.info(f"✅ Audio pre-rendering started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start audio pre-rendering: {e}")
            # Continue anyway - audio will be rendered on demand
        
        # Log total generation time
        total_generation_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 Total generation time: {total_generation_time:.1f}s")
        logger.info(f"   - Playlist generation: {playlist_duration:.1f}s")
        logger.info(f"   - Metadata loading: {metadata_duration:.1f}s")
        logger.info(f"   - Transition planning: {transitions_duration:.1f}s")
        logger.info(f"   - Timing calculation: {timing_duration:.1f}s")
        logger.info(f"   Set ID: {set_id}")
        
        return dj_set

    async def _load_track_metadata(self, playlist: List[Dict]) -> List[Dict]:
        """Load full track metadata from database"""

        db_path = os.path.join(os.path.dirname(__file__), "..", "tracks.db")
        logger.debug(f"   Database path: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        tracks_with_metadata = []
        missing_tracks = []

        for item in playlist:
            filepath = item.get("filepath")
            if not filepath:
                logger.warning(f"   ⚠️ Missing filepath for track: {item}")
                continue

            cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (filepath,))
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()

            if row:
                track = dict(zip(columns, row))
                # Add playlist-specific info
                track["order"] = item.get("order", len(tracks_with_metadata) + 1)
                track["mixing_note"] = item.get("mixing_note", "")
                track["playlist_energy"] = item.get(
                    "energy", track.get("energy_level", 0.5)
                )
                
                # Parse hot_cues JSON if present
                if track.get("hot_cues") and isinstance(track["hot_cues"], str):
                    try:
                        track["hot_cues"] = json.loads(track["hot_cues"])
                    except (json.JSONDecodeError, TypeError):
                        track["hot_cues"] = []
                        logger.warning(f"   ⚠️ Failed to parse hot_cues for: {track.get('title', filepath)}")
                else:
                    track["hot_cues"] = []
                
                tracks_with_metadata.append(track)
                logger.debug(f"   ✓ Loaded metadata for: {track.get('title', filepath)}")
            else:
                missing_tracks.append(filepath)
                logger.warning(f"   ❌ Track not found in database: {filepath}")

        cursor.close()
        conn.close()

        if missing_tracks:
            logger.warning(f"   ⚠️ {len(missing_tracks)} tracks not found in database")

        return tracks_with_metadata
    
    def _extract_mix_cue_points(self, track: Dict) -> Tuple[float, float]:
        """Extract Mix In and Mix Out times from hot cues.
        
        Returns:
            Tuple of (mix_in_time, mix_out_time) in seconds
        """
        hot_cues = track.get("hot_cues", [])
        
        mix_in_time = None
        mix_out_time = None
        
        # Look for specific Mix In/Out cues
        for cue in hot_cues:
            cue_name = cue.get("name", "").lower()
            if "mix in" in cue_name or cue_name == "intro":
                mix_in_time = cue.get("time", 0.0)
                logger.debug(f"   🎯 Found Mix In cue at {mix_in_time:.1f}s")
            elif "mix out" in cue_name or cue_name == "outro":
                mix_out_time = cue.get("time")
                logger.debug(f"   🎯 Found Mix Out cue at {mix_out_time:.1f}s")
        
        # Get track duration for fallback calculations
        duration = track.get("duration", 240.0)
        
        # Fallback to intelligent defaults if cues not found
        if mix_in_time is None:
            # Default to 10% in (typically after intro)
            mix_in_time = duration * 0.1
            logger.debug(f"   📐 Using default Mix In at {mix_in_time:.1f}s (10% of track)")
            
        if mix_out_time is None:
            # Default to 90% out (before outro)
            mix_out_time = duration * 0.9
            logger.debug(f"   📐 Using default Mix Out at {mix_out_time:.1f}s (90% of track)")
        
        # Ensure mix_out is after mix_in
        if mix_out_time <= mix_in_time:
            logger.warning(f"   ⚠️ Invalid cue points: mix_out ({mix_out_time}) <= mix_in ({mix_in_time}), using defaults")
            mix_in_time = duration * 0.1
            mix_out_time = duration * 0.9
            
        return mix_in_time, mix_out_time


    async def _calculate_set_timing(
        self,
        tracks: List[Dict],
        transitions: List[Union[TransitionPlan, Dict]],
        target_duration: float,
        track_length_seconds: Optional[int] = None,
    ) -> Tuple[List[DJSetTrack], List[DJSetTransition]]:
        """Calculate exact timing for all tracks and transitions"""

        dj_set_tracks = []
        dj_set_transitions = []

        # AI-driven deck assignment considering track characteristics and transitions
        # For now, use alternating pattern but this could be enhanced with AI logic
        # that considers track key compatibility, energy levels, and mixing strategy
        deck_assignment = []
        for i in range(len(tracks)):
            # Alternate between decks for smooth mixing
            # Future: AI could assign decks based on harmonic mixing rules
            deck = "A" if i % 2 == 0 else "B"
            deck_assignment.append(deck)

        current_time = 0.0

        for i, track in enumerate(tracks):
            # Get hot cue points for this track
            mix_in_time, mix_out_time = self._extract_mix_cue_points(track)
            
            # Calculate effective duration based on hot cues
            full_duration = track.get("duration", 240.0)
            hot_cue_duration = mix_out_time - mix_in_time
            
            # Log hot cue usage
            logger.info(f"   🎯 Track {i+1} hot cues: Mix In at {mix_in_time:.1f}s, Mix Out at {mix_out_time:.1f}s")
            logger.info(f"      Effective duration: {hot_cue_duration:.1f}s (was {full_duration:.1f}s full)")
            
            # Apply track length limit if specified (to hot cue duration)
            if track_length_seconds and hot_cue_duration > track_length_seconds:
                logger.info(f"   Limiting track {i+1} from {hot_cue_duration:.1f}s to {track_length_seconds}s")
                # Adjust mix_out_time to respect the limit
                mix_out_time = mix_in_time + track_length_seconds
                hot_cue_duration = track_length_seconds

            # Assign deck
            deck = deck_assignment[i]

            # Calculate start and end times in the mix
            start_time = current_time
            
            # Store hot cue info for later use
            track["mix_in_time"] = mix_in_time
            track["mix_out_time"] = mix_out_time

            # For transitions, we need overlap
            if i < len(transitions):
                transition = transitions[i]
                
                # Handle both TransitionPlan objects and dictionaries
                if isinstance(transition, dict):
                    overlap_duration = transition.get("crossfade_duration", 8.0)
                else:
                    overlap_duration = transition.crossfade_duration

                # The track plays from hot cue in to hot cue out, fading during transition
                fade_out_time = start_time + hot_cue_duration - overlap_duration
                end_time = start_time + hot_cue_duration

                # Next track starts during the overlap
                if i == 0:
                    # First track starts immediately
                    fade_in_time = start_time
                else:
                    # Subsequent tracks fade in during previous track's fade out
                    fade_in_time = fade_out_time
            else:
                # Last track - no transition out
                fade_in_time = start_time if i == 0 else start_time
                fade_out_time = start_time + hot_cue_duration - 10  # 10s fade at end
                end_time = start_time + hot_cue_duration

            # Create DJSetTrack
            dj_track = DJSetTrack(
                order=i + 1,
                filepath=track["filepath"],
                deck=deck,
                start_time=start_time,
                end_time=end_time,
                fade_in_time=fade_in_time,
                fade_out_time=fade_out_time,
                title=track.get("title"),
                artist=track.get("artist"),
                bpm=track.get("bpm", 120),
                key=track.get("key"),
                energy_level=track.get("energy_level", 0.5),
                mixing_note=track.get("mixing_note", ""),
                tempo_adjust=0.0,  # Can be calculated based on BPM matching
                gain_adjust=1.0,
                eq_low=0.0,
                eq_mid=0.0,
                eq_high=0.0,
                hot_cue_in_offset=mix_in_time,  # Where to start in the audio file
                hot_cue_out_offset=mix_out_time,  # Where to end in the audio file
            )

            dj_set_tracks.append(dj_track)

            # Create transition if not the last track
            if i < len(transitions):
                transition = transitions[i]
                next_deck = deck_assignment[i + 1]

                # Handle both TransitionPlan objects and dictionaries
                if isinstance(transition, dict):
                    # Extract properties from dictionary
                    # CRITICAL FIX: Effects are nested under "effect_plan" in AI output
                    effect_plan = transition.get("effect_plan", {})
                    effects_data = effect_plan.get("effects", [])
                    
                    # Log the extraction for debugging
                    logger.info(f"   📦 Extracting effects from transition {i+1}:")
                    logger.info(f"      Raw transition keys: {list(transition.keys())}")
                    if "effect_plan" in transition:
                        logger.info(f"      Effect plan keys: {list(effect_plan.keys())}")
                        logger.info(f"      Found {len(effects_data)} effects: {[e.get('type', 'unknown') for e in effects_data if isinstance(e, dict)]}")
                    else:
                        logger.warning(f"      ⚠️ No effect_plan found in transition!")
                    
                    crossfade_duration = transition.get("crossfade_duration", 8.0)
                    transition_type = transition.get("transition_type", "smooth_fade")
                    technique_notes = transition.get("technique_notes", "")
                    risk_level = transition.get("risk_level", "low")
                    compatibility_score = transition.get("compatibility_score", 0.8)
                else:
                    # Use TransitionPlan object properties
                    effects_data = transition.effects
                    crossfade_duration = transition.crossfade_duration
                    transition_type = transition.transition_type
                    technique_notes = transition.technique_notes
                    risk_level = transition.risk_level
                    compatibility_score = transition.compatibility_score

                # Validate and fix effects with proper error handling
                validated_effects = []
                logger.info(f"   🔍 Validating {len(effects_data)} effects for transition {i+1}")
                
                for effect_idx, effect in enumerate(effects_data):
                    try:
                        if isinstance(effect, TransitionEffect):
                            validated_effects.append(effect)
                            logger.info(f"      ✅ Effect {effect_idx+1}: {effect.type} (already validated)")
                        elif isinstance(effect, dict):
                            # Ensure all required fields exist with defaults
                            effect_type = effect.get('type', 'filter_sweep')
                            effect_dict = {
                                'type': effect_type,
                                'start_at': float(effect.get('start_at', 0.0)),
                                'duration': float(effect.get('duration', 3.0)),
                                'intensity': float(effect.get('intensity', 0.5))  # Increased default intensity
                            }
                            validated_effect = TransitionEffect(**effect_dict)
                            validated_effects.append(validated_effect)
                            logger.info(f"      ✅ Effect {effect_idx+1}: {effect_type} validated (intensity={effect_dict['intensity']})")
                        else:
                            logger.warning(f"      ⚠️ Unknown effect type: {type(effect)}")
                            # Add default effect as fallback
                            validated_effects.append(TransitionEffect(
                                type='filter_sweep',
                                start_at=0.0,
                                duration=3.0,
                                intensity=0.5
                            ))
                    except Exception as e:
                        logger.error(f"      ❌ Failed to validate effect {effect_idx+1}: {e}")
                        logger.error(f"         Raw effect data: {effect}")
                        # Add a default effect as fallback
                        validated_effects.append(TransitionEffect(
                            type='filter_sweep',
                            start_at=0.0,
                            duration=3.0,
                            intensity=0.5
                        ))
                
                logger.info(f"   📦 Total validated effects: {len(validated_effects)}")
                if len(validated_effects) == 0:
                    logger.warning(f"   ⚠️ No effects validated! Adding default filter_sweep")
                    validated_effects.append(TransitionEffect(
                        type='filter_sweep',
                        start_at=0.0,
                        duration=crossfade_duration,
                        intensity=0.7
                    ))

                dj_transition = DJSetTransition(
                    from_track_order=i + 1,
                    to_track_order=i + 2,
                    from_deck=deck,
                    to_deck=next_deck,
                    start_time=fade_out_time,
                    duration=crossfade_duration,
                    type=transition_type,
                    effects=validated_effects,
                    crossfade_curve="s-curve",
                    technique_notes=technique_notes,
                    risk_level=risk_level,
                    compatibility_score=compatibility_score,
                    outro_cue=0.9,  # Start outro at 90% of track
                    intro_cue=0.1,  # Start intro at 10% of next track
                )

                dj_set_transitions.append(dj_transition)

                # Update current time for next track (with overlap)
                current_time = fade_out_time
            else:
                # Last track - advance time to its end
                current_time = end_time

        # Adjust timing if we're significantly over target duration
        if current_time > target_duration * 1.2:  # 20% over
            logger.warning(
                f"⚠️ Set duration ({current_time / 60:.1f} min) exceeds target ({target_duration / 60:.1f} min)"
            )

        return dj_set_tracks, dj_set_transitions

    def get_dj_set(self, set_id: str) -> Optional[DJSet]:
        """Get a DJ set by ID"""
        return self._dj_sets.get(set_id)

    def get_playback_state(self, set_id: str) -> Optional[DJSetPlaybackState]:
        """Get current playback state for a DJ set"""
        return self._playback_states.get(set_id)

    def create_playback_state(self, dj_set: DJSet) -> DJSetPlaybackState:
        """Create a new playback state for a DJ set"""

        state = DJSetPlaybackState(
            set_id=dj_set.id,
            is_playing=False,
            is_paused=False,
            elapsed_time=0.0,
            current_track_order=1,
            next_track_order=2 if len(dj_set.tracks) > 1 else None,
            active_decks=[],
            primary_deck=dj_set.tracks[0].deck if dj_set.tracks else "A",
            in_transition=False,
            transition_progress=0.0,
            next_transition_in=dj_set.transitions[0].start_time
            if dj_set.transitions
            else None,
        )

        self._playback_states[dj_set.id] = state
        return state

    def update_playback_state(
        self, set_id: str, **updates
    ) -> Optional[DJSetPlaybackState]:
        """Update playback state"""

        state = self._playback_states.get(set_id)
        if not state:
            return None

        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.last_update = datetime.now()
        return state

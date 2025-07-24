"""
Set Playback Controller - Orchestrates DJ set playback with automatic transitions.
"""

import asyncio
import logging
from typing import Dict, List
from datetime import datetime
import time

from models.dj_set_models import DJSet, DJSetTrack, DJSetTransition, DJSetPlaybackState
from models.mix_models import EffectType
from services.dj_set_service import DJSetService
from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager
from services.effect_manager import EffectManager
from services.transition_executor import TransitionExecutor
from services.audio_engine import AudioEngine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🎮 [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class SetPlaybackController:
    """Controller for playing pre-planned DJ sets"""

    def __init__(
        self,
        deck_manager: DeckManager,
        mixer_manager: MixerManager,
        effect_manager: EffectManager,
        audio_engine: AudioEngine,
        dj_set_service: DJSetService,
    ):
        self.deck_manager = deck_manager
        self.mixer_manager = mixer_manager
        self.effect_manager = effect_manager
        self.audio_engine = audio_engine
        self.dj_set_service = dj_set_service

        # Transition executor for handling transitions
        self.transition_executor = TransitionExecutor(
            deck_manager, mixer_manager, effect_manager
        )

        # Active playback sessions
        self._active_sessions: Dict[str, asyncio.Task] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}

        logger.info("🎮 SetPlaybackController initialized")
    
    def _map_effect_type(self, effect_type_str: str) -> EffectType:
        """Map DJ LLM effect type strings to EffectType enums"""
        mapping = {
            # Legacy mapping
            "filter": EffectType.FILTER_SWEEP,
            # Current effect types
            "filter_sweep": EffectType.FILTER_SWEEP,
            "echo": EffectType.ECHO,
            "reverb": EffectType.REVERB,
            "delay": EffectType.DELAY,
            "gate": EffectType.GATE,
            "flanger": EffectType.FLANGER,
            "eq_sweep": EffectType.EQ_SWEEP,
            "scratch": EffectType.SCRATCH,
        }
        
        effect_type = mapping.get(effect_type_str.lower())
        if not effect_type:
            logger.warning(f"⚠️ Unknown effect type: {effect_type_str}, defaulting to FILTER_SWEEP")
            return EffectType.FILTER_SWEEP
            
        return effect_type

    async def start_playback(self, dj_set: DJSet) -> str:
        """Start playing a DJ set"""

        set_id = dj_set.id

        # Check if already playing
        if set_id in self._active_sessions:
            logger.warning(f"🎮 Set {set_id} is already playing")
            return set_id

        # Note: Pre-rendering is now done before this method is called
        logger.info(f"🎮 Starting playback for pre-rendered DJ set: {dj_set.name}")

        # Create playback state
        playback_state = self.dj_set_service.create_playback_state(dj_set)
        playback_state.is_playing = True
        playback_state.started_at = datetime.now()

        # Create session lock
        self._session_locks[set_id] = asyncio.Lock()

        # Start playback task (for state tracking, not actual audio)
        session_task = asyncio.create_task(self._playback_loop(dj_set, playback_state))
        self._active_sessions[set_id] = session_task

        logger.info(f"🎮 Started playback of DJ set: {dj_set.name}")
        return set_id

    async def stop_playback(self, set_id: str) -> bool:
        """Stop playing a DJ set"""

        if set_id not in self._active_sessions:
            logger.warning(f"🎮 Set {set_id} is not playing")
            return False

        # Cancel the playback task
        session_task = self._active_sessions[set_id]
        session_task.cancel()

        try:
            await session_task
        except asyncio.CancelledError:
            pass

        # Clean up
        del self._active_sessions[set_id]
        del self._session_locks[set_id]

        # Update playback state
        self.dj_set_service.update_playback_state(
            set_id, is_playing=False, is_paused=False
        )

        # Stop all decks
        for deck_id in ["A", "B", "C", "D"]:
            await self.deck_manager.update_deck_state(deck_id, {"is_playing": False})

        logger.info(f"🎮 Stopped playback of set {set_id}")
        return True

    async def pause_playback(self, set_id: str) -> bool:
        """Pause playback"""

        state = self.dj_set_service.get_playback_state(set_id)
        if not state or not state.is_playing:
            return False

        self.dj_set_service.update_playback_state(set_id, is_paused=True)

        # Pause active decks
        for deck_id in state.active_decks:
            await self.deck_manager.update_deck_state(deck_id, {"is_playing": False})

        logger.info(f"🎮 Paused playback of set {set_id}")
        return True

    async def resume_playback(self, set_id: str) -> bool:
        """Resume playback"""

        state = self.dj_set_service.get_playback_state(set_id)
        if not state or not state.is_paused:
            return False

        self.dj_set_service.update_playback_state(set_id, is_paused=False)

        # Resume active decks
        for deck_id in state.active_decks:
            await self.deck_manager.update_deck_state(deck_id, {"is_playing": True})

        logger.info(f"🎮 Resumed playback of set {set_id}")
        return True

    async def _playback_loop(self, dj_set: DJSet, state: DJSetPlaybackState):
        """Main playback loop for a DJ set"""

        set_id = dj_set.id
        start_time = time.time()

        try:
            logger.info(f"🎮 Starting playback loop for {dj_set.name}")

            # Pre-load first track
            first_track = dj_set.tracks[0]
            await self._load_track_on_deck(first_track)

            # Start playing first track
            logger.info(f"🎮 Starting playback of first track on deck {first_track.deck}")
            await self.deck_manager.update_deck_state(first_track.deck, {"is_playing": True})
            state.active_decks = [first_track.deck]
            
            # Verify deck is playing
            deck_state = await self.deck_manager.get_deck_state(first_track.deck)
            logger.info(f"🎮 Deck {first_track.deck} state after start: {deck_state}")
            
            # CRITICAL: Force audio engine to sync state immediately
            if self.audio_engine:
                logger.info(f"🎮 Forcing audio engine sync for deck {first_track.deck}")
                
                # Safely sync states if method exists
                if hasattr(self.audio_engine, '_sync_states'):
                    try:
                        await self.audio_engine._sync_states()
                    except Exception as e:
                        logger.warning(f"Failed to sync audio engine states: {e}")
                
                # Clear any silence buffers from the audio queue
                if hasattr(self.audio_engine, 'clear_audio_queue'):
                    try:
                        cleared_buffers = self.audio_engine.clear_audio_queue()
                        logger.info(f"🎮 Cleared {cleared_buffers} silence buffers from audio queue")
                    except Exception as e:
                        logger.warning(f"Failed to clear audio queue: {e}")
                
                # Set deck state through proper interface if available
                try:
                    if hasattr(self.audio_engine, '_processing_lock') and hasattr(self.audio_engine, '_audio_decks'):
                        with self.audio_engine._processing_lock:
                            if first_track.deck in self.audio_engine._audio_decks:
                                self.audio_engine._audio_decks[first_track.deck].is_playing = True
                                logger.info(f"🎮 Audio engine deck {first_track.deck} is_playing set to True")
                            else:
                                logger.warning(f"Deck {first_track.deck} not found in audio engine")
                    else:
                        logger.warning("Audio engine missing expected attributes for direct deck control")
                except Exception as e:
                    logger.error(f"Failed to set deck playing state: {e}")
            
            # Small delay to ensure synchronization and let fresh audio generate
            await asyncio.sleep(0.5)

            # Main playback loop
            while state.is_playing and state.current_track_order <= len(dj_set.tracks):
                # Handle pause
                while state.is_paused:
                    await asyncio.sleep(0.1)

                # Update elapsed time
                current_time = time.time()
                state.elapsed_time = current_time - start_time

                # Get current and next tracks
                current_track_idx = state.current_track_order - 1
                current_track = dj_set.tracks[current_track_idx]

                # Check if we need to load the next track
                if state.next_track_order and state.next_track_order <= len(
                    dj_set.tracks
                ):
                    next_track_idx = state.next_track_order - 1
                    next_track = dj_set.tracks[next_track_idx]

                    # Load next track 10 seconds before transition
                    if state.next_transition_in and state.next_transition_in <= 10:
                        if next_track.deck not in state.active_decks:
                            await self._load_track_on_deck(next_track)
                            state.active_decks.append(next_track.deck)
                            logger.info(
                                f"🎮 Pre-loaded track {next_track.order} on deck {next_track.deck}"
                            )

                # Check if we need to start a transition
                transition_idx = current_track_idx
                if transition_idx < len(dj_set.transitions):
                    transition = dj_set.transitions[transition_idx]

                    # Start transition when it's time
                    if (
                        state.elapsed_time >= transition.start_time
                        and not state.in_transition
                    ):
                        await self._execute_transition(dj_set, transition, state)

                # Update next transition timing
                if not state.in_transition and transition_idx < len(dj_set.transitions):
                    state.next_transition_in = (
                        dj_set.transitions[transition_idx].start_time
                        - state.elapsed_time
                    )
                else:
                    state.next_transition_in = None

                # Check if current track has ended
                if state.elapsed_time >= current_track.end_time:
                    # Move to next track
                    if state.current_track_order < len(dj_set.tracks):
                        # Stop the outgoing deck
                        await self.deck_manager.update_deck_state(current_track.deck, {"is_playing": False})
                        
                        # Safely remove deck from active_decks
                        if current_track.deck in state.active_decks:
                            state.active_decks.remove(current_track.deck)
                        else:
                            logger.warning(f"🎮 Deck {current_track.deck} not in active_decks when trying to remove")

                        # Update state
                        state.current_track_order += 1
                        state.next_track_order = (
                            state.current_track_order + 1
                            if state.current_track_order < len(dj_set.tracks)
                            else None
                        )

                        # Update primary deck
                        if state.active_decks:
                            state.primary_deck = state.active_decks[0]

                        logger.info(f"🎮 Advanced to track {state.current_track_order}")
                    else:
                        # Set has ended
                        logger.info(f"🎮 DJ set {dj_set.name} completed")
                        break

                # Update state
                state_dict = state.dict()
                # Remove set_id from state dict to avoid duplicate argument
                state_dict.pop('set_id', None)
                self.dj_set_service.update_playback_state(set_id, **state_dict)

                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info(f"🎮 Playback loop cancelled for {dj_set.name}")
            raise
        except Exception as e:
            logger.error(f"🎮 Error in playback loop: {e}")
            raise
        finally:
            # Clean up
            state.is_playing = False
            state.is_paused = False

            # Stop all decks
            for deck_id in ["A", "B", "C", "D"]:
                try:
                    await self.deck_manager.update_deck_state(deck_id, {"is_playing": False})
                except:
                    pass

    async def _load_track_on_deck(self, track: DJSetTrack):
        """Load a track onto its assigned deck"""

        logger.info(
            f"🎮 Loading track {track.order}: {track.title} on deck {track.deck}"
        )

        # Load track
        result = await self.deck_manager.load_track(
            deck_id=track.deck, track_filepath=track.filepath
        )
        logger.info(f"🎮 Load result: {result}")

        # Also load into audio engine
        if self.audio_engine:
            audio_result = await self.audio_engine.load_track(track.deck, track.filepath)
            logger.info(f"🎮 Audio engine load result: {audio_result}")
        else:
            logger.warning("🎮 No audio engine available for track loading!")

        # Set initial parameters
        await self.deck_manager.update_deck_state(
            deck_id=track.deck,
            updates={
                "volume": 1.0,
                "gain": track.gain_adjust,
                "tempo_adjust": track.tempo_adjust,
                "eq_low": track.eq_low,
                "eq_mid": track.eq_mid,
                "eq_high": track.eq_high,
            }
        )
        
        logger.info(f"🎮 Track {track.order} loaded and configured on deck {track.deck}")

    async def _execute_transition(
        self, dj_set: DJSet, transition: DJSetTransition, state: DJSetPlaybackState
    ):
        """Execute a pre-planned transition"""

        logger.info(
            f"🎮 Starting transition from track {transition.from_track_order} to {transition.to_track_order}"
        )

        state.in_transition = True
        state.transition_progress = 0.0

        # Get track info
        from_track = dj_set.tracks[transition.from_track_order - 1]
        to_track = dj_set.tracks[transition.to_track_order - 1]

        # Start the incoming track (cued)
        await self.deck_manager.update_deck_state(to_track.deck, {"is_playing": True})
        
        # Add the incoming deck to active_decks if not already there
        if to_track.deck not in state.active_decks:
            state.active_decks.append(to_track.deck)

        # Create transition config
        transition_config = {
            "from_deck": transition.from_deck,
            "to_deck": transition.to_deck,
            "duration": transition.duration,
            "type": transition.type,
            "effects": [
                {
                    "effect_type": self._map_effect_type(effect.type),
                    "start_at": effect.start_at,
                    "duration": effect.duration,
                    "intensity": effect.intensity,
                }
                for effect in transition.effects
            ],
            "crossfade_curve": transition.crossfade_curve,
            "auto_execute": True,
        }

        # Execute the transition
        try:
            # Start transition in background
            transition_task = asyncio.create_task(
                self.transition_executor.execute_transition(transition_config)
            )

            # Monitor transition progress
            while state.in_transition:
                # Check if transition is complete
                if transition_task.done():
                    break

                # Update progress (rough estimate based on time)
                elapsed = time.time() - (
                    state.started_at.timestamp() + transition.start_time
                )
                state.transition_progress = min(1.0, elapsed / transition.duration)

                await asyncio.sleep(0.1)

            # Wait for transition to complete
            await transition_task

            # Update state
            state.in_transition = False
            state.transition_progress = 0.0
            state.primary_deck = to_track.deck

            logger.info("🎮 Transition completed successfully")

        except Exception as e:
            logger.error(f"🎮 Error during transition: {e}")
            state.in_transition = False
            state.transition_progress = 0.0

    def get_active_sessions(self) -> List[str]:
        """Get list of active playback session IDs"""
        return list(self._active_sessions.keys())

    def is_playing(self, set_id: str) -> bool:
        """Check if a set is currently playing"""
        return set_id in self._active_sessions

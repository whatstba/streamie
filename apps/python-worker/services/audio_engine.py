"""
Audio Engine Service - Real-time audio mixing engine that bridges deck/mixer state with audio processing.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Optional, Tuple, AsyncGenerator
import time
import threading
import queue
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import os
import librosa

from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager
from services.effect_manager import EffectManager
from models.effect_models import EffectState
from models.mix_models import EffectType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler for audio engine logs
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🎵 [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


@dataclass
class AudioDeckState:
    """Internal audio state for a deck"""

    deck_id: str
    audio_data: Optional[np.ndarray] = None
    sample_rate: int = 44100
    position_frames: int = 0
    is_playing: bool = False
    tempo_adjust: float = 0.0  # -0.5 to 0.5
    volume: float = 1.0
    gain: float = 1.0
    eq_low: float = 0.0
    eq_mid: float = 0.0
    eq_high: float = 0.0
    filepath: Optional[str] = None
    original_bpm: float = 120.0

    # Cue and loop points
    cue_points: Dict[int, float] = None
    loop_in: Optional[float] = None
    loop_out: Optional[float] = None
    is_looping: bool = False

    def __post_init__(self):
        if self.cue_points is None:
            self.cue_points = {}


class AudioEngine:
    """
    Core audio mixing engine that processes multiple decks in real-time.
    Bridges the gap between database-backed state and actual audio processing.
    """

    def __init__(
        self,
        deck_manager: DeckManager,
        mixer_manager: MixerManager,
        effect_manager: EffectManager,
        sample_rate: int = 44100,
        buffer_size: int = 1024,
    ):
        self.deck_manager = deck_manager
        self.mixer_manager = mixer_manager
        self.effect_manager = effect_manager
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Audio deck states
        self._audio_decks: Dict[str, AudioDeckState] = {
            "A": AudioDeckState("A", sample_rate=sample_rate),
            "B": AudioDeckState("B", sample_rate=sample_rate),
            "C": AudioDeckState("C", sample_rate=sample_rate),
            "D": AudioDeckState("D", sample_rate=sample_rate),
        }

        # Audio processing thread
        self._processing_thread: Optional[threading.Thread] = None
        self._audio_queue = queue.Queue(maxsize=50)
        self._running = False
        self._processing_lock = threading.Lock()

        # Thread pool for CPU-intensive operations
        self._thread_pool = ThreadPoolExecutor(max_workers=4)

        # Sync state
        self._last_sync_time = 0
        self._sync_interval = 0.1  # Sync with DB every 100ms

        # Audio cache for loaded tracks
        self._audio_cache: Dict[str, Tuple[np.ndarray, int]] = {}
        self._cache_lock = threading.Lock()

        # EQ filter coefficients (will be initialized on first use)
        self._eq_filters = {}

        # Current mixer state (for thread-safe access)
        self._current_crossfader = 0.0
        self._current_master_volume = 1.0

        logger.info("🎵 AudioEngine initialized")

    async def start(self):
        """Start the audio processing engine"""
        if self._running:
            logger.warning("🎵 AudioEngine already running")
            return

        self._running = True

        # Start processing thread
        self._processing_thread = threading.Thread(
            target=self._audio_processing_loop, daemon=True
        )
        self._processing_thread.start()

        # Start sync task - don't wait for it
        self._sync_task = asyncio.create_task(self._sync_loop())

        logger.info("🎵 AudioEngine started")

    async def stop(self):
        """Stop the audio processing engine"""
        self._running = False

        # Cancel sync task
        if hasattr(self, "_sync_task") and self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        if self._processing_thread:
            self._processing_thread.join(timeout=2.0)

        # Clear audio queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)

        logger.info("🎵 AudioEngine stopped")

    async def load_track(self, deck_id: str, filepath: str) -> Dict:
        """Load a track into the audio engine"""
        try:
            # Resolve filepath to absolute path
            if os.path.isabs(filepath):
                file_path = filepath
            else:
                # Try relative to music directory (Downloads)
                music_dir = os.path.expanduser("~/Downloads")
                file_path = os.path.join(music_dir, filepath)

                # If not found, try current directory
                if not os.path.exists(file_path):
                    file_path = os.path.abspath(filepath)

                # If still not found, try Music folder
                if not os.path.exists(file_path):
                    music_path = os.path.expanduser(f"~/Music/{filepath}")
                    if os.path.exists(music_path):
                        file_path = music_path

            # Verify file exists
            if not os.path.exists(file_path):
                logger.error(f"🎵 File not found: {file_path}")
                return {
                    "status": "error",
                    "error": f"File not found: {filepath}",
                    "deck_id": deck_id,
                }

            # Check cache first (use original filepath as key)
            with self._cache_lock:
                if filepath in self._audio_cache:
                    audio_data, sr = self._audio_cache[filepath]
                    logger.info(f"🎵 Loaded track from cache for deck {deck_id}")
                else:
                    # Load audio file asynchronously
                    logger.info(f"🎵 Loading track: {file_path}")

                    # Run librosa.load in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    audio_data, sr = await loop.run_in_executor(
                        self._thread_pool,
                        lambda: librosa.load(file_path, sr=self.sample_rate, mono=False)
                    )

                    # Convert to stereo if mono
                    if audio_data.ndim == 1:
                        audio_data = np.stack([audio_data, audio_data])

                    # Cache the audio
                    self._audio_cache[filepath] = (audio_data, sr)

                    # Limit cache size (keep last 20 tracks)
                    if len(self._audio_cache) > 20:
                        oldest_key = next(iter(self._audio_cache))
                        del self._audio_cache[oldest_key]

            # Update audio deck state
            with self._processing_lock:
                audio_deck = self._audio_decks[deck_id]
                audio_deck.audio_data = audio_data.copy()
                audio_deck.sample_rate = sr
                audio_deck.position_frames = 0
                audio_deck.filepath = filepath

                # Get BPM from deck state
                deck_state = await self.deck_manager.get_deck_state(deck_id)
                if deck_state and deck_state.get("bpm"):
                    audio_deck.original_bpm = deck_state["bpm"]

            duration = len(audio_data[0]) / sr
            logger.info(f"🎵 Track loaded on deck {deck_id}: {duration:.1f}s")

            return {
                "status": "loaded",
                "deck_id": deck_id,
                "duration": duration,
                "sample_rate": sr,
            }

        except Exception as e:
            logger.error(f"🎵 Error loading track: {e}")
            return {"status": "error", "error": str(e), "deck_id": deck_id}

    async def unload_track(self, deck_id: str):
        """Unload track from deck"""
        with self._processing_lock:
            audio_deck = self._audio_decks[deck_id]
            audio_deck.audio_data = None
            audio_deck.position_frames = 0
            audio_deck.is_playing = False
            audio_deck.filepath = None

        logger.info(f"🎵 Track unloaded from deck {deck_id}")

    def _audio_processing_loop(self):
        """Main audio processing thread"""
        logger.info("🎵 Audio processing thread started")

        while self._running:
            try:
                # Generate audio buffer
                buffer = self._generate_mixed_buffer()

                # Queue for streaming
                if not self._audio_queue.full():
                    self._audio_queue.put(buffer)

                # Calculate sleep time based on buffer size
                buffer_duration = self.buffer_size / self.sample_rate
                time.sleep(buffer_duration * 0.5)  # Process ahead

            except Exception as e:
                logger.error(f"🎵 Audio processing error: {e}")
                time.sleep(0.1)

        logger.info("🎵 Audio processing thread stopped")

    def _generate_mixed_buffer(self) -> np.ndarray:
        """Generate a buffer of mixed audio from all decks"""
        # Create output buffer
        output = np.zeros((2, self.buffer_size), dtype=np.float32)

        with self._processing_lock:
            # Get current mixer state
            crossfader = self._current_crossfader
            master_volume = self._current_master_volume

            # Calculate deck gains based on crossfader
            if crossfader < 0:
                gains = {
                    "A": 1.0,
                    "B": 1.0 + crossfader,  # Fade out B
                    "C": 1.0,
                    "D": 1.0 + crossfader,
                }
            else:
                gains = {
                    "A": 1.0 - crossfader,  # Fade out A
                    "B": 1.0,
                    "C": 1.0 - crossfader,
                    "D": 1.0,
                }

            # Process each deck
            for deck_id, audio_deck in self._audio_decks.items():
                if audio_deck.is_playing and audio_deck.audio_data is not None:
                    # Get deck buffer
                    deck_buffer = self._get_deck_buffer(audio_deck)

                    if deck_buffer is not None:
                        # Apply EQ
                        deck_buffer = self._apply_eq(
                            deck_buffer,
                            audio_deck.eq_low,
                            audio_deck.eq_mid,
                            audio_deck.eq_high,
                        )

                        # Apply effects from EffectManager
                        deck_buffer = self._apply_effects(deck_id, deck_buffer)

                        # Apply gain and volume
                        total_gain = (
                            gains.get(deck_id, 1.0)
                            * audio_deck.volume
                            * audio_deck.gain
                        )

                        # Mix into output
                        output += deck_buffer * total_gain

            # Apply master volume and limiting
            output *= master_volume
            output = np.clip(output, -1.0, 1.0)

        return output

    def _get_deck_buffer(self, audio_deck: AudioDeckState) -> Optional[np.ndarray]:
        """Get audio buffer from deck with tempo adjustment"""
        audio_data = audio_deck.audio_data
        if audio_data is None:
            return None

        # Calculate playback rate
        rate = 1.0 + audio_deck.tempo_adjust

        # Calculate frames needed
        frames_needed = int(self.buffer_size * rate)
        total_frames = audio_data.shape[1]

        # Check if we have enough frames
        if audio_deck.position_frames >= total_frames:
            # End of track
            audio_deck.is_playing = False
            audio_deck.position_frames = total_frames - 1
            return np.zeros((2, self.buffer_size), dtype=np.float32)

        # Handle looping
        if audio_deck.is_looping and audio_deck.loop_out is not None:
            loop_out_frames = int(audio_deck.loop_out * total_frames)
            if audio_deck.position_frames + frames_needed >= loop_out_frames:
                # Jump back to loop in point
                loop_in_frames = int(audio_deck.loop_in * total_frames)
                audio_deck.position_frames = loop_in_frames

        # Get available frames
        frames_available = min(frames_needed, total_frames - audio_deck.position_frames)

        if frames_available <= 0:
            return np.zeros((2, self.buffer_size), dtype=np.float32)

        # Extract audio segment
        segment = audio_data[
            :,
            audio_deck.position_frames : audio_deck.position_frames + frames_available,
        ]

        # Apply tempo adjustment if needed
        if rate != 1.0 and segment.shape[1] > 0:
            # Use phase vocoder for time stretching
            segment = librosa.effects.time_stretch(segment, rate=rate)

        # Ensure correct buffer size
        if segment.shape[1] < self.buffer_size:
            # Pad with zeros
            pad_width = self.buffer_size - segment.shape[1]
            segment = np.pad(segment, ((0, 0), (0, pad_width)), mode="constant")
        elif segment.shape[1] > self.buffer_size:
            # Trim to size
            segment = segment[:, : self.buffer_size]

        # Update position
        audio_deck.position_frames += frames_needed

        return segment.astype(np.float32)

    def _apply_eq(
        self, buffer: np.ndarray, low: float, mid: float, high: float
    ) -> np.ndarray:
        """Apply 3-band EQ to buffer"""
        # Simple 3-band EQ using butterworth filters
        # Frequency bands: Low (20-250Hz), Mid (250-4000Hz), High (4000-20000Hz)

        if np.all(low == 0) and np.all(mid == 0) and np.all(high == 0):
            return buffer

        # TODO: Implement proper EQ filtering
        # For now, simple gain adjustment
        return buffer

    def _apply_effects(self, deck_id: str, buffer: np.ndarray) -> np.ndarray:
        """Apply active effects to audio buffer"""
        if not self.effect_manager:
            return buffer

        # Get active effects for this deck
        deck_effects = self.effect_manager.get_deck_effects(deck_id)
        if not deck_effects or not deck_effects.get_active_effects():
            return buffer

        # Process each effect
        processed_buffer = buffer.copy()
        for effect in deck_effects.get_active_effects():
            # Get current effect state
            effect_state = EffectState.from_active_effect(effect)

            # Apply effect based on type and parameters
            processed_buffer = self._process_effect(
                processed_buffer,
                effect.effect_type,
                effect_state.current_parameters,
                effect.intensity,
            )

        return processed_buffer

    def _process_effect(
        self,
        buffer: np.ndarray,
        effect_type: EffectType,
        parameters: Dict[str, float],
        intensity: float,
    ) -> np.ndarray:
        """Process a single effect on the audio buffer"""
        # For now, implement basic effects
        # TODO: Implement proper DSP for each effect type

        if effect_type == EffectType.FILTER_SWEEP:
            # Simple low-pass filter simulation
            cutoff_ratio = parameters.get("frequency", 8000) / 20000
            # Apply simple amplitude reduction for high frequencies
            if cutoff_ratio < 0.8:
                buffer = buffer * (0.7 + 0.3 * cutoff_ratio)

        elif effect_type == EffectType.ECHO:
            # Simple echo effect
            delay_samples = int(
                parameters.get("delay_time", 250) * self.sample_rate / 1000
            )
            feedback = parameters.get("feedback", 0.3)
            mix = parameters.get("mix", 0.3)

            if delay_samples < buffer.shape[1]:
                # Create delayed signal
                delayed = np.zeros_like(buffer)
                delayed[:, delay_samples:] = buffer[:, :-delay_samples] * feedback
                # Mix with original
                buffer = buffer * (1 - mix) + delayed * mix

        elif effect_type == EffectType.REVERB:
            # Simple reverb simulation using multiple delays
            room_size = parameters.get("room_size", 0.5)
            wet_level = parameters.get("wet_level", 0.2)

            # Create simple reverb with multiple delays
            reverb = np.zeros_like(buffer)
            delays = [0.013, 0.027, 0.037, 0.043]  # seconds
            gains = [0.7, 0.5, 0.3, 0.2]

            for delay, gain in zip(delays, gains):
                delay_samples = int(delay * self.sample_rate * room_size)
                if delay_samples < buffer.shape[1]:
                    delayed = np.zeros_like(buffer)
                    delayed[:, delay_samples:] = buffer[:, :-delay_samples] * gain
                    reverb += delayed

            # Mix with original
            buffer = buffer * (1 - wet_level) + reverb * wet_level

        elif effect_type == EffectType.GATE:
            # Simple gate effect
            gate_open = parameters.get("gate_open", 1.0)
            if gate_open < 0.5:
                buffer = buffer * 0.1  # Gate closed

        # More effects can be implemented here...

        return buffer

    async def _sync_loop(self):
        """Synchronize with deck and mixer managers"""
        # Initial delay to let services initialize
        await asyncio.sleep(1.0)

        while self._running:
            try:
                current_time = time.time()
                if current_time - self._last_sync_time >= self._sync_interval:
                    # Use timeout to prevent hanging
                    await asyncio.wait_for(self._sync_states(), timeout=15.0)
                    self._last_sync_time = current_time

                await asyncio.sleep(0.05)

            except asyncio.TimeoutError:
                logger.warning("🎵 Sync states timed out after 15s - deck manager may be busy")
                self._last_sync_time = time.time()
            except Exception as e:
                logger.error(f"🎵 Sync error: {e}")
                await asyncio.sleep(0.5)

    async def _sync_states(self):
        """Sync deck and mixer states from database"""
        # Sync each deck
        for deck_id in ["A", "B", "C", "D"]:
            try:
                # Only sync if deck manager is available
                if not self.deck_manager:
                    continue
                    
                deck_state = await self.deck_manager.get_deck_state(deck_id)
                if deck_state:
                    with self._processing_lock:
                        audio_deck = self._audio_decks[deck_id]

                        # Update playback state
                        audio_deck.is_playing = deck_state.get("is_playing", False)
                        audio_deck.volume = deck_state.get("volume", 1.0)
                        audio_deck.gain = deck_state.get("gain", 1.0)
                        audio_deck.tempo_adjust = deck_state.get("tempo_adjust", 0.0)

                        # Update EQ
                        audio_deck.eq_low = deck_state.get("eq_low", 0.0)
                        audio_deck.eq_mid = deck_state.get("eq_mid", 0.0)
                        audio_deck.eq_high = deck_state.get("eq_high", 0.0)
                        
                        # Remove spammy logging

                        # Load track if needed
                        if (
                            deck_state.get("track_filepath")
                            and audio_deck.filepath != deck_state["track_filepath"]
                        ):
                            # Track changed, load new one
                            # Skip loading during sync to avoid blocking
                            pass

                        # Update position if significantly different
                        if audio_deck.audio_data is not None:
                            db_position = deck_state.get("position_normalized", 0.0)
                            total_frames = audio_deck.audio_data.shape[1]
                            db_position_frames = int(db_position * total_frames)

                            # Only update if difference is significant (> 1 second)
                            frame_diff = abs(
                                audio_deck.position_frames - db_position_frames
                            )
                            if frame_diff > self.sample_rate:
                                audio_deck.position_frames = db_position_frames

            except Exception as e:
                logger.error(f"🎵 Error syncing deck {deck_id}: {e}")

        # Sync mixer state
        try:
            mixer_state = await self.mixer_manager.get_mixer_state()
            if mixer_state:
                # Store mixer state for use in audio processing
                # This will be accessed by the processing thread
                self._current_crossfader = mixer_state.get("crossfader", 0.0)
                self._current_master_volume = mixer_state.get("master_volume", 1.0)
        except Exception as e:
            logger.error(f"🎵 Error syncing mixer state: {e}")

    def get_audio_stream(self) -> Optional[np.ndarray]:
        """Get next audio buffer from queue for streaming"""
        try:
            return self._audio_queue.get_nowait()
        except queue.Empty:
            return None
    
    def clear_audio_queue(self):
        """Clear all buffers from the audio queue"""
        cleared_count = 0
        try:
            while True:
                self._audio_queue.get_nowait()
                cleared_count += 1
        except queue.Empty:
            pass
        
        if cleared_count > 0:
            logger.info(f"🎵 Cleared {cleared_count} buffers from audio queue")
        return cleared_count

    async def get_stream_generator(self) -> AsyncGenerator[np.ndarray, None]:
        """Async generator for audio streaming"""
        logger.info(f"🎵 get_stream_generator called, _running={self._running}")
        
        if not self._running:
            logger.error("🎵 AudioEngine is not running in get_stream_generator!")
            # Yield at least one buffer of silence to prevent hanging
            silence = np.zeros((2, self.buffer_size), dtype=np.float32)
            yield silence
            return
            
        consecutive_silence = 0
        max_silence_buffers = 1000  # About 10 seconds of silence before giving up
        
        while self._running:
            buffer = self.get_audio_stream()
            if buffer is not None:
                consecutive_silence = 0
                # Got audio buffer
                yield buffer
            else:
                # Generate silence if no audio available
                silence = np.zeros((2, self.buffer_size), dtype=np.float32)
                yield silence
                consecutive_silence += 1
                
                # Remove spammy logging
                
                # Prevent infinite silence generation
                if consecutive_silence > max_silence_buffers:
                    logger.error("🎵 Too many consecutive silence buffers, stopping stream")
                    break
                    
                await asyncio.sleep(0.01)

    def get_deck_position(self, deck_id: str) -> float:
        """Get current playback position (0-1) for a deck"""
        with self._processing_lock:
            audio_deck = self._audio_decks[deck_id]
            if audio_deck.audio_data is None:
                return 0.0

            total_frames = audio_deck.audio_data.shape[1]
            return (
                audio_deck.position_frames / total_frames if total_frames > 0 else 0.0
            )

    def seek_deck(self, deck_id: str, position: float):
        """Seek to position (0-1) on a deck"""
        with self._processing_lock:
            audio_deck = self._audio_decks[deck_id]
            if audio_deck.audio_data is not None:
                total_frames = audio_deck.audio_data.shape[1]
                audio_deck.position_frames = int(position * total_frames)
                logger.info(f"🎵 Deck {deck_id} seeked to {position:.2%}")

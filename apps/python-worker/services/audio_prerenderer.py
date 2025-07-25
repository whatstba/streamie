"""
Audio Pre-renderer - Renders complete DJ sets as WAV files before streaming
"""

import numpy as np
import logging
import struct
import os
import tempfile
import asyncio
from typing import Optional, Dict, List, Tuple
import time
from datetime import datetime
import librosa
from scipy import signal

from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager
from services.effect_manager import EffectManager
from models.dj_set_models import DJSet, DJSetTrack

logger = logging.getLogger(__name__)


class AudioPrerenderer:
    """
    Pre-renders complete DJ sets as WAV files with all effects and transitions.
    This replaces the live streaming approach for better browser compatibility.
    """
    
    def __init__(
        self,
        deck_manager: DeckManager,
        mixer_manager: MixerManager,
        effect_manager: EffectManager,
        sample_rate: int = 44100
    ):
        self.deck_manager = deck_manager
        self.mixer_manager = mixer_manager
        self.effect_manager = effect_manager
        self.sample_rate = sample_rate
        self.channels = 2
        self.bit_depth = 16
        
        # Pre-rendered files storage in temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="streamie_prerendered_")
        logger.info(f"🎬 Using temp directory: {self.temp_dir}")
        self._rendered_files: Dict[str, str] = {}
        self._render_progress: Dict[str, float] = {}
        
        logger.info(f"🎬 AudioPrerenderer initialized with output dir: {self.temp_dir}")
        
    def create_wav_header(self, data_size: int) -> bytes:
        """Create a complete WAV header with known size"""
        header = bytearray()
        
        # RIFF chunk
        header.extend(b"RIFF")
        header.extend(struct.pack("<I", 36 + data_size))  # File size - 8
        header.extend(b"WAVE")
        
        # fmt chunk
        header.extend(b"fmt ")
        header.extend(struct.pack("<I", 16))  # Chunk size
        header.extend(struct.pack("<H", 1))   # PCM format
        header.extend(struct.pack("<H", self.channels))
        header.extend(struct.pack("<I", self.sample_rate))
        byte_rate = self.sample_rate * self.channels * (self.bit_depth // 8)
        header.extend(struct.pack("<I", byte_rate))
        block_align = self.channels * (self.bit_depth // 8)
        header.extend(struct.pack("<H", block_align))
        header.extend(struct.pack("<H", self.bit_depth))
        
        # data chunk
        header.extend(b"data")
        header.extend(struct.pack("<I", data_size))
        
        return bytes(header)
        
    def load_track(self, filepath: str) -> Optional[np.ndarray]:
        """Load a track and return stereo audio data"""
        try:
            # Resolve filepath
            if not os.path.isabs(filepath):
                # Try different resolutions
                test_paths = [
                    os.path.expanduser(f"~/Downloads/{filepath}"),
                    os.path.expanduser(f"~/{filepath.lstrip('../')}"),
                    os.path.abspath(filepath),
                ]
                
                for test_path in test_paths:
                    if os.path.exists(test_path):
                        filepath = test_path
                        break
                else:
                    logger.error(f"❌ Track not found: {filepath}")
                    return None
                    
            logger.info(f"📁 Loading track: {filepath}")
            
            # Load with librosa
            audio_data, sr = librosa.load(filepath, sr=self.sample_rate, mono=False)
            
            # Ensure stereo
            if audio_data.ndim == 1:
                audio_data = np.stack([audio_data, audio_data])
            elif audio_data.shape[0] > 2:
                audio_data = audio_data[:2]
                
            logger.info(f"✅ Loaded {audio_data.shape[1] / self.sample_rate:.1f}s of audio")
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ Error loading track: {e}")
            return None
            
    def apply_eq(self, audio: np.ndarray, low: float, mid: float, high: float) -> np.ndarray:
        """Apply 3-band EQ to audio"""
        # Simple EQ implementation - can be enhanced with proper filters
        # For now, just apply gain adjustments
        return audio * (1.0 + (low + mid + high) / 3.0)
        
    def apply_effects(self, audio: np.ndarray, effects: List[Dict], start_time: float) -> np.ndarray:
        """Apply effects to audio based on effect plan"""
        processed = audio.copy()
        
        for effect in effects:
            effect_type = effect.get('type', '')
            effect_start = effect.get('start_at', 0.0)
            effect_duration = effect.get('duration', 1.0)
            effect_intensity = effect.get('intensity', 0.5)
            
            # Calculate sample positions
            start_sample = int((start_time + effect_start) * self.sample_rate)
            end_sample = int((start_time + effect_start + effect_duration) * self.sample_rate)
            
            # Ensure we're within bounds
            if start_sample >= audio.shape[1] or end_sample <= 0:
                continue
                
            start_sample = max(0, start_sample)
            end_sample = min(audio.shape[1], end_sample)
            
            if effect_type == 'filter':
                # Simple low-pass filter effect
                for i in range(start_sample, end_sample):
                    if i < processed.shape[1]:
                        processed[:, i] *= (1.0 - effect_intensity * 0.7)
                        
            elif effect_type == 'echo':
                # Simple echo effect
                delay_samples = int(0.1 * self.sample_rate)  # 100ms delay
                for i in range(start_sample, end_sample):
                    if i + delay_samples < processed.shape[1]:
                        processed[:, i + delay_samples] += processed[:, i] * effect_intensity * 0.3
                        
        return processed
        
    def apply_crossfade_curve(self, progress: float, curve: str = "s-curve") -> float:
        """Apply crossfade curve to progress value (0-1)"""
        if curve == "linear":
            return progress
        elif curve == "s-curve":
            # Smooth S-curve using cosine
            return 0.5 * (1 - np.cos(np.pi * progress))
        elif curve == "exponential":
            return progress ** 2
        else:
            return progress
            
    def process_transition_effect(
        self, 
        audio: np.ndarray, 
        effect_type: str, 
        intensity: float, 
        progress: float,
        parameters: Optional[Dict] = None
    ) -> np.ndarray:
        """Process a single transition effect on audio buffer"""
        processed = audio.copy()
        
        if effect_type == 'filter' or effect_type == 'filter_sweep':
            # Proper low-pass filter using scipy
            # Intensity controls cutoff frequency range
            # Progress sweeps from low to high frequency
            nyquist = self.sample_rate / 2.0
            
            # Start at 200Hz, sweep up to 8kHz based on intensity and progress
            min_freq = 200.0
            max_freq = min_freq + (8000.0 - min_freq) * intensity
            current_freq = min_freq + (max_freq - min_freq) * progress
            
            # Ensure frequency is within valid range
            current_freq = np.clip(current_freq, 100.0, nyquist * 0.95)
            
            # Design butterworth filter
            try:
                sos = signal.butter(4, current_freq / nyquist, btype='low', output='sos')
                # Apply filter to each channel
                for ch in range(processed.shape[0]):
                    processed[ch] = signal.sosfilt(sos, processed[ch])
            except Exception as e:
                logger.warning(f"Filter error, using fallback: {e}")
                # Fallback to simple amplitude reduction
                processed *= (1.0 - intensity * progress * 0.5)
            
        elif effect_type == 'echo':
            # Echo/delay effect
            delay_ms = parameters.get('delay_time', 250) if parameters else 250
            delay_samples = int(delay_ms * self.sample_rate / 1000)
            feedback = 0.4 + (intensity * 0.5)  # Increased feedback
            mix = 0.3 + (intensity * 0.6)  # Increased mix level
            
            if delay_samples < processed.shape[1]:
                delayed = np.zeros_like(processed)
                delayed[:, delay_samples:] = processed[:, :-delay_samples] * feedback
                processed = processed * (1 - mix) + delayed * mix
                
        elif effect_type == 'reverb':
            # Simple reverb using multiple delays
            room_size = 0.3 + (intensity * 0.5)
            wet_level = 0.3 + (intensity * 0.5)  # Increased wet level
            
            reverb = np.zeros_like(processed)
            delays = [0.013, 0.027, 0.037, 0.043]  # seconds
            gains = [0.8, 0.6, 0.4, 0.3]
            
            for delay, gain in zip(delays, gains):
                delay_samples = int(delay * self.sample_rate * room_size)
                if delay_samples < processed.shape[1]:
                    delayed = np.zeros_like(processed)
                    delayed[:, delay_samples:] = processed[:, :-delay_samples] * gain
                    reverb += delayed
                    
            processed = processed * (1 - wet_level) + reverb * wet_level
            
        elif effect_type == 'delay':
            # Longer delay than echo
            delay_ms = parameters.get('delay_time', 500) if parameters else 500
            delay_samples = int(delay_ms * self.sample_rate / 1000)
            feedback = 0.5 + (intensity * 0.4)  # Increased feedback
            mix = 0.3 + (intensity * 0.5)  # Increased mix level
            
            if delay_samples < processed.shape[1]:
                delayed = np.zeros_like(processed)
                delayed[:, delay_samples:] = processed[:, :-delay_samples] * feedback
                processed = processed * (1 - mix) + delayed * mix
                
        elif effect_type == 'gate':
            # Rhythmic volume cuts
            rate = 16.0  # 16th notes
            beat_time = 60.0 / 120.0 / (rate / 4.0)  # Assuming 120 BPM
            samples_per_beat = int(beat_time * self.sample_rate)
            
            for i in range(0, processed.shape[1], samples_per_beat):
                # Gate pattern - cut every other beat segment
                if (i // samples_per_beat) % 2 == 1:
                    end = min(i + samples_per_beat, processed.shape[1])
                    processed[:, i:end] *= (1.0 - intensity)
                    
        elif effect_type == 'scratch':
            # DJ scratch effect using pitch shifting and time stretching
            # Intensity controls the amount of pitch variation
            scratch_rate = 4.0  # Scratches per second
            scratch_period = int(self.sample_rate / scratch_rate)
            
            for i in range(0, processed.shape[1], scratch_period):
                if i + scratch_period < processed.shape[1]:
                    # Create a scratch pattern with pitch variation
                    segment = processed[:, i:i+scratch_period]
                    
                    # Simple pitch shift by resampling
                    pitch_factor = 1.0 + (np.sin(2 * np.pi * i / scratch_period) * intensity * 0.5)
                    new_length = int(segment.shape[1] / pitch_factor)
                    
                    if new_length > 0 and new_length < segment.shape[1] * 2:
                        # Resample each channel
                        scratched = np.zeros((2, scratch_period))
                        for ch in range(2):
                            resampled = np.interp(
                                np.linspace(0, segment.shape[1]-1, new_length),
                                np.arange(segment.shape[1]),
                                segment[ch]
                            )
                            # Stretch or compress back to original length
                            scratched[ch] = np.interp(
                                np.arange(scratch_period),
                                np.linspace(0, scratch_period-1, len(resampled)),
                                resampled
                            )
                        
                        # Mix scratched audio with original
                        processed[:, i:i+scratch_period] = (
                            processed[:, i:i+scratch_period] * (1 - intensity * 0.7) +
                            scratched * intensity * 0.7
                        )
                        
        elif effect_type == 'flanger':
            # Flanger effect - like chorus but with shorter delay and feedback
            delay_samples = int(0.005 * self.sample_rate)  # 5ms base delay
            lfo_rate = 0.5  # Hz
            depth = intensity * 0.8
            
            flanged = np.zeros_like(processed)
            for i in range(processed.shape[1]):
                # LFO modulates delay time
                lfo = np.sin(2 * np.pi * lfo_rate * i / self.sample_rate)
                current_delay = int(delay_samples * (1 + lfo * depth))
                
                if i >= current_delay:
                    # Mix delayed signal with original
                    flanged[:, i] = (
                        processed[:, i] * 0.5 +
                        processed[:, i - current_delay] * 0.5
                    )
                else:
                    flanged[:, i] = processed[:, i]
                    
            processed = flanged
            
        elif effect_type == 'eq_sweep':
            # EQ sweep - boost/cut frequencies that sweep across spectrum
            nyquist = self.sample_rate / 2.0
            
            # Center frequency sweeps from 200Hz to 4kHz
            center_freq = 200 + (4000 - 200) * progress
            bandwidth = 0.5  # Q factor
            gain_db = intensity * 12  # Up to 12dB boost
            
            try:
                # Design peaking EQ filter
                b, a = signal.iirpeak(center_freq / nyquist, bandwidth)
                
                # Apply gain
                gain_linear = 10 ** (gain_db / 20)
                
                # Apply filter to each channel
                for ch in range(processed.shape[0]):
                    filtered = signal.lfilter(b, a, processed[ch])
                    # Mix filtered and original based on intensity
                    processed[ch] = (
                        processed[ch] * (1 - intensity * 0.5) +
                        filtered * gain_linear * intensity * 0.5
                    )
            except Exception as e:
                logger.warning(f"EQ sweep error: {e}")
                    
        return processed
        
    async def prerender_dj_set(self, dj_set: DJSet) -> str:
        """
        Pre-render a complete DJ set to a WAV file.
        
        Returns:
            Path to the rendered WAV file
        """
        set_id = dj_set.id
        render_start_time = datetime.now()
        logger.info(f"🎬 Starting pre-render for DJ set: {set_id}")
        logger.info(f"   Set name: {dj_set.name}")
        logger.info(f"   Track count: {len(dj_set.tracks)}")
        logger.info(f"   Transition count: {len(dj_set.transitions)}")
        self._render_progress[set_id] = 0.0
        
        try:
            # Calculate total duration
            total_duration = max(track.end_time for track in dj_set.tracks) if dj_set.tracks else 0
            total_samples = int(total_duration * self.sample_rate)
            buffer_size_mb = (total_samples * 2 * 4) / (1024 * 1024)  # 2 channels, 4 bytes per float32
            
            logger.info(f"📊 Total duration: {total_duration:.1f}s ({len(dj_set.tracks)} tracks)")
            logger.info(f"   Sample rate: {self.sample_rate} Hz")
            logger.info(f"   Total samples: {total_samples:,}")
            logger.info(f"   Buffer size: {buffer_size_mb:.1f} MB")
            
            # Create output buffer for entire mix
            output = np.zeros((2, total_samples), dtype=np.float32)
            
            # Create buffers for each track
            track_buffers = []
            track_timing = []
            
            # First pass: Load and prepare all tracks
            loading_start_time = datetime.now()
            logger.info("\n📂 Phase 1: Loading and preparing tracks...")
            
            for i, track in enumerate(dj_set.tracks):
                track_start = datetime.now()
                logger.info(f"\n🎵 Loading track {i+1}/{len(dj_set.tracks)}: {track.title}")
                logger.info(f"   Artist: {track.artist}")
                logger.info(f"   Filepath: {track.filepath}")
                logger.info(f"   Timing: {track.start_time:.1f}s - {track.end_time:.1f}s")
                
                # Load track audio
                audio = self.load_track(track.filepath)
                if audio is None:
                    logger.error(f"❌ Skipping track {i+1} - failed to load")
                    logger.error(f"   Filepath was: {track.filepath}")
                    track_buffers.append(None)
                    track_timing.append(None)
                    continue
                
                # Extract hot cue portion of the track
                hot_cue_in_sample = int(track.hot_cue_in_offset * self.sample_rate)
                hot_cue_out_sample = int(track.hot_cue_out_offset * self.sample_rate)
                
                # Log hot cue extraction
                logger.info(f"   🎯 Extracting hot cue region:")
                logger.info(f"      Mix In: {track.hot_cue_in_offset:.1f}s (sample {hot_cue_in_sample:,})")
                logger.info(f"      Mix Out: {track.hot_cue_out_offset:.1f}s (sample {hot_cue_out_sample:,})")
                logger.info(f"      Hot cue duration: {track.hot_cue_out_offset - track.hot_cue_in_offset:.1f}s")
                
                # Ensure we don't exceed audio bounds
                if hot_cue_out_sample > audio.shape[1]:
                    logger.warning(f"   ⚠️ Hot cue out ({hot_cue_out_sample}) exceeds audio length ({audio.shape[1]}), adjusting")
                    hot_cue_out_sample = audio.shape[1]
                
                # Extract the hot cue region
                audio = audio[:, hot_cue_in_sample:hot_cue_out_sample]
                logger.info(f"   ✂️ Extracted {audio.shape[1] / self.sample_rate:.1f}s of audio from hot cues")
                    
                # Calculate timing for the mix
                start_sample = int(track.start_time * self.sample_rate)
                end_sample = int(track.end_time * self.sample_rate)
                duration_samples = end_sample - start_sample
                
                # Verify extracted audio matches expected duration
                if audio.shape[1] > duration_samples:
                    # Trim if we have more audio than needed
                    audio = audio[:, :duration_samples]
                    logger.info(f"   ✂️ Trimmed to {duration_samples / self.sample_rate:.1f}s for mix timing")
                elif audio.shape[1] < duration_samples:
                    # Pad with silence if needed
                    padding = duration_samples - audio.shape[1]
                    audio = np.concatenate([audio, np.zeros((2, padding))], axis=1)
                    padding_seconds = padding / self.sample_rate
                    actual_duration = audio.shape[1] / self.sample_rate
                    expected_duration = duration_samples / self.sample_rate
                    logger.warning(f"   ⚠️ Hot cue extraction resulted in shorter audio than expected:")
                    logger.warning(f"      Expected: {expected_duration:.1f}s, Got: {(audio.shape[1] - padding) / self.sample_rate:.1f}s")
                    logger.warning(f"      Padded with {padding_seconds:.1f}s of silence")
                    logger.warning(f"      Hot cue range: {track.hot_cue_in_offset:.1f}s - {track.hot_cue_out_offset:.1f}s")
                    
                # Apply gain
                audio = audio * track.gain_adjust
                
                # Apply EQ
                audio = self.apply_eq(audio, track.eq_low, track.eq_mid, track.eq_high)
                
                # Store track and timing info
                track_buffers.append(audio)
                track_timing.append({
                    'start_sample': start_sample,
                    'end_sample': end_sample,
                    'track': track
                })
                
                track_load_time = (datetime.now() - track_start).total_seconds()
                logger.info(f"   ✅ Track loaded successfully in {track_load_time:.2f}s")
                logger.info(f"   Buffer shape: {audio.shape}")
                logger.info(f"   Duration: {audio.shape[1] / self.sample_rate:.1f}s")
                logger.info(f"   Gain: {track.gain_adjust:.2f}, EQ: L={track.eq_low:.2f} M={track.eq_mid:.2f} H={track.eq_high:.2f}")
                
                # Update progress
                self._render_progress[set_id] = (i + 1) / (len(dj_set.tracks) * 2)  # Half progress for loading
                logger.info(f"   Loading progress: {self._render_progress[set_id] * 100:.1f}%")
                
                # Allow async operations
                await asyncio.sleep(0)
                
            # Second pass: Mix tracks with transitions
            loading_duration = (datetime.now() - loading_start_time).total_seconds()
            logger.info(f"\n✅ Loading phase complete in {loading_duration:.1f}s")
            
            mixing_start_time = datetime.now()
            logger.info("\n🎛️ Phase 2: Mixing tracks with transitions...")
            
            for i, (buffer, timing) in enumerate(zip(track_buffers, track_timing)):
                if buffer is None or timing is None:
                    logger.warning(f"   ⚠️ Skipping track {i+1} - no buffer available")
                    continue
                    
                track = timing['track']
                start_sample = timing['start_sample']
                
                logger.info(f"\n🎚️ Mixing track {track.order}: {track.title}")
                logger.info(f"   Start position: {track.start_time:.1f}s (sample {start_sample:,})")
                
                # Check if this track is part of a transition
                transition_as_source = None
                transition_as_target = None
                
                for transition in dj_set.transitions:
                    if transition.from_track_order == track.order:
                        transition_as_source = transition
                    if transition.to_track_order == track.order:
                        transition_as_target = transition
                        
                # Process the track buffer based on transitions
                processed_buffer = buffer.copy()
                
                # If this track is the source of a transition
                if transition_as_source:
                    logger.info(f"   🎚️ Processing outgoing transition from track {track.order}")
                    logger.info(f"      Type: {transition_as_source.type}")
                    logger.info(f"      Duration: {transition_as_source.duration}s")
                    logger.info(f"      Effects: {len(transition_as_source.effects)}")
                    logger.info(f"      Curve: {transition_as_source.crossfade_curve}")
                    transition_start_sample = int(transition_as_source.start_time * self.sample_rate)
                    transition_duration_samples = int(transition_as_source.duration * self.sample_rate)
                    
                    # Apply crossfade curve to outgoing track
                    # Keep minimum volume during effects to make them audible
                    min_volume_during_effects = 0.5  # 50% minimum volume
                    
                    for j in range(transition_duration_samples):
                        global_sample = transition_start_sample + j
                        local_sample = global_sample - start_sample
                        
                        if 0 <= local_sample < processed_buffer.shape[1]:
                            progress = j / transition_duration_samples
                            fade_curve = self.apply_crossfade_curve(1.0 - progress, transition_as_source.crossfade_curve)
                            
                            # Keep minimum volume if effects are active
                            if len(transition_as_source.effects) > 0:
                                fade_curve = max(fade_curve, min_volume_during_effects)
                            
                            processed_buffer[:, local_sample] *= fade_curve
                            
                    # Apply transition effects to outgoing track
                    for effect_idx, effect in enumerate(transition_as_source.effects):
                        # Log detailed effect information
                        effect_type = effect.type if hasattr(effect, 'type') else str(effect)
                        effect_intensity = effect.intensity if hasattr(effect, 'intensity') else 0.5
                        effect_duration = effect.duration if hasattr(effect, 'duration') else 3.0
                        effect_start_at = effect.start_at if hasattr(effect, 'start_at') else 0.0
                        
                        logger.info(f"      🎵 Applying effect {effect_idx + 1}/{len(transition_as_source.effects)}:")
                        logger.info(f"         Type: {effect_type}")
                        logger.info(f"         Intensity: {effect_intensity:.2f}")
                        logger.info(f"         Duration: {effect_duration}s")
                        logger.info(f"         Start at: {effect_start_at}s (relative to transition)")
                        
                        effect_start = int((transition_as_source.start_time + effect_start_at) * self.sample_rate)
                        effect_duration_samples = int(effect_duration * self.sample_rate)
                        
                        # Calculate the range of samples affected by this effect
                        effect_start_local = effect_start - start_sample
                        effect_end_local = effect_start_local + effect_duration_samples
                        
                        # Ensure we're within buffer bounds
                        if effect_end_local > 0 and effect_start_local < processed_buffer.shape[1]:
                            # Clip to valid range
                            valid_start = max(0, effect_start_local)
                            valid_end = min(processed_buffer.shape[1], effect_end_local)
                            
                            # Extract the portion of audio to process
                            audio_segment = processed_buffer[:, valid_start:valid_end]
                            
                            # Calculate progress for the entire effect duration
                            progress_start = (valid_start - effect_start_local) / effect_duration_samples if effect_duration_samples > 0 else 0
                            progress_end = (valid_end - effect_start_local) / effect_duration_samples if effect_duration_samples > 0 else 1
                            
                            # Process the entire segment with the effect
                            logger.info(f"         🎛️ Processing effect on samples {valid_start}-{valid_end}")
                            logger.info(f"         Audio segment shape: {audio_segment.shape}")
                            
                            effected = self.process_transition_effect(
                                audio_segment,
                                effect_type,
                                effect_intensity,
                                (progress_start + progress_end) / 2,  # Average progress for this segment
                                effect.parameters if hasattr(effect, 'parameters') else None
                            )
                            
                            # Log the effect result
                            logger.info(f"         🎯 Effect applied! Output shape: {effected.shape}")
                            # Check if effect actually changed the audio
                            diff = np.abs(effected - audio_segment).mean()
                            logger.info(f"         Audio difference (effect strength): {diff:.6f}")
                            
                            # Replace the processed segment
                            processed_buffer[:, valid_start:valid_end] = effected
                            
                            logger.info(f"         Applied to samples {valid_start}-{valid_end} ({(valid_end-valid_start)/self.sample_rate:.2f}s)")
                
                # If this track is the target of a transition
                if transition_as_target:
                    logger.info(f"   🎚️ Processing incoming transition to track {track.order}")
                    transition_start_sample = int(transition_as_target.start_time * self.sample_rate)
                    transition_duration_samples = int(transition_as_target.duration * self.sample_rate)
                    
                    # Apply crossfade curve to incoming track
                    # Keep minimum volume during effects to make them audible
                    min_volume_during_effects = 0.5  # 50% minimum volume
                    
                    for j in range(transition_duration_samples):
                        global_sample = transition_start_sample + j
                        local_sample = global_sample - start_sample
                        
                        if 0 <= local_sample < processed_buffer.shape[1]:
                            progress = j / transition_duration_samples
                            fade_curve = self.apply_crossfade_curve(progress, transition_as_target.crossfade_curve)
                            
                            # Keep minimum volume if effects are active (check previous transition)
                            # Since effects are on the outgoing track, check if we're still in effect range
                            effect_active = False
                            if i > 0 and i - 1 < len(dj_set.transitions):
                                prev_transition = dj_set.transitions[i - 1]
                                if len(prev_transition.effects) > 0:
                                    # Check if we're still within effect duration
                                    for effect in prev_transition.effects:
                                        effect_end = prev_transition.start_time + effect.start_at + effect.duration
                                        if transition_as_target.start_time <= effect_end:
                                            effect_active = True
                                            break
                            
                            if effect_active:
                                fade_curve = max(fade_curve, min_volume_during_effects)
                            
                            processed_buffer[:, local_sample] *= fade_curve
                            
                # Apply standard fade in/out if not part of a transition
                if not transition_as_source and not transition_as_target:
                    fade_samples = int(0.5 * self.sample_rate)  # 0.5 second fades
                    if processed_buffer.shape[1] > fade_samples * 2:
                        # Fade in
                        fade_in = np.linspace(0, 1, fade_samples)
                        processed_buffer[:, :fade_samples] *= fade_in
                        
                        # Fade out
                        fade_out = np.linspace(1, 0, fade_samples)
                        processed_buffer[:, -fade_samples:] *= fade_out
                        
                # Mix into output
                if start_sample + processed_buffer.shape[1] <= output.shape[1]:
                    output[:, start_sample:start_sample + processed_buffer.shape[1]] += processed_buffer
                else:
                    # Clip if exceeds total duration
                    remaining = output.shape[1] - start_sample
                    output[:, start_sample:] += processed_buffer[:, :remaining]
                    
                # Update progress
                self._render_progress[set_id] = 0.5 + (i + 1) / (len(track_buffers) * 2)  # Second half for mixing
                logger.info(f"   Mixing progress: {self._render_progress[set_id] * 100:.1f}%")
                
                # Allow async operations
                await asyncio.sleep(0)
                
            mixing_duration = (datetime.now() - mixing_start_time).total_seconds()
            logger.info(f"\n✅ Mixing phase complete in {mixing_duration:.1f}s")
            
            # Log summary of effects applied
            logger.info("\n🎨 Effects Summary:")
            total_effects = 0
            effect_types = {}
            for transition in dj_set.transitions:
                for effect in transition.effects:
                    total_effects += 1
                    effect_type = effect.type
                    if effect_type not in effect_types:
                        effect_types[effect_type] = []
                    effect_types[effect_type].append(f"intensity={effect.intensity:.2f}")
            
            logger.info(f"   Total effects applied: {total_effects}")
            if total_effects == 0:
                logger.warning("   ⚠️ NO EFFECTS WERE APPLIED! Check transition data structure.")
            for effect_type, instances in effect_types.items():
                logger.info(f"   - {effect_type}: {len(instances)} instances ({', '.join(instances[:3])}{'...' if len(instances) > 3 else ''})")
            
            # Log supported effect types for reference
            logger.info("\n📋 Supported effect types:")
            logger.info("   - filter/filter_sweep: Low-pass filter sweep")
            logger.info("   - echo: Delay with feedback (250ms)")
            logger.info("   - reverb: Room simulation")
            logger.info("   - delay: Long delay (500ms)")
            logger.info("   - gate: Rhythmic volume cuts")
            logger.info("   - scratch: DJ scratch effect")
            logger.info("   - flanger: LFO modulation")
            logger.info("   - eq_sweep: Sweeping EQ boost")
            
            # Normalize to prevent clipping
            logger.info("\n🔊 Phase 3: Normalizing and encoding...")
            max_val = np.abs(output).max()
            if max_val > 0:
                output = output / max_val * 0.95
                logger.info(f"   ✅ Normalized audio, peak level: {max_val:.3f}")
                logger.info(f"   Final peak: {np.abs(output).max():.3f}")
            else:
                logger.warning("   ⚠️ No audio signal - output is silence!")
                
            # Convert to 16-bit PCM
            output_16bit = (output * 32767).astype(np.int16)
            
            # Interleave channels
            interleaved = np.empty((output_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = output_16bit[0]  # Left channel
            interleaved[1::2] = output_16bit[1]  # Right channel
            
            # Create WAV file
            audio_data = interleaved.tobytes()
            wav_header = self.create_wav_header(len(audio_data))
            
            # Save to file
            filename = f"dj_set_{set_id}_{int(time.time())}.wav"
            filepath = os.path.join(self.temp_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(wav_header + audio_data)
                
            # Store reference
            self._rendered_files[set_id] = filepath
            self._render_progress[set_id] = 1.0
            
            file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
            total_render_time = (datetime.now() - render_start_time).total_seconds()
            
            logger.info(f"\n🎉 Pre-render complete!")
            logger.info(f"   Output file: {filepath}")
            logger.info(f"   File size: {file_size:.1f} MB")
            logger.info(f"   Duration: {total_duration:.1f}s")
            logger.info(f"   Total render time: {total_render_time:.1f}s")
            logger.info(f"   - Loading phase: {loading_duration:.1f}s")
            logger.info(f"   - Mixing phase: {mixing_duration:.1f}s")
            logger.info(f"   - Encoding phase: {total_render_time - loading_duration - mixing_duration:.1f}s")
            logger.info(f"   Render speed: {total_duration / total_render_time:.1f}x realtime")
            
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Pre-render failed: {e}")
            self._render_progress[set_id] = -1.0  # Error state
            raise
            
    def get_rendered_file(self, set_id: str) -> Optional[str]:
        """Get the path to a pre-rendered file if available"""
        return self._rendered_files.get(set_id)
        
    def get_render_progress(self, set_id: str) -> float:
        """Get rendering progress (0.0 to 1.0, -1.0 for error)"""
        return self._render_progress.get(set_id, 0.0)
        
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"🧹 Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up: {e}")
"""DJ Toolset - Core DJ functionality"""
from typing import Optional, Dict, List, Tuple
import asyncio
import numpy as np
import librosa
import soundfile as sf
from dataclasses import dataclass, field
import logging
from scipy import signal
import threading
import queue
import time

logger = logging.getLogger(__name__)

@dataclass
class DeckState:
    """State for a single deck"""
    track_path: Optional[str] = None
    audio_data: Optional[np.ndarray] = None
    sample_rate: int = 44100
    playing: bool = False
    position: float = 0.0  # 0-1
    position_frames: int = 0  # Current frame position
    tempo: float = 0.0  # -50% to +50%
    volume: float = 1.0
    original_bpm: float = 120.0
    effective_bpm: float = 120.0
    cues: Dict[int, float] = field(default_factory=dict)
    loop_in: Optional[float] = None
    loop_out: Optional[float] = None
    looping: bool = False
    eq: Dict[str, float] = field(default_factory=lambda: {'low': 0.0, 'mid': 0.0, 'high': 0.0})
    track_info: Optional[Dict] = None

@dataclass
class MixerState:
    """Mixer state"""
    crossfader: float = 0.0  # -1 to 1
    master_volume: float = 1.0
    monitor_volume: float = 0.7
    recording: bool = False

class DJToolset:
    """Core DJ functionality toolset"""
    
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        # Initialize decks
        self.decks = {
            'A': DeckState(sample_rate=sample_rate),
            'B': DeckState(sample_rate=sample_rate),
            'C': DeckState(sample_rate=sample_rate),
            'D': DeckState(sample_rate=sample_rate)
        }
        
        # Initialize mixer
        self.mixer = MixerState()
        
        # Audio processing thread
        self.audio_queue = queue.Queue(maxsize=100)
        self.processing_thread = None
        self.running = False
        
        # Effects (simplified for now)
        self.effects = {}
        
        # Sync engine
        self.sync_leader = None
        self.sync_followers = []
    
    # --- Track Loading ---
    async def load_track(self, deck: str, file_path: str, track_info: Optional[Dict] = None) -> Dict:
        """Load a track onto a deck"""
        try:
            # Load audio file
            audio_data, sr = librosa.load(file_path, sr=self.sample_rate, mono=False)
            
            # Convert to stereo if mono
            if audio_data.ndim == 1:
                audio_data = np.stack([audio_data, audio_data])
            
            # Store in deck
            deck_state = self.decks[deck]
            deck_state.track_path = file_path
            deck_state.audio_data = audio_data
            deck_state.sample_rate = sr
            deck_state.position = 0.0
            deck_state.position_frames = 0
            deck_state.track_info = track_info or {}
            
            # Get duration
            duration = len(audio_data[0]) / sr
            
            # Extract BPM if not provided
            if track_info and 'bpm' in track_info:
                deck_state.original_bpm = track_info['bpm']
                deck_state.effective_bpm = track_info['bpm']
            else:
                # Quick BPM detection
                tempo, _ = librosa.beat.beat_track(y=audio_data[0], sr=sr)
                deck_state.original_bpm = float(tempo)
                deck_state.effective_bpm = float(tempo)
            
            return {
                'status': 'loaded',
                'deck': deck,
                'duration': duration,
                'bpm': deck_state.original_bpm,
                'filepath': file_path
            }
            
        except Exception as e:
            logger.error(f"Error loading track: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'deck': deck
            }
    
    def load_deck(self, deck: str, filepath: str) -> Dict:
        """Alias for load_track for compatibility"""
        return self.load_track(deck, filepath)
    
    def clear_deck(self, deck: str) -> Dict:
        """Clear/unload a deck"""
        state = self.decks[deck]
        state.track_path = None
        state.audio_data = None
        state.playing = False
        state.position = 0.0
        state.position_frames = 0
        state.tempo = 0.0
        state.original_bpm = 120.0
        state.effective_bpm = 120.0
        state.cues.clear()
        state.loop_in = None
        state.loop_out = None
        state.looping = False
        state.track_info = None
        
        return {
            'status': 'cleared',
            'deck': deck
        }
    
    # --- Playback Control ---
    def play_pause(self, deck: str) -> Dict:
        """Toggle play/pause for a deck"""
        state = self.decks[deck]
        state.playing = not state.playing
        
        # Start processing thread if needed
        if state.playing and not self.running:
            self.start_processing()
        
        return {
            'deck': deck,
            'playing': state.playing,
            'position': state.position
        }
    
    def seek(self, deck: str, position: float) -> Dict:
        """Seek to position in track (0-1)"""
        state = self.decks[deck]
        state.position = np.clip(position, 0, 1)
        
        if state.audio_data is not None:
            total_frames = len(state.audio_data[0])
            state.position_frames = int(position * total_frames)
        
        return {'deck': deck, 'position': position}
    
    def set_tempo(self, deck: str, tempo_adjust: float) -> Dict:
        """Adjust tempo (-50% to +50%)"""
        state = self.decks[deck]
        state.tempo = np.clip(tempo_adjust, -0.5, 0.5)
        state.effective_bpm = state.original_bpm * (1 + tempo_adjust)
        
        return {
            'deck': deck,
            'tempo_adjust': tempo_adjust,
            'effective_bpm': state.effective_bpm
        }
    
    # --- Mixing ---
    def set_volume(self, deck: str, volume: float) -> Dict:
        """Set deck volume (0-1)"""
        self.decks[deck].volume = np.clip(volume, 0, 1)
        return {'deck': deck, 'volume': self.decks[deck].volume}
    
    def set_crossfader(self, position: float) -> Dict:
        """Set crossfader position (-1 to 1)"""
        self.mixer.crossfader = np.clip(position, -1, 1)
        
        # Calculate deck gains (simple linear for now)
        if position < 0:
            gain_a = 1.0
            gain_b = 1.0 + position
        else:
            gain_a = 1.0 - position
            gain_b = 1.0
            
        return {
            'position': self.mixer.crossfader,
            'gain_a': gain_a,
            'gain_b': gain_b
        }
    
    def set_eq(self, deck: str, low: float, mid: float, high: float) -> Dict:
        """Set 3-band EQ (-1 to 1 for each)"""
        eq = self.decks[deck].eq
        eq['low'] = np.clip(low, -1, 1)
        eq['mid'] = np.clip(mid, -1, 1)
        eq['high'] = np.clip(high, -1, 1)
        
        return {'deck': deck, 'eq': eq}
    
    # --- Sync ---
    def enable_sync(self, deck: str, mode: str = 'follower') -> Dict:
        """Enable beat sync for a deck"""
        if mode == 'leader':
            self.sync_leader = deck
            self.sync_followers = [d for d in self.sync_followers if d != deck]
        else:
            if deck not in self.sync_followers:
                self.sync_followers.append(deck)
            
            # Sync to leader if exists
            if self.sync_leader:
                leader_bpm = self.decks[self.sync_leader].effective_bpm
                follower_bpm = self.decks[deck].original_bpm
                tempo_adjust = (leader_bpm / follower_bpm) - 1
                self.set_tempo(deck, tempo_adjust)
                
        return {
            'deck': deck,
            'sync_mode': mode,
            'synced_to': self.sync_leader if mode == 'follower' else None
        }
    
    def disable_sync(self, deck: str) -> Dict:
        """Disable sync for a deck"""
        if deck == self.sync_leader:
            self.sync_leader = None
        elif deck in self.sync_followers:
            self.sync_followers.remove(deck)
            
        return {'deck': deck, 'sync': False}
    
    # --- Cues & Loops ---
    def set_cue_point(self, deck: str, cue_number: int, 
                     position: Optional[float] = None) -> Dict:
        """Set a cue point"""
        state = self.decks[deck]
        if position is None:
            position = state.position
            
        state.cues[cue_number] = position
        
        return {
            'deck': deck,
            'cue': cue_number,
            'position': position
        }
    
    def jump_to_cue(self, deck: str, cue_number: int) -> Dict:
        """Jump to a cue point"""
        state = self.decks[deck]
        if cue_number in state.cues:
            position = state.cues[cue_number]
            self.seek(deck, position)
            return {'deck': deck, 'cue': cue_number, 'position': position}
        
        return {'error': f'Cue {cue_number} not set on deck {deck}'}
    
    def enable_loop(self, deck: str, beats: float) -> Dict:
        """Enable a beat loop"""
        deck_state = self.decks[deck]
        beat_length = 60.0 / deck_state.effective_bpm
        loop_length = beats * beat_length
        
        # Convert to position (0-1)
        if deck_state.audio_data is not None:
            total_duration = len(deck_state.audio_data[0]) / deck_state.sample_rate
            loop_length_normalized = loop_length / total_duration
            
            deck_state.loop_in = deck_state.position
            deck_state.loop_out = deck_state.position + loop_length_normalized
            deck_state.looping = True
        
        return {
            'deck': deck,
            'loop_beats': beats,
            'loop_in': deck_state.loop_in,
            'loop_out': deck_state.loop_out
        }
    
    def disable_loop(self, deck: str) -> Dict:
        """Disable looping"""
        self.decks[deck].looping = False
        return {'deck': deck, 'looping': False}
    
    # --- Audio Processing ---
    def start_processing(self):
        """Start audio processing thread"""
        if not self.running:
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_audio)
            self.processing_thread.start()
    
    def stop_processing(self):
        """Stop audio processing thread"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()
    
    def _process_audio(self):
        """Audio processing thread"""
        while self.running:
            try:
                # Generate buffer of mixed audio
                buffer = self._generate_buffer()
                
                # Put in queue for streaming
                if not self.audio_queue.full():
                    self.audio_queue.put(buffer)
                
                # Sleep based on buffer size
                sleep_time = self.buffer_size / self.sample_rate
                time.sleep(sleep_time * 0.5)  # Process ahead
                
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
    
    def _generate_buffer(self) -> np.ndarray:
        """Generate a buffer of mixed audio"""
        # Create output buffer (stereo)
        output = np.zeros((2, self.buffer_size), dtype=np.float32)
        
        # Get crossfader position
        cf_pos = self.mixer.crossfader
        
        # Calculate deck gains
        if cf_pos < 0:
            gains = {'A': 1.0, 'B': 1.0 + cf_pos, 'C': 0.0, 'D': 0.0}
        else:
            gains = {'A': 1.0 - cf_pos, 'B': 1.0, 'C': 0.0, 'D': 0.0}
        
        # Mix each active deck
        for deck_name, deck_state in self.decks.items():
            if deck_state.playing and deck_state.audio_data is not None:
                # Get deck buffer
                deck_buffer = self._get_deck_buffer(deck_name, deck_state)
                
                # Apply gain
                deck_gain = gains.get(deck_name, 0.0) * deck_state.volume
                
                # Mix into output
                output += deck_buffer * deck_gain
        
        # Apply master volume and limiting
        output *= self.mixer.master_volume
        output = np.clip(output, -1.0, 1.0)
        
        return output
    
    def _get_deck_buffer(self, deck_name: str, deck_state: DeckState) -> np.ndarray:
        """Get buffer from deck with tempo adjustment"""
        # Calculate playback rate
        rate = 1.0 + deck_state.tempo
        
        # Calculate frames needed
        frames_needed = int(self.buffer_size * rate)
        
        # Get audio data
        audio = deck_state.audio_data
        total_frames = audio.shape[1]
        
        # Check bounds
        if deck_state.position_frames + frames_needed >= total_frames:
            # Handle end of track
            frames_available = total_frames - deck_state.position_frames
            buffer = np.zeros((2, self.buffer_size), dtype=np.float32)
            
            if frames_available > 0:
                # Resample available frames
                available_audio = audio[:, deck_state.position_frames:deck_state.position_frames + frames_available]
                resampled = librosa.resample(available_audio, orig_sr=rate, target_sr=1.0, axis=1)
                copy_frames = min(len(resampled[0]), self.buffer_size)
                buffer[:, :copy_frames] = resampled[:, :copy_frames]
            
            # Stop playback
            deck_state.playing = False
            deck_state.position_frames = total_frames - 1
            
        else:
            # Get audio segment
            segment = audio[:, deck_state.position_frames:deck_state.position_frames + frames_needed]
            
            # Resample for tempo adjustment
            if rate != 1.0:
                buffer = librosa.resample(segment, orig_sr=rate, target_sr=1.0, axis=1)
                # Ensure correct size
                if buffer.shape[1] > self.buffer_size:
                    buffer = buffer[:, :self.buffer_size]
                elif buffer.shape[1] < self.buffer_size:
                    pad_width = self.buffer_size - buffer.shape[1]
                    buffer = np.pad(buffer, ((0, 0), (0, pad_width)), mode='constant')
            else:
                buffer = segment[:, :self.buffer_size]
            
            # Update position
            deck_state.position_frames += frames_needed
            
            # Handle looping
            if deck_state.looping and deck_state.loop_out is not None:
                loop_out_frames = int(deck_state.loop_out * total_frames)
                if deck_state.position_frames >= loop_out_frames:
                    loop_in_frames = int(deck_state.loop_in * total_frames)
                    deck_state.position_frames = loop_in_frames
        
        # Update position (0-1)
        deck_state.position = deck_state.position_frames / total_frames
        
        return buffer.astype(np.float32)
    
    # --- Output ---
    def get_audio_stream(self) -> Optional[np.ndarray]:
        """Get next audio buffer from queue"""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
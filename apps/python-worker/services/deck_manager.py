"""Deck Manager Service for DJ mixing operations"""
import asyncio
import json
import logging
import sqlite3
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import numpy as np
import librosa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Deck, DeckHistory, Track, MixerState, DeckStatus, SyncMode
from models.database import get_session
from tools.dj_toolset import DJToolset
from utils.enhanced_analyzer import EnhancedTrackAnalyzer
from services.mixer_manager import MixerManager

logger = logging.getLogger(__name__)


class DeckManager:
    """Manages virtual deck operations and state persistence"""
    
    def __init__(self, engine):
        self.engine = engine
        self.dj_toolset = DJToolset()
        self._audio_cache: Dict[str, np.ndarray] = {}
        self._deck_locks = {
            'A': asyncio.Lock(),
            'B': asyncio.Lock(),
            'C': asyncio.Lock(),
            'D': asyncio.Lock()
        }
        # Path to tracks database
        self.tracks_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tracks.db")
        # Mixer manager for coordination
        self.mixer_manager = None  # Will be set after initialization
        
    async def get_deck_state(self, deck_id: str) -> Optional[Dict]:
        """Get current state of a deck"""
        async with get_session(self.engine) as session:
            deck = await session.get(Deck, deck_id)
            if not deck:
                return None
                
            # Convert to dict with all relevant info
            state = {
                'id': deck.id,
                'status': deck.status.value if deck.status else 'empty',
                'track_id': deck.track_id,
                'track_filepath': deck.track_filepath,
                'position': deck.position or 0.0,
                'position_normalized': deck.position_normalized or 0.0,
                'is_playing': deck.is_playing or False,
                'bpm': deck.bpm,
                'original_bpm': deck.original_bpm,
                'tempo_adjust': deck.tempo_adjust or 0.0,
                'volume': deck.volume or 1.0,
                'gain': deck.gain or 1.0,
                'eq_low': deck.eq_low or 0.0,
                'eq_mid': deck.eq_mid or 0.0,
                'eq_high': deck.eq_high or 0.0,
                'sync_mode': deck.sync_mode.value if deck.sync_mode else 'off',
                'cue_points': json.loads(deck.cue_points) if deck.cue_points else {},
                'effects_enabled': json.loads(deck.effects_enabled) if deck.effects_enabled else [],
                'loaded_at': deck.loaded_at.isoformat() if deck.loaded_at else None
            }
            
            # Include track info if loaded
            if deck.track_filepath:
                # Get track info from tracks.db
                try:
                    conn = sqlite3.connect(self.tracks_db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT title, artist, duration, genre, key, energy_level as energy
                        FROM tracks
                        WHERE filepath = ?
                    """, (deck.track_filepath,))
                    
                    row = cursor.fetchone()
                    if row:
                        state['track_info'] = dict(row)
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"Error getting track info: {e}")
            
            return state
    
    async def get_all_decks(self) -> List[Dict]:
        """Get state of all decks"""
        decks = []
        for deck_id in ['A', 'B', 'C', 'D']:
            state = await self.get_deck_state(deck_id)
            if state:
                decks.append(state)
        return decks
    
    async def load_track(self, deck_id: str, track_filepath: str) -> Dict:
        """Load a track onto a deck"""
        async with self._deck_locks[deck_id]:
            async with get_session(self.engine) as session:
                # Get the deck
                deck = await session.get(Deck, deck_id)
                if not deck:
                    return {
                        'success': False,
                        'deck_id': deck_id,
                        'track': None,
                        'error': f'Deck {deck_id} not found'
                    }
                
                # Get track from tracks.db
                track = None
                track_id = None
                
                try:
                    conn = sqlite3.connect(self.tracks_db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT id, filename, filepath, duration, title, artist, album, 
                               genre, year, has_artwork, bpm, key, energy_level as energy
                        FROM tracks
                        WHERE filepath = ?
                    """, (track_filepath,))
                    
                    row = cursor.fetchone()
                    if row:
                        track = dict(row)
                        track_id = track['id']
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"Error querying tracks.db: {e}")
                
                if not track:
                    return {
                        'success': False,
                        'deck_id': deck_id,
                        'track': None,
                        'error': f'Track not found: {track_filepath}'
                    }
                
                # Save current track to history if there was one
                if deck.track_id and deck.started_playing_at:
                    history = DeckHistory(
                        deck_id=deck_id,
                        track_id=deck.track_id,
                        track_filepath=deck.track_filepath,
                        loaded_at=deck.loaded_at,
                        started_playing_at=deck.started_playing_at,
                        stopped_playing_at=datetime.utcnow(),
                        play_duration=(datetime.utcnow() - deck.started_playing_at).total_seconds() if deck.started_playing_at else 0,
                        tempo_adjust_used=deck.tempo_adjust,
                        max_gain_applied=deck.gain,
                        effects_used=deck.effects_enabled
                    )
                    session.add(history)
                
                # Update deck state
                deck.track_id = track_id
                deck.track_filepath = track['filepath']
                deck.status = DeckStatus.LOADED
                deck.position = 0.0
                deck.position_normalized = 0.0
                deck.is_playing = False
                deck.original_bpm = track['bpm']
                deck.bpm = track['bpm']
                deck.tempo_adjust = 0.0
                deck.loaded_at = datetime.utcnow()
                deck.audio_cached = False
                deck.started_playing_at = None  # Initialize this field
                
                # Use DJToolset to load track
                try:
                    self.dj_toolset.load_deck(deck_id, track_filepath)
                    
                    # Pre-load audio for caching
                    await self._cache_audio(track_filepath)
                    deck.audio_cached = True
                    
                except Exception as e:
                    logger.error(f"Error loading track with DJToolset: {e}")
                
                await session.commit()
                
                # Optionally apply auto-gain on load
                if self.mixer_manager:
                    try:
                        await self.mixer_manager.auto_gain_deck(deck_id)
                    except Exception as e:
                        logger.warning(f"Failed to apply auto-gain: {e}")
                
                return {
                    'success': True,
                    'deck_id': deck_id,
                    'track': {
                        'filepath': track['filepath'],
                        'title': track['title'],
                        'artist': track['artist'],
                        'bpm': track['bpm'],
                        'duration': track['duration'],
                        'key': track.get('key')
                    }
                }
    
    async def clear_deck(self, deck_id: str) -> Dict:
        """Clear a deck"""
        async with self._deck_locks[deck_id]:
            async with get_session(self.engine) as session:
                deck = await session.get(Deck, deck_id)
                if not deck:
                    return {'success': False, 'error': f'Deck {deck_id} not found'}
                
                # Save to history if playing
                if deck.is_playing and deck.started_playing_at:
                    history = DeckHistory(
                        deck_id=deck_id,
                        track_id=deck.track_id,
                        track_filepath=deck.track_filepath,
                        loaded_at=deck.loaded_at,
                        started_playing_at=deck.started_playing_at,
                        stopped_playing_at=datetime.utcnow(),
                        play_duration=(datetime.utcnow() - deck.started_playing_at).total_seconds(),
                        tempo_adjust_used=deck.tempo_adjust,
                        max_gain_applied=deck.gain,
                        effects_used=deck.effects_enabled
                    )
                    session.add(history)
                
                # Clear deck state
                deck.track_id = None
                deck.track_filepath = None
                deck.status = DeckStatus.EMPTY
                deck.position = 0.0
                deck.position_normalized = 0.0
                deck.is_playing = False
                deck.bpm = None
                deck.original_bpm = None
                deck.loaded_at = None
                deck.audio_cached = False
                
                # Clear from DJToolset
                self.dj_toolset.clear_deck(deck_id)
                
                # Clear from cache
                if deck.track_filepath in self._audio_cache:
                    del self._audio_cache[deck.track_filepath]
                
                await session.commit()
                
                return {'success': True, 'deck_id': deck_id}
    
    async def update_deck_state(self, deck_id: str, updates: Dict) -> Dict:
        """Update deck state (position, tempo, volume, etc)"""
        async with self._deck_locks[deck_id]:
            async with get_session(self.engine) as session:
                deck = await session.get(Deck, deck_id)
                if not deck:
                    return {'success': False, 'error': f'Deck {deck_id} not found'}
                
                # Update allowed fields
                allowed_fields = [
                    'position', 'position_normalized', 'is_playing', 'tempo_adjust',
                    'volume', 'gain', 'eq_low', 'eq_mid', 'eq_high', 'filter_cutoff',
                    'sync_mode', 'looping', 'loop_in', 'loop_out'
                ]
                
                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(deck, field, value)
                        
                # Special handling for some fields
                if 'tempo_adjust' in updates:
                    # Recalculate BPM
                    if deck.original_bpm:
                        deck.bpm = deck.original_bpm * (1 + updates['tempo_adjust'] / 100)
                        
                        # Update DJToolset (expects value from -0.5 to 0.5)
                        self.dj_toolset.set_tempo(deck_id, updates['tempo_adjust'] / 100)
                
                if 'is_playing' in updates:
                    if updates['is_playing'] and not deck.is_playing:
                        # Starting playback
                        deck.status = DeckStatus.PLAYING
                        if not hasattr(deck, 'started_playing_at'):
                            deck.started_playing_at = datetime.utcnow()
                    elif not updates['is_playing'] and deck.is_playing:
                        # Stopping playback
                        deck.status = DeckStatus.PAUSED
                
                if 'sync_mode' in updates:
                    deck.sync_mode = SyncMode(updates['sync_mode'])
                
                if 'cue_points' in updates:
                    deck.cue_points = json.dumps(updates['cue_points'])
                
                if 'effects_enabled' in updates:
                    deck.effects_enabled = json.dumps(updates['effects_enabled'])
                
                await session.commit()
                
                return {
                    'success': True,
                    'deck_id': deck_id,
                    'updated_fields': list(updates.keys())
                }
    
    async def get_deck_history(self, deck_id: str, limit: int = 50) -> List[Dict]:
        """Get play history for a deck"""
        async with get_session(self.engine) as session:
            stmt = (
                select(DeckHistory)
                .where(DeckHistory.deck_id == deck_id)
                .order_by(DeckHistory.started_playing_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            history_entries = result.scalars().all()
            
            history = []
            for entry in history_entries:
                history.append({
                    'id': entry.id,
                    'track_filepath': entry.track_filepath,
                    'loaded_at': entry.loaded_at.isoformat() if entry.loaded_at else None,
                    'started_playing_at': entry.started_playing_at.isoformat() if entry.started_playing_at else None,
                    'stopped_playing_at': entry.stopped_playing_at.isoformat() if entry.stopped_playing_at else None,
                    'play_duration': entry.play_duration,
                    'tempo_adjust_used': entry.tempo_adjust_used,
                    'effects_used': json.loads(entry.effects_used) if entry.effects_used else [],
                    'transition_in_type': entry.transition_in_type,
                    'transition_out_type': entry.transition_out_type
                })
            
            return history
    
    async def get_mixer_state(self) -> Dict:
        """Get current mixer state"""
        async with get_session(self.engine) as session:
            mixer = await session.get(MixerState, 1)  # Single mixer instance
            if not mixer:
                return None
                
            return {
                'crossfader': mixer.crossfader,
                'crossfader_curve': mixer.crossfader_curve,
                'master_volume': mixer.master_volume,
                'master_gain': mixer.master_gain,
                'monitor_volume': mixer.monitor_volume,
                'monitor_cue_mix': mixer.monitor_cue_mix,
                'recording': mixer.recording,
                'broadcasting': mixer.broadcasting
            }
    
    async def update_mixer_state(self, updates: Dict) -> Dict:
        """Update mixer state"""
        async with get_session(self.engine) as session:
            mixer = await session.get(MixerState, 1)
            if not mixer:
                return {'success': False, 'error': 'Mixer state not found'}
            
            allowed_fields = [
                'crossfader', 'crossfader_curve', 'master_volume', 'master_gain',
                'monitor_volume', 'monitor_cue_mix', 'recording', 'broadcasting'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(mixer, field, value)
            
            await session.commit()
            
            return {
                'success': True,
                'updated_fields': list(updates.keys())
            }
    
    async def sync_decks(self, leader_deck_id: str, follower_deck_id: str) -> Dict:
        """Sync two decks for beatmatching"""
        async with get_session(self.engine) as session:
            leader = await session.get(Deck, leader_deck_id)
            follower = await session.get(Deck, follower_deck_id)
            
            if not leader or not follower:
                return {'success': False, 'error': 'One or both decks not found'}
            
            if not leader.bpm or not follower.original_bpm:
                return {'success': False, 'error': 'BPM information missing'}
            
            # Calculate tempo adjustment needed
            tempo_adjust = ((leader.bpm / follower.original_bpm) - 1) * 100
            
            # Limit to ±50%
            tempo_adjust = max(-50, min(50, tempo_adjust))
            
            # Update follower deck
            follower.tempo_adjust = tempo_adjust
            follower.bpm = follower.original_bpm * (1 + tempo_adjust / 100)
            follower.sync_mode = SyncMode.FOLLOWER
            
            # Update leader sync mode
            leader.sync_mode = SyncMode.LEADER
            
            await session.commit()
            
            return {
                'success': True,
                'leader_deck': leader_deck_id,
                'follower_deck': follower_deck_id,
                'tempo_adjust': tempo_adjust,
                'matched_bpm': follower.bpm
            }
    
    async def _cache_audio(self, filepath: str) -> np.ndarray:
        """Cache audio data for a track"""
        if filepath in self._audio_cache:
            return self._audio_cache[filepath]
        
        try:
            # Load audio with librosa
            audio, sr = librosa.load(filepath, sr=44100, mono=True)
            self._audio_cache[filepath] = audio
            return audio
        except Exception as e:
            logger.error(f"Error caching audio for {filepath}: {e}")
            return None
    
    async def get_audio_data(self, filepath: str) -> Optional[np.ndarray]:
        """Get cached audio data for a track"""
        return await self._cache_audio(filepath)
    
    async def calculate_mix_point(self, deck_a_id: str, deck_b_id: str) -> Dict:
        """Calculate optimal mix point between two decks"""
        async with get_session(self.engine) as session:
            deck_a = await session.get(Deck, deck_a_id)
            deck_b = await session.get(Deck, deck_b_id)
            
            if not deck_a or not deck_b or not deck_a.track_filepath or not deck_b.track_filepath:
                return {'success': False, 'error': 'Decks not properly loaded'}
            
            # Get beat grids from tracks.db
            beats_a = []
            beats_b = []
            
            try:
                conn = sqlite3.connect(self.tracks_db_path)
                cursor = conn.cursor()
                
                # Get beat times for track A
                cursor.execute("SELECT beat_times FROM tracks WHERE filepath = ?", (deck_a.track_filepath,))
                row = cursor.fetchone()
                if row and row[0]:
                    beats_a = json.loads(row[0])
                
                # Get beat times for track B
                cursor.execute("SELECT beat_times FROM tracks WHERE filepath = ?", (deck_b.track_filepath,))
                row = cursor.fetchone()
                if row and row[0]:
                    beats_b = json.loads(row[0])
                
                conn.close()
            except Exception as e:
                logger.error(f"Error getting beat times: {e}")
                return {'success': False, 'error': 'Failed to get beat data'}
            
            if not beats_a or not beats_b:
                return {'success': False, 'error': 'Beat grid data not available'}
            
            # Find mix points (usually 16 or 32 bars before end of track A)
            # and corresponding intro point in track B
            bars_before_end = 32  # Professional standard
            beats_per_bar = 4
            beats_needed = bars_before_end * beats_per_bar
            
            if len(beats_a) > beats_needed:
                outro_start_beat = len(beats_a) - beats_needed
                outro_start_time = beats_a[outro_start_beat]
            else:
                outro_start_time = beats_a[0]  # Fallback to beginning
            
            # Find good intro point in track B (after intro, usually 32-64 beats in)
            intro_beats = min(64, len(beats_b) // 4)
            intro_start_time = beats_b[intro_beats] if len(beats_b) > intro_beats else 0
            
            return {
                'success': True,
                'deck_a': {
                    'deck_id': deck_a_id,
                    'outro_start_time': outro_start_time,
                    'outro_start_beat': outro_start_beat if 'outro_start_beat' in locals() else 0
                },
                'deck_b': {
                    'deck_id': deck_b_id,
                    'intro_start_time': intro_start_time,
                    'intro_start_beat': intro_beats
                },
                'transition_duration': bars_before_end / (deck_a.bpm / 60) if deck_a.bpm else 30  # seconds
            }
    
    async def get_deck_effective_output(self, deck_id: str) -> Dict:
        """Get the effective output level for a deck considering all mixer settings"""
        if not self.mixer_manager:
            # Fallback if mixer manager not available
            async with get_session(self.engine) as session:
                deck = await session.get(Deck, deck_id)
                if not deck:
                    return {'deck_id': deck_id, 'level': 0.0, 'error': 'Deck not found'}
                
                return {
                    'deck_id': deck_id,
                    'level': deck.volume * deck.gain,
                    'clipping': False
                }
        
        # Use mixer manager for full calculation
        return await self.mixer_manager.calculate_channel_output(deck_id)
    
    def set_mixer_manager(self, mixer_manager):
        """Set the mixer manager reference for coordination"""
        self.mixer_manager = mixer_manager
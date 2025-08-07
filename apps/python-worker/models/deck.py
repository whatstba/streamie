"""Deck models for DJ system"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base


class DeckStatus(enum.Enum):
    """Deck status enumeration"""

    EMPTY = "empty"
    LOADED = "loaded"
    PLAYING = "playing"
    PAUSED = "paused"
    CUEING = "cueing"


class SyncMode(enum.Enum):
    """Deck sync mode enumeration"""

    OFF = "off"
    LEADER = "leader"
    FOLLOWER = "follower"


class Deck(Base):
    """Virtual deck state for DJ mixing"""

    __tablename__ = "decks"

    id = Column(String, primary_key=True)  # A, B, C, D

    # Track information
    track_id = Column(Integer, ForeignKey("tracks.id"))
    track_filepath = Column(String)  # Cached for quick access
    status = Column(Enum(DeckStatus), default=DeckStatus.EMPTY)

    # Playback state
    position = Column(Float, default=0.0)  # Current position in seconds
    position_normalized = Column(Float, default=0.0)  # 0.0 to 1.0
    is_playing = Column(Boolean, default=False)

    # Tempo and sync
    bpm = Column(Float)  # Current BPM (with tempo adjustment)
    original_bpm = Column(Float)  # Original track BPM
    tempo_adjust = Column(Float, default=0.0)  # -50% to +50%
    sync_mode = Column(Enum(SyncMode), default=SyncMode.OFF)
    beat_offset = Column(Float, default=0.0)

    # Audio controls
    volume = Column(Float, default=1.0)  # 0.0 to 1.0
    gain = Column(Float, default=1.0)  # Pre-gain
    eq_low = Column(Float, default=0.0)  # -1.0 to 1.0
    eq_mid = Column(Float, default=0.0)
    eq_high = Column(Float, default=0.0)
    filter_cutoff = Column(Float, default=1.0)  # 0.0 to 1.0

    # Effects
    effects_enabled = Column(Text)  # JSON array of active effect IDs

    # Cue points and loops
    cue_points = Column(Text)  # JSON dict {1: position, 2: position, ...}
    loop_in = Column(Float)
    loop_out = Column(Float)
    looping = Column(Boolean, default=False)

    # Metadata
    loaded_at = Column(DateTime)
    started_playing_at = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Audio cache
    audio_cached = Column(Boolean, default=False)
    cache_filepath = Column(String)  # Path to cached numpy array
    waveform_data = Column(Text)  # JSON waveform for visualization

    # Mixer integration
    crossfader_gain = Column(Float, default=1.0)  # Gain from crossfader position
    auto_gain_applied = Column(Boolean, default=False)
    cue_active = Column(Boolean, default=False)  # Cue/monitor active
    peak_level = Column(Float, default=0.0)  # Peak level meter
    rms_level = Column(Float, default=0.0)  # RMS level meter

    # Relationships
    track = relationship("Track")
    history_entries = relationship("DeckHistory", back_populates="deck")

    def __repr__(self):
        return f"<Deck(id='{self.id}', status={self.status.value if self.status else 'empty'}, track='{self.track_filepath}')>"


class DeckHistory(Base):
    """History of tracks played on each deck"""

    __tablename__ = "deck_history"

    id = Column(Integer, primary_key=True)
    deck_id = Column(String, ForeignKey("decks.id"))
    track_id = Column(Integer, ForeignKey("tracks.id"))
    track_filepath = Column(String)  # Denormalized for quick access

    # Playback info
    loaded_at = Column(DateTime, nullable=False)
    started_playing_at = Column(DateTime)
    stopped_playing_at = Column(DateTime)
    play_duration = Column(Float)  # Total seconds played

    # Mix context
    previous_track_id = Column(Integer, ForeignKey("tracks.id"))
    next_track_id = Column(Integer, ForeignKey("tracks.id"))
    transition_in_type = Column(String)  # How this track was mixed in
    transition_out_type = Column(String)  # How this track was mixed out

    # Performance metrics
    tempo_adjust_used = Column(Float)
    max_gain_applied = Column(Float)
    effects_used = Column(Text)  # JSON array

    # Session context
    session_id = Column(String)  # Link to DJ session if applicable
    mix_id = Column(
        Integer, ForeignKey("mixes.id")
    )  # Link to planned mix if applicable

    # Relationships
    deck = relationship("Deck", back_populates="history_entries")
    track = relationship("Track", foreign_keys=[track_id])
    previous_track = relationship("Track", foreign_keys=[previous_track_id])
    next_track = relationship("Track", foreign_keys=[next_track_id])

    def __repr__(self):
        return f"<DeckHistory(deck='{self.deck_id}', track='{self.track_filepath}', played_at={self.started_playing_at})>"


class MixerState(Base):
    """Global mixer state"""

    __tablename__ = "mixer_state"

    id = Column(Integer, primary_key=True)

    # Crossfader
    crossfader = Column(Float, default=0.0)  # -1.0 (A) to 1.0 (B)
    crossfader_curve = Column(String, default="linear")  # linear, logarithmic, scratch

    # Master outputs
    master_volume = Column(Float, default=0.8)
    master_gain = Column(Float, default=1.0)
    monitor_volume = Column(Float, default=0.7)
    monitor_cue_mix = Column(Float, default=0.5)  # 0=cue only, 1=master only

    # Recording/broadcasting
    recording = Column(Boolean, default=False)
    recording_filepath = Column(String)
    recording_started_at = Column(DateTime)
    broadcasting = Column(Boolean, default=False)
    broadcast_url = Column(String)

    # Metadata
    session_id = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MixerState(crossfader={self.crossfader:.2f}, master_vol={self.master_volume:.2f})>"

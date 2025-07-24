"""Database models for DJ system"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncAttrs,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models with async support"""

    pass


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    filepath = Column(String, unique=True, nullable=False)
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    duration = Column(Float)  # seconds
    bpm = Column(Float)
    key = Column(String)  # Musical key
    energy = Column(Float)  # 0-1 energy level
    genre = Column(String)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Additional analysis data
    beat_times = Column(Text)  # JSON array of beat timestamps
    key_confidence = Column(Float)
    mood_tags = Column(Text)  # JSON array of mood tags

    # Relationships
    mix_tracks = relationship("MixTrack", back_populates="track")

    def __repr__(self):
        return f"<Track(title='{self.title}', artist='{self.artist}', bpm={self.bpm})>"


class Mix(Base):
    __tablename__ = "mixes"

    id = Column(Integer, primary_key=True)
    vibe_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    duration = Column(Float)  # total seconds
    track_count = Column(Integer)
    status = Column(String, default="pending")  # pending, processing, completed, failed

    # Relationships
    tracks = relationship(
        "MixTrack", back_populates="mix", order_by="MixTrack.position"
    )

    def __repr__(self):
        return f"<Mix(id={self.id}, vibe='{self.vibe_description}', tracks={self.track_count})>"


class MixTrack(Base):
    __tablename__ = "mix_tracks"

    id = Column(Integer, primary_key=True)
    mix_id = Column(Integer, ForeignKey("mixes.id"))
    track_id = Column(Integer, ForeignKey("tracks.id"))
    position = Column(Integer)  # Order in the mix

    # Transition details
    transition_type = Column(String)  # crossfade, echo_out, filter_sweep, etc.
    transition_duration = Column(Float)  # seconds
    transition_start_time = Column(Float)  # When in the track to start transition

    # Mix parameters at this point
    tempo_adjustment = Column(Float, default=0.0)  # -50% to +50%
    gain = Column(Float, default=1.0)
    eq_low = Column(Float, default=0.0)  # -1 to 1
    eq_mid = Column(Float, default=0.0)
    eq_high = Column(Float, default=0.0)

    # Relationships
    mix = relationship("Mix", back_populates="tracks")
    track = relationship("Track", back_populates="mix_tracks")

    def __repr__(self):
        return f"<MixTrack(position={self.position}, track_id={self.track_id})>"


# Database setup
async def init_db(db_url: str = "sqlite+aiosqlite:///./dj_system.db"):
    """Initialize database with async engine"""
    engine = create_async_engine(db_url, echo=False)

    # Create tables asynchronously
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


def get_async_session_maker(engine):
    """Get async session maker"""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class get_session:
    """Async context manager for database sessions"""

    def __init__(self, engine):
        self.engine = engine
        self.session_maker = get_async_session_maker(engine)
        self.session = None

    async def __aenter__(self):
        self.session = self.session_maker()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

"""Music library management service"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy import select, and_, or_, func
import logging
import json

from models.database import Track, init_db, get_session
from tools.analyzers import TrackAnalyzer
from utils.mood_interpreter import interpret_mood

logger = logging.getLogger(__name__)


class MusicLibraryManager:
    """Manages music library scanning and metadata"""

    def __init__(self, db_engine=None):
        self.db_engine = db_engine
        self.analyzer = TrackAnalyzer()
        self.supported_formats = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]

    async def scan_directory(self, directory: str, rescan: bool = False) -> Dict:
        """Scan directory for music files"""
        scanned = 0
        analyzed = 0
        errors = []

        # Get all audio files
        audio_files = self._find_audio_files(directory)
        logger.info(f"Found {len(audio_files)} audio files in {directory}")

        # Get database session
        async with get_session(self.db_engine) as session:
            for filepath in audio_files:
                try:
                    # Check if already in database
                    existing = await session.execute(
                        select(Track).where(Track.filepath == str(filepath))
                    )
                    track = existing.scalar_one_or_none()

                    if track and not rescan:
                        logger.debug(f"Skipping existing track: {filepath}")
                        continue

                    # Analyze track
                    logger.info(f"Analyzing: {filepath}")
                    analysis = await self.analyzer.analyze_track(str(filepath))

                    if analysis.get("analyzed"):
                        # Extract metadata
                        metadata = self._extract_metadata(filepath)

                        # Create or update track
                        if track:
                            # Update existing
                            track.bpm = analysis.get("bpm")
                            track.key = analysis.get("key")
                            track.energy = analysis.get("energy")
                            track.duration = analysis.get("duration")
                            track.beat_times = json.dumps(
                                analysis.get("beat_times", [])
                            )
                            track.key_confidence = analysis.get("key_confidence")
                        else:
                            # Create new
                            track = Track(
                                filepath=str(filepath),
                                title=metadata.get("title", filepath.stem),
                                artist=metadata.get("artist", "Unknown"),
                                album=metadata.get("album", "Unknown"),
                                duration=analysis.get("duration"),
                                bpm=analysis.get("bpm"),
                                key=analysis.get("key"),
                                energy=analysis.get("energy"),
                                genre=metadata.get("genre", "Unknown"),
                                beat_times=json.dumps(analysis.get("beat_times", [])),
                                key_confidence=analysis.get("key_confidence"),
                            )
                            session.add(track)

                        analyzed += 1
                    else:
                        errors.append(
                            {
                                "file": str(filepath),
                                "error": analysis.get("error", "Unknown error"),
                            }
                        )

                    scanned += 1

                    # Commit periodically
                    if scanned % 10 == 0:
                        await session.commit()

                except Exception as e:
                    logger.error(f"Error processing {filepath}: {e}")
                    errors.append({"file": str(filepath), "error": str(e)})

            # Final commit
            await session.commit()

        return {
            "scanned": scanned,
            "analyzed": analyzed,
            "total_files": len(audio_files),
            "errors": errors,
        }

    def _find_audio_files(self, directory: str) -> List[Path]:
        """Find all audio files in directory"""
        audio_files = []
        path = Path(directory)

        for ext in self.supported_formats:
            audio_files.extend(path.rglob(f"*{ext}"))

        return audio_files

    def _extract_metadata(self, filepath: Path) -> Dict:
        """Extract metadata from filename if tags not available"""
        # Basic implementation - can be enhanced with mutagen
        parts = filepath.stem.split(" - ")

        if len(parts) >= 2:
            return {"artist": parts[0].strip(), "title": parts[1].strip()}
        else:
            return {"title": filepath.stem, "artist": "Unknown"}

    async def search_by_mood(
        self, mood_description: str, limit: int = 20
    ) -> List[Track]:
        """Search tracks by mood/vibe description"""
        # Interpret mood
        mood_params = interpret_mood(mood_description)

        async with get_session(self.db_engine) as session:
            # Build query based on mood parameters
            query = select(Track)

            # Filter by BPM range
            if "bpm_min" in mood_params and "bpm_max" in mood_params:
                query = query.where(
                    and_(
                        Track.bpm >= mood_params["bpm_min"],
                        Track.bpm <= mood_params["bpm_max"],
                    )
                )

            # Filter by energy
            if "energy" in mood_params:
                energy_threshold = mood_params["energy"]
                energy_min = max(0, energy_threshold - 0.2)
                energy_max = min(1, energy_threshold + 0.2)
                query = query.where(
                    and_(Track.energy >= energy_min, Track.energy <= energy_max)
                )

            # Filter by genre if specified
            if "genre" in mood_params and mood_params["genre"]:
                query = query.where(Track.genre.ilike(f"%{mood_params['genre']}%"))

            # Order by energy match
            if "energy" in mood_params:
                # Simple ordering for now - can be enhanced
                query = query.order_by(Track.energy.desc())

            # Limit results
            query = query.limit(limit)

            result = await session.execute(query)
            tracks = result.scalars().all()

            return tracks

    async def get_compatible_tracks(self, track: Track, limit: int = 10) -> List[Track]:
        """Find tracks compatible for mixing"""
        async with get_session(self.db_engine) as session:
            # BPM compatibility (within 5%)
            bpm_min = track.bpm * 0.95
            bpm_max = track.bpm * 1.05

            # Key compatibility (Camelot wheel)
            compatible_keys = self._get_compatible_keys(track.key)

            query = select(Track).where(
                and_(
                    Track.id != track.id,
                    Track.bpm >= bpm_min,
                    Track.bpm <= bpm_max,
                    or_(*[Track.key == k for k in compatible_keys])
                    if compatible_keys
                    else True,
                )
            )

            # Order by energy similarity
            # For async queries, we need to use func.abs for absolute difference
            query = query.order_by(func.abs(Track.energy - track.energy)).limit(limit)

            result = await session.execute(query)
            return result.scalars().all()

    def _get_compatible_keys(self, key: str) -> List[str]:
        """Get harmonically compatible keys"""
        # Camelot wheel compatibility
        camelot_compatible = {
            "1A": ["1A", "12A", "2A", "1B"],
            "1B": ["1B", "12B", "2B", "1A"],
            "2A": ["2A", "1A", "3A", "2B"],
            "2B": ["2B", "1B", "3B", "2A"],
            "3A": ["3A", "2A", "4A", "3B"],
            "3B": ["3B", "2B", "4B", "3A"],
            "4A": ["4A", "3A", "5A", "4B"],
            "4B": ["4B", "3B", "5B", "4A"],
            "5A": ["5A", "4A", "6A", "5B"],
            "5B": ["5B", "4B", "6B", "5A"],
            "6A": ["6A", "5A", "7A", "6B"],
            "6B": ["6B", "5B", "7B", "6A"],
            "7A": ["7A", "6A", "8A", "7B"],
            "7B": ["7B", "6B", "8B", "7A"],
            "8A": ["8A", "7A", "9A", "8B"],
            "8B": ["8B", "7B", "9B", "8A"],
            "9A": ["9A", "8A", "10A", "9B"],
            "9B": ["9B", "8B", "10B", "9A"],
            "10A": ["10A", "9A", "11A", "10B"],
            "10B": ["10B", "9B", "11B", "10A"],
            "11A": ["11A", "10A", "12A", "11B"],
            "11B": ["11B", "10B", "12B", "11A"],
            "12A": ["12A", "11A", "1A", "12B"],
            "12B": ["12B", "11B", "1B", "12A"],
        }

        # Check if the key matches Camelot notation
        if key in camelot_compatible:
            return camelot_compatible[key]

        return [key]  # Return same key if not in Camelot format

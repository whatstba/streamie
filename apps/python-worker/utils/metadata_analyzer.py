"""Lightweight metadata analyzer for fast track scanning."""

import os
import sqlite3
from typing import Dict, Optional
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
import logging

logger = logging.getLogger(__name__)


class MetadataAnalyzer:
    """Fast metadata-only analyzer that doesn't load audio data."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def analyze_metadata_only(self, filepath: str) -> Optional[Dict]:
        """Extract metadata without loading audio.

        This is much faster than full audio analysis as it only reads
        file tags and basic properties.
        """
        try:
            # Get file metadata using mutagen
            audio_file = File(filepath)
            if audio_file is None:
                logger.warning(f"Could not read metadata from {filepath}")
                return None

            metadata = {
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "file_size": os.path.getsize(filepath),
                "last_modified": os.path.getmtime(filepath),
            }

            # Extract common tags
            if audio_file.tags:
                metadata["title"] = self._get_tag(
                    audio_file.tags, ["TIT2", "Title", "\xa9nam"]
                )
                metadata["artist"] = self._get_tag(
                    audio_file.tags, ["TPE1", "Artist", "\xa9ART"]
                )
                metadata["album"] = self._get_tag(
                    audio_file.tags, ["TALB", "Album", "\xa9alb"]
                )
                metadata["genre"] = self._get_tag(
                    audio_file.tags, ["TCON", "Genre", "\xa9gen"]
                )
                metadata["year"] = self._get_tag(
                    audio_file.tags, ["TDRC", "Date", "\xa9day"]
                )
                metadata["albumartist"] = self._get_tag(
                    audio_file.tags, ["TPE2", "AlbumArtist", "aART"]
                )
                metadata["track"] = self._get_tag(
                    audio_file.tags, ["TRCK", "TrackNumber", "trkn"]
                )

                # Check for artwork
                metadata["has_artwork"] = self._has_artwork(audio_file)

            # Get duration without loading full audio
            if hasattr(audio_file.info, "length"):
                metadata["duration"] = audio_file.info.length

            # Get basic audio properties
            if hasattr(audio_file.info, "bitrate"):
                metadata["bitrate"] = audio_file.info.bitrate
            if hasattr(audio_file.info, "sample_rate"):
                metadata["sample_rate"] = audio_file.info.sample_rate

            return metadata

        except Exception as e:
            logger.error(f"Error analyzing metadata for {filepath}: {e}")
            return None

    def _get_tag(self, tags, keys):
        """Get tag value from multiple possible keys."""
        for key in keys:
            if key in tags:
                value = tags[key]
                if isinstance(value, list) and value:
                    return str(value[0])
                elif value:
                    return str(value)
        return None

    def _has_artwork(self, audio_file):
        """Check if file has embedded artwork."""
        if isinstance(audio_file, MP3):
            return (
                any(key.startswith("APIC") for key in audio_file.tags.keys())
                if audio_file.tags
                else False
            )
        elif isinstance(audio_file, MP4):
            return "covr" in audio_file.tags if audio_file.tags else False
        elif isinstance(audio_file, FLAC):
            return len(audio_file.pictures) > 0
        return False

    def batch_analyze_metadata(self, filepaths: list, batch_size: int = 100) -> int:
        """Analyze metadata for multiple files efficiently."""
        analyzed_count = 0

        for i in range(0, len(filepaths), batch_size):
            batch = filepaths[i : i + batch_size]
            batch_results = []

            for filepath in batch:
                metadata = self.analyze_metadata_only(filepath)
                if metadata:
                    batch_results.append(metadata)

            # Batch insert/update in database
            if batch_results:
                self._batch_update_database(batch_results)
                analyzed_count += len(batch_results)

            logger.info(
                f"Analyzed metadata for {analyzed_count}/{len(filepaths)} tracks"
            )

        return analyzed_count

    def _batch_update_database(self, metadata_list: list):
        """Batch update database with metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for metadata in metadata_list:
                # Update existing track or insert new
                cursor.execute(
                    """
                    UPDATE tracks SET 
                        filename = ?,
                        file_size = ?,
                        last_modified = ?,
                        title = ?,
                        artist = ?,
                        album = ?,
                        genre = ?,
                        year = ?,
                        albumartist = ?,
                        track = ?,
                        duration = ?,
                        has_artwork = ?,
                        analysis_status = 'metadata_complete'
                    WHERE filepath = ?
                """,
                    (
                        metadata.get("filename"),
                        metadata.get("file_size"),
                        metadata.get("last_modified"),
                        metadata.get("title"),
                        metadata.get("artist"),
                        metadata.get("album"),
                        metadata.get("genre"),
                        metadata.get("year"),
                        metadata.get("albumartist"),
                        metadata.get("track"),
                        metadata.get("duration"),
                        metadata.get("has_artwork", False),
                        metadata["filepath"],
                    ),
                )

                # If no rows updated, insert new track
                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO tracks (
                            filepath, filename, file_size, last_modified,
                            title, artist, album, genre, year, albumartist,
                            track, duration, has_artwork, analysis_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'metadata_complete')
                    """,
                        (
                            metadata["filepath"],
                            metadata.get("filename"),
                            metadata.get("file_size"),
                            metadata.get("last_modified"),
                            metadata.get("title"),
                            metadata.get("artist"),
                            metadata.get("album"),
                            metadata.get("genre"),
                            metadata.get("year"),
                            metadata.get("albumartist"),
                            metadata.get("track"),
                            metadata.get("duration"),
                            metadata.get("has_artwork", False),
                        ),
                    )

            conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error(f"Error batch updating database: {e}")
            raise
        finally:
            conn.close()

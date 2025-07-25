#!/usr/bin/env python3
"""
Analyze musical keys for tracks missing this information.

This script:
- Finds tracks without key information
- Uses Essentia to detect musical keys
- Updates the database with key, scale, and Camelot notation
- Shows progress and handles errors gracefully
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.enhanced_analyzer import EnhancedTrackAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "tracks.db")


class KeyAnalyzer:
    """Analyzes tracks for musical key information."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.analyzer = EnhancedTrackAnalyzer(db_path)
        self.connection = None

    def connect(self):
        """Connect to the database."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def disconnect(self):
        """Disconnect from the database."""
        if self.connection:
            self.connection.close()

    def get_tracks_without_keys(self) -> list:
        """Get list of tracks missing key information."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, filepath, title, artist 
            FROM tracks 
            WHERE key IS NULL OR key = '' OR key = 'Unknown'
            ORDER BY id
        """)
        return cursor.fetchall()

    def update_track_key(self, track_id: int, key_info: dict) -> bool:
        """Update track with key information."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                UPDATE tracks 
                SET key = ?, 
                    key_scale = ?,
                    key_confidence = ?,
                    camelot_key = ?,
                    analyzed_at = ?
                WHERE id = ?
            """,
                (
                    key_info.get("key", "Unknown"),
                    key_info.get("scale", "Unknown"),
                    key_info.get("strength", 0.0),
                    key_info.get("camelot"),
                    datetime.now().isoformat(),
                    track_id,
                ),
            )
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update track {track_id}: {e}")
            self.connection.rollback()
            return False

    def analyze_track_key(self, filepath: str) -> dict:
        """Analyze a single track for key information."""
        try:
            # Use the enhanced analyzer's key detection
            key_info = self.analyzer._detect_key(filepath)
            return key_info
        except Exception as e:
            logger.error(f"Key detection failed for {filepath}: {e}")
            return {
                "key": "Unknown",
                "scale": "Unknown",
                "strength": 0.0,
                "camelot": None,
            }

    def process_all_tracks(self):
        """Process all tracks missing key information."""
        self.connect()

        try:
            # Get tracks without keys
            tracks = self.get_tracks_without_keys()
            total_tracks = len(tracks)

            logger.info(f"Found {total_tracks} tracks without key information")

            if total_tracks == 0:
                logger.info("All tracks already have key information!")
                return

            # Process each track
            success_count = 0
            error_count = 0
            start_time = time.time()

            for i, track in enumerate(tracks, 1):
                track_id = track["id"]
                filepath = track["filepath"]
                title = track["title"] or "Unknown"
                artist = track["artist"] or "Unknown"

                # Progress indicator
                progress = (i / total_tracks) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / i) * (total_tracks - i) if i > 0 else 0

                logger.info(
                    f"[{i}/{total_tracks}] ({progress:.1f}%) Analyzing: {artist} - {title}"
                )

                # Prepend MUSIC_DIR to the relative filepath
                full_filepath = os.path.join(
                    os.path.expanduser("~/Downloads"), filepath
                )

                # Check if file exists
                if not os.path.exists(full_filepath):
                    logger.warning(f"File not found: {full_filepath}")
                    error_count += 1
                    continue

                # Analyze key
                key_info = self.analyze_track_key(full_filepath)

                # Update database
                if self.update_track_key(track_id, key_info):
                    success_count += 1
                    key_str = f"{key_info['key']} {key_info['scale']}"
                    camelot = key_info.get("camelot", "N/A")
                    confidence = key_info.get("strength", 0) * 100
                    logger.info(
                        f"  ✓ Key: {key_str} ({camelot}) - Confidence: {confidence:.1f}%"
                    )
                else:
                    error_count += 1
                    logger.error("  ✗ Failed to update database")

                # Show ETA every 10 tracks
                if i % 10 == 0:
                    logger.info(f"  ⏱️  ETA: {eta / 60:.1f} minutes remaining")

            # Summary
            elapsed_total = time.time() - start_time
            logger.info("=" * 60)
            logger.info("Key analysis complete!")
            logger.info(f"  Total tracks: {total_tracks}")
            logger.info(f"  Successful: {success_count}")
            logger.info(f"  Errors: {error_count}")
            logger.info(f"  Time elapsed: {elapsed_total / 60:.1f} minutes")
            logger.info(
                f"  Average time per track: {elapsed_total / total_tracks:.1f} seconds"
            )

        finally:
            self.disconnect()


def main():
    """Main entry point."""
    analyzer = KeyAnalyzer()

    # Show current status
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tracks")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tracks WHERE key IS NOT NULL AND key != '' AND key != 'Unknown'"
    )
    with_keys = cursor.fetchone()[0]

    conn.close()

    logger.info("=" * 60)
    logger.info("Musical Key Analysis Tool")
    logger.info("=" * 60)
    logger.info(f"Total tracks in database: {total}")
    logger.info(f"Tracks with key information: {with_keys}")
    logger.info(f"Tracks missing key information: {total - with_keys}")
    logger.info("=" * 60)

    # Check for command line argument to skip confirmation
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        logger.info("\nRunning in automatic mode...")
        analyzer.process_all_tracks()
    else:
        # Ask for confirmation
        try:
            response = input(
                "\nDo you want to analyze keys for all tracks missing this information? (y/n): "
            )
            if response.lower() == "y":
                analyzer.process_all_tracks()
            else:
                logger.info("Analysis cancelled.")
        except EOFError:
            logger.info("\nRunning in non-interactive mode...")
            analyzer.process_all_tracks()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze energy levels for tracks missing this information.

This script:
- Finds tracks without energy level information
- Uses librosa to calculate energy metrics
- Updates the database with energy level and profile
- Shows progress and handles errors gracefully
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
import time
import librosa
import numpy as np
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "tracks.db")


class EnergyAnalyzer:
    """Analyzes tracks for energy level information."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Connect to the database."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def disconnect(self):
        """Disconnect from the database."""
        if self.connection:
            self.connection.close()

    def get_tracks_without_energy(self) -> list:
        """Get list of tracks missing energy information."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, filepath, title, artist, genre, bpm 
            FROM tracks 
            WHERE energy_level IS NULL
            ORDER BY id
        """)
        return cursor.fetchall()

    def update_track_energy(self, track_id: int, energy_info: dict) -> bool:
        """Update track with energy information."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                UPDATE tracks 
                SET energy_level = ?, 
                    energy_profile = ?,
                    analyzed_at = ?
                WHERE id = ?
            """,
                (
                    energy_info.get("level", 0.5),
                    energy_info.get("profile", "medium"),
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

    def analyze_track_energy(self, filepath: str) -> dict:
        """Analyze a single track for energy information."""
        try:
            # Load audio with librosa
            y, sr = librosa.load(filepath, sr=None, duration=90)  # Analyze first 90 seconds
            
            # RMS energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Spectral centroid (brightness)
            cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            
            # Zero crossing rate (percussiveness)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            # Calculate overall energy level (0-1)
            # Normalize RMS to 0-1 range
            energy_level = float(np.mean(rms))
            # Scale to 0-1 range (typical RMS values are 0-0.5)
            energy_level = min(energy_level * 2, 1.0)
            
            energy_variance = float(np.std(rms))
            
            # Classify energy profile
            if energy_variance > 0.3:
                energy_profile = "dynamic"
            elif energy_level > 0.7:
                energy_profile = "high"
            elif energy_level < 0.3:
                energy_profile = "low"
            else:
                energy_profile = "medium"
            
            return {
                "level": energy_level,
                "variance": energy_variance,
                "brightness": float(np.mean(cent)),
                "percussiveness": float(np.mean(zcr)),
                "profile": energy_profile,
            }
            
        except Exception as e:
            logger.error(f"Energy analysis failed for {filepath}: {e}")
            # Return default values
            return {
                "level": 0.5,
                "variance": 0.1,
                "brightness": 5000.0,
                "percussiveness": 0.1,
                "profile": "medium",
            }

    def estimate_energy_from_features(self, bpm: Optional[float], genre: Optional[str]) -> dict:
        """Quick energy estimation based on BPM and genre when audio analysis fails."""
        energy_level = 0.5  # Default
        
        if bpm:
            # BPM-based estimation
            if bpm < 100:
                energy_level = bpm / 200
            elif bpm < 128:
                energy_level = 0.5 + (bpm - 100) / 56
            else:
                energy_level = min(0.8 + (bpm - 128) / 40, 1.0)
        
        if genre:
            genre_lower = genre.lower()
            # Genre-based adjustments
            if any(g in genre_lower for g in ["ambient", "downtempo", "chill"]):
                energy_level = min(energy_level * 0.7, 0.5)
            elif any(g in genre_lower for g in ["techno", "hardstyle", "dnb", "drum and bass"]):
                energy_level = max(energy_level * 1.2, 0.6)
            elif any(g in genre_lower for g in ["house", "dance", "electronic"]):
                energy_level = max(energy_level, 0.5)
        
        # Determine profile based on estimated level
        if energy_level > 0.7:
            profile = "high"
        elif energy_level < 0.3:
            profile = "low"
        else:
            profile = "medium"
        
        return {
            "level": energy_level,
            "variance": 0.1,
            "brightness": 5000.0,
            "percussiveness": 0.1,
            "profile": profile,
        }

    def process_all_tracks(self):
        """Process all tracks missing energy information."""
        self.connect()

        try:
            # Get tracks without energy
            tracks = self.get_tracks_without_energy()
            total_tracks = len(tracks)

            logger.info(f"Found {total_tracks} tracks without energy information")

            if total_tracks == 0:
                logger.info("All tracks already have energy information!")
                return

            # Process each track
            success_count = 0
            error_count = 0
            estimated_count = 0
            start_time = time.time()

            for i, track in enumerate(tracks, 1):
                track_id = track["id"]
                filepath = track["filepath"]
                title = track["title"] or "Unknown"
                artist = track["artist"] or "Unknown"
                genre = track["genre"]
                bpm = track["bpm"]

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
                    # Try to estimate from BPM and genre
                    energy_info = self.estimate_energy_from_features(bpm, genre)
                    if self.update_track_energy(track_id, energy_info):
                        estimated_count += 1
                        logger.info(
                            f"  ⚡ Estimated: Energy={energy_info['level']:.2f} ({energy_info['profile']})"
                        )
                    else:
                        error_count += 1
                    continue

                # Analyze energy
                energy_info = self.analyze_track_energy(full_filepath)

                # Update database
                if self.update_track_energy(track_id, energy_info):
                    success_count += 1
                    logger.info(
                        f"  ✓ Energy: {energy_info['level']:.2f} ({energy_info['profile']}) - Variance: {energy_info['variance']:.2f}"
                    )
                else:
                    error_count += 1
                    logger.error(f"  ✗ Failed to update database")

                # Show ETA every 10 tracks
                if i % 10 == 0:
                    logger.info(f"  ⏱️  ETA: {eta / 60:.1f} minutes remaining")

            # Summary
            elapsed_total = time.time() - start_time
            logger.info("=" * 60)
            logger.info(f"Energy analysis complete!")
            logger.info(f"  Total tracks: {total_tracks}")
            logger.info(f"  Successfully analyzed: {success_count}")
            logger.info(f"  Estimated from metadata: {estimated_count}")
            logger.info(f"  Errors: {error_count}")
            logger.info(f"  Time elapsed: {elapsed_total / 60:.1f} minutes")
            if total_tracks > 0:
                logger.info(
                    f"  Average time per track: {elapsed_total / total_tracks:.1f} seconds"
                )

        finally:
            self.disconnect()


def main():
    """Main entry point."""
    analyzer = EnergyAnalyzer()

    # Show current status
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tracks")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tracks WHERE energy_level IS NOT NULL"
    )
    with_energy = cursor.fetchone()[0]

    conn.close()

    logger.info("=" * 60)
    logger.info("Track Energy Analysis Tool")
    logger.info("=" * 60)
    logger.info(f"Total tracks in database: {total}")
    logger.info(f"Tracks with energy information: {with_energy}")
    logger.info(f"Tracks missing energy information: {total - with_energy}")
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
                "\nDo you want to analyze energy levels for all tracks missing this information? (y/n): "
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
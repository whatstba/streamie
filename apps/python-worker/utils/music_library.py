"""Music library management for Streamie."""

import os
import sqlite3
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MusicLibraryManager:
    """Manages music folders and library configuration."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add_music_folder(self, folder_path: str, auto_scan: bool = True) -> Dict:
        """Add a music folder to the library."""
        # Validate folder
        folder_path = os.path.abspath(folder_path)
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder does not exist: {folder_path}")
        if not os.path.isdir(folder_path):
            raise ValueError(f"Path is not a directory: {folder_path}")
        if not os.access(folder_path, os.R_OK):
            raise ValueError(f"No read permission for folder: {folder_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO music_folders 
                (path, enabled, auto_scan, last_scan)
                VALUES (?, 1, ?, NULL)
            """,
                (folder_path, auto_scan),
            )

            folder_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added music folder: {folder_path}")

            return {
                "id": folder_id,
                "path": folder_path,
                "enabled": True,
                "auto_scan": auto_scan,
                "status": "added",
            }

        finally:
            conn.close()

    def remove_music_folder(self, folder_path: str) -> bool:
        """Remove a music folder from the library."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM music_folders WHERE path = ?", (folder_path,))
            affected = cursor.rowcount
            conn.commit()

            if affected > 0:
                logger.info(f"Removed music folder: {folder_path}")
                return True
            return False

        finally:
            conn.close()

    def get_music_folders(self) -> List[Dict]:
        """Get all configured music folders."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, path, enabled, auto_scan, last_scan, created_at
                FROM music_folders
                ORDER BY path
            """)

            folders = []
            for row in cursor.fetchall():
                folder = dict(row)
                # Check if folder still exists
                folder["exists"] = os.path.exists(folder["path"])
                folder["accessible"] = folder["exists"] and os.access(
                    folder["path"], os.R_OK
                )
                folders.append(folder)

            return folders

        finally:
            conn.close()

    def update_folder_scan_time(self, folder_path: str):
        """Update the last scan time for a folder."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE music_folders 
                SET last_scan = CURRENT_TIMESTAMP 
                WHERE path = ?
            """,
                (folder_path,),
            )
            conn.commit()

        finally:
            conn.close()

    def scan_folder_for_tracks(self, folder_path: str) -> List[str]:
        """Scan a folder for audio files."""
        audio_extensions = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".m4p"}
        tracks = []

        try:
            for root, _, files in os.walk(folder_path):
                for filename in files:
                    if any(filename.lower().endswith(ext) for ext in audio_extensions):
                        filepath = os.path.join(root, filename)
                        tracks.append(filepath)

        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")

        return tracks

    def get_new_tracks(self, folder_path: str) -> List[str]:
        """Get tracks in folder that aren't in the database."""
        tracks = self.scan_folder_for_tracks(folder_path)

        if not tracks:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get relative paths of existing tracks
            cursor.execute("SELECT filepath FROM tracks")
            existing_paths = {row[0] for row in cursor.fetchall()}

            # Find new tracks
            new_tracks = []
            for track_path in tracks:
                # Check both absolute and relative paths
                rel_path = os.path.relpath(track_path)
                if rel_path not in existing_paths and track_path not in existing_paths:
                    new_tracks.append(track_path)

            return new_tracks

        finally:
            conn.close()

    def get_settings(self) -> Dict[str, str]:
        """Get all settings from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT key, value FROM settings")
            return dict(cursor.fetchall())

        finally:
            conn.close()

    def update_setting(self, key: str, value: str):
        """Update a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (key, value),
            )
            conn.commit()

        finally:
            conn.close()

    def is_first_run(self) -> bool:
        """Check if this is the first run."""
        settings = self.get_settings()
        return settings.get("first_run_complete", "false") == "false"

    def mark_first_run_complete(self):
        """Mark that first run setup is complete."""
        self.update_setting("first_run_complete", "true")

    def get_library_stats(self) -> Dict:
        """Get statistics about the music library."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            stats = {}

            # Total tracks
            cursor.execute("SELECT COUNT(*) FROM tracks")
            stats["total_tracks"] = cursor.fetchone()[0]

            # Analyzed tracks
            cursor.execute(
                "SELECT COUNT(*) FROM tracks WHERE analysis_status = 'completed'"
            )
            stats["analyzed_tracks"] = cursor.fetchone()[0]

            # Pending analysis
            cursor.execute(
                "SELECT COUNT(*) FROM analysis_queue WHERE status = 'pending'"
            )
            stats["pending_analysis"] = cursor.fetchone()[0]

            # Failed analysis
            cursor.execute(
                "SELECT COUNT(*) FROM analysis_queue WHERE status = 'failed'"
            )
            stats["failed_analysis"] = cursor.fetchone()[0]

            # Music folders
            cursor.execute("SELECT COUNT(*) FROM music_folders WHERE enabled = 1")
            stats["active_folders"] = cursor.fetchone()[0]

            # Total size
            cursor.execute("SELECT SUM(file_size) FROM tracks")
            total_size = cursor.fetchone()[0] or 0
            stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)

            return stats

        finally:
            conn.close()

    def get_tracks_needing_metadata(self, limit: Optional[int] = None) -> List[str]:
        """Get tracks that are missing essential metadata."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get tracks missing critical metadata
            # Consider a track needs metadata if it's missing:
            # - Title AND Artist (basic metadata)
            # - OR has no BPM (needed for DJ features)
            # - OR has never been analyzed (analysis_version is NULL or < 2)
            query = """
                SELECT filepath FROM tracks 
                WHERE (
                    (title IS NULL AND artist IS NULL) OR
                    bpm IS NULL OR
                    analysis_version IS NULL OR
                    analysis_version < 2
                )
                AND (analysis_status IS NULL OR analysis_status != 'failed')
                ORDER BY filepath
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

        finally:
            conn.close()

    def get_tracks_missing_enhanced_metadata(
        self, limit: Optional[int] = None
    ) -> List[str]:
        """Get tracks that have basic metadata but are missing enhanced features."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get tracks that have basic metadata but missing enhanced features
            query = """
                SELECT filepath FROM tracks 
                WHERE (
                    title IS NOT NULL AND 
                    artist IS NOT NULL AND
                    bpm IS NOT NULL
                ) AND (
                    key IS NULL OR
                    key_scale IS NULL OR
                    energy_profile IS NULL OR
                    structure IS NULL
                )
                AND (analysis_status IS NULL OR analysis_status != 'failed')
                ORDER BY filepath
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]

        finally:
            conn.close()

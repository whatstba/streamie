"""File system watcher for automatic music file detection."""

import os
import asyncio
import logging
from typing import Set
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

logger = logging.getLogger(__name__)


class MusicFileHandler(FileSystemEventHandler):
    """Handles file system events for music files."""

    AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".m4p"}

    def __init__(self, analysis_queue, db_path: str):
        self.analysis_queue = analysis_queue
        self.db_path = db_path
        self.processing_files: Set[str] = set()

    def is_audio_file(self, path: str) -> bool:
        """Check if the file is an audio file."""
        return any(path.lower().endswith(ext) for ext in self.AUDIO_EXTENSIONS)

    def should_process(self, path: str) -> bool:
        """Check if the file should be processed."""
        if not self.is_audio_file(path):
            return False

        # Skip temporary files
        basename = os.path.basename(path)
        if basename.startswith(".") or basename.startswith("~"):
            return False

        # Skip if already processing
        if path in self.processing_files:
            return False

        return True

    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events."""
        if event.is_directory:
            return

        if self.should_process(event.src_path):
            logger.info(f"New music file detected: {event.src_path}")
            self.processing_files.add(event.src_path)

            # Queue for analysis with high priority
            asyncio.create_task(self._queue_file(event.src_path, priority=2))

    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return

        if self.should_process(event.src_path):
            logger.info(f"Music file modified: {event.src_path}")

            # Mark existing analysis as outdated
            asyncio.create_task(self._mark_outdated(event.src_path))

            # Re-queue for analysis
            asyncio.create_task(self._queue_file(event.src_path, priority=3))

    def on_moved(self, event: FileMovedEvent):
        """Handle file move events."""
        if event.is_directory:
            return

        # Handle source path removal
        if self.is_audio_file(event.src_path):
            logger.info(f"Music file moved from: {event.src_path}")
            asyncio.create_task(self._remove_from_db(event.src_path))

        # Handle destination path addition
        if self.should_process(event.dest_path):
            logger.info(f"Music file moved to: {event.dest_path}")
            asyncio.create_task(self._queue_file(event.dest_path, priority=3))

    async def _queue_file(self, filepath: str, priority: int):
        """Queue a file for analysis."""
        try:
            await self.analysis_queue.add_track(filepath, priority)
        except Exception as e:
            logger.error(f"Error queueing file {filepath}: {e}")
        finally:
            self.processing_files.discard(filepath)

    async def _mark_outdated(self, filepath: str):
        """Mark existing analysis as outdated."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            rel_path = os.path.relpath(filepath)
            cursor.execute(
                """
                UPDATE tracks 
                SET analysis_status = 'outdated' 
                WHERE filepath = ?
            """,
                (rel_path,),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error marking file as outdated {filepath}: {e}")
        finally:
            conn.close()

    async def _remove_from_db(self, filepath: str):
        """Remove a file from the database."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            rel_path = os.path.relpath(filepath)
            cursor.execute("DELETE FROM tracks WHERE filepath = ?", (rel_path,))
            cursor.execute("DELETE FROM analysis_queue WHERE filepath = ?", (filepath,))
            conn.commit()
            logger.info(f"Removed from database: {filepath}")
        except Exception as e:
            logger.error(f"Error removing file from database {filepath}: {e}")
        finally:
            conn.close()


class MusicFolderWatcher:
    """Watches music folders for changes."""

    def __init__(self, analysis_queue, db_path: str):
        self.analysis_queue = analysis_queue
        self.db_path = db_path
        self.observer = Observer()
        self.handler = MusicFileHandler(analysis_queue, db_path)
        self.watched_paths: Set[str] = set()

    def start(self):
        """Start the file system observer."""
        self.observer.start()
        logger.info("Music folder watcher started")

    def stop(self):
        """Stop the file system observer."""
        self.observer.stop()
        self.observer.join()
        logger.info("Music folder watcher stopped")

    def add_folder(self, folder_path: str):
        """Add a folder to watch."""
        if folder_path in self.watched_paths:
            return

        try:
            self.observer.schedule(self.handler, folder_path, recursive=True)
            self.watched_paths.add(folder_path)
            logger.info(f"Now watching folder: {folder_path}")
        except Exception as e:
            logger.error(f"Error watching folder {folder_path}: {e}")

    def remove_folder(self, folder_path: str):
        """Remove a folder from watching."""
        if folder_path not in self.watched_paths:
            return

        # Note: watchdog doesn't have a direct way to unschedule a path
        # We'd need to stop and restart the observer with new paths
        # For now, just track it
        self.watched_paths.discard(folder_path)
        logger.info(f"Removed from watch: {folder_path}")

    def update_watched_folders(self, folder_paths: Set[str]):
        """Update the list of watched folders."""
        # This is a simplified implementation
        # In production, you'd want to properly handle adding/removing watches
        new_paths = folder_paths - self.watched_paths
        removed_paths = self.watched_paths - folder_paths

        for path in new_paths:
            self.add_folder(path)

        for path in removed_paths:
            self.remove_folder(path)

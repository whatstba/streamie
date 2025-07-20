"""Tests for music library management features."""

import pytest
import os
import tempfile
import shutil
import sqlite3
import asyncio
from unittest.mock import Mock, AsyncMock

from utils.music_library import MusicLibraryManager
from utils.analysis_queue import AnalysisQueue
from utils.file_watcher import MusicFolderWatcher, MusicFileHandler


class TestMusicLibraryManager:
    """Test music library management functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Initialize schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS music_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                auto_scan BOOLEAN DEFAULT 1,
                last_scan TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT UNIQUE NOT NULL,
                duration REAL,
                title TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                year TEXT,
                has_artwork BOOLEAN DEFAULT 0,
                bpm REAL,
                beat_times TEXT,
                energy_level REAL,
                analysis_status TEXT DEFAULT 'pending',
                file_size INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS analysis_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def music_library(self, temp_db):
        """Create a MusicLibraryManager instance."""
        return MusicLibraryManager(temp_db)

    @pytest.fixture
    def temp_music_folder(self):
        """Create a temporary music folder."""
        folder = tempfile.mkdtemp()

        # Create some test files
        test_files = ["test1.mp3", "test2.mp3", "test3.wav"]
        for filename in test_files:
            filepath = os.path.join(folder, filename)
            with open(filepath, "wb") as f:
                f.write(b"fake audio data")

        yield folder

        # Cleanup
        shutil.rmtree(folder)

    def test_add_music_folder(self, music_library, temp_music_folder):
        """Test adding a music folder."""
        result = music_library.add_music_folder(temp_music_folder)

        assert result["status"] == "added"
        assert result["path"] == temp_music_folder
        assert result["enabled"] is True
        assert result["auto_scan"] is True

        # Verify in database
        folders = music_library.get_music_folders()
        assert len(folders) == 1
        assert folders[0]["path"] == temp_music_folder
        assert folders[0]["exists"] is True

    def test_add_nonexistent_folder(self, music_library):
        """Test adding a non-existent folder."""
        with pytest.raises(ValueError, match="does not exist"):
            music_library.add_music_folder("/path/that/does/not/exist")

    def test_remove_music_folder(self, music_library, temp_music_folder):
        """Test removing a music folder."""
        # First add it
        music_library.add_music_folder(temp_music_folder)

        # Then remove it
        success = music_library.remove_music_folder(temp_music_folder)
        assert success is True

        # Verify it's gone
        folders = music_library.get_music_folders()
        assert len(folders) == 0

    def test_scan_folder_for_tracks(self, music_library, temp_music_folder):
        """Test scanning a folder for audio files."""
        tracks = music_library.scan_folder_for_tracks(temp_music_folder)

        assert len(tracks) == 3
        assert any("test1.mp3" in track for track in tracks)
        assert any("test2.mp3" in track for track in tracks)
        assert any("test3.wav" in track for track in tracks)

    def test_get_new_tracks(self, music_library, temp_music_folder):
        """Test finding new tracks not in database."""
        # Initially all tracks should be new
        new_tracks = music_library.get_new_tracks(temp_music_folder)
        assert len(new_tracks) == 3

        # Add one track to database
        conn = sqlite3.connect(music_library.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tracks (filename, filepath, duration)
            VALUES ('test1.mp3', ?, 120.0)
        """,
            (os.path.relpath(os.path.join(temp_music_folder, "test1.mp3")),),
        )
        conn.commit()
        conn.close()

        # Now only 2 should be new
        new_tracks = music_library.get_new_tracks(temp_music_folder)
        assert len(new_tracks) == 2

    def test_settings_management(self, music_library):
        """Test settings get/update."""
        # Default should be empty
        settings = music_library.get_settings()
        assert isinstance(settings, dict)

        # Update a setting
        music_library.update_setting("auto_analyze", "true")
        music_library.update_setting("watch_folders", "false")

        # Verify
        settings = music_library.get_settings()
        assert settings["auto_analyze"] == "true"
        assert settings["watch_folders"] == "false"

    def test_first_run_detection(self, music_library):
        """Test first run detection."""
        assert music_library.is_first_run() is True

        music_library.mark_first_run_complete()
        assert music_library.is_first_run() is False

    def test_library_stats(self, music_library, temp_db):
        """Test library statistics."""
        # Add some test data
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Add tracks (file_size column doesn't exist in our schema)
        cursor.executemany(
            """
            INSERT INTO tracks (filename, filepath, duration, analysis_status)
            VALUES (?, ?, ?, ?)
        """,
            [
                ("track1.mp3", "path1", 180.0, "completed"),
                ("track2.mp3", "path2", 240.0, "completed"),
                ("track3.mp3", "path3", 200.0, "pending"),
            ],
        )

        # Add folder
        cursor.execute("""
            INSERT INTO music_folders (path, enabled)
            VALUES ('/music', 1)
        """)

        conn.commit()
        conn.close()

        stats = music_library.get_library_stats()

        assert stats["total_tracks"] == 3
        assert stats["analyzed_tracks"] == 2
        assert stats["pending_analysis"] == 0  # analysis_queue table not populated
        assert stats["active_folders"] == 1
        assert stats["total_size_mb"] == 0.0  # file_size not in our test data


class TestAnalysisQueue:
    """Test analysis queue functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Initialize schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS analysis_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                analysis_status TEXT DEFAULT 'pending'
            );
        """)
        conn.commit()
        conn.close()

        yield db_path

        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def analysis_queue(self, temp_db):
        """Create an AnalysisQueue instance."""
        return AnalysisQueue(temp_db, max_workers=2)

    @pytest.mark.asyncio
    async def test_add_track(self, analysis_queue):
        """Test adding a track to the queue."""
        job_id = await analysis_queue.add_track("/path/to/track.mp3", priority=3)

        assert job_id > 0

        # Verify in database
        conn = sqlite3.connect(analysis_queue.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM analysis_queue WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "/path/to/track.mp3"  # filepath
        assert row[2] == 3  # priority
        assert row[3] == "pending"  # status

    @pytest.mark.asyncio
    async def test_get_status(self, analysis_queue, temp_db):
        """Test getting queue status."""
        # Add some test jobs
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO analysis_queue (filepath, status)
            VALUES (?, ?)
        """,
            [
                ("track1.mp3", "pending"),
                ("track2.mp3", "pending"),
                ("track3.mp3", "processing"),
                ("track4.mp3", "completed"),
                ("track5.mp3", "failed"),
            ],
        )
        conn.commit()
        conn.close()

        status = await analysis_queue.get_status()

        assert status["pending"] == 2
        assert status["processing"] == 1
        assert status["completed"] == 1
        assert status["failed"] == 1
        assert status["total"] == 5
        assert status["running"] is False

    @pytest.mark.asyncio
    async def test_worker_lifecycle(self, analysis_queue):
        """Test starting and stopping workers."""
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze_file = AsyncMock(return_value=True)

        # Start queue
        await analysis_queue.start(mock_analyzer)
        assert analysis_queue.running is True
        assert len(analysis_queue.workers) == 2

        # Stop queue
        await analysis_queue.stop()
        assert analysis_queue.running is False
        assert len(analysis_queue.workers) == 0


class TestFileWatcher:
    """Test file system watcher functionality."""

    @pytest.fixture
    def mock_queue(self):
        """Create a mock analysis queue."""
        queue = Mock()
        queue.add_track = AsyncMock()
        return queue

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def file_handler(self, mock_queue, temp_db):
        """Create a MusicFileHandler instance."""
        return MusicFileHandler(mock_queue, temp_db)

    def test_is_audio_file(self, file_handler):
        """Test audio file detection."""
        assert file_handler.is_audio_file("song.mp3") is True
        assert file_handler.is_audio_file("track.M4A") is True  # Case insensitive
        assert file_handler.is_audio_file("audio.wav") is True
        assert file_handler.is_audio_file("document.pdf") is False
        assert file_handler.is_audio_file("image.jpg") is False

    def test_should_process(self, file_handler):
        """Test file processing logic."""
        # Should process audio files
        assert file_handler.should_process("song.mp3") is True

        # Should skip non-audio files
        assert file_handler.should_process("readme.txt") is False

        # Should skip hidden files
        assert file_handler.should_process(".hidden.mp3") is False

        # Should skip temp files
        assert file_handler.should_process("~temp.mp3") is False

        # Should skip already processing files
        file_handler.processing_files.add("processing.mp3")
        assert file_handler.should_process("processing.mp3") is False

    @pytest.mark.asyncio
    async def test_on_created(self, file_handler, mock_queue):
        """Test handling file creation events."""
        # Mock event
        event = Mock()
        event.is_directory = False
        event.src_path = "/music/new_song.mp3"

        # Handle event
        file_handler.on_created(event)

        # Allow async task to run
        await asyncio.sleep(0.1)

        # Verify file was queued
        mock_queue.add_track.assert_called_with("/music/new_song.mp3", 2)

    def test_folder_watcher_lifecycle(self, mock_queue, temp_db):
        """Test starting and stopping the folder watcher."""
        watcher = MusicFolderWatcher(mock_queue, temp_db)

        # Start watcher
        watcher.start()
        assert watcher.observer.is_alive() is True

        # Add folder
        with tempfile.TemporaryDirectory() as temp_dir:
            watcher.add_folder(temp_dir)
            assert temp_dir in watcher.watched_paths

        # Stop watcher
        watcher.stop()
        assert watcher.observer.is_alive() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Integration tests for database operations.
"""

import pytest
from unittest.mock import patch
import sqlite3
import json

from tests.fixtures.mock_data import MOCK_TRACKS_DB, MOCK_BEAT_TRACK_RESPONSE
from tests.utils.helpers import create_test_db_track


class TestDatabaseOperations:
    """Test database operations and SQLite adapter."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_store_track_analysis(self, test_client, mock_db, mock_audio_file):
        """Test storing track analysis results in database."""

        # Create test data
        track_data = create_test_db_track("test_track.mp3", bpm=128.0, energy=0.75)

        # Use the test database
        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            # Create a real SQLite connection for testing
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn

            # Insert track
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tracks (
                    filename, filepath, title, artist, album, 
                    duration, bpm, energy, genre, year, has_artwork
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    track_data["filename"],
                    track_data["filepath"],
                    track_data["title"],
                    track_data["artist"],
                    track_data["album"],
                    track_data["duration"],
                    track_data["bpm"],
                    track_data["energy"],
                    track_data["genre"],
                    track_data["year"],
                    track_data["has_artwork"],
                ),
            )
            conn.commit()

            # Query back
            cursor.execute(
                "SELECT * FROM tracks WHERE filename = ?", (track_data["filename"],)
            )
            result = cursor.fetchone()

            assert result is not None
            # Verify data integrity
            assert result[1] == track_data["filename"]  # filename
            assert result[6] == track_data["duration"]  # duration
            assert result[7] == track_data["bpm"]  # bpm

            conn.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mongodb_adapter_compatibility(self, test_client, mock_db):
        """Test SQLite adapter works with MongoDB-style queries."""
        from utils.sqlite_db import get_tracks_by_criteria, insert_track

        # Insert test tracks
        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn

            # Insert multiple tracks
            for track in MOCK_TRACKS_DB:
                insert_track(track)

            # Test MongoDB-style queries
            # Find by BPM range
            results = get_tracks_by_criteria({"bpm": {"$gte": 124, "$lte": 126}})
            assert len(results) == 2
            assert all(124 <= t["bpm"] <= 126 for t in results)

            # Find by genre
            results = get_tracks_by_criteria({"genre": "Progressive House"})
            assert len(results) == 3

            # Complex query
            results = get_tracks_by_criteria(
                {
                    "bpm": {"$gte": 125},
                    "energy": {"$gte": 0.7},
                    "mood_happy": {"$gte": 0.8},
                }
            )
            assert len(results) >= 1

            conn.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_beat_times_storage(self, test_client, mock_db):
        """Test storing and retrieving beat timing data."""

        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn

            # Insert track
            track = create_test_db_track("beat_test.mp3")
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tracks (filename, filepath, title, bpm)
                VALUES (?, ?, ?, ?)
            """,
                (track["filename"], track["filepath"], track["title"], track["bpm"]),
            )
            track_id = cursor.lastrowid

            # Store beat times
            beat_times = MOCK_BEAT_TRACK_RESPONSE["beat_times"]
            beat_times_json = json.dumps(beat_times)

            cursor.execute(
                """
                UPDATE tracks SET beat_times = ? WHERE id = ?
            """,
                (beat_times_json, track_id),
            )
            conn.commit()

            # Retrieve and verify
            cursor.execute("SELECT beat_times FROM tracks WHERE id = ?", (track_id,))
            result = cursor.fetchone()

            assert result[0] is not None
            retrieved_beats = json.loads(result[0])
            assert retrieved_beats == beat_times

            conn.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_track_search_performance(self, test_client, mock_db):
        """Test track search with various criteria."""
        from utils.sqlite_db import search_tracks

        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn

            # Insert many tracks for testing
            cursor = conn.cursor()
            for i in range(100):
                track = create_test_db_track(
                    f"track_{i}.mp3",
                    bpm=120 + (i % 20),
                    energy=0.5 + (i % 50) / 100,
                    mood_happy=i / 100,
                )

                cursor.execute(
                    """
                    INSERT INTO tracks (
                        filename, filepath, title, artist, 
                        bpm, energy, mood_happy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        track["filename"],
                        track["filepath"],
                        track["title"],
                        track["artist"],
                        track["bpm"],
                        track["energy"],
                        track["mood_happy"],
                    ),
                )
            conn.commit()

            # Test various searches
            with patch("utils.sqlite_db.search_tracks") as mock_search:
                # Mock the search function to use our test connection
                def search_impl(criteria):
                    cursor = conn.cursor()
                    query = "SELECT * FROM tracks WHERE 1=1"
                    params = []

                    if "bpm_min" in criteria:
                        query += " AND bpm >= ?"
                        params.append(criteria["bpm_min"])
                    if "bpm_max" in criteria:
                        query += " AND bpm <= ?"
                        params.append(criteria["bpm_max"])
                    if "energy_min" in criteria:
                        query += " AND energy >= ?"
                        params.append(criteria["energy_min"])

                    cursor.execute(query, params)
                    return cursor.fetchall()

                mock_search.side_effect = search_impl

                # Search by BPM range
                results = search_tracks({"bpm_min": 125, "bpm_max": 130})
                assert len(results) > 0

                # Search by energy
                results = search_tracks({"energy_min": 0.8})
                assert len(results) > 0

            conn.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_migrations(self, test_client, mock_db):
        """Test database schema migrations and updates."""

        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn
            cursor = conn.cursor()

            # Check all required columns exist
            cursor.execute("PRAGMA table_info(tracks)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Verify essential columns
            required_columns = [
                "id",
                "filename",
                "filepath",
                "title",
                "artist",
                "bpm",
                "energy",
                "duration",
                "beat_times",
                "mood_happy",
                "mood_sad",
                "mood_aggressive",
            ]

            for col in required_columns:
                assert col in column_names, f"Missing column: {col}"

            conn.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_transaction_handling(self, test_client, mock_db):
        """Test database transaction handling and rollback."""

        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn

            try:
                # Start transaction
                cursor = conn.cursor()
                cursor.execute("BEGIN")

                # Insert track
                cursor.execute(
                    """
                    INSERT INTO tracks (filename, filepath, title)
                    VALUES (?, ?, ?)
                """,
                    (
                        "transaction_test.mp3",
                        "/test/transaction_test.mp3",
                        "Transaction Test",
                    ),
                )

                # Simulate error
                raise Exception("Simulated error")

                cursor.execute("COMMIT")
            except:
                # Rollback on error
                cursor.execute("ROLLBACK")

            # Verify track was not inserted
            cursor.execute(
                "SELECT * FROM tracks WHERE filename = ?", ("transaction_test.mp3",)
            )
            result = cursor.fetchone()
            assert result is None

            conn.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_duplicate_track_handling(self, test_client, mock_db):
        """Test handling of duplicate track entries."""
        from utils.sqlite_db import insert_or_update_track

        with patch("utils.sqlite_db.get_sqlite_db") as mock_get_db:
            conn = sqlite3.connect(mock_db)
            mock_get_db.return_value = conn
            cursor = conn.cursor()

            # Create unique index on filepath
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_filepath 
                ON tracks(filepath)
            """)

            # Insert track
            track = create_test_db_track("duplicate_test.mp3", bpm=120)
            cursor.execute(
                """
                INSERT INTO tracks (filename, filepath, title, bpm)
                VALUES (?, ?, ?, ?)
            """,
                (track["filename"], track["filepath"], track["title"], track["bpm"]),
            )
            conn.commit()

            # Try to insert duplicate - should update instead
            track["bpm"] = 125  # Changed BPM

            with patch("utils.sqlite_db.insert_or_update_track") as mock_insert_update:

                def insert_or_update_impl(track_data):
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO tracks (filename, filepath, title, bpm)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            track_data["filename"],
                            track_data["filepath"],
                            track_data["title"],
                            track_data["bpm"],
                        ),
                    )
                    conn.commit()

                mock_insert_update.side_effect = insert_or_update_impl
                insert_or_update_track(track)

            # Verify update
            cursor.execute(
                "SELECT bpm FROM tracks WHERE filepath = ?", (track["filepath"],)
            )
            result = cursor.fetchone()
            assert result[0] == 125  # BPM should be updated

            # Verify no duplicates
            cursor.execute(
                "SELECT COUNT(*) FROM tracks WHERE filepath = ?", (track["filepath"],)
            )
            count = cursor.fetchone()[0]
            assert count == 1

            conn.close()

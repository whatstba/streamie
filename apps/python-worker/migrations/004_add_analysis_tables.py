"""
Migration to add analysis task tracking tables.
"""

import sqlite3
import os
from datetime import datetime


def migrate():
    """Add tables for analysis task management and caching."""

    # Get database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dj_system.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create analysis_tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_tasks (
                task_id TEXT PRIMARY KEY,
                filepath TEXT NOT NULL,
                priority INTEGER DEFAULT 2,
                deck_id TEXT,
                analysis_type TEXT DEFAULT 'full',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT,
                results TEXT,  -- JSON
                FOREIGN KEY (deck_id) REFERENCES decks(id)
            )
        """)

        # Create analysis_cache table for quick lookups
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_cache (
                filepath TEXT PRIMARY KEY,
                bpm REAL,
                key TEXT,
                camelot_key TEXT,
                energy_level REAL,
                energy_profile TEXT,
                spectral_centroid REAL,
                danceability REAL,
                beat_times TEXT,  -- JSON array
                hot_cues TEXT,    -- JSON array
                structure TEXT,   -- JSON object
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_version TEXT DEFAULT '1.0'
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status 
            ON analysis_tasks(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_tasks_priority 
            ON analysis_tasks(priority, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_cache_updated 
            ON analysis_cache(last_updated)
        """)

        # Add analysis fields to tracks table if not exists
        # Check if columns exist first
        cursor.execute("PRAGMA table_info(tracks)")
        columns = [col[1] for col in cursor.fetchall()]

        new_columns = [
            ("spectral_centroid", "REAL"),
            ("danceability", "REAL"),
            ("analysis_version", "TEXT DEFAULT '1.0'"),
            ("analyzed_at", "TIMESTAMP"),
            ("analysis_status", "TEXT DEFAULT 'pending'"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                cursor.execute(f"""
                    ALTER TABLE tracks ADD COLUMN {col_name} {col_type}
                """)
                print(f"Added column {col_name} to tracks table")

        # Create transition_analysis table for caching transition compatibility
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transition_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_a_filepath TEXT NOT NULL,
                track_b_filepath TEXT NOT NULL,
                compatibility_overall REAL,
                compatibility_bpm REAL,
                compatibility_key REAL,
                compatibility_energy REAL,
                compatibility_genre REAL,
                transition_points TEXT,  -- JSON array
                recommended_effects TEXT,  -- JSON array
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(track_a_filepath, track_b_filepath)
            )
        """)

        conn.commit()
        print("✅ Analysis tables created successfully")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

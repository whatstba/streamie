"""Database migration system for Streamie."""

import os
import sqlite3
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migrations for the Streamie music database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = os.path.join(
            os.path.dirname(__file__), "..", "migrations"
        )

    def ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT filename FROM migrations ORDER BY applied_at")
        applied = [row[0] for row in cursor.fetchall()]

        conn.close()
        return applied

    def get_pending_migrations(self) -> List[Tuple[str, str]]:
        """Get list of migrations that need to be applied."""
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            return []

        applied = self.get_applied_migrations()
        pending = []

        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith(".sql") and filename not in applied:
                filepath = os.path.join(self.migrations_dir, filename)
                with open(filepath, "r") as f:
                    content = f.read()
                pending.append((filename, content))

        return pending

    def column_exists(self, cursor, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns

    def apply_migration(self, filename: str, content: str):
        """Apply a single migration."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Special handling for the music folders migration
            if filename == "add_music_folders_and_metadata.sql":
                self._apply_music_folders_migration(cursor)
            else:
                # Execute the migration normally
                cursor.executescript(content)

            # Record that it was applied
            cursor.execute("INSERT INTO migrations (filename) VALUES (?)", (filename,))

            conn.commit()
            logger.info(f"Applied migration: {filename}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to apply migration {filename}: {e}")
            raise

        finally:
            conn.close()

    def _apply_music_folders_migration(self, cursor):
        """Apply the music folders migration with column existence checking."""
        # Create music_folders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                last_scan TIMESTAMP,
                auto_scan BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add columns to tracks table if they don't exist
        columns_to_add = [
            ("analysis_status", 'TEXT DEFAULT "pending"'),
            ("analysis_error", "TEXT"),
            ("analysis_version", "INTEGER DEFAULT 2"),
            ("hot_cues", "TEXT"),
            ("auto_cues", "TEXT"),
            ("has_serato_data", "BOOLEAN DEFAULT 0"),
            ("key", "TEXT"),
            ("key_scale", "TEXT"),
            ("key_confidence", "REAL"),
            ("camelot_key", "TEXT"),
            ("intro_start", "REAL"),
            ("intro_end", "REAL"),
            ("outro_start", "REAL"),
            ("outro_end", "REAL"),
            ("phrase_length", "INTEGER"),
            ("downbeats", "TEXT"),
            ("energy_curve", "TEXT"),
            ("energy_profile", "TEXT"),
            ("structure", "TEXT"),
            ("spectral_centroid", "REAL"),
            ("genre_detailed", "TEXT"),
        ]

        for column_name, column_def in columns_to_add:
            if not self.column_exists(cursor, "tracks", column_name):
                try:
                    cursor.execute(
                        f"ALTER TABLE tracks ADD COLUMN {column_name} {column_def}"
                    )
                    logger.info(f"Added column {column_name} to tracks table")
                except Exception as e:
                    logger.warning(f"Could not add column {column_name}: {e}")

        # Create analysis_queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                UNIQUE(filepath)
            )
        """)

        # Create settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert default settings
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES 
                ('auto_analyze', 'true'),
                ('analysis_threads', '4'),
                ('watch_folders', 'true'),
                ('first_run_complete', 'false')
        """)

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_analysis_status ON tracks(analysis_status)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_queue_status ON analysis_queue(status)",
            "CREATE INDEX IF NOT EXISTS idx_key ON tracks(key)",
            "CREATE INDEX IF NOT EXISTS idx_camelot ON tracks(camelot_key)",
        ]

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")

        # Update analysis_version for existing tracks
        if self.column_exists(cursor, "tracks", "analysis_version"):
            cursor.execute(
                "UPDATE tracks SET analysis_version = 2 WHERE analysis_version < 2 OR analysis_version IS NULL"
            )

    def run_migrations(self):
        """Run all pending migrations."""
        self.ensure_migrations_table()

        pending = self.get_pending_migrations()
        if not pending:
            logger.info("No pending migrations")
            return

        logger.info(f"Found {len(pending)} pending migrations")

        for filename, content in pending:
            self.apply_migration(filename, content)

        logger.info("All migrations completed successfully")


def run_migrations(db_path: str):
    """Convenience function to run migrations."""
    runner = MigrationRunner(db_path)
    runner.run_migrations()

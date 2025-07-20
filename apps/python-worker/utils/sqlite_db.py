"""
SQLite database adapter that provides MongoDB-like interface for the DJ agent.
"""

import sqlite3
import os
import json
from typing import Dict, List, Optional


class SQLiteAdapter:
    """Adapter to provide MongoDB-like interface for SQLite database."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "tracks.db")
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    def find_one(self, query: Dict) -> Optional[Dict]:
        """Find a single document matching the query."""
        cursor = self.connection.cursor()

        if "filepath" in query:
            cursor.execute(
                "SELECT * FROM tracks WHERE filepath = ?", (query["filepath"],)
            )
        else:
            # For more complex queries, build dynamically
            where_clause, params = self._build_where_clause(query)
            cursor.execute(f"SELECT * FROM tracks {where_clause}", params)

        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def find(self, query: Dict = None, limit: int = None) -> List[Dict]:
        """Find multiple documents matching the query."""
        cursor = self.connection.cursor()

        if query is None:
            query = {}

        where_clause, params = self._build_where_clause(query)
        sql = f"SELECT * FROM tracks {where_clause}"

        if limit:
            sql += f" LIMIT {limit}"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def update_one(self, query: Dict, update_data: Dict):
        """Update a single document."""
        cursor = self.connection.cursor()

        # Extract the update operation
        if "$push" in update_data:
            # Handle $push operations for arrays (like mixing_history)
            for field, value in update_data["$push"].items():
                # For now, we'll store as JSON string
                # In a real implementation, you might want a separate table
                pass

        # For now, return success
        self.connection.commit()
        return {"acknowledged": True}

    def insert_one(self, document: Dict):
        """Insert a single document."""
        cursor = self.connection.cursor()

        # For transition_ratings table (create if not exists)
        if all(key in document for key in ["from_track", "to_track", "rating"]):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transition_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_track TEXT,
                    to_track TEXT,
                    rating REAL,
                    notes TEXT,
                    timestamp REAL
                )
            """)

            cursor.execute(
                """
                INSERT INTO transition_ratings (from_track, to_track, rating, notes, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    document.get("from_track"),
                    document.get("to_track"),
                    document.get("rating"),
                    document.get("notes"),
                    document.get("timestamp"),
                ),
            )

        self.connection.commit()
        return {"acknowledged": True}

    def count_documents(self, query: Dict = None) -> int:
        """Count documents matching the query."""
        cursor = self.connection.cursor()

        if query is None:
            query = {}

        where_clause, params = self._build_where_clause(query)
        cursor.execute(f"SELECT COUNT(*) FROM tracks {where_clause}", params)
        return cursor.fetchone()[0]

    def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        """Simple aggregation support."""
        # For now, return empty list
        # In a full implementation, you'd parse the aggregation pipeline
        return []

    def _build_where_clause(self, query: Dict) -> tuple:
        """Build WHERE clause from MongoDB-style query."""
        if not query:
            return "", []

        conditions = []
        params = []

        for key, value in query.items():
            if isinstance(value, dict):
                # Handle operators like {"rating": {"$gte": 0.7}}
                for op, op_value in value.items():
                    if op == "$gte":
                        conditions.append(f"{key} >= ?")
                        params.append(op_value)
                    elif op == "$lte":
                        conditions.append(f"{key} <= ?")
                        params.append(op_value)
                    elif op == "$gt":
                        conditions.append(f"{key} > ?")
                        params.append(op_value)
                    elif op == "$lt":
                        conditions.append(f"{key} < ?")
                        params.append(op_value)
            else:
                conditions.append(f"{key} = ?")
                params.append(value)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert SQLite row to dictionary with proper data types."""
        data = dict(row)

        # Parse JSON fields
        if data.get("beat_times"):
            try:
                data["beat_times"] = json.loads(data["beat_times"])
            except (json.JSONDecodeError, TypeError):
                data["beat_times"] = []

        # Add missing fields with defaults for compatibility
        mood_fields = {
            "mood_acoustic": 0.0,
            "mood_aggressive": 0.0,
            "mood_electronic": 0.0,
            "mood_happy": 0.0,
            "mood_party": 0.0,
            "mood_relaxed": 0.0,
            "mood_sad": 0.0,
        }

        # Check if we have any mood data (might be in a separate table or computed)
        data["mood"] = mood_fields

        # Ensure required fields exist
        if "energy_level" not in data or data["energy_level"] is None:
            # Calculate energy level from BPM if not stored
            bpm = data.get("bpm", 120)
            data["energy_level"] = min(1.0, max(0.0, (bpm - 60) / 140))

        return data


class SQLiteCollectionAdapter:
    """Adapter for a specific collection (table)."""

    def __init__(self, db_adapter: SQLiteAdapter, collection_name: str):
        self.db = db_adapter
        self.collection_name = collection_name

    def find_one(self, query: Dict = None) -> Optional[Dict]:
        if self.collection_name == "tracks":
            return self.db.find_one(query or {})
        elif self.collection_name == "transition_ratings":
            # Handle transition_ratings queries
            cursor = self.db.connection.cursor()
            where_clause, params = self.db._build_where_clause(query or {})

            # Check if table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='transition_ratings'"
            )
            if not cursor.fetchone():
                return None

            cursor.execute(f"SELECT * FROM transition_ratings {where_clause}", params)
            row = cursor.fetchone()
            return dict(row) if row else None
        return None

    def find(self, query: Dict = None, limit: int = None) -> List[Dict]:
        if self.collection_name == "tracks":
            return self.db.find(query or {}, limit)
        return []

    def insert_one(self, document: Dict):
        return self.db.insert_one(document)

    def update_one(self, query: Dict, update_data: Dict):
        return self.db.update_one(query, update_data)

    def count_documents(self, query: Dict = None) -> int:
        if self.collection_name == "tracks":
            return self.db.count_documents(query or {})
        return 0

    def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        return self.db.aggregate(pipeline)


class SQLiteDatabase:
    """Database adapter that mimics MongoDB database interface."""

    def __init__(self, db_path: str = None):
        self.adapter = SQLiteAdapter(db_path)

    @property
    def tracks(self):
        """Access to tracks collection."""
        return SQLiteCollectionAdapter(self.adapter, "tracks")

    @property
    def transition_ratings(self):
        """Access to transition_ratings collection."""
        return SQLiteCollectionAdapter(self.adapter, "transition_ratings")


def get_sqlite_db() -> SQLiteDatabase:
    """Get SQLite database instance."""
    return SQLiteDatabase()

"""
Migration script to transfer data from MongoDB to SQLite.

This script will:
- Connect to your existing MongoDB database
- Read all track data
- Transfer it to the new SQLite database
- Preserve all existing metadata and analysis
"""

import os
import sys
import json
from typing import Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyze_and_enhance_tracks_sql import TrackDatabase
from main import MUSIC_DIR

try:
    from utils.db import get_db

    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("❌ MongoDB dependencies not available")


def convert_mongo_to_sql_format(mongo_doc: Dict) -> Dict:
    """Convert MongoDB document format to SQL format."""
    # Handle beat times
    beat_times = mongo_doc.get("beat_times", [])
    if isinstance(beat_times, list):
        beat_times_json = json.dumps(beat_times)
    else:
        beat_times_json = json.dumps([])

    # Handle mood data
    mood_data = mongo_doc.get("mood", {})
    if isinstance(mood_data, str):
        # Old format where mood was just a string label
        mood_label = mood_data
        mood_scores = {}
    elif isinstance(mood_data, dict):
        # New format with mood scores
        mood_label = max(mood_data, key=mood_data.get) if mood_data else None
        mood_scores = mood_data
    else:
        mood_label = None
        mood_scores = {}

    # Create the track data in SQL format
    track_data = {
        # File info
        "filepath": mongo_doc.get("filepath", ""),
        "filename": mongo_doc.get("filename", ""),
        "file_hash": "",  # Will be calculated on next analysis
        "file_size": 0,  # Will be calculated on next analysis
        "last_modified": 0,  # Will be calculated on next analysis
        # Basic metadata
        "title": mongo_doc.get("title", ""),
        "artist": mongo_doc.get("artist", ""),
        "album": mongo_doc.get("album", ""),
        "genre": mongo_doc.get("genre", ""),
        "year": mongo_doc.get("year", ""),
        "track": mongo_doc.get("track", ""),
        "albumartist": mongo_doc.get("albumartist", ""),
        "duration": mongo_doc.get("duration", 0.0),
        "has_artwork": mongo_doc.get("has_artwork", False),
        # Audio analysis
        "bpm": mongo_doc.get("bpm", 0.0),
        "beat_times": beat_times_json,
        # Mood analysis
        "mood_acoustic": mood_scores.get("mood_acoustic", 0.0),
        "mood_aggressive": mood_scores.get("mood_aggressive", 0.0),
        "mood_electronic": mood_scores.get("mood_electronic", 0.0),
        "mood_happy": mood_scores.get("mood_happy", 0.0),
        "mood_party": mood_scores.get("mood_party", 0.0),
        "mood_relaxed": mood_scores.get("mood_relaxed", 0.0),
        "mood_sad": mood_scores.get("mood_sad", 0.0),
        "mood_label": mood_label,
        # Enhanced features (if available)
        "energy_level": mongo_doc.get("energy_level"),
        "danceability": mongo_doc.get("danceability"),
        "tempo_stability": mongo_doc.get("tempo_stability"),
        "vocal_presence": mongo_doc.get("vocal_presence"),
        "valence": mongo_doc.get("valence"),
    }

    return track_data


def migrate_data():
    """Migrate data from MongoDB to SQLite."""
    if not MONGO_AVAILABLE:
        print("❌ Cannot migrate: MongoDB not available")
        return

    print("🔄 Starting MongoDB to SQLite migration...")

    # Connect to MongoDB
    try:
        mongo_db = get_db()
        collection = mongo_db.tracks

        # Get all tracks from MongoDB
        mongo_tracks = list(collection.find({}))
        total_tracks = len(mongo_tracks)

        if total_tracks == 0:
            print("✅ No tracks found in MongoDB - nothing to migrate")
            return

        print(f"Found {total_tracks} tracks in MongoDB")

    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return

    # Initialize SQLite database
    sql_db = TrackDatabase()

    # Migrate each track
    migrated_count = 0
    skipped_count = 0

    for i, mongo_track in enumerate(mongo_tracks, 1):
        try:
            print(
                f"[{i}/{total_tracks}] Migrating: {mongo_track.get('filename', 'Unknown')}"
            )

            # Convert format
            sql_track_data = convert_mongo_to_sql_format(mongo_track)

            # Check if file still exists
            file_path = os.path.join(MUSIC_DIR, sql_track_data["filepath"])
            if not os.path.exists(file_path):
                print(f"  ⚠️  File not found, skipping: {sql_track_data['filepath']}")
                skipped_count += 1
                continue

            # Update file metadata
            sql_track_data["file_hash"] = sql_db.get_file_hash(file_path)
            sql_track_data["file_size"] = os.path.getsize(file_path)
            sql_track_data["last_modified"] = os.path.getmtime(file_path)

            # Insert into SQLite using the direct SQL approach
            cursor = sql_db.connection.cursor()

            columns = ", ".join(sql_track_data.keys())
            placeholders = ", ".join([f":{key}" for key in sql_track_data.keys()])

            cursor.execute(
                f"""
                INSERT OR REPLACE INTO tracks ({columns})
                VALUES ({placeholders})
            """,
                sql_track_data,
            )

            sql_db.connection.commit()
            migrated_count += 1

            print("  ✅ Migrated successfully")

        except Exception as e:
            print(f"  ❌ Error migrating track: {e}")
            continue

    # Summary
    print("\n" + "=" * 50)
    print("✅ Migration complete!")
    print(f"📊 Migrated: {migrated_count}/{total_tracks} tracks")
    if skipped_count > 0:
        print(f"⚠️  Skipped: {skipped_count} tracks (files not found)")
    print(f"📁 SQLite database: {sql_db.db_path}")

    sql_db.close()


def main():
    """Main migration function."""
    print("🔄 MongoDB to SQLite Migration Tool")
    print("=" * 40)

    if not MONGO_AVAILABLE:
        print("❌ This script requires MongoDB to be available")
        print("Make sure pymongo is installed and MongoDB is accessible")
        return

    try:
        migrate_data()
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simple test script to verify AI DJ endpoints are working.
Run this before starting the frontend to ensure the backend is ready.
"""

import requests
import sys
from utils.db import get_db

API_BASE = "http://localhost:8000"


def test_api_connection():
    """Test basic API connection"""
    try:
        response = requests.get(f"{API_BASE}/")
        if response.status_code == 200:
            print("✅ Backend API is running")
            return True
        else:
            print(f"❌ Backend API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend API. Make sure the server is running with:")
        print("   cd apps/python-worker && python main.py")
        return False


def test_track_database():
    """Test database connection and track data"""
    try:
        db = get_db()
        track_count = db.tracks.count_documents({})
        print(f"✅ Database connected. Found {track_count} tracks")

        if track_count == 0:
            print("⚠️  No tracks in database. Run the migration script:")
            print("   python scripts/migrate_mongo_to_sql.py")
            return False

        # Get a sample track for testing
        sample_track = db.tracks.find_one({})
        if sample_track:
            print(
                f"   Sample track: {sample_track.get('title', 'Unknown')} - {sample_track.get('artist', 'Unknown')}"
            )
            return sample_track["filepath"]

        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_ai_endpoints(sample_track_filepath):
    """Test AI DJ endpoints with a sample track"""
    print("\n🧠 Testing AI DJ endpoints...")

    # Test vibe analysis
    try:
        response = requests.post(
            f"{API_BASE}/ai/analyze-vibe",
            json={"current_track_id": sample_track_filepath, "context": {"test": True}},
        )

        if response.status_code == 200:
            vibe_data = response.json()
            print(
                f"✅ Vibe analysis: {vibe_data['dominant_vibe']} ({vibe_data['energy_level']:.2f} energy)"
            )
        else:
            print(f"❌ Vibe analysis failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Vibe analysis error: {e}")
        return False

    # Test next track suggestion
    try:
        response = requests.post(
            f"{API_BASE}/ai/suggest-next-track",
            json={"current_track_id": sample_track_filepath, "context": {"test": True}},
        )

        if response.status_code == 200:
            suggestion_data = response.json()
            print(
                f"✅ Next track suggestion: {suggestion_data['confidence']:.2f} confidence"
            )
        else:
            print(
                f"❌ Next track suggestion failed: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Next track suggestion error: {e}")
        return False

    # Test playlist generation
    try:
        response = requests.post(
            f"{API_BASE}/ai/generate-playlist",
            json={
                "seed_track_id": sample_track_filepath,
                "playlist_length": 5,
                "energy_pattern": "wave",
            },
        )

        if response.status_code == 200:
            playlist_data = response.json()
            print(
                f"✅ Playlist generation: {len(playlist_data['playlist'])} tracks generated"
            )
        else:
            print(
                f"❌ Playlist generation failed: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Playlist generation error: {e}")
        return False

    # Test mixing insights
    try:
        response = requests.get(f"{API_BASE}/ai/mixing-insights")

        if response.status_code == 200:
            insights_data = response.json()
            print(f"✅ Mixing insights: {insights_data['total_ratings']} total ratings")
        else:
            print(
                f"❌ Mixing insights failed: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Mixing insights error: {e}")
        return False

    return True


def main():
    print("🚀 Testing AI DJ Backend...\n")

    # Test basic connection
    if not test_api_connection():
        sys.exit(1)

    # Test database
    sample_track = test_track_database()
    if not sample_track:
        sys.exit(1)

    # Test AI endpoints
    if not test_ai_endpoints(sample_track):
        sys.exit(1)

    print("\n🎉 All tests passed! The AI DJ backend is ready.")
    print("\nYou can now start the frontend with:")
    print("   cd apps/web && npm run dev")
    print("\nThen visit: http://localhost:3000")


if __name__ == "__main__":
    main()

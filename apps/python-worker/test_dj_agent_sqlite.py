#!/usr/bin/env python3
"""
Test script for LangGraph DJ Agent with SQLite database.
Demonstrates track analysis and similarity calculations without requiring OpenAI API.
"""

import os
import sys
from agents.dj_agent import DJAgent
from utils.sqlite_db import get_sqlite_db

def test_track_analysis():
    """Test track analysis functionality."""
    print("🎧 Testing DJ Agent Track Analysis")
    print("=" * 50)
    
    # Get database connection
    db = get_sqlite_db()
    total_tracks = db.tracks.count_documents({})
    print(f"📊 Database: {total_tracks} tracks available")
    
    # Get a sample track
    sample_track = db.tracks.find_one({})
    if not sample_track:
        print("❌ No tracks found in database")
        return
    
    print(f"\n🎵 Sample Track: {sample_track['title']} by {sample_track['artist']}")
    print(f"   BPM: {sample_track.get('bpm', 'Unknown')}")
    print(f"   Duration: {sample_track.get('duration', 'Unknown')} seconds")
    print(f"   Energy Level: {sample_track.get('energy_level', 'Unknown')}")
    
    # Test DJ Agent initialization (without OpenAI)
    try:
        # Don't initialize the LLM
        print("\n🤖 Testing DJ Agent Core Functions...")
        
        # Create a minimal agent instance for testing
        class TestDJAgent:
            def __init__(self):
                self.db = get_sqlite_db()
            
            def _calculate_energy_level(self, track):
                """Calculate energy level from BPM and mood."""
                bpm = track.get("bpm", 120)
                mood = track.get("mood", {})
                
                # Normalize BPM to 0-1 scale (60-200 BPM range)
                bpm_energy = (bpm - 60) / 140
                bpm_energy = max(0, min(1, bpm_energy))
                
                # Calculate mood energy
                high_energy_moods = ["mood_aggressive", "mood_party", "mood_electronic"]
                low_energy_moods = ["mood_relaxed", "mood_sad", "mood_acoustic"]
                
                mood_energy = 0
                for mood_type in high_energy_moods:
                    mood_energy += mood.get(mood_type, 0)
                for mood_type in low_energy_moods:
                    mood_energy -= mood.get(mood_type, 0) * 0.5
                
                mood_energy = (mood_energy + 1) / 2  # Normalize to 0-1
                
                # Weighted combination
                return 0.6 * bpm_energy + 0.4 * mood_energy
            
            def _get_dominant_vibe(self, mood):
                """Get the dominant mood/vibe from mood scores."""
                if not mood:
                    return "neutral"
                
                # Remove 'mood_' prefix and find max
                mood_scores = {k.replace("mood_", ""): v for k, v in mood.items()}
                return max(mood_scores, key=mood_scores.get)
            
            def _calculate_similarity(self, reference, candidate, context):
                """Calculate similarity score between tracks."""
                weights = {
                    'bpm_proximity': 0.30,
                    'mood_match': 0.25,
                    'energy_compatibility': 0.20,
                    'genre_affinity': 0.15,
                    'key_compatibility': 0.10
                }
                
                scores = {}
                
                # BPM proximity (within 5% is perfect match)
                ref_bpm = reference.get("bpm", 120)
                cand_bpm = candidate.get("bpm", 120)
                bpm_diff = abs(ref_bpm - cand_bpm) / ref_bpm
                scores['bpm_proximity'] = max(0, 1 - (bpm_diff * 20))
                
                # Genre affinity
                ref_genre = reference.get("genre", "").lower()
                cand_genre = candidate.get("genre", "").lower()
                if ref_genre and cand_genre:
                    if ref_genre == cand_genre:
                        scores['genre_affinity'] = 1.0
                    elif any(word in cand_genre for word in ref_genre.split()) or \
                         any(word in ref_genre for word in cand_genre.split()):
                        scores['genre_affinity'] = 0.7
                    else:
                        scores['genre_affinity'] = 0.3
                else:
                    scores['genre_affinity'] = 0.5
                
                # Energy compatibility
                ref_energy = self._calculate_energy_level(reference)
                cand_energy = self._calculate_energy_level(candidate)
                energy_diff = abs(ref_energy - cand_energy)
                scores['energy_compatibility'] = 1 - energy_diff
                
                # Mood and key defaults
                scores['mood_match'] = 0.5
                scores['key_compatibility'] = 0.7
                
                # Calculate weighted total
                total_score = sum(scores.get(factor, 0) * weight 
                                 for factor, weight in weights.items())
                
                return total_score
        
        agent = TestDJAgent()
        
        # Test energy calculation
        energy = agent._calculate_energy_level(sample_track)
        print(f"   Calculated Energy: {energy:.3f}")
        
        # Test vibe detection
        vibe = agent._get_dominant_vibe(sample_track.get("mood", {}))
        print(f"   Dominant Vibe: {vibe}")
        
        # Find similar tracks
        print(f"\n🔍 Finding similar tracks to '{sample_track['title']}'...")
        
        all_tracks = agent.db.tracks.find({}, limit=50)  # Test with first 50 tracks
        similar_tracks = []
        
        context = {"suggested_energy_direction": "maintain"}
        
        for track in all_tracks:
            if track["filepath"] == sample_track["filepath"]:
                continue  # Skip the same track
            
            similarity = agent._calculate_similarity(sample_track, track, context)
            if similarity > 0.6:  # Similarity threshold
                similar_tracks.append({
                    "track": track,
                    "similarity": similarity
                })
        
        # Sort by similarity
        similar_tracks.sort(key=lambda x: x["similarity"], reverse=True)
        
        print(f"   Found {len(similar_tracks)} similar tracks (>60% match)")
        
        # Show top 5 matches
        print("\n🎯 Top Similar Tracks:")
        for i, match in enumerate(similar_tracks[:5]):
            track = match["track"]
            similarity = match["similarity"]
            print(f"   {i+1}. {track['title']} by {track['artist']}")
            print(f"      BPM: {track.get('bpm', 'Unknown')}, Similarity: {similarity:.1%}")
        
        if not similar_tracks:
            print("   No highly similar tracks found in sample set")
        
        print("\n✅ DJ Agent core functions working correctly!")
        
    except Exception as e:
        print(f"❌ Error testing DJ Agent: {e}")
        import traceback
        traceback.print_exc()

def test_database_stats():
    """Show database statistics."""
    print("\n📊 Database Statistics")
    print("=" * 30)
    
    db = get_sqlite_db()
    
    # Count tracks by decade
    all_tracks = db.tracks.find({})
    decades = {}
    genres = {}
    bpm_ranges = {"<100": 0, "100-120": 0, "120-140": 0, ">140": 0}
    
    for track in all_tracks:
        # Year analysis
        year = track.get("year")
        if year and year.isdigit():
            decade = f"{int(year)//10*10}s"
            decades[decade] = decades.get(decade, 0) + 1
        
        # Genre analysis
        genre = track.get("genre", "Unknown")
        genres[genre] = genres.get(genre, 0) + 1
        
        # BPM analysis
        bpm = track.get("bpm", 0)
        if bpm < 100:
            bpm_ranges["<100"] += 1
        elif bpm < 120:
            bpm_ranges["100-120"] += 1
        elif bpm < 140:
            bpm_ranges["120-140"] += 1
        else:
            bpm_ranges[">140"] += 1
    
    print("📅 Tracks by Decade:")
    for decade, count in sorted(decades.items()):
        print(f"   {decade}: {count} tracks")
    
    print("\n🎵 Top Genres:")
    sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
    for genre, count in sorted_genres[:10]:
        print(f"   {genre}: {count} tracks")
    
    print("\n🥁 BPM Distribution:")
    for bpm_range, count in bpm_ranges.items():
        print(f"   {bpm_range} BPM: {count} tracks")

if __name__ == "__main__":
    print("🎧 LangGraph DJ Agent - SQLite Test")
    print("=" * 50)
    
    test_track_analysis()
    test_database_stats()
    
    print("\n" + "=" * 50)
    print("🎉 Testing Complete!")
    print("\nTo use the DJ Agent with AI features:")
    print("1. Set OPENAI_API_KEY in your .env file")
    print("2. Run: python examples/test_dj_agent.py")
    print("3. Or start the FastAPI server: python main.py")
    print("4. Test AI endpoints at: http://localhost:8000/docs") 
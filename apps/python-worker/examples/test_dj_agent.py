"""
Example script to test the LangGraph DJ Agent functionality.
"""

import asyncio
import json
from agents.dj_agent import DJAgent


async def test_dj_agent():
    """Test the DJ agent with sample data."""

    # Initialize the agent
    agent = DJAgent()

    # Example track ID (you'll need to replace with an actual track from your DB)
    current_track_id = "example_track.mp3"

    # Test 1: Suggest next track
    print("=== Testing Next Track Suggestion ===")
    context = {"time_of_day": "evening", "crowd_energy": 0.7, "energy_pattern": "wave"}

    result = await agent.suggest_next_track(current_track_id, context)
    print(f"Suggestion: {json.dumps(result, indent=2)}")

    # Test 2: Generate playlist
    print("\n=== Testing Playlist Generation ===")
    playlist_result = await agent.generate_playlist(
        seed_track_id=current_track_id,
        length=5,
        energy_pattern="build_up",
        context={"time_of_day": "night"},
    )

    if "error" not in playlist_result:
        print(f"Generated {len(playlist_result['playlist'])} tracks")
        print("Energy flow:", playlist_result["energy_flow"])
        for i, track in enumerate(playlist_result["playlist"]):
            print(
                f"{i + 1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} ({track.get('bpm', 0):.1f} BPM)"
            )
    else:
        print(f"Error: {playlist_result['error']}")


async def test_similarity_calculation():
    """Test the similarity calculation between tracks."""

    agent = DJAgent()

    # Mock tracks for testing
    reference_track = {
        "bpm": 128,
        "mood": {"mood_electronic": 0.8, "mood_party": 0.7, "mood_aggressive": 0.3},
        "genre": "House",
    }

    candidate_track = {
        "bpm": 126,
        "mood": {"mood_electronic": 0.9, "mood_party": 0.6, "mood_happy": 0.4},
        "genre": "Tech House",
    }

    context = {"suggested_energy_direction": "maintain"}

    # Calculate energy levels
    ref_energy = agent._calculate_energy_level(reference_track)
    cand_energy = agent._calculate_energy_level(candidate_track)

    # Add energy levels for similarity calculation
    reference_track["energy_level"] = ref_energy

    similarity = agent._calculate_similarity(reference_track, candidate_track, context)

    print("=== Similarity Calculation Test ===")
    print(
        f"Reference: {reference_track['genre']} @ {reference_track['bpm']} BPM, Energy: {ref_energy:.2f}"
    )
    print(
        f"Candidate: {candidate_track['genre']} @ {candidate_track['bpm']} BPM, Energy: {cand_energy:.2f}"
    )
    print(f"Similarity Score: {similarity:.3f}")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_dj_agent())
    print("\n" + "=" * 50 + "\n")
    asyncio.run(test_similarity_calculation())

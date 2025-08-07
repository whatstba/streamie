"""
Example script to test the LangGraph DJ Agent functionality.
"""

import asyncio
import json
import pytest
from agents.dj_agent import DJAgent


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_similarity_calculation():
    """Test the similarity calculation between tracks."""
    # NOTE: This test is outdated. The _calculate_energy_level and _calculate_similarity
    # methods have been removed in favor of AI-powered track evaluation through LLMs.
    # The DJ agent now uses the DJLLMService for track similarity and energy analysis.
    
    # TODO: Update this test to use the new AI-powered approach or remove it
    pytest.skip("Test uses outdated methods that have been replaced by AI-powered evaluation")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_dj_agent())
    # Skip the similarity calculation test as it uses outdated methods
    # print("\n" + "=" * 50 + "\n")
    # asyncio.run(test_similarity_calculation())

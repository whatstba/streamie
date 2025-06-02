"""
Test script for the new LangGraph-based DJ Agent
"""

import asyncio
import sys
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.dj_agent import DJAgent


async def test_agent():
    """Test the DJ agent's capabilities"""
    
    print("🎧 Testing LangGraph DJ Agent")
    print("="*60)
    
    # Initialize agent
    agent = DJAgent(llm_model="gpt-4o-mini")
    
    # Test 1: Generate a chill evening playlist
    print("\n📀 Test 1: Generate Chill Evening Playlist")
    print("-"*40)
    
    result = await agent.generate_playlist(
        vibe_description="chill evening vibes, something smooth and relaxing",
        length=5,
        energy_pattern="cool_down",
        thread_id="test-session-1"
    )
    
    if result["success"]:
        print(f"\n✅ Agent Response:\n{result['response']}")
    else:
        print(f"\n❌ Error: {result['error']}")
    
    # Test 2: Generate a workout playlist
    print("\n\n📀 Test 2: Generate Workout Playlist")
    print("-"*40)
    
    result = await agent.generate_playlist(
        vibe_description="high energy workout music, upbeat and motivating",
        length=5,
        energy_pattern="peak_time",
        thread_id="test-session-2"
    )
    
    if result["success"]:
        print(f"\n✅ Agent Response:\n{result['response']}")
    else:
        print(f"\n❌ Error: {result['error']}")
    
    # Test 3: Suggest next track
    print("\n\n📀 Test 3: Suggest Next Track")
    print("-"*40)
    
    # Pick a track from the database as current
    current_track = "PLAYLISTS/THRWBYKES/112/112 (Album)/07 Come See Me.mp3"
    
    result = await agent.suggest_next_track(
        current_track=current_track,
        context="Playing at a late night lounge, want to keep it smooth",
        thread_id="test-session-3"
    )
    
    if result["success"]:
        print(f"\n✅ Agent Response:\n{result['response']}")
    else:
        print(f"\n❌ Error: {result['error']}")
    
    print("\n" + "="*60)
    print("✅ Tests completed!")


if __name__ == "__main__":
    asyncio.run(test_agent()) 
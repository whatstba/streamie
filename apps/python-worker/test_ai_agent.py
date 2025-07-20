#!/usr/bin/env python3
"""
Test the AI-powered DJ agent to ensure all manual calculations have been removed.
"""

import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from agents.dj_agent import DJAgent


async def test_ai_agent():
    """Test the AI-powered DJ agent functionality."""

    print("🎵 Testing AI-Powered DJ Agent")
    print("=" * 50)

    # Initialize the agent
    agent = DJAgent(llm_model="gpt-4")  # Using GPT-4 for testing

    # Test 1: Generate a vibe-based playlist using AI
    print("\n🎯 Test 1: Generate AI-powered vibe playlist")
    vibe_result = await agent.generate_playlist(
        vibe_description="upbeat house music for a sunset beach party",
        length=5,
        energy_pattern="wave",
    )

    if vibe_result["success"]:
        print(
            f"✅ Success! Generated {len(vibe_result.get('finalized_playlist', []))} tracks"
        )
        print(f"Response: {vibe_result['response'][:200]}...")

        # Check for AI insights
        if vibe_result.get("finalized_playlist"):
            print("\n📋 Playlist tracks:")
            for i, track in enumerate(vibe_result["finalized_playlist"][:3]):
                print(f"   {i + 1}. {track.get('filepath', 'Unknown')}")

        # Check transitions were planned with AI
        if vibe_result.get("transitions"):
            print(f"\n🔄 AI planned {len(vibe_result['transitions'])} transitions")
            first_transition = vibe_result["transitions"][0]
            if "effect_plan" in first_transition:
                print(
                    f"   First transition profile: {first_transition['effect_plan'].get('profile', 'Unknown')}"
                )
                print(
                    f"   AI reasoning: {first_transition['effect_plan'].get('reasoning', 'No reasoning')[:100]}..."
                )
    else:
        print(f"❌ Error: {vibe_result.get('error', 'Unknown error')}")

    # Test 2: Test AI vibe analysis directly
    print("\n\n🎯 Test 2: Test AI vibe analysis")
    from utils.dj_llm import DJLLMService

    dj_service = DJLLMService()

    try:
        vibe_analysis = await dj_service.analyze_vibe(
            "dark techno for late night warehouse party"
        )
        print("✅ AI Vibe Analysis successful!")
        print(f"   Energy: {vibe_analysis.energy_level}")
        print(f"   BPM Range: {vibe_analysis.bpm_range}")
        print(f"   Mood: {vibe_analysis.mood_keywords}")
        print(f"   Mixing style: {vibe_analysis.mixing_style}")
    except Exception as e:
        print(f"❌ AI vibe analysis failed: {e}")

    # Test 3: Check that manual calculations are gone
    print("\n\n🎯 Test 3: Verify manual calculations removed")

    # Check for removed methods
    removed_methods = [
        "_calculate_energy_level",
        "_get_dominant_vibe",
        "_suggest_energy_direction",
        "_calculate_similarity",
        "_build_playlist_by_pattern",
        "_create_transition_planning_graph",
    ]

    for method in removed_methods:
        if hasattr(agent, method):
            print(f"❌ WARNING: {method} still exists!")
        else:
            print(f"✅ {method} successfully removed")

    print("\n" + "=" * 50)
    print("🎉 AI Agent Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_ai_agent())

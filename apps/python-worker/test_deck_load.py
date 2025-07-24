"""Direct test of deck loading to debug validation error"""

import asyncio
import sys
import pytest

sys.path.append("/Users/lynscott/Projects/streamie/apps/python-worker")

from models import init_db
from services.deck_manager import DeckManager


@pytest.mark.asyncio
async def test_load_track():
    print("Testing deck load directly...")

    # Initialize database and manager
    engine = await init_db()
    deck_manager = DeckManager(engine)

    # Test loading a track
    filepath = "/Users/lynscott/Downloads/ASAKE - JOHA.mp3"

    print(f"\nLoading track: {filepath}")
    result = await deck_manager.load_track("A", filepath)

    print("\nResult type:", type(result))
    print(
        "Result keys:",
        list(result.keys()) if isinstance(result, dict) else "Not a dict",
    )
    print("\nFull result:")
    for key, value in result.items():
        print(f"  {key}: {value} (type: {type(value).__name__})")

    # Check if it matches LoadTrackResponse model
    print("\nChecking LoadTrackResponse fields:")
    print(f"  - success: {'success' in result}")
    print(f"  - deck_id: {'deck_id' in result}")
    print(f"  - track: {'track' in result}")
    print(f"  - error: {'error' in result}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_load_track())

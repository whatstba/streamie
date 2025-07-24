#!/usr/bin/env python3
"""
Test DJ Set with simpler vibe descriptions
"""

import asyncio
import aiohttp
import logging
import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_simple_vibes():
    """Test with vibes that should match available genres"""

    async with aiohttp.ClientSession() as session:
        # Test vibes that match actual genres in the database
        test_vibes = [
            {"vibe": "hip hop party mix", "duration": 10, "pattern": "steady"},
            {"vibe": "jazz music for relaxing", "duration": 10, "pattern": "wave"},
            {"vibe": "reggae vibes", "duration": 10, "pattern": "steady"},
            {"vibe": "dance and electro energy", "duration": 10, "pattern": "building"},
        ]

        for test in test_vibes:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Testing: {test['vibe']}")
            logger.info(f"{'=' * 60}")

            # Just generate (don't play yet)
            async with session.post(
                f"{BASE_URL}/api/dj-set/generate",
                json={
                    "vibe_description": test["vibe"],
                    "duration_minutes": test["duration"],
                    "energy_pattern": test["pattern"],
                },
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Success! Generated {result['track_count']} tracks")
                    logger.info(f"   Duration: {result['total_duration'] / 60:.1f} min")

                    # Show first 3 tracks
                    for i, track in enumerate(result["tracks"][:3]):
                        logger.info(
                            f"   {i + 1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')}"
                        )
                else:
                    error = await resp.text()
                    logger.error(f"❌ Failed: {error}")

            # Small delay between tests
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(test_simple_vibes())

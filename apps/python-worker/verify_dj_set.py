#!/usr/bin/env python3
"""Verify DJ Set functionality works correctly"""

import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def test_simple_dj_set():
    """Test creating a simple DJ set"""

    logger.info("🎵 Testing DJ Set Generation")

    payload = {
        "vibe_description": "chill hip hop beats",
        "duration_minutes": 10,
        "energy_pattern": "steady",
    }

    async with aiohttp.ClientSession() as session:
        # Generate DJ set
        logger.info("📀 Generating DJ set...")
        async with session.post(
            f"{BASE_URL}/api/dj-set/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=180),
        ) as response:
            if response.status == 200:
                result = await response.json()

                if result.get("success"):
                    dj_set = result["dj_set"]
                    logger.info("✅ DJ Set created successfully!")
                    logger.info(f"   ID: {dj_set['id']}")
                    logger.info(f"   Name: {dj_set['name']}")
                    logger.info(f"   Tracks: {dj_set['track_count']}")
                    logger.info(
                        f"   Duration: {dj_set['total_duration'] / 60:.1f} minutes"
                    )

                    # Check tracks
                    logger.info("\n📋 Tracks in set:")
                    for i, track in enumerate(dj_set["tracks"][:5]):
                        logger.info(
                            f"   {i + 1}. {track['title']} by {track['artist']}"
                        )
                        logger.info(
                            f"      BPM: {track['bpm']:.0f}, Energy: {track['energy_level']:.2f}"
                        )
                        logger.info(f"      File: {track['filepath']}")

                        # Check for fake tracks
                        if (
                            "track_" in track["filepath"].lower()
                            and ".mp3" in track["filepath"]
                        ):
                            logger.error("      ❌ FAKE TRACK DETECTED!")

                    # Test immediate playback
                    logger.info("\n🎧 Starting playback...")
                    async with session.post(
                        f"{BASE_URL}/api/dj-set/{dj_set['id']}/play"
                    ) as play_response:
                        if play_response.status == 200:
                            play_result = await play_response.json()
                            logger.info(f"✅ Playback started: {play_result}")

                            # Check status
                            await asyncio.sleep(2)
                            async with session.get(
                                f"{BASE_URL}/api/dj-set/playback/status"
                            ) as status_response:
                                if status_response.status == 200:
                                    status = await status_response.json()
                                    logger.info("\n📊 Playback Status:")
                                    logger.info(
                                        f"   Playing: {status.get('is_playing')}"
                                    )
                                    logger.info(
                                        f"   Current Track: {status.get('current_track_order')}"
                                    )
                                    logger.info(
                                        f"   Elapsed: {status.get('elapsed_time', 0):.1f}s"
                                    )
                        else:
                            error = await play_response.text()
                            logger.error(f"❌ Playback failed: {error}")
                else:
                    logger.error(f"❌ DJ Set generation failed: {result.get('error')}")
            else:
                error = await response.text()
                logger.error(f"❌ HTTP {response.status}: {error}")


if __name__ == "__main__":
    asyncio.run(test_simple_dj_set())

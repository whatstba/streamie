#!/usr/bin/env python3
"""
Production-like test of the complete DJ set generation and pre-rendering flow.
This test uses the real DJ Agent to generate a set and pre-renders it,
exactly like the production workflow.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.service_manager import service_manager
from services.dj_set_service import DJSetService
from services.set_playback_controller import SetPlaybackController
from services.audio_prerenderer import AudioPrerenderer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_production_dj_set_flow():
    """Test the complete production flow: AI generation → pre-rendering"""
    
    logger.info("\n🎵 PRODUCTION DJ SET TEST")
    logger.info("=" * 60)
    logger.info("This test simulates the exact production workflow:")
    logger.info("1. AI generates a DJ set based on vibe")
    logger.info("2. Pre-renders the complete mix")
    logger.info("3. Verifies the output")
    
    try:
        # Initialize all services exactly like production
        logger.info("\n🔧 Initializing production services...")
        
        # Get services from service manager
        dj_set_service = await service_manager.get_dj_set_service()
        playback_controller = await service_manager.get_set_playback_controller()
        deck_manager = await service_manager.get_deck_manager()
        mixer_manager = await service_manager.get_mixer_manager()
        effect_manager = await service_manager.get_effect_manager()
        
        logger.info("✅ All services initialized")
        
        # Step 1: Generate a DJ set using AI (like production)
        logger.info("\n🤖 Step 1: Generating DJ set with AI...")
        
        # Test with a short set (3-4 tracks, ~5 minutes)
        vibe_request = {
            "vibe": "upbeat afrobeats party mix with smooth transitions",
            "duration_minutes": 5,  # Short for testing
            "energy_pattern": "building",
            "name": "Production Test Mix"
        }
        
        logger.info(f"   Vibe: {vibe_request['vibe']}")
        logger.info(f"   Duration: {vibe_request['duration_minutes']} minutes")
        logger.info(f"   Energy pattern: {vibe_request['energy_pattern']}")
        
        # Generate the DJ set using the real production service
        dj_set = await dj_set_service.generate_dj_set(
            vibe_description=vibe_request["vibe"],
            duration_minutes=vibe_request["duration_minutes"],
            energy_pattern=vibe_request["energy_pattern"],
            name=vibe_request["name"]
        )
        
        logger.info(f"✅ DJ set generated: {dj_set.name}")
        logger.info(f"   ID: {dj_set.id}")
        logger.info(f"   Tracks: {dj_set.track_count}")
        logger.info(f"   Total duration: {dj_set.total_duration/60:.1f} minutes")
        logger.info(f"   Energy pattern: {dj_set.energy_pattern}")
        
        # Log track details
        logger.info("\n📋 Track List:")
        for i, track in enumerate(dj_set.tracks, 1):
            logger.info(f"   {i}. {track.artist} - {track.title}")
            logger.info(f"      BPM: {track.bpm:.1f}, Key: {track.key}, Deck: {track.deck}")
            logger.info(f"      Time: {track.start_time:.1f}s - {track.end_time:.1f}s")
        
        # Log transitions
        if dj_set.transitions:
            logger.info("\n🔄 Transitions:")
            for transition in dj_set.transitions:
                logger.info(f"   Track {transition.from_track_order} → {transition.to_track_order}")
                logger.info(f"   Type: {transition.type}, Duration: {transition.duration}s")
                logger.info(f"   Technique: {transition.technique_notes}")
        
        # Step 2: Pre-render the DJ set (like production)
        logger.info("\n🎬 Step 2: Pre-rendering the DJ set...")
        
        # Create pre-renderer
        prerenderer = AudioPrerenderer(deck_manager, mixer_manager, effect_manager)
        
        # Pre-render the set
        start_time = datetime.now()
        output_path = await prerenderer.prerender_dj_set(dj_set)
        render_time = (datetime.now() - start_time).total_seconds()
        
        # Copy to test location
        import shutil
        final_path = os.path.expanduser("~/Downloads/test_production_dj_set.wav")
        shutil.copy2(output_path, final_path)
        
        # Step 3: Verify the output
        logger.info("\n✅ Step 3: Verification")
        
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        
        # Load a snippet to verify it's valid audio
        import librosa
        try:
            y, sr = librosa.load(final_path, duration=5.0)
            duration = librosa.get_duration(path=final_path)
            
            logger.info(f"   Output file: {final_path}")
            logger.info(f"   File size: {file_size:.2f} MB")
            logger.info(f"   Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
            logger.info(f"   Render time: {render_time:.1f}s")
            logger.info(f"   Render speed: {duration/render_time:.1f}x realtime")
            
            # Verify duration matches the DJ set
            expected_duration = dj_set.total_duration
            if abs(duration - expected_duration) < 2.0:  # Within 2 seconds
                logger.info(f"   ✅ Duration matches DJ set ({expected_duration:.1f}s)")
            else:
                logger.warning(f"   ⚠️ Duration mismatch: expected {expected_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"   ❌ Failed to verify audio: {e}")
            return False
        
        # Test the playback controller (optional - just initialization)
        logger.info("\n🎮 Testing playback controller initialization...")
        
        # Load the set into playback controller (without actually playing)
        success = await playback_controller.load_dj_set(dj_set.id)
        if success:
            logger.info("   ✅ Playback controller can load the set")
            status = playback_controller.get_playback_status(dj_set.id)
            logger.info(f"   Status: {status}")
        else:
            logger.warning("   ⚠️ Playback controller couldn't load the set")
        
        logger.info("\n🎉 PRODUCTION TEST COMPLETED SUCCESSFULLY!")
        logger.info(f"🎧 You can play the output: {final_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"\n💥 Production test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            await service_manager.shutdown()
        except:
            pass


async def main():
    """Run the production test"""
    logger.info("🚀 Starting Production DJ Set Test")
    logger.info("This test uses the real AI agent and production workflow")
    
    success = await test_production_dj_set_flow()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
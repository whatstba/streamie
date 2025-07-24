#!/usr/bin/env python3
"""
Test script to process a real audio file through the audio engine with effects.
This verifies the engine can load, process, and pre-render actual music files.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.service_manager import service_manager
from services.audio_prerenderer import AudioPrerenderer
from models.dj_set_models import DJSet, DJSetTrack
from utils.dj_llm import TransitionEffect

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_audio_engine_with_real_file():
    """Test the audio engine with a real audio file and effects."""
    
    # Test file path
    test_file = "/Users/lynscott/Downloads/PLAYLISTS/AFRO HITS/Gyakie/Forever (Remix) (Single)/01 Forever (Remix).mp3"
    
    # Check if file exists
    if not os.path.exists(test_file):
        logger.error(f"Test file not found: {test_file}")
        return False
    
    logger.info(f"🎵 Testing audio engine with file: {test_file}")
    
    try:
        # Initialize services
        logger.info("🔧 Initializing services...")
        deck_manager = await service_manager.get_deck_manager()
        mixer_manager = await service_manager.get_mixer_manager()
        effect_manager = await service_manager.get_effect_manager()
        
        # Create pre-renderer
        prerenderer = AudioPrerenderer(deck_manager, mixer_manager, effect_manager)
        logger.info("✅ Pre-renderer initialized")
        
        # Create a test DJ set with the real file
        test_set = DJSet(
            id="test-real-file",
            name="Real File Test",
            duration=60.0,  # 1 minute excerpt
            vibe_description="Testing with real audio file and effects",
            total_duration=60.0,
            track_count=1,
            energy_pattern="steady",
            transitions=[],
            energy_graph=[0.7] * 10,  # Higher energy
            key_moments=[],
            mixing_style="effects_test",
            tracks=[
                DJSetTrack(
                    filepath=test_file,
                    title="Forever (Remix)",
                    artist="Gyakie",
                    bpm=120.0,  # Approximate BPM
                    key="Am",
                    start_time=0.0,
                    end_time=60.0,  # 1 minute
                    gain_adjust=1.0,
                    eq_low=0.1,   # Slight bass boost
                    eq_mid=-0.1,  # Slight mid cut
                    eq_high=0.2,  # Treble boost
                    order=1,
                    deck="A",
                    fade_in_time=0.0,
                    fade_out_time=58.0,  # Fade out at 58 seconds
                    energy_level=0.7,
                    mixing_note="Test with EQ and fade effects",
                    tempo_adjust=0.0  # No tempo change
                )
            ]
        )
        
        logger.info("📋 Created test DJ set")
        
        # Pre-render the set
        logger.info("🎬 Starting pre-render process...")
        output_path = await prerenderer.prerender_dj_set(test_set)
        
        # Verify the output
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            logger.info(f"✅ SUCCESS! Pre-rendered file created:")
            logger.info(f"   Path: {output_path}")
            logger.info(f"   Size: {file_size:.2f} MB")
            
            # Copy to a fixed location for easy access
            import shutil
            final_path = os.path.expanduser("~/Downloads/test_real_audio_output.wav")
            shutil.copy2(output_path, final_path)
            logger.info(f"📁 Copied to: {final_path}")
            
            return True
        else:
            logger.error(f"❌ Pre-render failed - no output file created")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
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
    """Main test runner."""
    logger.info("🚀 Starting audio engine test with real file")
    
    success = await test_audio_engine_with_real_file()
    
    if success:
        logger.info("🎉 Test completed successfully!")
        logger.info("🎧 You can now play the output file: ~/Downloads/test_real_audio_output.wav")
    else:
        logger.error("💥 Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
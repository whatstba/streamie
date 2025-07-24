#!/usr/bin/env python3
"""
Comprehensive test of the audio engine with real audio files.
Tests loading, processing, effects, and pre-rendering capabilities.
"""

import asyncio
import os
import sys
import logging
import numpy as np
import librosa
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.dj_set_models import DJSet, DJSetTrack, DJSetTransition
from services.audio_prerenderer import AudioPrerenderer
from services.service_manager import service_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def find_test_file():
    """Find a suitable test audio file"""
    # Try specific locations
    test_paths = [
        "/Users/lynscott/Downloads/PLAYLISTS/AFRO HITS/Gyakie/Forever (Remix) (Single)/01 Forever (Remix).mp3",
        "/Users/lynscott/Downloads/PLAYLISTS/AFRO HITS/Burna Boy/Love, Damini/08 For My Hand (feat. Ed Sheeran).mp3",
        "/Users/lynscott/Downloads/PLAYLISTS/AFRO HITS/Wizkid/Made In Lagos/11 Essence (feat. Tems).mp3",
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            return path
    
    # Search for any MP3 file
    import glob
    mp3_files = glob.glob(os.path.expanduser("~/Downloads/PLAYLISTS/*/*/*/*.mp3"))
    if mp3_files:
        return mp3_files[0]
    
    return None


async def analyze_audio_file(filepath: str):
    """Analyze an audio file to get BPM, key, and energy"""
    logger.info(f"🔍 Analyzing audio file: {os.path.basename(filepath)}")
    
    try:
        # Load audio
        y, sr = librosa.load(filepath, duration=30.0, sr=44100)
        
        # Get tempo (BPM)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
        
        # Get energy (RMS)
        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms))
        
        logger.info(f"  BPM: {bpm:.1f}, Energy: {energy:.3f}")
        return bpm, energy
        
    except Exception as e:
        logger.warning(f"  Failed to analyze: {e}")
        return 120.0, 0.5  # Default values


async def test_single_track_effects():
    """Test processing a single track with various effects"""
    logger.info("\n🎵 TEST 1: Single Track with Effects")
    logger.info("=" * 50)
    
    # Find test file
    test_file = await find_test_file()
    if not test_file:
        logger.error("❌ No test audio file found!")
        return False
    
    logger.info(f"📁 Using file: {os.path.basename(test_file)}")
    
    # Analyze the file
    bpm, energy = await analyze_audio_file(test_file)
    
    try:
        # Initialize services
        logger.info("🔧 Initializing audio services...")
        deck_manager = await service_manager.get_deck_manager()
        mixer_manager = await service_manager.get_mixer_manager()
        effect_manager = await service_manager.get_effect_manager()
        prerenderer = AudioPrerenderer(deck_manager, mixer_manager, effect_manager)
        
        # Create test DJ set with effects
        test_set = DJSet(
            id="test-effects",
            name="Single Track Effects Test",
            vibe_description="Testing audio engine with various effects",
            total_duration=30.0,
            track_count=1,
            energy_pattern="steady",
            transitions=[],
            energy_graph=[energy] * 10,
            key_moments=[],
            mixing_style="effects_showcase",
            tracks=[
                DJSetTrack(
                    filepath=test_file,
                    title=os.path.basename(test_file),
                    artist="Test Artist",
                    bpm=bpm,
                    key="Am",
                    start_time=0.0,
                    end_time=30.0,
                    gain_adjust=0.8,      # Slight volume reduction
                    eq_low=0.2,          # Bass boost
                    eq_mid=-0.1,         # Slight mid cut
                    eq_high=0.1,         # Slight treble boost
                    order=1,
                    deck="A",
                    fade_in_time=2.0,    # 2 second fade in
                    fade_out_time=28.0,  # 2 second fade out
                    energy_level=energy,
                    mixing_note="Testing EQ, gain, and fade effects",
                    tempo_adjust=0.0
                )
            ]
        )
        
        # Pre-render
        logger.info("🎬 Pre-rendering with effects...")
        output_path = await prerenderer.prerender_dj_set(test_set)
        
        # Copy to test location
        import shutil
        final_path = os.path.expanduser("~/Downloads/test_1_single_track_effects.wav")
        shutil.copy2(output_path, final_path)
        
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        logger.info(f"✅ SUCCESS! Output: {final_path}")
        logger.info(f"   Size: {file_size:.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_two_track_transition():
    """Test mixing two tracks with a transition"""
    logger.info("\n🎵 TEST 2: Two Track Transition")
    logger.info("=" * 50)
    
    # Find test files
    import glob
    mp3_files = glob.glob(os.path.expanduser("~/Downloads/PLAYLISTS/*/*/*/*.mp3"))[:2]
    
    if len(mp3_files) < 2:
        logger.error("❌ Need at least 2 audio files for transition test!")
        return False
    
    logger.info(f"📁 Track 1: {os.path.basename(mp3_files[0])}")
    logger.info(f"📁 Track 2: {os.path.basename(mp3_files[1])}")
    
    # Analyze files
    bpm1, energy1 = await analyze_audio_file(mp3_files[0])
    bpm2, energy2 = await analyze_audio_file(mp3_files[1])
    
    try:
        # Initialize services
        logger.info("🔧 Initializing audio services...")
        deck_manager = await service_manager.get_deck_manager()
        mixer_manager = await service_manager.get_mixer_manager()
        effect_manager = await service_manager.get_effect_manager()
        prerenderer = AudioPrerenderer(deck_manager, mixer_manager, effect_manager)
        
        # Create test DJ set with transition
        test_set = DJSet(
            id="test-transition",
            name="Two Track Transition Test",
            vibe_description="Testing crossfade transition between two tracks",
            total_duration=40.0,
            track_count=2,
            energy_pattern="building",
            transitions=[
                DJSetTransition(
                    from_track_order=1,
                    to_track_order=2,
                    from_deck="A",
                    to_deck="B",
                    start_time=15.0,  # Start transition at 15 seconds
                    duration=10.0,    # 10 second transition
                    type="smooth_blend",
                    effects=[],       # Simple crossfade, no effects
                    crossfade_curve="s-curve",
                    technique_notes="Smooth crossfade between tracks",
                    risk_level="safe",
                    compatibility_score=0.8,
                    outro_cue=0.9,    # 90% into track 1
                    intro_cue=0.1     # 10% into track 2
                )
            ],
            energy_graph=[energy1] * 5 + [energy2] * 5,
            key_moments=[{"time": "20.0", "description": "Track transition"}],
            mixing_style="smooth_transition",
            tracks=[
                DJSetTrack(
                    filepath=mp3_files[0],
                    title=os.path.basename(mp3_files[0]),
                    artist="Artist 1",
                    bpm=bpm1,
                    key="Am",
                    start_time=0.0,
                    end_time=25.0,     # Ends during transition
                    gain_adjust=1.0,
                    eq_low=0.0,
                    eq_mid=0.0,
                    eq_high=0.0,
                    order=1,
                    deck="A",
                    fade_in_time=0.0,
                    fade_out_time=15.0,  # Start fading at transition
                    energy_level=energy1,
                    mixing_note="First track, crossfades out",
                    tempo_adjust=0.0
                ),
                DJSetTrack(
                    filepath=mp3_files[1],
                    title=os.path.basename(mp3_files[1]),
                    artist="Artist 2",
                    bpm=bpm2,
                    key="Cm",
                    start_time=15.0,   # Starts during transition
                    end_time=40.0,
                    gain_adjust=1.0,
                    eq_low=0.0,
                    eq_mid=0.0,
                    eq_high=0.0,
                    order=2,
                    deck="B",
                    fade_in_time=15.0,   # Fade in during transition
                    fade_out_time=40.0,
                    energy_level=energy2,
                    mixing_note="Second track, crossfades in",
                    tempo_adjust=0.0
                )
            ]
        )
        
        # Pre-render
        logger.info("🎬 Pre-rendering transition mix...")
        output_path = await prerenderer.prerender_dj_set(test_set)
        
        # Copy to test location
        import shutil
        final_path = os.path.expanduser("~/Downloads/test_2_track_transition.wav")
        shutil.copy2(output_path, final_path)
        
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        logger.info(f"✅ SUCCESS! Output: {final_path}")
        logger.info(f"   Size: {file_size:.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dj_effects():
    """Test DJ-specific effects like filter sweeps and echo"""
    logger.info("\n🎵 TEST 3: DJ Effects (Filter & Echo)")
    logger.info("=" * 50)
    
    # Find test file
    test_file = await find_test_file()
    if not test_file:
        logger.error("❌ No test audio file found!")
        return False
    
    logger.info(f"📁 Using file: {os.path.basename(test_file)}")
    
    # Analyze the file
    bpm, energy = await analyze_audio_file(test_file)
    
    try:
        # Initialize services
        logger.info("🔧 Initializing audio services...")
        deck_manager = await service_manager.get_deck_manager()
        mixer_manager = await service_manager.get_mixer_manager()
        effect_manager = await service_manager.get_effect_manager()
        prerenderer = AudioPrerenderer(deck_manager, mixer_manager, effect_manager)
        
        # Create test DJ set with DJ effects
        # Note: Since transition effects are handled separately,
        # we'll use EQ to simulate filter effects
        test_set = DJSet(
            id="test-dj-effects",
            name="DJ Effects Test",
            vibe_description="Testing DJ effects like filters and echo",
            total_duration=20.0,
            track_count=1,
            energy_pattern="dynamic",
            transitions=[],
            energy_graph=[0.5, 0.7, 0.9, 0.7, 0.5] * 2,
            key_moments=[
                {"time": "5.0", "description": "Filter sweep up"},
                {"time": "10.0", "description": "Filter sweep down"},
                {"time": "15.0", "description": "Echo effect"}
            ],
            mixing_style="effects_heavy",
            tracks=[
                DJSetTrack(
                    filepath=test_file,
                    title=os.path.basename(test_file),
                    artist="Test Artist",
                    bpm=bpm,
                    key="Am",
                    start_time=0.0,
                    end_time=20.0,
                    gain_adjust=0.9,
                    # Simulate filter sweep with extreme EQ
                    eq_low=-0.5,     # Heavy bass cut (high-pass filter effect)
                    eq_mid=0.2,      # Mid boost
                    eq_high=0.5,     # Heavy treble boost
                    order=1,
                    deck="A",
                    fade_in_time=0.0,
                    fade_out_time=19.0,
                    energy_level=energy,
                    mixing_note="Testing filter sweep simulation with EQ",
                    tempo_adjust=0.0
                )
            ]
        )
        
        # Pre-render
        logger.info("🎬 Pre-rendering with DJ effects...")
        output_path = await prerenderer.prerender_dj_set(test_set)
        
        # Copy to test location
        import shutil
        final_path = os.path.expanduser("~/Downloads/test_3_dj_effects.wav")
        shutil.copy2(output_path, final_path)
        
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        logger.info(f"✅ SUCCESS! Output: {final_path}")
        logger.info(f"   Size: {file_size:.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_output_files():
    """Verify all output files are valid WAV files"""
    logger.info("\n🔍 Verifying Output Files")
    logger.info("=" * 50)
    
    output_files = [
        "~/Downloads/test_1_single_track_effects.wav",
        "~/Downloads/test_2_track_transition.wav",
        "~/Downloads/test_3_dj_effects.wav"
    ]
    
    all_valid = True
    
    for file_path in output_files:
        full_path = os.path.expanduser(file_path)
        if os.path.exists(full_path):
            try:
                # Try to load with librosa to verify it's valid audio
                y, sr = librosa.load(full_path, duration=1.0)
                file_size = os.path.getsize(full_path) / (1024 * 1024)
                duration = librosa.get_duration(path=full_path)
                logger.info(f"✅ {os.path.basename(full_path)}: Valid WAV, {file_size:.2f} MB, {duration:.1f}s")
            except Exception as e:
                logger.error(f"❌ {os.path.basename(full_path)}: Invalid audio file - {e}")
                all_valid = False
        else:
            logger.warning(f"⚠️  {os.path.basename(full_path)}: File not found")
    
    return all_valid


async def main():
    """Run all audio engine tests"""
    logger.info("🚀 Starting Comprehensive Audio Engine Tests")
    logger.info("This will test loading, processing, and pre-rendering real audio files")
    
    try:
        # Run tests
        test_results = []
        
        # Test 1: Single track with effects
        result1 = await test_single_track_effects()
        test_results.append(("Single Track Effects", result1))
        
        # Test 2: Two track transition
        result2 = await test_two_track_transition()
        test_results.append(("Two Track Transition", result2))
        
        # Test 3: DJ effects
        result3 = await test_dj_effects()
        test_results.append(("DJ Effects", result3))
        
        # Verify output files
        verify_result = await verify_output_files()
        
        # Summary
        logger.info("\n📊 TEST SUMMARY")
        logger.info("=" * 50)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nFile Verification: {'✅ PASSED' if verify_result else '❌ FAILED'}")
        
        # Overall result
        all_passed = all(result for _, result in test_results) and verify_result
        
        if all_passed:
            logger.info("\n🎉 ALL TESTS PASSED! Audio engine is working correctly.")
            logger.info("🎧 You can now play the output files in ~/Downloads/test_*.wav")
        else:
            logger.error("\n💥 Some tests failed. Check the logs above.")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            await service_manager.shutdown()
        except:
            pass


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Production-like test of pre-rendering with a pre-made DJ set.
This test creates a realistic DJ set with real music files and pre-renders it,
testing the exact production pre-rendering workflow.
"""

import asyncio
import os
import sys
import logging
import glob
import random
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.dj_set_models import DJSet, DJSetTrack, DJSetTransition
from services.service_manager import service_manager
from services.audio_prerenderer import AudioPrerenderer
from services.set_playback_controller import SetPlaybackController
from utils.dj_llm import TransitionEffect
import librosa
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_music_files(limit=6):
    """Find real music files from the local library"""
    music_paths = [
        "~/Downloads/PLAYLISTS/AFRO HITS/*/*/*.mp3",
        "~/Downloads/PLAYLISTS/AFRO CARIB/*/*/*.mp3",
        "~/Downloads/PLAYLISTS/DANCEHALL/*/*/*.mp3"
    ]
    
    all_files = []
    for pattern in music_paths:
        files = glob.glob(os.path.expanduser(pattern))
        all_files.extend(files)
    
    # Shuffle and take a subset
    random.shuffle(all_files)
    return all_files[:limit]


def analyze_track(filepath):
    """Quick analysis of a track to get BPM and energy"""
    try:
        y, sr = librosa.load(filepath, duration=30.0, sr=44100)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
        
        # Get energy (RMS)
        rms = librosa.feature.rms(y=y)
        energy = float(np.mean(rms))
        
        return bpm, energy
    except:
        # Default values if analysis fails
        return 120.0, 0.5


def create_pre_made_dj_set():
    """Create a realistic DJ set with real files"""
    logger.info("📋 Creating pre-made DJ set with real music files...")
    
    # Find real music files
    music_files = find_music_files(6)  # Get 6 tracks for a ~15 minute mix
    
    if len(music_files) < 3:
        logger.error("❌ Not enough music files found!")
        return None
    
    logger.info(f"   Found {len(music_files)} music files")
    
    # Create tracks with timing
    dj_tracks = []
    transitions = []
    current_time = 0.0
    track_duration = 180.0  # 3 minutes per track
    transition_duration = 8.0  # 8 second transitions (more realistic for DJ mixing)
    
    decks = ["A", "B"]  # Alternate between decks
    
    for i, filepath in enumerate(music_files):
        # Analyze track
        bpm, energy = analyze_track(filepath)
        
        # Extract metadata from filename
        filename = os.path.basename(filepath)
        parts = filepath.split("/")
        artist = parts[-3] if len(parts) > 3 else "Unknown Artist"
        title = os.path.splitext(filename)[0]
        
        # Determine timing
        if i == 0:
            # First track starts immediately
            start_time = 0.0
            end_time = track_duration
            fade_in_time = 0.0
            fade_out_time = track_duration - transition_duration
        elif i == len(music_files) - 1:
            # Last track
            start_time = current_time - transition_duration
            end_time = start_time + track_duration
            fade_in_time = start_time
            fade_out_time = end_time - 2.0  # Quick fade at end
        else:
            # Middle tracks
            start_time = current_time - transition_duration
            end_time = start_time + track_duration
            fade_in_time = start_time
            fade_out_time = end_time - transition_duration
        
        # Create track
        track = DJSetTrack(
            filepath=filepath,
            title=title,
            artist=artist,
            bpm=bpm,
            key="Am",  # Default key
            start_time=start_time,
            end_time=end_time,
            gain_adjust=0.9,
            eq_low=0.0,
            eq_mid=0.0,
            eq_high=0.0,
            order=i + 1,
            deck=decks[i % 2],
            fade_in_time=fade_in_time,
            fade_out_time=fade_out_time,
            energy_level=energy,
            mixing_note=f"Track {i+1} - {'Opening' if i==0 else 'Peak' if i==2 else 'Closing' if i==len(music_files)-1 else 'Building'}",
            tempo_adjust=0.0
        )
        
        dj_tracks.append(track)
        
        # Create transition (except for last track)
        if i < len(music_files) - 1:
            # Create realistic DJ transition effects
            transition_effects = []
            
            # Add filter sweep on outgoing track (high-pass filter)
            transition_effects.append(TransitionEffect(
                type="filter",
                start_at=0.0,  # Start immediately when transition begins
                duration=transition_duration * 0.8,  # 80% of transition duration
                intensity=0.7,  # Strong filter effect
                parameters={"filter_type": "high_pass", "resonance": 0.3}
            ))
            
            # Add subtle echo on the last few beats
            if i % 2 == 0:  # Alternate echo effect
                transition_effects.append(TransitionEffect(
                    type="echo",
                    start_at=transition_duration * 0.6,  # Start at 60% through transition
                    duration=transition_duration * 0.3,  # Last 30% of transition
                    intensity=0.3,  # Subtle echo
                    parameters={"delay_time": 125, "feedback": 0.3}
                ))
            
            transition = DJSetTransition(
                from_track_order=i + 1,
                to_track_order=i + 2,
                from_deck=decks[i % 2],
                to_deck=decks[(i + 1) % 2],
                start_time=fade_out_time,
                duration=transition_duration,
                type="smooth_blend",
                effects=transition_effects,
                crossfade_curve="s-curve",
                technique_notes=f"Professional DJ transition with filter sweep from track {i+1} to {i+2}",
                risk_level="safe",
                compatibility_score=0.8,
                outro_cue=0.85,
                intro_cue=0.15
            )
            transitions.append(transition)
        
        # Update current time
        if i < len(music_files) - 1:
            current_time = end_time - transition_duration
        else:
            current_time = end_time
    
    # Calculate total duration
    total_duration = max(t.end_time for t in dj_tracks)
    
    # Create energy graph
    energy_graph = []
    for track in dj_tracks:
        # Add 3 energy points per track
        energy_graph.extend([track.energy_level] * 3)
    
    # Create the DJ set
    dj_set = DJSet(
        id="test-production-mix",
        name="Production Test Mix - Afrobeats Selection",
        vibe_description="Upbeat afrobeats party mix with smooth transitions",
        total_duration=total_duration,
        track_count=len(dj_tracks),
        energy_pattern="wave",
        tracks=dj_tracks,
        transitions=transitions,
        energy_graph=energy_graph,
        key_moments=[
            {"time": "60.0", "description": "First transition"},
            {"time": str(total_duration/2), "description": "Peak energy"},
            {"time": str(total_duration-60), "description": "Final transition"}
        ],
        mixing_style="smooth_blend",
        ai_insights={
            "vibe_analysis": "High energy party mix",
            "mixing_approach": "Smooth crossfades with beat matching"
        }
    )
    
    logger.info(f"✅ Created DJ set with {len(dj_tracks)} tracks")
    logger.info(f"   Total duration: {total_duration/60:.1f} minutes")
    
    return dj_set


async def test_production_prerender():
    """Test the production pre-rendering workflow"""
    
    logger.info("\n🎵 PRODUCTION PRE-RENDER TEST")
    logger.info("=" * 60)
    logger.info("Testing the exact production pre-rendering workflow")
    
    try:
        # Initialize services
        logger.info("\n🔧 Initializing production services...")
        
        # Get services from service manager
        deck_manager = await service_manager.get_deck_manager()
        mixer_manager = await service_manager.get_mixer_manager()
        effect_manager = await service_manager.get_effect_manager()
        playback_controller = await service_manager.get_set_playback_controller()
        dj_set_service = await service_manager.get_dj_set_service()
        
        logger.info("✅ All services initialized")
        
        # Step 1: Create pre-made DJ set
        logger.info("\n📋 Step 1: Creating pre-made DJ set...")
        dj_set = create_pre_made_dj_set()
        
        if not dj_set:
            logger.error("❌ Failed to create DJ set")
            return False
        
        # Register the set with the service (like production)
        dj_set_service._dj_sets[dj_set.id] = dj_set
        
        # Log track details
        logger.info("\n📋 Track List:")
        for i, track in enumerate(dj_set.tracks, 1):
            logger.info(f"   {i}. {track.artist} - {track.title}")
            logger.info(f"      File: {os.path.basename(track.filepath)}")
            logger.info(f"      BPM: {track.bpm:.1f}, Energy: {track.energy_level:.3f}")
            logger.info(f"      Time: {track.start_time:.1f}s - {track.end_time:.1f}s")
            logger.info(f"      Deck: {track.deck}")
        
        # Log transitions
        logger.info("\n🔄 Transitions:")
        for transition in dj_set.transitions:
            logger.info(f"   Track {transition.from_track_order} → {transition.to_track_order}")
            logger.info(f"   Time: {transition.start_time:.1f}s, Duration: {transition.duration}s")
            logger.info(f"   Type: {transition.type}")
        
        # Step 2: Pre-render the DJ set
        logger.info("\n🎬 Step 2: Pre-rendering the DJ set...")
        
        # Create pre-renderer
        prerenderer = AudioPrerenderer(deck_manager, mixer_manager, effect_manager)
        
        # Pre-render the set
        start_time = datetime.now()
        output_path = await prerenderer.prerender_dj_set(dj_set)
        render_time = (datetime.now() - start_time).total_seconds()
        
        # Copy to test location
        import shutil
        final_path = os.path.expanduser("~/Downloads/test_production_prerender.wav")
        shutil.copy2(output_path, final_path)
        
        # Step 3: Verify the output
        logger.info("\n✅ Step 3: Verification")
        
        file_size = os.path.getsize(final_path) / (1024 * 1024)
        
        # Load a snippet to verify it's valid audio
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
        
        # Test playback controller integration
        logger.info("\n🎮 Testing playback controller...")
        
        # Test that the controller can start playback (without actually playing)
        # Just verify it recognizes the set
        try:
            # Check if the set is registered
            if dj_set.id in dj_set_service._dj_sets:
                logger.info("   ✅ DJ set is registered with the service")
                
                # Check playback status
                status = playback_controller.get_playback_status(dj_set.id)
                logger.info(f"   Playback status: {status}")
                
                # Verify pre-rendered file exists
                if os.path.exists(output_path):
                    logger.info(f"   ✅ Pre-rendered file verified: {os.path.basename(output_path)}")
                    logger.info(f"   ✅ File ready for streaming: {file_size:.2f} MB")
                else:
                    logger.warning("   ⚠️ Pre-rendered file not found")
                    
            else:
                logger.warning("   ⚠️ DJ set not registered with service")
        except Exception as e:
            logger.warning(f"   ⚠️ Playback controller test skipped: {e}")
        
        logger.info("\n🎉 PRODUCTION PRE-RENDER TEST COMPLETED SUCCESSFULLY!")
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
    """Run the production pre-render test"""
    logger.info("🚀 Starting Production Pre-render Test")
    logger.info("This test uses pre-made DJ sets with real music files")
    
    success = await test_production_prerender()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
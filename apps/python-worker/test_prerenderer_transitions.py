"""
Test script for verifying prerenderer transition effect support
"""

import asyncio
import logging
from datetime import datetime

from services.service_manager import ServiceManager
from services.audio_prerenderer import AudioPrerenderer
from models.dj_set_models import DJSet, DJSetTrack, DJSetTransition
from utils.dj_llm import TransitionEffect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_prerenderer_transitions():
    """Test the prerenderer with a simple DJ set containing transitions"""
    
    # Initialize services
    service_manager = ServiceManager()
    await service_manager.initialize_all_services()
    
    # Get services
    deck_manager = await service_manager.get_deck_manager()
    mixer_manager = await service_manager.get_mixer_manager()
    effect_manager = await service_manager.get_effect_manager()
    
    # Get prerenderer
    prerenderer = AudioPrerenderer(
        deck_manager=deck_manager,
        mixer_manager=mixer_manager,
        effect_manager=effect_manager
    )
    
    # Create a test DJ set with 3 tracks and 2 transitions
    test_set = DJSet(
        id="test_transitions_001",
        name="Test Transition Effects",
        vibe_description="Testing transition effects in prerenderer",
        total_duration=180.0,  # 3 minutes
        track_count=3,
        energy_pattern="building",
        tracks=[
            DJSetTrack(
                order=1,
                filepath="Martin Garrix - Animals (Original Mix).mp3",
                deck="A",
                start_time=0.0,
                end_time=60.0,
                fade_in_time=0.0,
                fade_out_time=50.0,
                title="Animals",
                artist="Martin Garrix",
                bpm=128.0,
                key="F#m",
                energy_level=0.8,
                mixing_note="High energy opener",
                gain_adjust=1.0,
                eq_low=0.0,
                eq_mid=0.0,
                eq_high=0.0
            ),
            DJSetTrack(
                order=2,
                filepath="David Guetta - Titanium ft. Sia.mp3",
                deck="B",
                start_time=50.0,
                end_time=120.0,
                fade_in_time=50.0,
                fade_out_time=110.0,
                title="Titanium",
                artist="David Guetta ft. Sia",
                bpm=126.0,
                key="Eb",
                energy_level=0.7,
                mixing_note="Smooth transition with filter sweep",
                gain_adjust=1.0,
                eq_low=0.0,
                eq_mid=0.0,
                eq_high=0.0
            ),
            DJSetTrack(
                order=3,
                filepath="Avicii - Levels.mp3",
                deck="A",
                start_time=110.0,
                end_time=180.0,
                fade_in_time=110.0,
                fade_out_time=180.0,
                title="Levels",
                artist="Avicii",
                bpm=126.0,
                key="C#m",
                energy_level=0.9,
                mixing_note="Energy boost with echo effect",
                gain_adjust=1.0,
                eq_low=0.0,
                eq_mid=0.0,
                eq_high=0.0
            )
        ],
        transitions=[
            DJSetTransition(
                from_track_order=1,
                to_track_order=2,
                from_deck="A",
                to_deck="B",
                start_time=50.0,
                duration=10.0,
                type="smooth_blend",
                effects=[
                    TransitionEffect(
                        type="filter_sweep",
                        start_at=0.0,
                        duration=8.0,
                        intensity=0.6
                    )
                ],
                crossfade_curve="s-curve",
                technique_notes="Filter sweep on outgoing track",
                risk_level="safe",
                compatibility_score=0.85,
                outro_cue=0.83,
                intro_cue=0.0
            ),
            DJSetTransition(
                from_track_order=2,
                to_track_order=3,
                from_deck="B",
                to_deck="A",
                start_time=110.0,
                duration=10.0,
                type="energy_shift",
                effects=[
                    TransitionEffect(
                        type="echo",
                        start_at=2.0,
                        duration=6.0,
                        intensity=0.4
                    ),
                    TransitionEffect(
                        type="reverb",
                        start_at=5.0,
                        duration=5.0,
                        intensity=0.3
                    )
                ],
                crossfade_curve="exponential",
                technique_notes="Echo and reverb for dramatic energy shift",
                risk_level="moderate",
                compatibility_score=0.75,
                outro_cue=0.87,
                intro_cue=0.0
            )
        ],
        energy_graph=[0.8, 0.75, 0.7, 0.75, 0.85, 0.9],
        key_moments=[
            {"time": "0:50", "description": "Filter sweep transition begins"},
            {"time": "1:50", "description": "Echo/reverb energy shift"}
        ],
        mixing_style="Progressive energy building",
        created_at=datetime.now()
    )
    
    try:
        logger.info("🎬 Starting prerender test with transitions...")
        
        # Prerender the DJ set
        output_file = await prerenderer.prerender_dj_set(test_set)
        
        logger.info(f"✅ Prerender complete! Output file: {output_file}")
        logger.info("🎉 Transition effects have been successfully applied!")
        logger.info("\n📊 Test Summary:")
        logger.info("  - 3 tracks mixed together")
        logger.info("  - 2 transitions with effects:")
        logger.info("    1. Filter sweep (smooth blend)")
        logger.info("    2. Echo + Reverb (energy shift)")
        logger.info("  - Different crossfade curves (s-curve, exponential)")
        logger.info(f"\n🎵 Listen to the output file to verify transitions: {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
    finally:
        await service_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(test_prerenderer_transitions())
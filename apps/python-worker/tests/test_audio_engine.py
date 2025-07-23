#!/usr/bin/env python3
"""
Basic tests for audio engine functionality (no file loading)
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from services.audio_engine import AudioEngine, AudioDeckState
from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager
from services.effect_manager import EffectManager


@pytest_asyncio.fixture
async def mock_deck_manager():
    """Create mock deck manager"""
    manager = Mock(spec=DeckManager)
    manager.get_deck_state = AsyncMock(return_value={
        "id": "A",
        "status": "empty",
        "is_playing": False,
        "volume": 1.0,
        "gain": 1.0,
        "tempo_adjust": 0.0,
        "eq_low": 0.0,
        "eq_mid": 0.0,
        "eq_high": 0.0,
    })
    return manager


@pytest_asyncio.fixture
async def mock_mixer_manager():
    """Create mock mixer manager"""
    manager = Mock(spec=MixerManager)
    manager.get_mixer_state = AsyncMock(return_value={
        "crossfader": 0.0,
        "master_volume": 1.0,
    })
    return manager


@pytest_asyncio.fixture
async def mock_effect_manager():
    """Create mock effect manager"""
    manager = Mock(spec=EffectManager)
    manager.get_deck_effects = Mock(return_value=None)
    return manager


@pytest_asyncio.fixture
async def audio_engine(mock_deck_manager, mock_mixer_manager, mock_effect_manager):
    """Create audio engine with mocked dependencies"""
    engine = AudioEngine(
        deck_manager=mock_deck_manager,
        mixer_manager=mock_mixer_manager,
        effect_manager=mock_effect_manager,
        sample_rate=44100,
        buffer_size=1024
    )
    return engine


@pytest.mark.asyncio
async def test_audio_engine_initialization(audio_engine):
    """Test audio engine initializes correctly"""
    assert audio_engine.sample_rate == 44100
    assert audio_engine.buffer_size == 1024
    assert not audio_engine._running
    assert len(audio_engine._audio_decks) == 4
    assert all(deck_id in audio_engine._audio_decks for deck_id in ["A", "B", "C", "D"])


@pytest.mark.asyncio
async def test_audio_engine_start_stop(audio_engine):
    """Test starting and stopping audio engine"""
    # Start engine
    await audio_engine.start()
    assert audio_engine._running
    assert audio_engine._processing_thread is not None
    assert audio_engine._processing_thread.is_alive()
    
    # Stop engine
    await audio_engine.stop()
    assert not audio_engine._running
    
    # Wait for thread to stop
    await asyncio.sleep(0.1)
    assert not audio_engine._processing_thread.is_alive()


@pytest.mark.asyncio
async def test_get_deck_position(audio_engine):
    """Test getting deck position"""
    # Initial position should be 0
    position = audio_engine.get_deck_position("A")
    assert position == 0.0
    
    # Set some audio data
    import numpy as np
    audio_engine._audio_decks["A"].audio_data = np.zeros((2, 44100))  # 1 second of audio
    audio_engine._audio_decks["A"].position_frames = 22050  # Half way
    
    position = audio_engine.get_deck_position("A")
    assert position == 0.5


@pytest.mark.asyncio
async def test_seek_deck(audio_engine):
    """Test seeking deck position"""
    import numpy as np
    
    # Set some audio data
    audio_engine._audio_decks["A"].audio_data = np.zeros((2, 44100))  # 1 second
    
    # Seek to 75%
    audio_engine.seek_deck("A", 0.75)
    
    position = audio_engine.get_deck_position("A")
    assert abs(position - 0.75) < 0.01  # Allow small rounding error


@pytest.mark.asyncio
async def test_audio_stream_generator(audio_engine):
    """Test audio stream generator produces buffers"""
    await audio_engine.start()
    
    # Get a few buffers
    buffers_received = 0
    async for buffer in audio_engine.get_stream_generator():
        assert buffer is not None
        assert buffer.shape == (2, 1024)  # Stereo, buffer size
        buffers_received += 1
        
        if buffers_received >= 3:
            break
    
    await audio_engine.stop()
    assert buffers_received >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
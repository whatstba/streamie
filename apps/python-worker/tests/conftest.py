"""
Shared test fixtures and configuration for pytest.
"""

import pytest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
import numpy as np
import soundfile as sf

# Import the FastAPI app
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def async_test_client():
    """Create an async test client for the FastAPI app."""
    from httpx import AsyncClient

    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_audio_file(temp_dir):
    """Create a synthetic audio file for testing."""
    # Create a simple sine wave audio file
    duration = 5.0  # seconds
    sample_rate = 44100
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)

    # Add some variation to make it more realistic
    audio_data += 0.1 * np.sin(2 * np.pi * frequency * 2 * t)

    file_path = os.path.join(temp_dir, "test_track.wav")
    sf.write(file_path, audio_data, sample_rate)

    return file_path


@pytest.fixture
def mock_audio_files(temp_dir):
    """Create multiple synthetic audio files with different characteristics."""
    files = []

    # Different BPMs and frequencies to simulate different tracks
    track_specs = [
        {"name": "track_120bpm.wav", "bpm": 120, "frequency": 440},
        {"name": "track_128bpm.wav", "bpm": 128, "frequency": 523},
        {"name": "track_140bpm.wav", "bpm": 140, "frequency": 659},
    ]

    for spec in track_specs:
        duration = 10.0
        sample_rate = 44100

        # Create a beat pattern based on BPM
        beat_duration = 60.0 / spec["bpm"]
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Base tone
        audio_data = 0.3 * np.sin(2 * np.pi * spec["frequency"] * t)

        # Add beat pulses
        for beat_time in np.arange(0, duration, beat_duration):
            beat_idx = int(beat_time * sample_rate)
            if beat_idx < len(audio_data):
                # Create a kick drum-like pulse
                pulse_length = int(0.1 * sample_rate)
                pulse = np.exp(-10 * np.linspace(0, 1, pulse_length))
                audio_data[beat_idx : beat_idx + pulse_length] += pulse[
                    : min(pulse_length, len(audio_data) - beat_idx)
                ]

        file_path = os.path.join(temp_dir, spec["name"])
        sf.write(file_path, audio_data, sample_rate)
        files.append(file_path)

    return files


@pytest.fixture
def mock_db(temp_dir):
    """Create a temporary SQLite database for testing."""
    db_path = os.path.join(temp_dir, "test_tracks.db")

    # Create engine and tables
    from utils.sqlite_db import Base

    engine_test = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine_test)

    return db_path


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls."""
    with patch("openai.ChatCompletion.create") as mock_create:
        mock_create.return_value = {
            "choices": [{"message": {"content": "Mocked AI response"}}]
        }
        yield mock_create


@pytest.fixture
def mock_langchain():
    """Mock LangChain/LangGraph components."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_instance = Mock()
        mock_instance.invoke = AsyncMock(return_value=Mock(content="Mocked response"))
        mock_chat.return_value = mock_instance
        yield mock_chat


@pytest.fixture
def sample_track_data():
    """Sample track data for testing."""
    return {
        "filename": "test_track.mp3",
        "filepath": "/test/test_track.mp3",
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "duration": 180.5,
        "genre": "Electronic",
        "year": "2024",
        "has_artwork": True,
        "bpm": 128.0,
        "beat_times": [0.0, 0.469, 0.938, 1.406],
        "energy": 0.75,
        "mood_aggressive": 0.2,
        "mood_happy": 0.8,
        "mood_relaxed": 0.6,
        "mood_sad": 0.1,
    }


@pytest.fixture
def mock_vibe_request():
    """Sample vibe playlist request."""
    return {
        "vibe": "uplifting progressive house for a sunset beach party",
        "num_tracks": 5,
        "duration_minutes": 30,
    }


@pytest.fixture
def mock_dj_agent_response():
    """Mock response from DJ agent."""
    return {
        "playlist": [
            {
                "filename": "track1.mp3",
                "title": "Sunset Vibes",
                "artist": "Beach House DJ",
                "bpm": 124,
                "energy": 0.7,
                "reason": "Perfect opener with uplifting melodies",
            },
            {
                "filename": "track2.mp3",
                "title": "Ocean Breeze",
                "artist": "Coastal Sound",
                "bpm": 126,
                "energy": 0.75,
                "reason": "Smooth progression maintaining the vibe",
            },
        ],
        "thinking_process": [
            "Analyzing vibe: uplifting, progressive house, sunset, beach",
            "Searching for tracks with 120-128 BPM range",
            "Selecting tracks with positive energy and beach vibes",
        ],
    }


# Add context about disabled endpoints
"""
Note: The AI router endpoints are currently disabled in main.py (line 41).
These endpoints provide advanced DJ functionality:
- /ai/analyze-vibe - Analyzes the musical vibe/mood of a track
- /ai/generate-playlist - Creates intelligent playlists based on criteria
- /ai/suggest-next-track - Recommends the next track based on current playing
- /ai/rate-transition - Evaluates how well two tracks mix together
- /ai/mixing-insights - Provides mixing tips and pattern analysis

These were likely disabled during the migration from MongoDB to SQLite
or due to API cost considerations during development.
"""

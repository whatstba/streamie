"""
Test helper functions and utilities.
"""
import os
import json
from typing import Dict, List, Any
from unittest.mock import Mock
import numpy as np


def create_mock_audio_analysis(bpm: float = 128.0, duration: float = 180.0) -> Dict[str, Any]:
    """Create a mock audio analysis result."""
    beat_interval = 60.0 / bpm
    num_beats = int(duration / beat_interval)
    beat_times = [i * beat_interval for i in range(num_beats)]
    
    return {
        "bpm": bpm,
        "tempo": bpm,
        "duration": duration,
        "beats": beat_times,
        "beat_times": beat_times,
        "energy": np.random.uniform(0.5, 0.9),
        "danceability": np.random.uniform(0.6, 0.95),
        "loudness": np.random.uniform(-20, -5)
    }


def create_mock_file_metadata(
    title: str = "Test Track",
    artist: str = "Test Artist",
    duration: float = 180.0
) -> Dict[str, Any]:
    """Create mock file metadata."""
    return {
        "title": title,
        "artist": artist,
        "album": "Test Album",
        "date": "2024",
        "genre": "Electronic",
        "duration": duration,
        "bitrate": 320000,
        "sample_rate": 44100
    }


def create_mock_mutagen_file() -> Mock:
    """Create a mock mutagen File object."""
    mock_file = Mock()
    mock_file.info.length = 180.0
    mock_file.info.bitrate = 320000
    mock_file.info.sample_rate = 44100
    
    # Mock ID3 tags
    mock_file.tags = {
        "TIT2": Mock(text=["Test Track"]),
        "TPE1": Mock(text=["Test Artist"]),
        "TALB": Mock(text=["Test Album"]),
        "TDRC": Mock(text=["2024"]),
        "TCON": Mock(text=["Electronic"])
    }
    
    # Mock APIC (artwork) frame
    mock_artwork = Mock()
    mock_artwork.data = b"fake_image_data"
    mock_artwork.mime = "image/jpeg"
    mock_file.tags["APIC:"] = mock_artwork
    
    return mock_file


def create_mock_openai_response(content: str) -> Dict[str, Any]:
    """Create a mock OpenAI API response."""
    return {
        "id": "mock-response-id",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 150,
            "total_tokens": 250
        }
    }


def create_mock_langchain_message(content: str) -> Mock:
    """Create a mock LangChain message."""
    mock_message = Mock()
    mock_message.content = content
    return mock_message


def assert_track_analysis_valid(analysis: Dict[str, Any]) -> None:
    """Assert that a track analysis result has all required fields."""
    required_fields = ["bpm", "beats", "duration"]
    for field in required_fields:
        assert field in analysis, f"Missing required field: {field}"
    
    assert isinstance(analysis["bpm"], (int, float))
    assert 50 <= analysis["bpm"] <= 200, "BPM out of reasonable range"
    
    assert isinstance(analysis["beats"], list)
    assert len(analysis["beats"]) > 0, "No beats detected"
    
    assert isinstance(analysis["duration"], (int, float))
    assert analysis["duration"] > 0, "Invalid duration"


def assert_vibe_playlist_valid(playlist: List[Dict[str, Any]]) -> None:
    """Assert that a vibe playlist result is valid."""
    assert isinstance(playlist, list)
    assert len(playlist) > 0, "Empty playlist"
    
    for track in playlist:
        assert "filename" in track
        assert "title" in track
        assert "artist" in track
        assert "bpm" in track
        assert isinstance(track["bpm"], (int, float))
        
        # Check BPM progression is smooth
        if len(playlist) > 1:
            bpms = [t["bpm"] for t in playlist]
            for i in range(1, len(bpms)):
                bpm_diff = abs(bpms[i] - bpms[i-1])
                assert bpm_diff <= 6, f"BPM jump too large: {bpm_diff}"


def create_test_db_track(
    filename: str,
    bpm: float = 128.0,
    energy: float = 0.7,
    **kwargs
) -> Dict[str, Any]:
    """Create a test track entry for database."""
    track = {
        "filename": filename,
        "filepath": f"/test/{filename}",
        "title": kwargs.get("title", filename.replace(".mp3", "").title()),
        "artist": kwargs.get("artist", "Test Artist"),
        "album": kwargs.get("album", "Test Album"),
        "duration": kwargs.get("duration", 180.0),
        "bpm": bpm,
        "energy": energy,
        "genre": kwargs.get("genre", "Electronic"),
        "year": kwargs.get("year", "2024"),
        "has_artwork": kwargs.get("has_artwork", True)
    }
    
    # Add mood values
    moods = ["acoustic", "aggressive", "electronic", "happy", "party", "relaxed", "sad"]
    for mood in moods:
        track[f"mood_{mood}"] = kwargs.get(f"mood_{mood}", np.random.uniform(0, 1))
    
    return track


def compare_tracks(track1: Dict[str, Any], track2: Dict[str, Any]) -> Dict[str, float]:
    """Compare two tracks for compatibility."""
    bpm_diff = abs(track1["bpm"] - track2["bpm"])
    energy_diff = abs(track1.get("energy", 0.5) - track2.get("energy", 0.5))
    
    # Calculate mood similarity
    mood_fields = [k for k in track1.keys() if k.startswith("mood_")]
    mood_similarity = 0
    if mood_fields:
        for field in mood_fields:
            if field in track2:
                mood_similarity += 1 - abs(track1[field] - track2[field])
        mood_similarity /= len(mood_fields)
    
    return {
        "bpm_difference": bpm_diff,
        "energy_difference": energy_diff,
        "mood_similarity": mood_similarity,
        "compatibility_score": (1 - bpm_diff/10) * 0.4 + (1 - energy_diff) * 0.3 + mood_similarity * 0.3
    }
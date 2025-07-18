"""
Integration tests for DJ Agent and vibe-based playlist generation.
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
import json
import asyncio
from typing import Dict, Any

from tests.fixtures.mock_data import (
    MOCK_TRACKS_DB,
    MOCK_OPENAI_VIBE_ANALYSIS,
    MOCK_DJ_AGENT_THINKING,
    MOCK_LANGGRAPH_STATE
)
from tests.utils.helpers import (
    assert_vibe_playlist_valid,
    create_mock_langchain_message,
    create_test_db_track
)


class TestDJAgentFlow:
    """Test DJ Agent and vibe-based playlist generation."""
    
    @pytest.mark.integration
    async def test_generate_vibe_playlist(self, test_client, mock_langchain, mock_db):
        """Test generating a playlist based on vibe description."""
        request_data = {
            "vibe": "uplifting progressive house for a sunset beach party",
            "num_tracks": 5,
            "duration_minutes": 30
        }
        
        # Mock the database to return test tracks
        with patch('utils.sqlite_db.get_tracks_by_criteria') as mock_get_tracks:
            mock_get_tracks.return_value = MOCK_TRACKS_DB
            
            # Mock LangGraph agent execution
            with patch('agents.dj_agent.DJAgent') as mock_dj_agent:
                mock_agent = Mock()
                mock_agent.generate_playlist = AsyncMock()
                mock_agent.generate_playlist.return_value = {
                    "playlist": [
                        {
                            "filename": track["filename"],
                            "title": track["title"],
                            "artist": track["artist"],
                            "bpm": track["bpm"],
                            "energy": track["energy"],
                            "reason": f"Good fit for {request_data['vibe']}"
                        }
                        for track in MOCK_TRACKS_DB[:5]
                    ],
                    "thinking_process": MOCK_DJ_AGENT_THINKING
                }
                mock_dj_agent.return_value = mock_agent
                
                response = test_client.post("/ai/generate-vibe-playlist", json=request_data)
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert "playlist" in data
                assert "thinking_process" in data
                assert len(data["playlist"]) == 5
                
                # Validate playlist
                assert_vibe_playlist_valid(data["playlist"])
                
                # Check thinking process
                assert len(data["thinking_process"]) > 0
                assert any("analyze_vibe" in step["step"] for step in data["thinking_process"])
    
    @pytest.mark.integration
    async def test_vibe_playlist_streaming(self, test_client, mock_langchain):
        """Test streaming AI thinking process during playlist generation."""
        request_params = {
            "vibe": "dark techno for late night warehouse party",
            "num_tracks": 3
        }
        
        with patch('agents.dj_agent.DJAgent') as mock_dj_agent:
            mock_agent = Mock()
            
            # Mock streaming responses
            async def mock_stream():
                steps = [
                    {"step": "analyze_vibe", "output": "Analyzing: dark techno, late night, warehouse"},
                    {"step": "search_tracks", "output": "Searching for tracks with dark, driving energy"},
                    {"step": "select_tracks", "output": "Found 3 perfect tracks"}
                ]
                for step in steps:
                    yield f"data: {json.dumps(step)}\n\n"
                    await asyncio.sleep(0.1)
                yield "data: [DONE]\n\n"
            
            mock_agent.stream_generation = mock_stream
            mock_dj_agent.return_value = mock_agent
            
            # Test streaming endpoint
            response = test_client.get(
                "/ai/generate-vibe-playlist-stream",
                params=request_params
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # Parse streaming response
            lines = response.text.strip().split('\n\n')
            assert len(lines) >= 3
            
            # Verify each step
            for line in lines[:-1]:  # Skip [DONE]
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    assert "step" in data
                    assert "output" in data
    
    @pytest.mark.integration
    async def test_dj_agent_energy_patterns(self, test_client, mock_langchain, mock_db):
        """Test DJ agent respects energy patterns in playlist generation."""
        # Test different energy patterns
        energy_patterns = [
            ("build up energy for peak time", "build_up"),
            ("maintain high energy throughout", "peak_time"),
            ("cool down after intense set", "cool_down"),
            ("create a journey with waves", "wave")
        ]
        
        for vibe_desc, expected_pattern in energy_patterns:
            request_data = {
                "vibe": vibe_desc,
                "num_tracks": 4,
                "duration_minutes": 20
            }
            
            with patch('agents.dj_agent.DJAgent') as mock_dj_agent:
                mock_agent = Mock()
                mock_agent.generate_playlist = AsyncMock()
                
                # Create tracks with appropriate energy progression
                if expected_pattern == "build_up":
                    energies = [0.5, 0.65, 0.8, 0.95]
                elif expected_pattern == "cool_down":
                    energies = [0.9, 0.75, 0.6, 0.4]
                elif expected_pattern == "peak_time":
                    energies = [0.9, 0.95, 0.9, 0.95]
                else:  # wave
                    energies = [0.6, 0.8, 0.6, 0.8]
                
                mock_playlist = []
                for i, energy in enumerate(energies):
                    track = create_test_db_track(
                        f"track_{i}.mp3",
                        bpm=125 + i,
                        energy=energy
                    )
                    mock_playlist.append(track)
                
                mock_agent.generate_playlist.return_value = {
                    "playlist": mock_playlist,
                    "energy_pattern": expected_pattern,
                    "thinking_process": [{"step": "energy_analysis", "output": f"Using {expected_pattern} pattern"}]
                }
                mock_dj_agent.return_value = mock_agent
                
                response = test_client.post("/ai/generate-vibe-playlist", json=request_data)
                assert response.status_code == 200
                
                data = response.json()
                
                # Verify energy progression matches pattern
                playlist_energies = [t["energy"] for t in data["playlist"]]
                
                if expected_pattern == "build_up":
                    assert all(playlist_energies[i] <= playlist_energies[i+1] 
                             for i in range(len(playlist_energies)-1))
                elif expected_pattern == "cool_down":
                    assert all(playlist_energies[i] >= playlist_energies[i+1] 
                             for i in range(len(playlist_energies)-1))
    
    @pytest.mark.integration
    async def test_dj_agent_bpm_progression(self, test_client, mock_langchain):
        """Test DJ agent maintains smooth BPM progression."""
        request_data = {
            "vibe": "progressive house journey from 124 to 128 BPM",
            "num_tracks": 5,
            "duration_minutes": 25
        }
        
        with patch('agents.dj_agent.DJAgent') as mock_dj_agent:
            mock_agent = Mock()
            mock_agent.generate_playlist = AsyncMock()
            
            # Create playlist with smooth BPM progression
            bpms = [124, 125, 126, 127, 128]
            mock_playlist = []
            for i, bpm in enumerate(bpms):
                track = create_test_db_track(
                    f"progressive_{i}.mp3",
                    bpm=bpm,
                    energy=0.7 + (i * 0.05)
                )
                mock_playlist.append(track)
            
            mock_agent.generate_playlist.return_value = {
                "playlist": mock_playlist,
                "thinking_process": [
                    {"step": "bpm_analysis", "output": "Target BPM range: 124-128"},
                    {"step": "verify_transitions", "output": "All BPM transitions <= 2 BPM"}
                ]
            }
            mock_dj_agent.return_value = mock_agent
            
            response = test_client.post("/ai/generate-vibe-playlist", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            playlist = data["playlist"]
            
            # Verify smooth BPM progression
            for i in range(1, len(playlist)):
                bpm_diff = abs(playlist[i]["bpm"] - playlist[i-1]["bpm"])
                assert bpm_diff <= 2, f"BPM jump too large between tracks {i-1} and {i}"
    
    @pytest.mark.integration
    async def test_dj_agent_error_handling(self, test_client):
        """Test DJ agent handles errors gracefully."""
        request_data = {
            "vibe": "test error handling",
            "num_tracks": 5
        }
        
        # Test OpenAI API error
        with patch('agents.dj_agent.DJAgent') as mock_dj_agent:
            mock_agent = Mock()
            mock_agent.generate_playlist = AsyncMock(
                side_effect=Exception("OpenAI API error: Rate limit exceeded")
            )
            mock_dj_agent.return_value = mock_agent
            
            response = test_client.post("/ai/generate-vibe-playlist", json=request_data)
            
            assert response.status_code == 500
            assert "error" in response.json()
            assert "OpenAI API error" in response.json()["detail"]
    
    @pytest.mark.integration
    async def test_dj_agent_with_constraints(self, test_client, mock_langchain):
        """Test DJ agent respects additional constraints."""
        request_data = {
            "vibe": "vocal progressive house, no aggressive tracks",
            "num_tracks": 4,
            "duration_minutes": 20,
            "constraints": {
                "min_bpm": 122,
                "max_bpm": 126,
                "required_moods": ["happy", "uplifting"],
                "excluded_moods": ["aggressive", "dark"]
            }
        }
        
        with patch('agents.dj_agent.DJAgent') as mock_dj_agent:
            mock_agent = Mock()
            mock_agent.generate_playlist = AsyncMock()
            
            # Create tracks that meet constraints
            mock_playlist = []
            for i in range(4):
                track = create_test_db_track(
                    f"vocal_prog_{i}.mp3",
                    bpm=124 + (i * 0.5),  # Stay within BPM range
                    energy=0.7,
                    mood_happy=0.8,
                    mood_aggressive=0.1,  # Low aggression
                    mood_dark=0.1,  # Low darkness
                    vocal_presence=True
                )
                mock_playlist.append(track)
            
            mock_agent.generate_playlist.return_value = {
                "playlist": mock_playlist,
                "thinking_process": [
                    {"step": "apply_constraints", "output": "Filtering tracks: BPM 122-126, vocal, non-aggressive"}
                ]
            }
            mock_dj_agent.return_value = mock_agent
            
            response = test_client.post("/ai/generate-vibe-playlist", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify all tracks meet constraints
            for track in data["playlist"]:
                assert 122 <= track["bpm"] <= 126
                assert track.get("mood_aggressive", 0) < 0.3
                assert track.get("mood_dark", 0) < 0.3
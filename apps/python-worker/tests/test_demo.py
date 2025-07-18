"""
Demonstration test showing the testing framework capabilities.
"""
import pytest
from unittest.mock import patch, Mock
from tests.fixtures.mock_data import MOCK_TRACKS_DB, MOCK_BEAT_TRACK_RESPONSE
from tests.utils.helpers import create_mock_audio_analysis, assert_track_analysis_valid


class TestDemoIntegration:
    """Demonstration of integration testing patterns."""
    
    def test_mock_librosa_analysis(self):
        """Test mocking audio analysis with librosa."""
        with patch('utils.librosa.run_beat_track') as mock_beat_track:
            # Set up the mock to return our test data
            mock_beat_track.return_value = MOCK_BEAT_TRACK_RESPONSE
            
            # Import and call the function
            from utils.librosa import run_beat_track
            result = run_beat_track("/fake/audio.mp3")
            
            # Verify the mock was called and returned expected data
            assert result["tempo"] == 128.0
            assert len(result["beats"]) == 8
            mock_beat_track.assert_called_once_with("/fake/audio.mp3")
    
    def test_mock_database_operations(self):
        """Test mocking database operations."""
        with patch('utils.sqlite_db.get_sqlite_db') as mock_get_db:
            # Mock the database connection
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [
                (1, "sunset_vibes.mp3", "/music/sunset_vibes.mp3", "Sunset Vibes", "Beach House DJ", 124.0)
            ]
            mock_get_db.return_value = mock_conn
            
            # Simulate using the database
            from utils.sqlite_db import get_sqlite_db
            conn = get_sqlite_db()
            cursor = conn.cursor()
            cursor.fetchall()
            
            # Verify results
            assert mock_cursor.fetchall.called
            results = mock_cursor.fetchall.return_value
            assert len(results) == 1
            assert results[0][3] == "Sunset Vibes"  # title
            assert results[0][5] == 124.0  # bpm
    
    def test_mock_openai_response(self):
        """Test mocking OpenAI API calls."""
        with patch('openai.ChatCompletion.create') as mock_create:
            # Mock the OpenAI response
            mock_create.return_value = {
                "choices": [{
                    "message": {
                        "content": "uplifting, energetic, beach vibes"
                    }
                }]
            }
            
            # Simulate calling OpenAI
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Analyze this vibe"}]
            )
            
            # Verify response
            content = response["choices"][0]["message"]["content"]
            assert "uplifting" in content
            assert "beach" in content
    
    @pytest.mark.asyncio
    async def test_async_dj_agent(self):
        """Test async DJ agent operations."""
        from unittest.mock import AsyncMock
        
        # Create an async mock for the DJ agent
        mock_agent = Mock()
        mock_agent.generate_playlist = AsyncMock()
        mock_agent.generate_playlist.return_value = {
            "playlist": [MOCK_TRACKS_DB[0]],
            "thinking_process": ["Analyzing vibe", "Selecting tracks"]
        }
        
        # Call the async method
        result = await mock_agent.generate_playlist("test vibe")
        
        # Verify results
        assert len(result["playlist"]) == 1
        assert result["playlist"][0]["title"] == "Sunset Vibes"
        assert len(result["thinking_process"]) == 2
    
    def test_helper_functions(self):
        """Test the helper utility functions."""
        # Test audio analysis creation
        analysis = create_mock_audio_analysis(bpm=120, duration=200)
        assert analysis["bpm"] == 120
        assert analysis["duration"] == 200
        assert len(analysis["beats"]) > 0
        
        # Test validation
        assert_track_analysis_valid(analysis)
    
    def test_error_handling(self):
        """Test error handling patterns."""
        with patch('utils.librosa.run_beat_track') as mock_beat_track:
            # Simulate an error
            mock_beat_track.side_effect = Exception("Audio file corrupted")
            
            # Test error handling
            from utils.librosa import run_beat_track
            with pytest.raises(Exception) as exc_info:
                run_beat_track("/corrupted/file.mp3")
            
            assert "Audio file corrupted" in str(exc_info.value)
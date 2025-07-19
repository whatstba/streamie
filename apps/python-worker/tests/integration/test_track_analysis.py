"""
Integration tests for track analysis functionality.
"""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path

from tests.fixtures.mock_data import (
    MOCK_BEAT_TRACK_RESPONSE,
    MOCK_MOOD_ANALYSIS,
    MOCK_SERATO_DATA,
)
from tests.utils.helpers import create_mock_mutagen_file


class TestTrackAnalysis:
    """Test track analysis endpoints and functionality."""

    @pytest.mark.integration
    async def test_analyze_single_track(self, test_client, mock_audio_file):
        """Test analyzing a single track."""
        # Mock the librosa beat tracking
        with patch("utils.librosa.run_beat_track") as mock_beat_track:
            mock_beat_track.return_value = MOCK_BEAT_TRACK_RESPONSE

            # Mock mutagen file reading
            with patch("mutagen.File") as mock_mutagen:
                mock_mutagen.return_value = create_mock_mutagen_file()

                # Mock Essentia mood analysis
                with patch("utils.essentia_utils.analyze_mood") as mock_mood:
                    mock_mood.return_value = MOCK_MOOD_ANALYSIS

                    # Get the filename from the path
                    filename = Path(mock_audio_file).name

                    # Test the analysis endpoint
                    response = test_client.get(f"/track/{filename}/analysis")

                    assert response.status_code == 200
                    data = response.json()

                    # Verify response structure
                    assert "bpm" in data
                    assert data["bpm"] == 128.0
                    assert "beats" in data
                    assert len(data["beats"]) > 0
                    assert "duration" in data
                    assert "metadata" in data
                    assert data["metadata"]["title"] == "Test Track"
                    assert data["metadata"]["artist"] == "Test Artist"

                    # Verify mood data is included
                    assert "mood_analysis" in data
                    assert data["mood_analysis"]["mood_happy"] == 0.8

    @pytest.mark.integration
    async def test_batch_analyze_tracks(self, test_client, mock_audio_files, temp_dir):
        """Test batch analysis of multiple tracks."""
        # Create request with file paths
        request_data = {
            "directory": temp_dir,
            "tracks": [Path(f).name for f in mock_audio_files],
        }

        with patch("utils.librosa.run_beat_track") as mock_beat_track:
            # Return different BPMs for each track
            mock_beat_track.side_effect = [
                {"tempo": 120.0, "beats": [0, 0.5, 1.0], "beat_times": [0, 0.5, 1.0]},
                {
                    "tempo": 128.0,
                    "beats": [0, 0.469, 0.938],
                    "beat_times": [0, 0.469, 0.938],
                },
                {
                    "tempo": 140.0,
                    "beats": [0, 0.429, 0.857],
                    "beat_times": [0, 0.429, 0.857],
                },
            ]

            with patch("mutagen.File") as mock_mutagen:
                mock_mutagen.return_value = create_mock_mutagen_file()

                response = test_client.post("/tracks/batch-analyze", json=request_data)

                assert response.status_code == 200
                data = response.json()

                assert "results" in data
                assert len(data["results"]) == 3

                # Verify each track was analyzed
                bpms = [track["bpm"] for track in data["results"]]
                assert bpms == [120.0, 128.0, 140.0]

    @pytest.mark.integration
    async def test_track_analysis_with_corrupted_file(self, test_client, temp_dir):
        """Test handling of corrupted audio files."""
        # Create a corrupted file
        corrupted_file = Path(temp_dir) / "corrupted.mp3"
        corrupted_file.write_text("This is not an audio file")

        with patch("utils.librosa.run_beat_track") as mock_beat_track:
            mock_beat_track.side_effect = Exception("Cannot read audio file")

            response = test_client.get(f"/track/{corrupted_file.name}/analysis")

            # Should handle error gracefully
            assert response.status_code == 500
            assert "error" in response.json()

    @pytest.mark.integration
    async def test_track_analysis_caching(self, test_client, mock_audio_file, mock_db):
        """Test that analysis results are cached in database."""
        filename = Path(mock_audio_file).name

        with patch("utils.librosa.run_beat_track") as mock_beat_track:
            mock_beat_track.return_value = MOCK_BEAT_TRACK_RESPONSE

            with patch("mutagen.File") as mock_mutagen:
                mock_mutagen.return_value = create_mock_mutagen_file()

                # First request - should analyze
                response1 = test_client.get(f"/track/{filename}/analysis")
                assert response1.status_code == 200
                assert mock_beat_track.call_count == 1

                # Second request - should use cache
                response2 = test_client.get(f"/track/{filename}/analysis")
                assert response2.status_code == 200
                # Beat track should not be called again
                assert mock_beat_track.call_count == 1

                # Data should be the same
                assert response1.json() == response2.json()

    @pytest.mark.integration
    async def test_track_listing_with_analysis(
        self, test_client, mock_audio_files, temp_dir
    ):
        """Test listing tracks with optional analysis."""
        with patch("os.path.expanduser") as mock_expand:
            mock_expand.return_value = temp_dir

            with patch("utils.librosa.run_beat_track") as mock_beat_track:
                mock_beat_track.return_value = MOCK_BEAT_TRACK_RESPONSE

                with patch("mutagen.File") as mock_mutagen:
                    mock_mutagen.return_value = create_mock_mutagen_file()

                    # List without analysis
                    response = test_client.get("/tracks")
                    assert response.status_code == 200
                    data = response.json()
                    assert len(data) == 3

                    # Verify basic info
                    for track in data:
                        assert "filename" in track
                        assert "filepath" in track
                        assert "bpm" not in track  # No analysis requested

                    # List with analysis
                    response = test_client.get("/tracks?analyze=true")
                    assert response.status_code == 200
                    data = response.json()

                    # Should have BPM data now
                    for track in data:
                        assert "bpm" in track
                        assert track["bpm"] == 128.0

    @pytest.mark.integration
    async def test_serato_data_extraction(self, test_client, mock_audio_file):
        """Test extraction of Serato cue points and beatgrid."""
        filename = Path(mock_audio_file).name

        with patch("utils.librosa.run_beat_track") as mock_beat_track:
            mock_beat_track.return_value = MOCK_BEAT_TRACK_RESPONSE

            with patch("mutagen.File") as mock_mutagen:
                mock_file = create_mock_mutagen_file()
                # Add Serato tags
                mock_file.tags["GEOB:Serato Markers2"] = Mock(data=b"fake_serato_data")
                mock_mutagen.return_value = mock_file

                with patch("utils.serato_reader.read_serato_data") as mock_serato:
                    mock_serato.return_value = MOCK_SERATO_DATA

                    response = test_client.get(f"/track/{filename}/analysis")
                    assert response.status_code == 200

                    data = response.json()
                    assert "serato_data" in data
                    assert "hot_cues" in data["serato_data"]
                    assert len(data["serato_data"]["hot_cues"]) == 3
                    assert data["serato_data"]["hot_cues"][0]["name"] == "Intro"

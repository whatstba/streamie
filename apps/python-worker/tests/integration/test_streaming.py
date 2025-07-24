"""
Integration tests for audio streaming functionality.
"""

import pytest
from unittest.mock import patch, Mock, mock_open
from pathlib import Path


class TestAudioStreaming:
    """Test audio file streaming endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stream_audio_file(self, test_client, mock_audio_file):
        """Test streaming an entire audio file."""
        filename = Path(mock_audio_file).name

        # Mock file operations
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=1000000):  # 1MB file
                with patch("builtins.open", mock_open(read_data=b"fake audio data")):
                    response = test_client.get(f"/track/{filename}/stream")

                    assert response.status_code == 200
                    assert response.headers["content-type"] == "audio/mpeg"
                    assert "content-length" in response.headers
                    assert response.headers["accept-ranges"] == "bytes"
                    assert response.content == b"fake audio data"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stream_with_range_request(self, test_client, mock_audio_file):
        """Test streaming with HTTP range requests."""
        filename = Path(mock_audio_file).name
        file_size = 1000000  # 1MB

        # Create fake audio data
        fake_data = b"A" * file_size

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=file_size):
                with patch("builtins.open", mock_open(read_data=fake_data)):
                    # Test range request for first 100KB
                    headers = {"Range": "bytes=0-102399"}
                    response = test_client.get(
                        f"/track/{filename}/stream", headers=headers
                    )

                    assert response.status_code == 206  # Partial Content
                    assert (
                        response.headers["content-range"]
                        == f"bytes 0-102399/{file_size}"
                    )
                    assert len(response.content) == 102400

                    # Test range request for middle portion
                    headers = {"Range": "bytes=500000-599999"}
                    response = test_client.get(
                        f"/track/{filename}/stream", headers=headers
                    )

                    assert response.status_code == 206
                    assert (
                        response.headers["content-range"]
                        == f"bytes 500000-599999/{file_size}"
                    )
                    assert len(response.content) == 100000

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stream_nonexistent_file(self, test_client):
        """Test streaming a file that doesn't exist."""
        with patch("os.path.exists", return_value=False):
            response = test_client.get("/track/nonexistent.mp3/stream")

            assert response.status_code == 404
            assert "detail" in response.json()
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stream_invalid_range(self, test_client, mock_audio_file):
        """Test streaming with invalid range requests."""
        filename = Path(mock_audio_file).name
        file_size = 1000000

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=file_size):
                # Test range beyond file size
                headers = {"Range": "bytes=2000000-3000000"}
                response = test_client.get(f"/track/{filename}/stream", headers=headers)

                assert response.status_code == 416  # Range Not Satisfiable
                assert response.headers["content-range"] == f"bytes */{file_size}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stream_multiple_ranges(self, test_client, mock_audio_file):
        """Test handling of multiple range requests (not supported)."""
        filename = Path(mock_audio_file).name

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=1000000):
                # Multiple ranges (not supported by most implementations)
                headers = {"Range": "bytes=0-999,2000-2999"}
                response = test_client.get(f"/track/{filename}/stream", headers=headers)

                # Should either return 200 (full content) or 206 (first range only)
                assert response.status_code in [200, 206]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_artwork(self, test_client, mock_audio_file):
        """Test extracting and serving album artwork."""
        filename = Path(mock_audio_file).name

        # Mock mutagen file with artwork
        mock_file = Mock()
        mock_file.tags = {
            "APIC:": Mock(data=b"\xff\xd8\xff\xe0fake_jpeg_data", mime="image/jpeg")
        }

        with patch("mutagen.File", return_value=mock_file):
            response = test_client.get(f"/track/{filename}/artwork")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/jpeg"
            assert response.content.startswith(b"\xff\xd8\xff\xe0")  # JPEG header

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_artwork_no_image(self, test_client, mock_audio_file):
        """Test handling tracks without artwork."""
        filename = Path(mock_audio_file).name

        # Mock mutagen file without artwork
        mock_file = Mock()
        mock_file.tags = {"TIT2": Mock(text=["Title Only"])}

        with patch("mutagen.File", return_value=mock_file):
            response = test_client.get(f"/track/{filename}/artwork")

            assert response.status_code == 404
            assert "No artwork found" in response.json()["detail"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_streaming(self, test_client, mock_audio_file):
        """Test handling concurrent streaming requests."""
        filename = Path(mock_audio_file).name
        file_size = 1000000

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=file_size):
                with patch("builtins.open", mock_open(read_data=b"A" * file_size)):
                    # Simulate multiple concurrent requests
                    responses = []
                    for i in range(5):
                        # Different ranges for each request
                        start = i * 100000
                        end = start + 99999
                        headers = {"Range": f"bytes={start}-{end}"}

                        response = test_client.get(
                            f"/track/{filename}/stream", headers=headers
                        )
                        responses.append(response)

                    # All requests should succeed
                    for response in responses:
                        assert response.status_code == 206
                        assert len(response.content) == 100000

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stream_different_audio_formats(self, test_client, temp_dir):
        """Test streaming various audio formats."""
        formats = [
            ("test.mp3", "audio/mpeg"),
            ("test.wav", "audio/wav"),
            ("test.flac", "audio/flac"),
            ("test.m4a", "audio/mp4"),
            ("test.ogg", "audio/ogg"),
        ]

        for filename, expected_mime in formats:
            file_path = Path(temp_dir) / filename
            file_path.write_bytes(b"fake audio data")

            with patch("os.path.exists", return_value=True):
                with patch("os.path.getsize", return_value=1000):
                    with patch(
                        "builtins.open", mock_open(read_data=b"fake audio data")
                    ):
                        response = test_client.get(f"/track/{filename}/stream")

                        assert response.status_code == 200
                        assert response.headers["content-type"] == expected_mime

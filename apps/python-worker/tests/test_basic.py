"""
Basic tests to verify the testing framework is working.
"""
import pytest
from unittest.mock import Mock, patch
from tests.fixtures.mock_data import MOCK_TRACKS_DB, MOCK_BEAT_TRACK_RESPONSE


def test_mock_data_available():
    """Test that mock data is accessible."""
    assert len(MOCK_TRACKS_DB) > 0
    assert MOCK_BEAT_TRACK_RESPONSE["tempo"] == 128.0


def test_basic_mocking():
    """Test basic mocking functionality."""
    mock_func = Mock(return_value={"bpm": 128})
    result = mock_func()
    assert result["bpm"] == 128
    mock_func.assert_called_once()


@pytest.mark.asyncio
async def test_async_test():
    """Test async test support."""
    import asyncio
    result = await asyncio.sleep(0, result="test")
    assert result == "test"


def test_patching():
    """Test patching functionality."""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        import os
        assert os.path.exists("/fake/path") is True
        mock_exists.assert_called_with("/fake/path")
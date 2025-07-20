"""
Basic test to verify pytest setup is working correctly.
"""

import pytest


def test_pytest_setup():
    """Test that pytest is configured correctly."""
    assert True


def test_fixtures_available(test_client, mock_audio_file, sample_track_data):
    """Test that fixtures are available and working."""
    assert test_client is not None
    assert mock_audio_file is not None
    assert sample_track_data is not None
    assert "filename" in sample_track_data


def test_fastapi_client(test_client):
    """Test that FastAPI test client works."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI DJ Backend is running"}


@pytest.mark.asyncio
async def test_async_support():
    """Test that async tests work."""
    import asyncio

    await asyncio.sleep(0.1)
    assert True


def test_mocking_works():
    """Test that mocking is configured."""
    from unittest.mock import Mock

    mock = Mock()
    mock.return_value = "mocked"
    assert mock() == "mocked"

"""
Audio Streaming Router - WebSocket endpoints for real-time audio streaming from the mixing engine.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional, Any
import asyncio
import json
import logging
import numpy as np
import struct
from datetime import datetime

from services.service_manager import service_manager
from services.audio_engine import AudioEngine
from services.audio_streamer import AudioStreamer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])


class AudioStreamConfig(BaseModel):
    """Configuration for audio streaming"""

    format: str = "wav"  # wav, mp3, opus
    quality: str = "high"  # low, medium, high
    sample_rate: int = 44100
    channels: int = 2
    bit_depth: int = 16


class AudioEngineStatus(BaseModel):
    """Status of the audio engine"""

    is_running: bool
    buffer_size: int
    sample_rate: int
    active_decks: int
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


# Dependency to get audio engine
async def get_audio_engine() -> AudioEngine:
    """Get the audio engine instance"""
    engine = await service_manager.get_audio_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Audio engine not available")
    return engine


# Dependency to get audio streamer
async def get_audio_streamer() -> AudioStreamer:
    """Get the audio streamer instance"""
    # For now, create a new instance
    # TODO: Get from service manager
    engine = await get_audio_engine()
    dj_toolset = engine.dj_toolset if hasattr(engine, "dj_toolset") else None
    return AudioStreamer(dj_toolset)


@router.get("/status", response_model=AudioEngineStatus)
async def get_audio_engine_status(
    audio_engine: AudioEngine = Depends(get_audio_engine),
) -> AudioEngineStatus:
    """Get the current status of the audio engine"""
    # Count active decks
    active_decks = 0
    for deck_id in ["A", "B", "C", "D"]:
        if audio_engine._audio_decks[deck_id].is_playing:
            active_decks += 1

    return AudioEngineStatus(
        is_running=audio_engine._running,
        buffer_size=audio_engine.buffer_size,
        sample_rate=audio_engine.sample_rate,
        active_decks=active_decks,
    )


@router.post("/start")
async def start_audio_engine(
    audio_engine: AudioEngine = Depends(get_audio_engine),
) -> Dict[str, Any]:
    """Start the audio processing engine"""
    await audio_engine.start()
    return {"status": "started", "message": "Audio engine started successfully"}


@router.post("/stop")
async def stop_audio_engine(
    audio_engine: AudioEngine = Depends(get_audio_engine),
) -> Dict[str, Any]:
    """Stop the audio processing engine"""
    await audio_engine.stop()
    return {"status": "stopped", "message": "Audio engine stopped successfully"}


# TEMPORARILY DISABLED - FIXING WEBSOCKET ISSUES
# WebSocket endpoints commented out to prevent server hangs


@router.get("/stream/http")
async def stream_audio_http():
    """HTTP streaming endpoint for audio (alternative to WebSocket)"""
    try:
        audio_engine = await service_manager.get_audio_engine()
        if not audio_engine:
            raise HTTPException(status_code=503, detail="Audio engine not available")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Audio engine error: {str(e)}")

    async def audio_generator():
        """Generate audio chunks for HTTP streaming"""
        # Send WAV header
        header = create_wav_header_http(44100, 2, 16)
        yield header

        # Stream audio
        async for audio_buffer in audio_engine.get_stream_generator():
            if audio_buffer is not None and audio_buffer.size > 0:
                # Convert to 16-bit PCM
                audio_16bit = (audio_buffer * 32767).astype(np.int16)

                # Interleave stereo channels
                interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
                interleaved[0::2] = audio_16bit[0]
                interleaved[1::2] = audio_16bit[1]

                yield interleaved.tobytes()

    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )


def create_wav_header_http(sample_rate: int, channels: int, bit_depth: int) -> bytes:
    """Create WAV file header for HTTP streaming"""
    header = bytearray()

    # RIFF chunk
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 0x7FFFFFFF - 8))  # File size
    header.extend(b"WAVE")

    # fmt chunk
    header.extend(b"fmt ")
    header.extend(struct.pack("<I", 16))  # Chunk size
    header.extend(struct.pack("<H", 1))  # PCM format
    header.extend(struct.pack("<H", channels))
    header.extend(struct.pack("<I", sample_rate))
    byte_rate = sample_rate * channels * (bit_depth // 8)
    header.extend(struct.pack("<I", byte_rate))
    block_align = channels * (bit_depth // 8)
    header.extend(struct.pack("<H", block_align))
    header.extend(struct.pack("<H", bit_depth))

    # data chunk
    header.extend(b"data")
    header.extend(struct.pack("<I", 0x7FFFFFFF - 44))  # Data size

    return bytes(header)


@router.get("/decks/{deck_id}/position")
async def get_deck_position(
    deck_id: str, audio_engine: AudioEngine = Depends(get_audio_engine)
) -> Dict[str, Any]:
    """Get the current playback position of a deck from the audio engine"""
    if deck_id not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Invalid deck ID")

    position = audio_engine.get_deck_position(deck_id)

    return {
        "deck_id": deck_id,
        "position_normalized": position,
        "timestamp": datetime.utcnow().isoformat(),
    }

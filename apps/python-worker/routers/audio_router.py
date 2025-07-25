"""
Audio Streaming Router - WebSocket endpoints for real-time audio streaming from the mixing engine.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel
from typing import Dict, Optional, Any
import logging
import numpy as np
import struct
from datetime import datetime
import asyncio
import os

from services.service_manager import service_manager
from services.audio_engine import AudioEngine
from services.audio_streamer import AudioStreamer
from services.chunked_audio_streamer import ChunkedAudioStreamer
from services.audio_prerenderer import AudioPrerenderer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])


async def get_prerenderer() -> AudioPrerenderer:
    """Get the audio prerenderer from service manager"""
    return await service_manager.get_audio_prerenderer()


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


# Dependency to get chunked audio streamer
async def get_chunked_audio_streamer() -> ChunkedAudioStreamer:
    """Get the chunked audio streamer instance"""
    engine = await get_audio_engine()
    return ChunkedAudioStreamer(engine)


@router.get("/status", response_model=AudioEngineStatus)
async def get_audio_engine_status(
    audio_engine: AudioEngine = Depends(get_audio_engine),
) -> AudioEngineStatus:
    """Get the current status of the audio engine"""
    # If engine is not available, return error status
    if not audio_engine:
        logger.error("🎵 Audio engine is None in status endpoint")
        return AudioEngineStatus(
            is_running=False,
            buffer_size=1024,
            sample_rate=44100,
            active_decks=0,
        )
    
    # Count active decks
    active_decks = 0
    try:
        for deck_id in ["A", "B", "C", "D"]:
            if audio_engine._audio_decks[deck_id].is_playing:
                active_decks += 1
    except Exception as e:
        logger.error(f"🎵 Error counting active decks: {e}")

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


@router.post("/prerender/{set_id}")
async def prerender_dj_set(
    set_id: str,
    prerenderer: AudioPrerenderer = Depends(get_prerenderer)
) -> Dict[str, Any]:
    """Pre-render a DJ set to a complete WAV file"""
    logger.info(f"🎬 Pre-render request for DJ set: {set_id}")
    
    try:
        # Get DJ set from service
        dj_set_service = await service_manager.get_dj_set_service()
        dj_set = dj_set_service.get_dj_set(set_id)
        
        if not dj_set:
            raise HTTPException(status_code=404, detail=f"DJ set {set_id} not found")
            
        # Start pre-rendering
        filepath = await prerenderer.prerender_dj_set(dj_set)
        
        return {
            "status": "completed",
            "set_id": set_id,
            "filepath": filepath,
            "message": "DJ set pre-rendered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Pre-render failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pre-render failed: {str(e)}")


@router.get("/prerender/{set_id}/status")
async def get_prerender_status(
    set_id: str,
    prerenderer: AudioPrerenderer = Depends(get_prerenderer)
) -> Dict[str, Any]:
    """Get pre-rendering status"""
    progress = prerenderer.get_render_progress(set_id)
    filepath = prerenderer.get_rendered_file(set_id)
    
    return {
        "set_id": set_id,
        "progress": progress,
        "is_complete": progress == 1.0,
        "has_error": progress == -1.0,
        "filepath": filepath
    }


@router.get("/stream/prerendered/{set_id}")
async def stream_prerendered_audio(
    set_id: str,
    request: Request,
    prerenderer: AudioPrerenderer = Depends(get_prerenderer)
):
    """Stream a pre-rendered DJ set WAV file"""
    stream_start = datetime.now()
    logger.info(f"🎵 Stream request for pre-rendered set: {set_id}")
    logger.info(f"   Request time: {stream_start.isoformat()}")
    
    # Check if file exists
    filepath = prerenderer.get_rendered_file(set_id)
    logger.info(f"   Cached filepath: {filepath}")
    
    if not filepath or not os.path.exists(filepath):
        logger.warning(f"   ⚠️ Pre-rendered file not found, will render on demand")
        
        # Try to pre-render if not available
        try:
            dj_set_service = await service_manager.get_dj_set_service()
            dj_set = dj_set_service.get_dj_set(set_id)
            
            if not dj_set:
                logger.error(f"   ❌ DJ set {set_id} not found in service")
                raise HTTPException(status_code=404, detail=f"DJ set {set_id} not found")
                
            logger.info(f"🎬 Pre-rendering on demand for set: {set_id}")
            logger.info(f"   DJ set name: {dj_set.name}")
            logger.info(f"   Track count: {len(dj_set.tracks)}")
            
            render_start = datetime.now()
            filepath = await prerenderer.prerender_dj_set(dj_set)
            render_duration = (datetime.now() - render_start).total_seconds()
            
            logger.info(f"   ✅ On-demand rendering complete in {render_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to pre-render: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Full error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to pre-render: {str(e)}")
    else:
        logger.info(f"   ✅ Using existing pre-rendered file")
    
    # Validate file
    if not os.path.exists(filepath):
        logger.error(f"   ❌ File doesn't exist after rendering: {filepath}")
        raise HTTPException(status_code=500, detail="Pre-rendered file not found")
        
    file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
    logger.info(f"   File size: {file_size:.1f} MB")
    logger.info(f"   File path: {filepath}")
    
    total_prep_time = (datetime.now() - stream_start).total_seconds()
    logger.info(f"   Total preparation time: {total_prep_time:.2f}s")
    
    # Check for Range header
    range_header = request.headers.get("range")
    file_size = os.path.getsize(filepath)
    
    if range_header:
        logger.info(f"   Range request: {range_header}")
        
        # Parse range header (e.g., "bytes=0-1023")
        try:
            range_str = range_header.replace("bytes=", "")
            range_parts = range_str.split("-")
            
            start = int(range_parts[0]) if range_parts[0] else 0
            end = int(range_parts[1]) if range_parts[1] else file_size - 1
            
            # Ensure valid range
            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            
            logger.info(f"   Serving bytes {start}-{end} of {file_size}")
            
            # Open file and seek to start position
            with open(filepath, "rb") as f:
                f.seek(start)
                content_length = end - start + 1
                content = f.read(content_length)
            
            # Return partial content response
            headers = {
                "Content-Type": "audio/wav",
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
            }
            
            return Response(
                content=content,
                status_code=206,  # Partial Content
                headers=headers,
                media_type="audio/wav"
            )
            
        except Exception as e:
            logger.error(f"   Error parsing range header: {e}")
            # Fall through to serve full file
    
    logger.info(f"   Sending full file...")
    
    # Return the complete WAV file with Accept-Ranges header
    return FileResponse(
        filepath,
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )


# TEMPORARILY DISABLED - FIXING WEBSOCKET ISSUES
# WebSocket endpoints commented out to prevent server hangs


@router.get("/stream/chunked/{set_id}")
async def stream_audio_chunked(
    set_id: str,
    chunked_streamer: ChunkedAudioStreamer = Depends(get_chunked_audio_streamer)
):
    """
    Stream audio in fixed-size WAV chunks for reliable browser playback.
    Each chunk is a complete WAV file with proper headers.
    """
    logger.info(f"🎵 Chunked audio stream requested for set {set_id}")
    
    # Validate that the set exists and is playing
    from services.service_manager import service_manager
    playback_controller = await service_manager.get_set_playback_controller()
    
    if not playback_controller.is_playing(set_id):
        logger.error(f"🎵 Set {set_id} is not currently playing")
        raise HTTPException(
            status_code=404, 
            detail=f"DJ set {set_id} is not currently playing"
        )
    
    async def chunked_generator():
        """Generate fixed-size WAV chunks"""
        try:
            async for chunk in chunked_streamer.stream_chunked_audio(set_id):
                yield chunk
        except Exception as e:
            logger.error(f"🎵 Chunked streaming error: {e}")
            raise
    
    return StreamingResponse(
        chunked_generator(),
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept-Encoding",
            # Don't set Content-Length for streaming
        },
    )


@router.get("/stream/file/{set_id}")
async def get_rendered_audio_file(
    set_id: str,
    prerenderer: AudioPrerenderer = Depends(get_prerenderer)
):
    """
    Get the pre-rendered audio file if available.
    Returns 404 if still rendering.
    """
    filepath = prerenderer.get_rendered_file(set_id)
    
    if not filepath or not os.path.exists(filepath):
        # Also check chunked streamer as fallback
        chunked_streamer = ChunkedAudioStreamer(await service_manager.get_audio_engine())
        filepath = chunked_streamer.get_rendered_file(set_id)
        
        if not filepath or not os.path.exists(filepath):
            raise HTTPException(
                status_code=404,
                detail="Audio file not ready yet"
            )
    
    # Get file size
    file_size = os.path.getsize(filepath)
    
    # Create file response with proper headers
    return FileResponse(
        filepath,
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/stream/status/{set_id}")
async def get_stream_status(
    set_id: str,
    chunked_streamer: ChunkedAudioStreamer = Depends(get_chunked_audio_streamer)
):
    """Get the status of audio streaming/rendering for a DJ set"""
    is_rendered = chunked_streamer.get_rendered_file(set_id) is not None
    render_progress = chunked_streamer.get_render_progress(set_id)
    
    return {
        "set_id": set_id,
        "is_rendered": is_rendered,
        "render_progress_seconds": render_progress,
        "file_ready": is_rendered,
        "file_url": f"/api/audio/stream/file/{set_id}" if is_rendered else None
    }


@router.get("/stream/http")
async def stream_audio_http():
    """HTTP streaming endpoint for audio (alternative to WebSocket)"""
    logger.info("🎵 Audio stream endpoint called")
    
    try:
        audio_engine = await service_manager.get_audio_engine()
        if not audio_engine:
            logger.error("🎵 No audio engine available from service manager")
            raise HTTPException(status_code=503, detail="Audio engine not available")
        
        logger.info(f"🎵 Audio engine status: running={audio_engine._running}")
        
        # Check if the audio engine is actually running
        if not audio_engine._running:
            logger.warning("🎵 Audio engine is not running! Starting it now...")
            try:
                await audio_engine.start()
                logger.info("🎵 Audio engine started successfully")
                
                # Give it a moment to initialize
                await asyncio.sleep(0.5)
                
                # Verify it's running
                if not audio_engine._running:
                    raise Exception("Audio engine failed to start properly")
                    
            except Exception as start_error:
                logger.error(f"🎵 Failed to start audio engine: {start_error}")
                raise HTTPException(status_code=503, detail="Audio engine is not running and failed to start")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🎵 Error getting audio engine: {e}")
        raise HTTPException(status_code=503, detail=f"Audio engine error: {str(e)}")

    async def audio_generator():
        """Generate audio chunks for HTTP streaming"""
        generator_start = datetime.now()
        try:
            logger.info("🎵 Starting audio streaming generator")
            logger.info(f"   Generator started at: {generator_start.isoformat()}")
            
            # Check audio engine state
            active_decks = 0
            for deck_id in ["A", "B", "C", "D"]:
                deck = audio_engine._audio_decks[deck_id]
                if deck.is_playing:
                    active_decks += 1
                    logger.info(f"🎵 Deck {deck_id} is active and playing")
                    logger.info(f"   Track: {deck.current_track if hasattr(deck, 'current_track') else 'Unknown'}")
            
            if active_decks == 0:
                logger.warning("🎵 No active decks found! Audio will be silence.")
            else:
                logger.info(f"🎵 Total active decks: {active_decks}")
            
            # Send WAV header
            header = create_wav_header_http(44100, 2, 16)
            logger.info(f"🎵 Sending WAV header: {len(header)} bytes")
            yield header

            # Stream audio
            buffer_count = 0
            silence_count = 0
            last_log_time = datetime.now()
            bytes_sent = len(header)
            
            async for audio_buffer in audio_engine.get_stream_generator():
                if audio_buffer is not None and audio_buffer.size > 0:
                    buffer_count += 1
                    
                    # Check if buffer is silence
                    is_silence = np.max(np.abs(audio_buffer)) < 0.001
                    if is_silence:
                        silence_count += 1
                    else:
                        if silence_count > 0:
                            logger.info(f"🎵 Had {silence_count} silence buffers, now getting audio!")
                        silence_count = 0
                    
                    # Log periodically (every 5 seconds)
                    current_time = datetime.now()
                    if (current_time - last_log_time).total_seconds() >= 5:
                        duration = (current_time - generator_start).total_seconds()
                        logger.info(f"🎵 Streaming status: {buffer_count} buffers sent, {bytes_sent / 1024 / 1024:.1f} MB, {duration:.1f}s elapsed")
                        logger.info(f"   Audio level: {'SILENCE' if is_silence else 'ACTIVE'}")
                        last_log_time = current_time
                        
                    # Convert to 16-bit PCM
                    audio_16bit = (audio_buffer * 32767).astype(np.int16)

                    # Interleave stereo channels
                    interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
                    interleaved[0::2] = audio_16bit[0]
                    interleaved[1::2] = audio_16bit[1]

                    chunk = interleaved.tobytes()
                    bytes_sent += len(chunk)
                    yield chunk
                else:
                    logger.warning("🎵 Got None buffer from audio engine")
                    
            total_duration = (datetime.now() - generator_start).total_seconds()
            logger.warning(f"🎵 Audio generator completed after {total_duration:.1f}s")
            logger.info(f"   Total buffers sent: {buffer_count}")
            logger.info(f"   Total data sent: {bytes_sent / 1024 / 1024:.1f} MB")
            
        except asyncio.CancelledError:
            logger.info("🎵 Audio generator cancelled by client")
            raise
        except Exception as e:
            logger.error(f"🎵 Error in audio generator: {e}", exc_info=True)
            logger.error(f"   Error occurred after {(datetime.now() - generator_start).total_seconds():.1f}s")
            raise

    logger.info("🎵 Creating StreamingResponse")
    
    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept-Encoding",
        },
    )


@router.get("/test-stream")
async def test_stream():
    """Test endpoint to verify streaming works"""
    async def generate():
        logger.info("🎵 Test stream generator started")
        for i in range(10):
            data = f"Test chunk {i}\n".encode()
            logger.info(f"🎵 Yielding test chunk {i}")
            yield data
            await asyncio.sleep(0.1)
        logger.info("🎵 Test stream generator completed")
    
    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/test-sine-wave")
async def test_sine_wave():
    """Test endpoint that generates a sine wave to verify audio streaming"""
    async def sine_generator():
        logger.info("🎵 Starting sine wave test")
        
        # WAV header
        header = create_wav_header_http(44100, 2, 16)
        yield header
        
        # Generate 5 seconds of 440Hz sine wave
        sample_rate = 44100
        frequency = 440  # A4 note
        duration = 5  # seconds
        
        samples_per_buffer = 1024
        total_samples = sample_rate * duration
        samples_generated = 0
        
        while samples_generated < total_samples:
            # Generate sine wave
            t = np.arange(samples_generated, min(samples_generated + samples_per_buffer, total_samples))
            sine_wave = np.sin(2 * np.pi * frequency * t / sample_rate) * 0.5
            
            # Convert to stereo
            stereo = np.stack([sine_wave, sine_wave])
            
            # Convert to 16-bit PCM
            audio_16bit = (stereo * 32767).astype(np.int16)
            
            # Interleave
            interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = audio_16bit[0]
            interleaved[1::2] = audio_16bit[1]
            
            yield interleaved.tobytes()
            samples_generated += samples_per_buffer
            
            # Small delay to simulate real-time
            await asyncio.sleep(0.01)
        
        logger.info("🎵 Sine wave test completed")
    
    return StreamingResponse(
        sine_generator(),
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/test-prerender")
async def test_prerender(
    prerenderer: AudioPrerenderer = Depends(get_prerenderer)
):
    """Test pre-rendering by creating a simple test audio file"""
    import tempfile
    from models.dj_set_models import DJSet, DJSetTrack
    
    logger.info("🎵 Creating test pre-rendered file")
    
    # Create a test DJ set with a sine wave "track"
    test_set = DJSet(
        id="test-prerender",
        name="Test Pre-render",
        duration=10.0,
        vibe_description="Test sine wave for pre-rendering",
        total_duration=10.0,
        track_count=1,
        energy_pattern="steady",
        transitions=[],
        energy_graph=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        key_moments=[],
        mixing_style="simple",
        tracks=[
            DJSetTrack(
                filepath="test_sine_wave.wav",  # Dummy path
                title="Test Sine Wave",
                artist="Test Artist",
                bpm=120.0,
                key="C",
                start_time=0.0,
                end_time=10.0,
                gain_adjust=1.0,
                eq_low=0.0,
                eq_mid=0.0,
                eq_high=0.0,
                order=1,
                deck="A",
                fade_in_time=0.0,
                fade_out_time=10.0,
                energy_level=0.5,
                mixing_note="Test mixing note"
            )
        ]
    )
    
    # Override the load_track method to generate a sine wave instead
    original_load_track = prerenderer.load_track
    def mock_load_track(filepath: str):
        logger.info(f"📁 Generating test sine wave for: {filepath}")
        # Generate 10 seconds of 440Hz sine wave
        sample_rate = 44100
        duration = 10.0
        t = np.arange(0, int(sample_rate * duration))
        frequency = 440.0
        sine_wave = np.sin(2 * np.pi * frequency * t / sample_rate) * 0.3
        stereo = np.stack([sine_wave, sine_wave])
        return stereo
    
    prerenderer.load_track = mock_load_track
    
    try:
        # Pre-render the test set
        filepath = await prerenderer.prerender_dj_set(test_set)
        
        # Copy to a fixed location for easy access
        import shutil
        fixed_path = os.path.expanduser("~/Downloads/test_prerender.wav")
        shutil.copy2(filepath, fixed_path)
        
        logger.info(f"🎵 Test file saved to: {fixed_path}")
        
        return {
            "status": "success",
            "message": f"Test pre-rendered file saved to: {fixed_path}",
            "original_path": filepath,
            "file_size_mb": os.path.getsize(filepath) / 1024 / 1024
        }
    finally:
        # Restore original method
        prerenderer.load_track = original_load_track


@router.get("/stream/simple")
async def stream_simple_audio():
    """Simplified audio streaming for debugging"""
    logger.info("🎵 Simple audio stream endpoint called")
    
    try:
        audio_engine = await service_manager.get_audio_engine()
        if not audio_engine or not audio_engine._running:
            # Return a simple WAV file with silence
            logger.warning("🎵 Audio engine not available, returning silence")
            
            def generate_silence():
                # WAV header for 1 second of silence
                header = create_wav_header_http(44100, 2, 16)
                yield header
                
                # 1 second of silence
                silence = np.zeros((2, 44100), dtype=np.int16)
                yield silence.tobytes()
            
            return StreamingResponse(
                generate_silence(),
                media_type="audio/wav",
                headers={
                    "Content-Type": "audio/wav",
                    "Access-Control-Allow-Origin": "*",
                }
            )
            
        # Normal audio streaming
        logger.info("🎵 Using audio engine for streaming")
        
        async def simple_generator():
            # Send WAV header
            header = create_wav_header_http(44100, 2, 16)
            yield header
            
            # Get just 10 buffers for testing
            buffer_count = 0
            async for buffer in audio_engine.get_stream_generator():
                if buffer_count >= 10:
                    break
                    
                # Convert to 16-bit PCM
                audio_16bit = (buffer * 32767).astype(np.int16)
                
                # Interleave stereo channels
                interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
                interleaved[0::2] = audio_16bit[0]
                interleaved[1::2] = audio_16bit[1]
                
                yield interleaved.tobytes()
                buffer_count += 1
                
            logger.info(f"🎵 Simple generator sent {buffer_count} buffers")
        
        return StreamingResponse(
            simple_generator(),
            media_type="audio/wav",
            headers={
                "Content-Type": "audio/wav",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        logger.error(f"🎵 Simple stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_wav_header_http(sample_rate: int, channels: int, bit_depth: int) -> bytes:
    """Create WAV file header for HTTP streaming"""
    # Use a reasonable size that browsers will accept
    # 1 hour of audio at given sample rate
    reasonable_size = 1 * 60 * 60 * sample_rate * channels * (bit_depth // 8)
    
    # Make sure it fits in 32-bit unsigned integer
    max_size = 0xFFFFFFF0  # Leave some room
    if reasonable_size > max_size:
        reasonable_size = max_size
    
    header = bytearray()

    # RIFF chunk
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", reasonable_size + 36))  # File size - 8
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
    header.extend(struct.pack("<I", reasonable_size))  # Data size

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

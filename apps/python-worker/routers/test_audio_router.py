"""
Test Audio Router - Simple streaming endpoints for debugging
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
import numpy as np
import struct
import logging
import os
import asyncio
import librosa

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["test"])


def create_simple_wav_header(sample_rate: int = 44100, channels: int = 2, bit_depth: int = 16) -> bytes:
    """Create a simple WAV header for streaming"""
    # Use a reasonable size that browsers will accept
    # 1 hour of audio at 44.1kHz stereo 16-bit (fits in 32-bit)
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
    header.extend(struct.pack("<H", 1))   # PCM format
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


@router.get("/instant-tone")
async def stream_instant_tone():
    """Stream a test tone immediately - no waiting, no complexity"""
    logger.info("🎵 Instant tone stream requested")
    
    async def tone_generator():
        # Send WAV header immediately
        yield create_simple_wav_header()
        
        # Generate 5 seconds of 440Hz sine wave
        sample_rate = 44100
        frequency = 440  # A4 note
        duration = 5  # seconds
        amplitude = 0.3  # 30% volume
        
        samples_per_chunk = 4410  # 0.1 second chunks
        total_samples = sample_rate * duration
        samples_generated = 0
        
        while samples_generated < total_samples:
            # Generate sine wave chunk
            t = np.arange(samples_generated, min(samples_generated + samples_per_chunk, total_samples))
            sine_wave = np.sin(2 * np.pi * frequency * t / sample_rate) * amplitude
            
            # Convert to stereo
            stereo = np.stack([sine_wave, sine_wave])
            
            # Convert to 16-bit PCM
            audio_16bit = (stereo * 32767).astype(np.int16)
            
            # Interleave
            interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = audio_16bit[0]
            interleaved[1::2] = audio_16bit[1]
            
            yield interleaved.tobytes()
            samples_generated += samples_per_chunk
            
            # Small async yield to prevent blocking
            await asyncio.sleep(0.001)
    
    return StreamingResponse(
        tone_generator(),
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/instant-file")
async def stream_instant_file(filepath: str = "/Users/lynscott/Downloads/09 M.I.A. (Clean).mp3"):
    """Stream a real audio file immediately"""
    logger.info(f"🎵 Instant file stream requested: {filepath}")
    
    if not os.path.exists(filepath):
        # Try a test file
        test_file = "/Users/lynscott/Downloads/09 M.I.A. (Clean).mp3"
        if os.path.exists(test_file):
            filepath = test_file
        else:
            raise HTTPException(status_code=404, detail="Audio file not found")
    
    async def file_generator():
        try:
            # Load audio file
            logger.info(f"🎵 Loading audio file: {filepath}")
            audio_data, sample_rate = librosa.load(filepath, sr=44100, mono=False)
            
            # Ensure stereo
            if audio_data.ndim == 1:
                audio_data = np.stack([audio_data, audio_data])
            elif audio_data.shape[0] > 2:
                audio_data = audio_data[:2]
            
            logger.info(f"🎵 Audio loaded: {audio_data.shape}")
            
            # Send WAV header
            yield create_simple_wav_header(sample_rate, 2, 16)
            
            # Stream audio in chunks
            chunk_size = 44100  # 1 second chunks
            total_samples = audio_data.shape[1]
            
            for i in range(0, total_samples, chunk_size):
                chunk = audio_data[:, i:i+chunk_size]
                
                # Convert to 16-bit PCM
                audio_16bit = (chunk * 32767).astype(np.int16)
                
                # Interleave
                interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
                interleaved[0::2] = audio_16bit[0]
                interleaved[1::2] = audio_16bit[1]
                
                yield interleaved.tobytes()
                
                # Small async yield
                await asyncio.sleep(0.001)
                
        except Exception as e:
            logger.error(f"🎵 Streaming error: {e}")
            raise
    
    return StreamingResponse(
        file_generator(),
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/chunked-tone")
async def stream_chunked_tone():
    """Stream test tone in fixed-size WAV chunks (browser-friendly)"""
    logger.info("🎵 Chunked tone stream requested")
    
    async def chunked_generator():
        # Generate 5-second chunks
        chunk_duration = 5.0
        sample_rate = 44100
        frequency = 440
        amplitude = 0.3
        
        chunk_samples = int(sample_rate * chunk_duration)
        
        for chunk_num in range(3):  # 3 chunks = 15 seconds total
            # Generate audio for this chunk
            t = np.arange(chunk_num * chunk_samples, (chunk_num + 1) * chunk_samples)
            sine_wave = np.sin(2 * np.pi * frequency * t / sample_rate) * amplitude
            
            # Convert to stereo
            stereo = np.stack([sine_wave, sine_wave])
            
            # Convert to 16-bit PCM
            audio_16bit = (stereo * 32767).astype(np.int16)
            
            # Interleave
            interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = audio_16bit[0]
            interleaved[1::2] = audio_16bit[1]
            
            audio_bytes = interleaved.tobytes()
            
            # Create complete WAV chunk with proper header
            header = bytearray()
            
            # RIFF chunk
            header.extend(b"RIFF")
            header.extend(struct.pack("<I", 36 + len(audio_bytes)))  # File size - 8
            header.extend(b"WAVE")
            
            # fmt chunk
            header.extend(b"fmt ")
            header.extend(struct.pack("<I", 16))  # Chunk size
            header.extend(struct.pack("<H", 1))   # PCM format
            header.extend(struct.pack("<H", 2))   # Channels
            header.extend(struct.pack("<I", sample_rate))
            byte_rate = sample_rate * 2 * 2  # stereo * 16-bit
            header.extend(struct.pack("<I", byte_rate))
            header.extend(struct.pack("<H", 4))  # Block align
            header.extend(struct.pack("<H", 16)) # Bit depth
            
            # data chunk
            header.extend(b"data")
            header.extend(struct.pack("<I", len(audio_bytes)))
            
            # Yield complete WAV file
            yield bytes(header) + audio_bytes
            
            logger.info(f"🎵 Sent chunk {chunk_num + 1} ({len(audio_bytes) / 1024:.1f} KB)")
            
            await asyncio.sleep(0.001)
    
    return StreamingResponse(
        chunked_generator(),
        media_type="audio/wav",
        headers={
            "Content-Type": "audio/wav",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )
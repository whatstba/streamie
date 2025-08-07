"""
Chunked Audio Streamer - Provides fixed-size WAV chunks for reliable browser streaming.
"""

import asyncio
import logging
import numpy as np
import struct
import io
from typing import AsyncGenerator, Optional, Dict, Tuple
import threading
import queue
import os
import tempfile
from datetime import datetime
import time

from services.audio_engine import AudioEngine

logger = logging.getLogger(__name__)


class ChunkedAudioStreamer:
    """
    Streams audio as a single WAV stream: one header, then raw PCM chunks.
    Also pre-renders the complete file in the background.
    """
    
    def __init__(self, audio_engine: AudioEngine, chunk_duration: float = 5.0):
        self.audio_engine = audio_engine
        self.chunk_duration = chunk_duration  # Duration of each chunk in seconds
        self.sample_rate = 44100
        self.channels = 2
        self.bit_depth = 16
        
        # Calculate chunk size in samples
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        self.chunk_frames = self.chunk_samples * self.channels * (self.bit_depth // 8)
        
        # Background rendering
        self._render_tasks: Dict[str, asyncio.Task] = {}
        self._rendered_files: Dict[str, str] = {}
        self._render_progress: Dict[str, float] = {}
        self._render_lock = threading.Lock()
        
        # Temporary directory for rendered files
        self.temp_dir = tempfile.mkdtemp(prefix="streamie_audio_")
        logger.info(f"🎵 ChunkedAudioStreamer initialized with temp dir: {self.temp_dir}")
        
    def create_wav_chunk_header(self, data_size: int) -> bytes:
        """Create a complete WAV header for a chunk with known size"""
        header = bytearray()
        
        # RIFF chunk
        header.extend(b"RIFF")
        header.extend(struct.pack("<I", 36 + data_size))  # File size - 8
        header.extend(b"WAVE")
        
        # fmt chunk
        header.extend(b"fmt ")
        header.extend(struct.pack("<I", 16))  # Chunk size
        header.extend(struct.pack("<H", 1))   # PCM format
        header.extend(struct.pack("<H", self.channels))
        header.extend(struct.pack("<I", self.sample_rate))
        byte_rate = self.sample_rate * self.channels * (self.bit_depth // 8)
        header.extend(struct.pack("<I", byte_rate))
        block_align = self.channels * (self.bit_depth // 8)
        header.extend(struct.pack("<H", block_align))
        header.extend(struct.pack("<H", self.bit_depth))
        
        # data chunk
        header.extend(b"data")
        header.extend(struct.pack("<I", data_size))
        
        return bytes(header)
    
    def _generate_test_tone(self) -> np.ndarray:
        """Generate a test tone when no real audio is available"""
        # Generate 440Hz sine wave (A4 note)
        samples = np.arange(self.audio_engine.buffer_size)
        frequency = 440.0
        sine_wave = np.sin(2 * np.pi * frequency * samples / self.sample_rate) * 0.1  # Low volume
        
        # Create stereo buffer
        stereo_buffer = np.stack([sine_wave, sine_wave]).astype(np.float32)
        logger.info(f"🎵 Generated test tone: {frequency}Hz")
        return stereo_buffer
    
    async def stream_chunked_audio(self, set_id: str) -> AsyncGenerator[bytes, None]:
        """
        Stream audio as one continuous WAV: send a single header first,
        then emit interleaved PCM chunks. Also accumulate audio for background rendering.
        """
        logger.info(f"🎵 Starting chunked audio stream for set {set_id}")
        
        # Initialize collections for background rendering
        all_audio_buffers = []  # Collect all buffers for rendering
        
        # Send a single WAV header up front for a large-but-safe data size
        # Use ~1 hour header to satisfy browsers without needing Content-Length
        header = self._create_stream_header()
        yield header

        # Stream PCM chunks
        chunk_count = 0
        audio_buffer = np.zeros((2, 0), dtype=np.float32)
        
        # Start streaming immediately
        logger.info(f"🎵 Starting stream immediately")
        
        async for buffer in self.audio_engine.get_stream_generator():
            if buffer is None:
                continue
                
            # Store buffer for background rendering
            all_audio_buffers.append(buffer.copy())
            
            # Accumulate audio for chunking
            audio_buffer = np.concatenate((audio_buffer, buffer), axis=1)
            
            # Check if we have enough for a PCM chunk
            while audio_buffer.shape[1] >= self.chunk_samples:
                # Extract chunk
                chunk_audio = audio_buffer[:, :self.chunk_samples]
                audio_buffer = audio_buffer[:, self.chunk_samples:]
                
                # Convert to 16-bit PCM
                audio_16bit = (chunk_audio * 32767).astype(np.int16)
                
                # Interleave stereo channels
                interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
                interleaved[0::2] = audio_16bit[0]
                interleaved[1::2] = audio_16bit[1]
                
                # Yield raw PCM payload (header already sent)
                audio_data = interleaved.tobytes()
                yield audio_data
                
                chunk_count += 1
                logger.info(f"🎵 Streamed PCM chunk {chunk_count} ({self.chunk_duration}s)")
                
                # Check if pre-rendered file is ready
                if self._is_render_complete(set_id):
                    logger.info(f"🎵 Pre-rendered file ready, switching to file streaming")
                    # Signal frontend to switch to file URL
                    # This is handled by frontend polling
                    return
        
        # Stream any remaining audio as final PCM chunk
        if audio_buffer.shape[1] > 0:
            # Pad to minimum size if needed
            if audio_buffer.shape[1] < self.sample_rate:  # Less than 1 second
                padding = self.sample_rate - audio_buffer.shape[1]
                audio_buffer = np.pad(audio_buffer, ((0, 0), (0, padding)), mode='constant')
            
            # Convert final chunk
            audio_16bit = (audio_buffer * 32767).astype(np.int16)
            interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = audio_16bit[0]
            interleaved[1::2] = audio_16bit[1]
            
            audio_data = interleaved.tobytes()
            yield audio_data
            
            logger.info(f"🎵 Streamed final PCM chunk ({audio_buffer.shape[1] / self.sample_rate:.1f}s)")
        
        # Now render the complete file in the background
        asyncio.create_task(self._render_from_buffers(set_id, all_audio_buffers))
    
    async def _render_from_buffers(self, set_id: str, audio_buffers: list):
        """Render the complete DJ set to a WAV file from collected buffers"""
        try:
            logger.info(f"🎵 Background render starting for set {set_id}")
            
            if not audio_buffers:
                logger.error(f"🎵 No audio buffers to render for set {set_id}")
                return
            
            # Concatenate all audio
            complete_audio = np.concatenate(audio_buffers, axis=1)
            total_samples = complete_audio.shape[1]
            
            # Convert to 16-bit PCM
            audio_16bit = (complete_audio * 32767).astype(np.int16)
            
            # Interleave stereo channels
            interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = audio_16bit[0]
            interleaved[1::2] = audio_16bit[1]
            
            # Create complete WAV file
            audio_data = interleaved.tobytes()
            wav_header = self.create_wav_chunk_header(len(audio_data))
            
            # Write to temporary file
            filename = f"djset_{set_id}_{int(time.time())}.wav"
            filepath = os.path.join(self.temp_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(wav_header)
                f.write(audio_data)
            
            # Store file path
            with self._render_lock:
                self._rendered_files[set_id] = filepath
                
            duration = total_samples / self.sample_rate
            file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
            logger.info(f"🎵 Background render complete: {filepath} ({duration:.1f}s, {file_size:.1f}MB)")
            
        except Exception as e:
            logger.error(f"🎵 Background render failed for set {set_id}: {e}")
            
    def _is_render_complete(self, set_id: str) -> bool:
        """Check if background rendering is complete"""
        with self._render_lock:
            return set_id in self._rendered_files
            
    def get_rendered_file(self, set_id: str) -> Optional[str]:
        """Get the path to the pre-rendered file if available"""
        with self._render_lock:
            return self._rendered_files.get(set_id)
            
    def get_render_progress(self, set_id: str) -> float:
        """Get rendering progress in seconds"""
        return self._render_progress.get(set_id, 0.0)
        
    def cleanup(self):
        """Clean up temporary files"""
        try:
            for filepath in self._rendered_files.values():
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"🎵 Cleaned up: {filepath}")
                    
            os.rmdir(self.temp_dir)
            logger.info(f"🎵 Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"🎵 Cleanup error: {e}")

    def _create_stream_header(self) -> bytes:
        """Create a single WAV header with a large reasonable data size (~1h)."""
        max_seconds = 60 * 60  # 1 hour
        data_size = max_seconds * self.sample_rate * self.channels * (self.bit_depth // 8)
        # Cap to avoid 32-bit overflow in header fields
        max_size = 0xFFFFFFF0
        if data_size > max_size:
            data_size = max_size
        return self.create_wav_chunk_header(data_size)
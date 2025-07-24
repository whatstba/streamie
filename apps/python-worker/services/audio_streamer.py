"""Audio streaming service for web output"""

import asyncio
import numpy as np
import struct
import logging
from typing import AsyncGenerator, Optional, Dict

from tools.dj_toolset import DJToolset

logger = logging.getLogger(__name__)


class AudioStreamer:
    """Handles audio streaming to web clients"""

    def __init__(self, dj_toolset: DJToolset):
        self.dj_toolset = dj_toolset
        self.sample_rate = 44100
        self.channels = 2
        self.bytes_per_sample = 2  # 16-bit

        # Streaming state
        self.is_streaming = False
        self.stream_queue = asyncio.Queue(maxsize=50)
        self.stream_task: Optional[asyncio.Task] = None

    async def start_streaming(self):
        """Start the audio streaming process"""
        if self.is_streaming:
            return

        self.is_streaming = True
        self.stream_task = asyncio.create_task(self._stream_processor())
        logger.info("Audio streaming started")

    async def stop_streaming(self):
        """Stop audio streaming"""
        self.is_streaming = False

        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass

        logger.info("Audio streaming stopped")

    async def _stream_processor(self):
        """Process audio from DJ toolset and queue for streaming"""
        while self.is_streaming:
            try:
                # Get audio buffer from DJ toolset
                audio_buffer = self.dj_toolset.get_audio_stream()

                if audio_buffer is not None:
                    # Convert to WAV format chunks
                    wav_chunk = self._convert_to_wav_chunk(audio_buffer)

                    # Queue for streaming
                    await self.stream_queue.put(wav_chunk)
                else:
                    # No audio available, wait a bit
                    await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                await asyncio.sleep(0.1)

    def _convert_to_wav_chunk(self, audio_buffer: np.ndarray) -> bytes:
        """Convert numpy audio buffer to WAV format bytes"""
        # Ensure correct shape (2, samples)
        if audio_buffer.ndim == 1:
            audio_buffer = np.stack([audio_buffer, audio_buffer])

        # Convert to 16-bit PCM
        audio_16bit = (audio_buffer * 32767).astype(np.int16)

        # Interleave stereo channels
        interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
        interleaved[0::2] = audio_16bit[0]  # Left channel
        interleaved[1::2] = audio_16bit[1]  # Right channel

        return interleaved.tobytes()

    async def stream_wav(self) -> AsyncGenerator[bytes, None]:
        """Stream audio as WAV format"""
        # First, yield WAV header
        header = self._create_wav_header()
        yield header

        # Then stream audio chunks
        while self.is_streaming:
            try:
                # Get chunk from queue with timeout
                chunk = await asyncio.wait_for(self.stream_queue.get(), timeout=0.1)
                yield chunk

            except asyncio.TimeoutError:
                # No data available, yield silence
                silence_duration = 0.1  # 100ms
                silence_samples = int(silence_duration * self.sample_rate)
                silence = np.zeros((2, silence_samples), dtype=np.float32)
                yield self._convert_to_wav_chunk(silence)

    def _create_wav_header(self, file_size: int = 0x7FFFFFFF) -> bytes:
        """Create WAV file header"""
        # WAV header format
        header = bytearray()

        # RIFF chunk
        header.extend(b"RIFF")
        header.extend(struct.pack("<I", file_size - 8))  # File size - 8
        header.extend(b"WAVE")

        # fmt chunk
        header.extend(b"fmt ")
        header.extend(struct.pack("<I", 16))  # Chunk size
        header.extend(struct.pack("<H", 1))  # PCM format
        header.extend(struct.pack("<H", self.channels))  # Channels
        header.extend(struct.pack("<I", self.sample_rate))  # Sample rate
        byte_rate = self.sample_rate * self.channels * self.bytes_per_sample
        header.extend(struct.pack("<I", byte_rate))  # Byte rate
        block_align = self.channels * self.bytes_per_sample
        header.extend(struct.pack("<H", block_align))  # Block align
        header.extend(struct.pack("<H", self.bytes_per_sample * 8))  # Bits per sample

        # data chunk
        header.extend(b"data")
        header.extend(struct.pack("<I", file_size - 44))  # Data size

        return bytes(header)

    async def stream_mp3(self) -> AsyncGenerator[bytes, None]:
        """Stream audio as MP3 format (requires additional encoding)"""
        # This would require real-time MP3 encoding
        # For now, we'll use WAV format
        async for chunk in self.stream_wav():
            yield chunk

    def get_stream_info(self) -> Dict:
        """Get current streaming information"""
        return {
            "is_streaming": self.is_streaming,
            "format": "wav",
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bits_per_sample": self.bytes_per_sample * 8,
            "queue_size": self.stream_queue.qsize()
            if hasattr(self.stream_queue, "qsize")
            else 0,
        }

"""Text-to-Speech service for radio host voice generation."""

import hashlib
import os
import time
from typing import AsyncIterator, Dict, Optional, Union
from pathlib import Path

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

from utils.logger_config import setup_logger

logger = setup_logger(__name__)


class TTSConfig(BaseModel):
    """Configuration for TTS generation."""

    model: str = "gpt-4o-mini-tts"
    voice: str = "coral"
    instructions: str = "Speak in a friendly, conversational tone"
    response_format: str = "mp3"
    speed: Optional[float] = None  # Not supported by gpt-4o-mini-tts


class VoiceCache:
    """Simple in-memory cache for voice segments."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 900):  # 15 min TTL
        self.cache: Dict[str, tuple[bytes, float]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[bytes]:
        """Get cached audio if available and not expired."""
        if key in self.cache:
            audio, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                logger.info(f"Cache hit for key: {key[:8]}...")
                return audio
            else:
                # Expired, remove it
                del self.cache[key]
        return None

    def set(self, key: str, audio: bytes):
        """Cache audio data."""
        # Implement simple LRU by removing oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (audio, time.time())
        logger.info(f"Cached audio for key: {key[:8]}...")

    def generate_key(self, text: str, config: TTSConfig) -> str:
        """Generate cache key from text and config."""
        cache_string = f"{text}|{config.model}|{config.voice}|{config.instructions}"
        return hashlib.sha256(cache_string.encode()).hexdigest()


class TTSService:
    """Service for generating text-to-speech audio."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        self.cache = VoiceCache()

        # Rate limiting
        self.rate_limit = 100  # requests per minute
        self.rate_window = 60  # seconds
        self.request_times = []

    def _check_rate_limit(self):
        """Check if we're within rate limits."""
        current_time = time.time()
        # Remove old requests outside the window
        self.request_times = [
            t for t in self.request_times if current_time - t < self.rate_window
        ]

        if len(self.request_times) >= self.rate_limit:
            oldest_request = min(self.request_times)
            wait_time = self.rate_window - (current_time - oldest_request)
            raise Exception(f"Rate limit exceeded. Wait {wait_time:.1f} seconds.")

        self.request_times.append(current_time)

    def generate_speech(
        self,
        text: str,
        voice: str = "coral",
        instructions: str = "Speak in a friendly, conversational tone",
        response_format: str = "mp3",
        use_cache: bool = True,
    ) -> bytes:
        """Generate speech synchronously."""
        try:
            config = TTSConfig(
                voice=voice, instructions=instructions, response_format=response_format
            )

            # Check cache first
            if use_cache:
                cache_key = self.cache.generate_key(text, config)
                cached_audio = self.cache.get(cache_key)
                if cached_audio:
                    return cached_audio

            # Check rate limit
            self._check_rate_limit()

            # Generate speech
            logger.info(f"Generating TTS for text: {text[:50]}...")

            response = self.client.audio.speech.create(
                model=config.model,
                voice=config.voice,
                input=text,
                instructions=config.instructions,
                response_format=config.response_format,
            )

            # Get audio data
            audio_data = response.read()

            # Cache the result
            if use_cache:
                self.cache.set(cache_key, audio_data)

            logger.info(f"Generated {len(audio_data)} bytes of {response_format} audio")
            return audio_data

        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise

    async def generate_speech_async(
        self,
        text: str,
        voice: str = "coral",
        instructions: str = "Speak in a friendly, conversational tone",
        response_format: str = "mp3",
        use_cache: bool = True,
    ) -> bytes:
        """Generate speech asynchronously."""
        try:
            config = TTSConfig(
                voice=voice, instructions=instructions, response_format=response_format
            )

            # Check cache first
            if use_cache:
                cache_key = self.cache.generate_key(text, config)
                cached_audio = self.cache.get(cache_key)
                if cached_audio:
                    return cached_audio

            # Check rate limit
            self._check_rate_limit()

            # Generate speech
            logger.info(f"Generating TTS async for text: {text[:50]}...")

            response = await self.async_client.audio.speech.create(
                model=config.model,
                voice=config.voice,
                input=text,
                instructions=config.instructions,
                response_format=config.response_format,
            )

            # Get audio data
            audio_data = await response.read()

            # Cache the result
            if use_cache:
                self.cache.set(cache_key, audio_data)

            logger.info(f"Generated {len(audio_data)} bytes of {response_format} audio")
            return audio_data

        except Exception as e:
            logger.error(f"Error generating speech async: {e}")
            raise

    async def stream_speech(
        self,
        text: str,
        voice: str = "coral",
        instructions: str = "Speak in a friendly, conversational tone",
        response_format: str = "pcm",  # PCM is best for streaming
    ) -> AsyncIterator[bytes]:
        """Stream speech audio in real-time."""
        try:
            config = TTSConfig(
                voice=voice, instructions=instructions, response_format=response_format
            )

            # Check rate limit
            self._check_rate_limit()

            logger.info(f"Streaming TTS for text: {text[:50]}...")

            async with self.async_client.audio.speech.with_streaming_response.create(
                model=config.model,
                voice=config.voice,
                input=text,
                instructions=config.instructions,
                response_format=config.response_format,
            ) as response:
                chunk_count = 0
                async for chunk in response.iter_bytes(chunk_size=1024):
                    chunk_count += 1
                    yield chunk

                logger.info(f"Streamed {chunk_count} chunks of {response_format} audio")

        except Exception as e:
            logger.error(f"Error streaming speech: {e}")
            raise

    def build_dynamic_instructions(
        self, base_instructions: str, context: Dict[str, any]
    ) -> str:
        """Build dynamic instructions based on context."""
        instructions_parts = [base_instructions]

        # Add contextual modifications
        if context.get("is_downtempo"):
            instructions_parts.append("Speak more softly and slowly.")

        if context.get("high_energy"):
            instructions_parts.append("Add extra excitement and energy!")

        if context.get("transition_active"):
            instructions_parts.append("Acknowledge the smooth transition.")

        if context.get("late_night"):
            instructions_parts.append("Use a more intimate, late-night radio voice.")

        return " ".join(instructions_parts)

    def generate_with_retry(
        self, text: str, config: TTSConfig, max_retries: int = 3
    ) -> bytes:
        """Generate speech with retry logic."""
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff
                    wait_time = 2**attempt
                    logger.info(f"Retry attempt {attempt + 1}, waiting {wait_time}s...")
                    time.sleep(wait_time)

                return self.generate_speech(
                    text=text,
                    voice=config.voice,
                    instructions=config.instructions,
                    response_format=config.response_format,
                    use_cache=True,
                )

            except Exception as e:
                logger.error(f"TTS generation attempt {attempt + 1} failed: {e}")
                last_error = e

        raise Exception(
            f"Failed to generate speech after {max_retries} attempts: {last_error}"
        )

    def save_to_file(self, audio_data: bytes, filepath: Union[str, Path]):
        """Save audio data to file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(audio_data)

        logger.info(f"Saved audio to {filepath}")

    async def preview_voice(self, voice: str, instructions: str) -> bytes:
        """Generate a preview of a voice with given instructions."""
        preview_text = "Hello! This is a preview of how I'll sound as your radio host. Let's enjoy some great music together!"

        return await self.generate_speech_async(
            text=preview_text,
            voice=voice,
            instructions=instructions,
            response_format="mp3",
            use_cache=False,  # Don't cache previews
        )


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create the TTS service singleton."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

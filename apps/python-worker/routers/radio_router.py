"""Radio mode API router."""

import asyncio
import io
import json
import time
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agents.radio_host_agent import (
    RadioHostAgent,
    PersonaConfig,
    PRESET_PERSONAS,
)
from utils.tts_service import get_tts_service
from utils.logger_config import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/radio", tags=["radio"])

# Global state (in production, use Redis or similar)
radio_sessions: Dict[str, Dict] = {}
radio_agent = RadioHostAgent()
tts_service = get_tts_service()


class RadioEnableRequest(BaseModel):
    """Request to enable radio mode."""

    session_id: Optional[str] = None
    persona_id: str = "world_citizen"
    playlist_context: Optional[Dict] = Field(default_factory=dict)


class RadioStatusResponse(BaseModel):
    """Radio mode status response."""

    enabled: bool
    session_id: Optional[str]
    current_persona: Optional[Dict]
    total_segments: int = 0
    last_spoke_at: Optional[float]


class PersonaUpdateRequest(BaseModel):
    """Request to update persona settings."""

    persona_id: Optional[str] = None
    custom_instructions: Optional[str] = None
    voice_settings: Optional[Dict] = None


class VoiceSettingsRequest(BaseModel):
    """Voice settings update request."""

    voice: Optional[str] = None
    instructions: Optional[str] = None
    preview: bool = False


class NextSegmentResponse(BaseModel):
    """Response with next voice segment."""

    segment: Optional[Dict] = None
    audio_url: Optional[str] = None
    estimated_duration: float = 0.0


@router.post("/enable")
async def enable_radio_mode(request: RadioEnableRequest) -> RadioStatusResponse:
    """Enable radio mode for a session."""
    try:
        session_id = request.session_id or str(uuid4())

        # Get persona
        if request.persona_id not in PRESET_PERSONAS:
            raise HTTPException(400, f"Unknown persona: {request.persona_id}")

        persona = PRESET_PERSONAS[request.persona_id]

        # Initialize session
        session = {
            "session_id": session_id,
            "enabled": True,
            "current_persona": persona.dict(),
            "last_spoke_at": time.time() - 120,  # Ready to speak
            "tracks_since_last": 0,
            "total_segments": 0,
            "voice_queue": [],
            "playlist_context": request.playlist_context or {},
            "session_start": time.time(),
            "next_content_type": None,
            "error": None,
        }

        radio_sessions[session_id] = session

        logger.info(
            f"Enabled radio mode for session {session_id} with persona {request.persona_id}"
        )

        return RadioStatusResponse(
            enabled=True,
            session_id=session_id,
            current_persona=persona.dict(),
            total_segments=0,
            last_spoke_at=session["last_spoke_at"],
        )

    except Exception as e:
        logger.error(f"Error enabling radio mode: {e}")
        raise HTTPException(500, str(e))


@router.post("/disable")
async def disable_radio_mode(session_id: str = Query(...)) -> RadioStatusResponse:
    """Disable radio mode for a session."""
    try:
        if session_id not in radio_sessions:
            raise HTTPException(404, "Session not found")

        session = radio_sessions[session_id]
        session["enabled"] = False

        logger.info(f"Disabled radio mode for session {session_id}")

        return RadioStatusResponse(
            enabled=False,
            session_id=session_id,
            current_persona=session["current_persona"],
            total_segments=session["total_segments"],
            last_spoke_at=session["last_spoke_at"],
        )

    except Exception as e:
        logger.error(f"Error disabling radio mode: {e}")
        raise HTTPException(500, str(e))


@router.get("/status")
async def get_radio_status(session_id: str = Query(...)) -> RadioStatusResponse:
    """Get current radio mode status."""
    try:
        if session_id not in radio_sessions:
            return RadioStatusResponse(
                enabled=False,
                session_id=session_id,
                current_persona=None,
                total_segments=0,
                last_spoke_at=None,
            )

        session = radio_sessions[session_id]

        return RadioStatusResponse(
            enabled=session["enabled"],
            session_id=session_id,
            current_persona=session["current_persona"],
            total_segments=session["total_segments"],
            last_spoke_at=session["last_spoke_at"],
        )

    except Exception as e:
        logger.error(f"Error getting radio status: {e}")
        raise HTTPException(500, str(e))


@router.post("/persona")
async def update_persona(
    session_id: str = Query(...), request: PersonaUpdateRequest = Body(...)
) -> Dict:
    """Update persona settings for a session."""
    try:
        if session_id not in radio_sessions:
            raise HTTPException(404, "Session not found")

        session = radio_sessions[session_id]

        # Update to new preset persona
        if request.persona_id:
            if request.persona_id not in PRESET_PERSONAS:
                raise HTTPException(400, f"Unknown persona: {request.persona_id}")

            persona = PRESET_PERSONAS[request.persona_id]
            session["current_persona"] = persona.dict()

        # Update custom instructions
        if request.custom_instructions:
            session["current_persona"]["voice"]["instructions"] = (
                request.custom_instructions
            )

        # Update voice settings
        if request.voice_settings:
            session["current_persona"]["voice"].update(request.voice_settings)

        logger.info(f"Updated persona for session {session_id}")

        return {"success": True, "current_persona": session["current_persona"]}

    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise HTTPException(500, str(e))


@router.get("/personas")
async def get_available_personas() -> Dict[str, Dict]:
    """Get all available preset personas."""
    try:
        return {
            persona_id: persona.dict()
            for persona_id, persona in PRESET_PERSONAS.items()
        }

    except Exception as e:
        logger.error(f"Error getting personas: {e}")
        raise HTTPException(500, str(e))


@router.post("/voice-settings")
async def update_voice_settings(
    session_id: str = Query(...), request: VoiceSettingsRequest = Body(...)
) -> Dict:
    """Update voice settings and optionally preview."""
    try:
        if session_id not in radio_sessions:
            raise HTTPException(404, "Session not found")

        session = radio_sessions[session_id]
        persona = PersonaConfig(**session["current_persona"])

        # Update voice settings
        if request.voice:
            persona.voice["voice"] = request.voice

        if request.instructions:
            persona.voice["instructions"] = request.instructions

        session["current_persona"] = persona.dict()

        # Generate preview if requested
        preview_url = None
        if request.preview:
            preview_audio = await tts_service.preview_voice(
                voice=persona.voice["voice"], instructions=persona.voice["instructions"]
            )

            # In production, upload to S3 and return URL
            # For now, return a placeholder
            preview_url = f"/radio/preview/{session_id}"

        logger.info(f"Updated voice settings for session {session_id}")

        return {
            "success": True,
            "voice_settings": persona.voice,
            "preview_url": preview_url,
        }

    except Exception as e:
        logger.error(f"Error updating voice settings: {e}")
        raise HTTPException(500, str(e))


@router.get("/next-segment")
async def get_next_segment(
    session_id: str = Query(...),
    current_track: Optional[str] = Query(None),
    next_track: Optional[str] = Query(None),
) -> NextSegmentResponse:
    """Get the next voice segment if one should play."""
    try:
        if session_id not in radio_sessions:
            raise HTTPException(404, "Session not found")

        session = radio_sessions[session_id]

        if not session["enabled"]:
            return NextSegmentResponse(segment=None)

        # Parse track info if provided
        current_track_info = json.loads(current_track) if current_track else {}
        next_track_info = json.loads(next_track) if next_track else None

        # Update session state
        session["tracks_since_last"] += 1
        if current_track_info:
            session["playlist_context"]["previous_track"] = session.get(
                "current_track", {}
            )
            session["current_track"] = current_track_info
            session["next_track"] = next_track_info

        # Process with radio agent
        segments = radio_agent.process_track_change(
            current_track=current_track_info,
            next_track=next_track_info,
            playlist_context=session["playlist_context"],
        )

        if segments:
            segment = segments[0]  # Get first segment

            # Generate TTS audio
            audio_data = await tts_service.generate_speech_async(
                text=segment.script,
                voice=segment.voice_config["voice"],
                instructions=segment.instructions,
                use_cache=True,
            )

            # Update session
            session["last_spoke_at"] = time.time()
            session["tracks_since_last"] = 0
            session["total_segments"] += 1

            # In production, upload audio and return URL
            audio_url = f"/radio/audio/{segment.id}"

            return NextSegmentResponse(
                segment=segment.dict(),
                audio_url=audio_url,
                estimated_duration=segment.duration_estimate,
            )

        return NextSegmentResponse(segment=None)

    except Exception as e:
        logger.error(f"Error getting next segment: {e}")
        raise HTTPException(500, str(e))


@router.get("/stream/{session_id}")
async def stream_radio_updates(session_id: str):
    """Stream radio updates via Server-Sent Events."""

    async def event_generator():
        try:
            if session_id not in radio_sessions:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "Session not found"}),
                }
                return

            logger.info(f"Starting SSE stream for radio session {session_id}")

            while True:
                session = radio_sessions.get(session_id)
                if not session or not session["enabled"]:
                    yield {
                        "event": "close",
                        "data": json.dumps({"reason": "Session ended"}),
                    }
                    break

                # Check for voice segments in queue
                if session["voice_queue"]:
                    segment = session["voice_queue"].pop(0)
                    yield {"event": "voice_segment", "data": json.dumps(segment)}

                # Send heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps(
                        {
                            "session_id": session_id,
                            "enabled": session["enabled"],
                            "timestamp": time.time(),
                        }
                    ),
                }

                await asyncio.sleep(1)  # Check every second

        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@router.post("/track-change")
async def notify_track_change(
    session_id: str = Query(...),
    current_track: Dict = Body(...),
    next_track: Optional[Dict] = Body(None),
    playlist_context: Optional[Dict] = Body(default_factory=dict),
) -> Dict:
    """Notify radio host of a track change."""
    try:
        if session_id not in radio_sessions:
            raise HTTPException(404, "Session not found")

        session = radio_sessions[session_id]

        if not session["enabled"]:
            return {"processed": False, "reason": "Radio mode disabled"}

        # Update context
        session["playlist_context"].update(playlist_context or {})

        # Process with radio agent
        segments = radio_agent.process_track_change(
            current_track=current_track,
            next_track=next_track,
            playlist_context=session["playlist_context"],
        )

        # Add segments to queue
        for segment in segments:
            session["voice_queue"].append(segment.dict())

        logger.info(f"Processed track change, generated {len(segments)} segments")

        return {"processed": True, "segments_generated": len(segments)}

    except Exception as e:
        logger.error(f"Error processing track change: {e}")
        raise HTTPException(500, str(e))


# Audio serving endpoints (in production, use S3 or CDN)
audio_cache: Dict[str, bytes] = {}


@router.get("/audio/{segment_id}")
async def get_audio_segment(segment_id: str):
    """Get audio for a specific segment."""
    try:
        if segment_id not in audio_cache:
            raise HTTPException(404, "Audio segment not found")

        audio_data = audio_cache[segment_id]

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename={segment_id}.mp3",
                "Cache-Control": "public, max-age=3600",
            },
        )

    except Exception as e:
        logger.error(f"Error serving audio: {e}")
        raise HTTPException(500, str(e))


@router.get("/preview/{session_id}")
async def get_preview_audio(session_id: str):
    """Get preview audio for current voice settings."""
    try:
        if session_id not in radio_sessions:
            raise HTTPException(404, "Session not found")

        session = radio_sessions[session_id]
        persona = PersonaConfig(**session["current_persona"])

        # Generate preview
        preview_audio = await tts_service.preview_voice(
            voice=persona.voice["voice"], instructions=persona.voice["instructions"]
        )

        return StreamingResponse(
            io.BytesIO(preview_audio),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename=preview_{session_id}.mp3"
            },
        )

    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(500, str(e))

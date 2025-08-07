"""
Mix Router - API endpoints for mix coordination and transition management.
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Optional, Any
import logging
import json
import asyncio

from models.mix_models import (
    MixPlanResponse,
    MixDecision,
    TransitionState,
    DJSessionState,
    MixHistory,
)
from agents.mix_coordinator_agent import MixCoordinatorAgent
from services.transition_executor import TransitionExecutor
from services.service_manager import service_manager

# Create router
router = APIRouter(prefix="/api/mix", tags=["Mix Coordination"])

# Logger
logger = logging.getLogger(__name__)

# Session storage (in production, use Redis or database)
dj_sessions: Dict[str, DJSessionState] = {}
mix_histories: Dict[str, MixHistory] = {}


async def get_mix_coordinator() -> MixCoordinatorAgent:
    """Get the singleton MixCoordinatorAgent instance"""
    return await service_manager.get_mix_coordinator()


async def get_transition_executor() -> TransitionExecutor:
    """Get the singleton TransitionExecutor instance"""
    return await service_manager.get_transition_executor()


# Request/Response models
class CoordinateMixRequest(BaseModel):
    session_id: Optional[str] = "default"
    force: bool = False  # Force new mix even if one is active


class ExecuteTransitionRequest(BaseModel):
    mix_decision: MixDecision


class TransitionControlRequest(BaseModel):
    action: str  # "cancel", "pause", "resume"


# Endpoints


@router.post("/coordinate", response_model=MixPlanResponse)
async def coordinate_mix(
    request: CoordinateMixRequest,
    coordinator: MixCoordinatorAgent = Depends(get_mix_coordinator),
    executor: TransitionExecutor = Depends(get_transition_executor),
):
    """Trigger mix coordination to generate a transition plan."""
    try:
        # Check if transition is already active
        if executor.get_transition_state() and not request.force:
            raise HTTPException(
                status_code=409,
                detail="Transition already in progress. Use force=true to override.",
            )

        # Get current session state, passing the services from coordinator
        session_state = await _get_session_state(
            request.session_id,
            deck_manager=coordinator.deck_manager,
            mixer_manager=coordinator.mixer_manager,
            analysis_service=coordinator.analysis_service,
        )

        # Coordinate mix
        mix_decision = await coordinator.coordinate_mix(session_state)

        if not mix_decision:
            # Return empty response when no mix is needed
            from models.mix_models import TrackCompatibility

            return MixPlanResponse(
                mix_decision=None,
                compatibility=TrackCompatibility(
                    overall=0.0, bpm=0.0, key=0.0, energy=0.0, genre=0.0
                ),
                warnings=["No suitable mix candidates found"],
            )

        # Add to history
        _add_to_history(request.session_id, mix_decision)

        # Update session state
        if request.session_id in dj_sessions:
            dj_sessions[request.session_id].current_mix_plan = mix_decision

        # Get compatibility scores from coordinator state
        # For now, return basic compatibility
        from models.mix_models import TrackCompatibility

        compatibility = TrackCompatibility(
            overall=mix_decision.decision_confidence,
            bpm=0.8,
            key=0.7,
            energy=0.8,
            genre=0.9,
        )

        return MixPlanResponse(
            mix_decision=mix_decision, compatibility=compatibility, warnings=[]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error coordinating mix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current-plan")
async def get_current_plan(session_id: str = "default"):
    """Get the current mix plan for a session."""
    try:
        if session_id in dj_sessions:
            plan = dj_sessions[session_id].current_mix_plan
            return {"current_plan": plan.dict() if plan else None}
        return {"current_plan": None}
    except Exception as e:
        logger.error(f"Error getting current plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-transition")
async def execute_transition(
    request: ExecuteTransitionRequest,
    executor: TransitionExecutor = Depends(get_transition_executor),
):
    """Execute a specific transition plan."""
    try:
        # Check if already executing
        if executor.get_transition_state():
            raise HTTPException(
                status_code=409, detail="Transition already in progress"
            )

        # Execute the transition
        success = await executor.execute_transition(request.mix_decision)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to start transition")

        return {"status": "started", "transition": request.mix_decision.dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing transition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition/control")
async def control_transition(
    request: TransitionControlRequest,
    executor: TransitionExecutor = Depends(get_transition_executor),
):
    """Control an active transition (cancel, pause, resume)."""
    try:
        if request.action == "cancel":
            await executor.cancel_transition()
            return {"status": "cancelled"}
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported action: {request.action}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling transition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transition/status")
async def get_transition_status(
    executor: TransitionExecutor = Depends(get_transition_executor),
):
    """Get current transition status."""
    try:
        state = executor.get_transition_state()

        if not state:
            return {"active": False, "state": None}

        return {
            "active": state.is_active,
            "state": {
                "progress": state.progress,
                "current_phase": state.current_phase,
                "started_at": state.started_at.isoformat(),
                "mix_decision": state.mix_decision.dict(),
                "effects_applied": state.effects_applied,
            },
        }

    except Exception as e:
        logger.error(f"Error getting transition status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_mix_history(session_id: str = "default", limit: int = 10):
    """Get mix history for a session."""
    try:
        history = mix_histories.get(session_id)

        if not history:
            return {"session_id": session_id, "decisions": [], "total": 0}

        recent = history.get_recent_decisions(limit)

        return {
            "session_id": session_id,
            "decisions": [d.dict() for d in recent],
            "total": len(history.decisions),
        }

    except Exception as e:
        logger.error(f"Error getting mix history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream")
async def stream_mix_updates(
    websocket: WebSocket,
    session_id: str = "default",
    executor: TransitionExecutor = Depends(get_transition_executor),
):
    """WebSocket endpoint for streaming mix and transition updates."""
    await websocket.accept()

    # Callback for transition updates
    async def send_transition_update(state: TransitionState):
        try:
            await websocket.send_json(
                {
                    "type": "transition_update",
                    "data": {
                        "progress": state.progress,
                        "phase": state.current_phase,
                        "is_active": state.is_active,
                        "effects_applied": state.effects_applied,
                    },
                }
            )
        except:
            pass  # Connection might be closed

    # Register callback
    executor.add_update_callback(send_transition_update)

    try:
        logger.info(f"WebSocket connected for mix stream (session: {session_id})")

        # Send initial state
        await websocket.send_json({"type": "connected", "session_id": session_id})

        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages (with timeout for periodic updates)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # Handle client messages if needed
                data = json.loads(message)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        executor.remove_update_callback(send_transition_update)
        logger.info(f"WebSocket disconnected for mix stream (session: {session_id})")


# Helper functions


async def _get_session_state(
    session_id: str, deck_manager=None, mixer_manager=None, analysis_service=None
) -> Dict[str, Any]:
    """Get current session state from various services."""
    # If services not provided, get them from service_manager
    if not deck_manager:
        deck_manager = await service_manager.get_deck_manager()
    if not mixer_manager:
        mixer_manager = await service_manager.get_mixer_manager()
    if not analysis_service:
        analysis_service = await service_manager.get_analysis_service()

    # Collect state
    decks = {}
    analysis_cache = {}

    # Get all deck states
    deck_states = await deck_manager.get_all_decks()
    for deck_state in deck_states:
        deck_id = deck_state["id"]
        decks[deck_id] = deck_state

        # Get analysis for loaded tracks
        if deck_state.get("track_filepath"):
            try:
                analysis = await analysis_service.get_cached_analysis(
                    deck_state["track_filepath"]
                )
                if analysis:
                    analysis_cache[deck_state["track_filepath"]] = analysis
            except:
                pass

    # Get mixer state
    mixer_state = await mixer_manager.get_mixer_state()

    # Get or create session
    if session_id not in dj_sessions:
        dj_sessions[session_id] = DJSessionState(
            session_id=session_id, energy_trajectory="building"
        )

    session = dj_sessions[session_id]

    # Build complete state
    return {
        "decks": decks,
        "mixer": mixer_state,
        "analysis_cache": analysis_cache,
        "mix_history": [d.dict() for d in session.mix_history],
        "energy_trajectory": session.energy_trajectory.value,
        "performance_metrics": session.performance_metrics,
    }


def _add_to_history(session_id: str, mix_decision: MixDecision):
    """Add mix decision to history."""
    if session_id not in mix_histories:
        mix_histories[session_id] = MixHistory(session_id=session_id)

    mix_histories[session_id].add_decision(mix_decision)

    # Also update session
    if session_id in dj_sessions:
        dj_sessions[session_id].mix_history.append(mix_decision)

"""
Effect Router - API endpoints for effect management and testing.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from models.effect_models import EffectState, EffectEvent, AutomationCurve, ActiveEffect
from models.mix_models import TransitionEffect, EffectType
from services.service_manager import service_manager
from services.effect_manager import EffectManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/effects", tags=["effects"])


# Request/Response models
class ManualEffectRequest(BaseModel):
    """Request to manually apply an effect"""

    deck_id: str = Field(pattern="^[A-D]$")
    effect_type: EffectType
    intensity: float = Field(ge=0.0, le=1.0, default=0.5)
    duration: Optional[float] = Field(ge=0.0, le=60.0, default=None)
    parameters: Optional[Dict[str, float]] = None


class EffectUpdateRequest(BaseModel):
    """Request to update effect parameters"""

    parameters: Optional[Dict[str, float]] = None
    target_parameters: Optional[Dict[str, float]] = None
    automation_curve: Optional[AutomationCurve] = None


class EffectResponse(BaseModel):
    """Response for effect operations"""

    effect_id: str
    status: str
    message: Optional[str] = None


class ActiveEffectsResponse(BaseModel):
    """Response listing active effects"""

    effects: List[EffectState]
    total_count: int


class DeckEffectsResponse(BaseModel):
    """Response for deck-specific effects"""

    deck_id: str
    effects: List[EffectState]
    bypass_all: bool = False


class EffectEventLogResponse(BaseModel):
    """Response for effect event log"""

    events: List[EffectEvent]
    total_events: int


# Dependency to get EffectManager
async def get_effect_manager() -> EffectManager:
    """Get the EffectManager instance"""
    return await service_manager.get_effect_manager()


@router.get("/active", response_model=ActiveEffectsResponse)
async def get_all_active_effects(
    effect_manager: EffectManager = Depends(get_effect_manager),
):
    """Get all currently active effects across all decks"""
    effects = effect_manager.get_all_active_effects()
    return ActiveEffectsResponse(effects=effects, total_count=len(effects))


@router.get("/{effect_id}", response_model=EffectState)
async def get_effect_state(
    effect_id: str, effect_manager: EffectManager = Depends(get_effect_manager)
):
    """Get the current state of a specific effect"""
    state = effect_manager.get_effect_state(effect_id)
    if not state:
        raise HTTPException(status_code=404, detail="Effect not found")
    return state


@router.post("/manual", response_model=EffectResponse)
async def apply_manual_effect(
    request: ManualEffectRequest,
    effect_manager: EffectManager = Depends(get_effect_manager),
):
    """Manually apply an effect to a deck (for testing)"""
    try:
        # Create TransitionEffect from request
        effect = TransitionEffect(
            type=request.effect_type,
            intensity=request.intensity,
            duration=request.duration,
            parameters=request.parameters or {},
        )

        # Apply effect
        effect_id = await effect_manager.apply_effect(
            deck_id=request.deck_id, effect=effect
        )

        return EffectResponse(
            effect_id=effect_id,
            status="applied",
            message=f"{request.effect_type} applied to deck {request.deck_id}",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to apply manual effect: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply effect")


@router.put("/{effect_id}/parameters", response_model=EffectResponse)
async def update_effect_parameters(
    effect_id: str,
    request: EffectUpdateRequest,
    effect_manager: EffectManager = Depends(get_effect_manager),
):
    """Update parameters of an active effect"""
    success = await effect_manager.update_effect(
        effect_id=effect_id,
        parameters=request.parameters,
        target_parameters=request.target_parameters,
        automation_curve=request.automation_curve,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Effect not found or inactive")

    return EffectResponse(
        effect_id=effect_id, status="updated", message="Effect parameters updated"
    )


@router.put("/{effect_id}/bypass", response_model=EffectResponse)
async def bypass_effect(
    effect_id: str,
    bypassed: bool = True,
    effect_manager: EffectManager = Depends(get_effect_manager),
):
    """Bypass or un-bypass an effect"""
    success = await effect_manager.bypass_effect(effect_id, bypassed)

    if not success:
        raise HTTPException(status_code=404, detail="Effect not found")

    return EffectResponse(
        effect_id=effect_id,
        status="bypassed" if bypassed else "active",
        message=f"Effect {'bypassed' if bypassed else 'resumed'}",
    )


@router.delete("/{effect_id}", response_model=EffectResponse)
async def stop_effect(
    effect_id: str, effect_manager: EffectManager = Depends(get_effect_manager)
):
    """Stop and remove an effect"""
    success = await effect_manager.stop_effect(effect_id)

    if not success:
        raise HTTPException(status_code=404, detail="Effect not found")

    return EffectResponse(
        effect_id=effect_id, status="stopped", message="Effect stopped and removed"
    )


@router.get("/deck/{deck_id}", response_model=DeckEffectsResponse)
async def get_deck_effects(
    deck_id: str, effect_manager: EffectManager = Depends(get_effect_manager)
):
    """Get all active effects for a specific deck"""
    if deck_id not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Invalid deck ID")

    effects = effect_manager.get_deck_effects(deck_id)
    effect_states = [EffectState.from_active_effect(e) for e in effects]

    return DeckEffectsResponse(
        deck_id=deck_id,
        effects=effect_states,
        bypass_all=False,  # Could be extended to support deck bypass
    )


@router.delete("/deck/{deck_id}/all", response_model=Dict[str, Any])
async def clear_deck_effects(
    deck_id: str, effect_manager: EffectManager = Depends(get_effect_manager)
):
    """Clear all effects from a deck"""
    if deck_id not in ["A", "B", "C", "D"]:
        raise HTTPException(status_code=400, detail="Invalid deck ID")

    count = await effect_manager.clear_deck_effects(deck_id)

    return {"deck_id": deck_id, "effects_cleared": count, "status": "success"}


@router.get("/events/log", response_model=EffectEventLogResponse)
async def get_effect_event_log(
    deck_id: Optional[str] = None,
    effect_id: Optional[str] = None,
    limit: int = 100,
    effect_manager: EffectManager = Depends(get_effect_manager),
):
    """Get effect event log for debugging"""
    events = effect_manager.get_event_log(
        deck_id=deck_id, effect_id=effect_id, limit=limit
    )

    return EffectEventLogResponse(events=events, total_events=len(events))


@router.post("/simulate/tick", response_model=Dict[str, Any])
async def simulate_effect_tick(
    current_time: float, effect_manager: EffectManager = Depends(get_effect_manager)
):
    """Simulate a time tick for effect parameter automation (testing only)"""
    deck_parameters = effect_manager.process_tick(current_time)

    return {
        "current_time": current_time,
        "deck_parameters": deck_parameters,
        "active_effects_count": len(effect_manager._active_effects),
    }

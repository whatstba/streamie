"""
Mixer Router - API endpoints for mixer control and monitoring.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging

from models import init_db
from services.mixer_manager import MixerManager
from services.deck_manager import DeckManager


# Create router
router = APIRouter(prefix="/api/mixer", tags=["Mixer Control"])

# Logger
logger = logging.getLogger(__name__)

# Database dependency
_engine = None

async def get_engine():
    global _engine
    if _engine is None:
        _engine = await init_db()
    return _engine

async def get_mixer_manager():
    engine = await get_engine()
    return MixerManager(engine)

async def get_deck_manager():
    engine = await get_engine()
    return DeckManager(engine)


# Request/Response models
class CrossfaderUpdateRequest(BaseModel):
    position: float  # -1.0 to 1.0
    apply_to_decks: bool = True

class CrossfaderCurveRequest(BaseModel):
    curve: str  # linear, logarithmic, scratch

class MasterOutputRequest(BaseModel):
    volume: Optional[float] = None  # 0.0 to 1.0
    gain: Optional[float] = None   # 0.0 to 2.0

class MonitorRequest(BaseModel):
    volume: Optional[float] = None   # 0.0 to 1.0
    cue_mix: Optional[float] = None  # 0.0 to 1.0 (0=cue only, 1=master only)

class RecordingRequest(BaseModel):
    filepath: str

class CrossfaderStateResponse(BaseModel):
    success: bool
    position: float
    gain_a: float
    gain_b: float
    curve: str

class ChannelLevelResponse(BaseModel):
    deck_id: str
    level: float
    pre_fader_level: float
    post_fader_level: float
    clipping: bool
    pre_master_clipping: bool

class AllLevelsResponse(BaseModel):
    A: ChannelLevelResponse
    B: ChannelLevelResponse
    C: ChannelLevelResponse
    D: ChannelLevelResponse
    master: Dict[str, Any]

class AutoGainResponse(BaseModel):
    success: bool
    deck_id: Optional[str] = None
    energy_level: Optional[float] = None
    suggested_gain: Optional[float] = None
    applied: Optional[bool] = None
    error: Optional[str] = None

class CueToggleResponse(BaseModel):
    success: bool
    deck_id: str
    cue_active: bool
    error: Optional[str] = None


# Endpoints

@router.get("/state")
async def get_mixer_state(mixer_manager: MixerManager = Depends(get_mixer_manager)):
    """Get the current mixer state"""
    try:
        state = await mixer_manager.get_mixer_state()
        if not state:
            raise HTTPException(status_code=404, detail="Mixer state not found")
        return state
    except Exception as e:
        logger.error(f"Error getting mixer state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/crossfader", response_model=CrossfaderStateResponse)
async def update_crossfader(
    request: CrossfaderUpdateRequest,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Update crossfader position"""
    try:
        result = await mixer_manager.update_crossfader(request.position, request.apply_to_decks)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update crossfader'))
        return result
    except Exception as e:
        logger.error(f"Error updating crossfader: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/crossfader/curve", response_model=CrossfaderStateResponse)
async def update_crossfader_curve(
    request: CrossfaderCurveRequest,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Update crossfader curve type"""
    try:
        result = await mixer_manager.update_crossfader_curve(request.curve)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update curve'))
        return result
    except Exception as e:
        logger.error(f"Error updating crossfader curve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/master")
async def update_master_output(
    request: MasterOutputRequest,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Update master output settings"""
    try:
        result = await mixer_manager.update_master_output(request.volume, request.gain)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update master'))
        return result
    except Exception as e:
        logger.error(f"Error updating master output: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/monitor")
async def update_monitor_settings(
    request: MonitorRequest,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Update monitor/cue output settings"""
    try:
        result = await mixer_manager.update_monitor_settings(request.volume, request.cue_mix)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update monitor'))
        return result
    except Exception as e:
        logger.error(f"Error updating monitor settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/levels", response_model=AllLevelsResponse)
async def get_all_channel_levels(mixer_manager: MixerManager = Depends(get_mixer_manager)):
    """Get real-time level meters for all channels"""
    try:
        levels = await mixer_manager.get_all_channel_levels()
        return levels
    except Exception as e:
        logger.error(f"Error getting channel levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/channels/{deck_id}/cue", response_model=CueToggleResponse)
async def toggle_deck_cue(
    deck_id: str,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Toggle cue monitoring for a deck"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        result = await mixer_manager.toggle_deck_cue(deck_id)
        return CueToggleResponse(**result)
    except Exception as e:
        logger.error(f"Error toggling deck cue: {e}")
        return CueToggleResponse(
            success=False,
            deck_id=deck_id,
            cue_active=False,
            error=str(e)
        )


@router.post("/auto-gain/{deck_id}", response_model=AutoGainResponse)
async def apply_auto_gain(
    deck_id: str,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Calculate and apply auto-gain for a deck"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        result = await mixer_manager.auto_gain_deck(deck_id)
        return AutoGainResponse(**result)
    except Exception as e:
        logger.error(f"Error applying auto-gain: {e}")
        return AutoGainResponse(
            success=False,
            deck_id=deck_id,
            error=str(e)
        )


@router.post("/auto-gain/all")
async def apply_auto_gain_all(mixer_manager: MixerManager = Depends(get_mixer_manager)):
    """Apply auto-gain to all loaded decks"""
    results = {}
    for deck_id in ['A', 'B', 'C', 'D']:
        result = await mixer_manager.auto_gain_deck(deck_id)
        results[deck_id] = result
    
    return {
        'success': all(r.get('success', False) for r in results.values()),
        'results': results
    }


@router.post("/recording/start")
async def start_recording(
    request: RecordingRequest,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Start recording the master output"""
    try:
        result = await mixer_manager.start_recording(request.filepath)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to start recording'))
        return result
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recording/stop")
async def stop_recording(mixer_manager: MixerManager = Depends(get_mixer_manager)):
    """Stop recording"""
    try:
        result = await mixer_manager.stop_recording()
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to stop recording'))
        return result
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channel/{deck_id}/level", response_model=ChannelLevelResponse)
async def get_channel_level(
    deck_id: str,
    mixer_manager: MixerManager = Depends(get_mixer_manager)
):
    """Get output level for a specific channel"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        level = await mixer_manager.calculate_channel_output(deck_id)
        return level
    except Exception as e:
        logger.error(f"Error getting channel level: {e}")
        raise HTTPException(status_code=500, detail=str(e))
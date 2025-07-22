"""
Deck Router - API endpoints for deck management and control.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging

from models import init_db
from services.deck_manager import DeckManager


# Create router
router = APIRouter(prefix="/api/decks", tags=["Deck Control"])

# Logger
logger = logging.getLogger(__name__)

# Database dependency
_engine = None

async def get_engine():
    global _engine
    if _engine is None:
        _engine = await init_db()
    return _engine

async def get_deck_manager():
    engine = await get_engine()
    deck_manager = DeckManager(engine)
    # Create mixer manager and set cross-references
    from services.mixer_manager import MixerManager
    mixer_manager = MixerManager(engine)
    deck_manager.set_mixer_manager(mixer_manager)
    return deck_manager


# Request/Response models
class LoadTrackRequest(BaseModel):
    track_filepath: str


class UpdateDeckStateRequest(BaseModel):
    position: Optional[float] = None
    position_normalized: Optional[float] = None
    is_playing: Optional[bool] = None
    tempo_adjust: Optional[float] = None
    volume: Optional[float] = None
    gain: Optional[float] = None
    eq_low: Optional[float] = None
    eq_mid: Optional[float] = None
    eq_high: Optional[float] = None
    filter_cutoff: Optional[float] = None
    sync_mode: Optional[str] = None
    looping: Optional[bool] = None
    loop_in: Optional[float] = None
    loop_out: Optional[float] = None
    cue_points: Optional[Dict[str, float]] = None
    effects_enabled: Optional[List[str]] = None


class SyncDecksRequest(BaseModel):
    leader_deck_id: str
    follower_deck_id: str


class MixerUpdateRequest(BaseModel):
    crossfader: Optional[float] = None
    crossfader_curve: Optional[str] = None
    master_volume: Optional[float] = None
    master_gain: Optional[float] = None
    monitor_volume: Optional[float] = None
    monitor_cue_mix: Optional[float] = None
    recording: Optional[bool] = None
    broadcasting: Optional[bool] = None


class DeckStateResponse(BaseModel):
    id: str
    status: str
    track_id: Optional[int] = None
    track_filepath: Optional[str] = None
    position: float
    position_normalized: float
    is_playing: bool
    bpm: Optional[float] = None
    original_bpm: Optional[float] = None
    tempo_adjust: float
    volume: float
    gain: float
    eq_low: float
    eq_mid: float
    eq_high: float
    sync_mode: str
    cue_points: Dict[str, float]
    effects_enabled: List[str]
    loaded_at: Optional[str] = None
    track_info: Optional[Dict[str, Any]] = None


class LoadTrackResponse(BaseModel):
    success: bool
    deck_id: str
    track: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DeckHistoryEntry(BaseModel):
    id: int
    track_filepath: str
    loaded_at: Optional[str]
    started_playing_at: Optional[str]
    stopped_playing_at: Optional[str]
    play_duration: Optional[float]
    tempo_adjust_used: Optional[float]
    effects_used: List[str]
    transition_in_type: Optional[str]
    transition_out_type: Optional[str]


class MixPointResponse(BaseModel):
    success: bool
    deck_a: Optional[Dict[str, Any]]
    deck_b: Optional[Dict[str, Any]]
    transition_duration: Optional[float]
    error: Optional[str]


# Endpoints

@router.get("/", response_model=List[DeckStateResponse])
async def get_all_decks(deck_manager: DeckManager = Depends(get_deck_manager)):
    """Get the current state of all decks"""
    try:
        decks = await deck_manager.get_all_decks()
        return decks
    except Exception as e:
        logger.error(f"Error getting all decks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deck_id}", response_model=DeckStateResponse)
async def get_deck_state(deck_id: str, deck_manager: DeckManager = Depends(get_deck_manager)):
    """Get the current state of a specific deck"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        state = await deck_manager.get_deck_state(deck_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")
        return state
    except Exception as e:
        logger.error(f"Error getting deck state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deck_id}/load", response_model=LoadTrackResponse)
async def load_track(
    deck_id: str, 
    request: LoadTrackRequest,
    deck_manager: DeckManager = Depends(get_deck_manager)
):
    """Load a track onto a deck"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        result = await deck_manager.load_track(deck_id, request.track_filepath)
        return result
    except Exception as e:
        logger.error(f"Error loading track: {e}")
        return LoadTrackResponse(
            success=False,
            deck_id=deck_id,
            track=None,
            error=str(e)
        )


@router.post("/{deck_id}/clear")
async def clear_deck(deck_id: str, deck_manager: DeckManager = Depends(get_deck_manager)):
    """Clear a deck"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        result = await deck_manager.clear_deck(deck_id)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to clear deck'))
        return result
    except Exception as e:
        logger.error(f"Error clearing deck: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{deck_id}/state")
async def update_deck_state(
    deck_id: str,
    request: UpdateDeckStateRequest,
    deck_manager: DeckManager = Depends(get_deck_manager)
):
    """Update deck state (position, tempo, volume, etc)"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        # Convert request to dict, excluding None values
        updates = request.dict(exclude_none=True)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = await deck_manager.update_deck_state(deck_id, updates)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update deck'))
        return result
    except Exception as e:
        logger.error(f"Error updating deck state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deck_id}/history", response_model=List[DeckHistoryEntry])
async def get_deck_history(
    deck_id: str,
    limit: int = 50,
    deck_manager: DeckManager = Depends(get_deck_manager)
):
    """Get play history for a deck"""
    if deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID. Must be A, B, C, or D")
    
    try:
        history = await deck_manager.get_deck_history(deck_id, limit)
        return history
    except Exception as e:
        logger.error(f"Error getting deck history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_decks(
    request: SyncDecksRequest,
    deck_manager: DeckManager = Depends(get_deck_manager)
):
    """Sync two decks for beatmatching"""
    if request.leader_deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid leader deck ID")
    if request.follower_deck_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid follower deck ID")
    if request.leader_deck_id == request.follower_deck_id:
        raise HTTPException(status_code=400, detail="Cannot sync deck with itself")
    
    try:
        result = await deck_manager.sync_decks(request.leader_deck_id, request.follower_deck_id)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to sync decks'))
        return result
    except Exception as e:
        logger.error(f"Error syncing decks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mixer/state")
async def get_mixer_state(deck_manager: DeckManager = Depends(get_deck_manager)):
    """Get current mixer state"""
    try:
        state = await deck_manager.get_mixer_state()
        if not state:
            raise HTTPException(status_code=404, detail="Mixer state not found")
        return state
    except Exception as e:
        logger.error(f"Error getting mixer state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mixer/state")
async def update_mixer_state(
    request: MixerUpdateRequest,
    deck_manager: DeckManager = Depends(get_deck_manager)
):
    """Update mixer state"""
    try:
        updates = request.dict(exclude_none=True)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = await deck_manager.update_mixer_state(updates)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update mixer'))
        return result
    except Exception as e:
        logger.error(f"Error updating mixer state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mix-point/{deck_a_id}/{deck_b_id}", response_model=MixPointResponse)
async def calculate_mix_point(
    deck_a_id: str,
    deck_b_id: str,
    deck_manager: DeckManager = Depends(get_deck_manager)
):
    """Calculate optimal mix point between two decks"""
    if deck_a_id not in ['A', 'B', 'C', 'D'] or deck_b_id not in ['A', 'B', 'C', 'D']:
        raise HTTPException(status_code=400, detail="Invalid deck ID")
    if deck_a_id == deck_b_id:
        raise HTTPException(status_code=400, detail="Cannot calculate mix point for same deck")
    
    try:
        result = await deck_manager.calculate_mix_point(deck_a_id, deck_b_id)
        return MixPointResponse(**result)
    except Exception as e:
        logger.error(f"Error calculating mix point: {e}")
        return MixPointResponse(
            success=False,
            deck_a=None,
            deck_b=None,
            transition_duration=None,
            error=str(e)
        )
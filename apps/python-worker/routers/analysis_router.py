"""
Analysis Router - API endpoints for track analysis and real-time monitoring.
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
import json
import asyncio

from services.analysis_service import AnalysisService
from agents.realtime_analysis_agent import RealTimeAnalysisAgent
from utils.enhanced_analyzer import StreamingAnalysisResult
from services.service_manager import service_manager

# Create router
router = APIRouter(prefix="/api/analysis", tags=["Track Analysis"])

# Logger
logger = logging.getLogger(__name__)

async def get_analysis_service():
    """Get the singleton AnalysisService instance"""
    return await service_manager.get_analysis_service()


# Request/Response models
class AnalyzeTrackRequest(BaseModel):
    filepath: str
    priority: int = 2
    deck_id: Optional[str] = None
    analysis_type: str = "full"  # "full" or "realtime"


class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[float] = None
    deck_id: Optional[str] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class AnalysisResultResponse(BaseModel):
    filepath: str
    bpm: Optional[float] = None
    key: Optional[str] = None
    camelot_key: Optional[str] = None
    energy_level: Optional[float] = None
    energy_profile: Optional[str] = None
    beat_times: Optional[List[float]] = None
    hot_cues: Optional[List[Dict]] = None
    structure: Optional[Dict] = None


class TransitionAnalysisRequest(BaseModel):
    deck_a_id: str
    deck_b_id: str


class TransitionAnalysisResponse(BaseModel):
    compatibility: Dict[str, float]
    transition_points: List[Dict[str, Any]]
    recommended_effects: List[Dict[str, Any]]


class QueueStatusResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    total: int
    queue_size: int
    workers: int
    running: bool


# Endpoints

@router.post("/track", response_model=AnalysisStatusResponse)
async def analyze_track(
    request: AnalyzeTrackRequest,
    service: AnalysisService = Depends(get_analysis_service)
):
    """Trigger analysis for a specific track."""
    try:
        # Enqueue analysis task
        task_id = await service.enqueue_analysis(
            filepath=request.filepath,
            priority=request.priority,
            deck_id=request.deck_id,
            analysis_type=request.analysis_type
        )
        
        # Get initial status
        status = await service.get_task_status(task_id)
        
        return AnalysisStatusResponse(
            task_id=task_id,
            status=status["status"],
            created_at=status["created_at"],
            deck_id=status.get("deck_id")
        )
        
    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    task_id: str,
    service: AnalysisService = Depends(get_analysis_service)
):
    """Check the status of an analysis task."""
    try:
        status = await service.get_task_status(task_id)
        
        if status["status"] == "unknown":
            raise HTTPException(status_code=404, detail="Task not found")
        
        return AnalysisStatusResponse(task_id=task_id, **status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GetResultsRequest(BaseModel):
    filepath: str


@router.post("/results", response_model=AnalysisResultResponse)
async def get_analysis_results(
    request: GetResultsRequest,
    service: AnalysisService = Depends(get_analysis_service)
):
    """Get cached analysis results for a track."""
    try:
        results = await service.get_cached_analysis(request.filepath)
        
        if not results:
            raise HTTPException(
                status_code=404, 
                detail="No analysis results found. Please trigger analysis first."
            )
        
        return AnalysisResultResponse(filepath=request.filepath, **results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition", response_model=TransitionAnalysisResponse)
async def analyze_transition(
    request: TransitionAnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service)
):
    """Analyze transition compatibility between two decks."""
    try:
        # Create analysis agent
        agent = RealTimeAnalysisAgent(service)
        
        # Get current deck states (simplified for now)
        # In real implementation, would get from DeckManager
        state = {
            "decks": {
                request.deck_a_id: {"track_filepath": "track_a.mp3"},  # Placeholder
                request.deck_b_id: {"track_filepath": "track_b.mp3"}   # Placeholder
            }
        }
        
        # Perform transition analysis
        result = await agent.analyze_for_transition(
            request.deck_a_id,
            request.deck_b_id,
            state
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return TransitionAnalysisResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing transition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status(
    service: AnalysisService = Depends(get_analysis_service)
):
    """Get current analysis queue statistics."""
    try:
        status = service.get_queue_status()
        return QueueStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream/{deck_id}")
async def stream_analysis(
    websocket: WebSocket,
    deck_id: str,
    service: AnalysisService = Depends(get_analysis_service)
):
    """WebSocket endpoint for streaming live analysis data."""
    await websocket.accept()
    
    try:
        logger.info(f"WebSocket connected for deck {deck_id} analysis stream")
        
        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "deck_id": deck_id
        })
        
        # Create analysis agent
        agent = RealTimeAnalysisAgent(service)
        
        # Stream analysis updates
        while True:
            try:
                # Check for deck state changes
                # In real implementation, would subscribe to deck events
                
                # Send periodic updates
                await asyncio.sleep(0.5)  # 500ms update interval
                
                # Get current analysis status for deck
                if deck_id in agent.active_analyses:
                    task_id = agent.active_analyses[deck_id]
                    status = await service.get_task_status(task_id)
                    
                    await websocket.send_json({
                        "type": "analysis_update",
                        "deck_id": deck_id,
                        "status": status["status"],
                        "progress": status.get("progress", 0),
                        "results": status.get("results")
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in analysis stream: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket disconnected for deck {deck_id}")


@router.post("/batch")
async def analyze_batch(
    filepaths: List[str],
    priority: int = 3,
    service: AnalysisService = Depends(get_analysis_service)
):
    """Queue multiple tracks for analysis."""
    try:
        task_ids = []
        
        for filepath in filepaths:
            task_id = await service.enqueue_analysis(
                filepath=filepath,
                priority=priority,
                analysis_type="full"
            )
            task_ids.append(task_id)
        
        return {
            "queued": len(task_ids),
            "task_ids": task_ids
        }
        
    except Exception as e:
        logger.error(f"Error queuing batch analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BeatPhaseRequest(BaseModel):
    filepath: str
    position: float


@router.post("/beat-phase")
async def get_beat_phase(
    request: BeatPhaseRequest,
    service: AnalysisService = Depends(get_analysis_service)
):
    """Calculate beat phase information for a specific position in a track."""
    try:
        # Get cached analysis
        analysis = await service.get_cached_analysis(request.filepath)
        
        if not analysis or "beat_times" not in analysis:
            raise HTTPException(
                status_code=404,
                detail="Beat analysis not available for this track"
            )
        
        # Calculate beat phase
        from utils.enhanced_analyzer import EnhancedTrackAnalyzer
        analyzer = EnhancedTrackAnalyzer("")  # Don't need DB for this
        
        phase_info = analyzer.analyze_beat_phase(
            request.position,
            analysis["beat_times"],
            analysis.get("bpm", 120)
        )
        
        return phase_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating beat phase: {e}")
        raise HTTPException(status_code=500, detail=str(e))
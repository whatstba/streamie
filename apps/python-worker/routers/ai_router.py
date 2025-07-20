"""
AI DJ Router - API endpoints for the LangGraph DJ agent.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

from agents.dj_agent import DJAgent


# Create router
router = APIRouter(prefix="/ai", tags=["AI DJ"])

# Initialize the DJ agent
dj_agent = DJAgent()


# Request/Response models
class VibeAnalysisRequest(BaseModel):
    current_track_id: str
    context: Optional[Dict] = None


class PlaylistGenerationRequest(BaseModel):
    seed_track_id: str
    playlist_length: int = 10
    energy_pattern: str = "wave"  # "build_up", "peak_time", "cool_down", "wave"
    context: Optional[Dict] = None


class NextTrackRequest(BaseModel):
    current_track_id: str
    played_tracks: List[str] = []
    desired_vibe: Optional[str] = None
    context: Optional[Dict] = None


class TransitionRatingRequest(BaseModel):
    from_track_id: str
    to_track_id: str
    rating: float  # 0-1
    notes: Optional[str] = None


class VibeAnalysisResponse(BaseModel):
    track_id: str
    bpm: float
    energy_level: float
    dominant_vibe: str
    mood_vector: Dict[str, float]
    genre: str
    recommendations: List[str]


class TrackSuggestion(BaseModel):
    track: Dict
    confidence: float
    transition: Optional[Dict] = None
    reasoning: Optional[str] = None


class PlaylistResponse(BaseModel):
    playlist: List[Dict]
    transitions: List[Dict]
    energy_flow: List[float]
    vibe_analysis: Dict


@router.post("/analyze-vibe", response_model=VibeAnalysisResponse)
async def analyze_vibe(request: VibeAnalysisRequest):
    """Analyze the vibe of the current track and get recommendations."""
    try:
        # Get suggestion which includes vibe analysis
        result = await dj_agent.suggest_next_track(
            request.current_track_id, request.context
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        vibe = result["vibe_analysis"]

        # Get top 5 recommendations
        full_playlist = await dj_agent.generate_playlist(
            request.current_track_id,
            length=5,
            energy_pattern="wave",
            context=request.context,
        )

        recommendations = [track["filepath"] for track in full_playlist["playlist"]]

        return VibeAnalysisResponse(
            track_id=vibe["track_id"],
            bpm=vibe["bpm"],
            energy_level=vibe["energy_level"],
            dominant_vibe=vibe["dominant_vibe"],
            mood_vector=vibe["mood_vector"],
            genre=vibe["genre"],
            recommendations=recommendations,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-playlist", response_model=PlaylistResponse)
async def generate_playlist(request: PlaylistGenerationRequest):
    """Generate an intelligent playlist from a seed track."""
    try:
        result = await dj_agent.generate_playlist(
            seed_track_id=request.seed_track_id,
            length=request.playlist_length,
            energy_pattern=request.energy_pattern,
            context=request.context,
        )

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return PlaylistResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-next-track", response_model=TrackSuggestion)
async def suggest_next_track(request: NextTrackRequest):
    """Get AI suggestion for the next track to play."""
    try:
        # Enhance context with played tracks and desired vibe
        context = request.context or {}
        context["played_tracks"] = request.played_tracks
        if request.desired_vibe:
            context["desired_vibe"] = request.desired_vibe

        result = await dj_agent.suggest_next_track(request.current_track_id, context)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # Add reasoning based on the analysis
        reasoning = (
            f"Selected based on {result['vibe_analysis']['dominant_vibe']} vibe, "
        )
        reasoning += f"{result['confidence']:.0%} confidence match"

        return TrackSuggestion(
            track=result["track"],
            confidence=result["confidence"],
            transition=result["transition"],
            reasoning=reasoning,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-transition")
async def rate_transition(request: TransitionRatingRequest):
    """Rate a transition to improve future suggestions."""
    try:
        # Store the rating in the database for learning
        from utils.db import get_db

        db = get_db()

        rating_doc = {
            "from_track": request.from_track_id,
            "to_track": request.to_track_id,
            "rating": request.rating,
            "notes": request.notes,
            "timestamp": asyncio.get_event_loop().time(),
        }

        db.transition_ratings.insert_one(rating_doc)

        # Update mixing history for both tracks
        db.tracks.update_one(
            {"filepath": request.from_track_id},
            {
                "$push": {
                    "mixing_history": {
                        "to_track": request.to_track_id,
                        "rating": request.rating,
                    }
                }
            },
        )

        return {"success": True, "message": "Rating recorded"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mixing-insights")
async def get_mixing_insights():
    """Get insights from mixing history and patterns."""
    try:
        from utils.db import get_db

        db = get_db()

        # Aggregate successful transitions
        pipeline = [
            {"$match": {"rating": {"$gte": 0.7}}},
            {
                "$group": {
                    "_id": {"from": "$from_track", "to": "$to_track"},
                    "avg_rating": {"$avg": "$rating"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"avg_rating": -1}},
            {"$limit": 10},
        ]

        top_transitions = list(db.transition_ratings.aggregate(pipeline))

        # Get most mixed tracks
        most_mixed = db.tracks.aggregate(
            [
                {
                    "$project": {
                        "filepath": 1,
                        "title": 1,
                        "artist": 1,
                        "mix_count": {"$size": {"$ifNull": ["$mixing_history", []]}},
                    }
                },
                {"$sort": {"mix_count": -1}},
                {"$limit": 10},
            ]
        )

        return {
            "top_transitions": top_transitions,
            "most_mixed_tracks": list(most_mixed),
            "total_ratings": db.transition_ratings.count_documents({}),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
LangGraph DJ Agent for intelligent playlist and vibe management.
"""

from typing import TypedDict, List, Dict, Optional, Annotated, Sequence, Union
from datetime import datetime
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import numpy as np
import logging
import json
import sqlite3
import os

from utils.sqlite_db import get_sqlite_db
from utils.dj_llm import DJLLMService, VibeAnalysis, TrackEvaluation

# Configure logging for the DJ agent
logger = logging.getLogger("DJAgent")
logger.setLevel(logging.DEBUG)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "🎧 [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class DJAgentState(TypedDict):
    """State for the DJ agent."""

    current_track: Optional[Dict]
    context: Dict
    track_history: List[Dict]
    candidate_tracks: List[Dict]
    playlist: List[Dict]
    transitions: List[Dict]
    messages: Annotated[Sequence[BaseMessage], operator.add]
    vibe_analysis: Optional[Dict]
    energy_pattern: str
    vibe_description: Optional[str]
    final_response: Optional[str]
    finalized_playlist: Optional[List[Dict]]
    transition_plan: Optional[Dict]  # New: Hot cue transition planning
    hot_cue_analysis: Optional[Dict]  # New: Hot cue compatibility analysis


# Define tools for the agentic approach


async def analyze_hot_cue_transitions(track_filepaths: List[str]) -> Dict:
    """Analyze hot cue compatibility for transitions between consecutive tracks."""
    try:
        import json

        logger.info(
            f"🎛️ Analyzing hot cue transitions for {len(track_filepaths)} tracks"
        )

        transition_analysis = {
            "transitions": [],
            "total_tracks": len(track_filepaths),
            "tracks_with_hot_cues": 0,
            "optimal_transitions": 0,
            "recommendations": [],
        }

        # Get database connection for full file paths
        db_path = os.path.join(os.path.dirname(__file__), "..", "tracks.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Analyze each consecutive pair of tracks
        for i in range(len(track_filepaths) - 1):
            current_filepath = track_filepaths[i]
            next_filepath = track_filepaths[i + 1]

            logger.info(
                f"Analyzing transition {i + 1}: {current_filepath} -> {next_filepath}"
            )

            # Get full track data including BPM
            cursor.execute(
                "SELECT * FROM tracks WHERE filepath = ?", (current_filepath,)
            )
            current_track_data = cursor.fetchone()

            cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (next_filepath,))
            next_track_data = cursor.fetchone()

            if not current_track_data or not next_track_data:
                logger.warning(f"Missing track data for transition {i + 1}")
                continue

            # Convert to dict
            columns = [description[0] for description in cursor.description]
            current_track = dict(zip(columns, current_track_data))
            next_track = dict(zip(columns, next_track_data))

            # Get hot cue data from database (already stored from enhanced analysis)
            try:
                current_hot_cues = []
                next_hot_cues = []

                # Parse hot cues from database
                if current_track.get("hot_cues") and isinstance(
                    current_track["hot_cues"], str
                ):
                    try:
                        current_hot_cues = json.loads(current_track["hot_cues"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                if next_track.get("hot_cues") and isinstance(
                    next_track["hot_cues"], str
                ):
                    try:
                        next_hot_cues = json.loads(next_track["hot_cues"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                if current_hot_cues:
                    transition_analysis["tracks_with_hot_cues"] += 1
                if (
                    next_hot_cues and i == len(track_filepaths) - 2
                ):  # Count last track too
                    transition_analysis["tracks_with_hot_cues"] += 1

                # Analyze transition compatibility
                transition_info = await analyze_transition_compatibility(
                    current_track, next_track, current_hot_cues, next_hot_cues
                )

                transition_analysis["transitions"].append(
                    {
                        "position": i + 1,
                        "current_track": {
                            "filepath": current_filepath,
                            "title": current_track.get("title", "Unknown"),
                            "artist": current_track.get("artist", "Unknown"),
                            "bpm": current_track.get("bpm"),
                            "hot_cues_count": len(current_hot_cues),
                        },
                        "next_track": {
                            "filepath": next_filepath,
                            "title": next_track.get("title", "Unknown"),
                            "artist": next_track.get("artist", "Unknown"),
                            "bpm": next_track.get("bpm"),
                            "hot_cues_count": len(next_hot_cues),
                        },
                        "compatibility": transition_info,
                    }
                )

                if transition_info.get("score", 0) > 0.6:
                    transition_analysis["optimal_transitions"] += 1

            except Exception as e:
                logger.error(f"Error analyzing hot cues for transition {i + 1}: {e}")
                continue

        cursor.close()
        conn.close()

        # Generate recommendations
        optimal_ratio = transition_analysis["optimal_transitions"] / max(
            1, len(transition_analysis["transitions"])
        )

        if optimal_ratio > 0.7:
            transition_analysis["recommendations"].append(
                "Excellent hot cue coverage! Most transitions will be smooth."
            )
        elif optimal_ratio > 0.4:
            transition_analysis["recommendations"].append(
                "Good hot cue coverage. Some transitions may need manual adjustment."
            )
        else:
            transition_analysis["recommendations"].append(
                "Limited hot cue data. Consider using BPM-based transitions as fallback."
            )

        if transition_analysis["tracks_with_hot_cues"] < len(track_filepaths) * 0.5:
            transition_analysis["recommendations"].append(
                "Consider tracks with more Serato hot cue data for better transitions."
            )

        logger.info(
            f"✅ Hot cue analysis complete: {transition_analysis['optimal_transitions']}/{len(transition_analysis['transitions'])} optimal transitions"
        )
        return transition_analysis

    except Exception as e:
        logger.error(f"Error in hot cue analysis: {e}")
        return {"error": str(e), "transitions": []}


async def analyze_transition_compatibility(
    current_track: Dict,
    next_track: Dict,
    current_hot_cues: List[Dict],
    next_hot_cues: List[Dict],
) -> Dict:
    """Analyze compatibility between two tracks for transition planning using AI."""
    from utils.dj_llm import DJLLMService

    dj_service = DJLLMService()

    compatibility = {
        "score": 0.0,
        "bpm_compatible": False,
        "hot_cue_compatible": False,
        "recommended_effects": [],
        "optimal_outro_cue": None,
        "optimal_intro_cue": None,
        "notes": [],
        "effect_plan": {"profile": "standard", "effects": [], "reasoning": ""},
    }

    # Get AI-powered transition plan
    try:
        # Determine DJ style based on context
        dj_style = "smooth"  # Default
        current_genre = current_track.get("genre", "").lower()
        next_genre = next_track.get("genre", "").lower()

        if any(
            g in current_genre + next_genre for g in ["techno", "hard", "industrial"]
        ):
            dj_style = "aggressive"
        elif any(
            g in current_genre + next_genre for g in ["experimental", "ambient", "idm"]
        ):
            dj_style = "creative"

        # Get AI transition plan
        transition_plan = await dj_service.plan_transition(
            current_track, next_track, dj_style
        )

        # Convert AI plan to compatibility format
        compatibility["score"] = transition_plan.compatibility_score
        compatibility["bpm_compatible"] = transition_plan.compatibility_score > 0.5

        # Extract effects and timing
        compatibility["effect_plan"] = {
            "profile": transition_plan.transition_type,
            "effects": [
                {
                    "type": effect.type,
                    "start_at": effect.start_at,
                    "duration": effect.duration,
                    "intensity": effect.intensity,
                }
                if hasattr(effect, "type")
                else effect
                for effect in transition_plan.effects
            ],
            "reasoning": transition_plan.technique_notes,
        }

        # Add professional notes
        compatibility["notes"].append(transition_plan.technique_notes)

        # Extract recommended effects from AI plan
        for effect in transition_plan.effects:
            effect_type = effect.type if hasattr(effect, "type") else effect.get("type")
            if effect_type and effect_type not in compatibility["recommended_effects"]:
                compatibility["recommended_effects"].append(effect_type)

        # Add risk assessment
        if transition_plan.risk_level == "adventurous":
            compatibility["notes"].append("⚠️ Advanced technique - practice recommended")

    except Exception as e:
        logger.error(f"AI transition planning failed: {e}")
        # Fallback to basic BPM analysis
        current_bpm = current_track.get("bpm")
        next_bpm = next_track.get("bpm")

        if current_bpm and next_bpm:
            bpm_diff = abs(current_bpm - next_bpm)
            if bpm_diff <= 5:
                compatibility["score"] = 0.8
                compatibility["bpm_compatible"] = True
                compatibility["effect_plan"] = {
                    "profile": "smooth_blend",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 2.0,
                            "duration": 4.0,
                            "intensity": 0.25,
                        }
                    ],
                    "reasoning": "Close BPM match allows smooth transition",
                }
            elif bpm_diff <= 15:
                compatibility["score"] = 0.6
                compatibility["bpm_compatible"] = True
                compatibility["effect_plan"] = {
                    "profile": "tempo_blend",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 0.0,
                            "duration": 5.0,
                            "intensity": 0.35,
                        },
                    ],
                    "reasoning": "Medium BPM difference requires filter transition",
                }
            else:
                compatibility["score"] = 0.3
                compatibility["effect_plan"] = {
                    "profile": "energy_shift",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 0.0,
                            "duration": 6.0,
                            "intensity": 0.45,
                        }
                    ],
                    "reasoning": "Large BPM gap requires careful transition",
                }

    # Hot cue compatibility analysis (kept as is for now)
    if current_hot_cues and next_hot_cues:
        current_duration = current_track.get("duration", 300)  # Default 5 minutes

        # Find outro hot cues (last 40% of track)
        outro_cues = [
            cue for cue in current_hot_cues if cue["time"] > current_duration * 0.6
        ]

        # Find intro hot cues (first 2 minutes)
        intro_cues = [cue for cue in next_hot_cues if cue["time"] < 120]

        if outro_cues and intro_cues:
            compatibility["hot_cue_compatible"] = True
            compatibility["score"] = min(1.0, compatibility["score"] + 0.2)

            # Simply use the first available cues
            if outro_cues and intro_cues:
                compatibility["optimal_outro_cue"] = outro_cues[0]
                compatibility["optimal_intro_cue"] = intro_cues[0]
                compatibility["notes"].append(
                    f"Hot cue transition: {outro_cues[0]['name']} -> {intro_cues[0]['name']}"
                )

                # AI might recommend scratch for phrase transitions
                if (
                    outro_cues[0].get("type") == "phrase"
                    and intro_cues[0].get("type") == "phrase"
                ):
                    if "scratch" not in compatibility["recommended_effects"]:
                        compatibility["recommended_effects"].append("scratch")
                    compatibility["notes"].append(
                        "Phrase-to-phrase transition - scratch effect recommended"
                    )

    elif current_hot_cues or next_hot_cues:
        compatibility["score"] += 0.1
        compatibility["notes"].append("Partial hot cue data available")

    return compatibility


@tool
async def search_tracks_by_vibe(vibe_keywords: str, limit: int = 20) -> List[Dict]:
    """Search for tracks that match the given vibe keywords using AI analysis.

    Args:
        vibe_keywords: Keywords describing the desired vibe (e.g., "chill relaxing smooth")
        limit: Maximum number of tracks to return

    Returns:
        List of tracks matching the vibe
    """
    logger.info(
        f"🔍 AI-Powered track search for vibe: '{vibe_keywords}' (limit: {limit})"
    )

    # Initialize DJ LLM service
    dj_service = DJLLMService()

    # Genre mapper no longer needed - AI now uses exact database genres

    # Get AI vibe analysis
    try:
        vibe_analysis = await dj_service.analyze_vibe(vibe_keywords)
        logger.info(
            f"   🤖 AI Vibe Analysis: Energy={vibe_analysis.energy_level:.2f}, "
            f"Mood={vibe_analysis.mood_keywords}, BPM={vibe_analysis.bpm_range}"
        )
    except Exception as e:
        logger.error(f"   ❌ AI analysis failed, using fallback: {e}")
        # Fallback to basic analysis
        vibe_analysis = VibeAnalysis(
            energy_level=0.5,
            energy_progression="steady",
            mood_keywords=vibe_keywords.lower().split(),
            genre_preferences=[],  # Empty list means no genre filtering
            bpm_range={"min": 100, "max": 140},
            mixing_style="smooth",
        )

    db = get_sqlite_db()
    cursor = db.adapter.connection.cursor()

    # Build intelligent query based on AI analysis
    query_conditions = []
    order_by = []

    # TODO: Add energy level filtering once values are populated using librosa/essentia
    # For now, we'll query by BPM only

    # BPM-based filtering
    if vibe_analysis.bpm_range:
        query_conditions.append(
            f"(bpm BETWEEN {vibe_analysis.bpm_range['min']} AND {vibe_analysis.bpm_range['max']} OR bpm IS NULL)"
        )

    # Genre filtering if specified and not empty
    if vibe_analysis.genre_preferences and len(vibe_analysis.genre_preferences) > 0:
        # Use exact genre matching (AI now provides exact database genres)
        genre_conditions = " OR ".join(
            [f"genre = '{g}'" for g in vibe_analysis.genre_preferences[:3]]
        )
        query_conditions.append(f"({genre_conditions})")
        logger.debug(
            f"   📊 Using genres: {vibe_analysis.genre_preferences}"
        )

    # Combine conditions
    where_clause = " AND ".join(query_conditions) if query_conditions else "1=1"
    logger.debug(f"   📊 Query conditions: {query_conditions}")
    logger.debug(f"   📊 Where clause: {where_clause}")

    # Smart ordering based on vibe
    # TODO: Use energy_level once values are populated
    # For now, use BPM as a proxy for energy
    if vibe_analysis.energy_progression == "building":
        order_by.append("bpm ASC")  # Lower BPM first, building up
    elif vibe_analysis.energy_progression == "cooling":
        order_by.append("bpm DESC")  # Higher BPM first, cooling down
    else:
        # Order by closeness to target BPM (middle of range)
        if vibe_analysis.bpm_range:
            target_bpm = (
                vibe_analysis.bpm_range["min"] + vibe_analysis.bpm_range["max"]
            ) / 2
            order_by.append(f"ABS(COALESCE(bpm, 120) - {target_bpm})")
        else:
            order_by.append("RANDOM()")

    order_clause = ", ".join(order_by) if order_by else "RANDOM()"

    # Execute intelligent query
    query = f"""
        SELECT * FROM tracks 
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT ?
    """

    logger.debug(f"   📊 Executing AI-driven query: {query}")
    logger.debug(f"   📊 Query limit: {limit * 2}")
    cursor.execute(query, (limit * 2,))  # Get extra for AI filtering

    columns = [description[0] for description in cursor.description]
    all_tracks = []
    rows = cursor.fetchall()
    logger.debug(f"   📊 Raw query returned {len(rows)} rows")

    for row in rows:
        track = dict(zip(columns, row))
        # Parse beat_times if it's a JSON string
        if track.get("beat_times") and isinstance(track["beat_times"], str):
            try:
                track["beat_times"] = json.loads(track["beat_times"])
            except (json.JSONDecodeError, TypeError):
                track["beat_times"] = []

        # Always estimate energy since database values might be NULL
        # TODO: Store calculated energy values back to database
        track["energy_level"] = dj_service.estimate_energy_from_features(
            track.get("bpm"), track.get("genre")
        )

        all_tracks.append(track)

    cursor.close()

    # Let AI evaluate and rank tracks
    evaluated_tracks = []
    for track in all_tracks[: limit * 2]:  # Evaluate up to 2x limit
        try:
            evaluation = await dj_service.evaluate_track(track, vibe_analysis)
            if evaluation.score > 0.3:  # Only include decent matches
                evaluated_tracks.append({"track": track, "evaluation": evaluation})
        except Exception:
            # Fallback: include with default score
            evaluated_tracks.append(
                {
                    "track": track,
                    "evaluation": TrackEvaluation(
                        score=0.5,
                        reasoning="Evaluation skipped",
                        energy_match=0.5,
                        suggested_position=None,
                        mixing_notes="Standard mix",
                    ),
                }
            )

    # Sort by AI score and take top tracks
    evaluated_tracks.sort(key=lambda x: x["evaluation"].score, reverse=True)
    final_tracks = [item["track"] for item in evaluated_tracks[:limit]]

    logger.info(
        f"   📊 AI selected {len(final_tracks)} tracks from {len(all_tracks)} candidates"
    )
    if final_tracks:
        # Log top selections with AI reasoning
        for i, item in enumerate(evaluated_tracks[:3]):
            track = item["track"]
            eval = item["evaluation"]
            logger.info(
                f"      {i + 1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} "
                f"({track.get('bpm', 0):.0f} BPM) [Score: {eval.score:.2f}] - {eval.reasoning}"
            )

    return final_tracks


@tool
async def get_track_details(track_filepath: str) -> Dict:
    """Get detailed information about a specific track.

    Args:
        track_filepath: The filepath of the track

    Returns:
        Detailed track information including BPM, energy, genre, etc.
    """
    # Run database operations in executor to prevent blocking
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def _get_track_sync(filepath):
        db = get_sqlite_db()
        cursor = db.adapter.connection.cursor()

        # Try multiple path variations to handle relative vs absolute paths
        path_variations = [
            filepath,  # Original path
            filepath.lstrip("/"),  # Remove leading slash
            "/" + filepath.lstrip("/"),  # Ensure leading slash
            filepath.replace("\\", "/"),  # Windows to Unix path
        ]

        # If it looks like a relative path starting with PLAYLISTS, try with common prefixes
        if filepath.startswith("PLAYLISTS/"):
            path_variations.extend(
                [
                    "../../../../Downloads/" + filepath,
                    "../../../Downloads/" + filepath,
                    "../../Downloads/" + filepath,
                    "../Downloads/" + filepath,
                    "Downloads/" + filepath,
                ]
            )

        row = None
        for path in path_variations:
            cursor.execute(
                "SELECT * FROM tracks WHERE filepath = ? OR filepath LIKE ?",
                (path, "%" + path),
            )
            columns = [description[0] for description in cursor.description]
            row = cursor.fetchone()
            if row:
                break

        cursor.close()

        if row:
            return dict(zip(columns, row))
        return None

    # Run in executor
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, _get_track_sync, track_filepath)

    if not result:
        return {"error": "Track not found"}

    track = result

    # Parse beat_times if needed
    if track.get("beat_times") and isinstance(track["beat_times"], str):
        try:
            track["beat_times"] = json.loads(track["beat_times"])
        except (json.JSONDecodeError, TypeError):
            track["beat_times"] = []

    return track


@tool
async def filter_tracks_by_energy(
    tracks: List[Dict], target_energy: float, tolerance: float = 0.2
) -> List[Dict]:
    """Filter tracks by energy level using AI understanding of energy dynamics.

    Args:
        tracks: List of tracks to filter (each track is a dictionary with title, artist, filepath, etc.)
        target_energy: Target energy level (0-1)
        tolerance: Acceptable deviation from target

    Returns:
        Filtered list of tracks
    """
    # Handle different input formats
    if not isinstance(tracks, list):
        logger.warning(f"🎚️ Received non-list tracks: {type(tracks)}")
        return []
    
    # Ensure all items are dictionaries
    validated_tracks = []
    for track in tracks:
        if isinstance(track, dict):
            validated_tracks.append(track)
        else:
            logger.warning(f"🎚️ Skipping non-dict track: {type(track)}")
    
    logger.info(f"🎚️ AI filtering {len(validated_tracks)} tracks for energy {target_energy:.2f}")

    dj_service = DJLLMService()
    filtered = []

    # Create a simple vibe analysis for the target energy
    target_vibe = VibeAnalysis(
        energy_level=target_energy,
        energy_progression="steady",
        mood_keywords=["energetic" if target_energy > 0.6 else "chill"],
        genre_preferences=[],
        bpm_range={"min": 60, "max": 200},
        mixing_style="smooth",
    )

    for track in validated_tracks:
        # Always estimate energy since database values might be NULL
        # TODO: Store calculated energy values back to database
        track["energy_level"] = dj_service.estimate_energy_from_features(
            track.get("bpm"), track.get("genre")
        )

        # Use AI to evaluate if this track matches the target energy
        try:
            evaluation = await dj_service.evaluate_track(track, target_vibe)
            if evaluation.energy_match > (1 - tolerance):
                filtered.append(track)
                logger.debug(
                    f"   ✅ {track.get('title')} - Energy match: {evaluation.energy_match:.2f}"
                )
        except Exception:
            # Fallback to simple comparison
            energy = track.get("energy_level", 0.5)
            if abs(energy - target_energy) <= tolerance:
                filtered.append(track)

    logger.info(f"   📊 Filtered to {len(filtered)} tracks matching energy criteria")
    return filtered


@tool
async def finalize_playlist(
    track_filepaths: List[str],
    mixing_notes: Optional[List[str]] = None,
    vibe_description: Optional[str] = None,
) -> Dict:
    """Finalize the playlist with AI-powered professional curation and flow analysis.

    Args:
        track_filepaths: List of track filepaths for the final playlist
        mixing_notes: Optional list of mixing notes for each track
        vibe_description: Optional description of the desired vibe

    Returns:
        Dictionary with success status and AI-enhanced playlist details
    """
    from utils.dj_llm import DJLLMService
    import sqlite3
    import os

    logger.info(
        f"🎯 Finalizing playlist with {len(track_filepaths)} tracks using AI curation"
    )

    if not track_filepaths:
        return {"success": False, "error": "No tracks provided"}

    # Validate tracks are not fake
    fake_track_patterns = ["track_", "placeholder", "dummy", "fake"]
    fake_tracks = []
    invalid_tracks = []

    # Also check if tracks look like generic names (e.g., track_021.mp3)
    import re

    generic_pattern = re.compile(r"^track_\d+\.(mp3|wav|flac)$", re.IGNORECASE)

    for filepath in track_filepaths:
        filename = os.path.basename(filepath)

        # Check for fake patterns
        if any(pattern in filepath.lower() for pattern in fake_track_patterns):
            fake_tracks.append(filepath)
        # Check for generic names like track_021.mp3
        elif generic_pattern.match(filename):
            fake_tracks.append(filepath)
        # Check if it's just a filename without proper path
        elif "/" not in filepath and "\\" not in filepath:
            invalid_tracks.append(filepath)

    if fake_tracks:
        logger.error(f"❌ Fake/Generic tracks detected: {fake_tracks}")
        return {
            "success": False,
            "error": f"Invalid track names detected: {fake_tracks}. Please use real tracks from search results only.",
        }

    if invalid_tracks:
        logger.error(f"❌ Invalid track paths detected: {invalid_tracks}")
        return {
            "success": False,
            "error": f"Invalid track paths detected: {invalid_tracks}. Tracks must have proper file paths.",
        }

    # Remove duplicates while preserving order
    seen = set()
    unique_filepaths = []
    duplicate_indices = []

    for i, filepath in enumerate(track_filepaths):
        if filepath not in seen:
            seen.add(filepath)
            unique_filepaths.append(filepath)
        else:
            duplicate_indices.append(i)
            logger.warning(f"⚠️ Duplicate track found at position {i + 1}: {filepath}")

    # Get track metadata from database
    db_path = os.path.join(os.path.dirname(__file__), "..", "tracks.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    track_data = []
    missing_tracks = []

    for filepath in unique_filepaths:
        cursor.execute(
            """
            SELECT filepath, title, artist, bpm, key, energy_level, duration, genre
            FROM tracks WHERE filepath = ?
        """,
            (filepath,),
        )
        result = cursor.fetchone()

        if result:
            columns = [description[0] for description in cursor.description]
            track_dict = dict(zip(columns, result))
            track_data.append(track_dict)
        else:
            missing_tracks.append(filepath)
            logger.warning(f"⚠️ Track not found in database: {filepath}")

    conn.close()

    # If any tracks are missing from database, fail the operation
    if missing_tracks:
        logger.error(f"❌ {len(missing_tracks)} tracks not found in database")
        return {
            "success": False,
            "error": f"The following tracks do not exist in the database: {missing_tracks}. Please use tracks from search results.",
        }

    # Use AI to finalize playlist
    dj_service = DJLLMService()

    try:
        # Get transition analysis if available
        transitions = []
        if hasattr(finalize_playlist, "_last_transitions"):
            transitions = finalize_playlist._last_transitions

        # Get AI-powered playlist finalization
        ai_result = await dj_service.finalize_playlist(
            track_list=track_data,
            vibe=vibe_description or "Professional DJ set",
            transitions=transitions,
        )

        # Convert AI result to expected format while preserving original filepaths
        playlist = []

        # Create a mapping of track identifiers to original track data
        track_map = {}
        for track in track_data:
            # Use title and artist as a composite key
            key = f"{track.get('title', 'Unknown')}_{track.get('artist', 'Unknown')}"
            track_map[key] = track

        # Process AI results and map back to original tracks
        for i, ai_track in enumerate(ai_result.tracks):
            # Try to find the original track
            original_track = None

            # First try direct position mapping if within bounds
            if i < len(track_data):
                original_track = track_data[i]
                logger.debug(
                    f"   Position mapping: Track {i + 1} -> {original_track.get('filepath')}"
                )

            # If AI provided track info, try to match by title/artist
            if not original_track and isinstance(ai_track, dict):
                ai_key = f"{ai_track.get('title', 'Unknown')}_{ai_track.get('artist', 'Unknown')}"
                if ai_key in track_map:
                    original_track = track_map[ai_key]
                    logger.debug(
                        f"   Title/artist mapping: {ai_key} -> {original_track.get('filepath')}"
                    )

            # Extract filepath from original track
            if original_track:
                filepath = original_track.get("filepath")
            else:
                # Fallback: use filepath from AI if provided (shouldn't happen)
                filepath = (
                    ai_track.get("filepath") if isinstance(ai_track, dict) else None
                )
                logger.warning(f"   ⚠️ Could not map AI track {i + 1} to original data")

            # Build playlist entry with original filepath and AI enhancements
            if filepath:
                playlist_entry = {
                    "filepath": filepath,
                    "order": i + 1,  # Use position-based order
                    "mixing_note": ai_track.get("mixing_note", f"Track {i + 1}")
                    if isinstance(ai_track, dict)
                    else f"Track {i + 1}",
                    "energy": ai_track.get(
                        "energy", original_track.get("energy_level", 0.5)
                    )
                    if isinstance(ai_track, dict)
                    else 0.5,
                }
                playlist.append(playlist_entry)
            else:
                logger.error(f"   ❌ Skipping track {i + 1} - no filepath found")

        # Validate we have tracks with filepaths
        tracks_with_filepaths = [t for t in playlist if t.get("filepath")]
        logger.info(
            f"   📊 Playlist validation: {len(tracks_with_filepaths)}/{len(playlist)} tracks have filepaths"
        )

        # If we have no valid tracks, fall back to original track list
        if not tracks_with_filepaths:
            logger.warning(
                "   ⚠️ No tracks with filepaths after AI processing, using original track order"
            )
            playlist = []
            for i, track in enumerate(track_data):
                if track.get("filepath"):
                    playlist.append(
                        {
                            "filepath": track["filepath"],
                            "order": i + 1,
                            "mixing_note": f"Track {i + 1} - {track.get('title', 'Unknown')}",
                            "energy": track.get("energy_level", 0.5),
                        }
                    )
            tracks_with_filepaths = playlist

        # Add AI insights to result
        result = {
            "success": True,
            "playlist": tracks_with_filepaths,  # Use validated playlist
            "track_count": len(tracks_with_filepaths),
            "duplicates_removed": len(track_filepaths) - len(unique_filepaths),
            "ai_insights": {
                "overall_flow": ai_result.overall_flow,
                "key_moments": ai_result.key_moments,
                "mixing_style": ai_result.mixing_style,
                "set_duration": ai_result.set_duration,
                "energy_graph": ai_result.energy_graph,
            },
        }

        logger.info(f"✅ AI-enhanced playlist finalized: {ai_result.overall_flow}")
        return result

    except Exception as e:
        logger.error(f"❌ AI finalization failed, using basic approach: {e}")
        # Fallback to basic finalization
        playlist = []
        for i, filepath in enumerate(unique_filepaths):
            track_entry = {
                "filepath": filepath,
                "order": i + 1,
                "mixing_note": mixing_notes[i]
                if mixing_notes and i < len(mixing_notes)
                else f"Track {i + 1}",
            }
            playlist.append(track_entry)

        return {
            "success": True,
            "playlist": playlist,
            "track_count": len(playlist),
            "duplicates_removed": len(track_filepaths) - len(unique_filepaths),
        }


class DJAgent:
    """LangGraph agent for DJ playlist and vibe management."""

    def __init__(self, llm_model: str = "gpt-4.1-mini"):
        logger.info(f"🚀 Initializing DJAgent with model: {llm_model}")
        self.db = get_sqlite_db()
        self.llm = ChatOpenAI(model=llm_model, temperature=1)

        # Bind tools to the LLM for agentic approach
        self.tools = [
            search_tracks_by_vibe,
            get_track_details,
            filter_tracks_by_energy,
            finalize_playlist,
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        # Configure ToolNode with error handling
        self.tool_node = ToolNode(self.tools, handle_tool_errors=True)

        # Build both graphs
        self.graph = self._build_graph()  # Original graph
        self.agent_graph = self._build_agent_graph()  # New agentic graph

        logger.info("✅ DJAgent initialized successfully")

    def _build_agent_graph(self) -> StateGraph:
        """Build the agentic LangGraph workflow."""
        workflow = StateGraph(DJAgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self.tool_node)
        workflow.add_node("format_response", self._format_response_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": "format_response"},
        )

        workflow.add_edge("tools", "agent")
        workflow.add_edge("format_response", END)

        return workflow.compile()

    def _agent_node(self, state: DJAgentState) -> Dict:
        """Agent node that decides what to do."""
        messages = state["messages"]

        # Ensure we have a proper message list
        if not isinstance(messages, list):
            messages = []

        logger.info(f"🤖 Agent processing: {len(messages)} messages in conversation")

        # Log the last user message if available
        if messages:
            for msg in reversed(messages):
                if hasattr(msg, "content") and not hasattr(msg, "tool_calls"):
                    logger.debug(f"   Last user input: {msg.content[:100]}...")
                    break

        # Invoke the model with the current messages
        # logger.info("🧠 Agent thinking...")
        response = self.llm_with_tools.invoke(messages)

        # Log if agent is calling tools or providing final answer
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_names = [tc.get("name", "unknown") for tc in response.tool_calls]
            logger.info(f"🔧 Agent calling tools: {', '.join(tool_names)}")
        else:
            logger.info("💬 Agent providing response")
            if hasattr(response, "content"):
                logger.debug(f"   Response preview: {response.content[:100]}...")

        # Return only the new message to be appended to state
        return {"messages": [response]}

    def _should_continue(self, state: DJAgentState) -> str:
        """Decide whether to continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If the last message has tool calls, continue
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        else:
            return "end"

    def _format_response_node(self, state: DJAgentState) -> Dict:
        """Format the final response."""
        messages = state["messages"]
        final_response = messages[-1].content if messages else "No response generated"

        # Extract finalized playlist from tool responses
        finalized_playlist = None

        # Debug: Log all messages to understand what's happening
        logger.debug(f"🔍 Total messages in state: {len(messages)}")

        # Look through messages for tool call results
        for i, msg in enumerate(messages):
            # Check for tool calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_names = []
                for tc in msg.tool_calls:
                    if isinstance(tc, dict):
                        tool_names.append(tc.get("name", "unknown"))
                    else:
                        tool_names.append(getattr(tc, "name", "unknown"))
                logger.debug(f"   Message {i}: Tool calls - {tool_names}")

            # Check for tool responses - handle both string content and structured content
            if hasattr(msg, "content"):
                content = msg.content

                # If content is already a dict (structured tool response)
                if isinstance(content, dict):
                    if content.get("success") and content.get("playlist"):
                        finalized_playlist = content["playlist"]
                        logger.info(
                            f"📋 Extracted finalized playlist with {len(finalized_playlist)} tracks from structured response"
                        )
                        break

                # If content is a string, try to parse it
                elif isinstance(content, str):
                    if '"success"' in content and '"playlist"' in content:
                        logger.debug(
                            f"   Message {i}: Found potential playlist response"
                        )
                        try:
                            import json

                            # Try to parse the tool response
                            tool_result = json.loads(content)
                            if tool_result.get("success") and tool_result.get(
                                "playlist"
                            ):
                                finalized_playlist = tool_result["playlist"]
                                logger.info(
                                    f"📋 Extracted finalized playlist with {len(finalized_playlist)} tracks from JSON response"
                                )
                                break
                        except Exception as e:
                            logger.debug(f"   Failed to parse message {i}: {e}")
                            continue

            # Also check for ToolMessage type specifically
            if hasattr(msg, "__class__") and "ToolMessage" in str(msg.__class__):
                logger.debug(f"   Message {i}: ToolMessage detected")
                if hasattr(msg, "content"):
                    logger.debug(f"   ToolMessage content type: {type(msg.content)}")
                    logger.debug(
                        f"   ToolMessage content preview: {str(msg.content)[:200]}"
                    )

        if not finalized_playlist:
            logger.warning("⚠️ No finalized playlist found in messages")
            # Log the last few messages for debugging
            for i, msg in enumerate(messages[-3:]):
                logger.debug(f"   Recent message {i}: {str(msg)[:200]}")

        return {
            "final_response": final_response,
            "finalized_playlist": finalized_playlist,
        }

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(DJAgentState)

        # Add nodes
        workflow.add_node("analyze_track", self.analyze_track_node)
        workflow.add_node("build_context", self.build_context_node)
        workflow.add_node("match_vibes", self.match_vibes_node)
        workflow.add_node("build_playlist", self.build_playlist_node)
        workflow.add_node("plan_transitions", self.plan_transitions_node)

        # Add edges
        workflow.set_entry_point("analyze_track")
        workflow.add_edge("analyze_track", "build_context")
        workflow.add_edge("build_context", "match_vibes")
        workflow.add_edge("match_vibes", "build_playlist")
        workflow.add_edge("build_playlist", "plan_transitions")
        workflow.add_edge("plan_transitions", END)

        return workflow.compile()

    def analyze_track_node(self, state: DJAgentState) -> Dict:
        """Analyze the current track's characteristics."""
        current_track = state["current_track"]

        logger.info("🔍 Starting track analysis...")

        if not current_track:
            logger.warning("❌ No current track provided")
            return {"messages": [AIMessage(content="No current track provided")]}

        logger.info(
            f"📀 Analyzing track: {current_track.get('title', 'Unknown')} by {current_track.get('artist', 'Unknown')}"
        )
        logger.debug(f"   - BPM: {current_track.get('bpm', 'N/A')}")
        logger.debug(f"   - Genre: {current_track.get('genre', 'Unknown')}")
        logger.debug(f"   - Duration: {current_track.get('duration', 0):.1f}s")

        # Get energy level from database or estimate if missing
        from utils.dj_llm import DJLLMService

        dj_service = DJLLMService()

        energy_level = current_track.get("energy_level")
        if energy_level is None:
            energy_level = dj_service.estimate_energy_from_features(
                current_track.get("bpm"), current_track.get("genre")
            )
            logger.info(f"⚡ Energy level (estimated): {energy_level:.2f}")
        else:
            logger.info(f"⚡ Energy level: {energy_level:.2f}")

        vibe_analysis = {
            "track_id": current_track["filepath"],
            "bpm": current_track.get("bpm", 0),
            "energy_level": energy_level,
            "dominant_vibe": "neutral",  # Simplified - let AI determine vibe
            "mood_vector": current_track.get("mood", {}),
            "genre": current_track.get("genre", "unknown"),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"✅ Track analysis complete: {energy_level:.2f} energy")

        return {
            "vibe_analysis": vibe_analysis,
            "messages": [
                AIMessage(
                    content=f"Analyzed track: {current_track.get('title', 'Unknown')} - {energy_level:.2f} energy"
                )
            ],
        }

    def build_context_node(self, state: DJAgentState) -> Dict:
        """Build the mixing context based on time, history, and preferences."""
        context = state.get("context", {})
        track_history = state.get("track_history", [])
        vibe_analysis = state["vibe_analysis"]

        logger.info("🏗️ Building mixing context...")
        logger.debug(f"   - Current context: {json.dumps(context, indent=2)}")
        logger.debug(f"   - Track history length: {len(track_history)}")

        # Analyze recent track history for trends
        if track_history:
            recent_bpms = [t.get("bpm", 0) for t in track_history[-5:]]
            avg_recent_bpm = (
                np.mean(recent_bpms) if recent_bpms else vibe_analysis["bpm"]
            )
            bpm_trend = (
                "increasing" if recent_bpms[-1] > recent_bpms[0] else "decreasing"
            )
            logger.info(f"📊 BPM trend: {bpm_trend} (avg: {avg_recent_bpm:.1f})")
        else:
            avg_recent_bpm = vibe_analysis["bpm"]
            bpm_trend = "stable"
            logger.info("📊 No track history - starting fresh")

        # Enhance context - let AI decide energy direction in the agentic workflow
        enhanced_context = {
            **context,
            "current_energy": vibe_analysis["energy_level"],
            "avg_recent_bpm": avg_recent_bpm,
            "bpm_trend": bpm_trend,
            "energy_pattern": state.get("energy_pattern", "wave"),
        }

        logger.info(f"🎯 Energy pattern: {enhanced_context['energy_pattern']}")
        logger.debug(f"   - Current energy: {enhanced_context['current_energy']:.2f}")
        logger.debug(f"   - Pattern: {state.get('energy_pattern', 'wave')}")

        return {
            "context": enhanced_context,
            "messages": [AIMessage(content=f"Context built: {bpm_trend} BPM trend")],
        }

    def match_vibes_node(self, state: DJAgentState) -> Dict:
        """Find tracks with similar vibes - simplified for AI workflow."""
        vibe_analysis = state["vibe_analysis"]

        logger.info("🎯 Finding similar tracks...")
        logger.debug(f"   - Reference BPM: {vibe_analysis['bpm']}")
        logger.debug(f"   - Reference energy: {vibe_analysis['energy_level']:.2f}")
        logger.debug(f"   - Reference genre: {vibe_analysis['genre']}")

        # For the original workflow, just get some tracks from DB
        # The agentic workflow will use search_tracks_by_vibe instead
        cursor = self.db.adapter.connection.cursor()

        # Simple query - get tracks with similar BPM range
        bpm = vibe_analysis["bpm"] or 120
        cursor.execute(
            """
            SELECT * FROM tracks 
            WHERE filepath != ? 
            AND bpm BETWEEN ? AND ?
            LIMIT 50
        """,
            (vibe_analysis["track_id"], bpm - 10, bpm + 10),
        )

        columns = [description[0] for description in cursor.description]
        candidates = []

        for row in cursor.fetchall():
            track = dict(zip(columns, row))

            # Parse beat_times if needed
            if track.get("beat_times") and isinstance(track["beat_times"], str):
                try:
                    track["beat_times"] = json.loads(track["beat_times"])
                except (json.JSONDecodeError, TypeError):
                    track["beat_times"] = []

            # Simple scoring based on BPM proximity
            bpm_diff = abs((track.get("bpm") or 120) - bpm)
            score = max(0, 1 - (bpm_diff / 50))  # Simple linear score

            candidates.append({**track, "similarity_score": score})

        cursor.close()

        # Sort by score
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_candidates = candidates[:20]

        logger.info(f"📊 Found {len(top_candidates)} candidate tracks")

        return {
            "candidate_tracks": top_candidates,
            "messages": [
                AIMessage(
                    content=f"Found {len(top_candidates)} tracks with similar BPM"
                )
            ],
        }

    def build_playlist_node(self, state: DJAgentState) -> Dict:
        """Build an ordered playlist - simplified for non-agentic workflow."""
        candidates = state["candidate_tracks"]
        context = state["context"]
        playlist_length = context.get("playlist_length", 10)

        logger.info("📝 Building playlist...")
        logger.info(f"   - Target length: {playlist_length}")
        logger.info(f"   - Available candidates: {len(candidates)}")

        # Simple approach - just take top scored tracks
        playlist = candidates[:playlist_length]

        logger.info(f"✅ Built {len(playlist)}-track playlist")

        # Log track list
        for i, track in enumerate(playlist):
            logger.debug(
                f"   {i + 1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} ({track.get('bpm', 0):.0f} BPM)"
            )

        return {
            "playlist": playlist,
            "messages": [AIMessage(content=f"Built {len(playlist)}-track playlist")],
        }

    async def plan_transitions_node(self, state: DJAgentState) -> Dict:
        """Plan transitions between tracks in the playlist using AI-powered analysis."""
        playlist = state["playlist"]
        current_track = state["current_track"]

        logger.info("🔄 Planning AI-powered transitions...")

        transitions = []

        # Plan transition from current track to first playlist track
        if playlist and current_track:
            first_transition = await self._plan_transition_agentic(
                current_track, playlist[0]
            )
            transitions.append(first_transition)
            logger.debug(
                f"   → From current to first: BPM {current_track.get('bpm', 0):.0f} → {playlist[0].get('bpm', 0):.0f}"
            )

        # Plan transitions between playlist tracks
        for i in range(len(playlist) - 1):
            transition = await self._plan_transition_agentic(
                playlist[i], playlist[i + 1]
            )
            transitions.append(transition)

            if i < 3:  # Log first few transitions
                from_bpm = playlist[i].get("bpm", 0)
                to_bpm = playlist[i + 1].get("bpm", 0)
                effect_type = transition.get("effect_plan", {}).get(
                    "profile", "unknown"
                )
                logger.debug(
                    f"   → Track {i + 1} to {i + 2}: BPM {from_bpm:.0f} → {to_bpm:.0f} ({effect_type})"
                )

        logger.info(f"✅ AI planned {len(transitions)} transitions")

        # Log AI-designed effects summary
        effect_profiles = {}
        for t in transitions:
            profile = t.get("effect_plan", {}).get("profile", "unknown")
            effect_profiles[profile] = effect_profiles.get(profile, 0) + 1

        if effect_profiles:
            logger.debug(f"   AI transition profiles: {dict(effect_profiles)}")

        return {
            "transitions": transitions,
            "messages": [
                AIMessage(content=f"AI planned {len(transitions)} transitions")
            ],
        }

    # Helper methods

    async def _plan_transition_agentic(self, from_track: Dict, to_track: Dict) -> Dict:
        """Plan transition using AI-powered analysis."""
        from utils.dj_llm import DJLLMService

        logger.debug(
            f"🔄 AI Planning transition: {from_track.get('title', 'Unknown')} -> {to_track.get('title', 'Unknown')}"
        )

        dj_service = DJLLMService()

        try:
            # Use AI to plan the transition
            transition_plan = await dj_service.plan_transition(from_track, to_track)

            return {
                "from_track": from_track.get("filepath"),
                "to_track": to_track.get("filepath"),
                "score": transition_plan.compatibility_score,
                "effect_plan": {
                    "profile": transition_plan.transition_type,
                    "effects": [
                        {
                            "type": effect.type,
                            "start_at": effect.start_at,
                            "duration": effect.duration,
                            "intensity": effect.intensity,
                        }
                        if hasattr(effect, "type")
                        else effect
                        for effect in transition_plan.effects
                    ],
                    "reasoning": transition_plan.technique_notes,
                    "crossfade_curve": "s-curve",  # Default curve
                },
                "from_analysis": {
                    "bpm": from_track.get("bpm"),
                    "energy": from_track.get("energy_level"),
                },
                "to_analysis": {
                    "bpm": to_track.get("bpm"),
                    "energy": to_track.get("energy_level"),
                },
            }
        except Exception as e:
            logger.error(f"AI transition planning failed: {e}")
            # Simple fallback
            return {
                "from_track": from_track.get("filepath"),
                "to_track": to_track.get("filepath"),
                "score": 0.5,
                "effect_plan": {
                    "profile": "smooth_blend",
                    "effects": [
                        {
                            "type": "filter",
                            "start_at": 0,
                            "duration": 3,
                            "intensity": 0.5,
                        }
                    ],
                    "reasoning": "Fallback transition",
                    "crossfade_curve": "linear",
                },
                "from_analysis": {
                    "bpm": from_track.get("bpm", 120),
                    "energy": from_track.get("energy_level", 0.5),
                },
                "to_analysis": {
                    "bpm": to_track.get("bpm", 120),
                    "energy": to_track.get("energy_level", 0.5),
                },
            }

    async def suggest_next_track(
        self,
        current_track: Optional[str] = None,
        current_track_id: Optional[str] = None,
        context: Optional[Union[str, Dict]] = None,
        thread_id: Optional[str] = None,
    ) -> Dict:
        """Suggest next track with support for both string context and dict context.

        Args:
            current_track: Track filepath (new parameter name)
            current_track_id: Track filepath (old parameter name for compatibility)
            context: Either a string description or dict with structured context
            thread_id: Optional thread ID for conversation context
        """
        # Handle parameter compatibility
        track_id = current_track or current_track_id
        if not track_id:
            return {
                "success": False,
                "error": "Either current_track or current_track_id must be provided",
            }

        # If context is a string, use agentic approach
        if isinstance(context, str):
            return await self._suggest_next_track_agentic(
                current_track=track_id, context_description=context, thread_id=thread_id
            )
        else:
            # Use original approach with dict context
            result = await self._suggest_next_track_original(
                current_track_id=track_id, context=context
            )
            # Wrap in expected format
            if "error" in result:
                return {"success": False, "error": result["error"]}
            else:
                track = result["track"]
                response = (
                    f"Suggested next track: {track.get('title', 'Unknown')} "
                    f"by {track.get('artist', 'Unknown')} "
                    f"({track.get('bpm', 0):.0f} BPM)\n\n"
                    f"Confidence: {result['confidence']:.0%}\n"
                    f"Transition: {result['transition']['mix_duration']} bars"
                )
                return {
                    "success": True,
                    "response": response,
                    "track": track,
                    "confidence": result["confidence"],
                    "transition": result["transition"],
                }

    async def _suggest_next_track_agentic(
        self,
        current_track: str,
        context_description: str,
        thread_id: Optional[str] = None,
    ) -> Dict:
        """Suggest next track using agentic approach with natural language context."""
        logger.info("=" * 50)
        logger.info("🎵 AGENTIC NEXT TRACK SUGGESTION")
        logger.info(f"   Current: {current_track}")
        logger.info(f"   Context: {context_description}")

        prompt = f"""You are a professional DJ assistant.
The current track playing is: {current_track}

Context: {context_description}

Use the available tools to:
1. Get details about the current track
2. Search for tracks that would mix well
3. Consider the context when making your suggestion

Suggest ONE track that would be perfect to play next, with mixing notes.

What track should I play after {current_track}?"""

        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "current_track": None,
            "context": {},
            "track_history": [],
            "candidate_tracks": [],
            "playlist": [],
            "transitions": [],
            "vibe_analysis": None,
            "energy_pattern": "wave",
            "vibe_description": context_description,
        }

        try:
            result = await self.agent_graph.ainvoke(initial_state)
            response_text = result.get("final_response", "")

            return {"success": True, "response": response_text, "thread_id": thread_id}

        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            return {"success": False, "error": str(e), "thread_id": thread_id}

    async def _suggest_next_track_original(
        self, current_track_id: str, context: Optional[Dict] = None
    ) -> Dict:
        """Original method implementation for backward compatibility."""
        logger.info("=" * 50)
        logger.info("🎵 NEXT TRACK SUGGESTION REQUEST")
        logger.info(f"   Current track: {current_track_id}")
        if context:
            logger.info(f"   Context: {json.dumps(context, indent=2)}")

        # Load current track from DB
        cursor = self.db.adapter.connection.cursor()
        cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (current_track_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return {"error": "Track not found"}

        current_track = dict(zip(columns, row))

        # Parse beat_times if needed
        if current_track.get("beat_times") and isinstance(
            current_track["beat_times"], str
        ):
            try:
                current_track["beat_times"] = json.loads(current_track["beat_times"])
            except (json.JSONDecodeError, TypeError):
                current_track["beat_times"] = []

        # Prepare state
        initial_state = {
            "current_track": current_track,
            "context": context or {},
            "track_history": [],
            "candidate_tracks": [],
            "playlist": [],
            "transitions": [],
            "messages": [],
            "vibe_analysis": None,
            "energy_pattern": context.get("energy_pattern", "wave")
            if context
            else "wave",
            "vibe_description": None,
        }

        # Run the graph
        logger.info("🚀 Running LangGraph workflow...")
        result = await self.graph.ainvoke(initial_state)

        # Return the first track from playlist as suggestion
        if result["playlist"]:
            suggestion = result["playlist"][0]
            logger.info(
                f"✅ Suggestion: {suggestion.get('title', 'Unknown')} by {suggestion.get('artist', 'Unknown')}"
            )
            logger.info(f"   - Confidence: {suggestion.get('similarity_score', 0):.2%}")
            logger.info("=" * 50)

            return {
                "track": suggestion,
                "confidence": suggestion.get("similarity_score", 0),
                "transition": result["transitions"][0]
                if result["transitions"]
                else None,
                "vibe_analysis": result["vibe_analysis"],
            }
        else:
            logger.error("❌ No suitable tracks found")
            logger.info("=" * 50)
            return {"error": "No suitable tracks found"}

    async def generate_playlist(
        self,
        vibe_description: Optional[str] = None,
        seed_track_id: Optional[str] = None,
        length: Optional[int] = None,
        duration_minutes: Optional[int] = None,
        energy_pattern: str = "wave",
        context: Optional[Dict] = None,
        thread_id: Optional[str] = None,
    ) -> Dict:
        """Generate a playlist using either a vibe description or seed track.

        This method supports both approaches:
        1. Vibe description: Uses the agentic approach with tools
        2. Seed track: Uses the original workflow-based approach
        
        Args:
            vibe_description: Natural language description of desired vibe
            seed_track_id: ID of track to use as seed (alternative to vibe)
            length: Number of tracks (optional, can be calculated from duration)
            duration_minutes: Target duration in minutes (AI will determine optimal track count)
            energy_pattern: Energy flow pattern (wave, build, steady, etc.)
            context: Additional context for generation
            thread_id: Thread ID for conversation continuity
        """
        if vibe_description:
            # Use the new agentic approach
            return await self._generate_playlist_from_vibe(
                vibe_description=vibe_description,
                length=length,
                duration_minutes=duration_minutes,
                energy_pattern=energy_pattern,
                thread_id=thread_id,
            )
        elif seed_track_id:
            # Use the original seed-based approach
            return await self._generate_playlist_from_seed(
                seed_track_id=seed_track_id,
                length=length,
                energy_pattern=energy_pattern,
                context=context,
            )
        else:
            return {
                "success": False,
                "error": "Either vibe_description or seed_track_id must be provided",
            }

    async def _generate_playlist_from_vibe(
        self,
        vibe_description: str,
        length: Optional[int] = None,
        duration_minutes: Optional[int] = None,
        energy_pattern: str = "wave",
        thread_id: Optional[str] = None,
    ) -> Dict:
        """Generate playlist from vibe description using agentic approach."""
        logger.info("=" * 50)
        logger.info("🎨 VIBE-BASED PLAYLIST GENERATION")
        logger.info(f"   Vibe: '{vibe_description}'")
        
        # AI will intelligently determine track count based on duration and context
        if duration_minutes:
            logger.info(f"   Duration: {duration_minutes} minutes")
            # Let AI determine optimal track count considering mixing style and energy pattern
            if not length:
                # Provide guidance but let AI make the final decision
                logger.info("   Length: AI will determine optimal track count")
        else:
            length = length or 20  # Default if neither specified
            logger.info(f"   Length: {length} tracks")
            
        logger.info(f"   Pattern: {energy_pattern}")
        logger.info(f"   Thread: {thread_id}")

        # Create the initial message
        if duration_minutes:
            system_content = f"""You are a professional DJ assistant. 
            Create a playlist for a {duration_minutes}-minute DJ set based on the following vibe: "{vibe_description}"
            
            IMPORTANT: You must determine the optimal number of tracks considering:
            - Average track length in the genre (EDM ~5-7min, pop ~3-4min, etc.)
            - Mixing style and transition lengths (longer transitions = fewer tracks)
            - Energy pattern "{energy_pattern}" (steady patterns allow longer tracks)
            - The vibe and context provided
            
            Aim for a natural flow that fits the duration without rushing or dragging."""
        else:
            system_content = f"""You are a professional DJ assistant. 
            Create a {length}-track playlist based on the following vibe description: "{vibe_description}"
            
            The playlist should follow a "{energy_pattern}" energy pattern.
            Energy patterns:
            - build_up: Start low energy and gradually increase
            - cool_down: Start high energy and gradually decrease  
            - peak_time: Maintain high energy throughout
            - wave: Alternate between high and low energy

            Use the available tools to:
            1. Search for tracks matching the vibe using search_tracks_by_vibe
            2. Get detailed track information using get_track_details if needed
            3. If you need to filter tracks by energy: filter_tracks_by_energy(tracks=<list of tracks>, target_energy=<0-1>, tolerance=<optional>)

            IMPORTANT RULES: 
            - You MUST ONLY use tracks that are returned by the search_tracks_by_vibe tool
            - NEVER create fake track names like "track_001.mp3" or similar
            - ONLY use these exact genres (no variations): African Music, Alternative, Bolero, Brazilian Music, Dance, Electro, Films/Games, Hip-Hop/Rap, Jazz, Latin Music, Pop, R&B, Rap/Hip Hop, Reggae, Reggaeton, Rock, Salsa, Soul & Funk
            - Select UNIQUE tracks only - do not include the same track multiple times
            - After selecting your tracks, you MUST call the finalize_playlist tool with:
              * A list of track filepaths (exactly {length} UNIQUE tracks from search results)
              * Mixing notes for each track explaining why it fits and how to mix it

            The finalize_playlist tool is required to complete the playlist creation.
            Your task is NOT complete until you have called finalize_playlist with REAL tracks.
            
            Example of correct final step:
            finalize_playlist(
                track_filepaths=["/path/track1.mp3", "/path/track2.mp3", ...],
                mixing_notes=["High energy opener", "Smooth transition from track 1", ...]
            )"""

        user_message = f"Create a {length}-track playlist with {vibe_description}"

        # Combine system and user content into a single message
        combined_message = f"{system_content}\n\nUser request: {user_message}"

        initial_state = {
            "messages": [HumanMessage(content=combined_message)],
            "vibe_description": vibe_description,
            "energy_pattern": energy_pattern,
            "context": {"playlist_length": length},
            "current_track": None,
            "track_history": [],
            "candidate_tracks": [],
            "playlist": [],
            "transitions": [],
            "vibe_analysis": None,
            "finalized_playlist": None,  # Initialize the new field
        }

        try:
            logger.info("🚀 Running agentic workflow...")
            result = await self.agent_graph.ainvoke(initial_state)

            response_text = result.get("final_response", "")
            logger.info("✅ Agent response generated")

            # Get the finalized playlist directly from the result
            finalized_playlist = result.get("finalized_playlist")

            # Initialize variables that will be used in the return statement
            transition_plan = None
            hot_cue_analysis = None

            if finalized_playlist:
                logger.info(
                    f"📋 Found finalized playlist with {len(finalized_playlist)} tracks"
                )

                # Step 2: Hot Cue Transition Planning
                logger.info("=" * 50)
                logger.info("🎛️ STEP 2: HOT CUE TRANSITION PLANNING")

                try:
                    # Extract track filepaths for hot cue analysis
                    track_filepaths = [
                        track.get("filepath")
                        for track in finalized_playlist
                        if track.get("filepath")
                    ]

                    if len(track_filepaths) >= 2:
                        logger.info(
                            f"Analyzing transitions for {len(track_filepaths)} tracks..."
                        )

                        # Analyze hot cue transitions directly
                        transition_analysis = await analyze_hot_cue_transitions(track_filepaths)

                        # Create transition planning result
                        transition_plan = transition_analysis
                        hot_cue_analysis = {
                            "tracks_analyzed": len(track_filepaths),
                            "optimal_transitions": transition_analysis.get(
                                "optimal_transitions", 0
                            ),
                            "total_transitions": len(
                                transition_analysis.get("transitions", [])
                            ),
                            "recommendations": transition_analysis.get(
                                "recommendations", []
                            ),
                        }

                        # Log transition analysis summary
                        optimal_count = transition_analysis.get(
                            "optimal_transitions", 0
                        )
                        total_count = len(transition_analysis.get("transitions", []))

                        logger.info("✅ Transition analysis complete:")
                        logger.info(
                            f"   Optimal transitions: {optimal_count}/{total_count}"
                        )
                        logger.info(
                            f"   Hot cue coverage: {transition_analysis.get('tracks_with_hot_cues', 0)}/{len(track_filepaths)} tracks"
                        )

                        for recommendation in transition_analysis.get(
                            "recommendations", []
                        ):
                            logger.info(f"   💡 {recommendation}")

                    else:
                        logger.warning("Not enough tracks for transition analysis")
                        transition_plan = {"error": "Insufficient tracks for analysis"}

                except Exception as e:
                    logger.error(f"❌ Error in transition planning: {e}")
                    transition_plan = {"error": str(e)}

            else:
                logger.warning("⚠️ No finalized playlist found in result")

            logger.info("=" * 50)

            # Enrich finalized_playlist with full track data for transition planning
            enriched_playlist = []
            if finalized_playlist:
                logger.info("📚 Enriching playlist with full track metadata...")
                cursor = self.db.adapter.connection.cursor()

                for track in finalized_playlist:
                    filepath = (
                        track.get("filepath") if isinstance(track, dict) else None
                    )
                    if filepath:
                        cursor.execute(
                            """
                            SELECT filepath, title, artist, bpm, key, energy_level, duration, genre
                            FROM tracks WHERE filepath = ?
                            """,
                            (filepath,),
                        )
                        result = cursor.fetchone()

                        if result:
                            columns = [
                                description[0] for description in cursor.description
                            ]
                            full_track = dict(zip(columns, result))
                            # Preserve mixing notes if they exist
                            if isinstance(track, dict) and "mixing_note" in track:
                                full_track["mixing_note"] = track["mixing_note"]
                            enriched_playlist.append(full_track)
                        else:
                            # Fallback with basic info
                            logger.warning(f"⚠️ Track not found in DB: {filepath}")
                            enriched_playlist.append(
                                {
                                    "filepath": filepath,
                                    "title": os.path.basename(filepath),
                                    "artist": "Unknown",
                                    "bpm": 120,
                                    "energy_level": 0.5,
                                    "mixing_note": track.get("mixing_note", "")
                                    if isinstance(track, dict)
                                    else "",
                                }
                            )

                cursor.close()
                logger.info(
                    f"✅ Enriched {len(enriched_playlist)} tracks with metadata"
                )

                # Use enriched playlist for display
                finalized_playlist = enriched_playlist

            # Generate transitions with effect plans using agentic workflow
            transitions_with_effects = []
            if enriched_playlist and len(enriched_playlist) > 1:
                logger.info(
                    f"🎯 Planning transitions for {len(enriched_playlist)} tracks using agentic workflow..."
                )
                try:
                    for i in range(len(enriched_playlist) - 1):
                        # Use the new agentic transition planning
                        transition = await self._plan_transition_agentic(
                            enriched_playlist[i], enriched_playlist[i + 1]
                        )
                        transitions_with_effects.append(transition)
                        if i == 0:  # Log the first transition for debugging
                            logger.info(f"   First transition: {transition}")
                    logger.info(
                        f"📊 Generated {len(transitions_with_effects)} transitions with agentic planning"
                    )
                except Exception as e:
                    logger.error(f"❌ Error in transition planning: {e}")
                    # Continue without transitions rather than failing entirely
                    transitions_with_effects = []

            return {
                "success": True,
                "response": response_text,
                "thread_id": thread_id,
                "finalized_playlist": finalized_playlist,
                "transition_plan": transition_plan,
                "hot_cue_analysis": hot_cue_analysis,
                "transitions": transitions_with_effects,  # Add transitions with effect plans
                "state": result,  # Include full state for debugging
            }

        except Exception as e:
            logger.error(f"❌ Error in agentic generation: {str(e)}")
            logger.info("=" * 50)

            # Try to return partial results if we have a playlist
            if "finalized_playlist" in locals() and finalized_playlist:
                logger.info(
                    f"⚠️ Returning partial results with {len(finalized_playlist)} tracks"
                )
                return {
                    "success": True,  # Partial success
                    "error": str(e),
                    "partial": True,
                    "response": response_text
                    if "response_text" in locals()
                    else "Error during generation",
                    "thread_id": thread_id,
                    "finalized_playlist": finalized_playlist,
                    "transition_plan": transition_plan
                    if "transition_plan" in locals()
                    else None,
                    "hot_cue_analysis": hot_cue_analysis
                    if "hot_cue_analysis" in locals()
                    else None,
                    "transitions": transitions_with_effects
                    if "transitions_with_effects" in locals()
                    else [],
                }

            return {"success": False, "error": str(e), "thread_id": thread_id}

    async def _generate_playlist_from_seed(
        self,
        seed_track_id: str,
        length: int = 10,
        energy_pattern: str = "wave",
        context: Optional[Dict] = None,
    ) -> Dict:
        """Original seed-based playlist generation (backward compatible)."""
        logger.info("=" * 50)
        logger.info("🎵 SEED-BASED PLAYLIST GENERATION")
        logger.info(f"   Seed track: {seed_track_id}")
        logger.info(f"   Length: {length} tracks")
        logger.info(f"   Pattern: {energy_pattern}")

        # Load seed track from SQLite
        cursor = self.db.adapter.connection.cursor()
        cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (seed_track_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return {"success": False, "error": "Seed track not found"}

        seed_track = dict(zip(columns, row))

        # Parse beat_times if needed
        if seed_track.get("beat_times") and isinstance(seed_track["beat_times"], str):
            try:
                seed_track["beat_times"] = json.loads(seed_track["beat_times"])
            except (json.JSONDecodeError, TypeError):
                seed_track["beat_times"] = []

        # Prepare context
        full_context = {**(context or {}), "playlist_length": length}

        # Prepare state
        initial_state = {
            "current_track": seed_track,
            "context": full_context,
            "track_history": [],
            "candidate_tracks": [],
            "playlist": [],
            "transitions": [],
            "messages": [],
            "vibe_analysis": None,
            "energy_pattern": energy_pattern,
            "vibe_description": None,
        }

        # Run the original graph
        logger.info("🚀 Running workflow...")
        result = await self.graph.ainvoke(initial_state)

        logger.info(f"✅ Generated {len(result['playlist'])} track playlist")
        logger.info("=" * 50)

        # Format response to match expected structure
        playlist_text = "\n".join(
            [
                f"{i + 1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} "
                f"({track.get('bpm', 0):.0f} BPM)"
                for i, track in enumerate(result["playlist"])
            ]
        )

        return {
            "success": True,
            "response": f"Generated {len(result['playlist'])}-track playlist:\n\n{playlist_text}",
            "playlist": result["playlist"],
            "transitions": result["transitions"],
            "vibe_analysis": result["vibe_analysis"],
            "energy_flow": [t.get("energy_level", 0.5) for t in result["playlist"]],
        }

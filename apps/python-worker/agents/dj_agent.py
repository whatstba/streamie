"""
LangGraph DJ Agent for intelligent playlist and vibe management.
"""

from typing import TypedDict, List, Dict, Optional, Annotated, Sequence, Union
from datetime import datetime
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import numpy as np
import logging
import json
import sqlite3
import os

from utils.sqlite_db import get_sqlite_db

# Configure logging for the DJ agent
logger = logging.getLogger("DJAgent")
logger.setLevel(logging.DEBUG)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '🎧 [%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
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

# Define tools for the agentic approach
@tool
def search_tracks_by_vibe(vibe_keywords: str, limit: int = 20) -> List[Dict]:
    """Search for tracks that match the given vibe keywords.
    
    Args:
        vibe_keywords: Keywords describing the desired vibe (e.g., "chill relaxing smooth")
        limit: Maximum number of tracks to return
        
    Returns:
        List of tracks matching the vibe
    """
    logger.info(f"🔍 Searching tracks with vibe: '{vibe_keywords}' (limit: {limit})")
    
    db = get_sqlite_db()
    cursor = db.adapter.connection.cursor()
    
    # Parse vibe keywords for energy level and genre hints
    keywords_lower = vibe_keywords.lower()
    
    # Energy level estimation from keywords
    high_energy_words = ['energetic', 'upbeat', 'pump', 'hype', 'intense', 'party', 'dance', 'workout', 'gym', 'fast']
    low_energy_words = ['chill', 'relaxing', 'calm', 'mellow', 'soft', 'quiet', 'ambient', 'downtempo', 'slow']
    
    high_count = sum(1 for word in high_energy_words if word in keywords_lower)
    low_count = sum(1 for word in low_energy_words if word in keywords_lower)
    
    # Build query based on energy preference
    if high_count > low_count:
        logger.info(f"   🔥 Detected high energy vibe (score: {high_count})")
        cursor.execute("""
            SELECT * FROM tracks 
            WHERE bpm > 120 OR energy_level > 0.6
            ORDER BY energy_level DESC, bpm DESC
            LIMIT ?
        """, (limit,))
    elif low_count > high_count:
        logger.info(f"   😌 Detected low energy vibe (score: {low_count})")
        cursor.execute("""
            SELECT * FROM tracks 
            WHERE bpm < 110 OR energy_level < 0.4
            ORDER BY energy_level ASC, bpm ASC
            LIMIT ?
        """, (limit,))
    else:
        logger.info(f"   🎵 No clear energy preference, selecting randomly")
        cursor.execute("""
            SELECT * FROM tracks 
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
    
    columns = [description[0] for description in cursor.description]
    tracks = []
    
    for row in cursor.fetchall():
        track = dict(zip(columns, row))
        # Parse beat_times if it's a JSON string
        if track.get("beat_times") and isinstance(track["beat_times"], str):
            try:
                track["beat_times"] = json.loads(track["beat_times"])
            except:
                track["beat_times"] = []
        tracks.append(track)
    
    cursor.close()
    
    logger.info(f"   📊 Found {len(tracks)} matching tracks")
    if tracks:
        # Log a few examples
        for i, track in enumerate(tracks[:3]):
            logger.debug(f"      {i+1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} ({track.get('bpm', 0):.0f} BPM)")
    
    return tracks

@tool
def get_track_details(track_filepath: str) -> Dict:
    """Get detailed information about a specific track.
    
    Args:
        track_filepath: The filepath of the track
        
    Returns:
        Detailed track information including BPM, energy, genre, etc.
    """
    db = get_sqlite_db()
    cursor = db.adapter.connection.cursor()
    
    cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (track_filepath,))
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    cursor.close()
    
    if not row:
        return {"error": "Track not found"}
    
    track = dict(zip(columns, row))
    
    # Parse beat_times if needed
    if track.get("beat_times") and isinstance(track["beat_times"], str):
        try:
            track["beat_times"] = json.loads(track["beat_times"])
        except:
            track["beat_times"] = []
    
    return track

@tool
def filter_tracks_by_energy(tracks: List[Dict], target_energy: float, tolerance: float = 0.2) -> List[Dict]:
    """Filter tracks by energy level.
    
    Args:
        tracks: List of tracks to filter
        target_energy: Target energy level (0-1)
        tolerance: Acceptable deviation from target
        
    Returns:
        Filtered list of tracks
    """
    filtered = []
    for track in tracks:
        energy = track.get("energy_level", 0.5)
        if abs(energy - target_energy) <= tolerance:
            filtered.append(track)
    return filtered

@tool
def sort_tracks_by_bpm_progression(tracks: List[Dict], start_bpm: float, direction: str = "increase") -> List[Dict]:
    """Sort tracks to create a smooth BPM progression.
    
    Args:
        tracks: List of tracks to sort
        start_bpm: Starting BPM
        direction: "increase", "decrease", or "maintain"
        
    Returns:
        Sorted list of tracks
    """
    if direction == "increase":
        return sorted(tracks, key=lambda x: abs(x.get("bpm", 120) - start_bpm))
    elif direction == "decrease":
        return sorted(tracks, key=lambda x: -abs(x.get("bpm", 120) - start_bpm))
    else:
        # Maintain - sort by closest BPM
        return sorted(tracks, key=lambda x: abs(x.get("bpm", 120) - start_bpm))

@tool
def finalize_playlist(track_filepaths: List[str], mixing_notes: Optional[List[str]] = None) -> Dict:
    """Finalize the playlist with selected tracks and mixing notes.
    
    Args:
        track_filepaths: List of track filepaths for the final playlist
        mixing_notes: Optional list of mixing notes for each track
        
    Returns:
        Dictionary with success status and playlist details
    """
    logger.info(f"🎯 Finalizing playlist with {len(track_filepaths)} tracks")
    
    if not track_filepaths:
        return {"success": False, "error": "No tracks provided"}
    
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
            logger.warning(f"⚠️ Duplicate track found at position {i+1}: {filepath}")
    
    # Adjust mixing notes if we removed duplicates
    if mixing_notes and duplicate_indices:
        unique_mixing_notes = []
        for i, note in enumerate(mixing_notes):
            if i not in duplicate_indices:
                unique_mixing_notes.append(note)
        mixing_notes = unique_mixing_notes
    
    # Ensure mixing_notes matches track count
    if mixing_notes and len(mixing_notes) != len(unique_filepaths):
        mixing_notes = None
        logger.warning("Mixing notes count doesn't match tracks after removing duplicates, ignoring notes")
    
    playlist = []
    for i, filepath in enumerate(unique_filepaths):
        track_entry = {
            "filepath": filepath,
            "order": i + 1,
            "mixing_note": mixing_notes[i] if mixing_notes else f"Track {i + 1}"
        }
        playlist.append(track_entry)
        logger.debug(f"   {i+1}. {filepath}")
    
    if len(unique_filepaths) < len(track_filepaths):
        logger.info(f"✅ Playlist finalized with {len(playlist)} unique tracks (removed {len(track_filepaths) - len(unique_filepaths)} duplicates)")
    else:
        logger.info(f"✅ Playlist finalized successfully")
    
    return {
        "success": True,
        "playlist": playlist,
        "track_count": len(playlist),
        "duplicates_removed": len(track_filepaths) - len(unique_filepaths)
    }

class DJAgent:
    """LangGraph agent for DJ playlist and vibe management."""
    
    def __init__(self, llm_model: str = "o4-mini"):
        logger.info(f"🚀 Initializing DJAgent with model: {llm_model}")
        self.db = get_sqlite_db()
        self.llm = ChatOpenAI(model=llm_model, temperature=1)
        
        # Bind tools to the LLM for agentic approach
        self.tools = [search_tracks_by_vibe, get_track_details, filter_tracks_by_energy, sort_tracks_by_bpm_progression, finalize_playlist]
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
            {
                "continue": "tools",
                "end": "format_response"
            }
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
                if hasattr(msg, 'content') and not hasattr(msg, 'tool_calls'):
                    logger.debug(f"   Last user input: {msg.content[:100]}...")
                    break
        
        # Invoke the model with the current messages
        logger.info("🧠 Agent thinking...")
        response = self.llm_with_tools.invoke(messages)
        
        # Log if agent is calling tools or providing final answer
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_names = [tc.get('name', 'unknown') for tc in response.tool_calls]
            logger.info(f"🔧 Agent calling tools: {', '.join(tool_names)}")
        else:
            logger.info("💬 Agent providing response")
            if hasattr(response, 'content'):
                logger.debug(f"   Response preview: {response.content[:100]}...")
        
        # Return only the new message to be appended to state
        return {"messages": [response]}
    
    def _should_continue(self, state: DJAgentState) -> str:
        """Decide whether to continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the last message has tool calls, continue
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"
        else:
            return "end"
    
    def _format_response_node(self, state: DJAgentState) -> Dict:
        """Format the final response."""
        messages = state["messages"]
        final_response = messages[-1].content if messages else "No response generated"
        
        # Extract finalized playlist from tool responses
        finalized_playlist = None
        
        # Look through messages for tool call results
        for msg in reversed(messages):  # Start from most recent
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                try:
                    # Check if this is a tool response containing our playlist
                    if '"success": true' in msg.content and '"playlist":' in msg.content:
                        import json
                        # Try to parse the tool response
                        tool_result = json.loads(msg.content)
                        if tool_result.get("success") and tool_result.get("playlist"):
                            finalized_playlist = tool_result["playlist"]
                            logger.info(f"📋 Extracted finalized playlist with {len(finalized_playlist)} tracks from tool response")
                            break
                except:
                    continue
        
        return {
            "final_response": final_response,
            "finalized_playlist": finalized_playlist
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
        
        logger.info(f"📀 Analyzing track: {current_track.get('title', 'Unknown')} by {current_track.get('artist', 'Unknown')}")
        logger.debug(f"   - BPM: {current_track.get('bpm', 'N/A')}")
        logger.debug(f"   - Genre: {current_track.get('genre', 'Unknown')}")
        logger.debug(f"   - Duration: {current_track.get('duration', 0):.1f}s")
        
        # Calculate energy level based on BPM and mood
        energy_level = self._calculate_energy_level(current_track)
        logger.info(f"⚡ Calculated energy level: {energy_level:.2f}")
        
        # Determine dominant vibe
        dominant_vibe = self._get_dominant_vibe(current_track.get("mood", {}))
        logger.info(f"🎵 Dominant vibe: {dominant_vibe}")
        
        vibe_analysis = {
            "track_id": current_track["filepath"],
            "bpm": current_track.get("bpm", 0),
            "energy_level": energy_level,
            "dominant_vibe": dominant_vibe,
            "mood_vector": current_track.get("mood", {}),
            "genre": current_track.get("genre", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Track analysis complete: {energy_level:.2f} energy, {dominant_vibe} vibe")
        
        return {
            "vibe_analysis": vibe_analysis,
            "messages": [AIMessage(content=f"Analyzed track: {current_track.get('title', 'Unknown')} - {energy_level:.2f} energy, {dominant_vibe} vibe")]
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
            avg_recent_bpm = np.mean(recent_bpms) if recent_bpms else vibe_analysis["bpm"]
            bpm_trend = "increasing" if recent_bpms[-1] > recent_bpms[0] else "decreasing"
            logger.info(f"📊 BPM trend: {bpm_trend} (avg: {avg_recent_bpm:.1f})")
        else:
            avg_recent_bpm = vibe_analysis["bpm"]
            bpm_trend = "stable"
            logger.info("📊 No track history - starting fresh")
        
        # Enhance context
        enhanced_context = {
            **context,
            "current_energy": vibe_analysis["energy_level"],
            "avg_recent_bpm": avg_recent_bpm,
            "bpm_trend": bpm_trend,
            "suggested_energy_direction": self._suggest_energy_direction(
                vibe_analysis["energy_level"],
                context.get("time_of_day", "evening"),
                state.get("energy_pattern", "wave")
            )
        }
        
        logger.info(f"🎯 Energy direction: {enhanced_context['suggested_energy_direction']}")
        logger.debug(f"   - Current energy: {enhanced_context['current_energy']:.2f}")
        logger.debug(f"   - Pattern: {state.get('energy_pattern', 'wave')}")
        
        return {
            "context": enhanced_context,
            "messages": [AIMessage(content=f"Context built: {bpm_trend} BPM trend, suggesting {enhanced_context['suggested_energy_direction']} energy")]
        }
    
    def match_vibes_node(self, state: DJAgentState) -> Dict:
        """Find tracks with similar vibes from the database."""
        vibe_analysis = state["vibe_analysis"]
        context = state["context"]
        
        logger.info("🎯 Starting vibe matching...")
        logger.debug(f"   - Reference BPM: {vibe_analysis['bpm']}")
        logger.debug(f"   - Reference energy: {vibe_analysis['energy_level']:.2f}")
        logger.debug(f"   - Reference genre: {vibe_analysis['genre']}")
        
        # Query database for candidate tracks using SQLite
        cursor = self.db.adapter.connection.cursor()
        cursor.execute("SELECT * FROM tracks WHERE filepath != ?", (vibe_analysis["track_id"],))
        columns = [description[0] for description in cursor.description]
        
        # Calculate similarity scores
        candidates = []
        total_tracks = 0
        
        for row in cursor.fetchall():
            total_tracks += 1
            track = dict(zip(columns, row))
            
            # Parse beat_times if it's a JSON string
            if track.get("beat_times") and isinstance(track["beat_times"], str):
                import json
                try:
                    track["beat_times"] = json.loads(track["beat_times"])
                except:
                    track["beat_times"] = []
                    
            similarity = self._calculate_similarity(vibe_analysis, track, context)
            
            if similarity > 0.5:  # Threshold for candidates
                candidates.append({
                    **track,
                    "similarity_score": similarity
                })
                
                if len(candidates) <= 5:  # Log first few matches
                    logger.debug(f"   ✓ Match found: {track.get('title', 'Unknown')} - Score: {similarity:.3f}")
        
        cursor.close()
        
        logger.info(f"📊 Analyzed {total_tracks} tracks, found {len(candidates)} matches (threshold > 0.5)")
        
        # Sort by similarity
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Take top candidates
        top_candidates = candidates[:20]
        
        if top_candidates:
            logger.info(f"🏆 Top match: {top_candidates[0].get('title', 'Unknown')} (score: {top_candidates[0]['similarity_score']:.3f})")
            logger.debug("   Top 5 candidates:")
            for i, cand in enumerate(top_candidates[:5]):
                logger.debug(f"   {i+1}. {cand.get('title', 'Unknown')} - {cand.get('artist', 'Unknown')} ({cand['similarity_score']:.3f})")
        
        return {
            "candidate_tracks": top_candidates,
            "messages": [AIMessage(content=f"Found {len(top_candidates)} vibe-matched tracks")]
        }
    
    def build_playlist_node(self, state: DJAgentState) -> Dict:
        """Build an ordered playlist considering energy flow."""
        candidates = state["candidate_tracks"]
        context = state["context"]
        energy_pattern = state.get("energy_pattern", "wave")
        playlist_length = context.get("playlist_length", 10)
        
        logger.info(f"📝 Building playlist...")
        logger.info(f"   - Pattern: {energy_pattern}")
        logger.info(f"   - Target length: {playlist_length}")
        logger.info(f"   - Available candidates: {len(candidates)}")
        
        # Build playlist based on energy pattern
        playlist = self._build_playlist_by_pattern(
            candidates,
            energy_pattern,
            playlist_length,
            context["current_energy"],
            context["suggested_energy_direction"]
        )
        
        logger.info(f"✅ Built {len(playlist)}-track playlist")
        
        # Log energy flow
        energy_flow = [self._calculate_energy_level(t) for t in playlist]
        logger.debug("   Energy flow:")
        for i, (track, energy) in enumerate(zip(playlist, energy_flow)):
            logger.debug(f"   {i+1}. {track.get('title', 'Unknown')} - Energy: {energy:.2f}")
        
        # Log BPM progression
        bpm_flow = [t.get('bpm', 0) for t in playlist]
        if bpm_flow:
            logger.debug(f"   BPM range: {min(bpm_flow):.0f} - {max(bpm_flow):.0f}")
        
        return {
            "playlist": playlist,
            "messages": [AIMessage(content=f"Built {len(playlist)}-track playlist with {energy_pattern} pattern")]
        }
    
    def plan_transitions_node(self, state: DJAgentState) -> Dict:
        """Plan transitions between tracks in the playlist."""
        playlist = state["playlist"]
        current_track = state["current_track"]
        
        logger.info("🔄 Planning transitions...")
        
        transitions = []
        
        # Plan transition from current track to first playlist track
        if playlist and current_track:
            first_transition = self._plan_transition(current_track, playlist[0])
            transitions.append(first_transition)
            logger.debug(f"   → From current to first: BPM {current_track.get('bpm', 0):.0f} → {playlist[0].get('bpm', 0):.0f}")
        
        # Plan transitions between playlist tracks
        for i in range(len(playlist) - 1):
            transition = self._plan_transition(playlist[i], playlist[i + 1])
            transitions.append(transition)
            
            if i < 3:  # Log first few transitions
                from_bpm = playlist[i].get('bpm', 0)
                to_bpm = playlist[i+1].get('bpm', 0)
                logger.debug(f"   → Track {i+1} to {i+2}: BPM {from_bpm:.0f} → {to_bpm:.0f} ({transition['mix_duration']} bars)")
        
        logger.info(f"✅ Planned {len(transitions)} transitions")
        
        # Log suggested effects summary
        all_effects = []
        for t in transitions:
            all_effects.extend(t.get('suggested_effects', []))
        if all_effects:
            effect_counts = {}
            for effect in all_effects:
                effect_counts[effect] = effect_counts.get(effect, 0) + 1
            logger.debug(f"   Suggested effects: {dict(effect_counts)}")
        
        return {
            "transitions": transitions,
            "messages": [AIMessage(content=f"Planned {len(transitions)} transitions")]
        }
    
    # Helper methods
    
    def _calculate_energy_level(self, track: Dict) -> float:
        """Calculate energy level from BPM and mood."""
        bpm = track.get("bpm", 120)
        
        # For SQLite, we have energy_level directly stored
        if "energy_level" in track and track["energy_level"] is not None:
            return track["energy_level"]
        
        # Otherwise calculate from BPM
        # Normalize BPM to 0-1 scale (60-200 BPM range)
        bpm_energy = (bpm - 60) / 140
        bpm_energy = max(0, min(1, bpm_energy))
        
        return bpm_energy
    
    def _get_dominant_vibe(self, mood: Dict) -> str:
        """Get the dominant mood/vibe from mood scores."""
        # For SQLite, we don't have mood vector, so use genre/BPM
        return "neutral"
    
    def _suggest_energy_direction(self, current_energy: float, time_of_day: str, pattern: str) -> str:
        """Suggest whether energy should go up, down, or maintain."""
        hour = datetime.now().hour
        
        if pattern == "build_up":
            return "increase"
        elif pattern == "cool_down":
            return "decrease"
        elif pattern == "peak_time":
            return "maintain" if current_energy > 0.7 else "increase"
        else:  # wave pattern
            if current_energy > 0.7:
                return "decrease"
            elif current_energy < 0.3:
                return "increase"
            else:
                return "maintain"
    
    def _calculate_similarity(self, reference: Dict, candidate: Dict, context: Dict) -> float:
        """Calculate similarity score between tracks."""
        weights = {
            'bpm_proximity': 0.35,
            'energy_compatibility': 0.30,
            'genre_affinity': 0.25,
            'danceability': 0.10
        }
        
        scores = {}
        
        # BPM proximity (within 5% is perfect match)
        ref_bpm = reference.get("bpm", 120)
        cand_bpm = candidate.get("bpm", 120)
        if ref_bpm > 0:
            bpm_diff = abs(ref_bpm - cand_bpm) / ref_bpm
            scores['bpm_proximity'] = max(0, 1 - (bpm_diff * 20))  # 5% diff = 0 score
        else:
            scores['bpm_proximity'] = 0.5
        
        # Energy compatibility
        ref_energy = reference.get("energy_level", 0.5)
        cand_energy = candidate.get("energy_level", 0.5) or self._calculate_energy_level(candidate)
        energy_diff = abs(ref_energy - cand_energy)
        
        # Consider context for energy compatibility
        if context.get("suggested_energy_direction") == "increase":
            if cand_energy > ref_energy:
                scores['energy_compatibility'] = 1 - (energy_diff * 0.5)
            else:
                scores['energy_compatibility'] = 0.5 - energy_diff
        elif context.get("suggested_energy_direction") == "decrease":
            if cand_energy < ref_energy:
                scores['energy_compatibility'] = 1 - (energy_diff * 0.5)
            else:
                scores['energy_compatibility'] = 0.5 - energy_diff
        else:  # maintain
            scores['energy_compatibility'] = 1 - energy_diff
        
        # Genre affinity
        ref_genre = (reference.get("genre") or "").lower()
        cand_genre = (candidate.get("genre") or "").lower()
        if ref_genre and cand_genre:
            if ref_genre == cand_genre:
                scores['genre_affinity'] = 1.0
            elif any(word in cand_genre for word in ref_genre.split()) or \
                 any(word in ref_genre for word in cand_genre.split()):
                scores['genre_affinity'] = 0.7
            else:
                scores['genre_affinity'] = 0.3
        else:
            scores['genre_affinity'] = 0.5
        
        # Danceability score
        cand_danceability = candidate.get("danceability", 0.7)
        scores['danceability'] = cand_danceability
        
        # Calculate weighted total
        total_score = sum(scores.get(factor, 0) * weight 
                         for factor, weight in weights.items())
        
        # Log detailed scoring for high-scoring tracks
        if total_score > 0.7:
            logger.debug(f"   High score for {candidate.get('title', 'Unknown')}: {total_score:.3f}")
            logger.debug(f"     - BPM: {scores.get('bpm_proximity', 0):.2f}, Energy: {scores.get('energy_compatibility', 0):.2f}, Genre: {scores.get('genre_affinity', 0):.2f}")
        
        return total_score
    
    def _build_playlist_by_pattern(self, candidates: List[Dict], pattern: str, 
                                   length: int, current_energy: float, 
                                   direction: str) -> List[Dict]:
        """Build playlist according to energy pattern."""
        if not candidates:
            return []
        
        playlist = []
        remaining = candidates.copy()
        
        # Calculate target energies for each position
        target_energies = []
        for i in range(length):
            if pattern == "build_up":
                target = current_energy + (i + 1) * (1 - current_energy) / length
            elif pattern == "cool_down":
                target = current_energy - (i + 1) * current_energy / length
            elif pattern == "peak_time":
                target = max(0.8, current_energy)
            else:  # wave
                phase = i % 4
                if phase < 2:
                    target = current_energy + 0.2
                else:
                    target = current_energy - 0.2
            target_energies.append(max(0, min(1, target)))
        
        # Select tracks to match target energies
        for target_energy in target_energies:
            if not remaining:
                break
                
            # Find best match for target energy
            best_track = None
            best_diff = float('inf')
            
            for track in remaining:
                track_energy = self._calculate_energy_level(track)
                diff = abs(track_energy - target_energy)
                if diff < best_diff:
                    best_diff = diff
                    best_track = track
            
            if best_track:
                playlist.append(best_track)
                remaining.remove(best_track)
        
        return playlist
    
    def _plan_transition(self, from_track: Dict, to_track: Dict) -> Dict:
        """Plan transition between two tracks."""
        from_bpm = from_track.get("bpm", 120)
        to_bpm = to_track.get("bpm", 120)
        bpm_diff = abs(from_bpm - to_bpm)
        
        transition = {
            "from_track": from_track.get("filepath"),
            "to_track": to_track.get("filepath"),
            "bpm_change": to_bpm - from_bpm,
            "mix_duration": 32 if bpm_diff < 5 else 16,  # bars
            "suggested_effects": []
        }
        
        # Suggest effects based on transition type
        if bpm_diff > 10:
            transition["suggested_effects"].append("echo_out")
            transition["suggested_effects"].append("filter_sweep")
            logger.debug(f"   Large BPM change ({bpm_diff:.0f}) - suggesting echo/filter effects")
        elif to_bpm > from_bpm:
            transition["suggested_effects"].append("high_pass_filter")
        else:
            transition["suggested_effects"].append("low_pass_filter")
        
        # Add mix point suggestions
        if from_track.get("beat_times"):
            # Find a good exit point (usually 32 or 64 bars from end)
            beat_times = from_track["beat_times"]
            bars_32_time = len(beat_times) - (32 * 4)  # 32 bars
            if bars_32_time > 0:
                transition["exit_point"] = beat_times[bars_32_time]
        
        return transition
    
    async def suggest_next_track(self,
                               current_track: Optional[str] = None,
                               current_track_id: Optional[str] = None,
                               context: Optional[Union[str, Dict]] = None,
                               thread_id: Optional[str] = None) -> Dict:
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
                "error": "Either current_track or current_track_id must be provided"
            }
        
        # If context is a string, use agentic approach
        if isinstance(context, str):
            return await self._suggest_next_track_agentic(
                current_track=track_id,
                context_description=context,
                thread_id=thread_id
            )
        else:
            # Use original approach with dict context
            result = await self._suggest_next_track_original(
                current_track_id=track_id,
                context=context
            )
            # Wrap in expected format
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
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
                    "transition": result["transition"]
                }
    
    async def _suggest_next_track_agentic(self,
                                        current_track: str,
                                        context_description: str,
                                        thread_id: Optional[str] = None) -> Dict:
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
            "messages": [
                HumanMessage(content=prompt)
            ],
            "current_track": None,
            "context": {},
            "track_history": [],
            "candidate_tracks": [],
            "playlist": [],
            "transitions": [],
            "vibe_analysis": None,
            "energy_pattern": "wave",
            "vibe_description": context_description
        }
        
        try:
            result = await self.agent_graph.ainvoke(initial_state)
            response_text = result.get("final_response", "")
            
            return {
                "success": True,
                "response": response_text,
                "thread_id": thread_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id
            }
    
    async def _suggest_next_track_original(self,
                                         current_track_id: str,
                                         context: Optional[Dict] = None) -> Dict:
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
        if current_track.get("beat_times") and isinstance(current_track["beat_times"], str):
            try:
                current_track["beat_times"] = json.loads(current_track["beat_times"])
            except:
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
            "energy_pattern": context.get("energy_pattern", "wave") if context else "wave",
            "vibe_description": None
        }
        
        # Run the graph
        logger.info("🚀 Running LangGraph workflow...")
        result = await self.graph.ainvoke(initial_state)
        
        # Return the first track from playlist as suggestion
        if result["playlist"]:
            suggestion = result["playlist"][0]
            logger.info(f"✅ Suggestion: {suggestion.get('title', 'Unknown')} by {suggestion.get('artist', 'Unknown')}")
            logger.info(f"   - Confidence: {suggestion.get('similarity_score', 0):.2%}")
            logger.info("=" * 50)
            
            return {
                "track": suggestion,
                "confidence": suggestion.get("similarity_score", 0),
                "transition": result["transitions"][0] if result["transitions"] else None,
                "vibe_analysis": result["vibe_analysis"]
            }
        else:
            logger.error("❌ No suitable tracks found")
            logger.info("=" * 50)
            return {"error": "No suitable tracks found"}
    
    async def generate_playlist(self, 
                              vibe_description: Optional[str] = None,
                              seed_track_id: Optional[str] = None,
                              length: int = 10,
                              energy_pattern: str = "wave",
                              context: Optional[Dict] = None,
                              thread_id: Optional[str] = None) -> Dict:
        """Generate a playlist using either a vibe description or seed track.
        
        This method supports both approaches:
        1. Vibe description: Uses the agentic approach with tools
        2. Seed track: Uses the original workflow-based approach
        """
        if vibe_description:
            # Use the new agentic approach
            return await self._generate_playlist_from_vibe(
                vibe_description=vibe_description,
                length=length,
                energy_pattern=energy_pattern,
                thread_id=thread_id
            )
        elif seed_track_id:
            # Use the original seed-based approach
            return await self._generate_playlist_from_seed(
                seed_track_id=seed_track_id,
                length=length,
                energy_pattern=energy_pattern,
                context=context
            )
        else:
            return {
                "success": False,
                "error": "Either vibe_description or seed_track_id must be provided"
            }
    
    async def _generate_playlist_from_vibe(self,
                                         vibe_description: str,
                                         length: int = 20,
                                         energy_pattern: str = "wave",
                                         thread_id: Optional[str] = None) -> Dict:
        """Generate playlist from vibe description using agentic approach."""
        logger.info("=" * 50)
        logger.info("🎨 VIBE-BASED PLAYLIST GENERATION")
        logger.info(f"   Vibe: '{vibe_description}'")
        logger.info(f"   Length: {length} tracks")
        logger.info(f"   Pattern: {energy_pattern}")
        logger.info(f"   Thread: {thread_id}")
        
        # Create the initial message
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
            3. Filter by energy levels using filter_tracks_by_energy if needed
            4. Sort tracks for smooth BPM progression using sort_tracks_by_bpm_progression

            IMPORTANT: 
            - Select UNIQUE tracks only - do not include the same track multiple times
            - After selecting your tracks, you MUST call the finalize_playlist tool with:
              * A list of track filepaths (exactly {length} UNIQUE tracks)
              * Mixing notes for each track explaining why it fits and how to mix it

            The finalize_playlist tool is required to complete the playlist creation."""

        user_message = f"Create a {length}-track playlist with {vibe_description}"
        
        # Combine system and user content into a single message
        combined_message = f"{system_content}\n\nUser request: {user_message}"
        
        initial_state = {
            "messages": [
                HumanMessage(content=combined_message)
            ],
            "vibe_description": vibe_description,
            "energy_pattern": energy_pattern,
            "context": {"playlist_length": length},
            "current_track": None,
            "track_history": [],
            "candidate_tracks": [],
            "playlist": [],
            "transitions": [],
            "vibe_analysis": None,
            "finalized_playlist": None  # Initialize the new field
        }
        
        try:
            logger.info("🚀 Running agentic workflow...")
            result = await self.agent_graph.ainvoke(initial_state)
            
            response_text = result.get("final_response", "")
            logger.info(f"✅ Agent response generated")
            
            # Get the finalized playlist directly from the result
            finalized_playlist = result.get("finalized_playlist")
            
            if finalized_playlist:
                logger.info(f"📋 Found finalized playlist with {len(finalized_playlist)} tracks")
            else:
                logger.warning("⚠️ No finalized playlist found in result")
            
            logger.info("=" * 50)
            
            return {
                "success": True,
                "response": response_text,
                "thread_id": thread_id,
                "finalized_playlist": finalized_playlist,
                "state": result  # Include full state for debugging
            }
            
        except Exception as e:
            logger.error(f"❌ Error in agentic generation: {str(e)}")
            logger.info("=" * 50)
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id
            }
    
    async def _generate_playlist_from_seed(self,
                                         seed_track_id: str,
                                         length: int = 10,
                                         energy_pattern: str = "wave",
                                         context: Optional[Dict] = None) -> Dict:
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
            return {
                "success": False,
                "error": "Seed track not found"
            }
        
        seed_track = dict(zip(columns, row))
        
        # Parse beat_times if needed
        if seed_track.get("beat_times") and isinstance(seed_track["beat_times"], str):
            try:
                seed_track["beat_times"] = json.loads(seed_track["beat_times"])
            except:
                seed_track["beat_times"] = []
        
        # Prepare context
        full_context = {
            **(context or {}),
            "playlist_length": length
        }
        
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
            "vibe_description": None
        }
        
        # Run the original graph
        logger.info("🚀 Running workflow...")
        result = await self.graph.ainvoke(initial_state)
        
        logger.info(f"✅ Generated {len(result['playlist'])} track playlist")
        logger.info("=" * 50)
        
        # Format response to match expected structure
        playlist_text = "\n".join([
            f"{i+1}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} "
            f"({track.get('bpm', 0):.0f} BPM)"
            for i, track in enumerate(result['playlist'])
        ])
        
        return {
            "success": True,
            "response": f"Generated {len(result['playlist'])}-track playlist:\n\n{playlist_text}",
            "playlist": result["playlist"],
            "transitions": result["transitions"],
            "vibe_analysis": result["vibe_analysis"],
            "energy_flow": [self._calculate_energy_level(t) for t in result["playlist"]]
        } 
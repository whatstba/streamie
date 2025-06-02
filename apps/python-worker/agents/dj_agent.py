"""
LangGraph DJ Agent for intelligent playlist and vibe management.
"""

from typing import TypedDict, List, Dict, Optional, Annotated, Sequence
from datetime import datetime
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import numpy as np
from pymongo import MongoClient

from utils.db import get_db


class DJAgentState(TypedDict):
    """State for the DJ agent."""
    current_track: Optional[Dict]
    context: Dict  # time_of_day, crowd_energy, etc.
    track_history: List[Dict]
    candidate_tracks: List[Dict]
    playlist: List[Dict]
    transitions: List[Dict]
    messages: Sequence[BaseMessage]
    vibe_analysis: Optional[Dict]
    energy_pattern: str  # "build_up", "peak_time", "cool_down", "wave"


class DJAgent:
    """LangGraph agent for DJ playlist and vibe management."""
    
    def __init__(self, llm_model: str = "gpt-4"):
        self.db = get_db()
        self.llm = ChatOpenAI(model=llm_model, temperature=0.7)
        self.graph = self._build_graph()
        
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
        
        if not current_track:
            return {"messages": [AIMessage(content="No current track provided")]}
        
        # Calculate energy level based on BPM and mood
        energy_level = self._calculate_energy_level(current_track)
        
        # Determine dominant vibe
        dominant_vibe = self._get_dominant_vibe(current_track.get("mood", {}))
        
        vibe_analysis = {
            "track_id": current_track["filepath"],
            "bpm": current_track.get("bpm", 0),
            "energy_level": energy_level,
            "dominant_vibe": dominant_vibe,
            "mood_vector": current_track.get("mood", {}),
            "genre": current_track.get("genre", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "vibe_analysis": vibe_analysis,
            "messages": [AIMessage(content=f"Analyzed track: {current_track.get('title', 'Unknown')} - {energy_level:.2f} energy, {dominant_vibe} vibe")]
        }
    
    def build_context_node(self, state: DJAgentState) -> Dict:
        """Build the mixing context based on time, history, and preferences."""
        context = state.get("context", {})
        track_history = state.get("track_history", [])
        vibe_analysis = state["vibe_analysis"]
        
        # Analyze recent track history for trends
        if track_history:
            recent_bpms = [t.get("bpm", 0) for t in track_history[-5:]]
            avg_recent_bpm = np.mean(recent_bpms) if recent_bpms else vibe_analysis["bpm"]
            bpm_trend = "increasing" if recent_bpms[-1] > recent_bpms[0] else "decreasing"
        else:
            avg_recent_bpm = vibe_analysis["bpm"]
            bpm_trend = "stable"
        
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
        
        return {
            "context": enhanced_context,
            "messages": [AIMessage(content=f"Context built: {bpm_trend} BPM trend, suggesting {enhanced_context['suggested_energy_direction']} energy")]
        }
    
    def match_vibes_node(self, state: DJAgentState) -> Dict:
        """Find tracks with similar vibes from the database."""
        vibe_analysis = state["vibe_analysis"]
        context = state["context"]
        
        # Query database for candidate tracks
        all_tracks = list(self.db.tracks.find({}))
        
        # Calculate similarity scores
        candidates = []
        for track in all_tracks:
            if track["filepath"] == vibe_analysis["track_id"]:
                continue  # Skip current track
                
            similarity = self._calculate_similarity(vibe_analysis, track, context)
            if similarity > 0.5:  # Threshold for candidates
                candidates.append({
                    **track,
                    "_id": str(track["_id"]),  # Convert ObjectId to string
                    "similarity_score": similarity
                })
        
        # Sort by similarity
        candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Take top candidates
        top_candidates = candidates[:20]
        
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
        
        # Build playlist based on energy pattern
        playlist = self._build_playlist_by_pattern(
            candidates,
            energy_pattern,
            playlist_length,
            context["current_energy"],
            context["suggested_energy_direction"]
        )
        
        return {
            "playlist": playlist,
            "messages": [AIMessage(content=f"Built {len(playlist)}-track playlist with {energy_pattern} pattern")]
        }
    
    def plan_transitions_node(self, state: DJAgentState) -> Dict:
        """Plan transitions between tracks in the playlist."""
        playlist = state["playlist"]
        current_track = state["current_track"]
        
        transitions = []
        
        # Plan transition from current track to first playlist track
        if playlist and current_track:
            first_transition = self._plan_transition(current_track, playlist[0])
            transitions.append(first_transition)
        
        # Plan transitions between playlist tracks
        for i in range(len(playlist) - 1):
            transition = self._plan_transition(playlist[i], playlist[i + 1])
            transitions.append(transition)
        
        return {
            "transitions": transitions,
            "messages": [AIMessage(content=f"Planned {len(transitions)} transitions")]
        }
    
    # Helper methods
    
    def _calculate_energy_level(self, track: Dict) -> float:
        """Calculate energy level from BPM and mood."""
        bpm = track.get("bpm", 120)
        mood = track.get("mood", {})
        
        # Normalize BPM to 0-1 scale (60-200 BPM range)
        bpm_energy = (bpm - 60) / 140
        bpm_energy = max(0, min(1, bpm_energy))
        
        # Calculate mood energy
        high_energy_moods = ["mood_aggressive", "mood_party", "mood_electronic"]
        low_energy_moods = ["mood_relaxed", "mood_sad", "mood_acoustic"]
        
        mood_energy = 0
        for mood_type in high_energy_moods:
            mood_energy += mood.get(mood_type, 0)
        for mood_type in low_energy_moods:
            mood_energy -= mood.get(mood_type, 0) * 0.5
        
        mood_energy = (mood_energy + 1) / 2  # Normalize to 0-1
        
        # Weighted combination
        return 0.6 * bpm_energy + 0.4 * mood_energy
    
    def _get_dominant_vibe(self, mood: Dict) -> str:
        """Get the dominant mood/vibe from mood scores."""
        if not mood:
            return "neutral"
        
        # Remove 'mood_' prefix and find max
        mood_scores = {k.replace("mood_", ""): v for k, v in mood.items()}
        return max(mood_scores, key=mood_scores.get)
    
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
            'bpm_proximity': 0.30,
            'mood_match': 0.25,
            'energy_compatibility': 0.20,
            'genre_affinity': 0.15,
            'key_compatibility': 0.10
        }
        
        scores = {}
        
        # BPM proximity (within 5% is perfect match)
        ref_bpm = reference.get("bpm", 120)
        cand_bpm = candidate.get("bpm", 120)
        bpm_diff = abs(ref_bpm - cand_bpm) / ref_bpm
        scores['bpm_proximity'] = max(0, 1 - (bpm_diff * 20))  # 5% diff = 0 score
        
        # Mood match (cosine similarity of mood vectors)
        ref_mood = reference.get("mood_vector", {})
        cand_mood = candidate.get("mood", {})
        mood_keys = set(ref_mood.keys()) | set(cand_mood.keys())
        if mood_keys:
            ref_vec = [ref_mood.get(k, 0) for k in mood_keys]
            cand_vec = [cand_mood.get(k, 0) for k in mood_keys]
            dot_product = sum(r * c for r, c in zip(ref_vec, cand_vec))
            ref_norm = np.sqrt(sum(r * r for r in ref_vec))
            cand_norm = np.sqrt(sum(c * c for c in cand_vec))
            if ref_norm > 0 and cand_norm > 0:
                scores['mood_match'] = dot_product / (ref_norm * cand_norm)
            else:
                scores['mood_match'] = 0
        else:
            scores['mood_match'] = 0
        
        # Energy compatibility
        ref_energy = reference.get("energy_level", 0.5)
        cand_energy = self._calculate_energy_level(candidate)
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
        ref_genre = reference.get("genre", "").lower()
        cand_genre = candidate.get("genre", "").lower()
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
        
        # Key compatibility (placeholder - would need key detection)
        scores['key_compatibility'] = 0.7  # Default moderate compatibility
        
        # Calculate weighted total
        total_score = sum(scores.get(factor, 0) * weight 
                         for factor, weight in weights.items())
        
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
    
    async def suggest_next_track(self, current_track_id: str, 
                                context: Optional[Dict] = None) -> Dict:
        """Main entry point for getting next track suggestion."""
        # Load current track from DB
        current_track = self.db.tracks.find_one({"filepath": current_track_id})
        if not current_track:
            return {"error": "Track not found"}
        
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
            "energy_pattern": context.get("energy_pattern", "wave") if context else "wave"
        }
        
        # Run the graph
        result = await self.graph.ainvoke(initial_state)
        
        # Return the first track from playlist as suggestion
        if result["playlist"]:
            suggestion = result["playlist"][0]
            return {
                "track": suggestion,
                "confidence": suggestion.get("similarity_score", 0),
                "transition": result["transitions"][0] if result["transitions"] else None,
                "vibe_analysis": result["vibe_analysis"]
            }
        else:
            return {"error": "No suitable tracks found"}
    
    async def generate_playlist(self, seed_track_id: str, length: int = 10,
                               energy_pattern: str = "wave", 
                               context: Optional[Dict] = None) -> Dict:
        """Generate a full playlist from a seed track."""
        # Load seed track
        seed_track = self.db.tracks.find_one({"filepath": seed_track_id})
        if not seed_track:
            return {"error": "Seed track not found"}
        
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
            "energy_pattern": energy_pattern
        }
        
        # Run the graph
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "playlist": result["playlist"],
            "transitions": result["transitions"],
            "vibe_analysis": result["vibe_analysis"],
            "energy_flow": [self._calculate_energy_level(t) for t in result["playlist"]]
        } 
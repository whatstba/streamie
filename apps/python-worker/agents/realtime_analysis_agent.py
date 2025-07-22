"""
Real-time Analysis Agent for continuous track analysis in DJ sessions.
"""

from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime
import json
from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage

from models import Deck, DeckStatus
from utils.enhanced_analyzer import EnhancedTrackAnalyzer
from services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🔬 [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class RealTimeAnalysisAgent:
    """Agent responsible for real-time analysis of loaded tracks."""
    
    def __init__(self, analysis_service: AnalysisService):
        self.analysis_service = analysis_service
        self.active_analyses = {}  # deck_id -> task_id mapping
        self.last_deck_states = {}  # Track deck state changes
        
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state and trigger analysis for newly loaded tracks."""
        logger.info("🔬 Real-time analysis agent checking deck states")
        
        updates = {
            "analysis_status": {},
            "analysis_results": {}
        }
        
        # Get current deck states
        decks = state.get("decks", {})
        
        for deck_id, deck_state in decks.items():
            # Check if this is a newly loaded track
            if self._is_newly_loaded(deck_id, deck_state):
                logger.info(f"🔬 New track detected on deck {deck_id}: {deck_state.get('track_filepath')}")
                
                # Trigger analysis
                task_id = await self._start_analysis(deck_id, deck_state)
                if task_id:
                    self.active_analyses[deck_id] = task_id
                    updates["analysis_status"][deck_id] = "analyzing"
            
            # Check ongoing analyses
            if deck_id in self.active_analyses:
                status = await self._check_analysis_status(deck_id)
                updates["analysis_status"][deck_id] = status["status"]
                
                if status["status"] == "completed":
                    updates["analysis_results"][deck_id] = status["results"]
                    del self.active_analyses[deck_id]
                elif status["status"] == "failed":
                    logger.error(f"❌ Analysis failed for deck {deck_id}: {status.get('error')}")
                    del self.active_analyses[deck_id]
        
        # Update last known states
        self.last_deck_states = {
            deck_id: {
                "track_filepath": deck_state.get("track_filepath"),
                "loaded_at": deck_state.get("loaded_at")
            }
            for deck_id, deck_state in decks.items()
        }
        
        return updates
    
    def _is_newly_loaded(self, deck_id: str, deck_state: Dict) -> bool:
        """Check if a track was newly loaded on the deck."""
        current_track = deck_state.get("track_filepath")
        
        if not current_track:
            return False
        
        # Check if this deck had a different track before
        if deck_id not in self.last_deck_states:
            return True
        
        last_track = self.last_deck_states[deck_id].get("track_filepath")
        return current_track != last_track
    
    async def _start_analysis(self, deck_id: str, deck_state: Dict) -> Optional[str]:
        """Start analysis for a track."""
        filepath = deck_state.get("track_filepath")
        if not filepath:
            return None
        
        # Priority based on deck status
        priority = 1 if deck_state.get("is_playing") else 2
        
        try:
            task_id = await self.analysis_service.enqueue_analysis(
                filepath=filepath,
                priority=priority,
                deck_id=deck_id,
                analysis_type="realtime"
            )
            logger.info(f"📊 Started analysis task {task_id} for deck {deck_id}")
            return task_id
        except Exception as e:
            logger.error(f"❌ Failed to start analysis: {e}")
            return None
    
    async def _check_analysis_status(self, deck_id: str) -> Dict:
        """Check the status of an ongoing analysis."""
        task_id = self.active_analyses.get(deck_id)
        if not task_id:
            return {"status": "unknown"}
        
        try:
            status = await self.analysis_service.get_task_status(task_id)
            return status
        except Exception as e:
            logger.error(f"❌ Failed to check analysis status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def analyze_for_transition(self, deck_a_id: str, deck_b_id: str, 
                                   state: Dict[str, Any]) -> Dict:
        """Perform specialized analysis for upcoming transition."""
        logger.info(f"🔄 Analyzing transition from deck {deck_a_id} to {deck_b_id}")
        
        decks = state.get("decks", {})
        deck_a = decks.get(deck_a_id, {})
        deck_b = decks.get(deck_b_id, {})
        
        if not deck_a.get("track_filepath") or not deck_b.get("track_filepath"):
            return {"error": "Tracks not loaded on both decks"}
        
        try:
            # Get detailed analysis for both tracks
            analysis_a = await self.analysis_service.get_cached_analysis(
                deck_a["track_filepath"]
            )
            analysis_b = await self.analysis_service.get_cached_analysis(
                deck_b["track_filepath"]
            )
            
            # Calculate compatibility
            compatibility = self._calculate_transition_compatibility(
                analysis_a, analysis_b
            )
            
            # Find optimal transition points
            transition_points = self._find_transition_points(
                analysis_a, analysis_b, deck_a, deck_b
            )
            
            return {
                "compatibility": compatibility,
                "transition_points": transition_points,
                "recommended_effects": self._suggest_transition_effects(
                    analysis_a, analysis_b, compatibility
                )
            }
        except Exception as e:
            logger.error(f"❌ Transition analysis failed: {e}")
            return {"error": str(e)}
    
    def _calculate_transition_compatibility(self, analysis_a: Dict, 
                                          analysis_b: Dict) -> Dict:
        """Calculate how compatible two tracks are for mixing."""
        compatibility = {
            "overall": 0.0,
            "bpm": 0.0,
            "key": 0.0,
            "energy": 0.0,
            "genre": 0.0
        }
        
        # BPM compatibility (within 5% is excellent)
        bpm_a = analysis_a.get("bpm", 120)
        bpm_b = analysis_b.get("bpm", 120)
        bpm_diff_percent = abs(bpm_a - bpm_b) / bpm_a * 100
        
        if bpm_diff_percent <= 5:
            compatibility["bpm"] = 1.0
        elif bpm_diff_percent <= 10:
            compatibility["bpm"] = 0.7
        else:
            compatibility["bpm"] = max(0, 1 - bpm_diff_percent / 50)
        
        # Key compatibility (using Camelot wheel)
        key_a = analysis_a.get("camelot_key", "8A")
        key_b = analysis_b.get("camelot_key", "8A")
        compatibility["key"] = self._calculate_key_compatibility(key_a, key_b)
        
        # Energy compatibility
        energy_a = analysis_a.get("energy_level", 0.5)
        energy_b = analysis_b.get("energy_level", 0.5)
        energy_diff = abs(energy_a - energy_b)
        compatibility["energy"] = 1.0 - min(energy_diff, 1.0)
        
        # Genre compatibility (simplified)
        genre_a = analysis_a.get("genre", "")
        genre_b = analysis_b.get("genre", "")
        compatibility["genre"] = 1.0 if genre_a == genre_b else 0.5
        
        # Overall score (weighted average)
        compatibility["overall"] = (
            compatibility["bpm"] * 0.4 +
            compatibility["key"] * 0.3 +
            compatibility["energy"] * 0.2 +
            compatibility["genre"] * 0.1
        )
        
        return compatibility
    
    def _calculate_key_compatibility(self, key_a: str, key_b: str) -> float:
        """Calculate key compatibility using Camelot wheel."""
        # Simplified Camelot compatibility
        # Perfect: same key, +1, -1, or relative major/minor
        
        if key_a == key_b:
            return 1.0
        
        # Extract number and letter
        try:
            num_a = int(key_a[:-1])
            letter_a = key_a[-1]
            num_b = int(key_b[:-1])
            letter_b = key_b[-1]
            
            # Adjacent keys on wheel
            if letter_a == letter_b and abs(num_a - num_b) == 1:
                return 0.9
            
            # Relative major/minor (same number, different letter)
            if num_a == num_b and letter_a != letter_b:
                return 0.85
            
            # Two steps away
            if letter_a == letter_b and abs(num_a - num_b) == 2:
                return 0.6
                
        except:
            pass
        
        return 0.3  # Default low compatibility
    
    def _find_transition_points(self, analysis_a: Dict, analysis_b: Dict,
                               deck_a: Dict, deck_b: Dict) -> List[Dict]:
        """Find optimal points for transitioning between tracks."""
        points = []
        
        # Get structural information
        structure_a = analysis_a.get("structure", {})
        structure_b = analysis_b.get("structure", {})
        
        # Common transition points
        transition_types = [
            ("outro_start", "intro_end"),
            ("breakdown_start", "drop_start"),
            ("verse_end", "verse_start")
        ]
        
        for out_point, in_point in transition_types:
            if out_point in structure_a and in_point in structure_b:
                points.append({
                    "type": f"{out_point}_to_{in_point}",
                    "deck_a_time": structure_a[out_point],
                    "deck_b_time": structure_b[in_point],
                    "confidence": 0.8
                })
        
        # Beat-aligned points (every 16 bars)
        beats_a = analysis_a.get("beat_times", [])
        beats_b = analysis_b.get("beat_times", [])
        
        if beats_a and beats_b:
            # Find 16-bar boundaries
            bars_16_a = [beats_a[i] for i in range(0, len(beats_a), 64) if i < len(beats_a)]
            bars_16_b = [beats_b[i] for i in range(0, len(beats_b), 64) if i < len(beats_b)]
            
            # Add some beat-aligned points
            for i, time_a in enumerate(bars_16_a[-3:]):  # Last 3 16-bar sections
                for j, time_b in enumerate(bars_16_b[:3]):  # First 3 16-bar sections
                    points.append({
                        "type": "beat_aligned",
                        "deck_a_time": time_a,
                        "deck_b_time": time_b,
                        "confidence": 0.6
                    })
        
        # Sort by confidence
        points.sort(key=lambda x: x["confidence"], reverse=True)
        
        return points[:5]  # Return top 5 transition points
    
    def _suggest_transition_effects(self, analysis_a: Dict, analysis_b: Dict,
                                  compatibility: Dict) -> List[Dict]:
        """Suggest effects based on track analysis and compatibility."""
        effects = []
        
        # Low compatibility might need more effects to smooth transition
        if compatibility["overall"] < 0.5:
            effects.append({
                "type": "filter_sweep",
                "intensity": 0.7,
                "reason": "Low compatibility requires filtering"
            })
        
        # BPM difference might need echo/delay
        if compatibility["bpm"] < 0.8:
            effects.append({
                "type": "echo",
                "intensity": 0.4,
                "reason": "BPM difference benefits from echo"
            })
        
        # Energy difference
        energy_diff = abs(
            analysis_a.get("energy_level", 0.5) - 
            analysis_b.get("energy_level", 0.5)
        )
        if energy_diff > 0.3:
            effects.append({
                "type": "eq_sweep",
                "intensity": 0.5,
                "reason": "Energy difference requires EQ adjustment"
            })
        
        # Limit to 2 effects max
        return effects[:2]
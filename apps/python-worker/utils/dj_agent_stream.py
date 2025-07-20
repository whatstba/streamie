"""
Enhanced DJ Agent streaming utilities for better UI/UX
"""

import logging
from typing import Dict, Optional
import re


class DJAgentStreamEnhancer:
    """Enhances DJ Agent output for better UI visualization"""

    def __init__(self):
        self.stage_patterns = {
            "analyzing_vibe": [
                r"VIBE ANALYSIS",
                r"Analyzing vibe",
                r"Understanding.*mood",
                r"Detecting.*genres?",
                r"Energy.*analysis",
                r"🎨.*vibe",
                r"Vibe.*description",
                r"Starting playlist generation",
            ],
            "searching_library": [
                r"Searching.*tracks?",
                r"Looking for.*music",
                r"Querying.*database",
                r"Found \d+ tracks?",
                r"Filtering.*library",
                r"🔍.*search",
                r"Database.*query",
                r"Retrieving.*tracks",
            ],
            "matching_tracks": [
                r"Matching.*mood",
                r"Scoring.*tracks?",
                r"Evaluating.*compatibility",
                r"Analyzing.*BPM",
                r"Checking.*harmonic",
                r"🎵.*match",
                r"Track.*analysis",
                r"Compatibility.*score",
            ],
            "optimizing_order": [
                r"Optimizing.*order",
                r"Arranging.*flow",
                r"Building.*progression",
                r"Creating.*journey",
                r"Sequencing.*tracks?",
                r"🎛️.*transition",
                r"Flow.*optimization",
                r"Playlist.*sequence",
            ],
            "finalizing": [
                r"Finalizing.*playlist",
                r"Completing.*selection",
                r"Final.*adjustments",
                r"Playlist.*complete",
                r"✅.*finish",
                r"Complete.*playlist",
                r"Ready.*play",
            ],
        }

        self.current_stage = "analyzing_vibe"
        self.stage_number = 1
        self.stage_progress = 0.0
        self.found_tracks = []
        self.detected_mood = None

    def detect_stage(self, message: str) -> Optional[str]:
        """Detect which stage we're in based on the message"""
        for stage, patterns in self.stage_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return stage
        return None

    def extract_track_info(self, message: str) -> Optional[Dict]:
        """Extract track information from log messages"""
        # Pattern: "Found track: Title - Artist (BPM: 120)"
        track_pattern = r"Found track:\s*(.+?)\s*-\s*(.+?)(?:\s*\(BPM:\s*(\d+)\))?"
        match = re.search(track_pattern, message)
        if match:
            return {
                "title": match.group(1).strip(),
                "artist": match.group(2).strip(),
                "bpm": int(match.group(3)) if match.group(3) else None,
                "match_score": 0.8 + (len(self.found_tracks) * 0.02),  # Mock score
            }

        # Pattern: "Adding: filename.mp3" or "Added track:"
        add_patterns = [
            r"Adding:\s*(.+?)(?:\.mp3|\.m4a|\.flac)?",
            r"Added track:\s*(.+)",
            r"Selected:\s*(.+)",
            r"Track \d+:\s*(.+)",
            r"🎵\s*(.+?)\s*(?:-\s*(.+?))?(?:\s*\((\d+)\s*BPM\))?",
        ]

        for pattern in add_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 3:  # Has artist and BPM
                    return {
                        "title": match.group(1).strip(),
                        "artist": match.group(2).strip()
                        if match.group(2)
                        else "Unknown Artist",
                        "bpm": int(match.group(3)) if match.group(3) else None,
                        "match_score": 0.7 + (len(self.found_tracks) * 0.02),
                    }
                else:  # Just filename
                    filename = match.group(1).strip()
                    # Try to extract artist from "Artist - Title" format
                    parts = filename.split(" - ", 1)
                    if len(parts) == 2:
                        return {
                            "title": parts[1],
                            "artist": parts[0],
                            "bpm": None,
                            "match_score": 0.7,
                        }
                    else:
                        return {
                            "title": filename,
                            "artist": "Unknown Artist",
                            "bpm": None,
                            "match_score": 0.7,
                        }

        return None

    def extract_mood_info(self, message: str) -> Optional[Dict]:
        """Extract mood analysis from messages"""
        # Pattern: "Detected genres: hip-hop, r&b"
        genre_pattern = r"(?:Detected|Found|Identified).*genres?:\s*(.+)"
        match = re.search(genre_pattern, message, re.IGNORECASE)
        if match:
            genres = [g.strip() for g in match.group(1).split(",")]
            return {"genres": genres}

        # Pattern: "Energy level: 0.8" or "High energy"
        energy_pattern = r"Energy.*?:\s*([\d.]+)|(\w+)\s+energy"
        match = re.search(energy_pattern, message, re.IGNORECASE)
        if match:
            if match.group(1):
                try:
                    # Validate it's a real number, not "..."
                    energy_val = float(match.group(1))
                    if 0 <= energy_val <= 1:
                        return {"energy": energy_val}
                except ValueError:
                    pass  # Ignore if not a valid float
            elif match.group(2):
                energy_map = {"low": 0.3, "medium": 0.5, "high": 0.8, "very high": 0.9}
                return {"energy": energy_map.get(match.group(2).lower(), 0.5)}

        # Pattern: "Mood: energetic"
        mood_pattern = r"Mood:\s*(\w+)"
        match = re.search(mood_pattern, message, re.IGNORECASE)
        if match:
            return {"mood": match.group(1).lower()}

        return None

    def calculate_stage_progress(self, message: str) -> float:
        """Calculate progress within current stage"""
        # Look for percentage patterns
        percent_pattern = r"(\d+)%|\((\d+)/(\d+)\)"
        match = re.search(percent_pattern, message)
        if match:
            if match.group(1):
                return float(match.group(1)) / 100
            elif match.group(2) and match.group(3):
                return float(match.group(2)) / float(match.group(3))

        # Estimate based on stage and found tracks
        if self.current_stage == "matching_tracks":
            return min(len(self.found_tracks) / 10, 1.0)

        # Default progression
        return min(self.stage_progress + 0.1, 0.9)

    def process_message(self, message: str) -> Dict:
        """Process a log message and return structured data"""
        # Debug logging
        logger = logging.getLogger("DJAgentStreamEnhancer")
        logger.debug(f"Processing message: {message[:100]}...")

        # Detect stage change
        new_stage = self.detect_stage(message)
        if new_stage and new_stage != self.current_stage:
            self.current_stage = new_stage
            self.stage_number = list(self.stage_patterns.keys()).index(new_stage) + 1
            self.stage_progress = 0.0
            logger.info(f"Stage changed to: {new_stage}")

            return {
                "type": "stage_update",
                "stage": self.current_stage,
                "stage_number": self.stage_number,
                "total_stages": len(self.stage_patterns),
                "progress": self.stage_progress,
                "message": self._get_stage_message(self.current_stage),
                "data": {"detected_mood": self.detected_mood}
                if self.detected_mood
                else {},
            }

        # Extract track info
        track_info = self.extract_track_info(message)
        if track_info:
            self.found_tracks.append(track_info)
            return {
                "type": "track_found",
                "track": track_info,
                "current_count": len(self.found_tracks),
                "target_count": 10,
            }

        # Extract mood info
        mood_info = self.extract_mood_info(message)
        if mood_info:
            if not self.detected_mood:
                self.detected_mood = {"genres": [], "energy": 0.5, "mood": "analyzing"}
            self.detected_mood.update(mood_info)

            # Send mood update with current stage
            return {
                "type": "stage_update",
                "stage": self.current_stage,
                "stage_number": self.stage_number,
                "total_stages": len(self.stage_patterns),
                "progress": self.stage_progress,
                "message": message,
                "data": {
                    "detected_genres": self.detected_mood.get("genres", []),
                    "energy_level": self.detected_mood.get("energy", 0.5),
                    "mood": self.detected_mood.get("mood", "analyzing"),
                },
            }

        # Update progress
        self.stage_progress = self.calculate_stage_progress(message)

        # Default status update
        return {
            "type": "stage_update",
            "stage": self.current_stage,
            "stage_number": self.stage_number,
            "total_stages": len(self.stage_patterns),
            "progress": self.stage_progress,
            "message": message,
            "data": {},
        }

    def _get_stage_message(self, stage: str) -> str:
        """Get a user-friendly message for each stage"""
        messages = {
            "analyzing_vibe": "Understanding your musical mood...",
            "searching_library": "Searching through the music library...",
            "matching_tracks": "Finding tracks that match your vibe...",
            "optimizing_order": "Arranging tracks for the perfect flow...",
            "finalizing": "Putting the finishing touches on your playlist...",
        }
        return messages.get(stage, "Processing...")

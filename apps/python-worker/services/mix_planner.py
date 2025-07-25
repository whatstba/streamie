"""Mix planning service - plans track order and transitions"""

import logging
from typing import List, Dict
from models.database import Track

logger = logging.getLogger(__name__)


class MixPlanner:
    """Plans mixes including track order and transitions"""

    def __init__(self):
        self.transition_types = ["crossfade", "echo_out", "filter_sweep", "beatmatch"]

    async def plan_mix(
        self, tracks: List[Track], target_duration: float, vibe_description: str
    ) -> Dict:
        """Plan a mix from available tracks"""
        # Sort tracks for good flow
        sorted_tracks = self._sort_tracks_for_flow(tracks, vibe_description)

        # Select tracks to fit duration
        selected_tracks = self._select_tracks_for_duration(
            sorted_tracks, target_duration
        )

        # Plan transitions
        mix_plan = self._plan_transitions(selected_tracks)

        # Calculate total duration
        total_duration = sum(t["track"].duration for t in mix_plan["tracks"])

        mix_plan["total_duration"] = total_duration
        mix_plan["vibe"] = vibe_description

        return mix_plan

    def _sort_tracks_for_flow(self, tracks: List[Track], vibe: str) -> List[Track]:
        """Sort tracks for good energy flow"""
        # Simple energy-based sorting with some randomization
        # Can be enhanced with more sophisticated algorithms

        # Group by energy levels
        low_energy = [t for t in tracks if t.energy < 0.4]
        mid_energy = [t for t in tracks if 0.4 <= t.energy < 0.7]
        high_energy = [t for t in tracks if t.energy >= 0.7]

        # Determine flow pattern based on vibe
        if "chill" in vibe.lower() or "relax" in vibe.lower():
            # Start low, stay low-mid
            flow = low_energy[:3] + mid_energy[:4] + low_energy[3:6]
        elif "party" in vibe.lower() or "energetic" in vibe.lower():
            # Build up energy
            flow = mid_energy[:2] + high_energy[:6] + mid_energy[2:4]
        elif "warm" in vibe.lower() or "build" in vibe.lower():
            # Gradual build
            flow = low_energy[:2] + mid_energy[:3] + high_energy[:3] + mid_energy[3:5]
        else:
            # Default: varied flow
            flow = []
            for i in range(len(tracks) // 3):
                if i < len(low_energy):
                    flow.append(low_energy[i])
                if i < len(mid_energy):
                    flow.append(mid_energy[i])
                if i < len(high_energy):
                    flow.append(high_energy[i])

        # Ensure we have tracks
        if not flow:
            flow = tracks[:10]

        # Sort by BPM within groups for smoother transitions
        flow.sort(key=lambda t: (int(t.energy * 3), t.bpm))

        return flow

    def _select_tracks_for_duration(
        self, tracks: List[Track], target_duration: float
    ) -> List[Track]:
        """Select tracks to approximately match target duration"""
        selected = []
        current_duration = 0

        for track in tracks:
            if current_duration >= target_duration:
                break

            # Don't add very short tracks
            if track.duration < 120:  # Less than 2 minutes
                continue

            selected.append(track)
            current_duration += track.duration

        # Ensure minimum tracks
        if len(selected) < 3 and len(tracks) >= 3:
            selected = tracks[:3]

        return selected

    def _plan_transitions(self, tracks: List[Track]) -> Dict:
        """Plan transitions between tracks"""
        mix_tracks = []

        for i, track in enumerate(tracks):
            track_plan = {"track": track, "position": i}

            # Plan transition to next track
            if i < len(tracks) - 1:
                next_track = tracks[i + 1]
                transition = self._choose_transition(track, next_track)

                # Calculate transition timing
                # Start transition in last 10% of track or last 30 seconds
                transition_window = min(track.duration * 0.1, 30)
                transition["start_time"] = track.duration - transition_window

                track_plan["transition"] = transition
            else:
                # Last track - no transition
                track_plan["transition"] = {
                    "type": "fade_out",
                    "duration": 5.0,
                    "start_time": track.duration - 5,
                }

            # Calculate tempo adjustment for beatmatching
            if i > 0:
                prev_track = tracks[i - 1]
                tempo_diff = (track.bpm - prev_track.bpm) / prev_track.bpm

                # Only adjust if difference is small
                if abs(tempo_diff) < 0.08:  # Within 8%
                    track_plan["tempo_adjustment"] = -tempo_diff

            mix_tracks.append(track_plan)

        return {"tracks": mix_tracks}

    def _choose_transition(self, track1: Track, track2: Track) -> Dict:
        """Choose appropriate transition type"""
        bpm_diff = abs(track1.bpm - track2.bpm)
        energy_diff = abs(track1.energy - track2.energy)

        # Check key compatibility
        key_compatible = self._check_key_compatibility(track1.key, track2.key)

        # Choose transition based on compatibility
        if bpm_diff < 5 and key_compatible:
            # Perfect for beatmatching
            transition_type = "beatmatch"
            duration = 16.0  # Longer blend
        elif bpm_diff < 10:
            # Good for filter sweep
            transition_type = "filter_sweep"
            duration = 8.0
        elif energy_diff > 0.3:
            # Big energy change - use echo
            transition_type = "echo_out"
            duration = 4.0
        else:
            # Default crossfade
            transition_type = "crossfade"
            duration = 6.0

        return {
            "type": transition_type,
            "duration": duration,
            "bpm_diff": bpm_diff,
            "energy_diff": energy_diff,
            "key_compatible": key_compatible,
        }

    def _check_key_compatibility(self, key1: str, key2: str) -> bool:
        """Check if two keys are harmonically compatible"""
        # Camelot wheel compatibility
        camelot_compatible = {
            "1A": ["1A", "12A", "2A", "1B"],
            "1B": ["1B", "12B", "2B", "1A"],
            "2A": ["2A", "1A", "3A", "2B"],
            "2B": ["2B", "1B", "3B", "2A"],
            "3A": ["3A", "2A", "4A", "3B"],
            "3B": ["3B", "2B", "4B", "3A"],
            "4A": ["4A", "3A", "5A", "4B"],
            "4B": ["4B", "3B", "5B", "4A"],
            "5A": ["5A", "4A", "6A", "5B"],
            "5B": ["5B", "4B", "6B", "5A"],
            "6A": ["6A", "5A", "7A", "6B"],
            "6B": ["6B", "5B", "7B", "6A"],
            "7A": ["7A", "6A", "8A", "7B"],
            "7B": ["7B", "6B", "8B", "7A"],
            "8A": ["8A", "7A", "9A", "8B"],
            "8B": ["8B", "7B", "9B", "8A"],
            "9A": ["9A", "8A", "10A", "9B"],
            "9B": ["9B", "8B", "10B", "9A"],
            "10A": ["10A", "9A", "11A", "10B"],
            "10B": ["10B", "9B", "11B", "10A"],
            "11A": ["11A", "10A", "12A", "11B"],
            "11B": ["11B", "10B", "12B", "11A"],
            "12A": ["12A", "11A", "1A", "12B"],
            "12B": ["12B", "11B", "1B", "12A"],
        }

        # Check if keys are in Camelot notation
        if key1 in camelot_compatible:
            return key2 in camelot_compatible.get(key1, [])

        # Simple check for same key
        return key1 == key2

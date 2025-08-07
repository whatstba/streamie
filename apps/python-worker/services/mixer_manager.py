"""Mixer Manager Service for DJ mixing operations"""

import asyncio
import logging
import math
from typing import Optional, Dict, Tuple
from datetime import datetime

from models import MixerState, Deck
from models.database import get_session

logger = logging.getLogger(__name__)


class CrossfaderCurve:
    """Different crossfader curve implementations"""

    @staticmethod
    def linear(position: float) -> Tuple[float, float]:
        """Linear crossfader curve (-1 to 1) -> (gain_a, gain_b)"""
        # Position: -1 = full A, 0 = center, 1 = full B
        position = max(-1.0, min(1.0, position))

        if position <= 0:
            # Left side: A at full, B fades in
            gain_a = 1.0
            gain_b = position + 1.0
        else:
            # Right side: B at full, A fades out
            gain_a = 1.0 - position
            gain_b = 1.0

        return gain_a, gain_b

    @staticmethod
    def logarithmic(position: float) -> Tuple[float, float]:
        """Logarithmic crossfader curve for smoother transitions"""
        position = max(-1.0, min(1.0, position))

        # Convert position to 0-1 range
        normalized = (position + 1.0) / 2.0

        # Apply logarithmic curve
        # Using x^2 curve for smooth fade
        gain_a = math.sqrt(1.0 - normalized)
        gain_b = math.sqrt(normalized)

        return gain_a, gain_b

    @staticmethod
    def scratch(position: float) -> Tuple[float, float]:
        """Sharp scratch curve with minimal overlap"""
        position = max(-1.0, min(1.0, position))

        # Very sharp cutoff near center
        threshold = 0.1

        if position < -threshold:
            return 1.0, 0.0
        elif position > threshold:
            return 0.0, 1.0
        else:
            # Quick transition in center zone
            normalized = (position + threshold) / (2 * threshold)
            gain_a = 1.0 - normalized
            gain_b = normalized
            return gain_a, gain_b


class MixerManager:
    """Manages mixer operations and state"""

    def __init__(self, engine):
        self.engine = engine
        self._mixer_lock = asyncio.Lock()
        self._level_history = {"A": [], "B": [], "C": [], "D": [], "master": []}

    async def get_mixer_state(self) -> Optional[Dict]:
        """Get current mixer state"""
        async with get_session(self.engine) as session:
            mixer = await session.get(MixerState, 1)  # Single mixer instance
            if not mixer:
                return None

            return {
                "crossfader": mixer.crossfader,
                "crossfader_curve": mixer.crossfader_curve,
                "master_volume": mixer.master_volume,
                "master_gain": mixer.master_gain,
                "monitor_volume": mixer.monitor_volume,
                "monitor_cue_mix": mixer.monitor_cue_mix,
                "recording": mixer.recording,
                "broadcasting": mixer.broadcasting,
            }

    async def update_crossfader(
        self, position: float, apply_to_decks: bool = True
    ) -> Dict:
        """Update crossfader position and optionally apply gains to decks"""
        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                # Clamp position
                position = max(-1.0, min(1.0, position))
                mixer.crossfader = position

                # Calculate deck gains based on curve
                curve_func = getattr(
                    CrossfaderCurve, mixer.crossfader_curve, CrossfaderCurve.linear
                )
                gain_a, gain_b = curve_func(position)

                # Apply gains to decks if requested
                if apply_to_decks:
                    deck_a = await session.get(Deck, "A")
                    deck_b = await session.get(Deck, "B")

                    if deck_a:
                        deck_a.crossfader_gain = gain_a
                    if deck_b:
                        deck_b.crossfader_gain = gain_b

                await session.commit()

                return {
                    "success": True,
                    "position": position,
                    "gain_a": gain_a,
                    "gain_b": gain_b,
                    "curve": mixer.crossfader_curve,
                }

    async def update_crossfader_curve(self, curve: str) -> Dict:
        """Update crossfader curve type"""
        valid_curves = ["linear", "logarithmic", "scratch"]
        if curve not in valid_curves:
            return {
                "success": False,
                "error": f"Invalid curve type. Must be one of: {valid_curves}",
            }

        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                mixer.crossfader_curve = curve

                # Calculate deck gains based on new curve
                position = mixer.crossfader
                curve_func = getattr(CrossfaderCurve, curve, CrossfaderCurve.linear)
                gain_a, gain_b = curve_func(position)

                # Apply gains to decks
                deck_a = await session.get(Deck, "A")
                deck_b = await session.get(Deck, "B")

                if deck_a:
                    deck_a.crossfader_gain = gain_a
                if deck_b:
                    deck_b.crossfader_gain = gain_b

                await session.commit()

                return {
                    "success": True,
                    "position": position,
                    "gain_a": gain_a,
                    "gain_b": gain_b,
                    "curve": curve,
                }

    async def update_master_output(
        self, volume: Optional[float] = None, gain: Optional[float] = None
    ) -> Dict:
        """Update master output settings"""
        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                updates = {}
                if volume is not None:
                    mixer.master_volume = max(0.0, min(1.0, volume))
                    updates["master_volume"] = mixer.master_volume

                if gain is not None:
                    mixer.master_gain = max(0.0, min(2.0, gain))  # Allow up to 2x gain
                    updates["master_gain"] = mixer.master_gain

                await session.commit()

                return {"success": True, "updated": updates}

    async def update_monitor_settings(
        self, volume: Optional[float] = None, cue_mix: Optional[float] = None
    ) -> Dict:
        """Update monitor/cue output settings"""
        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                updates = {}
                if volume is not None:
                    mixer.monitor_volume = max(0.0, min(1.0, volume))
                    updates["monitor_volume"] = mixer.monitor_volume

                if cue_mix is not None:
                    # 0 = cue only, 1 = master only
                    mixer.monitor_cue_mix = max(0.0, min(1.0, cue_mix))
                    updates["monitor_cue_mix"] = mixer.monitor_cue_mix

                await session.commit()

                return {"success": True, "updated": updates}

    async def calculate_channel_output(self, deck_id: str) -> Dict:
        """Calculate final output level for a deck channel"""
        async with get_session(self.engine) as session:
            deck = await session.get(Deck, deck_id)
            mixer = await session.get(MixerState, 1)

            if not deck or not mixer:
                return {"level": 0.0, "clipping": False}

            # Start with deck volume
            level = deck.volume

            # Apply gain
            level *= deck.gain

            # Apply EQ (simplified - in reality would use filters)
            # For now, just factor in EQ as gain adjustments
            eq_factor = 1.0
            eq_factor *= 1.0 + deck.eq_low * 0.3  # Low frequencies have less impact
            eq_factor *= 1.0 + deck.eq_mid * 0.5  # Mid frequencies moderate impact
            eq_factor *= 1.0 + deck.eq_high * 0.2  # High frequencies less impact
            level *= eq_factor

            # Apply crossfader for A/B decks
            if deck_id in ["A", "B"]:
                curve_func = getattr(
                    CrossfaderCurve, mixer.crossfader_curve, CrossfaderCurve.linear
                )
                gain_a, gain_b = curve_func(mixer.crossfader)

                if deck_id == "A":
                    level *= gain_a
                else:
                    level *= gain_b

            # Check for clipping before master section
            pre_master_clipping = level > 1.0

            # Apply master gain and volume
            level *= mixer.master_gain
            level *= mixer.master_volume

            # Final clipping check
            clipping = level > 1.0
            level = min(1.0, level)  # Hard limit

            return {
                "deck_id": deck_id,
                "level": level,
                "pre_fader_level": deck.volume * deck.gain,
                "post_fader_level": level,
                "clipping": clipping,
                "pre_master_clipping": pre_master_clipping,
            }

    async def get_all_channel_levels(self) -> Dict:
        """Get output levels for all channels"""
        levels = {}
        for deck_id in ["A", "B", "C", "D"]:
            levels[deck_id] = await self.calculate_channel_output(deck_id)

        # Calculate master output
        async with get_session(self.engine) as session:
            mixer = await session.get(MixerState, 1)

            # Sum all channel outputs
            master_level = sum(ch["level"] for ch in levels.values())

            # Check master clipping
            master_clipping = master_level > 1.0
            master_level = min(1.0, master_level)

            levels["master"] = {
                "level": master_level,
                "clipping": master_clipping,
                "volume": mixer.master_volume if mixer else 0.8,
                "gain": mixer.master_gain if mixer else 1.0,
            }

        # Store in history for monitoring
        timestamp = datetime.utcnow()
        for channel, data in levels.items():
            if channel not in self._level_history:
                self._level_history[channel] = []

            self._level_history[channel].append(
                {
                    "timestamp": timestamp,
                    "level": data["level"],
                    "clipping": data.get("clipping", False),
                }
            )

            # Keep only last 100 samples
            if len(self._level_history[channel]) > 100:
                self._level_history[channel].pop(0)

        return levels

    async def auto_gain_deck(self, deck_id: str) -> Dict:
        """Calculate and apply auto-gain for a deck"""
        async with get_session(self.engine) as session:
            deck = await session.get(Deck, deck_id)

            if not deck or not deck.track_filepath:
                return {"success": False, "error": "Deck not loaded"}

            # Get track energy level from tracks.db
            import sqlite3
            import os

            tracks_db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "tracks.db"
            )

            try:
                conn = sqlite3.connect(tracks_db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT energy_level, spectral_centroid
                    FROM tracks
                    WHERE filepath = ?
                """,
                    (deck.track_filepath,),
                )

                row = cursor.fetchone()
                conn.close()

                if not row:
                    return {"success": False, "error": "Track analysis not found"}

                energy_level = row[0] or 0.5

                # Calculate gain based on energy level
                # Target normalized level is 0.7
                target_level = 0.7

                # Simple gain calculation (in practice would be more sophisticated)
                if energy_level > 0:
                    suggested_gain = target_level / energy_level
                    # Clamp gain between 0.5 and 1.5
                    suggested_gain = max(0.5, min(1.5, suggested_gain))
                else:
                    suggested_gain = 1.0

                # Apply the gain
                deck.gain = suggested_gain
                deck.auto_gain_applied = True
                await session.commit()

                return {
                    "success": True,
                    "deck_id": deck_id,
                    "energy_level": energy_level,
                    "suggested_gain": suggested_gain,
                    "applied": True,
                }

            except Exception as e:
                logger.error(f"Error calculating auto-gain: {e}")
                return {"success": False, "error": str(e)}

    async def toggle_deck_cue(self, deck_id: str) -> Dict:
        """Toggle cue monitoring for a deck"""
        async with get_session(self.engine) as session:
            deck = await session.get(Deck, deck_id)

            if not deck:
                return {"success": False, "error": f"Deck {deck_id} not found"}

            # Toggle cue state
            deck.cue_active = not getattr(deck, "cue_active", False)
            await session.commit()

            return {"success": True, "deck_id": deck_id, "cue_active": deck.cue_active}

    async def start_recording(self, filepath: str) -> Dict:
        """Start recording the master output"""
        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                if mixer.recording:
                    return {"success": False, "error": "Already recording"}

                mixer.recording = True
                mixer.recording_filepath = filepath
                mixer.recording_started_at = datetime.utcnow()
                await session.commit()

                return {
                    "success": True,
                    "filepath": filepath,
                    "started_at": mixer.recording_started_at.isoformat(),
                }

    async def stop_recording(self) -> Dict:
        """Stop recording"""
        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                if not mixer.recording:
                    return {"success": False, "error": "Not recording"}

                filepath = mixer.recording_filepath
                started_at = mixer.recording_started_at

                mixer.recording = False
                mixer.recording_filepath = None
                mixer.recording_started_at = None
                await session.commit()

                duration = (
                    (datetime.utcnow() - started_at).total_seconds()
                    if started_at
                    else 0
                )

                return {"success": True, "filepath": filepath, "duration": duration}

    async def set_crossfader(self, position: float) -> Dict:
        """Set crossfader position"""
        async with self._mixer_lock:
            async with get_session(self.engine) as session:
                mixer = await session.get(MixerState, 1)
                if not mixer:
                    return {"success": False, "error": "Mixer state not found"}

                # Clamp position to -1.0 to 1.0
                mixer.crossfader = max(-1.0, min(1.0, position))
                await session.commit()

                return {"success": True, "crossfader": mixer.crossfader}

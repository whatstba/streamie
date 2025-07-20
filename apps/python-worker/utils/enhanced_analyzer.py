"""Enhanced track analyzer with key detection and structure analysis."""

import os
import json
import logging
import librosa
import numpy as np
from typing import Dict, List, Optional
import essentia.standard as es

logger = logging.getLogger(__name__)


class EnhancedTrackAnalyzer:
    """Analyzes tracks for enhanced metadata including key, structure, and auto-generated hot cues."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def analyze_file(self, filepath: str) -> bool:
        """Analyze a single audio file and store results in database."""
        try:
            logger.info(f"Starting enhanced analysis for: {filepath}")

            # Load audio
            y, sr = librosa.load(filepath, sr=None)
            duration = len(y) / sr

            # Basic analysis
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beats, sr=sr).tolist()

            # Key detection using Essentia
            key_info = self._detect_key(filepath)

            # Structure analysis
            structure = self._analyze_structure(y, sr, tempo)

            # Generate auto hot cues
            hot_cues = self._generate_hot_cues(structure, beat_times, duration)

            # Energy and mood analysis
            energy_info = self._analyze_energy(y, sr)

            # Store in database
            success = await self._store_analysis(
                filepath=filepath,
                tempo=float(tempo),
                beat_times=beat_times,
                key_info=key_info,
                structure=structure,
                hot_cues=hot_cues,
                energy_info=energy_info,
                duration=duration,
            )

            logger.info(f"Enhanced analysis completed for: {filepath}")
            return success

        except Exception as e:
            logger.error(f"Enhanced analysis failed for {filepath}: {e}")
            return False

    def _detect_key(self, filepath: str) -> Dict:
        """Detect musical key using Essentia."""
        try:
            # Load audio with Essentia
            loader = es.MonoLoader(filename=filepath)
            audio = loader()

            # Use key detection algorithm
            key_detector = es.KeyExtractor()
            key, scale, strength = key_detector(audio)

            # Convert to Camelot notation for DJ compatibility
            camelot = self._key_to_camelot(key, scale)

            return {
                "key": key,
                "scale": scale,
                "strength": float(strength),
                "camelot": camelot,
            }

        except Exception as e:
            logger.error(f"Key detection failed: {e}")
            return {
                "key": "Unknown",
                "scale": "Unknown",
                "strength": 0.0,
                "camelot": None,
            }

    def _analyze_structure(self, y: np.ndarray, sr: int, tempo: float) -> Dict:
        """Analyze song structure to identify intro, verses, chorus, outro."""
        try:
            # Compute beat-synchronous features
            hop_length = 512

            # Chroma features for harmonic structure
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

            # Spectral features for energy changes
            spectral_centroids = librosa.feature.spectral_centroid(
                y=y, sr=sr, hop_length=hop_length
            )[0]

            # Self-similarity matrix for structure
            rec_mat = librosa.segment.recurrence_matrix(chroma, mode="affinity")

            # Detect segments using spectral clustering
            bounds = librosa.segment.agglomerative(rec_mat, 15)
            bound_times = librosa.frames_to_time(bounds, sr=sr, hop_length=hop_length)

            # Analyze each segment
            segments = []
            for i in range(len(bound_times) - 1):
                start = bound_times[i]
                end = bound_times[i + 1]

                # Extract features for this segment
                start_frame = int(start * sr / hop_length)
                end_frame = int(end * sr / hop_length)

                segment_energy = np.mean(spectral_centroids[start_frame:end_frame])
                segment_chroma = np.mean(chroma[:, start_frame:end_frame], axis=1)

                # Classify segment type based on features
                segment_type = self._classify_segment(
                    segment_energy, segment_chroma, i, len(bound_times) - 1
                )

                segments.append(
                    {
                        "start": float(start),
                        "end": float(end),
                        "type": segment_type,
                        "energy": float(segment_energy),
                    }
                )

            return {"segments": segments, "total_segments": len(segments)}

        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {"segments": [], "total_segments": 0}

    def _classify_segment(
        self, energy: float, chroma: np.ndarray, index: int, total: int
    ) -> str:
        """Classify a segment as intro, verse, chorus, bridge, or outro."""
        # Simple heuristic classification
        if index == 0:
            return "intro"
        elif index >= total - 1:
            return "outro"
        elif energy > np.mean(chroma) * 1.5:
            return "chorus"
        elif energy < np.mean(chroma) * 0.8:
            return "bridge"
        else:
            return "verse"

    def _generate_hot_cues(
        self, structure: Dict, beat_times: List[float], duration: float
    ) -> List[Dict]:
        """Generate auto hot cues based on song structure."""
        hot_cues = []
        cue_colors = {
            "intro": "#00FF00",  # Green
            "verse": "#0080FF",  # Blue
            "chorus": "#FF0000",  # Red
            "bridge": "#FF00FF",  # Magenta
            "outro": "#FFFF00",  # Yellow
            "drop": "#FF8000",  # Orange
            "buildup": "#00FFFF",  # Cyan
        }

        # Add cues for major structure points
        for i, segment in enumerate(structure.get("segments", [])):
            # Skip very short segments
            if segment["end"] - segment["start"] < 4.0:
                continue

            # Find nearest beat to segment start
            nearest_beat_time = min(beat_times, key=lambda x: abs(x - segment["start"]))

            hot_cues.append(
                {
                    "name": f"{segment['type'].capitalize()} {i + 1}",
                    "time": nearest_beat_time,
                    "color": cue_colors.get(segment["type"], "#FFFFFF"),
                    "type": "cue",
                    "index": len(hot_cues),
                }
            )

        # Add mix in/out points if not already covered
        if not any(cue["name"].lower().startswith("intro") for cue in hot_cues):
            # Add mix in point around 16-32 beats
            if len(beat_times) > 32:
                hot_cues.insert(
                    0,
                    {
                        "name": "Mix In",
                        "time": beat_times[16],
                        "color": "#00FF00",
                        "type": "cue",
                        "index": 0,
                    },
                )

        if not any(cue["name"].lower().startswith("outro") for cue in hot_cues):
            # Add mix out point 32-64 beats before end
            if len(beat_times) > 64:
                mix_out_beat = len(beat_times) - 32
                hot_cues.append(
                    {
                        "name": "Mix Out",
                        "time": beat_times[mix_out_beat],
                        "color": "#FFFF00",
                        "type": "cue",
                        "index": len(hot_cues),
                    }
                )

        # Re-index cues
        for i, cue in enumerate(hot_cues):
            cue["index"] = i

        # Limit to 8 hot cues (standard DJ software limit)
        return hot_cues[:8]

    def _analyze_energy(self, y: np.ndarray, sr: int) -> Dict:
        """Analyze energy characteristics of the track."""
        try:
            # RMS energy
            rms = librosa.feature.rms(y=y)[0]

            # Spectral centroid (brightness)
            cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

            # Zero crossing rate (percussiveness)
            zcr = librosa.feature.zero_crossing_rate(y)[0]

            # Calculate overall energy level (0-1)
            energy_level = float(np.mean(rms))
            energy_variance = float(np.std(rms))

            # Classify energy profile
            if energy_variance > 0.3:
                energy_profile = "dynamic"
            elif energy_level > 0.7:
                energy_profile = "high"
            elif energy_level < 0.3:
                energy_profile = "low"
            else:
                energy_profile = "medium"

            return {
                "level": energy_level,
                "variance": energy_variance,
                "brightness": float(np.mean(cent)),
                "percussiveness": float(np.mean(zcr)),
                "profile": energy_profile,
            }

        except Exception as e:
            logger.error(f"Energy analysis failed: {e}")
            return {
                "level": 0.5,
                "variance": 0.1,
                "brightness": 5000.0,
                "percussiveness": 0.1,
                "profile": "medium",
            }

    def _key_to_camelot(self, key: str, scale: str) -> Optional[str]:
        """Convert musical key to Camelot Wheel notation."""
        camelot_wheel = {
            ("C", "major"): "8B",
            ("C", "minor"): "5A",
            ("C#", "major"): "3B",
            ("Db", "major"): "3B",
            ("C#", "minor"): "12A",
            ("Db", "minor"): "12A",
            ("D", "major"): "10B",
            ("D", "minor"): "7A",
            ("D#", "major"): "5B",
            ("Eb", "major"): "5B",
            ("D#", "minor"): "2A",
            ("Eb", "minor"): "2A",
            ("E", "major"): "12B",
            ("E", "minor"): "9A",
            ("F", "major"): "7B",
            ("F", "minor"): "4A",
            ("F#", "major"): "2B",
            ("Gb", "major"): "2B",
            ("F#", "minor"): "11A",
            ("Gb", "minor"): "11A",
            ("G", "major"): "9B",
            ("G", "minor"): "6A",
            ("G#", "major"): "4B",
            ("Ab", "major"): "4B",
            ("G#", "minor"): "1A",
            ("Ab", "minor"): "1A",
            ("A", "major"): "11B",
            ("A", "minor"): "8A",
            ("A#", "major"): "6B",
            ("Bb", "major"): "6B",
            ("A#", "minor"): "3A",
            ("Bb", "minor"): "3A",
            ("B", "major"): "1B",
            ("B", "minor"): "10A",
        }

        return camelot_wheel.get((key, scale.lower()))

    async def _store_analysis(
        self,
        filepath: str,
        tempo: float,
        beat_times: List[float],
        key_info: Dict,
        structure: Dict,
        hot_cues: List[Dict],
        energy_info: Dict,
        duration: float,
    ) -> bool:
        """Store analysis results in the database."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get relative path
            rel_path = os.path.relpath(filepath)

            # Update tracks table with enhanced metadata
            cursor.execute(
                """
                UPDATE tracks SET
                    bpm = ?,
                    beat_times = ?,
                    key = ?,
                    key_scale = ?,
                    key_confidence = ?,
                    camelot_key = ?,
                    energy_level = ?,
                    energy_profile = ?,
                    structure = ?,
                    hot_cues = ?,
                    analysis_status = 'completed',
                    analyzed_at = CURRENT_TIMESTAMP
                WHERE filepath = ?
            """,
                (
                    tempo,
                    json.dumps(beat_times),
                    key_info.get("key"),
                    key_info.get("scale"),
                    key_info.get("strength"),
                    key_info.get("camelot"),
                    energy_info.get("level"),
                    energy_info.get("profile"),
                    json.dumps(structure),
                    json.dumps(hot_cues),
                    rel_path,
                ),
            )

            # If track doesn't exist, insert it
            if cursor.rowcount == 0:
                # Get basic metadata first
                from utils.id3_reader import read_audio_metadata

                metadata = read_audio_metadata(filepath)

                cursor.execute(
                    """
                    INSERT INTO tracks (
                        filename, filepath, duration, title, artist, album,
                        genre, year, has_artwork, bpm, beat_times, key,
                        key_scale, key_confidence, camelot_key, energy_level,
                        energy_profile, structure, hot_cues, analysis_status,
                        analyzed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
                """,
                    (
                        os.path.basename(filepath),
                        rel_path,
                        duration,
                        metadata.get("title"),
                        metadata.get("artist"),
                        metadata.get("album"),
                        metadata.get("genre"),
                        metadata.get("date"),
                        metadata.get("has_artwork", False),
                        tempo,
                        json.dumps(beat_times),
                        key_info.get("key"),
                        key_info.get("scale"),
                        key_info.get("strength"),
                        key_info.get("camelot"),
                        energy_info.get("level"),
                        energy_info.get("profile"),
                        json.dumps(structure),
                        json.dumps(hot_cues),
                    ),
                )

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to store analysis for {filepath}: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

"""Enhanced track analyzer with key detection and structure analysis."""

import os
import json
import logging
import librosa
import numpy as np
from typing import Dict, List, Optional, Generator, Tuple
import essentia.standard as es
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamingAnalysisResult:
    """Result from streaming analysis chunk."""
    chunk_index: int
    total_chunks: int
    bpm_estimate: Optional[float] = None
    beat_positions: Optional[List[float]] = None
    energy_level: Optional[float] = None
    spectral_centroid: Optional[float] = None
    onset_positions: Optional[List[float]] = None
    is_final: bool = False


class EnhancedTrackAnalyzer:
    """Analyzes tracks for enhanced metadata including key, structure, and auto-generated hot cues."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.streaming_chunk_size = 30  # seconds per chunk
        self.streaming_overlap = 5  # seconds of overlap between chunks

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
    
    async def analyze_streaming(self, filepath: str) -> Generator[StreamingAnalysisResult, None, None]:
        """Analyze audio file in streaming chunks for real-time feedback."""
        try:
            # Get total duration first
            info = await asyncio.to_thread(librosa.get_duration, filename=filepath)
            total_duration = info
            
            # Calculate chunks
            chunk_size_samples = int(self.streaming_chunk_size * 44100)  # Assuming 44.1kHz
            overlap_samples = int(self.streaming_overlap * 44100)
            
            total_chunks = int(np.ceil(total_duration / (self.streaming_chunk_size - self.streaming_overlap)))
            
            # Process chunks
            for chunk_idx in range(total_chunks):
                offset = chunk_idx * (self.streaming_chunk_size - self.streaming_overlap)
                duration = self.streaming_chunk_size
                
                # Load chunk
                y_chunk, sr = await asyncio.to_thread(
                    librosa.load, 
                    filepath, 
                    offset=offset, 
                    duration=duration,
                    sr=44100
                )
                
                # Analyze chunk
                result = await self._analyze_chunk(
                    y_chunk, sr, chunk_idx, total_chunks, offset
                )
                
                yield result
                
                # Final analysis on last chunk
                if chunk_idx == total_chunks - 1:
                    # Perform full key detection on complete file
                    final_result = await self._finalize_streaming_analysis(filepath)
                    yield final_result
                    
        except Exception as e:
            logger.error(f"Streaming analysis failed: {e}")
            yield StreamingAnalysisResult(
                chunk_index=-1,
                total_chunks=0,
                is_final=True
            )
    
    async def _analyze_chunk(self, y: np.ndarray, sr: int, 
                           chunk_idx: int, total_chunks: int, 
                           offset: float) -> StreamingAnalysisResult:
        """Analyze a single audio chunk."""
        try:
            result = StreamingAnalysisResult(
                chunk_index=chunk_idx,
                total_chunks=total_chunks
            )
            
            # Quick BPM estimation
            tempo, beats = await asyncio.to_thread(
                librosa.beat.beat_track, y=y, sr=sr
            )
            result.bpm_estimate = float(tempo)
            
            # Convert beat frames to absolute times
            beat_times = librosa.frames_to_time(beats, sr=sr)
            result.beat_positions = (beat_times + offset).tolist()
            
            # Energy analysis
            rms = librosa.feature.rms(y=y)[0]
            result.energy_level = float(np.mean(rms))
            
            # Spectral centroid (brightness)
            cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            result.spectral_centroid = float(np.mean(cent))
            
            # Onset detection for cue points
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            result.onset_positions = (onset_times + offset).tolist()
            
            return result
            
        except Exception as e:
            logger.error(f"Chunk analysis failed: {e}")
            return StreamingAnalysisResult(
                chunk_index=chunk_idx,
                total_chunks=total_chunks
            )
    
    async def _finalize_streaming_analysis(self, filepath: str) -> StreamingAnalysisResult:
        """Perform final analysis that requires the complete file."""
        try:
            # Key detection needs full file
            key_info = await asyncio.to_thread(self._detect_key, filepath)
            
            # Create final result
            result = StreamingAnalysisResult(
                chunk_index=-1,
                total_chunks=-1,
                is_final=True
            )
            
            # Add key info to result (extend dataclass in real implementation)
            # For now, log it
            logger.info(f"Final analysis - Key: {key_info['key']} {key_info['scale']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Final analysis failed: {e}")
            return StreamingAnalysisResult(
                chunk_index=-1,
                total_chunks=-1,
                is_final=True
            )
    
    def analyze_beat_phase(self, audio_position: float, beat_times: List[float], 
                          bpm: float) -> Dict[str, float]:
        """Calculate beat phase information for perfect sync."""
        if not beat_times or bpm <= 0:
            return {"phase": 0.0, "next_beat": 0.0, "beat_number": 0}
        
        # Find current beat
        current_beat_idx = 0
        for i, beat_time in enumerate(beat_times):
            if beat_time > audio_position:
                break
            current_beat_idx = i
        
        # Calculate phase (0-1) within current beat
        beat_duration = 60.0 / bpm
        
        if current_beat_idx < len(beat_times) - 1:
            current_beat = beat_times[current_beat_idx]
            next_beat = beat_times[current_beat_idx + 1]
            phase = (audio_position - current_beat) / (next_beat - current_beat)
        else:
            # Extrapolate for last beat
            current_beat = beat_times[current_beat_idx]
            phase = (audio_position - current_beat) / beat_duration
        
        return {
            "phase": min(1.0, max(0.0, phase)),
            "next_beat": beat_times[current_beat_idx + 1] if current_beat_idx < len(beat_times) - 1 else current_beat + beat_duration,
            "beat_number": current_beat_idx,
            "bars": current_beat_idx // 4,
            "beat_in_bar": current_beat_idx % 4
        }

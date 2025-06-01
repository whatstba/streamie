"""Utility functions for audio analysis using librosa."""

import librosa
from typing import Dict, List


def analyze_track(file_path: str) -> Dict[str, any]:
    """Return BPM and beat times for the given audio file."""
    try:
        y, sr = librosa.load(file_path)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        return {
            "bpm": float(tempo),
            "beat_times": beat_times.tolist(),
        }
    except Exception as e:
        print(f"Error analyzing track {file_path}: {e}")
        raise


def run_beat_track(file_path: str) -> float:
    """Compatibility wrapper that returns only the BPM."""
    result = analyze_track(file_path)
    return result["bpm"]

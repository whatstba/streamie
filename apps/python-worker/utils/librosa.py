"""Utility functions for audio analysis using librosa."""

import librosa
from typing import Dict


def analyze_track(file_path: str) -> Dict[str, any]:
    """Return BPM and beat times for the given audio file."""
    import os
    
    # Resolve file path if it's relative
    if not os.path.isabs(file_path):
        # Try common base directories
        base_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Music"),
            os.getcwd()
        ]
        
        for base_dir in base_dirs:
            full_path = os.path.join(base_dir, file_path)
            if os.path.exists(full_path):
                file_path = full_path
                break
        else:
            # If not found in any base directory, check if it exists as-is
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
    
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

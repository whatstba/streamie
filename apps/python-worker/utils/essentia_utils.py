"""Utilities for audio analysis using the Essentia library."""

from typing import Dict

try:
    from essentia.standard import MusicExtractor
except Exception as e:  # pragma: no cover - library may not be installed
    MusicExtractor = None  # type: ignore
    print(f"Essentia not available: {e}")


def analyze_mood(file_path: str) -> Dict[str, float]:
    """Return mood probabilities for a track using Essentia."""
    if MusicExtractor is None:
        raise RuntimeError("Essentia is not installed")

    try:
        extractor = MusicExtractor()
        features = extractor(file_path)
        highlevel = features.get('highlevel', {})
        mood = {}
        for key in [
            'mood_acoustic',
            'mood_aggressive',
            'mood_electronic',
            'mood_happy',
            'mood_party',
            'mood_relaxed',
            'mood_sad',
        ]:
            value = highlevel.get(key)
            if isinstance(value, (int, float)):
                mood[key] = float(value)
            elif isinstance(value, list) and value:
                mood[key] = float(value[0])
        return mood
    except Exception as e:
        print(f"Error running Essentia mood analysis on {file_path}: {e}")
        return {}

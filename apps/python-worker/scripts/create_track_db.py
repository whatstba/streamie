"""Analyze all tracks and store metadata in MongoDB."""

import os
from pathlib import Path
from typing import List

from utils.id3_reader import read_audio_metadata
from utils.librosa import analyze_track
from utils.essentia_utils import analyze_mood
from utils.db import get_db
from main import MUSIC_DIR

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".m4p"}


def iter_audio_files(base_dir: str) -> List[Path]:
    for root, _, files in os.walk(base_dir):
        for name in files:
            if not any(name.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                continue
            yield Path(root) / name


def main():
    db = get_db()
    collection = db.tracks

    for file_path in iter_audio_files(MUSIC_DIR):
        relative_path = os.path.relpath(file_path, MUSIC_DIR)
        metadata = read_audio_metadata(str(file_path))
        analysis = analyze_track(str(file_path))
        mood_scores = analyze_mood(str(file_path))
        # Pick the mood label with highest score
        mood_label = None
        if mood_scores:
            mood_label = max(mood_scores, key=mood_scores.get)

        document = {
            "filepath": relative_path,
            "filename": file_path.name,
            "duration": metadata.get("duration", 0.0),
            "title": metadata.get("title"),
            "artist": metadata.get("artist"),
            "album": metadata.get("album"),
            "genre": metadata.get("genre"),
            "year": metadata.get("date"),
            "has_artwork": metadata.get("has_artwork", False),
            "bpm": analysis["bpm"],
            "beat_times": analysis["beat_times"],
            "mood": mood_label,
        }

        collection.update_one(
            {"filepath": relative_path}, {"$set": document}, upsert=True
        )
        print(
            f"Stored {file_path.name}: {analysis['bpm']:.2f} BPM, {len(analysis['beat_times'])} beats, mood={mood_label}"
        )


if __name__ == "__main__":
    main()

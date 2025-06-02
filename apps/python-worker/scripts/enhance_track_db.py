"""
Enhance track database with additional metadata for LangGraph agent.

This script adds:
- Energy level calculation
- Danceability estimation
- Tempo stability
- Vocal presence detection
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_db
import librosa
import numpy as np
from pathlib import Path


def calculate_energy_level(bpm: float, mood: dict) -> float:
    """Calculate energy level from BPM and mood."""
    # Normalize BPM to 0-1 scale (60-200 BPM range)
    bpm_energy = (bpm - 60) / 140
    bpm_energy = max(0, min(1, bpm_energy))
    
    # Calculate mood energy
    high_energy_moods = ["mood_aggressive", "mood_party", "mood_electronic"]
    low_energy_moods = ["mood_relaxed", "mood_sad", "mood_acoustic"]
    
    mood_energy = 0
    for mood_type in high_energy_moods:
        mood_energy += mood.get(mood_type, 0)
    for mood_type in low_energy_moods:
        mood_energy -= mood.get(mood_type, 0) * 0.5
    
    mood_energy = (mood_energy + 1) / 2  # Normalize to 0-1
    
    # Weighted combination
    return 0.6 * bpm_energy + 0.4 * mood_energy


def estimate_danceability(bpm: float, beat_times: list) -> float:
    """Estimate danceability based on BPM and beat regularity."""
    # Optimal dance BPM range is 120-130
    if 120 <= bpm <= 130:
        bpm_score = 1.0
    elif 100 <= bpm <= 140:
        bpm_score = 0.8
    elif 90 <= bpm <= 150:
        bpm_score = 0.6
    else:
        bpm_score = 0.3
    
    # Check beat regularity
    if len(beat_times) > 10:
        beat_intervals = np.diff(beat_times[:100])  # First 100 beats
        regularity = 1 - (np.std(beat_intervals) / np.mean(beat_intervals))
        regularity = max(0, min(1, regularity))
    else:
        regularity = 0.5
    
    return 0.7 * bpm_score + 0.3 * regularity


def calculate_tempo_stability(beat_times: list) -> float:
    """Calculate how stable the tempo is throughout the track."""
    if len(beat_times) < 10:
        return 0.5
    
    # Calculate rolling BPM over windows
    window_size = 32  # 8 bars
    bpms = []
    
    for i in range(0, len(beat_times) - window_size, window_size // 2):
        window = beat_times[i:i + window_size]
        if len(window) > 1:
            intervals = np.diff(window)
            avg_interval = np.mean(intervals)
            if avg_interval > 0:
                window_bpm = 60 / avg_interval
                bpms.append(window_bpm)
    
    if not bpms:
        return 0.5
    
    # Calculate stability (inverse of coefficient of variation)
    bpm_std = np.std(bpms)
    bpm_mean = np.mean(bpms)
    
    if bpm_mean > 0:
        cv = bpm_std / bpm_mean
        stability = 1 - min(cv * 2, 1)  # Scale CV to 0-1
    else:
        stability = 0.5
    
    return stability


def detect_vocal_presence(file_path: str) -> float:
    """Estimate vocal presence using spectral analysis."""
    try:
        # Load a portion of the track
        y, sr = librosa.load(file_path, duration=60, sr=22050)
        
        # Calculate spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        
        # Vocals typically have energy in 300-3000 Hz range
        # Spectral centroid in this range suggests vocals
        vocal_range_ratio = np.sum((spectral_centroids > 300) & (spectral_centroids < 3000)) / len(spectral_centroids)
        
        # Also check for harmonic content (characteristic of vocals)
        harmonic, percussive = librosa.effects.hpss(y)
        harmonic_ratio = np.sum(np.abs(harmonic)) / (np.sum(np.abs(y)) + 1e-6)
        
        # Combine metrics
        vocal_presence = 0.6 * vocal_range_ratio + 0.4 * harmonic_ratio
        
        return min(vocal_presence, 1.0)
    
    except Exception as e:
        print(f"Error detecting vocals: {e}")
        return 0.5


def enhance_track_metadata():
    """Add enhanced metadata to all tracks in the database."""
    db = get_db()
    collection = db.tracks
    
    # Get all tracks
    tracks = list(collection.find({}))
    total = len(tracks)
    
    print(f"Enhancing metadata for {total} tracks...")
    
    for i, track in enumerate(tracks):
        print(f"\nProcessing {i+1}/{total}: {track['filename']}")
        
        # Calculate energy level
        energy_level = calculate_energy_level(
            track.get('bpm', 120),
            track.get('mood', {})
        )
        
        # Estimate danceability
        danceability = estimate_danceability(
            track.get('bpm', 120),
            track.get('beat_times', [])
        )
        
        # Calculate tempo stability
        tempo_stability = calculate_tempo_stability(
            track.get('beat_times', [])
        )
        
        # Detect vocal presence (if file exists)
        vocal_presence = 0.5  # Default
        if 'filepath' in track:
            from main import MUSIC_DIR
            file_path = os.path.join(MUSIC_DIR, track['filepath'])
            if os.path.exists(file_path):
                vocal_presence = detect_vocal_presence(file_path)
        
        # Update document
        update_data = {
            'energy_level': energy_level,
            'danceability': danceability,
            'tempo_stability': tempo_stability,
            'vocal_presence': vocal_presence,
            'valence': track.get('mood', {}).get('mood_happy', 0.5),  # Use happy mood as proxy for valence
        }
        
        collection.update_one(
            {'_id': track['_id']},
            {'$set': update_data}
        )
        
        print(f"  Energy: {energy_level:.2f}, Dance: {danceability:.2f}, "
              f"Stability: {tempo_stability:.2f}, Vocals: {vocal_presence:.2f}")
    
    print(f"\n✅ Enhanced metadata for {total} tracks!")


if __name__ == "__main__":
    enhance_track_metadata() 
"""
Simplified track analysis script using SQLite (without Essentia).

This script:
- Creates a local SQLite database
- Analyzes audio files for metadata, BPM, and beats
- Stores everything locally in SQL for fast access
- Supports incremental updates (only processes unanalyzed or changed files)
"""

import os
import sys
import sqlite3
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our utilities
from utils.id3_reader import read_audio_metadata
from utils.librosa import analyze_track

# Audio analysis libraries
import librosa
import numpy as np

# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.m4p'}

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tracks.db')

# Get MUSIC_DIR from environment or use default
MUSIC_DIR = os.getenv('MUSIC_DIR', '/Users/lynscott/Music')


class DeprecatedTrackDatabase:
    """SQLite database manager for track analysis data."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.connection = None
        self.ensure_database()
    
    def ensure_database(self):
        """Create database and tables if they don't exist."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
        
        cursor = self.connection.cursor()
        
        # Create tracks table with all fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_hash TEXT,
                file_size INTEGER,
                last_modified REAL,
                
                -- Basic metadata
                title TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                year TEXT,
                track TEXT,
                albumartist TEXT,
                duration REAL,
                has_artwork BOOLEAN DEFAULT FALSE,
                
                -- Audio analysis
                bpm REAL,
                beat_times TEXT,  -- JSON array of beat times
                
                -- Enhanced features (calculated from BPM)
                energy_level REAL,
                danceability REAL,
                tempo_stability REAL,
                
                -- Processing metadata
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_version INTEGER DEFAULT 1
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filepath ON tracks(filepath)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bpm ON tracks(bpm)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy ON tracks(energy_level)')
        
        self.connection.commit()
        print(f"✅ Database initialized at {self.db_path}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Generate hash of file for change detection."""
        try:
            with open(file_path, 'rb') as f:
                # Read first and last 8KB for speed
                start = f.read(8192)
                f.seek(-8192, 2)
                end = f.read(8192)
                return hashlib.md5(start + end).hexdigest()
        except:
            return ""
    
    def needs_analysis(self, file_path: str) -> bool:
        """Check if file needs analysis (new or changed)."""
        cursor = self.connection.cursor()
        rel_path = os.path.relpath(file_path, MUSIC_DIR)
        
        cursor.execute('SELECT file_hash, last_modified FROM tracks WHERE filepath = ?', (rel_path,))
        row = cursor.fetchone()
        
        if not row:
            return True  # New file
        
        # Check if file has changed
        current_hash = self.get_file_hash(file_path)
        current_mtime = os.path.getmtime(file_path)
        
        return (current_hash != row['file_hash'] or 
                abs(current_mtime - row['last_modified']) > 1)
    
    def save_track(self, file_path: str, metadata: Dict, analysis: Dict, enhanced: Dict = None):
        """Save track data to database."""
        cursor = self.connection.cursor()
        rel_path = os.path.relpath(file_path, MUSIC_DIR)
        
        # File metadata
        file_hash = self.get_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        last_modified = os.path.getmtime(file_path)
        
        # Prepare beat times as JSON
        beat_times_json = json.dumps(analysis.get('beat_times', []))
        
        # Base data
        data = {
            'filepath': rel_path,
            'filename': Path(file_path).name,
            'file_hash': file_hash,
            'file_size': file_size,
            'last_modified': last_modified,
            
            # Metadata
            'title': metadata.get('title'),
            'artist': metadata.get('artist'),
            'album': metadata.get('album'),
            'genre': metadata.get('genre'),
            'year': metadata.get('date'),
            'track': metadata.get('track'),
            'albumartist': metadata.get('albumartist'),
            'duration': metadata.get('duration', 0.0),
            'has_artwork': metadata.get('has_artwork', False),
            
            # Analysis
            'bpm': analysis.get('bpm'),
            'beat_times': beat_times_json,
        }
        
        # Add enhanced data if provided
        if enhanced:
            data.update({
                'energy_level': enhanced.get('energy_level'),
                'danceability': enhanced.get('danceability'),
                'tempo_stability': enhanced.get('tempo_stability'),
            })
        
        # Insert or update
        columns = ', '.join(data.keys())
        placeholders = ', '.join([f':{key}' for key in data.keys()])
        
        cursor.execute(f'''
            INSERT OR REPLACE INTO tracks ({columns})
            VALUES ({placeholders})
        ''', data)
        
        self.connection.commit()
    
    def get_all_tracks(self) -> List[Dict]:
        """Get all tracks from database."""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM tracks ORDER BY artist, album, track')
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


class TrackAnalyzer:
    """Track analyzer with simplified features."""
    
    def __init__(self, db: TrackDatabase):
        self.db = db
    
    def calculate_energy_level(self, bpm: float) -> float:
        """Calculate energy level from BPM."""
        # Normalize BPM to 0-1 scale (60-200 BPM range)
        bpm_energy = (bpm - 60) / 140
        return max(0, min(1, bpm_energy))

    def estimate_danceability(self, bpm: float, beat_times: List[float]) -> float:
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
            if len(beat_intervals) > 0:
                regularity = 1 - (np.std(beat_intervals) / np.mean(beat_intervals))
                regularity = max(0, min(1, regularity))
            else:
                regularity = 0.5
        else:
            regularity = 0.5
        
        return 0.7 * bpm_score + 0.3 * regularity

    def calculate_tempo_stability(self, beat_times: List[float]) -> float:
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

    def enhance_track_features(self, bpm: float, beat_times: List[float]) -> Dict:
        """Calculate enhanced features for a track."""
        try:
            enhanced = {
                'energy_level': self.calculate_energy_level(bpm),
                'danceability': self.estimate_danceability(bpm, beat_times),
                'tempo_stability': self.calculate_tempo_stability(beat_times),
            }
        except Exception as e:
            print(f"  Warning: Error enhancing features: {e}")
            # Provide defaults
            enhanced = {
                'energy_level': 0.5,
                'danceability': 0.5,
                'tempo_stability': 0.5,
            }
        
        return enhanced

    def analyze_file(self, file_path: str, force: bool = False) -> bool:
        """Analyze a single audio file."""
        if not force and not self.db.needs_analysis(file_path):
            return False  # Already analyzed and up to date
        
        try:
            print(f"Analyzing: {Path(file_path).name}")
            
            # Read metadata
            print("  Reading metadata...")
            metadata = read_audio_metadata(file_path)
            
            # Analyze audio (BPM, beats)
            print("  Analyzing audio...")
            analysis = analyze_track(file_path)
            
            # Enhance features
            print("  Calculating features...")
            enhanced = self.enhance_track_features(
                analysis.get('bpm', 120), 
                analysis.get('beat_times', [])
            )
            
            # Save to database
            self.db.save_track(file_path, metadata, analysis, enhanced)
            
            print(f"  ✅ BPM: {analysis.get('bpm', 0):.1f}, "
                  f"Energy: {enhanced.get('energy_level', 0):.2f}, "
                  f"Dance: {enhanced.get('danceability', 0):.2f}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error analyzing {file_path}: {e}")
            return False


def iter_audio_files(base_dir: str) -> List[Path]:
    """Iterate through audio files in directory."""
    audio_files = []
    for root, _, files in os.walk(base_dir):
        for name in files:
            if any(name.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                audio_files.append(Path(root) / name)
    return audio_files


def main():
    """Main analysis function."""
    print("🎵 Streamie Track Analyzer (SQLite - Simplified)")
    print("=" * 50)
    
    if not os.path.exists(MUSIC_DIR):
        print(f"❌ Music directory not found: {MUSIC_DIR}")
        print("Set MUSIC_DIR environment variable or update the script")
        return
    
    # Initialize database
    db = TrackDatabase()
    analyzer = TrackAnalyzer(db)
    
    # Get all audio files
    print(f"Scanning {MUSIC_DIR} for audio files...")
    audio_files = iter_audio_files(MUSIC_DIR)
    total_files = len(audio_files)
    
    if total_files == 0:
        print("❌ No audio files found!")
        return
    
    print(f"Found {total_files} audio files")
    
    # Check which files need analysis
    files_to_analyze = [f for f in audio_files if db.needs_analysis(str(f))]
    
    if not files_to_analyze:
        print("✅ All files are up to date!")
        # Show stats
        all_tracks = db.get_all_tracks()
        if all_tracks:
            print(f"📈 Total tracks in database: {len(all_tracks)}")
            avg_bpm = np.mean([t['bpm'] for t in all_tracks if t['bpm']])
            print(f"🎵 Average BPM: {avg_bpm:.1f}")
        db.close()
        return
    
    print(f"Need to analyze {len(files_to_analyze)} files")
    print()
    
    # Analyze files
    start_time = time.time()
    analyzed_count = 0
    
    for i, file_path in enumerate(files_to_analyze, 1):
        print(f"[{i}/{len(files_to_analyze)}]", end=" ")
        if analyzer.analyze_file(str(file_path)):
            analyzed_count += 1
        print()
    
    # Summary
    elapsed = time.time() - start_time
    print("=" * 50)
    print(f"✅ Analysis complete!")
    print(f"📊 Processed {analyzed_count}/{len(files_to_analyze)} files")
    print(f"⏱️  Time elapsed: {elapsed:.1f} seconds")
    print(f"📁 Database: {db.db_path}")
    
    # Show some stats
    all_tracks = db.get_all_tracks()
    if all_tracks:
        print(f"📈 Total tracks in database: {len(all_tracks)}")
        avg_bpm = np.mean([t['bpm'] for t in all_tracks if t['bpm']])
        print(f"🎵 Average BPM: {avg_bpm:.1f}")
    
    db.close()


if __name__ == "__main__":
    main() 
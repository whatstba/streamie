"""
Comprehensive track analysis and enhancement script using SQLite.

This script:
- Creates a local SQLite database
- Analyzes audio files for metadata, BPM, beats, and mood
- Enhances tracks with energy level, danceability, tempo stability, and vocal presence
- Stores everything locally in SQL for fast access
- Supports incremental updates (only processes unanalyzed or changed files)
"""

import os
import sys
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our utilities
from utils.id3_reader import read_audio_metadata
from utils.librosa import analyze_track
from utils.essentia_utils import analyze_mood
from main import MUSIC_DIR

# Audio analysis libraries
import librosa
import numpy as np

# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.m4p'}

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tracks.db')


class TrackDatabase:
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
                
                -- Mood analysis (Essentia)
                mood_acoustic REAL DEFAULT 0.0,
                mood_aggressive REAL DEFAULT 0.0,
                mood_electronic REAL DEFAULT 0.0,
                mood_happy REAL DEFAULT 0.0,
                mood_party REAL DEFAULT 0.0,
                mood_relaxed REAL DEFAULT 0.0,
                mood_sad REAL DEFAULT 0.0,
                mood_label TEXT,  -- Primary mood
                
                -- Enhanced features
                energy_level REAL,
                danceability REAL,
                tempo_stability REAL,
                vocal_presence REAL,
                valence REAL,
                
                -- Processing metadata
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                enhanced_at TIMESTAMP,
                analysis_version INTEGER DEFAULT 1
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filepath ON tracks(filepath)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bpm ON tracks(bpm)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_energy ON tracks(energy_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mood_label ON tracks(mood_label)')
        
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
    
    def save_track(self, file_path: str, metadata: Dict, analysis: Dict, mood: Dict, enhanced: Dict = None):
        """Save track data to database."""
        cursor = self.connection.cursor()
        rel_path = os.path.relpath(file_path, MUSIC_DIR)
        
        # File metadata
        file_hash = self.get_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        last_modified = os.path.getmtime(file_path)
        
        # Determine primary mood
        mood_label = None
        if mood:
            mood_label = max(mood, key=mood.get) if mood else None
        
        # Prepare beat times as JSON
        import json
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
            
            # Mood
            'mood_acoustic': mood.get('mood_acoustic', 0.0),
            'mood_aggressive': mood.get('mood_aggressive', 0.0),
            'mood_electronic': mood.get('mood_electronic', 0.0),
            'mood_happy': mood.get('mood_happy', 0.0),
            'mood_party': mood.get('mood_party', 0.0),
            'mood_relaxed': mood.get('mood_relaxed', 0.0),
            'mood_sad': mood.get('mood_sad', 0.0),
            'mood_label': mood_label,
        }
        
        # Add enhanced data if provided
        if enhanced:
            data.update({
                'energy_level': enhanced.get('energy_level'),
                'danceability': enhanced.get('danceability'),
                'tempo_stability': enhanced.get('tempo_stability'),
                'vocal_presence': enhanced.get('vocal_presence'),
                'valence': enhanced.get('valence'),
                'enhanced_at': datetime.now().isoformat(),
            })
        
        # Insert or update
        columns = ', '.join(data.keys())
        placeholders = ', '.join([f':{key}' for key in data.keys()])
        
        cursor.execute(f'''
            INSERT OR REPLACE INTO tracks ({columns})
            VALUES ({placeholders})
        ''', data)
        
        self.connection.commit()
    
    def get_track_by_path(self, file_path: str) -> Optional[Dict]:
        """Get track data by file path."""
        cursor = self.connection.cursor()
        rel_path = os.path.relpath(file_path, MUSIC_DIR)
        
        cursor.execute('SELECT * FROM tracks WHERE filepath = ?', (rel_path,))
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
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
    """Comprehensive track analyzer and enhancer."""
    
    def __init__(self, db: TrackDatabase):
        self.db = db
    
    def calculate_energy_level(self, bpm: float, mood: Dict) -> float:
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

    def detect_vocal_presence(self, file_path: str) -> float:
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
            print(f"  Warning: Error detecting vocals: {e}")
            return 0.5

    def enhance_track_features(self, file_path: str, bpm: float, beat_times: List[float], mood: Dict) -> Dict:
        """Calculate enhanced features for a track."""
        enhanced = {}
        
        try:
            # Calculate energy level
            enhanced['energy_level'] = self.calculate_energy_level(bpm, mood)
            
            # Estimate danceability
            enhanced['danceability'] = self.estimate_danceability(bpm, beat_times)
            
            # Calculate tempo stability
            enhanced['tempo_stability'] = self.calculate_tempo_stability(beat_times)
            
            # Detect vocal presence
            enhanced['vocal_presence'] = self.detect_vocal_presence(file_path)
            
            # Valence (use happy mood as proxy)
            enhanced['valence'] = mood.get('mood_happy', 0.5)
            
        except Exception as e:
            print(f"  Warning: Error enhancing features: {e}")
            # Provide defaults
            enhanced = {
                'energy_level': 0.5,
                'danceability': 0.5,
                'tempo_stability': 0.5,
                'vocal_presence': 0.5,
                'valence': 0.5
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
            
            # Analyze mood
            print("  Analyzing mood...")
            try:
                mood = analyze_mood(file_path)
            except Exception as e:
                print(f"  Warning: Mood analysis failed: {e}")
                mood = {}
            
            # Enhance features
            print("  Enhancing features...")
            enhanced = self.enhance_track_features(
                file_path, 
                analysis.get('bpm', 120), 
                analysis.get('beat_times', []), 
                mood
            )
            
            # Save to database
            self.db.save_track(file_path, metadata, analysis, mood, enhanced)
            
            print(f"  ✅ BPM: {analysis.get('bpm', 0):.1f}, "
                  f"Energy: {enhanced.get('energy_level', 0):.2f}, "
                  f"Dance: {enhanced.get('danceability', 0):.2f}, "
                  f"Mood: {mood.get(max(mood, key=mood.get) if mood else 'unknown', 'unknown')}")
            
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
    print("🎵 Streamie Track Analyzer & Enhancer (SQLite)")
    print("=" * 50)
    
    if not os.path.exists(MUSIC_DIR):
        print(f"❌ Music directory not found: {MUSIC_DIR}")
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
"""
Utility script to query and manage the simplified SQLite tracks database.

Usage examples:
  python query_tracks_simple.py --stats               # Show database statistics
  python query_tracks_simple.py --search "artist"     # Search for tracks by artist
  python query_tracks_simple.py --bpm-range 120 140   # Find tracks in BPM range
  python query_tracks_simple.py --high-energy         # Find high energy tracks
  python query_tracks_simple.py --export tracks.json  # Export all tracks to JSON
"""

import os
import sys
import sqlite3
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tracks.db')


class TrackQuery:
    """Query interface for the tracks database."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            print("Run analyze_tracks_sql_simple.py first to create the database.")
            sys.exit(1)
        
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        cursor = self.connection.cursor()
        
        # Basic counts
        cursor.execute('SELECT COUNT(*) as total FROM tracks')
        total_tracks = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(DISTINCT artist) as artists FROM tracks WHERE artist IS NOT NULL')
        total_artists = cursor.fetchone()['artists']
        
        cursor.execute('SELECT COUNT(DISTINCT album) as albums FROM tracks WHERE album IS NOT NULL')
        total_albums = cursor.fetchone()['albums']
        
        # BPM stats
        cursor.execute('SELECT AVG(bpm) as avg_bpm, MIN(bpm) as min_bpm, MAX(bpm) as max_bpm FROM tracks WHERE bpm IS NOT NULL')
        bpm_stats = cursor.fetchone()
        
        # Energy stats
        cursor.execute('SELECT AVG(energy_level) as avg_energy, MIN(energy_level) as min_energy, MAX(energy_level) as max_energy FROM tracks WHERE energy_level IS NOT NULL')
        energy_stats = cursor.fetchone()
        
        # Duration stats
        cursor.execute('SELECT SUM(duration) as total_duration FROM tracks WHERE duration IS NOT NULL')
        total_duration = cursor.fetchone()['total_duration'] or 0
        
        # Top genres
        cursor.execute('''
            SELECT genre, COUNT(*) as count 
            FROM tracks 
            WHERE genre IS NOT NULL AND genre != ''
            GROUP BY genre 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_genres = cursor.fetchall()
        
        return {
            'total_tracks': total_tracks,
            'total_artists': total_artists,
            'total_albums': total_albums,
            'total_duration_hours': total_duration / 3600,
            'bpm': {
                'avg': bpm_stats['avg_bpm'] or 0,
                'min': bpm_stats['min_bpm'] or 0,
                'max': bpm_stats['max_bpm'] or 0
            },
            'energy': {
                'avg': energy_stats['avg_energy'] or 0,
                'min': energy_stats['min_energy'] or 0,
                'max': energy_stats['max_energy'] or 0
            },
            'top_genres': [{'genre': row['genre'], 'count': row['count']} for row in top_genres]
        }
    
    def search_tracks(self, query: str) -> List[Dict]:
        """Search tracks by artist, title, album, or genre."""
        cursor = self.connection.cursor()
        search_query = f'%{query}%'
        
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE artist LIKE ? OR title LIKE ? OR album LIKE ? OR genre LIKE ?
            ORDER BY artist, album, track
        ''', (search_query, search_query, search_query, search_query))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_tracks_by_bpm_range(self, min_bpm: float, max_bpm: float) -> List[Dict]:
        """Get tracks within a BPM range."""
        cursor = self.connection.cursor()
        
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE bpm BETWEEN ? AND ?
            ORDER BY bpm
        ''', (min_bpm, max_bpm))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_high_energy_tracks(self, min_energy: float = 0.7) -> List[Dict]:
        """Get high energy tracks."""
        cursor = self.connection.cursor()
        
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE energy_level >= ?
            ORDER BY energy_level DESC
        ''', (min_energy,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_danceable_tracks(self, min_danceability: float = 0.7) -> List[Dict]:
        """Get highly danceable tracks."""
        cursor = self.connection.cursor()
        
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE danceability >= ?
            ORDER BY danceability DESC
        ''', (min_danceability,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_tracks_by_genre(self, genre: str) -> List[Dict]:
        """Get tracks by genre."""
        cursor = self.connection.cursor()
        
        cursor.execute('''
            SELECT * FROM tracks 
            WHERE genre = ?
            ORDER BY artist, album, track
        ''', (genre,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_similar_tracks(self, reference_track_id: int, limit: int = 10) -> List[Dict]:
        """Find tracks similar to a reference track based on audio features."""
        cursor = self.connection.cursor()
        
        # Get reference track features
        cursor.execute('SELECT * FROM tracks WHERE id = ?', (reference_track_id,))
        ref_track = cursor.fetchone()
        
        if not ref_track:
            return []
        
        # Find similar tracks using weighted distance
        cursor.execute('''
            SELECT *,
                   ABS(bpm - ?) * 0.4 +
                   ABS(energy_level - ?) * 0.3 +
                   ABS(danceability - ?) * 0.3 as similarity_score
            FROM tracks 
            WHERE id != ? AND bpm IS NOT NULL AND energy_level IS NOT NULL
            ORDER BY similarity_score
            LIMIT ?
        ''', (ref_track['bpm'], ref_track['energy_level'], ref_track['danceability'], 
              reference_track_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def export_to_json(self, filename: str):
        """Export all tracks to JSON file."""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM tracks ORDER BY artist, album, track')
        tracks = [dict(row) for row in cursor.fetchall()]
        
        with open(filename, 'w') as f:
            json.dump(tracks, f, indent=2, default=str)
        
        print(f"✅ Exported {len(tracks)} tracks to {filename}")
    
    def close(self):
        """Close database connection."""
        self.connection.close()


def print_track_summary(track: Dict):
    """Print a summary of a track."""
    print(f"  🎵 {track['title'] or 'Unknown'} - {track['artist'] or 'Unknown Artist'}")
    print(f"     Album: {track['album'] or 'Unknown'}")
    print(f"     BPM: {track['bpm']:.1f}, Energy: {track['energy_level']:.2f}, "
          f"Dance: {track['danceability']:.2f}, Genre: {track['genre'] or 'Unknown'}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Query tracks database')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--search', metavar='QUERY', help='Search tracks by artist/title/album/genre')
    parser.add_argument('--bpm-range', nargs=2, metavar=('MIN', 'MAX'), type=float, 
                       help='Find tracks in BPM range')
    parser.add_argument('--high-energy', action='store_true', help='Find high energy tracks (>= 0.7)')
    parser.add_argument('--danceable', action='store_true', help='Find highly danceable tracks (>= 0.7)')
    parser.add_argument('--genre', metavar='GENRE', help='Find tracks by genre')
    parser.add_argument('--similar', metavar='TRACK_ID', type=int, help='Find tracks similar to given track ID')
    parser.add_argument('--export', metavar='FILENAME', help='Export all tracks to JSON file')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of results (default: 20)')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    db = TrackQuery()
    
    try:
        if args.stats:
            stats = db.get_stats()
            print("📊 Database Statistics")
            print("=" * 30)
            print(f"Total tracks: {stats['total_tracks']:,}")
            print(f"Total artists: {stats['total_artists']:,}")
            print(f"Total albums: {stats['total_albums']:,}")
            print(f"Total duration: {stats['total_duration_hours']:.1f} hours")
            print()
            print(f"BPM - Avg: {stats['bpm']['avg']:.1f}, "
                  f"Range: {stats['bpm']['min']:.1f}-{stats['bpm']['max']:.1f}")
            print(f"Energy - Avg: {stats['energy']['avg']:.2f}, "
                  f"Range: {stats['energy']['min']:.2f}-{stats['energy']['max']:.2f}")
            print()
            print("Top genres:")
            for genre in stats['top_genres']:
                print(f"  {genre['genre']}: {genre['count']} tracks")
        
        elif args.search:
            tracks = db.search_tracks(args.search)
            print(f"🔍 Search results for '{args.search}' ({len(tracks)} tracks):")
            print()
            for track in tracks[:args.limit]:
                print_track_summary(track)
        
        elif args.bpm_range:
            min_bpm, max_bpm = args.bpm_range
            tracks = db.get_tracks_by_bpm_range(min_bpm, max_bpm)
            print(f"🎵 Tracks with BPM {min_bpm}-{max_bpm} ({len(tracks)} tracks):")
            print()
            for track in tracks[:args.limit]:
                print_track_summary(track)
        
        elif args.high_energy:
            tracks = db.get_high_energy_tracks()
            print(f"⚡ High energy tracks ({len(tracks)} tracks):")
            print()
            for track in tracks[:args.limit]:
                print_track_summary(track)
        
        elif args.danceable:
            tracks = db.get_danceable_tracks()
            print(f"💃 Highly danceable tracks ({len(tracks)} tracks):")
            print()
            for track in tracks[:args.limit]:
                print_track_summary(track)
        
        elif args.genre:
            tracks = db.get_tracks_by_genre(args.genre)
            print(f"🎼 Tracks with genre '{args.genre}' ({len(tracks)} tracks):")
            print()
            for track in tracks[:args.limit]:
                print_track_summary(track)
        
        elif args.similar:
            tracks = db.get_similar_tracks(args.similar, args.limit)
            if tracks:
                print(f"🎯 Tracks similar to track ID {args.similar} ({len(tracks)} tracks):")
                print()
                for track in tracks:
                    print_track_summary(track)
                    print(f"     Similarity score: {track['similarity_score']:.3f}")
                    print()
            else:
                print(f"❌ Track ID {args.similar} not found")
        
        elif args.export:
            db.export_to_json(args.export)
    
    finally:
        db.close()


if __name__ == "__main__":
    main() 
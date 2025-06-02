from dotenv import load_dotenv
load_dotenv() 
from utils.mood_interpreter import interpret_mood
from utils.spotify import search_tracks, get_audio_features
from utils.youtube import search_youtube
from utils.soundcloud import search_soundcloud
from utils.transitions import suggest_transitions
from utils.librosa import run_beat_track
from utils.id3_reader import read_audio_metadata, extract_artwork
# from utils.serato_reader import serato_reader  # Temporarily disabled
from utils.db import get_db
from agents.dj_agent import DJAgent  # Import the DJ agent
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import os
from typing import List, Optional, Dict, Any
import librosa
import mimetypes
import re
import random
import asyncio
import sqlite3
from mutagen import File
from datetime import datetime
import json

# Import the AI router - temporarily disabled
# from routers.ai_router import router as ai_router

# Create FastAPI app instance
app = FastAPI(title="AI DJ Backend")

# Enable CORS for our Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the AI router - temporarily disabled
# app.include_router(ai_router)

# Directory where music files are stored
MUSIC_DIR = os.path.expanduser("~/Downloads")  # We'll use Downloads folder for testing

class SeratoHotCue(BaseModel):
    """Serato hot cue point model"""
    name: str
    time: float
    color: str
    type: str = 'cue'  # 'cue', 'loop', 'phrase'
    index: int = 0

class TrackInfo(BaseModel):
    filename: str
    filepath: str
    duration: float
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    has_artwork: bool = False
    bpm: Optional[float] = None  # Add BPM to track model
    # mood field removed - it's stored as a dict in SQLite

class TrackDBInfo(TrackInfo):
    """Track info stored in the database including beat timestamps."""
    beat_times: List[float] = []

class TrackAnalysisResponse(BaseModel):
    """Enhanced track analysis response with Serato data"""
    bpm: float
    beat_times: List[float] = []
    mood: Optional[str] = None
    success: bool
    confidence: float = 0.85
    analysis_time: str = "instant"
    suggested_transitions: Dict[str, bool] = {}
    serato_data: Dict[str, Any] = {}
    hot_cues: List[SeratoHotCue] = []

class VibePlaylistRequest(BaseModel):
    vibe_description: str
    playlist_length: int = 10

class VibePlaylistResponse(BaseModel):
    playlist: List[TrackInfo]
    vibe_analysis: Dict[str, Any]
    total_tracks_considered: int

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {"status": "ok", "message": "AI DJ Backend is running", "ai_enabled": False}


@app.get("/db/tracks", response_model=List[TrackDBInfo])
async def list_tracks_from_db():
    """Return track info stored in MongoDB."""
    db = get_db()
    docs = list(db.tracks.find({}))
    tracks = []
    for d in docs:
        d.pop("_id", None)
        tracks.append(TrackDBInfo(**d))
    return tracks

@app.get("/tracks", response_model=List[TrackInfo])
async def list_tracks(include_bpm: bool = False):
    """List all audio files in the music directory with optional BPM analysis"""
    tracks = []
    
    # Supported audio file extensions
    audio_extensions = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac', '.m4p'}
    
    print(f"🔍 Scanning for music files in: {MUSIC_DIR}")
    print(f"   Including subdirectories recursively...")
    
    # Recursively walk through all directories and subdirectories
    for root, dirs, files in os.walk(MUSIC_DIR):
        # Skip hidden directories (like .DS_Store, .git, etc.)
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        print(f"   📁 Scanning directory: {root}")
        
        for file_name in files:
            # Skip hidden files
            if file_name.startswith('.'):
                continue
                
            full_path = os.path.join(root, file_name)
            
            # Check if it's an audio file
            if not any(file_name.lower().endswith(ext) for ext in audio_extensions):
                continue
            
            try:
                # Get basic metadata
                metadata = read_audio_metadata(full_path)
                
                # Create relative path from MUSIC_DIR for the API
                relative_path = os.path.relpath(full_path, MUSIC_DIR)
                
                track_info = TrackInfo(
                    filename=file_name,
                    filepath=relative_path,  # Use relative path for API consistency
                    duration=metadata.get('duration', 0.0),
                    title=metadata.get('title'),
                    artist=metadata.get('artist'),
                    album=metadata.get('album'),
                    genre=metadata.get('genre'),
                    year=metadata.get('date'),
                    has_artwork=metadata.get('has_artwork', False)
                )
                
                # Optionally include BPM analysis (slower)
                if include_bpm:
                    try:
                        bpm = run_beat_track(full_path)
                        track_info.bpm = bpm
                        print(f"      🎵 {file_name}: {bpm:.2f} BPM")
                    except Exception as e:
                        print(f"      ❌ BPM analysis failed for {file_name}: {e}")
                        track_info.bpm = None
                else:
                    print(f"      🎵 Found: {file_name}")
                
                tracks.append(track_info)
                
            except Exception as e:
                print(f"      ❌ Error processing {file_name}: {e}")
                continue
    
    print(f"✅ Found {len(tracks)} total music files")
    
    # Sort by artist, then album, then title
    tracks.sort(key=lambda x: (
        x.artist or x.filename,
        x.album or "",
        x.title or x.filename
    ))
    
    return tracks

@app.post("/tracks/batch-analyze")
async def batch_analyze_tracks(filepaths: List[str]):
    """Analyze BPM for multiple tracks in batch"""
    results = []
    
    for filepath in filepaths:
        file_path = os.path.join(MUSIC_DIR, filepath)
        if not os.path.exists(file_path):
            results.append({
                "filepath": filepath,
                "bpm": None,
                "success": False,
                "error": "File not found"
            })
            continue
        
        try:
            bpm = run_beat_track(file_path)
            results.append({
                "filepath": filepath,
                "bpm": bpm,
                "success": True
            })
        except Exception as e:
            results.append({
                "filepath": filepath,
                "bpm": None,
                "success": False,
                "error": str(e)
            })
    
    return results

@app.get("/track/{filepath:path}/analysis", response_model=TrackAnalysisResponse)
async def analyze_track_enhanced(filepath: str):
    """Get comprehensive track analysis including BPM - Serato temporarily disabled"""
    file_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        print(f"🎧 ANALYZING TRACK: {os.path.basename(filepath)}")

        # Look up precomputed analysis in the SQLite database
        db_sqlite = get_sqlite_db()
        cursor = db_sqlite.adapter.connection.cursor()
        cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (filepath,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        cursor.close()
        
        doc = None
        if row:
            doc = dict(zip(columns, row))
            # Parse beat_times if it's a JSON string
            if doc.get("beat_times") and isinstance(doc["beat_times"], str):
                try:
                    doc["beat_times"] = json.loads(doc["beat_times"])
                except json.JSONDecodeError:
                    doc["beat_times"] = [] # Default to empty list on error
            elif not doc.get("beat_times"):
                 doc["beat_times"] = [] # Ensure beat_times exists

        if not doc:
            # If not in database, do live analysis
            try:
                bpm = run_beat_track(file_path)
                beat_times = [] # Live analysis doesn't provide beat_times here
                mood = None # Live analysis doesn't provide mood here
                energy_level = None # Live analysis doesn't provide energy_level
                print(f"🎵 Live BPM Analysis: {bpm:.2f} BPM")
            except Exception as e:
                print(f"❌ Live analysis failed: {e}")
                raise HTTPException(status_code=500, detail="Live analysis failed")
        else:
            bpm = doc.get("bpm")
            beat_times = doc.get("beat_times", [])
            mood = doc.get("mood") # mood might not be in SQLite schema yet
            energy_level = doc.get("energy_level") # energy_level from SQLite
            print(f"🎵 Database BPM: {bpm:.2f} BPM ({len(beat_times)} beats), Energy: {energy_level}")
        
        # Serato data temporarily disabled
        serato_info = {'hot_cues': [], 'serato_available': False}
        hot_cues = []
        
        # Suggested transitions based on BPM only (no Serato)
        suggested_transitions = {
            "filter_sweep": bpm > 120,
            "echo_effect": 100 <= bpm <= 140,
            "scratch_compatible": bpm >= 80,
            "has_serato_cues": False,  # Disabled
            "loop_ready": False  # Disabled
        }
        
        response = TrackAnalysisResponse(
            bpm=bpm,
            beat_times=beat_times, # Ensure this is a list
            mood=mood,
            success=True,
            confidence=0.85,  # Standard confidence without Serato
            analysis_time="enhanced",
            suggested_transitions=suggested_transitions,
            serato_data=serato_info,
            hot_cues=hot_cues
        )
        
        print(f"✅ Analysis complete: {bpm:.2f} BPM, mood={mood}")
        return response
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{filepath:path}/serato")
async def get_serato_data(filepath: str):
    """Get only Serato data for a track - temporarily disabled"""
    return {"error": "Serato functionality temporarily disabled", "serato_available": False}

@app.get("/track/{filepath:path}/waveform")
async def get_waveform(filepath: str):
    """Get waveform data for visualization"""
    file_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        y, sr = librosa.load(file_path)
        # Reduce waveform resolution for frontend visualization
        hop_length = 1024
        waveform = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        
        return {
            "waveform": waveform.tolist(),
            "sample_rate": sr,
            "hop_length": hop_length
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{filepath:path}/artwork")
async def get_artwork(filepath: str):
    """Get album artwork for a track"""
    file_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        artwork_data = extract_artwork(file_path)
        if artwork_data:
            image_data, mime_type = artwork_data
            return Response(content=image_data, media_type=mime_type)
        else:
            raise HTTPException(status_code=404, detail="No artwork found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{filepath:path}/stream")
async def stream_audio(filepath: str, request: Request):
    """Stream audio file with support for range requests (seeking)"""
    file_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        file_size = os.path.getsize(file_path)
        
        # Get the range header if present
        range_header = request.headers.get('Range')
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'audio/mpeg'  # Default to MP3
        
        if range_header:
            # Parse range header (e.g., "bytes=0-1023")
            byte_start = 0
            byte_end = file_size - 1
            
            if range_header.startswith('bytes='):
                range_spec = range_header[6:]
                if '-' in range_spec:
                    start_str, end_str = range_spec.split('-', 1)
                    if start_str:
                        byte_start = int(start_str)
                    if end_str:
                        byte_end = int(end_str)
            
            # Ensure valid range
            byte_start = max(0, byte_start)
            byte_end = min(file_size - 1, byte_end)
            content_length = byte_end - byte_start + 1
            
            def iterfile(file_path: str, start: int, chunk_size: int = 8192):
                with open(file_path, 'rb') as file:
                    file.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        to_read = min(chunk_size, remaining)
                        data = file.read(to_read)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
            
            return StreamingResponse(
                iterfile(file_path, byte_start),
                status_code=206,  # Partial Content
                headers={
                    'Content-Type': content_type,
                    'Content-Length': str(content_length),
                    'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'no-cache',
                }
            )
        else:
            # No range header, serve entire file
            def iterfile(file_path: str, chunk_size: int = 8192):
                with open(file_path, 'rb') as file:
                    while True:
                        data = file.read(chunk_size)
                        if not data:
                            break
                        yield data
            
            return StreamingResponse(
                iterfile(file_path),
                headers={
                    'Content-Type': content_type,
                    'Content-Length': str(file_size),
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'no-cache',
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/generate-vibe-playlist", response_model=VibePlaylistResponse)
async def generate_vibe_playlist(request: VibePlaylistRequest):
    """Generate a playlist based on vibe description using DJ agent"""
    try:
        print("\n" + "="*60)
        print(f"🎨 VIBE PLAYLIST REQUEST")
        print(f"   Vibe: '{request.vibe_description}'")
        print(f"   Length: {request.playlist_length} tracks")
        print("="*60)
        
        # Initialize DJ agent
        dj_agent = DJAgent()
        
        # Generate playlist using the new agentic approach
        result = await dj_agent.generate_playlist(
            vibe_description=request.vibe_description,
            length=request.playlist_length,
            energy_pattern="wave",  # Could be determined from vibe analysis
            thread_id=f"vibe-{datetime.now().timestamp()}"  # Unique thread ID
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate playlist"))
        
        # Parse the agent's response to extract playlist
        response_text = result["response"]
        
        print(f"\n🤖 Agent Response:\n{response_text}")
        
        # Extract the finalized playlist from the agent
        finalized_playlist = result.get("finalized_playlist", [])
        playlist_tracks = []
        
        if finalized_playlist:
            print(f"\n✅ Agent provided structured playlist with {len(finalized_playlist)} tracks")
            
            # Load our SQLite database to get full track info
            db_path = os.path.join(os.path.dirname(__file__), 'tracks.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get full track info for each filepath in the playlist
            for item in finalized_playlist:
                filepath = item.get('filepath')
                if not filepath:
                    continue
                    
                cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (filepath,))
                columns = [description[0] for description in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    track = dict(zip(columns, row))
                    track_info = TrackInfo(
                        filename=track.get('filename', ''),
                        filepath=track.get('filepath', ''),
                        duration=track.get('duration', 0.0),
                        title=track.get('title'),
                        artist=track.get('artist'),
                        album=track.get('album'),
                        genre=track.get('genre'),
                        year=track.get('year'),
                        has_artwork=track.get('has_artwork', False),
                        bpm=track.get('bpm')
                    )
                    playlist_tracks.append(track_info)
                    print(f"   {item['order']}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} ({item.get('mixing_note', '')})")
            
            cursor.close()
            conn.close()
            
        else:
            # Fallback: Try to extract from state's candidate_tracks (old method)
            print("\n⚠️ No finalized playlist from agent, checking for candidate tracks...")
            state = result.get("state", {})
            
            if state.get("candidate_tracks"):
                # Use candidate tracks from state
                tracks_data = state["candidate_tracks"][:request.playlist_length]
                for track in tracks_data:
                    track_info = TrackInfo(
                        filename=track.get('filename', ''),
                        filepath=track.get('filepath', ''),
                        duration=track.get('duration', 0.0),
                        title=track.get('title'),
                        artist=track.get('artist'),
                        album=track.get('album'),
                        genre=track.get('genre'),
                        year=track.get('year'),
                        has_artwork=track.get('has_artwork', False),
                        bpm=track.get('bpm')
                    )
                    playlist_tracks.append(track_info)
        
        # If still no tracks, do the original fallback query
        if not playlist_tracks:
            print("\n⚠️ No tracks found in agent response, using fallback query")
            
            # Analyze the vibe description
            vibe_analysis = analyze_vibe_description(request.vibe_description.lower())
            
            db_path = os.path.join(os.path.dirname(__file__), 'tracks.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Build query based on vibe analysis
            query = "SELECT * FROM tracks WHERE bpm IS NOT NULL"
            params = []
            
            # Add energy level filtering
            if vibe_analysis['energy_level'] > 0.6:
                query += " AND (bpm > 120 OR energy_level > 0.6)"
            elif vibe_analysis['energy_level'] < 0.4:
                query += " AND (bpm < 110 OR energy_level < 0.4)"
            
            # Add genre filtering if specific genres detected
            if vibe_analysis['genres']:
                genre_conditions = []
                for genre in vibe_analysis['genres']:
                    genre_conditions.append("genre LIKE ?")
                    params.append(f"%{genre}%")
                if genre_conditions:
                    query += f" AND ({' OR '.join(genre_conditions)})"
            
            query += " ORDER BY RANDOM() LIMIT ?"
            params.append(request.playlist_length)
            
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            
            for row in cursor.fetchall():
                track = dict(zip(columns, row))
                track_info = TrackInfo(
                    filename=track.get('filename', ''),
                    filepath=track.get('filepath', ''),
                    duration=track.get('duration', 0.0),
                    title=track.get('title'),
                    artist=track.get('artist'),
                    album=track.get('album'),
                    genre=track.get('genre'),
                    year=track.get('year'),
                    has_artwork=track.get('has_artwork', False),
                    bpm=track.get('bpm')
                )
                playlist_tracks.append(track_info)
            
            cursor.close()
            conn.close()
        
        # Create vibe analysis response
        vibe_analysis_response = {
            "agent_response": response_text,
            "vibe_description": request.vibe_description,
            "energy_pattern": "wave",
            "energy_level": analyze_vibe_description(request.vibe_description.lower()).get('energy_level', 0.5),
            "success": True
        }
        
        print(f"\n✅ Playlist generated: {len(playlist_tracks)} tracks")
        print("="*60 + "\n")
        
        return VibePlaylistResponse(
            playlist=playlist_tracks,
            vibe_analysis=vibe_analysis_response,
            total_tracks_considered=1000  # Approximate
        )
        
    except Exception as e:
        print(f"❌ Error in generate_vibe_playlist: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def determine_energy_pattern(vibe_analysis: Dict) -> str:
    """Determine energy pattern from vibe analysis"""
    activities = vibe_analysis.get("activities", [])
    energy_level = vibe_analysis.get("energy_level", 0.5)
    
    if "workout" in activities or "party" in activities:
        return "peak_time" if energy_level > 0.7 else "build_up"
    elif "study" in activities or "relaxation" in activities:
        return "cool_down"
    elif energy_level > 0.7:
        return "peak_time"
    elif energy_level < 0.3:
        return "cool_down"
    else:
        return "wave"

def analyze_vibe_description(vibe_text: str) -> Dict[str, Any]:
    """Analyze vibe description and extract musical preferences"""
    analysis = {
        'energy_level': 0.5,  # 0-1 scale
        'bpm_preference': 'any',  # 'slow', 'medium', 'fast', 'any'
        'genres': [],
        'moods': [],
        'activities': [],
        'time_of_day': None,
        'keywords': vibe_text.split()
    }
    
    # Energy level keywords
    high_energy_words = ['energetic', 'upbeat', 'pump', 'hype', 'intense', 'party', 'dance', 'workout', 'gym', 'running', 'fast', 'loud', 'banging']
    low_energy_words = ['chill', 'relaxing', 'calm', 'mellow', 'soft', 'quiet', 'ambient', 'downtempo', 'slow', 'peaceful', 'study', 'sleep']
    medium_energy_words = ['groove', 'smooth', 'cool', 'moderate', 'steady', 'walking']
    
    # Calculate energy level
    high_count = sum(1 for word in high_energy_words if word in vibe_text)
    low_count = sum(1 for word in low_energy_words if word in vibe_text)
    medium_count = sum(1 for word in medium_energy_words if word in vibe_text)
    
    if high_count > low_count:
        analysis['energy_level'] = 0.7 + (high_count * 0.1)
        analysis['bpm_preference'] = 'fast'
    elif low_count > high_count:
        analysis['energy_level'] = 0.3 - (low_count * 0.1)
        analysis['bpm_preference'] = 'slow'
    elif medium_count > 0:
        analysis['energy_level'] = 0.5
        analysis['bpm_preference'] = 'medium'
    
    # Clamp energy level
    analysis['energy_level'] = max(0.0, min(1.0, analysis['energy_level']))
    
    # Genre detection
    genre_keywords = {
        'hip-hop': ['hip-hop', 'hiphop', 'rap', 'hip hop'],
        'r&b': ['r&b', 'rnb', 'soul', 'rhythm and blues'],
        'jazz': ['jazz', 'bebop', 'smooth jazz'],
        'electronic': ['electronic', 'edm', 'techno', 'house', 'dubstep', 'electro'],
        'rock': ['rock', 'alternative', 'indie', 'punk'],
        'pop': ['pop', 'mainstream', 'top 40'],
        'reggae': ['reggae', 'dancehall', 'ska'],
        'funk': ['funk', 'funky', 'groove'],
        'latin': ['latin', 'salsa', 'reggaeton', 'spanish'],
        'country': ['country', 'folk', 'acoustic']
    }
    
    for genre, keywords in genre_keywords.items():
        if any(keyword in vibe_text for keyword in keywords):
            analysis['genres'].append(genre)
    
    # Activity detection
    activity_keywords = {
        'workout': ['workout', 'gym', 'exercise', 'running', 'jogging', 'training', 'working out'],
        'party': ['party', 'club', 'dancing', 'celebration'],
        'study': ['study', 'focus', 'concentration', 'reading'],
        'relaxation': ['relax', 'chill', 'unwind', 'stress relief'],
        'driving': ['driving', 'road trip', 'car', 'cruise'],
        'romance': ['romantic', 'date', 'love', 'intimate']
    }
    
    for activity, keywords in activity_keywords.items():
        if any(keyword in vibe_text for keyword in keywords):
            analysis['activities'].append(activity)
    
    # Time of day detection
    if any(word in vibe_text for word in ['morning', 'breakfast', 'dawn']):
        analysis['time_of_day'] = 'morning'
    elif any(word in vibe_text for word in ['afternoon', 'lunch', 'midday']):
        analysis['time_of_day'] = 'afternoon'
    elif any(word in vibe_text for word in ['evening', 'dinner', 'sunset']):
        analysis['time_of_day'] = 'evening'
    elif any(word in vibe_text for word in ['night', 'late night', 'midnight', 'bedtime']):
        analysis['time_of_day'] = 'night'
    
    return analysis

def calculate_vibe_score(track_doc: Dict, vibe_analysis: Dict) -> float:
    """Calculate how well a track matches the desired vibe"""
    score = 0.0
    
    # BPM matching
    bpm = track_doc.get('bpm')
    if bpm:
        bpm_score = 0.0
        if vibe_analysis['bpm_preference'] == 'slow' and bpm < 100:
            bpm_score = 1.0 - abs(80 - bpm) / 40  # Optimal around 80 BPM
        elif vibe_analysis['bpm_preference'] == 'medium' and 90 <= bpm <= 130:
            bpm_score = 1.0 - abs(110 - bpm) / 30  # Optimal around 110 BPM
        elif vibe_analysis['bpm_preference'] == 'fast' and bpm > 120:
            bpm_score = 1.0 - abs(140 - bpm) / 50  # Optimal around 140 BPM
        else:
            bpm_score = 0.5  # Neutral for 'any' or no clear preference
        
        score += max(0, bpm_score) * 0.3  # BPM contributes 30% to score
    
    # Energy level matching (using SQLite's calculated energy_level)
    energy_level = track_doc.get('energy_level')
    if energy_level is not None:
        energy_diff = abs(energy_level - vibe_analysis['energy_level'])
        energy_score = 1.0 - energy_diff
        score += energy_score * 0.3  # Energy contributes 30% to score
    
    # Genre matching
    track_genre = (track_doc.get('genre') or '').lower()
    if vibe_analysis['genres'] and track_genre:
        genre_match = any(genre in track_genre for genre in vibe_analysis['genres'])
        if genre_match:
            score += 0.4  # Genre match contributes 40% to score
        else:
            # Partial match for similar genres
            similar_matches = 0
            if 'hip-hop' in vibe_analysis['genres'] and any(word in track_genre for word in ['rap', 'hip hop']):
                similar_matches += 1
            if 'r&b' in vibe_analysis['genres'] and any(word in track_genre for word in ['soul', 'rnb']):
                similar_matches += 1
            if 'electronic' in vibe_analysis['genres'] and any(word in track_genre for word in ['dance', 'house', 'techno']):
                similar_matches += 1
            
            if similar_matches > 0:
                score += 0.2  # Partial genre match
    elif not vibe_analysis['genres']:
        score += 0.2  # No genre preference, give neutral score
    
    # Activity-based scoring
    if vibe_analysis['activities']:
        track_title = (track_doc.get('title', '') or '').lower()
        track_artist = (track_doc.get('artist', '') or '').lower()
        
        for activity in vibe_analysis['activities']:
            activity_boost = 0
            if activity == 'workout' and bpm and bpm > 120:
                activity_boost = 0.1
            elif activity == 'study' and bpm and bpm < 100:
                activity_boost = 0.1
            elif activity == 'party' and bpm and bpm > 110:
                activity_boost = 0.1
            elif activity == 'relaxation' and bpm and bpm < 90:
                activity_boost = 0.1
            
            score += activity_boost
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))

def run_mix_analysis():
    """Original main function logic for mix analysis"""
    beat_track = run_beat_track()
    print(beat_track)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) 
from dotenv import load_dotenv
load_dotenv() 
from utils.mood_interpreter import interpret_mood
from utils.spotify import search_tracks, get_audio_features
from utils.youtube import search_youtube
from utils.soundcloud import search_soundcloud
from utils.transitions import suggest_transitions
from utils.librosa import run_beat_track
from utils.id3_reader import read_audio_metadata, extract_artwork
from utils.serato_reader import serato_reader
from utils.db import get_db
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import os
from typing import List, Optional, Dict, Any
import librosa
import mimetypes

# Create FastAPI app instance
app = FastAPI(title="AI DJ Backend")

# Enable CORS for our Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    mood: Optional[str] = None  # Mood label from Essentia

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

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {"status": "ok", "message": "AI DJ Backend is running"}


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
    """Get comprehensive track analysis including BPM and Serato hot cues"""
    file_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        print(f"🎧 ANALYZING TRACK: {os.path.basename(filepath)}")

        # Look up precomputed analysis in the database
        db = get_db()
        doc = db.tracks.find_one({"filepath": filepath})
        if not doc:
            raise HTTPException(status_code=404, detail="Track analysis not found")

        bpm = doc.get("bpm")
        beat_times = doc.get("beat_times", [])
        mood = doc.get("mood")

        print(f"🎵 BPM Analysis: {bpm:.2f} BPM ({len(beat_times)} beats)")
        
        # Get Serato data including hot cues
        try:
            serato_info = serato_reader.get_serato_info(file_path)
            print(f"🎛️ Serato Data: Found {len(serato_info.get('hot_cues', []))} hot cues")
        except Exception as serato_error:
            print(f"⚠️ Serato analysis failed: {serato_error}")
            serato_info = {'hot_cues': [], 'serato_available': False}
        
        # Convert Serato hot cues to response format
        hot_cues = []
        for cue_data in serato_info.get('hot_cues', []):
            try:
                hot_cue = SeratoHotCue(
                    name=cue_data.get('name', 'Unknown Cue'),
                    time=cue_data.get('time', 0.0),
                    color=cue_data.get('color', '#ff0000'),
                    type=cue_data.get('type', 'cue'),
                    index=cue_data.get('index', len(hot_cues))
                )
                hot_cues.append(hot_cue)
                print(f"   📍 Hot Cue: {hot_cue.name} at {hot_cue.time:.2f}s ({hot_cue.color})")
            except Exception as cue_error:
                print(f"   ❌ Error processing cue: {cue_error}")
                continue
        
        # Suggested transitions based on BPM and Serato data
        suggested_transitions = {
            "filter_sweep": bpm > 120,
            "echo_effect": 100 <= bpm <= 140,
            "scratch_compatible": bpm >= 80,
            "has_serato_cues": len(hot_cues) > 0,
            "loop_ready": any(cue.type == 'loop' for cue in hot_cues)
        }
        
        response = TrackAnalysisResponse(
            bpm=bpm,
            beat_times=beat_times,
            mood=mood,
            success=True,
            confidence=0.90 if len(hot_cues) > 0 else 0.85,  # Higher confidence if Serato data exists
            analysis_time="enhanced",
            suggested_transitions=suggested_transitions,
            serato_data=serato_info,
            hot_cues=hot_cues
        )
        
        print(
            f"✅ Analysis complete: {bpm:.2f} BPM, mood={mood}, {len(hot_cues)} cues, Serato: {serato_info.get('serato_available', False)}"
        )
        return response
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{filepath:path}/serato")
async def get_serato_data(filepath: str):
    """Get only Serato data for a track (hot cues, loops, etc.)"""
    file_path = os.path.join(MUSIC_DIR, filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        serato_info = serato_reader.get_serato_info(file_path)
        return serato_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

def run_mix_analysis():
    """Original main function logic for mix analysis"""
    beat_track = run_beat_track()
    print(beat_track)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) 
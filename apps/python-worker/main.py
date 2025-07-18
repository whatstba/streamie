from dotenv import load_dotenv
load_dotenv()

# Set MUSIC_DIR environment variable before importing DJAgent
import os
MUSIC_DIR = os.path.expanduser("~/Downloads")  # We'll use Downloads folder for testing
os.environ['MUSIC_DIR'] = MUSIC_DIR

from utils.librosa import run_beat_track
from utils.id3_reader import read_audio_metadata, extract_artwork
from utils.db import get_db
from agents.dj_agent import DJAgent  # Import the DJ agent
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from utils.sqlite_db import get_sqlite_db

from pydantic import BaseModel
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
            # Track not found in database - no live analysis fallback
            print(f"❌ Track not found in database: {filepath}")
            raise HTTPException(
                status_code=404, 
                detail="Track not found in database. Please run track analysis first to populate BPM data."
            )
        
        # Get BPM and other data only from database
        bpm = doc.get("bpm")
        if bpm is None or bpm <= 0:
            print(f"❌ No valid BPM data available for track: {filepath} (BPM: {bpm})")
            raise HTTPException(
                status_code=422, 
                detail="No valid BPM data available for this track in database."
            )
            
        beat_times = doc.get("beat_times", [])
        mood = doc.get("mood") # mood might not be in SQLite schema yet
        energy_level = doc.get("energy_level") # energy_level from SQLite
        print(f"🎵 Database BPM: {bpm:.2f} BPM ({len(beat_times)} beats), Energy: {energy_level}")
        
        # Enable Serato hot cue extraction
        try:
            from utils.serato_reader import serato_reader
            serato_info = serato_reader.get_serato_info(file_path)
            hot_cues = [
                SeratoHotCue(
                    name=cue['name'],
                    time=cue['time'],
                    color=cue['color'],
                    type=cue['type'],
                    index=cue['index']
                )
                for cue in serato_info.get('hot_cues', [])
            ]
            print(f"🎛️ Extracted {len(hot_cues)} hot cues from Serato data")
        except Exception as e:
            print(f"❌ Error extracting Serato hot cues: {e}")
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
            energy_pattern="wave", 
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
        
        # Create vibe analysis response
        vibe_analysis_response = {
            "agent_response": response_text,
            "vibe_description": request.vibe_description,
            "energy_pattern": "wave",
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

@app.get("/ai/generate-vibe-playlist-stream")
async def generate_vibe_playlist_stream(
    vibe_description: str,
    playlist_length: int = 10
):
    """Stream the AI agent's thinking process while generating a playlist"""
    from queue import Queue
    import threading
    import logging
    from utils.dj_agent_stream import DJAgentStreamEnhancer
    
    async def event_generator():
        # Create a queue to capture log messages
        log_queue = Queue()
        
        # Create stream enhancer
        stream_enhancer = DJAgentStreamEnhancer()
        
        # Custom handler to capture DJ agent logs
        class QueueHandler(logging.Handler):
            def emit(self, record):
                log_queue.put(self.format(record))
        
        # Add our handler to the DJ agent logger
        dj_logger = logging.getLogger("DJAgent")
        queue_handler = QueueHandler()
        queue_handler.setFormatter(logging.Formatter('%(message)s'))
        dj_logger.addHandler(queue_handler)
        
        try:
            # Send initial stage update
            initial_data = {
                'type': 'stage_update',
                'stage': 'analyzing_vibe',
                'stage_number': 1,
                'total_stages': 5,
                'progress': 0.0,
                'message': f'Starting playlist generation for: {vibe_description}',
                'data': {}
            }
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            # Initialize DJ agent
            dj_agent = DJAgent()
            
            # Start playlist generation in a separate task
            generation_task = asyncio.create_task(
                dj_agent.generate_playlist(
                    vibe_description=vibe_description,
                    length=playlist_length,
                    energy_pattern="wave",
                    thread_id=f"vibe-stream-{datetime.now().timestamp()}"
                )
            )
            
            # Stream log messages while generation is running
            while not generation_task.done():
                # Check for new log messages
                while not log_queue.empty():
                    log_msg = log_queue.get()
                    # Process message through enhancer
                    if log_msg.strip():
                        enhanced_data = stream_enhancer.process_message(log_msg)
                        yield f"data: {json.dumps(enhanced_data)}\n\n"
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
            
            # Get the final result
            result = await generation_task
            
            # Send any remaining log messages
            while not log_queue.empty():
                log_msg = log_queue.get()
                if log_msg.strip():
                    enhanced_data = stream_enhancer.process_message(log_msg)
                    yield f"data: {json.dumps(enhanced_data)}\n\n"
            
            if not result["success"]:
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', 'Failed to generate playlist')})}\n\n"
                return
            
            # Process the playlist
            finalized_playlist = result.get("finalized_playlist", [])
            playlist_tracks = []
            
            if finalized_playlist:
                # Send finalizing stage update
                finalizing_data = {
                    'type': 'stage_update',
                    'stage': 'finalizing',
                    'stage_number': 5,
                    'total_stages': 5,
                    'progress': 0.5,
                    'message': f'Processing {len(finalized_playlist)} tracks...',
                    'data': {}
                }
                yield f"data: {json.dumps(finalizing_data)}\n\n"
                
                # Load track info from database
                db_path = os.path.join(os.path.dirname(__file__), 'tracks.db')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                for item in finalized_playlist:
                    filepath = item.get('filepath')
                    if not filepath:
                        continue
                    
                    cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (filepath,))
                    columns = [description[0] for description in cursor.description]
                    row = cursor.fetchone()
                    
                    if row:
                        track = dict(zip(columns, row))
                        track_info = {
                            "filename": track.get('filename', ''),
                            "filepath": track.get('filepath', ''),
                            "duration": track.get('duration', 0.0),
                            "title": track.get('title'),
                            "artist": track.get('artist'),
                            "album": track.get('album'),
                            "genre": track.get('genre'),
                            "year": track.get('year'),
                            "has_artwork": track.get('has_artwork', False),
                            "bpm": track.get('bpm')
                        }
                        playlist_tracks.append(track_info)
                
                cursor.close()
                conn.close()
            
            # Send the final playlist
            final_response = {
                "type": "complete",
                "playlist": playlist_tracks,
                "vibe_analysis": {
                    "agent_response": result.get("response", ""),
                    "vibe_description": vibe_description,
                    "energy_pattern": "wave",
                    "success": True
                },
                "total_tracks_considered": 1000
            }
            
            yield f"data: {json.dumps(final_response)}\n\n"
            
        finally:
            # Remove our handler
            dj_logger.removeHandler(queue_handler)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
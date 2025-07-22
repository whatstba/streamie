from dotenv import load_dotenv

load_dotenv()

# Set MUSIC_DIR environment variable before importing DJAgent
import os

MUSIC_DIR = os.path.expanduser("~/Downloads")  # We'll use Downloads folder for testing
os.environ["MUSIC_DIR"] = MUSIC_DIR

from utils.librosa import run_beat_track
from utils.id3_reader import extract_artwork
from utils.db import get_db
from agents.dj_agent import DJAgent  # Import the DJ agent
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from utils.sqlite_db import get_sqlite_db
from utils.db_migrations import run_migrations
from utils.music_library import MusicLibraryManager
from utils.analysis_queue import AnalysisQueue
from utils.file_watcher import MusicFolderWatcher
from utils.enhanced_analyzer import EnhancedTrackAnalyzer
from utils.metadata_analyzer import MetadataAnalyzer

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import mimetypes
import asyncio
import sqlite3
from datetime import datetime
import json

# Import the AI router - temporarily disabled
# from routers.ai_router import router as ai_router

# Import the deck router
from routers.deck_router import router as deck_router

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

# Include the deck router
app.include_router(deck_router)


class SeratoHotCue(BaseModel):
    """Serato hot cue point model"""

    name: str
    time: float
    color: str
    type: str = "cue"  # 'cue', 'loop', 'phrase'
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


class MusicFolderRequest(BaseModel):
    path: str
    auto_scan: bool = True


class AnalysisStatusResponse(BaseModel):
    pending: int
    processing: int
    completed: int
    failed: int
    total: int
    workers: int
    running: bool


# Global instances
db_path = os.path.join(os.path.dirname(__file__), "tracks.db")
music_library = MusicLibraryManager(db_path)
analysis_queue = AnalysisQueue(db_path)
file_watcher = MusicFolderWatcher(analysis_queue, db_path)
enhanced_analyzer = EnhancedTrackAnalyzer(db_path)
metadata_analyzer = MetadataAnalyzer(db_path)


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    # Run database migrations
    run_migrations(db_path)

    # Check if this is first run
    if music_library.is_first_run():
        print("🎵 First run detected - please configure music folders")
    else:
        print(
            "✅ Music library ready - tracks available, analysis on manual request only"
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    pass  # No cleanup needed - analysis queue only starts on manual request


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
    """List all tracks from the database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get all tracks from the database
        cursor.execute("""
            SELECT filename, filepath, duration, title, artist, album, 
                   genre, year, has_artwork, bpm
            FROM tracks
            ORDER BY artist, album, title
        """)

        tracks = []
        for row in cursor.fetchall():
            track_dict = dict(row)

            # Create TrackInfo object
            track_info = TrackInfo(
                filename=track_dict.get("filename", ""),
                filepath=track_dict.get("filepath", ""),
                duration=track_dict.get("duration", 0.0),
                title=track_dict.get("title"),
                artist=track_dict.get("artist"),
                album=track_dict.get("album"),
                genre=track_dict.get("genre"),
                year=track_dict.get("year"),
                has_artwork=track_dict.get("has_artwork", False),
                bpm=track_dict.get("bpm") if include_bpm else None,
            )
            tracks.append(track_info)

        print(f"✅ Found {len(tracks)} tracks in database")
        return tracks

    except Exception as e:
        print(f"❌ Error fetching tracks from database: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/tracks/batch-analyze")
async def batch_analyze_tracks(filepaths: List[str]):
    """Analyze BPM for multiple tracks in batch"""
    results = []

    for filepath in filepaths:
        # Handle absolute or relative paths
        if os.path.isabs(filepath):
            file_path = filepath
        else:
            file_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), filepath)
            )

        if not os.path.exists(file_path):
            results.append(
                {
                    "filepath": filepath,
                    "bpm": None,
                    "success": False,
                    "error": "File not found",
                }
            )
            continue

        try:
            bpm = run_beat_track(file_path)
            results.append({"filepath": filepath, "bpm": bpm, "success": True})
        except Exception as e:
            results.append(
                {"filepath": filepath, "bpm": None, "success": False, "error": str(e)}
            )

    return results


@app.get("/track/{filepath:path}/analysis", response_model=TrackAnalysisResponse)
async def analyze_track_enhanced(filepath: str):
    """Get comprehensive track analysis including BPM - Serato temporarily disabled"""
    # First check if the filepath is absolute or relative
    if os.path.isabs(filepath):
        file_path = filepath
    else:
        # Try to resolve the relative path
        # Check if it's relative to the python-worker directory
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), filepath))

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
                    doc["beat_times"] = []  # Default to empty list on error
            elif not doc.get("beat_times"):
                doc["beat_times"] = []  # Ensure beat_times exists

        if not doc:
            # Track not found in database - no live analysis fallback
            print(f"❌ Track not found in database: {filepath}")
            raise HTTPException(
                status_code=404,
                detail="Track not found in database. Please run track analysis first to populate BPM data.",
            )

        # Get BPM and other data only from database
        bpm = doc.get("bpm")
        if bpm is None or bpm <= 0:
            print(f"❌ No valid BPM data available for track: {filepath} (BPM: {bpm})")
            raise HTTPException(
                status_code=422,
                detail="No valid BPM data available for this track in database.",
            )

        beat_times = doc.get("beat_times", [])
        mood = doc.get("mood")  # mood might not be in SQLite schema yet
        energy_level = doc.get("energy_level")  # energy_level from SQLite
        print(
            f"🎵 Database BPM: {bpm:.2f} BPM ({len(beat_times)} beats), Energy: {energy_level}"
        )

        # Enable Serato hot cue extraction
        try:
            from utils.serato_reader import serato_reader

            serato_info = serato_reader.get_serato_info(file_path)
            hot_cues = [
                SeratoHotCue(
                    name=cue["name"],
                    time=cue["time"],
                    color=cue["color"],
                    type=cue["type"],
                    index=cue["index"],
                )
                for cue in serato_info.get("hot_cues", [])
            ]
            print(f"🎛️ Extracted {len(hot_cues)} hot cues from Serato data")
        except Exception as e:
            print(f"❌ Error extracting Serato hot cues: {e}")
            serato_info = {"hot_cues": [], "serato_available": False}
            hot_cues = []

        # Suggested transitions based on BPM only (no Serato)
        suggested_transitions = {
            "filter_sweep": bpm > 120,
            "echo_effect": 100 <= bpm <= 140,
            "scratch_compatible": bpm >= 80,
            "has_serato_cues": False,  # Disabled
            "loop_ready": False,  # Disabled
        }

        response = TrackAnalysisResponse(
            bpm=bpm,
            beat_times=beat_times,  # Ensure this is a list
            mood=mood,
            success=True,
            confidence=0.85,  # Standard confidence without Serato
            analysis_time="enhanced",
            suggested_transitions=suggested_transitions,
            serato_data=serato_info,
            hot_cues=hot_cues,
        )

        print(f"✅ Analysis complete: {bpm:.2f} BPM, mood={mood}")
        return response

    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/track/{filepath:path}/artwork")
async def get_artwork(filepath: str):
    """Get album artwork for a track"""
    # Handle absolute or relative paths
    if os.path.isabs(filepath):
        file_path = filepath
    else:
        # First try relative to current directory
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), filepath))

        # If not found, try common music directories
        if not os.path.exists(file_path):
            # Try in Downloads
            downloads_path = os.path.expanduser(f"~/Downloads/{filepath}")
            if os.path.exists(downloads_path):
                file_path = downloads_path
            else:
                # Try in Music folder
                music_path = os.path.expanduser(f"~/Music/{filepath}")
                if os.path.exists(music_path):
                    file_path = music_path

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
    # Handle absolute or relative paths
    if os.path.isabs(filepath):
        file_path = filepath
    else:
        # First try relative to current directory
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), filepath))

        # If not found, try common music directories
        if not os.path.exists(file_path):
            # Try in Downloads
            downloads_path = os.path.expanduser(f"~/Downloads/{filepath}")
            if os.path.exists(downloads_path):
                file_path = downloads_path
            else:
                # Try in Music folder
                music_path = os.path.expanduser(f"~/Music/{filepath}")
                if os.path.exists(music_path):
                    file_path = music_path

    # Log the path being accessed
    print(f"🎵 Streaming request for: {filepath}")
    print(f"🎵 Resolved path: {file_path}")
    print(f"🎵 File exists: {os.path.exists(file_path)}")

    if not os.path.exists(file_path):
        # Try to give more helpful error message
        print(f"❌ File not found: {file_path}")
        raise HTTPException(
            status_code=404, detail=f"Track not found at path: {filepath}"
        )

    try:
        file_size = os.path.getsize(file_path)

        # Get the range header if present
        range_header = request.headers.get("Range")

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "audio/mpeg"  # Default to MP3

        if range_header:
            # Parse range header (e.g., "bytes=0-1023")
            byte_start = 0
            byte_end = file_size - 1

            if range_header.startswith("bytes="):
                range_spec = range_header[6:]
                if "-" in range_spec:
                    start_str, end_str = range_spec.split("-", 1)
                    if start_str:
                        byte_start = int(start_str)
                    if end_str:
                        byte_end = int(end_str)

            # Ensure valid range
            byte_start = max(0, byte_start)
            byte_end = min(file_size - 1, byte_end)
            content_length = byte_end - byte_start + 1

            def iterfile(file_path: str, start: int, chunk_size: int = 8192):
                with open(file_path, "rb") as file:
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
                    "Content-Type": content_type,
                    "Content-Length": str(content_length),
                    "Content-Range": f"bytes {byte_start}-{byte_end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache",
                },
            )
        else:
            # No range header, serve entire file
            def iterfile(file_path: str, chunk_size: int = 8192):
                with open(file_path, "rb") as file:
                    while True:
                        data = file.read(chunk_size)
                        if not data:
                            break
                        yield data

            return StreamingResponse(
                iterfile(file_path),
                headers={
                    "Content-Type": content_type,
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache",
                },
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/generate-vibe-playlist", response_model=VibePlaylistResponse)
async def generate_vibe_playlist(request: VibePlaylistRequest):
    """Generate a playlist based on vibe description using DJ agent"""
    try:
        print("\n" + "=" * 60)
        print("🎨 VIBE PLAYLIST REQUEST")
        print(f"   Vibe: '{request.vibe_description}'")
        print(f"   Length: {request.playlist_length} tracks")
        print("=" * 60)

        # Initialize DJ agent
        dj_agent = DJAgent()

        # Generate playlist using the new agentic approach
        result = await dj_agent.generate_playlist(
            vibe_description=request.vibe_description,
            length=request.playlist_length,
            energy_pattern="wave",
            thread_id=f"vibe-{datetime.now().timestamp()}",  # Unique thread ID
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to generate playlist"),
            )

        # Parse the agent's response to extract playlist
        response_text = result["response"]

        print(f"\n🤖 Agent Response:\n{response_text}")

        # Extract the finalized playlist from the agent
        finalized_playlist = result.get("finalized_playlist", [])
        playlist_tracks = []

        if finalized_playlist:
            print(
                f"\n✅ Agent provided structured playlist with {len(finalized_playlist)} tracks"
            )

            # Load our SQLite database to get full track info
            db_path = os.path.join(os.path.dirname(__file__), "tracks.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get full track info for each filepath in the playlist
            for item in finalized_playlist:
                filepath = item.get("filepath")
                if not filepath:
                    continue

                cursor.execute("SELECT * FROM tracks WHERE filepath = ?", (filepath,))
                columns = [description[0] for description in cursor.description]
                row = cursor.fetchone()

                if row:
                    track = dict(zip(columns, row))
                    track_info = TrackInfo(
                        filename=track.get("filename", ""),
                        filepath=track.get("filepath", ""),
                        duration=track.get("duration", 0.0),
                        title=track.get("title"),
                        artist=track.get("artist"),
                        album=track.get("album"),
                        genre=track.get("genre"),
                        year=track.get("year"),
                        has_artwork=track.get("has_artwork", False),
                        bpm=track.get("bpm"),
                    )
                    playlist_tracks.append(track_info)
                    print(
                        f"   {item['order']}. {track.get('title', 'Unknown')} - {track.get('artist', 'Unknown')} ({item.get('mixing_note', '')})"
                    )

            cursor.close()
            conn.close()

        # Create vibe analysis response
        vibe_analysis_response = {
            "agent_response": response_text,
            "vibe_description": request.vibe_description,
            "energy_pattern": "wave",
            "success": True,
        }

        print(f"\n✅ Playlist generated: {len(playlist_tracks)} tracks")
        print("=" * 60 + "\n")

        return VibePlaylistResponse(
            playlist=playlist_tracks,
            vibe_analysis=vibe_analysis_response,
            total_tracks_considered=1000,  # Approximate
        )

    except Exception as e:
        print(f"❌ Error in generate_vibe_playlist: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/generate-vibe-playlist-stream")
async def generate_vibe_playlist_stream(
    vibe_description: str, playlist_length: int = 10
):
    """Stream the AI agent's thinking process while generating a playlist"""
    from queue import Queue
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
        queue_handler.setFormatter(logging.Formatter("%(message)s"))
        dj_logger.addHandler(queue_handler)

        try:
            # Send initial stage update
            initial_data = {
                "type": "stage_update",
                "stage": "analyzing_vibe",
                "stage_number": 1,
                "total_stages": 5,
                "progress": 0.0,
                "message": f"Starting playlist generation for: {vibe_description}",
                "data": {},
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
                    thread_id=f"vibe-stream-{datetime.now().timestamp()}",
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
                    "type": "stage_update",
                    "stage": "finalizing",
                    "stage_number": 5,
                    "total_stages": 5,
                    "progress": 0.5,
                    "message": f"Processing {len(finalized_playlist)} tracks...",
                    "data": {},
                }
                yield f"data: {json.dumps(finalizing_data)}\n\n"

                # Load track info from database
                db_path = os.path.join(os.path.dirname(__file__), "tracks.db")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                for item in finalized_playlist:
                    filepath = item.get("filepath")
                    if not filepath:
                        continue

                    cursor.execute(
                        "SELECT * FROM tracks WHERE filepath = ?", (filepath,)
                    )
                    columns = [description[0] for description in cursor.description]
                    row = cursor.fetchone()

                    if row:
                        track = dict(zip(columns, row))
                        track_info = {
                            "filename": track.get("filename", ""),
                            "filepath": track.get("filepath", ""),
                            "duration": track.get("duration", 0.0),
                            "title": track.get("title"),
                            "artist": track.get("artist"),
                            "album": track.get("album"),
                            "genre": track.get("genre"),
                            "year": track.get("year"),
                            "has_artwork": track.get("has_artwork", False),
                            "bpm": track.get("bpm"),
                        }
                        playlist_tracks.append(track_info)

                cursor.close()
                conn.close()

            # Send the final playlist
            final_response = {
                "type": "complete",
                "playlist": playlist_tracks,
                "transitions": result.get(
                    "transitions", []
                ),  # Include transitions with effect plans
                "vibe_analysis": {
                    "agent_response": result.get("response", ""),
                    "vibe_description": vibe_description,
                    "energy_pattern": "wave",
                    "success": True,
                },
                "total_tracks_considered": 1000,
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
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# Music Library Management Endpoints


@app.get("/api/library/folders")
async def get_music_folders():
    """Get all configured music folders."""
    folders = music_library.get_music_folders()
    return {"folders": folders}


@app.post("/api/library/folders")
async def add_music_folder(request: MusicFolderRequest):
    """Add a new music folder to the library."""
    try:
        folder_info = music_library.add_music_folder(request.path, request.auto_scan)

        # Auto-scan disabled - tracks are added to database but not analyzed
        folder_info["queued_tracks"] = 0
        folder_info["note"] = (
            "Tracks added to database. Use manual analysis to process them."
        )

        return folder_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/library/folders/{folder_path:path}")
async def remove_music_folder(folder_path: str):
    """Remove a music folder from the library."""
    success = music_library.remove_music_folder(folder_path)
    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"status": "removed", "path": folder_path}


@app.post("/api/library/scan/{folder_id}")
async def scan_music_folder(folder_id: int, full_scan: bool = False):
    """Scan a music folder for new tracks."""
    folders = music_library.get_music_folders()
    folder = next((f for f in folders if f["id"] == folder_id), None)

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not folder["exists"]:
        raise HTTPException(status_code=400, detail="Folder does not exist")

    # Get new tracks
    new_tracks = music_library.get_new_tracks(folder["path"])

    # Queue for analysis
    queued = 0
    for track in new_tracks:
        await analysis_queue.add_track(track, priority=3)
        queued += 1

    # Update scan time
    music_library.update_folder_scan_time(folder["path"])

    return {"folder": folder["path"], "new_tracks": len(new_tracks), "queued": queued}


@app.get("/api/library/stats")
async def get_library_stats():
    """Get music library statistics."""
    stats = music_library.get_library_stats()
    return stats


@app.get("/api/library/settings")
async def get_library_settings():
    """Get library settings."""
    settings = music_library.get_settings()
    return settings


@app.put("/api/library/settings")
async def update_library_settings(settings: Dict[str, str]):
    """Update library settings."""
    for key, value in settings.items():
        music_library.update_setting(key, value)
    return {"status": "updated", "settings": settings}


@app.get("/api/library/analysis/status", response_model=AnalysisStatusResponse)
async def get_analysis_status():
    """Get current analysis queue status."""
    status = await analysis_queue.get_status()
    return AnalysisStatusResponse(**status)


@app.post("/api/library/analysis/retry-failed")
async def retry_failed_analysis(max_retries: int = 3):
    """Retry failed analysis jobs."""
    await analysis_queue.retry_failed(max_retries)
    return {"status": "retrying"}


@app.post("/api/library/analysis/metadata-scan")
async def fast_metadata_scan(background_tasks: BackgroundTasks):
    """Fast metadata-only scan for tracks missing basic metadata.

    This is much faster than full analysis as it only reads file tags.
    """
    # Get tracks needing metadata
    tracks_needing_metadata = music_library.get_tracks_needing_metadata()

    if not tracks_needing_metadata:
        return {
            "status": "complete",
            "message": "All tracks have basic metadata",
            "scanned_tracks": 0,
        }

    # Run metadata analysis in background
    background_tasks.add_task(
        metadata_analyzer.batch_analyze_metadata, tracks_needing_metadata
    )

    return {
        "status": "scanning",
        "message": f"Scanning metadata for {len(tracks_needing_metadata)} tracks",
        "tracks_to_scan": len(tracks_needing_metadata),
    }


@app.post("/api/library/analysis/reprocess-all")
async def reprocess_all_tracks(
    force_reanalyze: bool = False, metadata_only: bool = False
):
    """Reprocess tracks with smart filtering.

    Args:
        force_reanalyze: If True, reanalyze all tracks regardless of current state
        metadata_only: If True, only analyze tracks missing basic metadata (faster)
    """
    if force_reanalyze:
        # Reset all tracks to pending for full reanalysis
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE tracks SET analysis_status = "pending", analysis_version = 1'
        )
        conn.commit()
        conn.close()

        # Get all tracks
        tracks = music_library.get_all_tracks()
        queued_count = 0

        for track in tracks:
            await analysis_queue.add_track(track["filepath"], priority=3)
            queued_count += 1
    else:
        # Smart filtering based on what's actually needed
        if metadata_only:
            # Only get tracks missing essential metadata
            tracks_to_analyze = music_library.get_tracks_needing_metadata()
        else:
            # Get tracks needing any analysis (basic or enhanced)
            tracks_needing_basic = music_library.get_tracks_needing_metadata()
            tracks_needing_enhanced = (
                music_library.get_tracks_missing_enhanced_metadata()
            )
            # Combine and deduplicate
            tracks_to_analyze = list(
                set(tracks_needing_basic + tracks_needing_enhanced)
            )

        queued_count = 0
        for filepath in tracks_to_analyze:
            await analysis_queue.add_track(filepath, priority=3)
            queued_count += 1

    return {
        "status": "reprocessing",
        "queued_tracks": queued_count,
        "analysis_type": "metadata_only" if metadata_only else "full",
        "message": f"Queued {queued_count} tracks for {('metadata' if metadata_only else 'full')} analysis",
    }


@app.post("/api/library/first-run-complete")
async def mark_first_run_complete():
    """Mark that first-run setup is complete."""
    music_library.mark_first_run_complete()
    # Start the analysis queue with enhanced analyzer
    await analysis_queue.start(enhanced_analyzer)
    return {"status": "complete"}


# WebSocket endpoint removed - using periodic HTTP polling instead

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

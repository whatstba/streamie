from dotenv import load_dotenv
load_dotenv() 
from utils.mood_interpreter import interpret_mood
from utils.spotify import search_tracks, get_audio_features
from utils.youtube import search_youtube
from utils.soundcloud import search_soundcloud
from utils.transitions import suggest_transitions
from utils.librosa import run_beat_track
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import List, Optional
import librosa

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

class TrackInfo(BaseModel):
    filename: str
    duration: float
    title: Optional[str] = None
    artist: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {"status": "ok", "message": "AI DJ Backend is running"}

@app.get("/tracks", response_model=List[TrackInfo])
async def list_tracks():
    """List all available music tracks"""
    tracks = []
    for file in os.listdir(MUSIC_DIR):
        if file.endswith(('.mp3', '.wav', '.m4a')):
            try:
                y, sr = librosa.load(os.path.join(MUSIC_DIR, file), duration=10)  # Load first 10 seconds for quick analysis
                duration = librosa.get_duration(y=y, sr=sr)
                
                # For now, we'll use filename as title
                title = os.path.splitext(file)[0]
                
                tracks.append(TrackInfo(
                    filename=file,
                    duration=duration,
                    title=title,
                    artist="Unknown"  # We can add ID3 tag reading later
                ))
            except Exception as e:
                print(f"Error processing {file}: {str(e)}")
                continue
    
    return tracks

@app.get("/track/{filename}/analysis")
async def analyze_track(filename: str):
    """Get beat analysis for a track"""
    file_path = os.path.join(MUSIC_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Track not found")
    
    try:
        return {
            "success": True
        }
        # beat_times = run_beat_track()
        # return {
        #     "beat_times": beat_times.tolist(),
        #     "success": True
        # }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{filename}/waveform")
async def get_waveform(filename: str):
    """Get waveform data for visualization"""
    file_path = os.path.join(MUSIC_DIR, filename)
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

def run_mix_analysis():
    """Original main function logic for mix analysis"""
    beat_track = run_beat_track()
    print(beat_track)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 
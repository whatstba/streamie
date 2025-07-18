"""
Mock data for testing various components.
"""

# Mock librosa beat tracking response
MOCK_BEAT_TRACK_RESPONSE = {
    "tempo": 128.0,
    "beats": [0.0, 0.469, 0.938, 1.406, 1.875, 2.344, 2.812, 3.281],
    "beat_times": [0.0, 0.469, 0.938, 1.406, 1.875, 2.344, 2.812, 3.281]
}

# Mock Essentia mood analysis response
MOCK_MOOD_ANALYSIS = {
    "mood_acoustic": 0.1,
    "mood_aggressive": 0.2,
    "mood_electronic": 0.9,
    "mood_happy": 0.8,
    "mood_party": 0.85,
    "mood_relaxed": 0.3,
    "mood_sad": 0.1,
    "mood_dark": 0.2,
    "mood_energetic": 0.8
}

# Mock metadata
MOCK_METADATA = {
    "title": "Test Track",
    "artist": "Test Artist",
    "album": "Test Album",
    "date": "2024",
    "genre": "Electronic",
    "comment": "Test comment",
    "duration": 180.5
}

# Mock Serato data
MOCK_SERATO_DATA = {
    "hot_cues": [
        {"name": "Intro", "time": 0.0, "color": "#FF0000", "type": "cue"},
        {"name": "Drop", "time": 30.5, "color": "#00FF00", "type": "cue"},
        {"name": "Break", "time": 60.0, "color": "#0000FF", "type": "cue"}
    ],
    "bpm": 128.0,
    "beatgrid": [0.0, 0.469, 0.938, 1.406]
}

# Mock OpenAI/LangChain responses
MOCK_OPENAI_VIBE_ANALYSIS = {
    "vibe_keywords": ["uplifting", "energetic", "progressive", "beach", "sunset"],
    "energy_pattern": "build_up",
    "bpm_range": {"min": 120, "max": 128},
    "mood_preference": ["happy", "party", "energetic"]
}

MOCK_DJ_AGENT_THINKING = [
    {"step": "analyze_vibe", "output": "Analyzing vibe: uplifting progressive house for sunset beach party"},
    {"step": "search_tracks", "output": "Found 15 tracks matching criteria"},
    {"step": "select_tracks", "output": "Selected 5 tracks with good energy progression"},
    {"step": "verify_transitions", "output": "All transitions verified, BPM progression smooth"}
]

# Mock track database entries
MOCK_TRACKS_DB = [
    {
        "id": 1,
        "filename": "sunset_vibes.mp3",
        "filepath": "/music/sunset_vibes.mp3",
        "title": "Sunset Vibes",
        "artist": "Beach House DJ",
        "album": "Summer Collection",
        "duration": 240.0,
        "bpm": 124.0,
        "key": "G#m",
        "energy": 0.7,
        "genre": "Progressive House",
        "year": "2024",
        "has_artwork": True,
        "mood_happy": 0.8,
        "mood_energetic": 0.75,
        "mood_aggressive": 0.2
    },
    {
        "id": 2,
        "filename": "ocean_breeze.mp3",
        "filepath": "/music/ocean_breeze.mp3",
        "title": "Ocean Breeze",
        "artist": "Coastal Sound",
        "album": "Beach Sessions",
        "duration": 300.0,
        "bpm": 126.0,
        "key": "Am",
        "energy": 0.75,
        "genre": "Progressive House",
        "year": "2024",
        "has_artwork": True,
        "mood_happy": 0.85,
        "mood_energetic": 0.8,
        "mood_relaxed": 0.6
    },
    {
        "id": 3,
        "filename": "peak_time_anthem.mp3",
        "filepath": "/music/peak_time_anthem.mp3",
        "title": "Peak Time Anthem",
        "artist": "Festival King",
        "album": "Main Stage",
        "duration": 330.0,
        "bpm": 128.0,
        "key": "Cm",
        "energy": 0.95,
        "genre": "Progressive House",
        "year": "2024",
        "has_artwork": True,
        "mood_aggressive": 0.7,
        "mood_energetic": 0.95,
        "mood_party": 0.9
    }
]

# Mock LangGraph state
MOCK_LANGGRAPH_STATE = {
    "current_track": MOCK_TRACKS_DB[0],
    "playlist": [],
    "vibe_context": "uplifting progressive house sunset beach",
    "energy_pattern": "build_up",
    "target_duration": 30,
    "bpm_range": {"min": 120, "max": 128}
}
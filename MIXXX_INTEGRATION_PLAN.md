# Mixxx LangGraph Integration Plan for Streamie DJ System

## Executive Summary
This plan outlines the integration of Mixxx-inspired multi-agent DJ functionality into the existing Streamie DJ agent system. The approach focuses on server-side audio mixing with WebSocket streaming and pre-planned DJ sets for optimal performance.

## Architecture Overview

### Key Design Decisions
1. **Server-side audio mixing** using scipy/numpy with WebSocket streaming
2. **Pre-planned DJ sets** eliminating real-time complexity
3. **Strict genre validation** using only the 18 genres in the database
4. **Pedalboard library** for professional audio effects (recommended based on research)

## Implementation Phases

### Phase 1: Core State Architecture ✅
Extend DJAgentState to support full DJ session management:
```python
class DJSessionState(DJAgentState):
    # Existing fields plus:
    decks: Dict[str, DeckState]  # A, B, C, D virtual decks
    mixer: MixerState
    effects: Dict[str, EffectState]
    session_id: str
    session_mode: str  # "pre_planned" for now
    audio_cache: Dict[str, np.ndarray]  # Pre-loaded audio
    mix_timeline: List[MixEvent]  # Complete mix script
    current_position: float  # Playback position in seconds
```

### Phase 2: Multi-Deck Management
Virtual deck implementation optimized for pre-planned sets:
- Pre-load all tracks using librosa.load()
- Calculate optimal cue points during planning phase
- Store beat grids and phrase markers
- No real-time beat sync needed

### Phase 3: Mixer Integration
Pre-calculated mixing parameters:
- Crossfader automation curves (linear, logarithmic, scratch)
- Volume envelopes for smooth transitions
- 3-band EQ automation (low, mid, high)
- All timing synchronized to beat grid

### Phase 4: Analysis Agent Enhancement
Batch analysis for complete playlists:
- Leverage existing audio_analyzer.py and enhanced_analyzer.py
- Add phrase detection for better mix points
- Store all analysis in SQLite database
- Calculate compatible transition points between tracks

### Phase 5: Mix Coordinator Agent
Intelligent mix planning using AI:
- Analyze entire playlist energy flow
- Optimize track order if needed
- Plan all transitions with AI assistance
- Generate complete mix timeline

### Phase 6: Effects System with Pedalboard
Professional effects using Spotify's Pedalboard library:
```python
from pedalboard import Pedalboard, HighpassFilter, LowpassFilter, Delay, Reverb

class EffectProcessor:
    def apply_filter_sweep(self, audio, start_freq, end_freq, duration):
        # Automated filter sweep
        
    def apply_echo(self, audio, delay_time, feedback, mix):
        # Echo/delay effect
        
    def apply_scratch(self, audio, pattern):
        # Simulated scratch effect using pitch shifting
```

### Phase 7: Session Persistence
LangGraph checkpointing for session management:
- SqliteSaver for persistent session state
- Save/resume mix planning sessions
- Export/import complete mix timelines
- Performance analytics storage

### Phase 8: Human-in-the-Loop Controls
Optional manual adjustments:
- Preview transitions before finalizing
- Adjust effect parameters
- Fine-tune crossfade timing
- Override AI suggestions

### Phase 9: Genre Validation System
Strict enforcement of available genres:
```python
VALID_GENRES = [
    "Rap/Hip Hop", "R&B", "Pop", "African Music", "Jazz", 
    "Dance", "Reggae", "Films/Games", "Electro", "Rock",
    "Soul & Funk", "Alternative", "Latin Music", "Salsa",
    "Reggaeton", "Brazilian Music", "Bolero"
]

# AI must only select from these genres
# No fuzzy matching or aliasing
```

### Phase 10: API Integration
FastAPI endpoints for control and streaming:
```python
# Planning endpoints
POST /api/session/plan - Create new pre-planned set
GET /api/session/{id}/timeline - Get mix timeline
PUT /api/session/{id}/adjust - Modify mix parameters

# Streaming endpoints
WS /ws/session/{id}/stream - Stream mixed audio
GET /api/session/{id}/preview/{timestamp} - Preview specific transition
POST /api/session/{id}/export - Export as single audio file
```

### Phase 11: Audio Mixing Engine
Core mixing implementation:
```python
class AudioMixEngine:
    def __init__(self):
        self.sample_rate = 44100
        self.board = Pedalboard()
        
    def process_timeline(self, timeline: MixTimeline) -> Generator:
        """Process mix timeline and yield audio chunks"""
        
    def apply_crossfade(self, deck_a, deck_b, position, curve):
        """Crossfade between decks with curve type"""
        
    def apply_eq_bands(self, audio, low, mid, high):
        """Apply 3-band EQ using Pedalboard filters"""
```

### Phase 12: Pre-planned Set Workflow
Complete set generation pipeline:
1. User requests vibe/playlist
2. AI analyzes request and selects from valid genres
3. System queries tracks matching criteria
4. AI evaluates and orders tracks
5. System batch analyzes all audio
6. AI plans all transitions and effects
7. System generates complete timeline
8. User previews key transitions
9. System streams final mix via WebSocket

## Technical Stack

### Audio Processing
- **librosa**: Audio loading and analysis
- **scipy**: Signal processing and filtering
- **numpy**: Array operations and mixing
- **pedalboard**: Professional audio effects
- **soundfile**: Audio I/O (already in requirements)

### Streaming
- **WebSocket**: Real-time audio streaming
- **asyncio**: Asynchronous processing
- **FastAPI**: API framework (existing)

### AI/ML
- **LangGraph**: Agent orchestration
- **LangChain**: LLM integration (existing)
- **OpenAI**: GPT-4 for intelligent decisions

## Error Handling & Edge Cases

1. **Genre Validation**: Reject invalid genres with clear error messages
2. **Audio Loading**: Graceful handling of corrupt/missing files
3. **Effect Limits**: Enforce 1-2 effects max per transition
4. **Memory Management**: Stream large audio files in chunks
5. **WebSocket Disconnects**: Resume from last position

## Performance Considerations

1. **Pre-load Strategy**: Cache frequently used tracks
2. **Chunk Size**: 4096 samples for WebSocket streaming
3. **Compression**: Optional MP3/OGG encoding for bandwidth
4. **Timeline Caching**: Store computed timelines in Redis

## Migration Path

1. Keep existing agent functionality intact
2. Add new DJ session endpoints alongside existing ones
3. Gradually migrate features to new architecture
4. Maintain backward compatibility for vibe playlists

## Database Schema Extensions

### New Tables
```sql
-- DJ Sessions
CREATE TABLE dj_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vibe_description TEXT,
    energy_pattern TEXT,
    genre_focus TEXT,
    mix_timeline JSON,
    status TEXT DEFAULT 'planning'
);

-- Session Tracks (ordered playlist)
CREATE TABLE session_tracks (
    session_id TEXT,
    position INTEGER,
    track_filepath TEXT,
    deck_assignment TEXT,
    load_time REAL,
    unload_time REAL,
    FOREIGN KEY (session_id) REFERENCES dj_sessions(id),
    FOREIGN KEY (track_filepath) REFERENCES tracks(filepath)
);

-- Mix Events (transitions, effects, etc)
CREATE TABLE mix_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    event_type TEXT,
    timestamp REAL,
    parameters JSON,
    FOREIGN KEY (session_id) REFERENCES dj_sessions(id)
);
```

## Next Steps

1. Install Pedalboard: `pip install pedalboard`
2. Create models for DeckState, MixerState, EffectState
3. Extend DJAgentState with new fields
4. Implement basic audio loading and caching
5. Create AudioMixEngine class
6. Build WebSocket streaming endpoint

This plan provides a complete roadmap for integrating professional DJ capabilities while maintaining the existing system's strengths.
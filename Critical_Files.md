# Critical Production Files - Streamie DJ Application

This document maps ONLY the essential files used in production. Test files, legacy code, and unused features are excluded.

## User Flow Overview

```
Frontend (React) → API (FastAPI) → Services → Database → Audio Processing → Streaming
     ↓                    ↓              ↓           ↓            ↓              ↓
  Web UI          HTTP Requests    Business     SQLite      Mixing &      HTTP/SSE
                                    Logic                   Effects       Response
```

## Frontend Essentials (apps/web/)

### Entry Points & Core Components
```
src/app/page.tsx                          # Main app entry point - renders Player component
src/components/player/Player.tsx          # Main UI component - track list, controls, now playing
src/components/player/DjModeControls.tsx  # DJ set generation UI and controls
src/components/player/TrackList.tsx       # Virtualized track list with search
src/components/player/QueueManager.tsx    # Queue display and management
src/components/player/AudioControls.tsx   # Playback controls (play/pause/skip)
src/components/player/ProgressBar.tsx     # Track progress display
src/components/navigation/Sidebar.tsx     # Left sidebar navigation
```

### State Management & Services
```
src/context/AudioPlayerContext.tsx        # Centralized audio state, server streaming integration
src/services/musicService.ts              # API client for backend communication
src/services/aiService.ts                 # SSE handler for real-time DJ set updates
src/hooks/useKeyboardShortcuts.ts         # Keyboard controls for playback
```

### Configuration
```
package.json                              # Dependencies and scripts
next.config.js                            # Next.js configuration
tailwind.config.ts                        # Styling configuration
```

## Backend Core (apps/python-worker/)

### Entry Point & API
```
main.py                                   # FastAPI server initialization, router mounting
```

### Active Routers
```
routers/audio_router.py                   # /api/audio/* - HTTP streaming endpoint
routers/mix_router.py                     # /api/dj-set/* - DJ set generation endpoints
routers/mixer_router.py                   # /api/mixer/* - Crossfader and master volume
routers/deck_router.py                    # /api/deck/* - Deck state management
routers/analysis_router.py                # /api/analysis/* - Track analysis endpoints
```

### Core Services
```
services/service_manager.py               # Initializes and manages all services
services/dj_set_service.py                # Generates AI-powered DJ sets with transitions
services/set_playback_controller.py       # Orchestrates automatic DJ set playback
services/audio_engine.py                  # Real-time audio mixing engine
services/deck_manager.py                  # Virtual deck state management (A/B/C/D)
services/mixer_manager.py                 # Crossfader and master volume control
services/effect_manager.py                # Manages and applies transition effects
services/audio_prerenderer.py             # Pre-renders tracks with effects for smooth playback
services/audio_streamer.py                # Converts numpy audio to streamable format
services/music_library.py                 # Scans and manages local music files
```

### AI & Analysis
```
agents/dj_agent.py                        # LangGraph agent for intelligent DJ set creation
utils/dj_llm.py                          # AI service with specialized DJ personas
utils/audio_analyzer.py                   # BPM and beat detection using librosa
utils/enhanced_analyzer.py                # Musical key and energy analysis
utils/genre_mapper.py                     # Maps folder names to music genres
```

### Database & Models
```
models/database.py                        # SQLAlchemy async setup, Track table
models/dj_set_models.py                  # Pydantic models for DJ sets and playback
models/deck.py                           # Deck state Pydantic models
models/mixer.py                          # Mixer configuration models
models/effect_models.py                  # Effect definitions and state tracking
utils/db_adapter.py                      # Database operations wrapper
```

### Utilities
```
utils/sse_manager.py                     # Server-sent events for real-time updates
utils/cache_manager.py                   # Audio file caching (if exists)
```

### Configuration
```
requirements.txt                         # Python dependencies
Makefile                                # Development commands (format, lint, test)
.env                                    # Environment variables (API keys)
```

## Critical Dependencies & Data Flow

### DJ Set Generation Flow
```
1. Frontend: DjModeControls.tsx → musicService.ts → POST /api/dj-set/generate
2. Backend: mix_router.py → dj_set_service.py → dj_agent.py → dj_llm.py
3. AI Processing: Vibe analysis → Track evaluation → Transition planning
4. Pre-rendering: audio_prerenderer.py applies effects to tracks
5. Response: SSE updates via sse_manager.py → aiService.ts → UI updates
```

### Playback Flow
```
1. Frontend: POST /api/dj-set/play-immediately
2. Backend: set_playback_controller.py orchestrates timing
3. Track Loading: deck_manager.py loads tracks at precise times
4. Audio Mixing: audio_engine.py reads deck states, applies effects
5. Streaming: audio_streamer.py → GET /api/audio/stream/http
6. Frontend: AudioPlayerContext.tsx receives and plays audio chunks
```

### Track Analysis Flow
```
1. Music Discovery: music_library.py scans ~/Downloads
2. Analysis: audio_analyzer.py (BPM) + enhanced_analyzer.py (key/energy)
3. Storage: Results saved to SQLite via db_adapter.py
4. Access: Frontend queries via /tracks endpoint
```

### Effect Processing
```
1. DJ Agent plans effects with timing and parameters
2. effect_manager.py schedules effects during transitions
3. audio_prerenderer.py OR audio_engine.py applies DSP
4. Effects include: filter_sweep, reverb, delay, echo, gate, eq_sweep
```

## File Dependencies

### Frontend Dependencies
- `Player.tsx` → `AudioPlayerContext.tsx`, `musicService.ts`
- `DjModeControls.tsx` → `musicService.ts`, `aiService.ts`
- `AudioPlayerContext.tsx` → `musicService.ts` (API calls)

### Backend Dependencies
- `main.py` → All routers, `service_manager.py`
- `dj_set_service.py` → `dj_agent.py`, `audio_prerenderer.py`, `db_adapter.py`
- `set_playback_controller.py` → `deck_manager.py`, `audio_engine.py`
- `audio_engine.py` → `deck_manager.py`, `mixer_manager.py`, `effect_manager.py`
- `dj_agent.py` → `dj_llm.py`, `db_adapter.py`

### Cross-System Dependencies
- Frontend `musicService.ts` ↔ Backend routers
- Frontend `aiService.ts` ↔ Backend `sse_manager.py`
- Database models ↔ All services via `db_adapter.py`

## Notes

- **Hot Cues**: Stored as JSON in database, extracted by `dj_set_service.py`
- **Audio Format**: 44.1kHz stereo, processed as numpy arrays
- **Streaming**: Base64-encoded audio chunks over HTTP
- **AI Models**: gpt-4.1-mini (analysis), o4-mini (finalization)
- **Music Source**: Scans ~/Downloads directory by default
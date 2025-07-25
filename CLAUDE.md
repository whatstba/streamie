# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Streamie is a modern music player and DJ experience application featuring AI-powered playlist generation, beat analysis, and intelligent mixing capabilities. It consists of a Python FastAPI backend for audio processing and a Next.js React frontend for the user interface.

## Essential Commands

### Python Backend (apps/python-worker/)
```bash
# Development
python main.py                    # Start the FastAPI server

# After making changes, run:
make format                       # Format code with ruff
make lint                        # Check linting (flake8 + ruff)
make test                        # Run all tests
make ci                          # Full CI pipeline (clean, lint, test-coverage)

# Testing
make test-integration            # Integration tests only
make test-unit                   # Unit tests only
make test-coverage               # Tests with coverage report
pytest -v -k "test_name"         # Run specific tests
```

### Web Frontend (apps/web/)
```bash
# Development
npm run dev                      # Start Next.js dev server with Turbopack

# After making changes, run:
npm run lint                     # ESLint check
npm run build                    # TypeScript check + build
npm test                         # Run all tests

# Testing
npm test:watch                   # Watch mode
npm test:coverage                # With coverage report
```

## Architecture Overview

### Backend Architecture
The Python backend uses FastAPI with a modular structure:

- **API Layer** (`main.py`): RESTful endpoints for track management, streaming, and AI features
- **DJ Agent** (`agents/dj_agent.py`): LangGraph-based intelligent playlist generation with AI-powered track selection and transition planning
- **DJ LLM Service** (`utils/dj_llm.py`): AI service with specialized personas for vibe analysis, track evaluation, and transition design
- **DJ Set Service** (`services/dj_set_service.py`): Generates complete DJ sets with pre-planned transitions and timing
- **Set Playback Controller** (`services/set_playback_controller.py`): Orchestrates automatic playback with track loading and transitions
- **Audio Engine** (`services/audio_engine.py`): Real-time audio mixing with effects processing
- **Deck Manager** (`services/deck_manager.py`): Virtual deck management for multi-track mixing
- **Effect Manager** (`services/effect_manager.py`): Applies DJ effects (filter, echo, scratch) with precise timing
- **Audio Analysis** (`utils/audio_analyzer.py`): Beat detection and BPM analysis using librosa and essentia
- **Enhanced Analyzer** (`utils/enhanced_analyzer.py`): Key detection, energy analysis, and structure detection
- **Database** (`utils/db_adapter.py`): SQLite with comprehensive metadata storage including BPM, key, energy levels
- **Music Services** (`utils/`): Integrations with Spotify, SoundCloud, and YouTube

Key API endpoints:
- `/tracks` - List all tracks with optional BPM filtering
- `/track/{filepath}/stream` - Individual track streaming with range request support
- `/track/{filepath}/analysis` - Get BPM, beats, key, and energy analysis
- `/api/dj-set/generate` - Generate complete DJ set with transitions
- `/api/dj-set/play-immediately` - Generate and start playing DJ set
- `/api/audio/stream/http` - Stream server-mixed audio with effects
- `/ai/generate-vibe-playlist` - (Deprecated) Use DJ set generation instead
- `/ai/generate-vibe-playlist-stream` - (Deprecated) Use DJ set generation instead

### Frontend Architecture
The Next.js frontend uses React 19 with TypeScript:

- **Audio Context** (`context/AudioPlayerContext.tsx`): Centralized audio state with transition effects and DJ mode
- **Player Components** (`components/player/`):
  - `DjModeControls.tsx`: Next track display, transition timing, BPM matching
  - `AdvancedDjControls.tsx`: Effect controls, beat grid visualization
  - `TrackList.tsx`: Virtualized track list with real-time search
- **Navigation** (`components/navigation/Sidebar.tsx`): Now Playing, mix settings (removed Home/Liked Songs)
- **Services** (`services/`): API client with SSE support for real-time updates
- **Virtualized Lists**: Performance optimization for large music libraries

## Key Technical Decisions

1. **Database Schema**: SQLite with columns: `key` (not `musical_key`), `energy_level`, `camelot_key`
2. **Audio Processing**: Pre-computed analysis with librosa/essentia, stored in database
3. **AI Models**: 
   - `gpt-4.1-mini` for vibe analysis, track evaluation, transition planning
   - `o4-mini` for playlist finalization (no temperature parameter)
4. **Transition Effects**: Limited to 1-2 effects max, low intensity (0.2-0.5) for natural sound
5. **Audio Transitions**: No pause() during transitions, use gain automation only
6. **Formatting**: Use `ruff` for Python formatting, not `black`

## Development Workflow

1. Music files are scanned from `~/Downloads` directory (configurable)
2. Audio analysis computed on-demand and cached:
   - BPM and beat detection (librosa)
   - Musical key detection (essentia) with Camelot notation
   - Energy level estimation (RMS, spectral features)
3. DJ Agent workflow:
   - Vibe analysis interprets natural language requests
   - Track evaluation scores each track's suitability
   - Transition planning designs effects and timing
   - Playlist finalization optimizes track order
4. Frontend receives real-time updates via Server-Sent Events (SSE)

## Testing Philosophy

- Mock at the boundary (external services, file system, audio libraries)
- Use synthetic test data for consistency
- Focus on complete user flows rather than isolated units
- All tests should run without external dependencies

## Recent Changes

### New API Endpoints
- `/api/dj-set/generate` - Generate a complete DJ set with transitions
- `/api/dj-set/play-immediately` - Generate and start playing a set
- `/api/dj-set/playback/status` - Get current playback status
- `/api/audio/stream/http` - Stream mixed audio output

### AI Integration
- Replaced manual calculations with AI-powered intelligence
- Added structured Pydantic models for LLM outputs
- Implemented specialized AI personas for different DJ tasks
- Fixed transition effect validation (TransitionEffect model)

### Database Updates
- Changed column name from `musical_key` to `key`
- Added energy level and profile storage
- Populated all tracks with key and energy data

### Frontend Improvements (To Be Updated)
- Fixed audio gaps during transitions (removed pause())
- Limited transition effects to 1-2 with lower intensity
- Added effect tracking to prevent overlaps
- Fixed NaN% intensity display issues
- Marked BPM Sync and Hot Cues as "Coming Soon"
- Removed Home and Liked Songs navigation buttons
- NOTE: Client-side mixing features are deprecated in favor of server-side mixing

### Analysis Scripts
- `analyze_track_keys.py`: Analyzes musical keys for tracks
- `analyze_track_energy.py`: Calculates energy levels using librosa
- `analyze_and_enhance_tracks_sql.py`: Main analysis pipeline

## Important Notes

- Always preserve `filepath` when processing AI-generated playlists
- Transition effects must include all fields: type, start_at, duration, intensity
- Use exactly `o4-mini` model name (not o1-mini)
- Energy levels can be estimated from BPM/genre when audio analysis fails
- Never use `gpt-3.5 or gpt-4/4o` models only o4-mini for complex tasks and gpt-4.1-mini for quicker tasks
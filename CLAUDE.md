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
make format                       # Format code with Black
make lint                        # Check linting (flake8 + black)
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
- **DJ Agent** (`agents/dj_agent.py`): LangGraph-based intelligent playlist generation with vibe-based selection and BPM-smooth transitions
- **Audio Analysis** (`utils/audio_analyzer.py`): Beat detection and BPM analysis using librosa and essentia
- **Database** (`utils/db_adapter.py`): SQLite with MongoDB-like interface for track metadata and analysis results
- **Music Services** (`utils/`): Integrations with Spotify, SoundCloud, and YouTube

Key API endpoints:
- `/tracks` - List all tracks with optional BPM filtering
- `/track/{filepath}/stream` - Audio streaming with range request support
- `/track/{filepath}/analysis` - Get BPM, beats, and mood analysis
- `/ai/generate-vibe-playlist` - AI-powered playlist generation

### Frontend Architecture
The Next.js frontend uses React 19 with TypeScript:

- **Audio Context** (`context/AudioPlayerContext.tsx`): Centralized audio state management
- **Player Components** (`components/player/`): DJ mode controls, BPM display, queue management
- **Services** (`services/`): API client layer for backend communication
- **Virtualized Lists**: Performance optimization for large music libraries

## Key Technical Decisions

1. **Database Migration**: Recently migrated from MongoDB to SQLite for simpler deployment
2. **Audio Processing**: Pre-computed analysis stored in database rather than real-time processing
3. **Streaming**: HTTP range requests for efficient audio delivery and seeking
4. **Testing Strategy**: Integration tests preferred over unit tests, with mocked external dependencies
5. **AI Integration**: LangGraph for stateful playlist generation with context awareness

## Development Workflow

1. Music files are scanned from `~/Downloads` directory (configurable)
2. Audio analysis (BPM, beats) is computed on-demand and cached in SQLite
3. The DJ agent uses track metadata and analysis to create smooth transitions
4. Frontend displays real-time updates via streaming responses

## Testing Philosophy

- Mock at the boundary (external services, file system, audio libraries)
- Use synthetic test data for consistency
- Focus on complete user flows rather than isolated units
- All tests should run without external dependencies

## Current Focus

The branch `codex/optimize-backend-analysis-with-librosa-and-bpm-storage` indicates ongoing work on:
- Backend audio analysis optimization
- BPM storage improvements
- Enhanced librosa integration for better beat detection
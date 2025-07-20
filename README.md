# Streamie - AI-Powered DJ Music Player

A modern music player and DJ experience featuring AI-powered playlist generation, intelligent beat mixing, and automated transitions. Built with Next.js, React, and FastAPI.


## 🚀 Getting Started

1. **Start the Python backend**:
   ```bash
   cd ../python-worker
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

2. **Start the web app**:
   ```bash
   npm install
   npm run dev
   ```

3. **Add music**: Place your music files (MP3, M4A, WAV, FLAC, OGG) in `~/Downloads`

4. **Use the app**:
   - Browse your music library with the virtualized list
   - Search for tracks, artists, or albums
   - Enable DJ Mode for AI-powered mixing and transitions
   - Generate playlists with natural language ("upbeat summer vibes")
   - Experience smooth, intelligent transitions between tracks

## 🎛️ Features

### Core Features
- **AI-Powered DJ Mode**: Intelligent playlist generation with smooth transitions
- **Natural Language Playlists**: Generate playlists from descriptions like "chill evening vibes"
- **Auto BPM & Key Analysis**: Automatic beat, tempo, and musical key detection
- **Smart Transitions**: AI-planned crossfades with filter, echo, and scratch effects
- **Energy & Mood Analysis**: Tracks analyzed for energy levels and mood profiles
- **Virtualized Scrolling**: Smooth performance even with thousands of tracks

### Audio Analysis
- **BPM Detection**: Using librosa and essentia for accurate tempo analysis
- **Musical Key Detection**: Camelot Wheel notation for harmonic mixing
- **Energy Estimation**: Dynamic energy profiling for better track selection
- **Beat Grid Visualization**: Real-time waveform and beat displays

### DJ Features
- **Auto-Mix Modes**: Track-end, interval, or hot-cue based mixing
- **Transition Effects**: Professional filter sweeps, echo, and scratch effects
- **BPM Display**: Precise tempo display (2 decimal places)
- **Queue Management**: See upcoming tracks and transition timing

### Coming Soon
- **BPM Sync**: Automatic tempo matching between tracks
- **Hot Cues**: Set and jump to cue points for live mixing

## 🔧 Tech Stack

### Frontend
- **Framework**: Next.js 15, React 19, TypeScript
- **Styling**: Tailwind CSS
- **Audio**: Web Audio API for effects and transitions
- **State Management**: React Context with SSE streaming
- **UI Components**: Heroicons, react-virtualized

### Backend
- **API**: Python FastAPI with async support
- **AI/ML**: 
  - LangGraph for stateful DJ agent workflows
  - OpenAI GPT-4.1-mini for vibe analysis and track evaluation
  - OpenAI o4-mini for playlist finalization and transitions
- **Audio Processing**:
  - librosa for BPM detection and audio analysis
  - essentia for musical key detection
- **Database**: SQLite with enhanced metadata storage
- **Streaming**: HTTP range requests for efficient audio delivery

## 🎵 AI Models

Streamie uses specialized AI models for different aspects of the DJ experience:

- **Vibe Analyst** (gpt-4.1-mini): Interprets natural language playlist requests
- **Track Evaluator** (gpt-4.1-mini): Scores tracks for playlist suitability
- **Transition Master** (gpt-4.1-mini): Plans professional transitions between tracks
- **Playlist Finalizer** (o4-mini): Optimizes track order and overall flow

## 📁 Database Schema

Tracks are stored with comprehensive metadata:
- Basic: title, artist, album, genre, year, duration
- Audio: BPM, musical key (with Camelot notation), energy level
- Analysis: beat times, key confidence, energy profile
- Structure: song segments, auto-generated hot cues
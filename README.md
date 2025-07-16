# Streamie Web App

A modern listening experience built with Next.js, React, and FastAPI.


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
   - Click any track to select and automatically analyze its BPM
   - View track metadata and album artwork

## 🎛️ Features

- **Auto BPM Analysis**: Click any track to automatically get beat analysis
- **Virtualized Scrolling**: Smooth performance even with thousands of tracks
- **Search & Filter**: Find tracks instantly with real-time search
- **Album Artwork**: Automatic artwork display with fallbacks
- **Metadata Display**: Shows artist, album, genre, year, and duration
- **Visual Feedback**: Loading states and analysis progress indicators

## 🔧 Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Virtualization**: react-virtualized
- **Icons**: Heroicons
- **Backend**: Python, FastAPI, Langgraph
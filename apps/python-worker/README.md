# AI DJ MVP

This is a command-line MVP for an AI DJ system that curates and arranges a short DJ mix based on a desired vibe, mood, or genre. It uses Spotify for discovery and metadata, and YouTube/SoundCloud for streaming links.

## Features
- Accepts a mood/genre prompt (e.g., "afrobeats party starter", "deep house afterhours")
- Selects a sequence of tracks that fit the vibe, based on audio features (BPM, key, energy, mood, etc.)
- Analyzes transition points and proposes smooth transitions
- Outputs a Mix Plan with tracklist, transition suggestions, and estimated duration

## Setup
1. Clone the repo and `cd` into the directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```env
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
   OPENAI_API_KEY=your_openai_api_key
   YOUTUBE_API_KEY=your_youtube_api_key
   SOUNDCLOUD_CLIENT_ID=your_soundcloud_client_id
   ```

## Usage
Run the main script:
```bash
python main.py
```
Enter a mood/genre prompt when prompted. The system will output a mix plan with tracklist, transitions, and streaming links.

### Pre-compute Track BPM and Mood
Analyze all tracks and store their BPM, beat grids, and mood classification in MongoDB:

```bash
python scripts/create_track_db.py
```

## Extending
- Add more moods/genres to `utils/mood_interpreter.py`
- Improve transition logic in `utils/transitions.py`
- Add support for user-uploaded tracks or previews

## License
MIT 
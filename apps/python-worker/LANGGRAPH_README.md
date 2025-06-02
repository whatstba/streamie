# LangGraph DJ Agent Implementation

## Overview

The LangGraph DJ Agent is an intelligent playlist and vibe manager that analyzes tracks based on BPM, mood, energy levels, and other metadata to create seamless, vibe-matched playlists.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file with:

```env
OPENAI_API_KEY=your_openai_api_key
MONGO_DB_PW=your_mongodb_password
MONGODB_DB=streamie
```

### 3. Populate Track Database

First, ensure your tracks are analyzed and stored in MongoDB:

```bash
python scripts/create_track_db.py
```

## Architecture

### Agent Nodes

1. **Track Analyzer Node**: Analyzes current track's BPM, mood, and energy
2. **Context Builder Node**: Builds mixing context (time, history, preferences)
3. **Vibe Matcher Node**: Queries database for similar tracks
4. **Playlist Builder Node**: Creates ordered playlist with energy flow
5. **Transition Planner Node**: Plans mix points and suggests effects

### Similarity Algorithm

The agent calculates track similarity using:
- **BPM Proximity (30%)**: Tracks within ±5% BPM
- **Mood Match (25%)**: Cosine similarity of mood vectors
- **Energy Compatibility (20%)**: Energy level matching
- **Genre Affinity (15%)**: Genre compatibility
- **Key Compatibility (10%)**: Harmonic mixing potential

## API Endpoints

### 1. Analyze Vibe
```http
POST /ai/analyze-vibe
{
  "current_track_id": "path/to/track.mp3",
  "context": {
    "time_of_day": "evening",
    "crowd_energy": 0.8
  }
}
```

### 2. Generate Playlist
```http
POST /ai/generate-playlist
{
  "seed_track_id": "path/to/track.mp3",
  "playlist_length": 10,
  "energy_pattern": "build_up",
  "context": {}
}
```

Energy patterns:
- `build_up`: Gradually increase energy
- `peak_time`: Maintain high energy
- `cool_down`: Gradually decrease energy
- `wave`: Alternating energy levels

### 3. Suggest Next Track
```http
POST /ai/suggest-next-track
{
  "current_track_id": "path/to/track.mp3",
  "played_tracks": ["track1.mp3", "track2.mp3"],
  "desired_vibe": "party",
  "context": {}
}
```

### 4. Rate Transition
```http
POST /ai/rate-transition
{
  "from_track_id": "track1.mp3",
  "to_track_id": "track2.mp3",
  "rating": 0.9,
  "notes": "Smooth transition, crowd loved it"
}
```

### 5. Get Mixing Insights
```http
GET /ai/mixing-insights
```

## Testing

Run the test script:

```bash
cd apps/python-worker
python examples/test_dj_agent.py
```

## Frontend Integration

### 1. Track Suggestion Component

```typescript
// Example React component
const TrackSuggestion = () => {
  const [suggestion, setSuggestion] = useState(null);
  
  const getSuggestion = async (currentTrackId) => {
    const response = await fetch('/api/ai/suggest-next-track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_track_id: currentTrackId,
        context: {
          time_of_day: new Date().getHours() < 12 ? 'morning' : 'evening',
          crowd_energy: 0.7
        }
      })
    });
    
    const data = await response.json();
    setSuggestion(data);
  };
  
  return (
    <div>
      {suggestion && (
        <div>
          <h3>Next Track Suggestion</h3>
          <p>{suggestion.track.title} - {suggestion.track.artist}</p>
          <p>Confidence: {(suggestion.confidence * 100).toFixed(0)}%</p>
          <p>{suggestion.reasoning}</p>
        </div>
      )}
    </div>
  );
};
```

### 2. Playlist Generator

```typescript
const PlaylistGenerator = () => {
  const generatePlaylist = async (seedTrackId, pattern) => {
    const response = await fetch('/api/ai/generate-playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        seed_track_id: seedTrackId,
        playlist_length: 10,
        energy_pattern: pattern
      })
    });
    
    return await response.json();
  };
};
```

## Energy Flow Visualization

The agent provides energy flow data for each playlist:

```javascript
// Example energy flow visualization
const energyFlow = [0.5, 0.6, 0.7, 0.8, 0.9, 0.85, 0.7, 0.6, 0.5, 0.4];

// Use with a charting library like Chart.js
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: playlist.map((_, i) => `Track ${i + 1}`),
    datasets: [{
      label: 'Energy Flow',
      data: energyFlow,
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.4
    }]
  }
});
```

## Learning and Improvement

The agent learns from:
1. **Transition Ratings**: Rate successful/unsuccessful transitions
2. **Play History**: Tracks commonly played together
3. **Skip Data**: Tracks that were suggested but skipped
4. **Time Patterns**: What works at different times

## Troubleshooting

### Common Issues

1. **No tracks found**: Ensure MongoDB has analyzed tracks
2. **Low similarity scores**: Check if tracks have mood data
3. **API errors**: Verify OpenAI API key is set

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Key Detection**: Add harmonic mixing capabilities
2. **Crowd Feedback**: Real-time energy adjustment
3. **Genre Evolution**: Track genre progression throughout set
4. **Vocal Analysis**: Detect vocal presence for better mixing
5. **Weather Integration**: Adjust vibes based on weather
6. **Historical Analysis**: Learn from past successful sets 
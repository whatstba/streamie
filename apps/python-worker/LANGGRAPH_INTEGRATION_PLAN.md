# LangGraph DJ Agent Integration Plan

## Overview
The LangGraph DJ Agent will act as an intelligent playlist and vibe manager that analyzes the current track's BPM and metadata to create seamless, vibe-matched playlists.

## Core Capabilities
1. **Track Analysis**: Analyze current track's BPM, mood, genre, and energy level
2. **Vibe Matching**: Find tracks with similar vibes based on multiple factors
3. **Playlist Generation**: Create intelligent playlists that maintain flow and energy
4. **Transition Planning**: Suggest optimal transitions between tracks
5. **Adaptive Learning**: Learn from user feedback and mixing history

## Technical Architecture

### 1. Database Schema Enhancements
Current fields we have:
- `filepath`, `filename`, `duration`
- `title`, `artist`, `album`, `genre`, `year`
- `bpm`, `beat_times`
- `mood` (acoustic, aggressive, electronic, happy, party, relaxed, sad)

Additional fields needed:
- `energy_level` (0-1): Overall energy/intensity
- `key` (musical key): For harmonic mixing
- `danceability` (0-1): How suitable for dancing
- `valence` (0-1): Musical positivity
- `tempo_stability` (0-1): How consistent the tempo is
- `vocal_presence` (0-1): Amount of vocals
- `mixing_history`: Array of successful mixes

### 2. LangGraph Agent Structure

```
┌─────────────────┐
│   User Input    │
│ (Current Track) │
└────────┬────────┘
         │
    ┌────▼────┐
    │  START  │
    └────┬────┘
         │
    ┌────▼─────────────┐
    │ Track Analyzer   │◄──── Analyzes current track
    │     Node         │      BPM, mood, energy
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │ Context Builder  │◄──── Builds mixing context
    │     Node         │      (crowd energy, time of day)
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │ Vibe Matcher     │◄──── Queries DB for similar tracks
    │     Node         │      Multi-factor similarity
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │ Playlist Builder │◄──── Creates ordered playlist
    │     Node         │      Considers energy flow
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │ Transition       │◄──── Plans mix points
    │ Planner Node     │      Suggests effects
    └────┬─────────────┘
         │
    ┌────▼────┐
    │   END    │
    └──────────┘
```

### 3. Similarity Algorithm

The agent will calculate track similarity using weighted factors:

```python
similarity_weights = {
    'bpm_proximity': 0.30,      # BPM within ±5%
    'mood_match': 0.25,         # Mood vector similarity
    'energy_compatibility': 0.20, # Energy level difference
    'genre_affinity': 0.15,    # Genre compatibility
    'key_compatibility': 0.10   # Harmonic mixing potential
}
```

### 4. Playlist Generation Strategies

1. **Energy Arc Patterns**:
   - Build-up: Gradually increase energy
   - Peak Time: Maintain high energy
   - Cool-down: Gradually decrease energy
   - Wave: Alternating energy levels

2. **Mood Journey Types**:
   - Happy → Party → Aggressive
   - Relaxed → Acoustic → Sad
   - Electronic → Aggressive → Party

3. **BPM Progression Rules**:
   - Smooth: ±2 BPM changes
   - Standard: ±5 BPM changes  
   - Creative: Halftime/Double-time transitions

### 5. API Endpoints

```python
# New endpoints for the FastAPI backend

POST /ai/analyze-vibe
- Input: current_track_id, context (time_of_day, crowd_energy)
- Output: vibe analysis and recommendations

POST /ai/generate-playlist
- Input: seed_track_id, playlist_length, energy_pattern
- Output: ordered playlist with transition suggestions

POST /ai/suggest-next-track
- Input: current_track_id, played_tracks, desired_vibe
- Output: next track recommendation with confidence score

POST /ai/rate-transition
- Input: from_track_id, to_track_id, rating, notes
- Output: success (updates learning model)

GET /ai/mixing-insights
- Output: patterns and insights from mixing history
```

### 6. Integration with Frontend

The agent will provide real-time suggestions to the DJ interface:

1. **Live Suggestions Panel**: Shows 3-5 next track suggestions
2. **Vibe Meter**: Visual representation of current vs. target vibe
3. **Energy Graph**: Playlist energy flow visualization
4. **Transition Helper**: Cue point and effect suggestions

### 7. Learning and Adaptation

The agent will learn from:
- Successful transitions (high ratings)
- Skipped suggestions
- Manual track selections
- Crowd response metrics (if available)

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- Set up LangGraph agent structure
- Implement track analyzer node
- Create similarity calculation engine
- Basic playlist generation

### Phase 2: Advanced Features (Week 2)
- Context-aware recommendations
- Transition planning
- Energy arc patterns
- API endpoints

### Phase 3: Frontend Integration (Week 3)
- Real-time suggestion UI
- Vibe visualization
- Transition helper UI
- Feedback collection

### Phase 4: Learning System (Week 4)
- Implement feedback loop
- Track mixing history
- Preference learning
- Performance optimization

## Technology Stack

- **LangGraph**: Agent orchestration
- **LangChain**: LLM integration for natural language queries
- **MongoDB**: Track metadata and mixing history
- **Redis**: Caching for real-time suggestions
- **FastAPI**: API backend
- **WebSocket**: Real-time updates to frontend

## Success Metrics

1. **Vibe Coherence**: 90%+ of suggested tracks maintain vibe
2. **BPM Compatibility**: 95%+ smooth BPM transitions
3. **User Adoption**: 70%+ of suggestions accepted
4. **Response Time**: <100ms for next track suggestion
5. **Learning Improvement**: 10%+ increase in acceptance rate over time 
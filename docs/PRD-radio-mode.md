# Product Requirements Document: Radio Mode with AI Host

## Overview
Radio Mode enhances Streamie's music player experience by introducing an AI-powered radio host that provides commentary, trivia, and positive news between tracks. The feature seamlessly integrates with existing playlist and transition functionality while adding a personalized, engaging voice companion.

## Core Features

### 1. AI Radio Host Agent
- **Voice Generation**: OpenAI gpt-4o-mini-tts model (latest, most reliable TTS)
- **Personality System**: Dynamic personas that adapt to playlist mood
- **Content Types**:
  - Track introductions and previews
  - Encouraging messages and uplift content
  - Music trivia and artist insights
  - Positive news snippets from curated sources
  - Smooth transition commentary

### 2. Voice Customization
- **OpenAI Voice Options** (11 built-in voices): 
  - Alloy, Ash, Ballad, Coral (cheerful/positive)
  - Echo, Fable (storytelling), Nova, Onyx
  - Sage, Shimmer (soft/calming)
- **Customizable via Instructions Parameter**:
  - Accent (American West-Coast, UK RP, Nigerian, etc.)
  - Emotional range and intonation patterns
  - Speech speed and tone variations
  - Impressions and character voices
  - Whisper mode for ambient sections
- **Real-time Streaming**: Support for chunk transfer encoding

### 3. Preset Personas
1. **Lo-fi Study Pal**: 
   - Voice: Shimmer or Sage
   - Instructions: "Speak in a soft ASMR tone, whisper during downtempo sections, slow speech speed"
2. **Festival Hype**: 
   - Voice: Nova or Coral
   - Instructions: "High energy, fast speech, hype intonation with occasional cheers"
3. **World Citizen**: 
   - Voice: Fable or Onyx
   - Instructions: "Rotate between light accents (UK, Nigerian, French), balanced emotional range"
4. **Retro Radio Host**: 
   - Voice: Echo or Ballad
   - Instructions: "Classic AM radio style, slight theatrical intonation, dad-joke humor"
5. **Mindful Mentor**: 
   - Voice: Sage or Ash
   - Instructions: "Calm, balanced emotional range, gentle pacing, mindfulness cues"

### 4. Engagement Cadence
- **Frequency**: 20-30 second segments every 2-3 tracks (~5 minutes)
- **Triggers**:
  - Track transitions (>3s gaps)
  - Energy shifts detected
  - Random inspirational moments (5% chance)
  - Session wrap-ups

### 5. Audio Integration
- **Audio Ducking**: Automatic volume reduction during voice segments
- **Seamless Mixing**: Voice overlays without interrupting music flow
- **Transition Awareness**: Commentary adapts to DJ mode transitions

## Technical Architecture

### Backend Components

#### 1. Radio Host Agent (`apps/python-worker/agents/radio_host_agent.py`)
```python
- LangGraph-based state machine
- Persona management and switching
- Content generation pipeline
- Voice timing orchestration
```

#### 2. TTS Service (`apps/python-worker/utils/tts_service.py`)
```python
- OpenAI TTS API integration
- Voice parameter management
- Audio stream handling
- Caching for repeated phrases
```

#### 3. Content Services
```python
- News API integration (positive news sources)
- Music trivia database
- Artist information lookup
- Playlist mood analysis
```

#### 4. API Endpoints
```
POST /radio/enable - Enable radio mode
POST /radio/disable - Disable radio mode
GET /radio/status - Current mode and settings
POST /radio/persona - Update persona settings
GET /radio/personas - List available personas
POST /radio/voice-settings - Update voice parameters
GET /radio/next-segment - Get next voice segment
```

### Frontend Components

#### 1. Radio Mode Toggle (`components/player/RadioModeToggle.tsx`)
- Clean on/off switch in player UI
- Visual indicator when active

#### 2. Voice Settings Modal (`components/settings/VoiceSettings.tsx`)
- Radial UI for voice parameters
- Persona preset selector
- Real-time preview capability

#### 3. Voice Visualization (`components/player/VoiceWaveform.tsx`)
- Minimal waveform animation during speech
- Color-coded by emotional range

#### 4. Context Updates
- Extend AudioPlayerContext with radio mode state
- Voice queue management
- Audio ducking controls

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
1. Radio Host Agent implementation
2. TTS service integration
3. Basic API endpoints
4. Simple on/off toggle UI

### Phase 2: Personas & Content (Week 2)
1. Persona system with presets
2. Content generation templates
3. News API integration
4. Music trivia database

### Phase 3: Voice Customization (Week 3)
1. Voice parameter controls
2. Settings UI implementation
3. Real-time voice preview
4. User preference persistence

### Phase 4: Polish & Testing (Week 4)
1. Audio ducking refinement
2. Timing optimization
3. Edge case handling
4. Performance testing

## Success Metrics
- User engagement: >60% try radio mode
- Retention: >40% keep it enabled
- Customization: >30% adjust voice settings
- Satisfaction: >4.5/5 rating

## Privacy & Safety
- No personal data commentary
- Positive/neutral content only
- Configurable frequency limits
- Easy mute/disable options

## Future Enhancements
- Multi-language support
- User-generated personas
- Community-shared presets
- Voice interaction capabilities
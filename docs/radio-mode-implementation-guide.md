# Radio Mode Implementation Guide

## TTS Integration with gpt-4o-mini-tts

### Basic TTS Request

```python
import openai
from typing import Optional
import io

class TTSService:
    def __init__(self):
        self.client = openai.OpenAI()
        self.model = "gpt-4o-mini-tts"
    
    async def generate_speech(
        self,
        text: str,
        voice: str = "coral",
        instructions: str = "Speak in a friendly, conversational tone",
        response_format: str = "mp3"
    ) -> bytes:
        """Generate speech with persona-specific instructions"""
        
        response = await self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            instructions=instructions,
            response_format=response_format
        )
        
        return await response.read()
```

### Persona Voice Mapping

```python
PERSONA_VOICES = {
    "lo_fi_study": {
        "voice": "shimmer",
        "instructions": (
            "Speak in a soft ASMR tone with a slow, relaxed pace. "
            "Whisper gently during transitions. "
            "Use calming intonation with minimal emotional range."
        )
    },
    "festival_hype": {
        "voice": "nova",
        "instructions": (
            "Speak with high energy and excitement! Fast speech, "
            "hype intonation, occasional 'Yeah!' or 'Let's go!' "
            "Sound like you're pumping up a festival crowd."
        )
    },
    "world_citizen": {
        "voice": "fable",
        "instructions": (
            "Speak with a warm, worldly tone. Occasionally hint at "
            "different accents (British, Nigerian, French) subtly. "
            "Balanced emotional range with storytelling quality."
        )
    },
    "retro_radio": {
        "voice": "echo",
        "instructions": (
            "Channel classic AM radio host energy. Slightly theatrical, "
            "clear enunciation, occasional dad jokes. Think 1970s "
            "smooth radio personality with vintage charm."
        )
    },
    "mindful_mentor": {
        "voice": "sage",
        "instructions": (
            "Speak calmly and thoughtfully. Gentle pacing with "
            "mindful pauses. Soothing tone that encourages "
            "reflection and presence. Never rushed."
        )
    }
}
```

### Dynamic Instruction Generation

```python
def build_voice_instructions(persona: PersonaConfig, context: dict) -> str:
    """Build dynamic instructions based on persona and context"""
    
    base_instructions = []
    
    # Accent
    if persona.personality.accent != "default":
        base_instructions.append(f"Speak with a {persona.personality.accent} accent")
    
    # Emotional range
    emotion_map = {
        "chill": "minimal emotional variation, stay relaxed",
        "balanced": "natural emotional expression",
        "hype": "high energy and excitement"
    }
    base_instructions.append(emotion_map[persona.personality.emotional_range])
    
    # Speed
    speed_map = {
        "slow": "Speak slowly and deliberately",
        "normal": "Natural conversational pace",
        "fast": "Quick, energetic speech"
    }
    base_instructions.append(speed_map[persona.personality.speech_speed])
    
    # Tone
    tone_map = {
        "warm": "warm and friendly tone",
        "energetic": "upbeat and energetic delivery",
        "playful": "playful and fun personality",
        "asmr-soft": "soft ASMR-style whisper"
    }
    base_instructions.append(tone_map[persona.personality.tone])
    
    # Context-specific adjustments
    if context.get("is_downtempo") and persona.personality.whisper_mode:
        base_instructions.append("Whisper softly for this downtempo section")
    
    if context.get("energy_shift"):
        base_instructions.append("Acknowledge the energy shift in your delivery")
    
    return ". ".join(base_instructions) + "."
```

### Streaming Implementation

```python
async def stream_radio_speech(
    self,
    text: str,
    persona: PersonaConfig,
    context: dict
) -> AsyncIterator[bytes]:
    """Stream TTS audio in real-time"""
    
    voice_config = PERSONA_VOICES.get(persona.id, PERSONA_VOICES["world_citizen"])
    instructions = build_voice_instructions(persona, context)
    
    # Override with persona-specific instructions if needed
    if persona.voice.instructions:
        instructions = persona.voice.instructions
    
    async with self.client.audio.speech.with_streaming_response.create(
        model=self.model,
        voice=voice_config["voice"],
        input=text,
        instructions=instructions,
        response_format="pcm"  # Best for streaming
    ) as response:
        async for chunk in response.iter_bytes():
            yield chunk
```

### Content Examples by Persona

```python
PERSONA_SCRIPTS = {
    "lo_fi_study": {
        "intro": "~whispers~ Hey there... {track} is floating in next... perfect for deep focus...",
        "encouragement": "~gentle reminder~ You're doing great... breathe deep... keep flowing...",
        "trivia": "~softly~ Did you know... {fact}... isn't that peaceful?",
        "sign_off": "~whispers~ Stay mindful, friend..."
    },
    "festival_hype": {
        "intro": "YOOO! GET READY! {track} is about to DROP! This is gonna be INSANE!",
        "encouragement": "YOU'RE CRUSHING IT! Keep that energy HIGH! Let's GOOO!",
        "trivia": "YO CHECK THIS OUT! {fact}! How SICK is that?!",
        "sign_off": "KEEP THE PARTY GOING! PEACE OUT!"
    },
    "world_citizen": {
        "intro": "Coming up, we have {track} - a beautiful journey at {bpm} BPM.",
        "encouragement": "Quick shout-out from {city} - you're doing brilliantly today.",
        "trivia": "Here's something fascinating: {fact}. Music truly connects us all.",
        "sign_off": "Until next time, keep exploring the world through sound."
    }
}
```

### Audio Ducking Integration

```python
class RadioModeController:
    def __init__(self, audio_context, tts_service):
        self.audio_context = audio_context
        self.tts_service = tts_service
        self.duck_level = 0.3  # 30% volume
        self.fade_duration = 500  # ms
    
    async def play_radio_segment(self, segment: VoiceSegment):
        """Play radio host speech with audio ducking"""
        
        # Generate or retrieve TTS audio
        audio_data = await self.tts_service.generate_speech(
            text=segment.script,
            voice=segment.persona.voice.voice,
            instructions=segment.instructions
        )
        
        # Duck the music
        await self.audio_context.fade_volume(1.0, self.duck_level, self.fade_duration)
        
        # Play the voice
        await self.audio_context.play_voice_overlay(audio_data)
        
        # Restore music volume
        await self.audio_context.fade_volume(self.duck_level, 1.0, self.fade_duration)
```

## Frontend Integration

### Radio Mode Toggle Component

```typescript
interface RadioModeProps {
    enabled: boolean;
    currentPersona: PersonaConfig;
    onToggle: () => void;
    onPersonaChange: (persona: PersonaConfig) => void;
}

export function RadioModeControls({ enabled, currentPersona, onToggle, onPersonaChange }: RadioModeProps) {
    return (
        <div className="radio-mode-controls">
            <button onClick={onToggle} className={`toggle ${enabled ? 'active' : ''}`}>
                <RadioIcon />
                {enabled ? 'Radio Mode ON' : 'Radio Mode OFF'}
            </button>
            
            {enabled && (
                <div className="persona-indicator">
                    <span className="persona-name">{currentPersona.name}</span>
                    <VoiceWaveform active={isVoicePlaying} color={getPersonaColor(currentPersona)} />
                </div>
            )}
        </div>
    );
}
```

### Voice Settings UI

```typescript
export function VoiceSettingsModal({ persona, onChange }: VoiceSettingsProps) {
    const presets = ['lo_fi_study', 'festival_hype', 'world_citizen', 'retro_radio', 'mindful_mentor'];
    
    return (
        <Modal title="Radio Host Settings">
            <div className="preset-selector">
                {presets.map(preset => (
                    <button
                        key={preset}
                        onClick={() => onChange(PERSONA_PRESETS[preset])}
                        className={persona.id === preset ? 'active' : ''}
                    >
                        {PERSONA_PRESETS[preset].name}
                    </button>
                ))}
            </div>
            
            <div className="voice-customization">
                <label>Voice</label>
                <select value={persona.voice.voice} onChange={e => updateVoice(e.target.value)}>
                    {AVAILABLE_VOICES.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
                
                <label>Custom Instructions</label>
                <textarea
                    value={persona.voice.instructions}
                    onChange={e => updateInstructions(e.target.value)}
                    placeholder="Describe how the voice should sound..."
                />
                
                <button onClick={previewVoice}>Preview Voice</button>
            </div>
        </Modal>
    );
}
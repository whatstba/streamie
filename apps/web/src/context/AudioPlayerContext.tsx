'use client';

import React, {
  createContext,
  useContext,
  useState,
  useRef,
  useEffect,
  ReactNode,
  useCallback,
  useMemo,
} from 'react';
import { musicService } from '@/services/musicService';

interface Track {
  filename: string;
  filepath: string;
  duration: number;
  title: string | null;
  artist: string | null;
  album: string | null;
  genre: string | null;
  year: string | null;
  has_artwork: boolean;
  bpm?: number;
}

interface HotCue {
  id: string;
  name: string;
  time: number;
  color: string;
  type: 'cue' | 'loop' | 'phrase';
}

interface TransitionEffect {
  type: 'filter' | 'echo' | 'reverse' | 'loop' | 'scratch';
  intensity: number;
  duration: number;
}

interface HotCueTransitionPlan {
  outroHotCue: HotCue;
  introHotCue: HotCue;
  compatibilityScore: number; // 0-1 score indicating how well the cues match
  bpmCompatible: boolean;
  phraseAligned: boolean;
  recommendedCrossfadeDuration: number;
  recommendedEffects: TransitionEffect[];
}

interface TransitionEffectPlan {
  profile: 'tempo_blend' | 'energy_shift' | 'genre_bridge' | 'smooth_flow';
  effects: Array<{
    type: 'filter' | 'echo' | 'reverse' | 'loop';
    start_at: number; // seconds from transition start
    duration: number;
    intensity: number;
  }>;
  crossfade_curve: 'linear' | 'exponential' | 's-curve';
}

interface AudioPlayerState {
  // Current track and queue
  currentTrack: Track | null;
  queue: Track[];
  currentIndex: number;

  // Playback state
  isPlaying: boolean;
  isLoading: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;

  // Player settings
  repeat: 'none' | 'one' | 'all';
  shuffle: boolean;

  // DJ Mode features
  djMode: boolean;
  autoTransition: boolean;
  mixInterval: number; // Fixed interval in seconds (30, 45, 60)
  mixMode: 'interval' | 'track-end' | 'hot-cue'; // Choose between fixed interval, track-end, or hot cue mixing
  transitionTime: number; // seconds before end to start transition (for track-end mode)
  crossfadeDuration: number; // duration of crossfade in seconds
  isTransitioning: boolean;
  transitionProgress: number; // 0 to 1
  nextTrack: Track | null;
  timeUntilTransition: number; // seconds until transition starts
  lastMixTime: number; // timestamp of last mix for interval mode

  // Enhanced DJ features
  bpmSyncEnabled: boolean;
  pitchShift: number;
  hotCues: { [trackId: string]: HotCue[] };
  currentEffects: TransitionEffect[];
  beatAlignment: boolean;
  loopActive: boolean;
  loopStart: number;
  loopEnd: number;
  scratchMode: boolean;

  // BPM matching
  sourceBpm: number | null;
  targetBpm: number | null;
  syncRatio: number;

  // Hot cue transition planning
  hotCueTransitionPlan: HotCueTransitionPlan | null;

  // Automated transition effects
  transitionEffectPlan: TransitionEffectPlan | null;
}

interface AudioPlayerActions {
  // Track control
  playTrack: (track: Track, queue?: Track[]) => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => void;

  // Navigation
  skipToNext: () => void;
  previousTrack: () => void;
  seekTo: (time: number) => void;

  // Volume control
  setVolume: (volume: number) => void;
  toggleMute: () => void;

  // Queue management
  addToQueue: (track: Track) => void;
  removeFromQueue: (index: number) => void;
  clearQueue: () => void;
  moveTrackInQueue: (fromIndex: number, toIndex: number) => void;

  // Settings
  setRepeat: (mode: 'none' | 'one' | 'all') => void;
  toggleShuffle: () => void;

  // DJ Mode
  toggleDjMode: () => Promise<void>;
  toggleAutoTransition: () => void;
  setTransitionTime: (seconds: number) => void;
  setCrossfadeDuration: (seconds: number) => void;
  forceTransition: () => void;
}

interface AudioPlayerContextType {
  // Existing state properties
  currentTrack: Track | null;
  isPlaying: boolean;
  isLoading: boolean;
  duration: number;
  currentTime: number;
  volume: number;
  isMuted: boolean;
  queue: Track[];
  currentIndex: number;
  shuffle: boolean;
  repeat: 'none' | 'one' | 'all';
  djMode: boolean;
  autoTransition: boolean;
  transitionTime: number;
  crossfadeDuration: number;
  isTransitioning: boolean;
  transitionProgress: number;
  nextTrack: Track | null;
  timeUntilTransition: number;

  // Enhanced DJ properties
  bpmSyncEnabled: boolean;
  pitchShift: number;
  hotCues: { [trackId: string]: HotCue[] };
  currentEffects: TransitionEffect[];
  beatAlignment: boolean;
  loopActive: boolean;
  sourceBpm: number | null;
  targetBpm: number | null;
  syncRatio: number;

  // Existing actions
  playTrack: (track: Track, queue?: Track[]) => Promise<void>;
  play: () => void;
  pause: () => void;
  skipToNext: () => void;
  skipToPrevious: () => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  toggleShuffle: () => void;
  toggleRepeat: () => void;
  addToQueue: (track: Track) => void;
  removeFromQueue: (index: number) => void;
  clearQueue: () => void;
  moveQueueItem: (fromIndex: number, toIndex: number) => void;
  toggleDjMode: () => void;
  setAutoTransition: (enabled: boolean) => void;
  setTransitionTime: (time: number) => void;
  setCrossfadeDuration: (duration: number) => void;
  forceTransition: () => void;

  // Enhanced DJ functions
  setBpmSync: (enabled: boolean, targetTrack?: Track) => Promise<void>;
  addHotCue: (trackId: string, name: string, time: number, type?: HotCue['type']) => void;
  jumpToHotCue: (cue: HotCue) => void;
  applyTransitionEffect: (effect: TransitionEffect) => void;
  toggleBeatAlignment: () => void;
  setPitchShift: (pitch: number) => void;
  triggerScratch: (intensity?: number) => void;
  triggerEcho: (intensity?: number) => void;
  triggerFilter: (intensity?: number) => void;
  setMixInterval: (seconds: number) => void;
  setMixMode: (mode: 'interval' | 'track-end' | 'hot-cue') => void;
  mixInterval: number;
  mixMode: 'interval' | 'track-end' | 'hot-cue';
  setTransitionEffectPlan: (plan: TransitionEffectPlan | null) => void;
  transitionEffectPlan: TransitionEffectPlan | null;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | null>(null);

export const useAudioPlayer = () => {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    throw new Error('useAudioPlayer must be used within an AudioPlayerProvider');
  }
  return context;
};

interface AudioPlayerProviderProps {
  children: ReactNode;
}

export const AudioPlayerProvider: React.FC<AudioPlayerProviderProps> = ({ children }) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const nextAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const currentGainRef = useRef<GainNode | null>(null);
  const nextGainRef = useRef<GainNode | null>(null);
  const currentSourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const nextSourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const transitionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const transitionIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Add state ref to avoid stale closures
  const stateRef = useRef<AudioPlayerState | null>(null);

  // Track connection state to prevent multiple connections
  const currentConnectedRef = useRef<boolean>(false);
  const nextConnectedRef = useRef<boolean>(false);

  // Compressor nodes for better audio quality
  const currentCompressorRef = useRef<DynamicsCompressorNode | null>(null);
  const nextCompressorRef = useRef<DynamicsCompressorNode | null>(null);

  // Enhanced audio processing refs
  const filterRef = useRef<BiquadFilterNode | null>(null);
  const delayRef = useRef<DelayNode | null>(null);
  const reverbRef = useRef<ConvolverNode | null>(null);
  const distortionRef = useRef<WaveShaperNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const beatDetectorRef = useRef<any>(null);
  const pitchShiftRef = useRef<AudioWorkletNode | null>(null);

  const [state, setState] = useState<AudioPlayerState>({
    currentTrack: null,
    queue: [],
    currentIndex: -1,
    isPlaying: false,
    isLoading: false,
    currentTime: 0,
    duration: 0,
    volume: 1,
    isMuted: false,
    repeat: 'none',
    shuffle: false,
    djMode: false,
    autoTransition: true,
    mixInterval: 60, // Default to 60 seconds
    mixMode: 'interval', // Default to interval mode
    transitionTime: 30,
    crossfadeDuration: 5,
    isTransitioning: false,
    transitionProgress: 0,
    nextTrack: null,
    timeUntilTransition: 0,
    lastMixTime: 0,
    bpmSyncEnabled: false,
    pitchShift: 0,
    hotCues: {},
    currentEffects: [],
    beatAlignment: true,
    loopActive: false,
    loopStart: 0,
    loopEnd: 0,
    scratchMode: false,
    sourceBpm: null,
    targetBpm: null,
    syncRatio: 1.0,
    hotCueTransitionPlan: null,
    transitionEffectPlan: null,
  });

  // Helper to update both state and ref atomically
  const updateState = useCallback((updater: (prev: AudioPlayerState) => AudioPlayerState) => {
    setState((prev) => {
      const newState = updater(prev);
      stateRef.current = newState;
      return newState;
    });
  }, []);

  // Web Audio API initialization is now ONLY done when DJ mode is explicitly enabled
  // This prevents conflicts with basic HTML5 audio playback
  // useEffect(() => { ... }) removed - AudioContext created in toggleDjMode() only

  // Add scratch buffer creation for real scratch effects
  const createScratchBuffer = () => {
    if (!audioContextRef.current) return null;

    const context = audioContextRef.current;
    const bufferLength = context.sampleRate * 0.1; // 100ms scratch buffer
    const buffer = context.createBuffer(1, bufferLength, context.sampleRate);
    const data = buffer.getChannelData(0);

    // Generate scratch sound (vinyl-like noise)
    for (let i = 0; i < bufferLength; i++) {
      const t = i / context.sampleRate;
      // Vinyl scratch simulation: filtered white noise with frequency sweep
      const noise = (Math.random() * 2 - 1) * 0.3;
      const freq = 1000 + Math.sin(t * 50) * 800; // Frequency sweep
      const tone = Math.sin(2 * Math.PI * freq * t) * 0.1;
      data[i] = (noise + tone) * Math.exp(-t * 5); // Decay envelope
    }

    return buffer;
  };

  // Initialize Web Audio connections ONCE when audio elements are created
  const initializeWebAudioConnections = async () => {
    if (!audioContextRef.current || !audioRef.current || !nextAudioRef.current) return;

    const context = audioContextRef.current;

    // Resume context if needed
    if (context.state === 'suspended') {
      await context.resume();
    }

    try {
      // Only create connections if they don't exist AND audio element is not already connected
      if (!currentSourceRef.current && !currentConnectedRef.current) {
        try {
          currentSourceRef.current = context.createMediaElementSource(audioRef.current);
          currentGainRef.current = context.createGain();
          currentCompressorRef.current = context.createDynamicsCompressor();
        } catch (mediaSourceError) {
          console.warn(
            '🎧 DJ MIND: Failed to create MediaElementSource for current track, falling back to HTML5 audio'
          );
          currentConnectedRef.current = false;
          return; // Exit early - will use basic HTML5 audio
        }

        // Configure compressor
        currentCompressorRef.current.threshold.setValueAtTime(-24, context.currentTime);
        currentCompressorRef.current.knee.setValueAtTime(30, context.currentTime);
        currentCompressorRef.current.ratio.setValueAtTime(12, context.currentTime);
        currentCompressorRef.current.attack.setValueAtTime(0.003, context.currentTime);
        currentCompressorRef.current.release.setValueAtTime(0.25, context.currentTime);

        // Create effects chain if it doesn't exist
        if (!filterRef.current || !delayRef.current) {
          createEffectsChain();
        }

        // Connect the full audio chain with effects in place but bypassed
        if (filterRef.current && delayRef.current) {
          // Connect: source -> gain -> filter -> delay -> compressor -> destination
          currentSourceRef.current.connect(currentGainRef.current);
          currentGainRef.current.connect(filterRef.current);
          filterRef.current.connect(delayRef.current);
          delayRef.current.connect(currentCompressorRef.current);
          currentCompressorRef.current.connect(context.destination);
          
          console.log('🎧 DJ MIND: Effects chain connected (bypassed)');
        } else {
          // Fallback: direct connection without effects
          currentSourceRef.current.connect(currentGainRef.current);
          currentGainRef.current.connect(currentCompressorRef.current);
          currentCompressorRef.current.connect(context.destination);
          
          console.log('🎧 DJ MIND: Direct audio chain connected (no effects)');
        }

        // Set initial gain value to match state volume
        currentGainRef.current.gain.value = state.volume;

        // IMPORTANT: Set audio element volume to 1 so Web Audio gain controls the volume
        audioRef.current.volume = 1;

        currentConnectedRef.current = true;
        console.log('🎧 DJ MIND: Current track Web Audio initialized');
      }

      if (!nextSourceRef.current && !nextConnectedRef.current) {
        try {
          nextSourceRef.current = context.createMediaElementSource(nextAudioRef.current);
          nextGainRef.current = context.createGain();
          nextCompressorRef.current = context.createDynamicsCompressor();
        } catch (mediaSourceError) {
          console.warn(
            '🎧 DJ MIND: Failed to create MediaElementSource for next track, falling back to HTML5 audio:',
            mediaSourceError
          );
          nextConnectedRef.current = false;
          return; // Exit early - will use basic HTML5 audio
        }

        // Configure compressor
        nextCompressorRef.current.threshold.setValueAtTime(-24, context.currentTime);
        nextCompressorRef.current.knee.setValueAtTime(30, context.currentTime);
        nextCompressorRef.current.ratio.setValueAtTime(12, context.currentTime);
        nextCompressorRef.current.attack.setValueAtTime(0.003, context.currentTime);
        nextCompressorRef.current.release.setValueAtTime(0.25, context.currentTime);

        // For next track, we don't need effects since it's just a crossfade target
        // Direct connection is fine
        nextSourceRef.current.connect(nextGainRef.current);
        nextGainRef.current.connect(nextCompressorRef.current);
        nextCompressorRef.current.connect(context.destination);

        // Start with gain at tiny value (avoids pops)
        nextGainRef.current.gain.value = 0.001;

        // IMPORTANT: Set audio element volume to 1 so Web Audio gain controls the volume
        nextAudioRef.current.volume = 1;

        nextConnectedRef.current = true;
        console.log('🎧 DJ MIND: Next track Web Audio initialized');
      }
    } catch (error) {
      console.error('🎧 DJ MIND: Error initializing Web Audio connections:', error);
    }
  };

  // Declare event handlers at component level so they can be reused
  const handleLoadStart = () => {
    console.log('🎧 DJ MIND: loadstart event - beginning to load audio');
    updateState((prev) => ({ ...prev, isLoading: true }));
  };

  const handleCanPlay = async () => {
    console.log('🎧 DJ MIND: canplay event - audio can start playing');
    updateState((prev) => ({ ...prev, isLoading: false }));

    // Initialize Web Audio connections if in DJ mode and not already connected
    if (
      state.djMode &&
      audioRef.current &&
      !currentConnectedRef.current &&
      audioContextRef.current
    ) {
      // Make sure audio context is running
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      await initializeWebAudioConnections();

      // After connecting, ensure volume is set correctly
      if (currentGainRef.current) {
        const volume = state.isMuted ? 0 : state.volume;
        currentGainRef.current.gain.value = volume;
        audioRef.current.volume = 1; // Element volume must be 1 for Web Audio
      }
    }
  };

  // Fix 1: Use a ref to track current time and only update state periodically
  const currentTimeRef = useRef<number>(0);
  const timeUpdateIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current && stateRef.current) {
      // Update ref immediately for accurate timing
      currentTimeRef.current = audioRef.current.currentTime;

      // Use stateRef to avoid stale closure
      // This can still run frequently for accurate transition timing
      updateTransitionTimer(currentTimeRef.current, stateRef.current);
    }
  }, []);

  // Set up periodic state updates instead of updating on every timeupdate event
  useEffect(() => {
    if (state.isPlaying) {
      // Update state 4 times per second while playing
      timeUpdateIntervalRef.current = setInterval(() => {
        if (Math.abs(currentTimeRef.current - state.currentTime) > 0.25) {
          updateState((prev) => ({ ...prev, currentTime: currentTimeRef.current }));
        }
      }, 250);
    } else {
      // Clear interval when not playing
      if (timeUpdateIntervalRef.current) {
        clearInterval(timeUpdateIntervalRef.current);
        timeUpdateIntervalRef.current = null;
      }
    }

    return () => {
      if (timeUpdateIntervalRef.current) {
        clearInterval(timeUpdateIntervalRef.current);
      }
    };
  }, [state.isPlaying, state.currentTime, updateState]);

  const handleDurationChange = () => {
    if (audioRef.current) {
      updateState((prev) => ({ ...prev, duration: audioRef.current!.duration || 0 }));
    }
  };

  const handleEnded = () => {
    updateState((prev) => ({ ...prev, isPlaying: false }));

    // Use stateRef to get current state values
    const currentState = stateRef.current;
    if (!currentState) return;

    // In DJ mode with auto transition, the transition should have already happened
    // If we reach here in DJ mode, it means the transition didn't trigger properly
    if (currentState.djMode && currentState.autoTransition && currentState.nextTrack) {
      console.log('🎧 DJ MIND: Track ended without transition, starting DJ transition now...');
      // We'll need to trigger the transition manually
      // Since we can't call startCreativeTransition directly, we'll start a basic transition
      if (audioRef.current && nextAudioRef.current && currentState.nextTrack) {
        const streamUrl = `http://localhost:8000/track/${encodeURIComponent(currentState.nextTrack.filepath)}/stream`;
        nextAudioRef.current.src = streamUrl;
        nextAudioRef.current.load();
        nextAudioRef.current
          .play()
          .then(() => {
            // Simple swap without crossfade
            audioRef.current?.pause();
            const tempAudio = audioRef.current;
            audioRef.current = nextAudioRef.current;
            nextAudioRef.current = tempAudio;

            // Get next index based on current state
            let nextIndex = currentState.currentIndex + 1;
            if (nextIndex >= currentState.queue.length) {
              nextIndex = currentState.repeat === 'all' ? 0 : -1;
            }

            if (nextIndex >= 0) {
              setState((prev) => ({
                ...prev,
                currentTrack: currentState.nextTrack!,
                currentIndex: nextIndex,
                isPlaying: true,
                currentTime: 0,
                duration: audioRef.current?.duration || 0,
              }));
            }
          })
          .catch((error) => {
            console.error('🎧 DJ MIND: Error playing next track:', error);
          });
      }
    } else {
      // Normal behavior - advance to next track
      console.log('🎧 DJ MIND: Track ended, advancing to next track...');

      // Get the next track based on current state
      const queue = currentState.queue;
      if (queue.length === 0) return;

      let nextIndex: number;
      if (currentState.repeat === 'one') {
        nextIndex = currentState.currentIndex;
      } else if (currentState.shuffle) {
        const availableIndices = queue
          .map((_, index) => index)
          .filter((index) => index !== currentState.currentIndex);
        nextIndex = availableIndices[Math.floor(Math.random() * availableIndices.length)] || -1;
      } else {
        nextIndex = currentState.currentIndex + 1;
        if (nextIndex >= queue.length) {
          nextIndex = currentState.repeat === 'all' ? 0 : -1;
        }
      }

      if (nextIndex < 0) {
        // No more tracks to play
        setState((prev) => ({ ...prev, isPlaying: false, currentTime: 0 }));
        if (audioRef.current) {
          audioRef.current.currentTime = 0;
        }
        return;
      }

      const nextTrack = queue[nextIndex];
      if (nextTrack && audioRef.current) {
        console.log('🎧 DJ MIND: Auto-playing next track:', {
          track: nextTrack.title || nextTrack.filename,
          position: `${nextIndex + 1}/${queue.length}`,
        });

        setState((prev) => ({
          ...prev,
          currentTrack: nextTrack,
          currentIndex: nextIndex,
          isLoading: true,
          isTransitioning: false,
          currentTime: 0,
          duration: 0,
        }));

        const streamUrl = `http://localhost:8000/track/${encodeURIComponent(nextTrack.filepath)}/stream`;
        audioRef.current.src = streamUrl;
        audioRef.current.load();

        audioRef.current
          .play()
          .then(() => {
            setState((prev) => ({ ...prev, isPlaying: true }));
            console.log('🎧 DJ MIND: Next track playing successfully');
          })
          .catch((error) => {
            console.error('🎧 DJ MIND: Error playing next track:', error);
            setState((prev) => ({ ...prev, isLoading: false, isPlaying: false }));
          });
      }
    }
  };

  const handleError = (e: Event) => {
    console.error('🎧 DJ MIND: Audio error event fired');

    if (audioRef.current) {
      const error = audioRef.current.error;
      const networkState = audioRef.current.networkState;

      console.error('🎧 DJ MIND: Audio error details:', {
        error: error,
        errorCode: error?.code,
        errorMessage: error?.message,
        networkState: networkState,
        networkStateDesc:
          networkState === 0
            ? 'NETWORK_EMPTY'
            : networkState === 1
              ? 'NETWORK_IDLE'
              : networkState === 2
                ? 'NETWORK_LOADING'
                : networkState === 3
                  ? 'NETWORK_NO_SOURCE'
                  : 'UNKNOWN',
        readyState: audioRef.current.readyState,
        src: audioRef.current.src,
        currentSrc: audioRef.current.currentSrc,
        duration: audioRef.current.duration,
        paused: audioRef.current.paused,
      });

      // Check specific error codes
      if (error) {
        switch (error.code) {
          case 1:
            console.error('🎧 DJ MIND: MEDIA_ERR_ABORTED - Fetching process aborted');
            break;
          case 2:
            console.error('🎧 DJ MIND: MEDIA_ERR_NETWORK - Network error occurred');
            break;
          case 3:
            console.error('🎧 DJ MIND: MEDIA_ERR_DECODE - Error decoding media');
            break;
          case 4:
            console.error('🎧 DJ MIND: MEDIA_ERR_SRC_NOT_SUPPORTED - Media format not supported');
            console.error(
              '🎧 DJ MIND: This often means the file does not exist on disk or the server returned a 404'
            );
            // Try to check if it's a 404
            fetch(audioRef.current.src, { method: 'HEAD' })
              .then((response) => {
                if (response.status === 404) {
                  console.error('🎧 DJ MIND: Confirmed - File not found (404) on server');
                } else {
                  console.error('🎧 DJ MIND: Server returned status:', response.status);
                }
              })
              .catch((err) => {
                console.error('🎧 DJ MIND: Could not check server status:', err);
              });
            break;
        }
      }
    }

    updateState((prev) => ({ ...prev, isLoading: false, isPlaying: false }));
  };

  // Helper function to attach event listeners to an audio element
  const attachEventListeners = (audio: HTMLAudioElement) => {
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
  };

  // Helper function to remove event listeners from an audio element
  const removeEventListeners = (audio: HTMLAudioElement) => {
    audio.removeEventListener('loadstart', handleLoadStart);
    audio.removeEventListener('canplay', handleCanPlay);
    audio.removeEventListener('timeupdate', handleTimeUpdate);
    audio.removeEventListener('durationchange', handleDurationChange);
    audio.removeEventListener('ended', handleEnded);
    audio.removeEventListener('error', handleError);
  };

  // Initialize audio elements
  useEffect(() => {
    audioRef.current = new Audio();
    nextAudioRef.current = new Audio();

    const audio = audioRef.current;
    const nextAudio = nextAudioRef.current;

    // Set up audio properties
    audio.preload = 'auto';
    nextAudio.preload = 'auto';
    audio.crossOrigin = 'anonymous';
    nextAudio.crossOrigin = 'anonymous';

    // Attach event listeners to main audio
    attachEventListeners(audio);

    return () => {
      removeEventListeners(audio);

      // Stop playback
      audio.pause();
      nextAudio.pause();

      // Clear timeouts
      if (transitionTimeoutRef.current) {
        clearTimeout(transitionTimeoutRef.current);
      }
      if (transitionIntervalRef.current) {
        clearInterval(transitionIntervalRef.current);
      }

      // Note: We don't close the audio context or disconnect nodes
      // because that would require recreating everything if the component remounts
    };
  }, []);

  // Update audio volume and mute state
  useEffect(() => {
    if (audioRef.current) {
      if (state.djMode && currentGainRef.current && currentConnectedRef.current) {
        // Use Web Audio API gain when in DJ mode and connected
        const volume = state.isMuted ? 0 : state.volume;
        currentGainRef.current.gain.value = volume;
        // Ensure audio element volume is 1 so Web Audio controls it
        audioRef.current.volume = 1;
      } else if (state.djMode && !currentConnectedRef.current) {
        // In DJ mode but not connected yet - keep element volume at 1
        audioRef.current.volume = 1;
      } else {
        // Use regular audio element volume
        audioRef.current.volume = state.isMuted ? 0 : state.volume;
      }
    }
  }, [state.volume, state.isMuted, state.djMode]);

  // Fix 4: Enhanced useEffect to handle nextTrack initialization properly
  const previousNextTrackRef = useRef<string | null>(null);

  useEffect(() => {
    if (state.djMode && state.queue.length > 0 && state.currentIndex >= 0) {
      const nextIndex = getNextTrackIndex();
      const nextTrack = nextIndex >= 0 ? state.queue[nextIndex] : null;

      // Use ref to track previous value instead of reading from state
      const nextTrackPath = nextTrack?.filepath || null;
      const hasChanged = nextTrackPath !== previousNextTrackRef.current;

      if (hasChanged) {
        previousNextTrackRef.current = nextTrackPath;
        console.log('🎧 DJ MIND: Planning next track...', {
          current: state.currentTrack?.title || state.currentTrack?.filename || 'None',
          next: nextTrack?.title || nextTrack?.filename || 'None',
          nextIndex,
          queueLength: state.queue.length,
          shuffle: state.shuffle,
          repeat: state.repeat,
        });

        // No need to clean up connections anymore - they're permanent

        // Preload next track if it exists
        if (nextAudioRef.current && nextTrack) {
          nextAudioRef.current.src = `http://localhost:8000/track/${encodeURIComponent(nextTrack.filepath)}/stream`;
          nextAudioRef.current.load();
          console.log('🎧 DJ MIND: Next track preloaded');

          // REMOVED: Automatic hot cue import to prevent unwanted track analysis
          // Hot cues should only be imported manually when explicitly requested
          // This prevents "Failed to analyze track" errors during basic playback
        }

        // Only setup effects chain if DJ mode is active and audio context exists
        if (state.djMode && audioContextRef.current) {
          createEffectsChain();
        }

        updateState((prev) => ({ ...prev, nextTrack }));
      }
    } else if (!state.djMode && previousNextTrackRef.current !== null) {
      // Clear nextTrack when DJ mode is disabled
      previousNextTrackRef.current = null;
      updateState((prev) => ({ ...prev, nextTrack: null }));
    }
  }, [state.queue, state.currentIndex, state.shuffle, state.repeat, state.djMode, updateState]); // Removed state.currentTrack from dependencies

  const getNextTrackIndex = (): number => {
    const currentState = stateRef.current || state;
    if (currentState.queue.length === 0) return -1;

    if (currentState.repeat === 'one') {
      return currentState.currentIndex;
    } else if (currentState.shuffle) {
      const availableIndices = currentState.queue
        .map((_, index) => index)
        .filter((index) => index !== currentState.currentIndex);
      return availableIndices[Math.floor(Math.random() * availableIndices.length)] || -1;
    } else {
      const nextIndex = currentState.currentIndex + 1;
      if (nextIndex >= currentState.queue.length) {
        return currentState.repeat === 'all' ? 0 : -1;
      }
      return nextIndex;
    }
  };

  // Fix 2: Update transition timer to accept parameters and avoid stale state
  const lastTransitionTimerUpdateRef = useRef<number>(0);
  const timeUntilTransitionRef = useRef<number>(0);

  const updateTransitionTimer = useCallback(
    (currentTime: number, currentState: AudioPlayerState) => {
      if (
        !audioRef.current ||
        !currentState.djMode ||
        !currentState.autoTransition ||
        currentState.isTransitioning
      )
        return;

      const duration = currentState.duration;

      if (duration > 0) {
        const now = Date.now();
        const shouldUpdateState = now - lastTransitionTimerUpdateRef.current > 1000; // Update once per second

        if (currentState.mixMode === 'interval') {
          // Fixed interval mixing
          const timeSinceStart = currentTime;
          const nextMixTime =
            Math.ceil(timeSinceStart / currentState.mixInterval) * currentState.mixInterval;
          const timeUntilTransition = nextMixTime - timeSinceStart;

          // Always update ref
          timeUntilTransitionRef.current = timeUntilTransition;

          if (
            shouldUpdateState &&
            Math.abs(timeUntilTransition - currentState.timeUntilTransition) > 0.5
          ) {
            lastTransitionTimerUpdateRef.current = now;
            updateState((prev) => ({ ...prev, timeUntilTransition }));
          }

          // Fix 3: Add proper transition locking and nextTrack check
          if (
            timeUntilTransition <= 0.5 &&
            currentState.nextTrack &&
            !currentState.isTransitioning
          ) {
            console.log('🎧 DJ MIND: ⏰ INTERVAL MIX TIME! Starting transition...', {
              interval: currentState.mixInterval,
              currentTime: timeSinceStart.toFixed(1),
              mixPoint: nextMixTime.toFixed(1),
            });

            // Call the transition with proper state checks
            triggerAutoTransition(currentState);
          }
        } else if (currentState.mixMode === 'track-end') {
          // Original track-end mixing
          const optimalTransitionTime =
            currentState.currentTrack && currentState.nextTrack
              ? calculateBeatAlignedTransition(currentState.currentTrack, currentState.nextTrack)
              : currentState.transitionTime;

          const timeUntilTransition = duration - currentTime - optimalTransitionTime;

          // Always update ref
          timeUntilTransitionRef.current = timeUntilTransition;

          if (
            shouldUpdateState &&
            Math.abs(timeUntilTransition - currentState.timeUntilTransition) > 0.5
          ) {
            lastTransitionTimerUpdateRef.current = now;
            updateState((prev) => ({ ...prev, timeUntilTransition }));
          }

          if (timeUntilTransition <= 0 && currentState.nextTrack && !currentState.isTransitioning) {
            console.log('🎧 DJ MIND: ⏰ TRACK-END TRANSITION TIME! Starting transition...');

            // Call the transition with proper state checks
            triggerAutoTransition(currentState);
          }
        } else if (currentState.mixMode === 'hot-cue') {
          // Simple hot cue-based mixing
          const currentTrackHotCues =
            currentState.hotCues[currentState.currentTrack?.filepath || ''] || [];

          if (currentTrackHotCues.length > 0) {
            // Find a good outro hot cue in the last part of the track
            const outroHotCues = currentTrackHotCues.filter(
              (cue) => cue.time > duration * 0.7 && cue.time < duration - 8 // Last 30% but not too close to end
            );

            if (outroHotCues.length > 0) {
              // Use the last outro hot cue as transition point
              const outroHotCue = outroHotCues[outroHotCues.length - 1];
              const timeUntilHotCue = outroHotCue.time - currentTime;

              // Always update ref
              timeUntilTransitionRef.current = timeUntilHotCue;

              if (
                shouldUpdateState &&
                Math.abs(timeUntilHotCue - currentState.timeUntilTransition) > 0.5
              ) {
                lastTransitionTimerUpdateRef.current = now;
                updateState((prev) => ({ ...prev, timeUntilTransition: timeUntilHotCue }));
              }

              if (
                timeUntilHotCue <= 1.0 &&
                currentState.nextTrack &&
                !currentState.isTransitioning
              ) {
                console.log('🎧 DJ MIND: ⏰ HOT CUE TRANSITION!', {
                  outroName: outroHotCue.name,
                  outroTime: outroHotCue.time.toFixed(1),
                });
                triggerAutoTransition(currentState);
              }
            } else {
              // No good outro hot cues, use track-end approach
              const timeUntilTransition = duration - currentTime - currentState.transitionTime;

              // Always update ref
              timeUntilTransitionRef.current = timeUntilTransition;

              if (
                shouldUpdateState &&
                Math.abs(timeUntilTransition - currentState.timeUntilTransition) > 0.5
              ) {
                lastTransitionTimerUpdateRef.current = now;
                updateState((prev) => ({ ...prev, timeUntilTransition }));
              }

              if (
                timeUntilTransition <= 0 &&
                currentState.nextTrack &&
                !currentState.isTransitioning
              ) {
                console.log('🎧 DJ MIND: ⏰ HOT CUE MODE - using track-end fallback');
                triggerAutoTransition(currentState);
              }
            }
          } else {
            // No hot cues available, use track-end approach
            const timeUntilTransition = duration - currentTime - currentState.transitionTime;

            // Always update ref
            timeUntilTransitionRef.current = timeUntilTransition;

            if (
              shouldUpdateState &&
              Math.abs(timeUntilTransition - currentState.timeUntilTransition) > 0.5
            ) {
              lastTransitionTimerUpdateRef.current = now;
              updateState((prev) => ({ ...prev, timeUntilTransition }));
            }

            if (
              timeUntilTransition <= 0 &&
              currentState.nextTrack &&
              !currentState.isTransitioning
            ) {
              console.log('🎧 DJ MIND: ⏰ HOT CUE MODE - no hot cues, using track-end fallback');
              triggerAutoTransition(currentState);
            }
          }
        }
      }
    },
    [updateState]
  );

  // Fixed transition trigger with proper race condition prevention
  const triggerAutoTransition = (currentState: AudioPlayerState) => {
    // Double-check state to prevent race conditions
    if (!currentState.djMode) {
      console.log('🎧 DJ MIND: Cannot trigger transition - DJ mode disabled');
      return;
    }

    if (!currentState.nextTrack) {
      console.log('🎧 DJ MIND: Cannot trigger transition - no next track');
      return;
    }

    if (currentState.isTransitioning) {
      console.log('🎧 DJ MIND: Cannot trigger transition - already transitioning');
      return;
    }

    console.log('🎧 DJ MIND: 🚀 AUTO TRANSITION TRIGGERED!', {
      currentTrack: currentState.currentTrack?.title || currentState.currentTrack?.filename,
      nextTrack: currentState.nextTrack?.title || currentState.nextTrack?.filename,
      mode: currentState.mixMode,
    });

    // Set transitioning state and immediately start transition
    updateState((prev) => {
      // Double-check again during state update
      if (prev.isTransitioning) {
        console.log('🎧 DJ MIND: Transition blocked - already in progress');
        return prev; // No change
      }

      return { ...prev, isTransitioning: true };
    });

    // Start transition immediately - no delay needed
    startTransition();
  };

  // New function to set mix interval
  const setMixInterval = useCallback(
    (seconds: number) => {
      // Only allow 30, 60, or 90 second intervals
      const validIntervals = [30, 60, 90];
      const newInterval = validIntervals.includes(seconds) ? seconds : 60;

      console.log('🎧 DJ MIND: Mix interval changed', {
        from: state.mixInterval,
        to: newInterval,
        mode: state.mixMode,
        meaning:
          state.mixMode === 'interval'
            ? `Will auto-mix every ${newInterval} seconds`
            : `Will start crossfade ${newInterval} seconds before track ends`,
      });

      setState((prev) => ({
        ...prev,
        mixInterval: newInterval,
        // Reset time calculation when interval changes
        timeUntilTransition: newInterval,
      }));
    },
    [updateState]
  );

  // New function to toggle mix mode
  const setMixMode = useCallback(
    (mode: 'interval' | 'track-end' | 'hot-cue') => {
      console.log('🎧 DJ MIND: Mix mode changed', {
        from: state.mixMode,
        to: mode,
        interval: state.mixInterval,
        transitionTime: state.transitionTime,
      });
      setState((prev) => ({ ...prev, mixMode: mode }));
    },
    [state.mixInterval, state.transitionTime]
  );

  const setTransitionEffectPlan = useCallback(
    (plan: TransitionEffectPlan | null) => {
      updateState((prev) => ({ ...prev, transitionEffectPlan: plan }));
    },
    [updateState]
  );

  const startTransition = async () => {
    if (
      !audioRef.current ||
      !nextAudioRef.current ||
      !stateRef.current?.nextTrack ||
      !audioContextRef.current
    ) {
      console.error('🎧 DJ MIND: Cannot start transition - missing required elements');
      updateState((prev) => ({ ...prev, isTransitioning: false }));
      return;
    }

    const currentState = stateRef.current;

    console.log('🎧 DJ MIND: 🔥 STARTING TRANSITION SEQUENCE 🔥', {
      currentTrack: currentState.currentTrack?.title || currentState.currentTrack?.filename,
      nextTrack: currentState.nextTrack?.title || currentState.nextTrack?.filename,
      currentTime: Math.floor(audioRef.current.currentTime),
      duration: Math.floor(currentState.duration),
      crossfadeDuration: currentState.crossfadeDuration,
      useWebAudio: !!audioContextRef.current,
    });

    // Ensure we're in transitioning state
    if (!currentState.isTransitioning) {
      updateState((prev) => ({ ...prev, isTransitioning: true, transitionProgress: 0 }));
    }

    try {
      const context = audioContextRef.current;

      // Ensure context is running
      if (context.state === 'suspended') {
        await context.resume();
        console.log('🎧 DJ MIND: Audio context resumed for transition');
      }

      // Pre-buffer next track to avoid stuttering
      if (nextAudioRef.current.readyState < 3) {
        // HAVE_FUTURE_DATA
        console.log('🎧 DJ MIND: Pre-buffering next track...');
        await new Promise((resolve, reject) => {
          const handleCanPlay = () => {
            nextAudioRef.current?.removeEventListener('canplay', handleCanPlay);
            nextAudioRef.current?.removeEventListener('error', handleError);
            resolve(true);
          };
          const handleError = () => {
            nextAudioRef.current?.removeEventListener('canplay', handleCanPlay);
            nextAudioRef.current?.removeEventListener('error', handleError);
            reject(new Error('Failed to buffer next track'));
          };
          nextAudioRef.current?.addEventListener('canplay', handleCanPlay);
          nextAudioRef.current?.addEventListener('error', handleError);

          // Timeout after 5 seconds
          setTimeout(() => {
            nextAudioRef.current?.removeEventListener('canplay', handleCanPlay);
            nextAudioRef.current?.removeEventListener('error', handleError);
            resolve(true); // Continue anyway
          }, 5000);
        });
      }

      // Ensure Web Audio is initialized
      if (!currentConnectedRef.current || !nextConnectedRef.current) {
        console.log('🎧 DJ MIND: Initializing Web Audio connections...');
        await initializeWebAudioConnections();
      }

      // Verify gain nodes exist
      if (!currentGainRef.current || !nextGainRef.current) {
        console.error('🎧 DJ MIND: Missing gain nodes, falling back to simple crossfade');
        await startSimpleCrossfade();
        return;
      }

      console.log('🎧 DJ MIND: Starting next track...');

      // Reset next track gain to tiny value before starting (avoids pops)
      nextGainRef.current.gain.value = 0.001;

      // Find the best musical entry point for ALL transitions
      if (currentState.nextTrack) {
        const nextTrackHotCues = currentState.hotCues[currentState.nextTrack.filepath] || [];

        console.log('🎧 DJ MIND: Checking hot cues for transition', {
          track: currentState.nextTrack.title || currentState.nextTrack.filename,
          hotCueCount: nextTrackHotCues.length,
          hotCues: nextTrackHotCues.map((c) => ({ name: c.name, time: c.time, type: c.type })),
        });

        if (nextTrackHotCues.length > 0) {
          // Simple, reliable hot cue selection: prefer musical entry points
          let bestIntroHotCue = null;

          // Priority 1: Look for intro/verse markers in first 45 seconds
          for (const cue of nextTrackHotCues) {
            const cueName = cue.name.toLowerCase();
            if (cue.time >= 8 && cue.time <= 45) {
              if (
                cueName.includes('intro') ||
                cueName.includes('verse') ||
                cueName.includes('start')
              ) {
                bestIntroHotCue = cue;
                break; // Take the first good match
              }
            }
          }

          // Priority 2: Any phrase-type cue in reasonable range
          if (!bestIntroHotCue) {
            for (const cue of nextTrackHotCues) {
              if (cue.time >= 8 && cue.time <= 30 && cue.type === 'phrase') {
                bestIntroHotCue = cue;
                break;
              }
            }
          }

          // Priority 3: Earliest cue that's not too early
          if (!bestIntroHotCue) {
            const goodCues = nextTrackHotCues.filter((cue) => cue.time >= 8 && cue.time <= 20);
            if (goodCues.length > 0) {
              bestIntroHotCue = goodCues[0]; // Take earliest
            }
          }

          if (bestIntroHotCue) {
            nextAudioRef.current.currentTime = bestIntroHotCue.time;
            console.log('🎧 DJ MIND: 🎯 Starting next track at hot cue', {
              cueName: bestIntroHotCue.name,
              cueTime: bestIntroHotCue.time.toFixed(1),
              cueType: bestIntroHotCue.type,
              mixMode: currentState.mixMode,
            });
          } else {
            // No good hot cue found, start at a sensible default
            nextAudioRef.current.currentTime = 8; // 8 seconds in
            console.log('🎧 DJ MIND: No suitable hot cue, starting at 8 seconds');
          }
        } else {
          // No hot cues available, start at beginning (skip silence)
          nextAudioRef.current.currentTime = 4;
          console.log('🎧 DJ MIND: No hot cues available, starting at 4 seconds');
        }
      }

      // Set up Web Audio gain BEFORE starting playback to prevent stutter
      const audioContext = audioContextRef.current!;
      const now = audioContext.currentTime;

      // Verify gain nodes exist and pre-configure next track gain
      if (!currentGainRef.current || !nextGainRef.current) {
        console.error('🎧 DJ MIND: ❌ Missing gain nodes for crossfade');
        await startSimpleCrossfade();
        return;
      }

      // Clear any existing automation and set initial values BEFORE playback
      // Add small offset to prevent glitches
      const startTime = now + 0.05; // 50ms offset for smoother transitions
      currentGainRef.current.gain.cancelScheduledValues(startTime);
      nextGainRef.current.gain.cancelScheduledValues(startTime);

      const currentVolume = currentState.volume;
      // Get the actual current gain value (in case user seeked)
      const actualCurrentGain = currentGainRef.current.gain.value;
      
      // Set initial values with proper timing
      currentGainRef.current.gain.setValueAtTime(actualCurrentGain, now);
      nextGainRef.current.gain.setValueAtTime(0.0001, now); // Even smaller initial value

      // IMPORTANT: Set element volume to 0 as a safety measure
      nextAudioRef.current.volume = 0;

      // Start playing next track
      await nextAudioRef.current.play();

      // Now set the element volume to 1 and let Web Audio control gain
      nextAudioRef.current.volume = 1;

      // Give a moment for audio to stabilize and prevent clicks
      await new Promise((resolve) => setTimeout(resolve, 100));

      console.log('🎧 DJ MIND: Next track playing silently, beginning smooth crossfade...');

      // Smooth crossfade using reliable automation
      const fadeTime = currentState.crossfadeDuration;

      // Schedule automated transition effects if we have a plan
      if (currentState.transitionEffectPlan) {
        console.log(
          '🎧 DJ MIND: 🎨 Applying transition effect plan:',
          currentState.transitionEffectPlan
        );

        // Define local trigger functions that apply effects with the right duration
        const triggerFilterEffect = (intensity: number, duration: number) => {
          applyTransitionEffect({
            type: 'filter',
            intensity,
            duration,
          });
        };

        const triggerEchoEffect = (intensity: number, duration: number) => {
          applyTransitionEffect({
            type: 'echo',
            intensity,
            duration,
          });
        };

        currentState.transitionEffectPlan.effects.forEach((effect) => {
          setTimeout(() => {
            // Use the appropriate trigger function with custom duration
            switch (effect.type) {
              case 'filter':
                triggerFilterEffect(effect.intensity, effect.duration);
                break;
              case 'echo':
                triggerEchoEffect(effect.intensity, effect.duration);
                break;
              default:
                applyTransitionEffect({
                  type: effect.type as any,
                  intensity: effect.intensity,
                  duration: effect.duration,
                });
            }
          }, effect.start_at * 1000);
        });

        // Schedule cleanup after all effects are done
        const maxEffectEnd = Math.max(
          ...currentState.transitionEffectPlan.effects.map((e) => e.start_at + e.duration)
        );
        setTimeout(
          () => {
            console.log('🎧 DJ MIND: 🧹 Cleaning up effects chain');
            // Reconnect audio chain without effects
            if (currentGainRef.current && currentCompressorRef.current) {
              try {
                currentGainRef.current.disconnect();
                currentGainRef.current.connect(currentCompressorRef.current);
              } catch (e) {
                console.warn('🎧 DJ MIND: Error cleaning up effects:', e);
              }
            }
            setState((prev) => ({ ...prev, currentEffects: [] }));
          },
          maxEffectEnd * 1000 + 500
        ); // Add 500ms buffer
      }

      console.log('🎧 DJ MIND: Starting smooth crossfade', {
        fadeTime,
        startTime: now.toFixed(3),
        endTime: (now + fadeTime).toFixed(3),
      });

      // Schedule smooth crossfade with better timing
      const fadeStartTime = now + 0.1; // Small delay to ensure stability
      const fadeEndTime = fadeStartTime + fadeTime;

      // Set current values at fade start time
      currentGainRef.current.gain.setValueAtTime(actualCurrentGain, fadeStartTime);
      nextGainRef.current.gain.setValueAtTime(0.0001, fadeStartTime);

      // Use setTargetAtTime for smoother, more natural curves
      // Time constant = duration / 5 for a good curve shape
      const timeConstant = fadeTime / 5;
      
      // Fade out current track with exponential-like curve
      currentGainRef.current.gain.setTargetAtTime(0.0001, fadeStartTime, timeConstant);
      
      // Fade in next track with exponential-like curve
      nextGainRef.current.gain.setTargetAtTime(currentVolume, fadeStartTime, timeConstant);

      // Add final linear ramp to ensure we reach exact values
      currentGainRef.current.gain.linearRampToValueAtTime(0.0001, fadeEndTime);
      nextGainRef.current.gain.linearRampToValueAtTime(currentVolume, fadeEndTime);

      console.log('🎧 DJ MIND: ✅ Smooth crossfade automation scheduled', {
        currentStart: actualCurrentGain,
        currentEnd: 0.0001,
        nextStart: 0.0001,
        nextEnd: currentVolume,
        duration: fadeTime,
        timeConstant: timeConstant.toFixed(2),
      });

      // Simple completion timer based on crossfade duration
      setTimeout(
        () => {
          console.log('🎧 DJ MIND: ✅ Crossfade complete, finalizing transition...');
          completeTransition();
        },
        fadeTime * 1000 + 100
      ); // Add small buffer

      // Update UI progress during crossfade
      const progressSteps = 20;
      const progressInterval = (fadeTime * 1000) / progressSteps;
      let progressStep = 0;

      const progressTimer = setInterval(() => {
        progressStep++;
        const progress = Math.min(progressStep / progressSteps, 1);
        updateState((prev) => ({ ...prev, transitionProgress: progress }));

        if (progress >= 1) {
          clearInterval(progressTimer);
        }
      }, progressInterval);
    } catch (error) {
      console.error('🎧 DJ MIND: ❌ ERROR during Web Audio transition:', error);
      console.log('🎧 DJ MIND: Falling back to simple crossfade...');
      await startSimpleCrossfade();
    }
  };

  // Fallback crossfade without Web Audio API
  const startSimpleCrossfade = async () => {
    const currentState = stateRef.current;
    if (!audioRef.current || !nextAudioRef.current || !currentState?.nextTrack) return;

    console.log('🎧 DJ MIND: Using fallback volume crossfade');

    try {
      // Ensure next track is loaded
      if (nextAudioRef.current.readyState < 3) {
        console.log('🎧 DJ MIND: Waiting for next track to load...');
        await new Promise((resolve) => {
          const handleCanPlay = () => {
            nextAudioRef.current?.removeEventListener('canplaythrough', handleCanPlay);
            resolve(true);
          };
          nextAudioRef.current?.addEventListener('canplaythrough', handleCanPlay);
          setTimeout(() => resolve(true), 3000); // Timeout after 3 seconds
        });
      }

      // Start playing next track at 0 volume
      nextAudioRef.current.volume = 0;
      await nextAudioRef.current.play();

      console.log('🎧 DJ MIND: Next track playing, beginning volume crossfade...');

      const duration = currentState.crossfadeDuration * 1000; // Convert to ms
      const steps = 30; // 30 steps for smooth fade
      const stepDuration = duration / steps;
      let currentStep = 0;

      const fadeInterval = setInterval(() => {
        currentStep++;
        const progress = currentStep / steps;

        // Calculate volumes
        const currentVolume = (1 - progress) * currentState.volume;
        const nextVolume = progress * currentState.volume;

        // Apply volumes
        if (audioRef.current) {
          audioRef.current.volume = Math.max(0, currentVolume);
        }
        if (nextAudioRef.current) {
          nextAudioRef.current.volume = Math.min(1, nextVolume);
        }

        // Update progress
        updateState((prev) => ({ ...prev, transitionProgress: progress }));

        if (currentStep >= steps) {
          clearInterval(fadeInterval);
          console.log('🎧 DJ MIND: Simple crossfade complete');
          completeTransition();
        }
      }, stepDuration);
    } catch (error) {
      console.error('🎧 DJ MIND: Error in simple crossfade:', error);
      // Try to complete transition anyway
      completeTransition();
    }
  };

  const completeTransition = () => {
    // Use stateRef to get the most current state
    const currentState = stateRef.current;
    if (!audioRef.current || !nextAudioRef.current || !currentState?.nextTrack) return;

    console.log('🎧 DJ MIND: 🎉 TRANSITION COMPLETE! 🎉', {
      previousTrack: currentState.currentTrack?.title || currentState.currentTrack?.filename,
      newCurrentTrack: currentState.nextTrack.title || currentState.nextTrack.filename,
      queuePosition: `${getNextTrackIndex() + 1}/${currentState.queue.length}`,
    });

    // Don't pause - let the crossfade handle the transition smoothly
    console.log('🎧 DJ MIND: Swapping audio elements seamlessly');

    // Store references for swapping
    const currentAudio = audioRef.current;

    // Remove event listeners from current audio element
    removeEventListeners(currentAudio);

    // Swap audio elements
    const tempAudio = audioRef.current;
    audioRef.current = nextAudioRef.current;
    nextAudioRef.current = tempAudio;

    // Add event listeners to the new current audio element
    attachEventListeners(audioRef.current);

    // Swap Web Audio connection states
    const tempConnected = currentConnectedRef.current;
    currentConnectedRef.current = nextConnectedRef.current;
    nextConnectedRef.current = tempConnected;

    // Swap Web Audio API references
    const tempSource = currentSourceRef.current;
    const tempGain = currentGainRef.current;
    const tempCompressor = currentCompressorRef.current;

    currentSourceRef.current = nextSourceRef.current;
    currentGainRef.current = nextGainRef.current;
    currentCompressorRef.current = nextCompressorRef.current;

    nextSourceRef.current = tempSource;
    nextGainRef.current = tempGain;
    nextCompressorRef.current = tempCompressor;

    console.log('🎧 DJ MIND: Audio elements and Web Audio connections swapped');

    // Calculate the next track index based on current state
    const nextIndex = getNextTrackIndex();

    // Update state with the new current track and reset transition state
    setState((prev) => ({
      ...prev,
      currentTrack: currentState.nextTrack,
      currentIndex: nextIndex,
      isTransitioning: false,
      transitionProgress: 0,
      currentTime: 0,
      duration: audioRef.current?.duration || 0,
      nextTrack: null, // Clear nextTrack so it gets recalculated
    }));

    // Reset volumes and gains with proper error handling
    try {
      if (currentState.djMode && currentGainRef.current && audioContextRef.current) {
        // In DJ mode, ensure gain is set correctly
        const now = audioContextRef.current.currentTime;
        currentGainRef.current.gain.cancelScheduledValues(now);
        currentGainRef.current.gain.setValueAtTime(currentState.volume, now);
        audioRef.current.volume = 1; // Keep element volume at 1, control through gain
        console.log('🎧 DJ MIND: Reset Web Audio gain to', currentState.volume);
      } else {
        // Normal mode, use element volume
        audioRef.current.volume = currentState.volume;
        console.log('🎧 DJ MIND: Reset element volume to', currentState.volume);
      }

      // Prepare next audio element for reuse
      if (nextAudioRef.current) {
        nextAudioRef.current.pause();
        nextAudioRef.current.currentTime = 0;
        nextAudioRef.current.volume = 1; // Reset to default
      }

      // Reset next track gain if it exists
      if (nextGainRef.current && audioContextRef.current) {
        const now = audioContextRef.current.currentTime;
        nextGainRef.current.gain.cancelScheduledValues(now);
        nextGainRef.current.gain.setValueAtTime(0, now);
      }
    } catch (error) {
      console.error('🎧 DJ MIND: Error resetting audio levels:', error);
    }

    console.log('🎧 DJ MIND: Volumes and gains reset, ready for next transition');

    // Set up the next track for future transition
    setTimeout(() => {
      const newState = stateRef.current;
      if (newState?.djMode && newState.queue.length > 0) {
        const upcomingNextIndex = getNextTrackIndex();
        const upcomingNextTrack = upcomingNextIndex >= 0 ? newState.queue[upcomingNextIndex] : null;

        if (upcomingNextTrack && nextAudioRef.current) {
          console.log('🎧 DJ MIND: Setting up next track after transition:', {
            track: upcomingNextTrack.title || upcomingNextTrack.filename,
            artist: upcomingNextTrack.artist || 'Unknown Artist',
            willTransitionIn: `${newState.mixInterval || newState.transitionTime} seconds`,
          });

          // No need to clean up - connections are permanent

          // Preload the new next track
          nextAudioRef.current.src = `http://localhost:8000/track/${encodeURIComponent(upcomingNextTrack.filepath)}/stream`;
          nextAudioRef.current.load();
          console.log('🎧 DJ MIND: New next track preloaded');

          // Update state with the new next track
          setState((prev) => ({ ...prev, nextTrack: upcomingNextTrack }));
        }
      }
    }, 100);
  };

  const playTrack = async (track: Track, queue: Track[] = []) => {
    if (!audioRef.current) return;

    const newQueue = queue.length > 0 ? queue : [track];
    const trackIndex = newQueue.findIndex((t) => t.filepath === track.filepath);

    // DJ MIND LOG: Track playback
    console.log('🎧 DJ MIND: Starting new track...', {
      track: track.title || track.filename,
      artist: track.artist || 'Unknown Artist',
      queuePosition: `${trackIndex + 1}/${newQueue.length}`,
      djMode: state.djMode,
      autoTransition: state.autoTransition,
      shuffle: state.shuffle,
      repeat: state.repeat,
    });

    setState((prev) => ({
      ...prev,
      currentTrack: track,
      queue: newQueue,
      currentIndex: trackIndex >= 0 ? trackIndex : 0,
      isLoading: true,
      isTransitioning: false,
      currentTime: 0,
      duration: 0,
    }));

    const streamUrl = musicService.getStreamUrl(track.filepath);

    // Ensure audio element is properly configured
    audioRef.current.crossOrigin = 'anonymous';
    audioRef.current.src = streamUrl;

    // Must call load() after setting src
    audioRef.current.load();

    // Simple play with basic error handling
    const playWhenReady = () => {
      if (!audioRef.current) return;

      audioRef.current
        .play()
        .then(() => {
          console.log('🎧 DJ MIND: ✅ Track playing successfully');
          updateState((prev) => ({ ...prev, isPlaying: true, isLoading: false }));
        })
        .catch((error) => {
          console.error('🎧 DJ MIND: Play error:', error.name, error.message);

          // If NotSupportedError, it might be because we're trying to play too early
          if (
            error.name === 'NotSupportedError' &&
            audioRef.current &&
            audioRef.current.readyState < 2
          ) {
            // Don't update state yet, wait for canplay
          } else {
            updateState((prev) => ({ ...prev, isLoading: false, isPlaying: false }));
          }
        });
    };

    // Use canplay event to know when audio is ready
    const handleCanPlayOnce = () => {
      if (audioRef.current) {
        audioRef.current.removeEventListener('canplay', handleCanPlayOnce);
        playWhenReady();
      }
    };

    // Listen for when audio is ready
    audioRef.current.addEventListener('canplay', handleCanPlayOnce);

    // Try to play immediately in case audio loads quickly
    if (audioRef.current.readyState >= 2) {
      playWhenReady();
    }
  };

  const pause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setState((prev) => ({ ...prev, isPlaying: false }));
    }
  };

  const resume = () => {
    if (audioRef.current) {
      audioRef.current
        .play()
        .then(() => {
          setState((prev) => ({ ...prev, isPlaying: true }));
        })
        .catch((error) => {
          console.error('Error resuming track:', error);
        });
    }
  };

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setState((prev) => ({
        ...prev,
        isPlaying: false,
        currentTime: 0,
      }));
    }
  };

  const skipToNextFn = () => {
    if (state.queue.length === 0) return;

    const nextIndex = getNextTrackIndex();
    if (nextIndex < 0) {
      stop();
      return;
    }

    const nextTrack = state.queue[nextIndex];
    if (nextTrack) {
      playTrack(nextTrack, state.queue);
    }
  };

  const previousTrack = () => {
    if (state.queue.length === 0) return;

    // If we're more than 3 seconds into the track, restart it
    if (state.currentTime > 3) {
      seekTo(0);
      return;
    }

    let prevIndex: number;

    if (state.shuffle) {
      const availableIndices = state.queue
        .map((_, index) => index)
        .filter((index) => index !== state.currentIndex);
      prevIndex = availableIndices[Math.floor(Math.random() * availableIndices.length)] || 0;
    } else {
      prevIndex = state.currentIndex - 1;
      if (prevIndex < 0) {
        if (state.repeat === 'all') {
          prevIndex = state.queue.length - 1;
        } else {
          prevIndex = 0;
        }
      }
    }

    const prevTrack = state.queue[prevIndex];
    if (prevTrack) {
      playTrack(prevTrack, state.queue);
    }
  };

  const seekTo = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setState((prev) => ({ ...prev, currentTime: time }));
    }
  };

  const setVolume = (volume: number) => {
    setState((prev) => ({ ...prev, volume: Math.max(0, Math.min(1, volume)) }));
  };

  const toggleMute = () => {
    setState((prev) => ({ ...prev, isMuted: !prev.isMuted }));
  };

  const addToQueue = (track: Track) => {
    setState((prev) => ({ ...prev, queue: [...prev.queue, track] }));
  };

  const removeFromQueue = (index: number) => {
    setState((prev) => {
      const newQueue = prev.queue.filter((_, i) => i !== index);
      const newCurrentIndex = index < prev.currentIndex ? prev.currentIndex - 1 : prev.currentIndex;

      return {
        ...prev,
        queue: newQueue,
        currentIndex: newCurrentIndex,
      };
    });
  };

  const clearQueue = () => {
    setState((prev) => ({ ...prev, queue: [], currentIndex: -1 }));
  };

  const moveTrackInQueue = (fromIndex: number, toIndex: number) => {
    setState((prev) => {
      const newQueue = [...prev.queue];
      const [movedTrack] = newQueue.splice(fromIndex, 1);
      newQueue.splice(toIndex, 0, movedTrack);

      // Adjust current index if needed
      let newCurrentIndex = prev.currentIndex;
      if (fromIndex === prev.currentIndex) {
        newCurrentIndex = toIndex;
      } else if (fromIndex < prev.currentIndex && toIndex >= prev.currentIndex) {
        newCurrentIndex--;
      } else if (fromIndex > prev.currentIndex && toIndex <= prev.currentIndex) {
        newCurrentIndex++;
      }

      return {
        ...prev,
        queue: newQueue,
        currentIndex: newCurrentIndex,
      };
    });
  };

  const setRepeat = (mode: 'none' | 'one' | 'all') => {
    setState((prev) => ({ ...prev, repeat: mode }));
  };

  const toggleShuffle = () => {
    setState((prev) => ({ ...prev, shuffle: !prev.shuffle }));
  };

  // Fix 5: Ensure nextTrack is set immediately when DJ mode is enabled
  const toggleDjMode = async () => {
    const newDjMode = !state.djMode;
    console.log(`🎧 DJ MIND: DJ Mode ${newDjMode ? 'ACTIVATED' : 'DEACTIVATED'}`, {
      currentTrack: state.currentTrack?.title || state.currentTrack?.filename || 'None',
      queueLength: state.queue.length,
      autoTransition: state.autoTransition,
      transitionTime: state.transitionTime,
      crossfadeDuration: state.crossfadeDuration,
    });

    // If enabling DJ mode and audio is currently playing, we need to handle the transition
    if (newDjMode && state.isPlaying) {
      console.log('🎧 DJ MIND: Transitioning from regular playback to DJ mode...');

      // Store current playback state
      const currentTime = audioRef.current?.currentTime || 0;
      const wasPlaying = state.isPlaying;
      const currentTrackToResume = state.currentTrack;

      // Pause current playback
      if (audioRef.current) {
        audioRef.current.pause();
      }

      // Reset audio elements to disconnect them from regular playback
      if (audioRef.current && currentConnectedRef.current === false) {
        // Create new audio elements to avoid conflicts
        const oldAudio = audioRef.current;
        const oldNext = nextAudioRef.current;

        // Remove old event listeners
        if (oldAudio) {
          removeEventListeners(oldAudio);
        }

        // Create fresh audio elements
        audioRef.current = new Audio();
        nextAudioRef.current = new Audio();

        // Set up audio properties
        audioRef.current.preload = 'auto';
        nextAudioRef.current.preload = 'auto';
        audioRef.current.crossOrigin = 'anonymous';
        nextAudioRef.current.crossOrigin = 'anonymous';

        // Attach event listeners
        attachEventListeners(audioRef.current);

        console.log('🎧 DJ MIND: Created fresh audio elements for DJ mode');
      }
    }

    // Ensure audio context is initialized when enabling DJ mode
    if (newDjMode && !audioContextRef.current) {
      try {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        console.log('🎧 DJ MIND: Audio context created for DJ mode');

        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume();
          console.log('🎧 DJ MIND: Audio context resumed');
        }

        createEffectsChain();
        console.log('🎧 DJ MIND: Effects chain created');
      } catch (error) {
        console.error('🎧 DJ MIND: Failed to create audio context:', error);
      }
    } else if (newDjMode && audioContextRef.current) {
      // Make sure it's not suspended
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
    }

    setState((prev) => ({ ...prev, djMode: newDjMode }));

    // Initialize Web Audio when enabling DJ mode
    if (newDjMode) {
      // If enabling DJ mode and audio is currently playing, handle transition
      if (state.isPlaying && audioRef.current) {
        audioRef.current.pause();
      }

      // Create fresh audio elements to avoid conflicts
      audioRef.current = new Audio();
      audioRef.current.preload = 'auto';
      audioRef.current.crossOrigin = 'anonymous';
      attachEventListeners(audioRef.current);

      nextAudioRef.current = new Audio();
      nextAudioRef.current.preload = 'auto';
      nextAudioRef.current.crossOrigin = 'anonymous';

      if (audioContextRef.current) {
        // Reset connection flags - connections will be made when audio plays
        currentConnectedRef.current = false;
        nextConnectedRef.current = false;
        currentSourceRef.current = null;
        nextSourceRef.current = null;

        // Don't initialize connections yet - wait for audio to be loaded
        // Connections will be made in handleCanPlay or playTrack

        // If we had a track playing, resume it in DJ mode
        if (state.currentTrack && state.isPlaying) {
          // Reload the track to play through Web Audio
          await playTrack(state.currentTrack, state.queue);
        }
      }
    } else if (!newDjMode && state.djMode) {
      // Disabling DJ mode - need to clean up Web Audio connections
      console.log('🎧 DJ MIND: Cleaning up Web Audio connections...');

      // Store current state if playing
      const wasPlaying = state.isPlaying;
      const currentTrackToResume = state.currentTrack;
      const currentTime = audioRef.current?.currentTime || 0;

      if (wasPlaying && audioRef.current) {
        audioRef.current.pause();
      }

      // Disconnect Web Audio nodes
      try {
        if (currentSourceRef.current) {
          currentSourceRef.current.disconnect();
          currentSourceRef.current = null;
        }
        if (nextSourceRef.current) {
          nextSourceRef.current.disconnect();
          nextSourceRef.current = null;
        }
        if (currentGainRef.current) {
          currentGainRef.current.disconnect();
          currentGainRef.current = null;
        }
        if (nextGainRef.current) {
          nextGainRef.current.disconnect();
          nextGainRef.current = null;
        }
      } catch (error) {
        console.warn('🎧 DJ MIND: Error disconnecting Web Audio nodes:', error);
      }

      // Reset connection flags
      currentConnectedRef.current = false;
      nextConnectedRef.current = false;

      // Create fresh audio elements for regular playback
      const oldAudio = audioRef.current;
      if (oldAudio) {
        removeEventListeners(oldAudio);
      }

      audioRef.current = new Audio();
      audioRef.current.preload = 'auto';
      audioRef.current.crossOrigin = 'anonymous';
      attachEventListeners(audioRef.current);

      console.log('🎧 DJ MIND: Switched back to regular HTML5 audio');

      // Resume playback if we were playing
      if (wasPlaying && currentTrackToResume) {
        console.log('🎧 DJ MIND: Resuming regular playback...');
        await playTrack(currentTrackToResume, state.queue);
        // Try to seek to previous position
        setTimeout(() => {
          if (audioRef.current && currentTime > 0) {
            audioRef.current.currentTime = currentTime;
          }
        }, 100);
      }
    }

    // Set nextTrack when enabling DJ mode
    if (newDjMode) {
      if (state.queue.length > 0 && state.currentIndex >= 0) {
        const nextIndex = getNextTrackIndex();
        const nextTrack = nextIndex >= 0 ? state.queue[nextIndex] : null;

        if (nextTrack && nextAudioRef.current) {
          nextAudioRef.current.src = `http://localhost:8000/track/${encodeURIComponent(nextTrack.filepath)}/stream`;
          nextAudioRef.current.load();
          console.log('🎧 DJ MIND: Next track preloaded on DJ mode activation');
        }

        updateState((prev) => ({ ...prev, nextTrack }));
      }
    }
  };

  const toggleAutoTransition = () => {
    const newAutoTransition = !state.autoTransition;
    console.log(`🎧 DJ MIND: Auto-transition ${newAutoTransition ? 'ENABLED' : 'DISABLED'}`, {
      djMode: state.djMode,
      transitionTime: state.transitionTime,
    });
    setState((prev) => ({ ...prev, autoTransition: newAutoTransition }));
  };

  const setTransitionTime = (seconds: number) => {
    const newTime = Math.max(5, Math.min(60, seconds));
    console.log('🎧 DJ MIND: Transition time changed', {
      from: state.transitionTime,
      to: newTime,
      meaning: `Will start crossfade ${newTime} seconds before track ends`,
    });
    setState((prev) => ({ ...prev, transitionTime: newTime }));
  };

  const setCrossfadeDuration = (seconds: number) => {
    const newDuration = Math.max(1, Math.min(10, seconds));
    console.log('🎧 DJ MIND: Crossfade duration changed', {
      from: state.crossfadeDuration,
      to: newDuration,
      meaning: `Crossfade will take ${newDuration} seconds to complete`,
    });
    setState((prev) => ({ ...prev, crossfadeDuration: newDuration }));
  };

  // Also fix the forceTransition to use current state from stateRef
  const forceTransition = () => {
    const currentState = stateRef.current;
    if (!currentState) return;

    if (currentState.djMode && currentState.nextTrack && !currentState.isTransitioning) {
      console.log('🎧 DJ MIND: 🚀 MANUAL TRANSITION TRIGGERED!', {
        currentTrack: currentState.currentTrack?.title || currentState.currentTrack?.filename,
        nextTrack: currentState.nextTrack?.title || currentState.nextTrack?.filename,
        reason: 'User forced transition',
      });

      // Set transitioning state immediately
      setState((prev) => ({ ...prev, isTransitioning: true }));

      startTransition();
    } else {
      console.log('🎧 DJ MIND: Cannot force transition', {
        djMode: currentState.djMode,
        hasNextTrack: !!currentState.nextTrack,
        isTransitioning: currentState.isTransitioning,
      });
    }
  };

  // Enhanced DJ Functions

  const createEffectsChain = () => {
    if (!audioContextRef.current) return;

    const context = audioContextRef.current;

    try {
      // Create effects nodes
      filterRef.current = context.createBiquadFilter();
      delayRef.current = context.createDelay(2.0); // 2 second max delay
      analyserRef.current = context.createAnalyser();

      // Setup filter for scratch/sweep effects
      filterRef.current.type = 'lowpass';
      filterRef.current.frequency.setValueAtTime(20000, context.currentTime); // Start fully open
      filterRef.current.Q.setValueAtTime(1, context.currentTime);

      // Setup delay for echo effects
      delayRef.current.delayTime.setValueAtTime(0.125, context.currentTime); // 1/8 note delay

      // Setup analyser for beat detection
      analyserRef.current.fftSize = 1024;
      analyserRef.current.smoothingTimeConstant = 0.3;

      // Create reverb using convolution (simple impulse response)
      reverbRef.current = context.createConvolver();
      const impulseLength = context.sampleRate * 2; // 2 second reverb
      const impulse = context.createBuffer(2, impulseLength, context.sampleRate);
      for (let channel = 0; channel < 2; channel++) {
        const channelData = impulse.getChannelData(channel);
        for (let i = 0; i < impulseLength; i++) {
          channelData[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / impulseLength, 2);
        }
      }
      reverbRef.current.buffer = impulse;

      // Create distortion using WaveShaper
      distortionRef.current = context.createWaveShaper();
      const makeDistortionCurve = (amount: number) => {
        const samples = 44100;
        const curve = new Float32Array(samples);
        const deg = Math.PI / 180;
        for (let i = 0; i < samples; i++) {
          const x = (i * 2) / samples - 1;
          curve[i] = ((3 + amount) * x * 20 * deg) / (Math.PI + amount * Math.abs(x));
        }
        return curve;
      };
      distortionRef.current.curve = makeDistortionCurve(30);
      distortionRef.current.oversample = '4x';

      console.log('🎧 DJ MIND: ✅ Effects chain created and configured');
    } catch (error) {
      console.error('🎧 DJ MIND: ❌ Error creating effects chain:', error);
    }
  };

  const importSeratoHotCues = async (track: Track) => {
    try {
      console.log('🎛️ DJ MIND: Checking for Serato hot cues...', {
        track: track.title || track.filename,
        trackId: track.filepath,
      });

      // Get enhanced analysis that includes Serato data
      const analysis = await musicService.getTrackAnalysis(track.filepath);

      if (analysis.hot_cues && analysis.hot_cues.length > 0) {
        console.log('🎛️ DJ MIND: Found Serato hot cues!', {
          count: analysis.hot_cues.length,
          cues: analysis.hot_cues.map((cue) => ({
            name: cue.name,
            time: cue.time.toFixed(2),
            type: cue.type,
          })),
        });

        const existingCues = state.hotCues[track.filepath] || [];
        const importedCues: HotCue[] = analysis.hot_cues.map((seratoCue) => ({
          id: `serato-${seratoCue.index}-${track.filepath}`,
          name: `🎛️ ${seratoCue.name}`, // Prefix to indicate Serato import
          time: seratoCue.time,
          color: seratoCue.color,
          type: seratoCue.type as HotCue['type'],
        }));

        // Merge with existing cues, avoiding duplicates based on time
        const allCues = [...existingCues];
        importedCues.forEach((importedCue) => {
          const timeThreshold = 0.5; // 500ms tolerance for duplicate detection
          const isDuplicate = existingCues.some(
            (existing) => Math.abs(existing.time - importedCue.time) < timeThreshold
          );

          if (!isDuplicate) {
            allCues.push(importedCue);
          }
        });

        // Sort by time
        allCues.sort((a, b) => a.time - b.time);

        setState((prev) => ({
          ...prev,
          hotCues: {
            ...prev.hotCues,
            [track.filepath]: allCues,
          },
        }));

        console.log('🎛️ DJ MIND: Serato hot cues imported!', {
          imported: importedCues.length,
          existing: existingCues.length,
          total: allCues.length,
          seratoAvailable: analysis.serato_data?.serato_available || false,
        });

        return {
          imported: importedCues.length,
          total: allCues.length,
          hasSeratoData: true,
        };
      } else {
        console.log('🎛️ DJ MIND: No Serato hot cues found for this track');
        return {
          imported: 0,
          total: (state.hotCues[track.filepath] || []).length,
          hasSeratoData: analysis.serato_data?.serato_available || false,
        };
      }
    } catch (error) {
      console.error('🎛️ DJ MIND: Error importing Serato hot cues:', error);
      return {
        imported: 0,
        total: (state.hotCues[track.filepath] || []).length,
        hasSeratoData: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  };

  const setBpmSync = async (enabled: boolean, targetTrack?: Track) => {
    if (!state.currentTrack || !audioRef.current) return;

    const currentBpm = state.currentTrack.bpm || state.sourceBpm;
    const targetBpm = targetTrack?.bpm || state.targetBpm;

    if (!currentBpm || !targetBpm) {
      console.log('🎧 DJ MIND: BPM data missing, cannot sync');
      return;
    }

    const syncRatio = enabled ? targetBpm / currentBpm : 1.0;

    // Apply playback rate change for BPM sync
    audioRef.current.playbackRate = syncRatio;
    if (nextAudioRef.current) {
      nextAudioRef.current.playbackRate = syncRatio;
    }

    setState((prev) => ({
      ...prev,
      bpmSyncEnabled: enabled,
      sourceBpm: currentBpm,
      targetBpm: targetBpm,
      syncRatio,
    }));

    console.log('🎧 DJ MIND: BPM Sync', {
      enabled,
      currentBpm,
      targetBpm,
      syncRatio: syncRatio.toFixed(3),
      pitchChange: `${((syncRatio - 1) * 100).toFixed(1)}%`,
    });
  };

  const addHotCue = (trackId: string, name: string, time: number, type: HotCue['type'] = 'cue') => {
    const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899'];
    const existingCues = state.hotCues[trackId] || [];
    const color = colors[existingCues.length % colors.length];

    const newCue: HotCue = {
      id: `${trackId}-${Date.now()}`,
      name,
      time,
      color,
      type,
    };

    setState((prev) => ({
      ...prev,
      hotCues: {
        ...prev.hotCues,
        [trackId]: [...existingCues, newCue],
      },
    }));

    console.log('🎧 DJ MIND: Hot cue added', { trackId, name, time, type });
  };

  const jumpToHotCue = (cue: HotCue) => {
    if (!audioRef.current) return;

    audioRef.current.currentTime = cue.time;

    if (cue.type === 'loop') {
      setState((prev) => ({
        ...prev,
        loopActive: true,
        loopStart: cue.time,
        loopEnd: cue.time + 4, // 4-second loop default
      }));
    }

    console.log('🎧 DJ MIND: Jumped to hot cue', { name: cue.name, time: cue.time });
  };

  // Track active effects to prevent overlapping
  const activeEffectsRef = useRef<Set<string>>(new Set());
  const effectTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const applyTransitionEffect = (effect: TransitionEffect) => {
    if (!audioContextRef.current) {
      console.warn('🎧 DJ MIND: No audio context available for effects');
      return;
    }

    const context = audioContextRef.current;
    const now = context.currentTime;

    // Create unique effect ID
    const effectId = `${effect.type}_${Date.now()}`;

    // Check if this effect type is already active
    if (activeEffectsRef.current.has(effect.type)) {
      console.log(`🎧 DJ MIND: ${effect.type} effect already active, skipping`);
      return;
    }

    // Mark effect as active
    activeEffectsRef.current.add(effect.type);

    // Ensure effects chain exists
    if (!filterRef.current || !delayRef.current) {
      createEffectsChain();
    }

    // Effects should already be connected in the chain
    // No need to reconnect on every effect application

    setState((prev) => ({
      ...prev,
      currentEffects: [...prev.currentEffects, effect],
    }));

    switch (effect.type) {
      case 'filter':
        if (!filterRef.current) break;

        // Always use lowpass for smoother transitions
        filterRef.current.type = 'lowpass';
        
        // Gentle Q values (1-3 instead of 0-10)
        const qValue = 1 + (effect.intensity * 2);
        filterRef.current.Q.cancelScheduledValues(now);
        filterRef.current.Q.setValueAtTime(qValue, now);

        // Sweep from high to low for subtle effect
        const startFreq = 15000;
        const endFreq = 200 + (effect.intensity * 1000); // 200-700 Hz based on intensity

        filterRef.current.frequency.cancelScheduledValues(now);
        filterRef.current.frequency.setValueAtTime(startFreq, now);
        
        // Use exponential ramp for smoother sweeps
        filterRef.current.frequency.exponentialRampToValueAtTime(
          endFreq, 
          now + effect.duration * 0.8
        );

        // Clean up after effect
        const cleanup = setTimeout(() => {
          if (filterRef.current && audioContextRef.current) {
            const cleanupTime = audioContextRef.current.currentTime;
            // Smooth return to neutral
            filterRef.current.frequency.cancelScheduledValues(cleanupTime);
            filterRef.current.frequency.setValueAtTime(
              filterRef.current.frequency.value, 
              cleanupTime
            );
            filterRef.current.frequency.exponentialRampToValueAtTime(
              20000, 
              cleanupTime + 1
            );
            filterRef.current.Q.exponentialRampToValueAtTime(1, cleanupTime + 1);
          }
          // Remove from active effects
          activeEffectsRef.current.delete('filter');
        }, effect.duration * 1000);

        // Track timeout for cleanup
        effectTimeoutsRef.current.set(effectId, cleanup);

        console.log('🎧 DJ MIND: Filter sweep applied', {
          type: filterRef.current.type,
          startFreq,
          endFreq,
          duration: effect.duration,
        });
        break;

      case 'echo':
        if (!delayRef.current) break;

        // Calculate delay time based on BPM if available
        let delayTime = 0.125; // Default 1/8 note at 120 BPM
        if (state.sourceBpm) {
          // Convert BPM to delay time for 1/8 note
          delayTime = 60 / state.sourceBpm / 2; // 1/8 note
        }

        // Create feedback loop for echo (only if not exists)
        let feedbackGain = context.createGain();
        let wetGain = context.createGain();

        // Much gentler feedback values
        const feedbackAmount = effect.intensity * 0.3; // Max 0.3 feedback
        const wetAmount = effect.intensity * 0.25; // Max 0.25 wet signal

        // Set delay time
        delayRef.current.delayTime.cancelScheduledValues(now);
        delayRef.current.delayTime.setValueAtTime(delayTime, now);
        
        // Set initial gains
        feedbackGain.gain.setValueAtTime(0, now);
        wetGain.gain.setValueAtTime(0, now);
        
        // Fade in the effect smoothly
        feedbackGain.gain.linearRampToValueAtTime(feedbackAmount, now + 0.1);
        wetGain.gain.linearRampToValueAtTime(wetAmount, now + 0.1);

        // Connect feedback loop: delay -> feedback -> delay
        try {
          delayRef.current.connect(feedbackGain);
          feedbackGain.connect(delayRef.current);
          delayRef.current.connect(wetGain);
          wetGain.connect(currentCompressorRef.current!);
        } catch (e) {
          console.warn('🎧 DJ MIND: Echo connections exist');
        }

        // Fade out echo smoothly
        const fadeOutTime = now + effect.duration * 0.7;
        feedbackGain.gain.setValueAtTime(feedbackAmount, fadeOutTime);
        wetGain.gain.setValueAtTime(wetAmount, fadeOutTime);
        
        // Smooth fade to zero
        feedbackGain.gain.linearRampToValueAtTime(0, fadeOutTime + 1);
        wetGain.gain.linearRampToValueAtTime(0, fadeOutTime + 1);

        // Clean up after effect
        const echoCleanup = setTimeout(() => {
          try {
            feedbackGain.disconnect();
            wetGain.disconnect();
            if (delayRef.current) {
              delayRef.current.disconnect();
              delayRef.current.connect(currentCompressorRef.current!);
              delayRef.current.delayTime.setValueAtTime(0, context.currentTime);
            }
          } catch (e) {
            // Ignore disconnection errors
          }
          // Remove from active effects
          activeEffectsRef.current.delete('echo');
        }, (effect.duration + 1) * 1000);

        // Track timeout for cleanup
        effectTimeoutsRef.current.set(effectId, echoCleanup);

        console.log('🎧 DJ MIND: Echo effect applied', {
          delayTime: `${delayTime.toFixed(3)}s`,
          feedback: effect.intensity * 0.6,
          bpm: state.sourceBpm,
          duration: effect.duration,
        });
        break;

      case 'reverse':
        // Reverse effect simulation (would need AudioWorklet for true reverse)
        console.log('🎧 DJ MIND: Reverse effect triggered - would need custom AudioWorklet');
        break;

      case 'loop':
        if (audioRef.current) {
          const currentTime = audioRef.current.currentTime;
          setState((prev) => ({
            ...prev,
            loopActive: true,
            loopStart: currentTime,
            loopEnd: currentTime + (effect.duration || 1),
          }));
          console.log('🎧 DJ MIND: Loop activated', {
            start: currentTime,
            end: currentTime + (effect.duration || 1),
          });
        }
        break;

      case 'scratch':
        // Simplified scratch effect using subtle gain modulation
        if (!filterRef.current || !currentGainRef.current) break;

        console.log('🎧 DJ MIND: 🎚️ Scratch effect triggered');

        // Store original gain
        const originalGain = state.volume;

        // Apply gentle highpass filter for scratch texture
        filterRef.current.type = 'highpass';
        filterRef.current.Q.cancelScheduledValues(now);
        filterRef.current.Q.setValueAtTime(3, now); // Much lower Q
        filterRef.current.frequency.cancelScheduledValues(now);
        filterRef.current.frequency.setValueAtTime(800, now);
        
        // Sweep the filter up gently
        filterRef.current.frequency.linearRampToValueAtTime(
          1500, 
          now + effect.duration * 0.5
        );

        // Simple gain pattern (fewer, gentler cuts)
        const scratchPattern = [
          { time: 0, gain: 1.0 },
          { time: 0.1, gain: 0.7 },
          { time: 0.2, gain: 1.0 },
          { time: 0.3, gain: 0.8 },
          { time: 0.4, gain: 1.0 },
        ];

        // Apply gain pattern with gentle intensity
        scratchPattern.forEach((step) => {
          const stepGain = originalGain * (1 - (1 - step.gain) * effect.intensity * 0.5);
          currentGainRef.current!.gain.setValueAtTime(
            stepGain,
            now + step.time
          );
        });

        // Return to original volume
        currentGainRef.current.gain.setValueAtTime(originalGain, now + 0.5);

        // Clean up after effect
        const scratchCleanup = setTimeout(() => {
          if (filterRef.current && currentGainRef.current && audioContextRef.current) {
            const cleanupTime = audioContextRef.current.currentTime;
            // Smooth filter reset
            filterRef.current.frequency.linearRampToValueAtTime(20000, cleanupTime + 0.5);
            filterRef.current.Q.linearRampToValueAtTime(1, cleanupTime + 0.5);
            
            // After transition, reset to lowpass
            setTimeout(() => {
              if (filterRef.current) {
                filterRef.current.type = 'lowpass';
              }
            }, 500);

            // Ensure gain is stable
            currentGainRef.current.gain.cancelScheduledValues(cleanupTime);
            currentGainRef.current.gain.setValueAtTime(state.volume, cleanupTime);
          }
          // Remove from active effects
          activeEffectsRef.current.delete('scratch');
        }, effect.duration * 1000);

        // Track timeout for cleanup
        effectTimeoutsRef.current.set(effectId, scratchCleanup);

        console.log('🎧 DJ MIND: Scratch pattern applied', {
          intensity: effect.intensity,
          duration: effect.duration,
        });
        break;
    }

    // Remove effect from state after duration
    setTimeout(() => {
      setState((prev) => {
        const newEffects = prev.currentEffects.filter((e) => e !== effect);
        return { ...prev, currentEffects: newEffects };
      });
    }, effect.duration * 1000);
  };

  // Simple, reliable scratch effect using playback rate modulation
  const scratchEffect = (intensity: number, duration: number) => {
    if (!audioRef.current) return;

    console.log('🎧 DJ MIND: 🎚️ Applying simple scratch effect');

    const originalRate = audioRef.current.playbackRate;
    const scratchPattern = [1.2, 0.8, 1.5, 0.7, 1.0];
    let step = 0;

    const scratchInterval = setInterval(
      () => {
        if (audioRef.current && step < scratchPattern.length) {
          const rate = scratchPattern[step] * intensity;
          audioRef.current.playbackRate = originalRate * rate;
          step++;
        } else {
          if (audioRef.current) {
            audioRef.current.playbackRate = originalRate;
          }
          clearInterval(scratchInterval);
          console.log('🎧 DJ MIND: Scratch effect complete');
        }
      },
      (duration * 1000) / scratchPattern.length
    );
  };

  // Calculate optimal hot cue transition between two tracks
  const calculateOptimalHotCueTransition = (
    currentTrackHotCues: HotCue[],
    nextTrackHotCues: HotCue[],
    currentTrackDuration: number,
    currentTime: number,
    currentBpm?: number,
    nextBpm?: number
  ): HotCueTransitionPlan | null => {
    try {
      // Filter suitable outro hot cues (in last 40% of track, but not too close to end)
      const outroHotCues = currentTrackHotCues.filter((cue) => {
        const minTime = currentTrackDuration * 0.6; // Last 40%
        const maxTime = currentTrackDuration - 15; // Not in last 15 seconds
        return cue.time >= minTime && cue.time <= maxTime && cue.time > currentTime + 5;
      });

      // Filter suitable intro hot cues (in first 2 minutes, prefer phrase types)
      const introHotCues = nextTrackHotCues.filter((cue) => {
        return cue.time >= 8 && cue.time <= 120; // Between 8 seconds and 2 minutes
      });

      if (outroHotCues.length === 0 || introHotCues.length === 0) {
        console.log('🎧 DJ MIND: No suitable hot cues for transition planning');
        return null;
      }

      let bestPlan: HotCueTransitionPlan | null = null;
      let bestScore = 0;

      // Analyze all possible outro-intro combinations
      for (const outroHotCue of outroHotCues) {
        for (const introHotCue of introHotCues) {
          const plan = analyzeHotCueCompatibility(outroHotCue, introHotCue, currentBpm, nextBpm);

          if (plan.compatibilityScore > bestScore) {
            bestScore = plan.compatibilityScore;
            bestPlan = plan;
          }
        }
      }

      if (bestPlan && bestScore > 0.3) {
        // Minimum acceptable compatibility
        console.log('🎧 DJ MIND: ✅ Optimal hot cue transition calculated', {
          outroHotCue: bestPlan.outroHotCue.name,
          introHotCue: bestPlan.introHotCue.name,
          score: bestScore.toFixed(2),
          bpmCompatible: bestPlan.bpmCompatible,
          phraseAligned: bestPlan.phraseAligned,
        });
        return bestPlan;
      }

      console.log(
        '🎧 DJ MIND: No high-quality hot cue transitions found (best score:',
        bestScore.toFixed(2),
        ')'
      );
      return null;
    } catch (error) {
      console.error('🎧 DJ MIND: Error calculating hot cue transition:', error);
      return null;
    }
  };

  // Analyze compatibility between two hot cues
  const analyzeHotCueCompatibility = (
    outroHotCue: HotCue,
    introHotCue: HotCue,
    currentBpm?: number,
    nextBpm?: number
  ): HotCueTransitionPlan => {
    let score = 0;
    let bpmCompatible = false;
    let phraseAligned = false;
    const recommendedEffects: TransitionEffect[] = [];

    // Score based on hot cue types
    if (outroHotCue.type === 'phrase' && introHotCue.type === 'phrase') {
      score += 0.4; // Phrase-to-phrase is ideal
      phraseAligned = true;
    } else if (outroHotCue.type === 'phrase' || introHotCue.type === 'phrase') {
      score += 0.2; // One phrase is good
    } else {
      score += 0.1; // Basic cue points
    }

    // Score based on BPM compatibility
    if (currentBpm && nextBpm) {
      const bpmDiff = Math.abs(currentBpm - nextBpm);
      if (bpmDiff <= 5) {
        score += 0.3;
        bpmCompatible = true;
      } else if (bpmDiff <= 15) {
        score += 0.15;
        bpmCompatible = true;
      } else if (bpmDiff <= 30) {
        score += 0.05;
        // Add filter effect for large BPM differences
        recommendedEffects.push({
          type: 'filter',
          intensity: Math.min(0.8, bpmDiff / 40),
          duration: 3.0,
        });
      }
    }

    // Score based on hot cue names (heuristic analysis)
    const outroName = outroHotCue.name.toLowerCase();
    const introName = introHotCue.name.toLowerCase();

    if (
      (outroName.includes('outro') || outroName.includes('end')) &&
      (introName.includes('intro') || introName.includes('start'))
    ) {
      score += 0.2; // Perfect structural match
    } else if (outroName.includes('break') && introName.includes('drop')) {
      score += 0.15; // Break to drop is good
    } else if (outroName.includes('bridge') || introName.includes('verse')) {
      score += 0.1; // Structural elements
    }

    // Add scratch effect for phrase-aligned transitions
    if (phraseAligned) {
      recommendedEffects.push({
        type: 'scratch',
        intensity: 0.7,
        duration: 1.0,
      });
    }

    // Calculate recommended crossfade duration based on compatibility
    let crossfadeDuration = 4.0; // Default
    if (score > 0.7) {
      crossfadeDuration = 6.0; // Longer for high-quality transitions
    } else if (score < 0.4) {
      crossfadeDuration = 3.0; // Shorter for basic transitions
    }

    return {
      outroHotCue,
      introHotCue,
      compatibilityScore: Math.min(1.0, score),
      bpmCompatible,
      phraseAligned,
      recommendedCrossfadeDuration: crossfadeDuration,
      recommendedEffects,
    };
  };

  const calculateBeatAlignedTransition = (currentTrack: Track, nextTrack: Track) => {
    if (!state.beatAlignment || !currentTrack.bpm || !nextTrack.bpm) {
      return state.transitionTime; // Use default if no BPM data
    }

    // Calculate beat length in seconds
    const currentBeatLength = 60 / currentTrack.bpm;
    const nextBeatLength = 60 / nextTrack.bpm;

    // Find optimal transition point (phrase boundary = 32 beats typically)
    const phraseLength = currentBeatLength * 32;
    const optimalTransitionTime = Math.ceil(state.transitionTime / phraseLength) * phraseLength;

    console.log('🎧 DJ MIND: Beat-aligned transition calculated', {
      currentBpm: currentTrack.bpm,
      nextBpm: nextTrack.bpm,
      currentBeatLength: currentBeatLength.toFixed(3),
      phraseLength: phraseLength.toFixed(1),
      optimalTransitionTime: optimalTransitionTime.toFixed(1),
    });

    return optimalTransitionTime;
  };

  // Fix 6: Improve startCreativeTransition to handle race conditions
  const startCreativeTransition = async () => {
    // Use stateRef to get most current state
    const currentState = stateRef.current;
    if (
      !audioRef.current ||
      !nextAudioRef.current ||
      !currentState?.nextTrack ||
      !currentState?.currentTrack
    ) {
      console.log('🎧 DJ MIND: Cannot start transition - missing requirements');
      updateState((prev) => ({ ...prev, isTransitioning: false }));
      return;
    }

    // Double-check we're not already transitioning
    if (currentState.isTransitioning) {
      console.log('🎧 DJ MIND: Transition already in progress, skipping...');
      return;
    }

    console.log('🎧 DJ MIND: 🎨 STARTING CREATIVE TRANSITION 🎨', {
      from: currentState.currentTrack.title || currentState.currentTrack.filename,
      to: currentState.nextTrack.title || currentState.nextTrack.filename,
      currentBpm: currentState.currentTrack.bpm,
      nextBpm: currentState.nextTrack.bpm,
      effects: currentState.currentEffects.length,
    });

    // Apply BPM sync if enabled and different BPMs
    if (
      currentState.bpmSyncEnabled &&
      currentState.currentTrack.bpm &&
      currentState.nextTrack.bpm
    ) {
      await setBpmSync(true, currentState.nextTrack);
    }

    // Choose creative effect based on BPM difference and track characteristics
    const bpmDiff = Math.abs(
      (currentState.currentTrack.bpm || 120) - (currentState.nextTrack.bpm || 120)
    );
    let transitionEffect: TransitionEffect;

    if (bpmDiff > 20) {
      // Large BPM difference - use dramatic filter sweep
      transitionEffect = {
        type: 'filter',
        intensity: 0.9,
        duration: Math.max(currentState.crossfadeDuration * 0.8, 6),
      };
    } else if (bpmDiff > 10) {
      // Medium BPM difference - use echo effect
      transitionEffect = {
        type: 'echo',
        intensity: 0.8,
        duration: Math.max(currentState.crossfadeDuration * 0.6, 4),
      };
    } else {
      // Similar BPM - use subtle loop or scratch
      transitionEffect = {
        type: Math.random() > 0.5 ? 'loop' : 'scratch',
        intensity: 0.7,
        duration: Math.max(currentState.crossfadeDuration * 0.3, 3),
      };
    }

    // Apply the effect
    applyTransitionEffect(transitionEffect);

    // Continue with standard crossfade
    await startTransition();
  };

  const toggleRepeatCallback = useCallback(() => {
    const modes: ('none' | 'one' | 'all')[] = ['none', 'one', 'all'];
    const currentIndex = modes.indexOf(state.repeat);
    const nextMode = modes[(currentIndex + 1) % modes.length];
    setRepeat(nextMode);
  }, [state.repeat]);

  const toggleBeatAlignmentCallback = useCallback(() => {
    updateState((prev) => ({ ...prev, beatAlignment: !prev.beatAlignment }));
  }, [updateState]);

  const setPitchShiftCallback = useCallback(
    (pitch: number) => {
      updateState((prev) => ({ ...prev, pitchShift: pitch }));
      // Apply pitch shift to audio elements
      const pitchRatio = Math.pow(2, pitch / 1200); // Convert cents to ratio
      if (audioRef.current) audioRef.current.playbackRate = state.syncRatio * pitchRatio;
      if (nextAudioRef.current) nextAudioRef.current.playbackRate = state.syncRatio * pitchRatio;
    },
    [updateState, state.syncRatio]
  );

  const triggerScratchCallback = useCallback(
    (intensity: number = 0.8) =>
      applyTransitionEffect({
        type: 'scratch',
        intensity,
        duration: 2.0,
      }),
    [applyTransitionEffect]
  );

  const triggerEchoCallback = useCallback(
    (intensity: number = 0.6) =>
      applyTransitionEffect({
        type: 'echo',
        intensity,
        duration: 4.0,
      }),
    [applyTransitionEffect]
  );

  const triggerFilterCallback = useCallback(
    (intensity: number = 0.7) =>
      applyTransitionEffect({
        type: 'filter',
        intensity,
        duration: 6.0,
      }),
    [applyTransitionEffect]
  );

  const contextValue: AudioPlayerContextType = useMemo(
    () => ({
      // State values
      currentTrack: state.currentTrack,
      isPlaying: state.isPlaying,
      isLoading: state.isLoading,
      duration: state.duration,
      currentTime: state.currentTime,
      volume: state.volume,
      isMuted: state.isMuted,
      queue: state.queue,
      currentIndex: state.currentIndex,
      shuffle: state.shuffle,
      repeat: state.repeat,
      djMode: state.djMode,
      autoTransition: state.autoTransition,
      transitionTime: state.transitionTime,
      crossfadeDuration: state.crossfadeDuration,
      isTransitioning: state.isTransitioning,
      transitionProgress: state.transitionProgress,
      nextTrack: state.nextTrack,
      timeUntilTransition: state.timeUntilTransition,
      mixInterval: state.mixInterval,
      mixMode: state.mixMode,

      // Enhanced DJ state
      bpmSyncEnabled: state.bpmSyncEnabled,
      pitchShift: state.pitchShift,
      hotCues: state.hotCues,
      currentEffects: state.currentEffects,
      beatAlignment: state.beatAlignment,
      loopActive: state.loopActive,
      sourceBpm: state.sourceBpm,
      targetBpm: state.targetBpm,
      syncRatio: state.syncRatio,

      // Actions
      playTrack,
      play: resume,
      pause,
      skipToNext: skipToNextFn,
      skipToPrevious: previousTrack,
      seek: seekTo,
      setVolume,
      toggleMute,
      toggleShuffle,
      toggleRepeat: toggleRepeatCallback,
      addToQueue,
      removeFromQueue,
      clearQueue,
      moveQueueItem: moveTrackInQueue,
      toggleDjMode,
      setAutoTransition: toggleAutoTransition,
      setTransitionTime,
      setCrossfadeDuration,
      forceTransition,
      setMixInterval,
      setMixMode,
      setTransitionEffectPlan,
      transitionEffectPlan: state.transitionEffectPlan,

      // Enhanced DJ functions
      setBpmSync,
      addHotCue,
      jumpToHotCue,
      applyTransitionEffect,
      toggleBeatAlignment: toggleBeatAlignmentCallback,
      setPitchShift: setPitchShiftCallback,
      triggerScratch: triggerScratchCallback,
      triggerEcho: triggerEchoCallback,
      triggerFilter: triggerFilterCallback,
    }),
    [
      // State dependencies
      state,
      // Function dependencies
      playTrack,
      resume,
      pause,
      skipToNextFn,
      previousTrack,
      seekTo,
      setVolume,
      toggleMute,
      toggleShuffle,
      toggleRepeatCallback,
      addToQueue,
      removeFromQueue,
      clearQueue,
      moveTrackInQueue,
      toggleDjMode,
      toggleAutoTransition,
      setTransitionTime,
      setCrossfadeDuration,
      forceTransition,
      setMixInterval,
      setMixMode,
      setTransitionEffectPlan,
      setBpmSync,
      addHotCue,
      jumpToHotCue,
      applyTransitionEffect,
      toggleBeatAlignmentCallback,
      setPitchShiftCallback,
      triggerScratchCallback,
      triggerEchoCallback,
      triggerFilterCallback,
    ]
  );

  return <AudioPlayerContext.Provider value={contextValue}>{children}</AudioPlayerContext.Provider>;
};

'use client';

import React, { createContext, useContext, useState, useRef, useEffect, ReactNode } from 'react';
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
  transitionTime: number; // seconds before end to start transition
  crossfadeDuration: number; // duration of crossfade in seconds
  isTransitioning: boolean;
  transitionProgress: number; // 0 to 1
  nextTrack: Track | null;
  timeUntilTransition: number; // seconds until transition starts
  
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
}

interface AudioPlayerActions {
  // Track control
  playTrack: (track: Track, queue?: Track[]) => void;
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
  toggleDjMode: () => void;
  toggleAutoTransition: () => void;
  setTransitionTime: (seconds: number) => void;
  setCrossfadeDuration: (seconds: number) => void;
  forceTransition: () => void;
}

interface AudioPlayerContextType {
  // Existing state properties
  currentTrack: Track | null;
  isPlaying: boolean;
  duration: number;
  currentTime: number;
  volume: number;
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
  playTrack: (track: Track, queue?: Track[]) => void;
  play: () => void;
  pause: () => void;
  skipToNext: () => void;
  skipToPrevious: () => void;
  seek: (time: number) => void;
  setVolume: (volume: number) => void;
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
    transitionTime: 30,
    crossfadeDuration: 5,
    isTransitioning: false,
    transitionProgress: 0,
    nextTrack: null,
    timeUntilTransition: 0,
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
  });

  // Initialize Web Audio API for crossfading
  useEffect(() => {
    const initAudioContext = async () => {
      if (!audioContextRef.current) {
        try {
          audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
          console.log('🎧 DJ MIND: Audio context created');
          
          // Resume context if needed
          if (audioContextRef.current.state === 'suspended') {
            await audioContextRef.current.resume();
            console.log('🎧 DJ MIND: Audio context resumed');
          }
          
          // Create effects chain once context is ready
          createEffectsChain();
        } catch (error) {
          console.error('🎧 DJ MIND: Failed to create audio context:', error);
        }
      }
    };

    // Initialize on first user interaction
    const handleFirstInteraction = async () => {
      await initAudioContext();
      document.removeEventListener('click', handleFirstInteraction);
      document.removeEventListener('keydown', handleFirstInteraction);
    };

    document.addEventListener('click', handleFirstInteraction);
    document.addEventListener('keydown', handleFirstInteraction);

    return () => {
      document.removeEventListener('click', handleFirstInteraction);
      document.removeEventListener('keydown', handleFirstInteraction);
    };
  }, []);

  // Setup Web Audio API connections for an audio element
  const setupAudioConnection = (audioElement: HTMLAudioElement, isNext: boolean = false) => {
    if (!audioContextRef.current) return null;

    try {
      const context = audioContextRef.current;
      
      // Create source if it doesn't exist
      let source: MediaElementAudioSourceNode;
      let gainNode: GainNode;
      
      if (isNext) {
        if (!nextSourceRef.current) {
          try {
            nextSourceRef.current = context.createMediaElementSource(audioElement);
            console.log('🎧 DJ MIND: Created next track source node');
          } catch (error: any) {
            if (error.message && error.message.includes('already connected')) {
              console.log('🎧 DJ MIND: Next track source already exists, reusing...');
              // If source already exists, we'll use the existing one
              return { source: nextSourceRef.current, gainNode: nextGainRef.current };
            } else {
              throw error;
            }
          }
        }
        if (!nextGainRef.current) {
          nextGainRef.current = context.createGain();
          console.log('🎧 DJ MIND: Created next track gain node');
        }
        source = nextSourceRef.current;
        gainNode = nextGainRef.current;
      } else {
        if (!currentSourceRef.current) {
          try {
            currentSourceRef.current = context.createMediaElementSource(audioElement);
            console.log('🎧 DJ MIND: Created current track source node');
          } catch (error: any) {
            if (error.message && error.message.includes('already connected')) {
              console.log('🎧 DJ MIND: Current track source already exists, reusing...');
              // If source already exists, we'll use the existing one
              return { source: currentSourceRef.current, gainNode: currentGainRef.current };
            } else {
              throw error;
            }
          }
        }
        if (!currentGainRef.current) {
          currentGainRef.current = context.createGain();
          console.log('🎧 DJ MIND: Created current track gain node');
        }
        source = currentSourceRef.current;
        gainNode = currentGainRef.current;
      }

      // Connect: source -> gain -> destination (only if not already connected)
      try {
        source.connect(gainNode);
        gainNode.connect(context.destination);
        console.log(`🎧 DJ MIND: ${isNext ? 'Next' : 'Current'} track audio graph connected`);
      } catch (error: any) {
        if (error.message && error.message.includes('already connected')) {
          console.log(`🎧 DJ MIND: ${isNext ? 'Next' : 'Current'} track audio graph already connected`);
        } else {
          throw error;
        }
      }
      
      // Set initial gain
      gainNode.gain.value = isNext ? 0 : 1;
      
      return { source, gainNode };
      
    } catch (error) {
      console.error('🎧 DJ MIND: Error setting up audio connection:', error);
      return null;
    }
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

    // Audio event listeners for main audio
    const handleLoadStart = () => setState(prev => ({ ...prev, isLoading: true }));
    const handleCanPlay = () => {
      setState(prev => ({ ...prev, isLoading: false }));
      // Setup Web Audio connection when audio is ready
      if (state.djMode && audioContextRef.current) {
        setupAudioConnection(audio, false);
      }
    };
    const handleTimeUpdate = () => {
      setState(prev => ({ ...prev, currentTime: audio.currentTime }));
      updateTransitionTimer();
    };
    const handleDurationChange = () => {
      setState(prev => ({ ...prev, duration: audio.duration || 0 }));
    };
    const handleEnded = () => {
      setState(prev => ({ ...prev, isPlaying: false }));
      if (!state.djMode || !state.autoTransition) {
        // Normal behavior - advance to next track
        setTimeout(() => skipToNextFn(), 100);
      }
    };
    const handleError = (e: Event) => {
      console.error('🎧 DJ MIND: Audio error:', e);
      setState(prev => ({ ...prev, isLoading: false, isPlaying: false }));
    };

    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.pause();
      nextAudio.pause();
      
      // Clear timeouts
      if (transitionTimeoutRef.current) {
        clearTimeout(transitionTimeoutRef.current);
      }
      if (transitionIntervalRef.current) {
        clearInterval(transitionIntervalRef.current);
      }
    };
  }, []);

  // Update audio volume and mute state
  useEffect(() => {
    if (audioRef.current) {
      if (state.djMode && currentGainRef.current) {
        // Use Web Audio API gain when in DJ mode
        const volume = state.isMuted ? 0 : state.volume;
        currentGainRef.current.gain.value = volume;
        console.log('🎧 DJ MIND: Updated current track gain:', volume);
      } else {
        // Use regular audio element volume
        audioRef.current.volume = state.isMuted ? 0 : state.volume;
      }
    }
  }, [state.volume, state.isMuted, state.djMode]);

  // Update next track when queue or current index changes
  useEffect(() => {
    if (state.djMode && state.queue.length > 0) {
      const nextIndex = getNextTrackIndex();
      const nextTrack = nextIndex >= 0 ? state.queue[nextIndex] : null;
      
      // DJ MIND LOG: Track planning
      if (nextTrack && nextTrack.filepath !== state.nextTrack?.filepath) {
        console.log('🎧 DJ MIND: Planning next track...', {
          current: state.currentTrack?.title || state.currentTrack?.filename || 'None',
          next: nextTrack.title || nextTrack.filename,
          nextIndex,
          queueLength: state.queue.length,
          shuffle: state.shuffle,
          repeat: state.repeat
        });
        
        // Preload next track
        if (nextAudioRef.current && nextTrack) {
          nextAudioRef.current.src = `http://localhost:8000/track/${encodeURIComponent(nextTrack.filepath)}/stream`;
          nextAudioRef.current.load();
          console.log('🎧 DJ MIND: Next track preloaded');
        }
        
        // Setup effects chain when track changes
        createEffectsChain();
        
        setState(prev => ({ ...prev, nextTrack }));
      }
    }
  }, [state.queue, state.currentIndex, state.shuffle, state.repeat, state.djMode]);

  const getNextTrackIndex = (): number => {
    if (state.queue.length === 0) return -1;

    if (state.repeat === 'one') {
      return state.currentIndex;
    } else if (state.shuffle) {
      const availableIndices = state.queue
        .map((_, index) => index)
        .filter(index => index !== state.currentIndex);
      return availableIndices[Math.floor(Math.random() * availableIndices.length)] || -1;
    } else {
      const nextIndex = state.currentIndex + 1;
      if (nextIndex >= state.queue.length) {
        return state.repeat === 'all' ? 0 : -1;
      }
      return nextIndex;
    }
  };

  const updateTransitionTimer = () => {
    if (!audioRef.current || !state.djMode || !state.autoTransition || state.isTransitioning) return;

    const currentTime = audioRef.current.currentTime;
    const duration = state.duration;
    
    if (duration > 0) {
      // Use beat-aligned transition timing if available
      const optimalTransitionTime = state.currentTrack && state.nextTrack 
        ? calculateBeatAlignedTransition(state.currentTrack, state.nextTrack)
        : state.transitionTime;
      
      const timeUntilTransition = duration - currentTime - optimalTransitionTime;
      
      setState(prev => ({ ...prev, timeUntilTransition }));
      
      if (timeUntilTransition <= 0 && state.nextTrack) {
        console.log('🎧 DJ MIND: ⏰ TRANSITION TIME! Starting creative transition...');
        startCreativeTransition(); // Use creative transition instead of basic
      }
    }
  };

  const startTransition = async () => {
    if (!audioRef.current || !nextAudioRef.current || !state.nextTrack || !audioContextRef.current) return;

    console.log('🎧 DJ MIND: 🔥 STARTING TRANSITION SEQUENCE 🔥', {
      currentTrack: state.currentTrack?.title || state.currentTrack?.filename,
      nextTrack: state.nextTrack.title || state.nextTrack.filename,
      currentTime: Math.floor(audioRef.current.currentTime),
      duration: Math.floor(state.duration),
      crossfadeDuration: state.crossfadeDuration,
      useWebAudio: !!audioContextRef.current
    });
    
    setState(prev => ({ ...prev, isTransitioning: true, transitionProgress: 0 }));

    try {
      const context = audioContextRef.current;
      
      // Ensure context is running
      if (context.state === 'suspended') {
        await context.resume();
        console.log('🎧 DJ MIND: Audio context resumed for transition');
      }

      // Setup next track audio connection if not already done
      if (!nextSourceRef.current) {
        console.log('🎧 DJ MIND: Setting up next track audio connection...');
        setupAudioConnection(nextAudioRef.current, true);
      }

      // Ensure both gain nodes exist
      if (!currentGainRef.current || !nextGainRef.current) {
        console.error('🎧 DJ MIND: Missing gain nodes, falling back to simple crossfade');
        await startSimpleCrossfade();
        return;
      }

      console.log('🎧 DJ MIND: Starting next track...');
      
      // Reset next track gain to 0 before starting
      nextGainRef.current.gain.value = 0;
      
      // Start playing next track
      nextAudioRef.current.volume = 1; // Set volume to 1 since Web Audio will control gain
      await nextAudioRef.current.play();
      
      console.log('🎧 DJ MIND: Next track playing, beginning crossfade...');

      // Crossfade animation
      const crossfadeSteps = 50;
      const stepDuration = (state.crossfadeDuration * 1000) / crossfadeSteps;
      let step = 0;

      const crossfadeInterval = setInterval(() => {
        step++;
        const progress = step / crossfadeSteps;
        
        // Calculate gains using cosine/sine for smooth crossfade
        const currentGain = Math.cos(progress * Math.PI / 2);
        const nextGain = Math.sin(progress * Math.PI / 2);
        
        // Apply gains
        if (currentGainRef.current) {
          currentGainRef.current.gain.value = currentGain * state.volume;
        }
        if (nextGainRef.current) {
          nextGainRef.current.gain.value = nextGain * state.volume;
        }
        
        // Log progress at key points
        if (step % 10 === 0 || step === crossfadeSteps) {
          console.log(`🎧 DJ MIND: Crossfade ${Math.round(progress * 100)}%`, {
            currentGain: currentGain.toFixed(2),
            nextGain: nextGain.toFixed(2),
            step: `${step}/${crossfadeSteps}`,
            currentActualGain: (currentGain * state.volume).toFixed(2),
            nextActualGain: (nextGain * state.volume).toFixed(2)
          });
        }
        
        setState(prev => ({ ...prev, transitionProgress: progress }));

        if (step >= crossfadeSteps) {
          clearInterval(crossfadeInterval);
          console.log('🎧 DJ MIND: Crossfade complete, finalizing transition...');
          completeTransition();
        }
      }, stepDuration);

    } catch (error) {
      console.error('🎧 DJ MIND: ❌ ERROR during Web Audio transition:', error);
      console.log('🎧 DJ MIND: Falling back to simple crossfade...');
      await startSimpleCrossfade();
    }
  };

  // Fallback crossfade without Web Audio API
  const startSimpleCrossfade = async () => {
    if (!audioRef.current || !nextAudioRef.current || !state.nextTrack) return;

    console.log('🎧 DJ MIND: Using fallback volume crossfade (no Web Audio API)');
    
    try {
      // Start playing next track
      nextAudioRef.current.volume = 0;
      await nextAudioRef.current.play();
      
      console.log('🎧 DJ MIND: Next track playing, beginning volume crossfade...');

      const crossfadeSteps = 50;
      const stepDuration = (state.crossfadeDuration * 1000) / crossfadeSteps;
      let step = 0;

      const crossfadeInterval = setInterval(() => {
        step++;
        const progress = step / crossfadeSteps;
        
        // Simple volume crossfade
        if (audioRef.current) {
          audioRef.current.volume = (1 - progress) * state.volume;
        }
        if (nextAudioRef.current) {
          nextAudioRef.current.volume = progress * state.volume;
        }
        
        // Log progress at key points
        if (step % 10 === 0 || step === crossfadeSteps) {
          console.log(`🎧 DJ MIND: Volume crossfade ${Math.round(progress * 100)}%`, {
            currentVolume: ((1 - progress) * state.volume).toFixed(2),
            nextVolume: (progress * state.volume).toFixed(2),
            step: `${step}/${crossfadeSteps}`
          });
        }
        
        setState(prev => ({ ...prev, transitionProgress: progress }));

        if (step >= crossfadeSteps) {
          clearInterval(crossfadeInterval);
          console.log('🎧 DJ MIND: Volume crossfade complete, finalizing transition...');
          completeTransition();
        }
      }, stepDuration);
    } catch (error) {
      console.error('🎧 DJ MIND: ❌ ERROR during simple crossfade:', error);
      completeTransition();
    }
  };

  const completeTransition = () => {
    if (!audioRef.current || !nextAudioRef.current || !state.nextTrack) return;

    console.log('🎧 DJ MIND: 🎉 TRANSITION COMPLETE! 🎉', {
      previousTrack: state.currentTrack?.title || state.currentTrack?.filename,
      newCurrentTrack: state.nextTrack.title || state.nextTrack.filename,
      queuePosition: `${getNextTrackIndex() + 1}/${state.queue.length}`
    });

    // Stop current track
    audioRef.current.pause();
    console.log('🎧 DJ MIND: Previous track stopped');

    // Swap audio elements and their Web Audio connections
    const tempAudio = audioRef.current;
    audioRef.current = nextAudioRef.current;
    nextAudioRef.current = tempAudio;
    
    // Swap Web Audio API references
    const tempSource = currentSourceRef.current;
    const tempGain = currentGainRef.current;
    currentSourceRef.current = nextSourceRef.current;
    currentGainRef.current = nextGainRef.current;
    nextSourceRef.current = tempSource;
    nextGainRef.current = tempGain;
    
    console.log('🎧 DJ MIND: Audio elements and Web Audio connections swapped');

    // Update state
    const nextIndex = getNextTrackIndex();
    setState(prev => ({
      ...prev,
      currentTrack: prev.nextTrack,
      currentIndex: nextIndex,
      isTransitioning: false,
      transitionProgress: 0,
      currentTime: 0,
      duration: audioRef.current?.duration || 0,
    }));

    // Reset volumes and gains
    if (state.djMode && currentGainRef.current) {
      // In DJ mode, use Web Audio gain
      currentGainRef.current.gain.value = state.volume;
      audioRef.current.volume = 1; // Keep element volume at 1, control through gain
      console.log('🎧 DJ MIND: Reset Web Audio gain to', state.volume);
    } else {
      // Normal mode, use element volume
      audioRef.current.volume = state.volume;
      console.log('🎧 DJ MIND: Reset element volume to', state.volume);
    }
    
    if (nextAudioRef.current) {
      nextAudioRef.current.volume = state.volume;
    }
    
    // Reset next track gain if it exists
    if (nextGainRef.current) {
      nextGainRef.current.gain.value = 0;
    }
    
    console.log('🎧 DJ MIND: Volumes and gains reset, ready for next transition');
    
    // Log what's coming up next
    setTimeout(() => {
      const upcomingNextIndex = getNextTrackIndex();
      const upcomingNextTrack = upcomingNextIndex >= 0 ? state.queue[upcomingNextIndex] : null;
      if (upcomingNextTrack) {
        console.log('🎧 DJ MIND: Next track in queue:', {
          track: upcomingNextTrack.title || upcomingNextTrack.filename,
          artist: upcomingNextTrack.artist || 'Unknown Artist',
          willTransitionIn: `${state.transitionTime} seconds before end`
        });
      } else {
        console.log('🎧 DJ MIND: No more tracks in queue after this one');
      }
    }, 100);
  };

  const playTrack = (track: Track, queue: Track[] = []) => {
    if (!audioRef.current) return;

    const newQueue = queue.length > 0 ? queue : [track];
    const trackIndex = newQueue.findIndex(t => t.filepath === track.filepath);
    
    // DJ MIND LOG: Track playback
    console.log('🎧 DJ MIND: Starting new track...', {
      track: track.title || track.filename,
      artist: track.artist || 'Unknown Artist',
      queuePosition: `${trackIndex + 1}/${newQueue.length}`,
      djMode: state.djMode,
      autoTransition: state.autoTransition,
      shuffle: state.shuffle,
      repeat: state.repeat
    });
    
    setState(prev => ({
      ...prev,
      currentTrack: track,
      queue: newQueue,
      currentIndex: trackIndex >= 0 ? trackIndex : 0,
      isLoading: true,
      isTransitioning: false,
    }));

    const streamUrl = musicService.getStreamUrl(track.filepath);
    audioRef.current.src = streamUrl;
    audioRef.current.load();
    
    audioRef.current.play().then(async () => {
      setState(prev => ({ ...prev, isPlaying: true }));
      console.log('🎧 DJ MIND: Track playing successfully', {
        track: track.title || track.filename,
        duration: Math.floor(audioRef.current?.duration || 0),
        djMode: state.djMode
      });
      
      // Setup Web Audio connection for DJ mode
      if (state.djMode && audioContextRef.current && audioRef.current) {
        console.log('🎧 DJ MIND: Setting up Web Audio for current track...');
        
        // Ensure audio context is resumed
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume();
          console.log('🎧 DJ MIND: Audio context resumed');
        }
        
        // Setup connection for current track
        setupAudioConnection(audioRef.current, false);
      }

      // Automatically import Serato hot cues for DJ mode
      if (state.djMode) {
        console.log('🎛️ DJ MIND: Auto-importing Serato hot cues...');
        try {
          const importResult = await importSeratoHotCues(track);
          if (importResult.imported > 0) {
            console.log('🎛️ DJ MIND: ✅ Auto-import successful!', importResult);
          } else if (importResult.hasSeratoData) {
            console.log('🎛️ DJ MIND: Serato available but no new cues to import');
          } else {
            console.log('🎛️ DJ MIND: No Serato data available for this track');
          }
        } catch (error) {
          console.error('🎛️ DJ MIND: Auto-import failed:', error);
        }
      }
    }).catch(error => {
      console.error('🎧 DJ MIND: ❌ Error playing track:', error);
      setState(prev => ({ ...prev, isLoading: false, isPlaying: false }));
    });
  };

  const pause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setState(prev => ({ ...prev, isPlaying: false }));
    }
  };

  const resume = () => {
    if (audioRef.current) {
      audioRef.current.play().then(() => {
        setState(prev => ({ ...prev, isPlaying: true }));
      }).catch(error => {
        console.error('Error resuming track:', error);
      });
    }
  };

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setState(prev => ({ 
        ...prev, 
        isPlaying: false,
        currentTime: 0 
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
        .filter(index => index !== state.currentIndex);
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
      setState(prev => ({ ...prev, currentTime: time }));
    }
  };

  const setVolume = (volume: number) => {
    setState(prev => ({ ...prev, volume: Math.max(0, Math.min(1, volume)) }));
  };

  const toggleMute = () => {
    setState(prev => ({ ...prev, isMuted: !prev.isMuted }));
  };

  const addToQueue = (track: Track) => {
    setState(prev => ({ ...prev, queue: [...prev.queue, track] }));
  };

  const removeFromQueue = (index: number) => {
    setState(prev => {
      const newQueue = prev.queue.filter((_, i) => i !== index);
      const newCurrentIndex = index < prev.currentIndex 
        ? prev.currentIndex - 1 
        : prev.currentIndex;
      
      return {
        ...prev,
        queue: newQueue,
        currentIndex: newCurrentIndex
      };
    });
  };

  const clearQueue = () => {
    setState(prev => ({ ...prev, queue: [], currentIndex: -1 }));
  };

  const moveTrackInQueue = (fromIndex: number, toIndex: number) => {
    setState(prev => {
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
        currentIndex: newCurrentIndex
      };
    });
  };

  const setRepeat = (mode: 'none' | 'one' | 'all') => {
    setState(prev => ({ ...prev, repeat: mode }));
  };

  const toggleShuffle = () => {
    setState(prev => ({ ...prev, shuffle: !prev.shuffle }));
  };

  const toggleDjMode = () => {
    const newDjMode = !state.djMode;
    console.log(`🎧 DJ MIND: DJ Mode ${newDjMode ? 'ACTIVATED' : 'DEACTIVATED'}`, {
      currentTrack: state.currentTrack?.title || state.currentTrack?.filename || 'None',
      queueLength: state.queue.length,
      autoTransition: state.autoTransition,
      transitionTime: state.transitionTime,
      crossfadeDuration: state.crossfadeDuration
    });
    setState(prev => ({ ...prev, djMode: newDjMode }));
  };

  const toggleAutoTransition = () => {
    const newAutoTransition = !state.autoTransition;
    console.log(`🎧 DJ MIND: Auto-transition ${newAutoTransition ? 'ENABLED' : 'DISABLED'}`, {
      djMode: state.djMode,
      transitionTime: state.transitionTime
    });
    setState(prev => ({ ...prev, autoTransition: newAutoTransition }));
  };

  const setTransitionTime = (seconds: number) => {
    const newTime = Math.max(5, Math.min(60, seconds));
    console.log('🎧 DJ MIND: Transition time changed', {
      from: state.transitionTime,
      to: newTime,
      meaning: `Will start crossfade ${newTime} seconds before track ends`
    });
    setState(prev => ({ ...prev, transitionTime: newTime }));
  };

  const setCrossfadeDuration = (seconds: number) => {
    const newDuration = Math.max(1, Math.min(10, seconds));
    console.log('🎧 DJ MIND: Crossfade duration changed', {
      from: state.crossfadeDuration,
      to: newDuration,
      meaning: `Crossfade will take ${newDuration} seconds to complete`
    });
    setState(prev => ({ ...prev, crossfadeDuration: newDuration }));
  };

  const forceTransition = () => {
    if (state.djMode && state.nextTrack && !state.isTransitioning) {
      console.log('🎧 DJ MIND: 🚀 MANUAL TRANSITION TRIGGERED!', {
        currentTrack: state.currentTrack?.title || state.currentTrack?.filename,
        nextTrack: state.nextTrack.title || state.nextTrack.filename,
        reason: 'User forced transition'
      });
      startTransition();
    } else {
      console.log('🎧 DJ MIND: Cannot force transition', {
        djMode: state.djMode,
        hasNextTrack: !!state.nextTrack,
        isTransitioning: state.isTransitioning
      });
    }
  };

  // Enhanced DJ Functions
  
  const createEffectsChain = () => {
    if (!audioContextRef.current) return;
    
    const context = audioContextRef.current;
    
    // Create effects nodes
    filterRef.current = context.createBiquadFilter();
    delayRef.current = context.createDelay(2.0); // 2 second max delay
    analyserRef.current = context.createAnalyser();
    
    // Setup analyser for beat detection
    analyserRef.current.fftSize = 1024;
    analyserRef.current.smoothingTimeConstant = 0.3;
    
    // Create reverb using convolution
    reverbRef.current = context.createConvolver();
    
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
    
    console.log('🎧 DJ MIND: Effects chain created');
  };

  const importSeratoHotCues = async (track: Track) => {
    try {
      console.log('🎛️ DJ MIND: Checking for Serato hot cues...', {
        track: track.title || track.filename,
        trackId: track.filepath
      });

      // Get enhanced analysis that includes Serato data
      const analysis = await musicService.getTrackAnalysis(track.filepath);
      
      if (analysis.hot_cues && analysis.hot_cues.length > 0) {
        console.log('🎛️ DJ MIND: Found Serato hot cues!', {
          count: analysis.hot_cues.length,
          cues: analysis.hot_cues.map(cue => ({
            name: cue.name,
            time: cue.time.toFixed(2),
            type: cue.type
          }))
        });

        const existingCues = state.hotCues[track.filepath] || [];
        const importedCues: HotCue[] = analysis.hot_cues.map(seratoCue => ({
          id: `serato-${seratoCue.index}-${track.filepath}`,
          name: `🎛️ ${seratoCue.name}`, // Prefix to indicate Serato import
          time: seratoCue.time,
          color: seratoCue.color,
          type: seratoCue.type as HotCue['type']
        }));

        // Merge with existing cues, avoiding duplicates based on time
        const allCues = [...existingCues];
        importedCues.forEach(importedCue => {
          const timeThreshold = 0.5; // 500ms tolerance for duplicate detection
          const isDuplicate = existingCues.some(existing => 
            Math.abs(existing.time - importedCue.time) < timeThreshold
          );
          
          if (!isDuplicate) {
            allCues.push(importedCue);
          }
        });

        // Sort by time
        allCues.sort((a, b) => a.time - b.time);

        setState(prev => ({
          ...prev,
          hotCues: {
            ...prev.hotCues,
            [track.filepath]: allCues
          }
        }));

        console.log('🎛️ DJ MIND: Serato hot cues imported!', {
          imported: importedCues.length,
          existing: existingCues.length,
          total: allCues.length,
          seratoAvailable: analysis.serato_data?.serato_available || false
        });

        return {
          imported: importedCues.length,
          total: allCues.length,
          hasSeratoData: true
        };
      } else {
        console.log('🎛️ DJ MIND: No Serato hot cues found for this track');
        return {
          imported: 0,
          total: (state.hotCues[track.filepath] || []).length,
          hasSeratoData: analysis.serato_data?.serato_available || false
        };
      }
    } catch (error) {
      console.error('🎛️ DJ MIND: Error importing Serato hot cues:', error);
      return {
        imported: 0,
        total: (state.hotCues[track.filepath] || []).length,
        hasSeratoData: false,
        error: error instanceof Error ? error.message : 'Unknown error'
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
    
    setState(prev => ({
      ...prev,
      bpmSyncEnabled: enabled,
      sourceBpm: currentBpm,
      targetBpm: targetBpm,
      syncRatio
    }));
    
    console.log('🎧 DJ MIND: BPM Sync', {
      enabled,
      currentBpm,
      targetBpm,
      syncRatio: syncRatio.toFixed(3),
      pitchChange: `${((syncRatio - 1) * 100).toFixed(1)}%`
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
      type
    };
    
    setState(prev => ({
      ...prev,
      hotCues: {
        ...prev.hotCues,
        [trackId]: [...existingCues, newCue]
      }
    }));
    
    console.log('🎧 DJ MIND: Hot cue added', { trackId, name, time, type });
  };

  const jumpToHotCue = (cue: HotCue) => {
    if (!audioRef.current) return;
    
    audioRef.current.currentTime = cue.time;
    
    if (cue.type === 'loop') {
      setState(prev => ({
        ...prev,
        loopActive: true,
        loopStart: cue.time,
        loopEnd: cue.time + 4 // 4-second loop default
      }));
    }
    
    console.log('🎧 DJ MIND: Jumped to hot cue', { name: cue.name, time: cue.time });
  };

  const applyTransitionEffect = (effect: TransitionEffect) => {
    if (!audioContextRef.current || !filterRef.current || !delayRef.current) return;
    
    const context = audioContextRef.current;
    const now = context.currentTime;
    
    setState(prev => ({
      ...prev,
      currentEffects: [...prev.currentEffects, effect]
    }));
    
    switch (effect.type) {
      case 'filter':
        // Sweep filter during transition
        const startFreq = effect.intensity > 0.5 ? 20000 : 100; // High-pass or low-pass
        const endFreq = effect.intensity > 0.5 ? 100 : 20000;
        
        filterRef.current.type = effect.intensity > 0.5 ? 'highpass' : 'lowpass';
        filterRef.current.frequency.setValueAtTime(startFreq, now);
        filterRef.current.frequency.exponentialRampToValueAtTime(endFreq, now + effect.duration);
        
        console.log('🎧 DJ MIND: Filter sweep applied', {
          type: filterRef.current.type,
          startFreq,
          endFreq,
          duration: effect.duration
        });
        break;
        
      case 'echo':
        // Echo effect for transition
        delayRef.current.delayTime.setValueAtTime(0.125, now); // 1/8 note delay
        const feedback = context.createGain();
        feedback.gain.setValueAtTime(effect.intensity * 0.7, now);
        
        delayRef.current.connect(feedback);
        feedback.connect(delayRef.current);
        
        // Fade out echo
        setTimeout(() => {
          feedback.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 1);
        }, effect.duration * 1000);
        
        console.log('🎧 DJ MIND: Echo effect applied', {
          delayTime: '1/8 note',
          feedback: effect.intensity * 0.7,
          duration: effect.duration
        });
        break;
        
      case 'reverse':
        // Reverse effect simulation (would need AudioWorklet for true reverse)
        console.log('🎧 DJ MIND: Reverse effect triggered - would need custom AudioWorklet');
        break;
        
      case 'loop':
        if (audioRef.current) {
          const currentTime = audioRef.current.currentTime;
          setState(prev => ({
            ...prev,
            loopActive: true,
            loopStart: currentTime,
            loopEnd: currentTime + (effect.duration || 1)
          }));
          console.log('🎧 DJ MIND: Loop activated', {
            start: currentTime,
            end: currentTime + (effect.duration || 1)
          });
        }
        break;
        
      case 'scratch':
        // Scratch simulation using rapid playback rate changes
        console.log('🎧 DJ MIND: Scratch effect triggered');
        scratchEffect(effect.intensity, effect.duration);
        break;
    }
    
    // Remove effect after duration
    setTimeout(() => {
      setState(prev => ({
        ...prev,
        currentEffects: prev.currentEffects.filter(e => e !== effect)
      }));
    }, effect.duration * 1000);
  };

  const scratchEffect = (intensity: number, duration: number) => {
    if (!audioRef.current) return;
    
    const originalRate = audioRef.current.playbackRate;
    const scratchPattern = [1.5, 0.5, 2.0, 0.3, 1.8, 0.7, 1.0]; // Scratch pattern
    let step = 0;
    
    const scratchInterval = setInterval(() => {
      if (audioRef.current && step < scratchPattern.length) {
        const rate = originalRate * (scratchPattern[step] * intensity);
        audioRef.current.playbackRate = rate;
        step++;
      } else {
        if (audioRef.current) {
          audioRef.current.playbackRate = originalRate;
        }
        clearInterval(scratchInterval);
        console.log('🎧 DJ MIND: Scratch effect complete');
      }
    }, (duration * 1000) / scratchPattern.length);
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
      optimalTransitionTime: optimalTransitionTime.toFixed(1)
    });
    
    return optimalTransitionTime;
  };

  // Enhanced transition with creative effects
  const startCreativeTransition = async () => {
    if (!audioRef.current || !nextAudioRef.current || !state.nextTrack || !state.currentTrack) return;

    console.log('🎧 DJ MIND: 🎨 STARTING CREATIVE TRANSITION 🎨', {
      from: state.currentTrack.title || state.currentTrack.filename,
      to: state.nextTrack.title || state.nextTrack.filename,
      currentBpm: state.currentTrack.bpm,
      nextBpm: state.nextTrack.bpm,
      effects: state.currentEffects.length
    });

    // Apply BPM sync if enabled and different BPMs
    if (state.bpmSyncEnabled && state.currentTrack.bpm && state.nextTrack.bpm) {
      await setBpmSync(true, state.nextTrack);
    }

    // Choose creative effect based on BPM difference and track characteristics
    const bpmDiff = Math.abs((state.currentTrack.bpm || 120) - (state.nextTrack.bpm || 120));
    let transitionEffect: TransitionEffect;

    if (bpmDiff > 20) {
      // Large BPM difference - use dramatic filter sweep
      transitionEffect = {
        type: 'filter',
        intensity: 0.8,
        duration: state.crossfadeDuration * 0.8
      };
    } else if (bpmDiff > 10) {
      // Medium BPM difference - use echo effect
      transitionEffect = {
        type: 'echo',
        intensity: 0.6,
        duration: state.crossfadeDuration * 0.6
      };
    } else {
      // Similar BPM - use subtle loop or scratch
      transitionEffect = {
        type: Math.random() > 0.5 ? 'loop' : 'scratch',
        intensity: 0.4,
        duration: state.crossfadeDuration * 0.3
      };
    }

    // Apply the effect
    applyTransitionEffect(transitionEffect);

    // Continue with standard crossfade
    await startTransition();
  };

  const contextValue: AudioPlayerContextType = {
    // State values
    currentTrack: state.currentTrack,
    isPlaying: state.isPlaying,
    duration: state.duration,
    currentTime: state.currentTime,
    volume: state.volume,
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
    toggleShuffle,
    toggleRepeat: () => {
      const modes: ('none' | 'one' | 'all')[] = ['none', 'one', 'all'];
      const currentIndex = modes.indexOf(state.repeat);
      const nextMode = modes[(currentIndex + 1) % modes.length];
      setRepeat(nextMode);
    },
    addToQueue,
    removeFromQueue,
    clearQueue,
    moveQueueItem: moveTrackInQueue,
    toggleDjMode,
    setAutoTransition: toggleAutoTransition,
    setTransitionTime,
    setCrossfadeDuration,
    forceTransition,
    
    // Enhanced DJ functions
    setBpmSync,
    addHotCue,
    jumpToHotCue,
    applyTransitionEffect,
    toggleBeatAlignment: () => setState(prev => ({ ...prev, beatAlignment: !prev.beatAlignment })),
    setPitchShift: (pitch: number) => {
      setState(prev => ({ ...prev, pitchShift: pitch }));
      // Apply pitch shift to audio elements
      const pitchRatio = Math.pow(2, pitch / 1200); // Convert cents to ratio
      if (audioRef.current) audioRef.current.playbackRate = state.syncRatio * pitchRatio;
      if (nextAudioRef.current) nextAudioRef.current.playbackRate = state.syncRatio * pitchRatio;
    },
    triggerScratch: (intensity: number = 0.8) => applyTransitionEffect({
      type: 'scratch',
      intensity,
      duration: 1.0
    }),
    triggerEcho: (intensity: number = 0.6) => applyTransitionEffect({
      type: 'echo',
      intensity,
      duration: 2.0
    }),
    triggerFilter: (intensity: number = 0.7) => applyTransitionEffect({
      type: 'filter',
      intensity,
      duration: 3.0
    }),
  };

  return (
    <AudioPlayerContext.Provider value={contextValue}>
      {children}
    </AudioPlayerContext.Provider>
  );
}; 
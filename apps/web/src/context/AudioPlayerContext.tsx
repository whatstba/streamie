'use client';

import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';
import { musicService } from '@/services/musicService';
import { aiService, type DJSet, type DJSetTrack, type DJSetPlaybackStatus } from '@/services/aiService';
import { useWebSocket, type ServerMessage } from '@/hooks/useWebSocket';

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

interface AudioPlayerState {
  // Server streaming state
  isServerStreaming: boolean;
  djSet: DJSet | null;
  playbackStatus: DJSetPlaybackStatus | null;
  hasDJSet: boolean; // Flag to indicate a DJ set exists (for WebSocket connection)
  
  // Basic playback state
  isPlaying: boolean;
  isLoading: boolean;
  isReadyToPlay: boolean; // New flag for when DJ set is loaded but not playing
  volume: number;
  isMuted: boolean;
  error: string | null;
  
  // WebSocket connection state
  wsConnected: boolean;
  wsError: string | null;
  
  // Legacy compatibility (minimal)
  currentTrack: Track | null;
  queue: Track[];
  djMode: boolean;
}

interface AudioPlayerContextType extends AudioPlayerState {
  // Server streaming actions
  playDJSet: (djSet: DJSet) => Promise<void>;
  stopDJSet: () => Promise<void>;
  pauseDJSet: () => Promise<void>;
  resumeDJSet: () => Promise<void>;
  manualPlay: () => Promise<void>;
  
  // Basic controls
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  
  // Legacy compatibility
  playTrack: (track: Track, queue?: Track[]) => Promise<void>;
  toggleDjMode: () => void;
  addToQueue: (track: Track) => void;
  
  // Audio element ref for seeking
  audioRef: React.RefObject<HTMLAudioElement | null>;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined);

export const AudioPlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AudioPlayerState>({
    isServerStreaming: false,
    djSet: null,
    playbackStatus: null,
    hasDJSet: false,
    isPlaying: false,
    isLoading: false,
    isReadyToPlay: false,
    volume: 0.7,
    isMuted: false,
    error: null,
    wsConnected: false,
    wsError: null,
    currentTrack: null,
    queue: [],
    djMode: true, // Always in DJ mode now
  });

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const wsRef = useRef<{ sendMessage: (msg: any) => void } | null>(null);
  const stateRef = useRef(state);
  
  // Keep stateRef in sync with state
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Update playback status from WebSocket
  const updatePlaybackStatus = useCallback((status: DJSetPlaybackStatus) => {
    setState(prev => {
      // Always defer to backend state as source of truth
      const backendIsPlaying = status.is_playing && !status.is_paused;
      
      // Log if there's a mismatch
      if (prev.isPlaying !== backendIsPlaying) {
        console.log(`State sync: Frontend was ${prev.isPlaying}, backend is ${backendIsPlaying}`);
      }
      
      // Build current track safely
      let currentTrack = prev.currentTrack;
      if (status.current_track_order !== null && status.current_track_order !== undefined && prev.djSet && status.current_track_order > 0) {
        const trackIndex = status.current_track_order - 1;
        const track = prev.djSet.tracks[trackIndex];
        if (track) {
          currentTrack = {
            filename: track.filepath.split('/').pop() || '',
            filepath: track.filepath,
            duration: track.end_time - track.start_time,
            title: track.title,
            artist: track.artist,
            album: track.album || null,
            genre: track.genre || null,
            year: null,
            has_artwork: false,
            bpm: track.bpm,
          };
        }
      }
      
      return {
        ...prev,
        playbackStatus: status,
        isPlaying: backendIsPlaying,
        currentTrack,
      };
    });
  }, []);
  
  // Memoize WebSocket callbacks to prevent recreating them on every render
  const handleWebSocketMessage = useCallback((message: ServerMessage) => {
    // Handle different message types
    if (message.type === 'playback_status' && message.data) {
      console.log('📡 WebSocket: Processing status update', message.data);
      updatePlaybackStatus(message.data as DJSetPlaybackStatus);
    } else if (message.type === 'connected') {
      console.log('✅ WebSocket connected:', message.sessionId);
    } else if (message.type === 'error') {
      console.error('❌ WebSocket error:', message.message);
      setState(prev => ({ ...prev, error: message.message || 'WebSocket error' }));
    }
  }, [updatePlaybackStatus]);

  const handleWebSocketOpen = useCallback(() => {
    console.log('✅ WebSocket connection opened');
    setState(prev => ({ ...prev, wsConnected: true, wsError: null }));
  }, []);

  const handleWebSocketClose = useCallback(() => {
    console.log('🔌 WebSocket connection closed');
    setState(prev => ({ ...prev, wsConnected: false }));
  }, []);

  const handleWebSocketError = useCallback(() => {
    console.error('❌ WebSocket connection error');
    setState(prev => ({ ...prev, wsError: 'WebSocket connection failed' }));
  }, []);
  
  // Use WebSocket for real-time updates and control
  const { 
    isConnected: wsConnected,
    sendMessage,
    connectionState
  } = useWebSocket({
    url: 'ws://localhost:8000/api/dj-set/playback/ws',
    enabled: state.isServerStreaming || state.hasDJSet || !!state.djSet, // Connect early when DJ set exists
    onMessage: handleWebSocketMessage,
    onOpen: handleWebSocketOpen,
    onClose: handleWebSocketClose,
    onError: handleWebSocketError
  });
  
  // Store sendMessage ref for use in other functions
  useEffect(() => {
    wsRef.current = { sendMessage };
  }, [sendMessage]);

  // Initialize audio element
  useEffect(() => {
    console.log('Initializing audio element');
    const audio = new Audio();
    audio.volume = state.volume;
    audio.crossOrigin = 'anonymous'; // Enable CORS
    
    // Define event handlers for proper cleanup
    const handleError = (e: Event) => {
      console.error('Audio streaming error:', e);
      const audioElement = e.target as HTMLAudioElement;
      let errorMessage = 'Failed to stream audio.';
      
      if (audioElement.error) {
        console.error('Media error code:', audioElement.error.code);
        console.error('Media error message:', audioElement.error.message);
        
        // Decode error codes
        switch (audioElement.error.code) {
          case 1: // MEDIA_ERR_ABORTED
            errorMessage = 'Audio playback was aborted.';
            break;
          case 2: // MEDIA_ERR_NETWORK
            errorMessage = 'Network error while loading audio.';
            break;
          case 3: // MEDIA_ERR_DECODE
            errorMessage = 'Audio decoding error.';
            break;
          case 4: // MEDIA_ERR_SRC_NOT_SUPPORTED
            errorMessage = 'Audio source not supported. Check if backend is running on http://localhost:8000';
            break;
        }
      }
      
      setState(prev => ({ 
        ...prev, 
        isPlaying: false, 
        isLoading: false,
        error: errorMessage
      }));
    };
    
    const handleLoadStart = () => {
      console.log('Started loading audio stream');
    };
    
    const handleCanPlay = () => {
      console.log('Audio stream ready to play');
      setState(prev => ({ ...prev, isLoading: false }));
    };
    
    const handleWaiting = () => {
      console.log('Audio stream buffering...');
      setState(prev => ({ ...prev, isLoading: true }));
    };
    
    const handlePlaying = () => {
      console.log('Audio stream playing');
      setState(prev => ({ ...prev, isPlaying: true, isLoading: false }));
    };
    
    // Add event listeners for syncing with backend
    const handleTimeUpdate = () => {
      // Only send time updates for DJ sets, not regular tracks
      const currentState = stateRef.current;
      if (wsRef.current && currentState.djSet && currentState.isServerStreaming) {
        const elapsed = audio.currentTime;
        // Throttle updates to every second normally, but more frequently during transitions
        const lastUpdate = (audio as any)._lastTimeUpdate || 0;
        
        // Check if we're in or near a transition (within 10 seconds)
        let updateInterval = 1.0; // Default 1 second
        if (currentState.nextTransition) {
          const timeToTransition = currentState.nextTransition.start_time - elapsed;
          if (timeToTransition <= 10 && timeToTransition >= -10) {
            updateInterval = 0.2; // Update every 200ms during transitions
          }
        }
        
        if (elapsed - lastUpdate >= updateInterval) {
          (audio as any)._lastTimeUpdate = elapsed;
          // Check WebSocket is ready before sending
          if (wsRef.current.sendMessage) {
            wsRef.current.sendMessage({ 
              type: 'time_update', 
              elapsed_time: elapsed,
              setId: currentState.djSet.id 
            });
          }
        }
      }
    };
    
    const handlePlay = () => {
      console.log('Audio element play event');
      const currentState = stateRef.current;
      if (wsRef.current && currentState.djSet && currentState.isServerStreaming) {
        // Check WebSocket is ready before sending
        if (wsRef.current.sendMessage) {
          wsRef.current.sendMessage({ 
            type: 'audio_playing', 
            elapsed_time: audio.currentTime,
            setId: currentState.djSet.id 
          });
        }
      }
    };
    
    const handlePause = () => {
      console.log('Audio element pause event');
      const currentState = stateRef.current;
      if (wsRef.current && currentState.djSet && currentState.isServerStreaming) {
        // Check WebSocket is ready before sending
        if (wsRef.current.sendMessage) {
          wsRef.current.sendMessage({ 
            type: 'audio_paused', 
            elapsed_time: audio.currentTime,
            setId: currentState.djSet.id 
          });
        }
      }
    };
    
    // Add all event listeners
    audio.addEventListener('error', handleError);
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('waiting', handleWaiting);
    audio.addEventListener('playing', handlePlaying);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    
    audioRef.current = audio;

    return () => {
      if (audioRef.current) {
        // Remove event listeners to prevent memory leaks
        audioRef.current.removeEventListener('error', handleError);
        audioRef.current.removeEventListener('loadstart', handleLoadStart);
        audioRef.current.removeEventListener('canplay', handleCanPlay);
        audioRef.current.removeEventListener('waiting', handleWaiting);
        audioRef.current.removeEventListener('playing', handlePlaying);
        audioRef.current.removeEventListener('timeupdate', handleTimeUpdate);
        audioRef.current.removeEventListener('play', handlePlay);
        audioRef.current.removeEventListener('pause', handlePause);
        
        audioRef.current.pause();
        audioRef.current.src = '';
      }
      // Status polling is handled by the separate useEffect
    };
  }, []);

  // Update volume
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = state.isMuted ? 0 : state.volume;
    }
  }, [state.volume, state.isMuted]);

  // WebSocket handles all real-time updates - no polling needed!

  const playDJSet = useCallback(async (djSet: DJSet) => {
    console.log('playDJSet called with DJ set:', { id: djSet.id, name: djSet.name });
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      // First, load the pre-rendered audio file directly
      console.log('Loading pre-rendered audio file directly');
      
      // Set up audio streaming from the pre-rendered file
      if (audioRef.current) {
        // Use pre-rendered streaming endpoint for complete mixed audio
        const streamUrl = `http://localhost:8000/api/audio/stream/file/${djSet.id}`;
        console.log('Setting pre-rendered audio stream URL:', streamUrl);
        audioRef.current.src = streamUrl;
        
        // Reset audio element to ensure clean state
        audioRef.current.load();
        
        // Don't auto-play - wait for user interaction to avoid browser autoplay policy
        console.log('DJ set loaded and ready to play. User must click play button.');
        console.log('Audio element state:', {
          src: audioRef.current.src,
          readyState: audioRef.current.readyState,
          error: audioRef.current.error
        });
      } else {
        console.error('Audio element ref is null!');
        throw new Error('Audio element not initialized');
      }

      // Update state to show ready
      setState(prev => {
        const newState = {
          ...prev,
          isServerStreaming: true,
          djSet,
          hasDJSet: true, // Set flag to enable WebSocket connection
          isPlaying: false, // Keep false - user must click play
          isLoading: false,
          isReadyToPlay: true, // Set ready flag
          error: null,
          currentTrack: djSet.tracks[0] ? {
          filename: djSet.tracks[0].filepath.split('/').pop() || '',
          filepath: djSet.tracks[0].filepath,
          duration: djSet.tracks[0].end_time - djSet.tracks[0].start_time,
          title: djSet.tracks[0].title,
          artist: djSet.tracks[0].artist,
          album: djSet.tracks[0].album || null,
          genre: djSet.tracks[0].genre || null,
          year: null,
          has_artwork: false,
          bpm: djSet.tracks[0].bpm,
        } : null,
        };
        console.log('Setting DJ set ready state:', {
          isLoading: newState.isLoading,
          isServerStreaming: newState.isServerStreaming,
          isReadyToPlay: newState.isReadyToPlay,
          currentTrack: !!newState.currentTrack
        });
        return newState;
      });

      // The backend now initializes playback state during generation
      // So we don't need to register here - just load the audio

    } catch (error) {
      console.error('Error loading DJ set:', error);
      console.error('Error details:', {
        error,
        djSetId: djSet.id,
        audioRefExists: !!audioRef.current
      });
      
      setState(prev => ({ 
        ...prev, 
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load DJ set audio'
      }));
      throw error;
    }
  }, []);

  const stopDJSet = useCallback(async () => {
    try {
      // Send stop command via WebSocket
      if (wsRef.current) {
        wsRef.current.sendMessage({ type: 'stop' });
      }
      
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }

      setState(prev => ({
        ...prev,
        isServerStreaming: false,
        djSet: null,
        playbackStatus: null,
        hasDJSet: false,
        isPlaying: false,
        isReadyToPlay: false,
        currentTrack: null,
      }));
    } catch (error) {
      console.error('Error stopping DJ set:', error);
    }
  }, []);

  const pauseDJSet = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      // Send pause command via WebSocket
      if (wsRef.current) {
        wsRef.current.sendMessage({ type: 'pause' });
      }
      
      if (audioRef.current) {
        audioRef.current.pause();
      }

      // Don't set isPlaying - WebSocket will update it from backend
      setState(prev => ({ ...prev, isLoading: false }));
    } catch (error) {
      console.error('Error pausing DJ set:', error);
      setState(prev => ({ 
        ...prev, 
        isLoading: false,
        error: 'Failed to pause playback'
      }));
    }
  }, []);

  const resumeDJSet = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true }));
      
      // For now, just use play command via WebSocket
      // Backend doesn't have a separate resume concept
      if (wsRef.current && state.djSet) {
        wsRef.current.sendMessage({ 
          type: 'play', 
          setId: state.djSet.id 
        });
      }
      
      if (audioRef.current) {
        // Try to play the audio
        const playPromise = audioRef.current.play();
        if (playPromise !== undefined) {
          try {
            await playPromise;
            // Don't set isPlaying - WebSocket will update it from backend
            setState(prev => ({ 
              ...prev, 
              isReadyToPlay: false,
              isLoading: false,
              error: null 
            }));
          } catch (error) {
            console.error('Resume playback failed:', error);
            setState(prev => ({ 
              ...prev, 
              isLoading: false,
              error: 'Click play button to resume audio'
            }));
          }
        }
      }
    } catch (error) {
      console.error('Error resuming DJ set:', error);
      setState(prev => ({ 
        ...prev, 
        isLoading: false,
        error: 'Failed to resume playback'
      }));
    }
  }, [state.djSet]);

  const manualPlay = useCallback(async () => {
    console.log('manualPlay called', {
      audioRef: !!audioRef.current,
      src: audioRef.current?.src,
      paused: audioRef.current?.paused,
      readyState: audioRef.current?.readyState,
      djSet: !!state.djSet,
      isServerStreaming: state.isServerStreaming
    });
    
    if (audioRef.current && audioRef.current.src) {
      try {
        if (audioRef.current.paused) {
          // Reset the audio element if needed
          if (audioRef.current.readyState === 0 || audioRef.current.error) {
            console.log('Resetting audio element before play');
            audioRef.current.load();
            await new Promise(resolve => setTimeout(resolve, 200));
          }
          
          try {
            console.log('Attempting to play audio...');
            
            // If this is a DJ set, notify the backend FIRST via WebSocket
            if (state.isServerStreaming && state.djSet) {
              console.log('Notifying backend that DJ set is playing...');
              setState(prev => ({ ...prev, isLoading: true, error: null }));
              
              try {
                // Send play command via WebSocket
                if (wsRef.current) {
                  wsRef.current.sendMessage({ 
                    type: 'play', 
                    setId: state.djSet.id 
                  });
                }
                
                // Play audio locally
                await audioRef.current.play();
                console.log('Audio playback started successfully');
                // Update isPlaying immediately for better responsiveness
                setState(prev => ({ ...prev, isPlaying: true, isReadyToPlay: false, isLoading: false }));
              } catch (error) {
                console.error('Failed to start playback:', error);
                setState(prev => ({ 
                  ...prev, 
                  isLoading: false,
                  error: 'Failed to start playback. Please try again.'
                }));
                return;
              }
            } else {
              // For non-DJ set audio, just play locally
              await audioRef.current.play();
              setState(prev => ({ ...prev, isPlaying: true, isReadyToPlay: false, error: null }));
            }
          } catch (error: any) {
            console.error('Manual play failed:', error);
            console.error('Error details:', {
              name: error.name,
              message: error.message,
              audioSrc: audioRef.current.src,
              readyState: audioRef.current.readyState,
              networkState: audioRef.current.networkState
            });
            setState(prev => ({ 
              ...prev, 
              isPlaying: false, 
              error: error.name === 'NotAllowedError' 
                ? 'Please click play again to start audio' 
                : `Playback error: ${error.message}`
            }));
          }
        } else {
          // Pause logic
          if (state.isServerStreaming && state.djSet) {
            // For DJ sets, notify backend first via WebSocket
            setState(prev => ({ ...prev, isLoading: true }));
            try {
              // Send pause command via WebSocket
              if (wsRef.current) {
                wsRef.current.sendMessage({ type: 'pause' });
              }
              audioRef.current.pause();
              // Update isPlaying immediately for better responsiveness
              setState(prev => ({ ...prev, isPlaying: false, isLoading: false }));
            } catch (error) {
              console.error('Failed to pause:', error);
              setState(prev => ({ 
                ...prev, 
                isLoading: false,
                error: 'Failed to pause playback'
              }));
            }
          } else {
            // For non-DJ set audio, just pause locally
            audioRef.current.pause();
            setState(prev => ({ ...prev, isPlaying: false }));
          }
        }
      } catch (error) {
        console.error('Manual play failed:', error);
        setState(prev => ({ 
          ...prev, 
          isPlaying: false,
          error: 'Failed to start playback. Click to retry.'
        }));
      }
    } else {
      console.error('manualPlay: No audio element or src!', {
        hasAudioRef: !!audioRef.current,
        src: audioRef.current?.src || 'no src'
      });
      setState(prev => ({ 
        ...prev, 
        error: 'Audio not ready. Please try again.'
      }));
    }
  }, [state.isServerStreaming, state.djSet]);

  const setVolume = useCallback((volume: number) => {
    setState(prev => ({ ...prev, volume }));
  }, []);

  const toggleMute = useCallback(() => {
    setState(prev => ({ ...prev, isMuted: !prev.isMuted }));
  }, []);

  // Play individual track by creating a single-track DJ set
  const playTrack = useCallback(async (track: Track, queue?: Track[]) => {
    setState(prev => ({ ...prev, isLoading: true }));
    
    try {
      // For regular track playback, just use direct file streaming
      // No need to involve the backend DJ system
      
      if (audioRef.current) {
        // Stop any existing playback
        audioRef.current.pause();
        audioRef.current.src = '';
        
        // Set up direct file streaming
        const streamUrl = musicService.getStreamUrl(track.filepath);
        console.log('Setting audio stream URL for direct playback:', streamUrl);
        audioRef.current.src = streamUrl;
        
        // Handle autoplay policy - try to play with user gesture context
        const playPromise = audioRef.current.play();
        
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              console.log('Audio playback started successfully');
              setState(prev => ({ ...prev, isPlaying: true }));
            })
            .catch(error => {
              console.error('Autoplay failed:', error);
              
              if (error.name === 'NotAllowedError') {
                // Browser autoplay policy blocked playback
                setState(prev => ({ 
                  ...prev, 
                  isPlaying: false,
                  error: 'Click play button to start audio (browser requires user interaction)'
                }));
              } else if (error.name === 'NotSupportedError') {
                setState(prev => ({ 
                  ...prev, 
                  isPlaying: false,
                  error: 'Audio format not supported by browser'
                }));
              } else {
                setState(prev => ({ 
                  ...prev, 
                  isPlaying: false,
                  error: `Playback error: ${error.message}`
                }));
              }
            });
        }
      }

      setState(prev => ({
        ...prev,
        isServerStreaming: false,  // Not using server streaming for regular tracks
        djSet: null,
        hasDJSet: false,
        isPlaying: true,
        isLoading: false,
        currentTrack: track,
        queue: queue || [],
        error: null,
      }));
    } catch (error) {
      console.error('Error playing track:', error);
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const toggleDjMode = useCallback(() => {
    // DJ mode is always on now
    console.warn('DJ mode is always enabled with server-side streaming');
  }, []);

  const addToQueue = useCallback((track: Track) => {
    console.warn('Queue management is handled server-side. Generate a new DJ set instead.');
  }, []);

  const contextValue: AudioPlayerContextType = {
    ...state,
    playDJSet,
    stopDJSet,
    pauseDJSet,
    resumeDJSet,
    manualPlay,
    setVolume,
    toggleMute,
    playTrack,
    toggleDjMode,
    addToQueue,
    audioRef,
  };

  return (
    <AudioPlayerContext.Provider value={contextValue}>
      {children}
    </AudioPlayerContext.Provider>
  );
};

export const useAudioPlayer = () => {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    throw new Error('useAudioPlayer must be used within AudioPlayerProvider');
  }
  return context;
};
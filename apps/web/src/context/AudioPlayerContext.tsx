'use client';

import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';
import { musicService } from '@/services/musicService';
import { aiService, type DJSet, type DJSetTrack, type DJSetPlaybackStatus } from '@/services/aiService';

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
  
  // Basic playback state
  isPlaying: boolean;
  isLoading: boolean;
  volume: number;
  isMuted: boolean;
  error: string | null;
  
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
}

const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined);

export const AudioPlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AudioPlayerState>({
    isServerStreaming: false,
    djSet: null,
    playbackStatus: null,
    isPlaying: false,
    isLoading: false,
    volume: 0.7,
    isMuted: false,
    error: null,
    currentTrack: null,
    queue: [],
    djMode: true, // Always in DJ mode now
  });

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const statusIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Initialize audio element
  useEffect(() => {
    const audio = new Audio();
    audio.volume = state.volume;
    audio.crossOrigin = 'anonymous'; // Enable CORS
    
    // Add error handling
    audio.addEventListener('error', (e) => {
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
    });
    
    audio.addEventListener('loadstart', () => {
      console.log('Started loading audio stream');
    });
    
    audio.addEventListener('canplay', () => {
      console.log('Audio stream ready to play');
      setState(prev => ({ ...prev, isLoading: false }));
    });
    
    audio.addEventListener('waiting', () => {
      console.log('Audio stream buffering...');
      setState(prev => ({ ...prev, isLoading: true }));
    });
    
    audio.addEventListener('playing', () => {
      console.log('Audio stream playing');
      setState(prev => ({ ...prev, isPlaying: true, isLoading: false }));
    });
    
    audioRef.current = audio;

    return () => {
      if (audioRef.current) {
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

  // Poll for playback status when streaming
  useEffect(() => {
    if (state.isServerStreaming) {
      const pollStatus = async () => {
        try {
          const status = await aiService.getDJSetPlaybackStatus();
          setState(prev => ({
            ...prev,
            playbackStatus: status,
            isPlaying: status.is_playing && !status.is_paused,
          }));
        } catch (error) {
          console.error('Error polling playback status:', error);
        }
      };

      // Poll immediately
      pollStatus();
      
      // Then poll every 2 seconds
      statusIntervalRef.current = setInterval(pollStatus, 2000);
    } else {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }
    }

    return () => {
      // Status polling is handled by the separate useEffect
    };
  }, [state.isServerStreaming]);

  const playDJSet = useCallback(async (djSet: DJSet) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      // Start server playback using the existing DJ set
      const response = await aiService.playDJSet(djSet.id);

      if (response.status !== 'playing') {
        throw new Error(response.error || 'Failed to start DJ set playback');
      }

      // Pre-rendering happens server-side during the play request
      // The server will return an error if pre-rendering fails
      // So if we get here, the file should be ready
      console.log('Server confirmed playback started, pre-rendered file should be ready');
      
      // Give the server a moment to ensure file is fully written
      await new Promise(resolve => setTimeout(resolve, 500));

      // Set up audio streaming from the pre-rendered file
      if (audioRef.current) {
        // Use pre-rendered streaming endpoint for complete mixed audio
        const streamUrl = `http://localhost:8000/api/audio/stream/prerendered/${djSet.id}`;
        console.log('Setting pre-rendered audio stream URL:', streamUrl);
        audioRef.current.src = streamUrl;
        
        // Reset audio element to ensure clean state
        audioRef.current.load();
        
        // Don't auto-play - wait for user interaction to avoid browser autoplay policy
        console.log('DJ set loaded and ready to play. User must click play button.');
        setState(prev => ({ 
          ...prev, 
          isPlaying: false,
          isLoading: false,
          error: null 
        }));
      }

      setState(prev => ({
        ...prev,
        isServerStreaming: true,
        djSet,
        isPlaying: true,
        isLoading: false,
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
      }));
    } catch (error) {
      console.error('Error playing DJ set:', error);
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const stopDJSet = useCallback(async () => {
    try {
      await aiService.stopDJSetPlayback();
      
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }

      setState(prev => ({
        ...prev,
        isServerStreaming: false,
        djSet: null,
        playbackStatus: null,
        isPlaying: false,
        currentTrack: null,
      }));
    } catch (error) {
      console.error('Error stopping DJ set:', error);
    }
  }, []);

  const pauseDJSet = useCallback(async () => {
    try {
      await aiService.pauseDJSetPlayback();
      
      if (audioRef.current) {
        audioRef.current.pause();
      }

      setState(prev => ({ ...prev, isPlaying: false }));
    } catch (error) {
      console.error('Error pausing DJ set:', error);
    }
  }, []);

  const resumeDJSet = useCallback(async () => {
    try {
      await aiService.resumeDJSetPlayback();
      
      if (audioRef.current) {
        // Try to play the audio
        const playPromise = audioRef.current.play();
        if (playPromise !== undefined) {
          playPromise.catch(error => {
            console.error('Resume playback failed:', error);
            setState(prev => ({ 
              ...prev, 
              isPlaying: false,
              error: 'Click play button to resume audio'
            }));
          });
        }
      }

      setState(prev => ({ ...prev, isPlaying: true }));
    } catch (error) {
      console.error('Error resuming DJ set:', error);
    }
  }, []);

  const manualPlay = useCallback(async () => {
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
            await audioRef.current.play();
            setState(prev => ({ ...prev, isPlaying: true, error: null }));
          } catch (error: any) {
            console.error('Manual play failed:', error);
            setState(prev => ({ 
              ...prev, 
              isPlaying: false, 
              error: error.name === 'NotAllowedError' 
                ? 'Please click play again to start audio' 
                : `Playback error: ${error.message}`
            }));
          }
        } else {
          audioRef.current.pause();
          setState(prev => ({ ...prev, isPlaying: false }));
        }
      } catch (error) {
        console.error('Manual play failed:', error);
        setState(prev => ({ 
          ...prev, 
          isPlaying: false,
          error: 'Failed to start playback. Click to retry.'
        }));
      }
    }
  }, []);

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
'use client';

import React from 'react';
import { PlayIcon, PauseIcon, ForwardIcon, BackwardIcon } from '@heroicons/react/24/solid';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const AudioControls: React.FC = () => {
  const { 
    isPlaying, 
    isLoading, 
    currentTrack, 
    isServerStreaming,
    isReadyToPlay,
    pauseDJSet,
    resumeDJSet,
    stopDJSet,
    manualPlay,
    error,
  } = useAudioPlayer();

  // Debug logging (only in development)
  if (process.env.NODE_ENV === 'development') {
    console.log('AudioControls state:', {
      isLoading,
      isServerStreaming,
      currentTrack: !!currentTrack,
      isReadyToPlay,
      buttonDisabled: isLoading || (!isServerStreaming && !currentTrack && !isReadyToPlay)
    });
  }

  const handlePlayPause = () => {
    console.log('handlePlayPause called', { isServerStreaming, isReadyToPlay, isPlaying, error });
    
    if (isServerStreaming || isReadyToPlay) {
      if (isPlaying) {
        pauseDJSet();
      } else {
        // For initial play of a DJ set, always use manualPlay
        // because resumeDJSet expects the backend to already be playing
        manualPlay();
      }
    } else {
      // Regular track playback - use manualPlay which handles the audio element
      manualPlay();
    }
  };

  const handleStop = () => {
    if (isServerStreaming) {
      stopDJSet();
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Error message */}
      {error && (
        <div className="text-xs text-red-400 max-w-xs text-center">
          {error}
        </div>
      )}
      
      <div className="flex items-center gap-4">
        {isServerStreaming && (
          <button
            onClick={handleStop}
            className="text-red-400 hover:text-red-300 transition"
            title="Stop DJ Set"
          >
            <span className="text-sm font-medium">STOP</span>
          </button>
        )}

        <button
          onClick={handlePlayPause}
          disabled={isLoading || (!isServerStreaming && !currentTrack && !isReadyToPlay)}
          className={`p-2 rounded-full hover:scale-105 transition disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'bg-yellow-500 hover:bg-yellow-400' : 
            isReadyToPlay ? 'bg-green-500 hover:bg-green-400 animate-pulse' : 
            'bg-white'
          } ${isReadyToPlay ? 'scale-110' : ''}`}
          title={error ? 'Click to retry playback' : isReadyToPlay ? 'Click to start DJ set' : (isPlaying ? 'Pause' : 'Play')}
        >
          {isLoading ? (
            <div className="h-6 w-6 text-black flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-black"></div>
            </div>
          ) : isPlaying ? (
            <PauseIcon className="h-6 w-6 text-black" />
          ) : (
            <PlayIcon className="h-6 w-6 text-black" />
          )}
        </button>
      </div>
      
      {isReadyToPlay && !error && (
        <div className="text-xs text-green-400 max-w-xs text-center mt-2 animate-pulse">
          Click play to start your DJ set!
        </div>
      )}
      
      {error && (
        <div className="text-xs text-red-400 max-w-xs text-center mt-2">
          {error}
        </div>
      )}
    </div>
  );
};

export default AudioControls;

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
    pauseDJSet,
    resumeDJSet,
    stopDJSet,
    manualPlay,
    error,
  } = useAudioPlayer();

  const handlePlayPause = () => {
    if (isServerStreaming) {
      if (isPlaying) {
        pauseDJSet();
      } else {
        // If there's an error, try manual play first
        if (error) {
          manualPlay();
        } else {
          resumeDJSet();
        }
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
          disabled={isLoading || (!isServerStreaming && !currentTrack)}
          className={`p-2 rounded-full hover:scale-105 transition disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'bg-yellow-500 hover:bg-yellow-400' : 'bg-white'
          }`}
          title={error ? 'Click to retry playback' : (isPlaying ? 'Pause' : 'Play')}
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
      
      {error && (
        <div className="text-xs text-red-400 max-w-xs text-center mt-2">
          {error}
        </div>
      )}
    </div>
  );
};

export default AudioControls;

'use client';

import React from 'react';
import {
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  BackwardIcon,
} from '@heroicons/react/24/solid';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const AudioControls: React.FC = () => {
  const {
    isPlaying,
    isLoading,
    currentTrack,
    pause,
    play,
    skipToNext,
    skipToPrevious,
  } = useAudioPlayer();

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={skipToPrevious}
        disabled={!currentTrack}
        className="text-gray-400 hover:text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
        title="Previous Track"
      >
        <BackwardIcon className="h-5 w-5" />
      </button>

      <button
        onClick={handlePlayPause}
        disabled={!currentTrack || isLoading}
        className="p-2 bg-white rounded-full hover:scale-105 transition disabled:opacity-50 disabled:cursor-not-allowed"
        title={isPlaying ? 'Pause' : 'Play'}
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

      <button
        onClick={skipToNext}
        disabled={!currentTrack}
        className="text-gray-400 hover:text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
        title="Next Track"
      >
        <ForwardIcon className="h-5 w-5" />
      </button>
    </div>
  );
};

export default AudioControls; 
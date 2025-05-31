'use client';

import React from 'react';
import {
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  BackwardIcon,
} from '@heroicons/react/24/solid';
import { ArrowPathIcon, ArrowsRightLeftIcon } from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const AudioControls: React.FC = () => {
  const {
    isPlaying,
    isLoading,
    currentTrack,
    repeat,
    shuffle,
    pause,
    resume,
    skipToNext,
    previousTrack,
    setRepeat,
    toggleShuffle,
  } = useAudioPlayer();

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      resume();
    }
  };

  const handleRepeatClick = () => {
    const nextRepeatMode = repeat === 'none' ? 'all' : repeat === 'all' ? 'one' : 'none';
    setRepeat(nextRepeatMode);
  };

  const getRepeatIcon = () => {
    switch (repeat) {
      case 'one':
        return '1';
      case 'all':
        return '∞';
      default:
        return '';
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Secondary Controls */}
      <div className="flex items-center gap-4">
        <button
          onClick={toggleShuffle}
          className={`text-sm transition ${
            shuffle ? 'text-purple-400' : 'text-gray-400 hover:text-white'
          }`}
          title="Toggle Shuffle"
        >
          <ArrowsRightLeftIcon className="h-4 w-4" />
        </button>
        
        <button
          onClick={handleRepeatClick}
          className={`relative text-sm transition ${
            repeat !== 'none' ? 'text-purple-400' : 'text-gray-400 hover:text-white'
          }`}
          title={`Repeat: ${repeat}`}
        >
          <ArrowPathIcon className="h-4 w-4" />
          {repeat === 'one' && (
            <span className="absolute -top-1 -right-1 text-xs font-bold">1</span>
          )}
        </button>
      </div>

      {/* Main Controls */}
      <div className="flex items-center gap-4">
        <button
          onClick={previousTrack}
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
    </div>
  );
};

export default AudioControls; 
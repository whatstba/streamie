'use client';

import React, { useState } from 'react';
import { ForwardIcon } from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import AudioControls from './AudioControls';
import ProgressBar from './ProgressBar';
import VolumeControl from './VolumeControl';
import KeyboardShortcutsHelp from './KeyboardShortcutsHelp';
import QueueManager from './QueueManager';

const Player = () => {
  const {
    currentTrack,
    djMode,
    isTransitioning,
    transitionProgress,
    timeUntilTransition,
    autoTransition,
    setAutoTransition,
    forceTransition,
    nextTrack,
  } = useAudioPlayer();

  const formatTime = (seconds: number): string => {
    if (seconds <= 0) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-24 bg-zinc-900 border-t border-zinc-800 px-4 relative">
      {/* DJ Mode Transition Indicator */}
      {djMode && isTransitioning && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-zinc-800">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-100"
            style={{ width: `${transitionProgress * 100}%` }}
          />
        </div>
      )}

      <div className="max-w-screen-xl mx-auto h-full flex items-center justify-between gap-6">
        {/* Left Side - Mix Controls */}
        <div className="flex-1 min-w-0 max-w-sm">
          <div className="flex items-center gap-3">
            {/*   */}

            {nextTrack && !isTransitioning && (
              <button
                onClick={forceTransition}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition"
                title="Force transition now"
              >
                <ForwardIcon className="h-4 w-4" />
                Mix Now
              </button>
            )}
          </div>

          {/* DJ Mode Status */}
          {djMode && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              {/* <span className="px-2 py-0.5 bg-purple-600 rounded text-white font-medium">
                DJ MODE
              </span> */}
              {isTransitioning && (
                <span className="text-purple-400 animate-pulse">
                  Crossfading... {Math.round(transitionProgress * 100)}%
                </span>
              )}
              {!isTransitioning && timeUntilTransition > 0 && timeUntilTransition <= 60 && (
                <span className="text-orange-400">
                  Next mix in {formatTime(timeUntilTransition)}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Playback Controls */}
        <div className="flex flex-col items-center gap-2">
          <AudioControls />
          <ProgressBar />
        </div>

        {/* Right Side Controls */}
        <div className="flex items-center gap-4 flex-1 max-w-sm justify-end">
          <VolumeControl />
          <QueueManager />
          <KeyboardShortcutsHelp />
        </div>
      </div>
    </div>
  );
};

export default Player;

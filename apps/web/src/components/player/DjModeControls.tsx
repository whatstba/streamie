'use client';

import React, { useState } from 'react';
import {
  MusicalNoteIcon,
  Cog6ToothIcon,
  PlayIcon,
  PauseIcon,
  ForwardIcon,
} from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const DjModeControls: React.FC = () => {
  const {
    djMode,
    autoTransition,
    transitionTime,
    crossfadeDuration,
    isTransitioning,
    transitionProgress,
    nextTrack,
    timeUntilTransition,
    toggleDjMode,
    toggleAutoTransition,
    setTransitionTime,
    setCrossfadeDuration,
    forceTransition,
  } = useAudioPlayer();

  const [showSettings, setShowSettings] = useState(false);

  const formatTime = (seconds: number): string => {
    if (seconds <= 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4">
      {/* DJ Mode Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={toggleDjMode}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
              djMode
                ? 'bg-purple-600 text-white hover:bg-purple-700'
                : 'bg-zinc-800 text-gray-300 hover:bg-zinc-700'
            }`}
          >
            <MusicalNoteIcon className="h-5 w-5" />
            {djMode ? 'DJ Mode ON' : 'DJ Mode OFF'}
          </button>
          
          {djMode && (
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-gray-400 hover:text-white transition"
              title="DJ Settings"
            >
              <Cog6ToothIcon className="h-5 w-5" />
            </button>
          )}
        </div>

        {djMode && (
          <div className="flex items-center gap-2">
            <button
              onClick={toggleAutoTransition}
              className={`px-3 py-1 rounded text-sm font-medium transition ${
                autoTransition
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-zinc-700 text-gray-300 hover:bg-zinc-600'
              }`}
            >
              Auto: {autoTransition ? 'ON' : 'OFF'}
            </button>
            
            {nextTrack && !isTransitioning && (
              <button
                onClick={forceTransition}
                className="flex items-center gap-1 px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium transition"
                title="Force transition now"
              >
                <ForwardIcon className="h-4 w-4" />
                Mix Now
              </button>
            )}
          </div>
        )}
      </div>

      {/* DJ Settings Panel */}
      {djMode && showSettings && (
        <div className="bg-zinc-800/50 rounded-lg p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-300">DJ Settings</h3>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Transition Time */}
            <div>
              <label className="block text-xs text-gray-400 mb-2">
                Transition Time (seconds before end)
              </label>
              <input
                type="range"
                min="5"
                max="60"
                value={transitionTime}
                onChange={(e) => setTransitionTime(Number(e.target.value))}
                className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>5s</span>
                <span className="font-medium text-white">{transitionTime}s</span>
                <span>60s</span>
              </div>
            </div>

            {/* Crossfade Duration */}
            <div>
              <label className="block text-xs text-gray-400 mb-2">
                Crossfade Duration
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={crossfadeDuration}
                onChange={(e) => setCrossfadeDuration(Number(e.target.value))}
                className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1s</span>
                <span className="font-medium text-white">{crossfadeDuration}s</span>
                <span>10s</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DJ Status */}
      {djMode && (
        <div className="bg-zinc-900/50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">DJ Status</h3>
            {autoTransition && (
              <span className="text-xs px-2 py-1 bg-green-600 rounded text-white">
                AUTO-MIX
              </span>
            )}
          </div>

          {/* Transition Progress */}
          {isTransitioning && (
            <div className="mb-3">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                <span>Crossfading...</span>
                <span>{Math.round(transitionProgress * 100)}%</span>
              </div>
              <div className="w-full bg-zinc-800 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-100"
                  style={{ width: `${transitionProgress * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Next Track Info */}
          {nextTrack ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Next Track:</span>
                {autoTransition && timeUntilTransition > 0 && (
                  <span className="text-xs text-orange-400">
                    Transition in {formatTime(timeUntilTransition)}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-zinc-800 rounded flex items-center justify-center">
                  <MusicalNoteIcon className="w-5 h-5 text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {nextTrack.title || nextTrack.filename}
                  </p>
                  <p className="text-xs text-gray-400 truncate">
                    {nextTrack.artist || 'Unknown Artist'}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-sm text-gray-500">No next track in queue</p>
              <p className="text-xs text-gray-600">Add more tracks to enable auto-mix</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DjModeControls; 
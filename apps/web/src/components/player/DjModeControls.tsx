'use client';

import React, { useState, useEffect } from 'react';
import {
  MusicalNoteIcon,
  Cog6ToothIcon,
  ForwardIcon,
  ClockIcon,
  MusicalNoteIcon as TrackIcon,
} from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const DjModeControls: React.FC = () => {
  const {
    djMode,
    autoTransition,
    mixInterval,
    mixMode,
    transitionTime,
    crossfadeDuration,
    isTransitioning,
    transitionProgress,
    nextTrack,
    timeUntilTransition,
    currentTime,
    toggleDjMode,
    setAutoTransition,
    setMixInterval,
    setMixMode,
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

  // Preset intervals for quick selection
  const intervalPresets = [
    { label: '30s', value: 30 },
    { label: '45s', value: 45 },
    { label: '60s', value: 60 },
    { label: '90s', value: 90 },
  ];

  if (!djMode) {
    return null;
  }

  return (
    <div className="bg-zinc-900/50 rounded-xl p-6 border border-zinc-500/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">DJ Controls</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoTransition(!autoTransition)}
            className={`px-3 py-1 rounded text-sm font-medium transition ${
              autoTransition
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-zinc-700 text-gray-300 hover:bg-zinc-600'
            }`}
          >
            Auto-Mix: {autoTransition ? 'ON' : 'OFF'}
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
          
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-1 text-gray-400 hover:text-white transition"
            title="DJ Settings"
          >
            <Cog6ToothIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Mix Mode Toggle */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm text-gray-400">Mix Mode:</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setMixMode('interval')}
            className={`flex items-center gap-2 px-3 py-2 rounded text-sm font-medium transition ${
              mixMode === 'interval'
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-700 text-gray-300 hover:bg-zinc-600'
            }`}
          >
            <ClockIcon className="h-4 w-4" />
            Fixed Interval
          </button>
          <button
            onClick={() => setMixMode('track-end')}
            className={`flex items-center gap-2 px-3 py-2 rounded text-sm font-medium transition ${
              mixMode === 'track-end'
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-700 text-gray-300 hover:bg-zinc-600'
            }`}
          >
            <TrackIcon className="h-4 w-4" />
            Track End
          </button>
        </div>
      </div>

      {/* Interval Presets (for interval mode) */}
      {mixMode === 'interval' && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-gray-400">Mix Every:</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {intervalPresets.map((preset) => (
              <button
                key={preset.value}
                onClick={() => setMixInterval(preset.value)}
                className={`px-3 py-1 rounded text-sm font-medium transition ${
                  mixInterval === preset.value
                    ? 'bg-purple-600 text-white'
                    : 'bg-zinc-700 text-gray-300 hover:bg-zinc-600'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Next mix in: {formatTime(timeUntilTransition)}
          </div>
        </div>
      )}

      {/* DJ Settings Panel */}
      {showSettings && (
        <div className="bg-zinc-800/50 rounded-lg p-4 space-y-4 mb-4">
          <div className="grid grid-cols-1 gap-4">
            {/* Mix Interval Slider (for interval mode) */}
            {mixMode === 'interval' && (
              <div>
                <label className="block text-xs text-gray-400 mb-2">
                  Mix Interval (seconds)
                </label>
                <input
                  type="range"
                  min="15"
                  max="120"
                  value={mixInterval}
                  onChange={(e) => setMixInterval(Number(e.target.value))}
                  className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>15s</span>
                  <span className="font-medium text-white">{mixInterval}s</span>
                  <span>2min</span>
                </div>
              </div>
            )}

            {/* Transition Time Slider (for track-end mode) */}
            {mixMode === 'track-end' && (
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
            )}

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

      {/* Transition Progress */}
      {isTransitioning && (
        <div className="mb-4">
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
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Next Track</span>
            {autoTransition && timeUntilTransition > 0 && (
              <span className="text-sm text-orange-400">
                {mixMode === 'interval' ? 'Mix' : 'Transition'} in {formatTime(timeUntilTransition)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-zinc-800 rounded flex items-center justify-center">
              <MusicalNoteIcon className="w-6 h-6 text-gray-400" />
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
          <p className="text-xs text-gray-600 mt-1">Add more tracks to enable auto-mix</p>
        </div>
      )}
    </div>
  );
};

export default DjModeControls; 
'use client';

import React from 'react';
import { MusicalNoteIcon, ForwardIcon } from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import { musicService } from '@/services/musicService';

const DjModeControls: React.FC = () => {
  const {
    djMode,
    autoTransition,
    mixMode,
    isTransitioning,
    transitionProgress,
    nextTrack,
    timeUntilTransition,
    forceTransition,
    currentTrack,
    sourceBpm,
    targetBpm,
    bpmSyncEnabled,
  } = useAudioPlayer();

  const formatTime = (seconds: number): string => {
    if (seconds <= 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!djMode) {
    return null;
  }

  return (
    <div className="bg-zinc-900/50 rounded-xl p-6 border border-zinc-500/30">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Next Track</h3>
          {currentTrack && sourceBpm && (
            <p className="text-xs text-gray-400 mt-1">Current: {sourceBpm.toFixed(0)} BPM</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {bpmSyncEnabled && (
            <span className="text-xs text-blue-400 bg-blue-400/20 px-2 py-1 rounded">BPM Sync</span>
          )}
          {autoTransition && (
            <span className="text-xs text-green-400 bg-green-400/20 px-2 py-1 rounded">
              Auto-Mix ON
            </span>
          )}

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
      </div>

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
                {mixMode === 'interval' ? 'Mix' : mixMode === 'hot-cue' ? 'Hot Cue' : 'Transition'}{' '}
                in {formatTime(timeUntilTransition)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-zinc-800 rounded flex items-center justify-center overflow-hidden">
              {nextTrack.has_artwork ? (
                <img
                  src={musicService.getArtworkUrl(nextTrack.filepath)}
                  alt={`${nextTrack.title || nextTrack.filename} cover`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to icon if image fails to load
                    e.currentTarget.style.display = 'none';
                    e.currentTarget.nextElementSibling?.classList.remove('hidden');
                  }}
                />
              ) : null}
              <MusicalNoteIcon
                className={`w-6 h-6 text-gray-400 ${nextTrack.has_artwork ? 'hidden' : ''}`}
              />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {nextTrack.title || nextTrack.filename}
              </p>
              <p className="text-xs text-gray-400 truncate">
                {nextTrack.artist || 'Unknown Artist'}
              </p>
            </div>
            {/* BPM Display */}
            <div className="text-right">
              <div className="text-sm font-mono text-purple-400">
                {targetBpm
                  ? `${targetBpm.toFixed(0)} BPM`
                  : nextTrack.bpm
                    ? `${nextTrack.bpm.toFixed(0)} BPM`
                    : '--'}
              </div>
              {sourceBpm && targetBpm && (
                <div className="text-xs text-gray-500">
                  {Math.abs(sourceBpm - targetBpm) <= 5 ? (
                    <span className="text-green-400">✓ Match</span>
                  ) : Math.abs(sourceBpm - targetBpm) <= 15 ? (
                    <span className="text-yellow-400">~ Close</span>
                  ) : (
                    <span className="text-orange-400">⚡ Diff</span>
                  )}
                </div>
              )}
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

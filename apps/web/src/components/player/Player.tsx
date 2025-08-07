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
    isServerStreaming,
    playbackStatus,
    djSet,
    isReadyToPlay,
    wsConnected,
  } = useAudioPlayer();

  const formatTime = (seconds: number): string => {
    if (seconds <= 0) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`h-24 bg-zinc-900 border-t border-zinc-800 px-4 relative ${isReadyToPlay ? 'ring-2 ring-green-500 ring-opacity-50' : ''}`}>
      {/* Ready to Play Indicator */}
      {isReadyToPlay && !isServerStreaming && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-green-500 animate-pulse" />
      )}
      
      {/* Server Streaming Progress Indicator */}
      {isServerStreaming && playbackStatus && djSet && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-zinc-800">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-100"
            style={{ 
              width: `${(playbackStatus.elapsed_time || 0) / djSet.total_duration * 100}%` 
            }}
          />
        </div>
      )}

      <div className="max-w-screen-xl mx-auto h-full flex items-center justify-between gap-6">
        {/* Left Side - DJ Set Status */}
        <div className="flex-1 min-w-0 max-w-sm">
          {isReadyToPlay && !isServerStreaming && djSet && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-green-400">
                DJ Set Ready: {djSet.name || 'Custom Mix'}
              </div>
              <div className="text-xs text-gray-400">
                {djSet.track_count} tracks • {Math.round(djSet.total_duration / 60)} minutes
              </div>
            </div>
          )}
          {isServerStreaming && playbackStatus && djSet && (
            <div className="space-y-2">
              <div className="text-sm font-medium">
                {djSet.name || 'DJ Set'} - {djSet.vibe_description}
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span>
                  Track {(playbackStatus.current_track_order || 0) + 1} of {djSet.track_count}
                </span>
                {playbackStatus.in_transition && (
                  <span className="text-purple-400 animate-pulse">
                    Mixing... {Math.round((playbackStatus.transition_progress || 0) * 100)}%
                  </span>
                )}
                {playbackStatus.next_transition_in && playbackStatus.next_transition_in <= 60 && (
                  <span className="text-orange-400">
                    Next mix in {formatTime(playbackStatus.next_transition_in)}
                  </span>
                )}
              </div>
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
          {/* WebSocket Connection Status */}
          {isServerStreaming && (
            <div className="flex items-center gap-2 text-xs">
              <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'}`} />
              <span className="text-zinc-500 hidden lg:inline">
                {wsConnected ? 'Live' : 'Connecting'}
              </span>
            </div>
          )}
          <VolumeControl />
          <QueueManager />
          <KeyboardShortcutsHelp />
        </div>
      </div>
    </div>
  );
};

export default Player;

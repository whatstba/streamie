'use client';

import React, { useState } from 'react';
import { SparklesIcon } from '@heroicons/react/24/solid';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import AudioControls from './AudioControls';
import ProgressBar from './ProgressBar';
import VolumeControl from './VolumeControl';
import CurrentTrackInfo from './CurrentTrackInfo';
import KeyboardShortcutsHelp from './KeyboardShortcutsHelp';
import QueueManager from './QueueManager';

const Player = () => {
  const [aiPrompt, setAiPrompt] = useState('');
  const { 
    currentTrack, 
    djMode, 
    isTransitioning, 
    transitionProgress,
    timeUntilTransition 
  } = useAudioPlayer();

  const handleAiSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (aiPrompt.trim()) {
      // TODO: Implement AI DJ functionality
      console.log('AI Prompt:', aiPrompt);
      setAiPrompt('');
    }
  };

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
        {/* Currently Playing */}
        <div className="flex-1 min-w-0 max-w-sm">
          <CurrentTrackInfo />
          
          {/* DJ Mode Status */}
          {djMode && (
            <div className="mt-1 flex items-center gap-2 text-xs">
              <span className="px-2 py-0.5 bg-purple-600 rounded text-white font-medium">
                DJ MODE
              </span>
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
          
          <div className="relative">
            <form onSubmit={handleAiSubmit}>
              <input
                type="text"
                placeholder="Tell AI DJ to change the vibe..."
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                className="w-64 px-4 py-2 rounded-full bg-zinc-800 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 text-white placeholder-gray-400"
              />
              <button 
                type="submit"
                disabled={!aiPrompt.trim()}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-purple-500 hover:text-purple-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <SparklesIcon className="h-5 w-5" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Player; 
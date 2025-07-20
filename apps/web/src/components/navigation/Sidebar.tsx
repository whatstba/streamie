'use client';

import React from 'react';
import {
  MicrophoneIcon,
  SparklesIcon,
  PlayIcon,
  PauseIcon,
  ClockIcon,
  MusicalNoteIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import { musicService } from '@/services/musicService';
import Image from 'next/image';

const Sidebar = () => {
  const {
    currentTrack,
    isPlaying,
    djMode,
    toggleDjMode,
    nextTrack: upcomingTrack,
    isTransitioning,
    currentTime,
    duration,
    autoTransition,
    setAutoTransition,
    mixMode,
    setMixMode,
    mixInterval,
    setMixInterval,
  } = useAudioPlayer();

  const formatDuration = (duration: number): string => {
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatTime = (time: number): string => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-80 bg-zinc-900 p-6 flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <SparklesIcon className="h-8 w-8 text-purple-500" />
        <h1 className="text-xl font-bold">Jamz</h1>
      </div>

      {/* Persistent Auto Mix Button */}
      {/* <div className="bg-gradient-to-r from-purple-900/40 to-pink-900/40 rounded-xl p-4 border border-purple-500/30">
        <button
          onClick={toggleDjMode}
          className={`w-full px-4 py-3 rounded-lg font-medium transition flex items-center justify-center gap-2 ${
            djMode 
              ? 'bg-purple-600 hover:bg-purple-700 text-white' 
              : 'bg-gray-600 hover:bg-gray-700 text-white'
          }`}
        >
          <MicrophoneIcon className="h-5 w-5" />
          {djMode ? 'Auto Mix ON' : 'Enable Auto Mix'}
        </button>
        {djMode && (
          <div className="mt-2 text-center">
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-green-400">DJ Mode Active</span>
            </div>
            {isTransitioning && (
              <div className="text-xs text-orange-400 mt-1 animate-pulse">
                Mixing tracks...
              </div>
            )}
          </div>
        )}
      </div> */}


      {/* Now Playing Section */}
      {currentTrack && (
        <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">
            Now Playing
          </h2>

          <div className="flex gap-3 mb-3">
            {currentTrack.has_artwork ? (
              <div className="w-16 h-16 rounded-lg overflow-hidden bg-zinc-800 relative flex-shrink-0">
                <Image
                  src={musicService.getArtworkUrl(currentTrack.filepath)}
                  alt={currentTrack.album || 'Album artwork'}
                  fill
                  className="object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
              </div>
            ) : (
              <div className="w-16 h-16 rounded-lg bg-zinc-800 flex items-center justify-center text-2xl text-gray-600 flex-shrink-0">
                ♪
              </div>
            )}

            <div className="flex-1 min-w-0">
              <p
                className="font-medium text-white truncate"
                title={currentTrack.title || currentTrack.filename}
              >
                {currentTrack.title || currentTrack.filename}
              </p>
              <p
                className="text-sm text-gray-400 truncate"
                title={currentTrack.artist || 'Unknown Artist'}
              >
                {currentTrack.artist || 'Unknown Artist'}
              </p>
              <div className="flex items-center gap-2 mt-1">
                {isPlaying ? (
                  <PlayIcon className="h-3 w-3 text-green-400" />
                ) : (
                  <PauseIcon className="h-3 w-3 text-gray-400" />
                )}
                <span className="text-xs text-gray-500">
                  {formatTime(currentTime)} / {formatDuration(duration)}
                </span>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-700 rounded-full h-1 mb-3">
            <div
              className="bg-purple-500 h-1 rounded-full transition-all duration-300"
              style={{ width: duration > 0 ? `${(currentTime / duration) * 100}%` : '0%' }}
            ></div>
          </div>

          {/* Next Track in DJ Mode */}
          {djMode && upcomingTrack && (
            <div className="border-t border-zinc-700 pt-3">
              <p className="text-xs text-orange-400 font-medium mb-2 uppercase tracking-wide">
                Next Up
              </p>
              <div className="flex gap-2">
                {upcomingTrack.has_artwork ? (
                  <div className="w-8 h-8 rounded overflow-hidden bg-zinc-700 relative flex-shrink-0">
                    <Image
                      src={musicService.getArtworkUrl(upcomingTrack.filepath)}
                      alt={upcomingTrack.album || 'Album artwork'}
                      fill
                      className="object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded bg-zinc-700 flex items-center justify-center text-xs text-gray-400 flex-shrink-0">
                    ♪
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium text-white truncate"
                    title={upcomingTrack.title || upcomingTrack.filename}
                  >
                    {upcomingTrack.title || upcomingTrack.filename}
                  </p>
                  <p
                    className="text-xs text-gray-400 truncate"
                    title={upcomingTrack.artist || 'Unknown Artist'}
                  >
                    {upcomingTrack.artist || 'Unknown Artist'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mix Mode Settings */}
      {djMode && (
        <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700">
          <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">
            Mix Settings
          </h2>

          {/* Auto Transition Toggle */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-gray-300">Auto-Mix</span>
            <button
              onClick={() => setAutoTransition(!autoTransition)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                autoTransition ? 'bg-green-600 text-white' : 'bg-gray-600 text-gray-300'
              }`}
            >
              {autoTransition ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Mix Mode Selection */}
          <div className="space-y-2">
            <label className="text-xs text-gray-400 uppercase tracking-wide">Mix Mode</label>
            <div className="grid grid-cols-3 gap-1">
              <button
                onClick={() => setMixMode('track-end')}
                className={`px-2 py-2 rounded text-xs font-medium transition flex flex-col items-center gap-1 ${
                  mixMode === 'track-end'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                title="Auto-mix near end of track"
              >
                <Cog6ToothIcon className="h-4 w-4" />
                Track End
              </button>
              <button
                onClick={() => setMixMode('interval')}
                className={`px-2 py-2 rounded text-xs font-medium transition flex flex-col items-center gap-1 ${
                  mixMode === 'interval'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                title="Auto-mix at fixed intervals"
              >
                <ClockIcon className="h-4 w-4" />
                Interval
              </button>
              <button
                onClick={() => setMixMode('hot-cue')}
                className={`px-2 py-2 rounded text-xs font-medium transition flex flex-col items-center gap-1 ${
                  mixMode === 'hot-cue'
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                title="Auto-mix at hot cue points"
              >
                <MusicalNoteIcon className="h-4 w-4" />
                Hot Cue
              </button>
            </div>
          </div>

          {/* Interval Settings */}
          {mixMode === 'interval' && (
            <div className="mt-4 space-y-2">
              <label className="text-xs text-gray-400 uppercase tracking-wide">Mix Interval</label>
              <div className="grid grid-cols-3 gap-1">
                <button
                  onClick={() => setMixInterval(30)}
                  className={`px-2 py-2 rounded text-xs font-medium transition ${
                    mixInterval === 30
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  30s
                </button>
                <button
                  onClick={() => setMixInterval(60)}
                  className={`px-2 py-2 rounded text-xs font-medium transition ${
                    mixInterval === 60
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  60s
                </button>
                <button
                  onClick={() => setMixInterval(90)}
                  className={`px-2 py-2 rounded text-xs font-medium transition ${
                    mixInterval === 90
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  90s
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Commented out Saved Vibes Section */}
      {/*
      <div className="mt-8">
        <h2 className="text-gray-400 text-sm font-semibold mb-4">SAVED VIBES</h2>
        <div className="space-y-2">
          <button className="w-full text-left py-2 px-4 rounded-lg hover:bg-zinc-800 transition">
            Chill Evening
          </button>
          <button className="w-full text-left py-2 px-4 rounded-lg hover:bg-zinc-800 transition">
            Workout Energy
          </button>
          <button className="w-full text-left py-2 px-4 rounded-lg hover:bg-zinc-800 transition">
            Focus Mode
          </button>
        </div>
      </div>
      */}
    </div>
  );
};

export default Sidebar;

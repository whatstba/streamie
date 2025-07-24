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
    isServerStreaming,
    djSet,
    playbackStatus,
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
                {isServerStreaming && playbackStatus && (
                  <span className="text-xs text-gray-500">
                    Track {(playbackStatus.current_track_order || 0) + 1} of {playbackStatus.total_tracks || 0}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {isServerStreaming && playbackStatus && djSet && (
            <div className="w-full bg-gray-700 rounded-full h-1 mb-3">
              <div
                className="bg-purple-500 h-1 rounded-full transition-all duration-300"
                style={{ width: `${(playbackStatus.elapsed_time || 0) / djSet.total_duration * 100}%` }}
              ></div>
            </div>
          )}

          {/* Next Track in DJ Mode */}
          {isServerStreaming && playbackStatus && djSet && 
           playbackStatus.current_track_order !== undefined && 
           playbackStatus.current_track_order < djSet.tracks.length - 1 && (
            <div className="border-t border-zinc-700 pt-3">
              <p className="text-xs text-orange-400 font-medium mb-2 uppercase tracking-wide">
                Next Up
              </p>
              <div className="flex gap-2">
                <div className="w-8 h-8 rounded bg-zinc-700 flex items-center justify-center text-xs text-gray-400 flex-shrink-0">
                  ♪
                </div>
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium text-white truncate"
                    title={djSet.tracks[playbackStatus.current_track_order + 1].title}
                  >
                    {djSet.tracks[playbackStatus.current_track_order + 1].title}
                  </p>
                  <p
                    className="text-xs text-gray-400 truncate"
                    title={djSet.tracks[playbackStatus.current_track_order + 1].artist}
                  >
                    {djSet.tracks[playbackStatus.current_track_order + 1].artist}
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

          {/* DJ Set Info */}
          {isServerStreaming && djSet && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">DJ Set</span>
                <span className="text-xs text-purple-400 font-medium">STREAMING</span>
              </div>
              <div className="text-xs text-gray-400 space-y-1">
                <p>Vibe: {djSet.vibe_description}</p>
                <p>Duration: {formatDuration(djSet.total_duration)}</p>
                <p>Energy: {djSet.energy_pattern}</p>
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

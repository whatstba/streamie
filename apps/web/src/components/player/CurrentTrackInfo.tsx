'use client';

import React from 'react';
import Image from 'next/image';
import { MusicalNoteIcon } from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import { musicService } from '@/services/musicService';

const CurrentTrackInfo: React.FC = () => {
  const { currentTrack } = useAudioPlayer();

  if (!currentTrack) {
    return (
      <div className="flex items-center gap-4 min-w-0">
        <div className="w-14 h-14 bg-zinc-800 rounded-md flex items-center justify-center">
          <MusicalNoteIcon className="w-6 h-6 text-gray-400" />
        </div>
        <div className="min-w-0">
          <h3 className="font-medium text-gray-400">No track selected</h3>
          <p className="text-sm text-gray-500">Choose a track to play</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 min-w-0">
      {/* Album Artwork */}
      <div className="w-14 h-14 rounded-md overflow-hidden bg-zinc-800 flex-shrink-0 relative">
        {currentTrack.has_artwork ? (
          <Image
            src={musicService.getArtworkUrl(currentTrack.filepath)}
            alt={currentTrack.album || 'Album artwork'}
            fill
            sizes="56px"
            className="object-cover"
            onError={(e) => {
              // Show music note icon on error
              const target = e.target as HTMLImageElement;
              const parent = target.parentElement;
              if (parent) {
                parent.innerHTML = '<div class="w-full h-full flex items-center justify-center text-gray-400"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path></svg></div>';
              }
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <MusicalNoteIcon className="w-6 h-6" />
          </div>
        )}
      </div>

      {/* Track Info */}
      <div className="min-w-0 flex-1">
        <h3 className="font-medium text-white truncate">
          {currentTrack.title || currentTrack.filename}
        </h3>
        <p className="text-sm text-gray-400 truncate">
          {currentTrack.artist || 'Unknown Artist'}
          {currentTrack.album && ` • ${currentTrack.album}`}
        </p>
        {currentTrack.year && (
          <p className="text-xs text-gray-500 truncate">
            {currentTrack.year}
            {currentTrack.genre && ` • ${currentTrack.genre}`}
          </p>
        )}
      </div>
    </div>
  );
};

export default CurrentTrackInfo; 
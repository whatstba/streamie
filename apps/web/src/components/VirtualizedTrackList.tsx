'use client';

import React, { useMemo, useState } from 'react';
import { List, AutoSizer, ListRowProps } from 'react-virtualized';
import Image from 'next/image';
import { musicService } from '@/services/musicService';
import { MagnifyingGlassIcon, MusicalNoteIcon, PlayIcon, PlusIcon } from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

interface Track {
  filename: string;
  filepath: string;
  duration: number;
  title: string | null;
  artist: string | null;
  album: string | null;
  genre: string | null;
  year: string | null;
  has_artwork: boolean;
}

interface VirtualizedTrackListProps {
  tracks: Track[];
  selectedTrackPath?: string;
  onTrackSelect: (track: Track) => void;
  onTrackAnalyze: (track: Track) => void;
  onAddToQueue?: (track: Track) => void;
  isAnalyzing?: boolean;
}

const VirtualizedTrackList: React.FC<VirtualizedTrackListProps> = ({
  tracks,
  selectedTrackPath,
  onTrackSelect,
  onTrackAnalyze,
  onAddToQueue,
  isAnalyzing = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const { playTrack, currentTrack, isPlaying, queue, djMode } = useAudioPlayer();

  // Filter tracks based on search term
  const filteredTracks = useMemo(() => {
    if (!searchTerm.trim()) return tracks;
    
    const lowerSearchTerm = searchTerm.toLowerCase();
    return tracks.filter(track => 
      (track.title || track.filename).toLowerCase().includes(lowerSearchTerm) ||
      (track.artist || '').toLowerCase().includes(lowerSearchTerm) ||
      (track.album || '').toLowerCase().includes(lowerSearchTerm) ||
      (track.genre || '').toLowerCase().includes(lowerSearchTerm)
    );
  }, [tracks, searchTerm]);

  const formatDuration = (duration: number): string => {
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const isTrackInQueue = (track: Track): boolean => {
    return queue.some(qTrack => qTrack.filepath === track.filepath);
  };

  const rowRenderer = ({ index, key, style }: ListRowProps) => {
    const track = filteredTracks[index];
    const isSelected = selectedTrackPath === track.filepath;
    const isCurrentTrack = currentTrack?.filepath === track.filepath;
    const inQueue = isTrackInQueue(track);

    const handleTrackClick = () => {
      onTrackSelect(track);
      // Auto-analyze when track is clicked
      onTrackAnalyze(track);
      // Start playback with the filtered list as queue
      playTrack(track, filteredTracks);
    };

    const handleAddToQueue = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (onAddToQueue && !inQueue) {
        onAddToQueue(track);
      }
    };

    return (
      <div key={key} style={style}>
        <div
          className={`flex items-center justify-between p-3 mx-2 hover:bg-zinc-800/50 rounded-lg transition-all duration-200 cursor-pointer border border-transparent group ${
            isCurrentTrack
              ? 'bg-purple-900/30 border-purple-500/30 shadow-lg shadow-purple-500/10' 
              : isSelected 
                ? 'bg-zinc-800/30 border-zinc-600/30'
                : inQueue
                ? 'bg-blue-900/20 border-blue-500/20'
                : 'hover:border-zinc-700/50'
          } ${isAnalyzing && isSelected ? 'opacity-75' : ''}`}
          onClick={handleTrackClick}
        >
          <div className="flex items-center gap-4 flex-1 min-w-0">
            <div className="relative">
              {track.has_artwork ? (
                <div className="w-12 h-12 rounded bg-zinc-800 overflow-hidden relative flex-shrink-0">
                  <Image
                    src={musicService.getArtworkUrl(track.filepath)}
                    alt={track.album || 'Album artwork'}
                    fill
                    sizes="48px"
                    className="object-cover"
                    onError={(e) => {
                      // Hide image on error and show music note
                      const target = e.target as HTMLImageElement;
                      const parent = target.parentElement;
                      if (parent) {
                        parent.innerHTML = '<div class="w-full h-full flex items-center justify-center text-gray-400"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg></div>';
                      }
                    }}
                  />
                </div>
              ) : (
                <div className="w-12 h-12 bg-zinc-800 rounded flex items-center justify-center text-gray-400 flex-shrink-0">
                  <MusicalNoteIcon className="w-6 h-6" />
                </div>
              )}
              
              {/* Play overlay on hover */}
              <div className="absolute inset-0 bg-black/50 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <PlayIcon className="w-5 h-5 text-white" />
              </div>
              
              {/* Now playing indicator */}
              {isCurrentTrack && isPlaying && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-purple-500 rounded-full animate-pulse" />
              )}

              {/* Queue indicator */}
              {inQueue && !isCurrentTrack && (
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full" />
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <h3 className={`font-medium truncate ${
                isCurrentTrack ? 'text-purple-300' : inQueue ? 'text-blue-300' : 'text-white'
              }`}>
                {track.title || track.filename}
              </h3>
              <p className="text-sm text-gray-400 truncate">
                {track.artist || 'Unknown Artist'}
                {track.album && ` • ${track.album}`}
              </p>
              {track.genre && (
                <p className="text-xs text-gray-500 truncate">{track.genre}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            {isAnalyzing && isSelected && (
              <div className="text-xs text-purple-400 animate-pulse font-medium">Analyzing...</div>
            )}
            
            {/* Queue Status */}
            {isCurrentTrack && (
              <div className="text-xs text-purple-400 font-medium">
                {isPlaying ? 'Playing' : 'Paused'}
              </div>
            )}
            {inQueue && !isCurrentTrack && (
              <div className="text-xs text-blue-400 font-medium">In Queue</div>
            )}

            {/* Add to Queue Button */}
            {onAddToQueue && !inQueue && !isCurrentTrack && (
              <button
                onClick={handleAddToQueue}
                className="p-1 text-gray-500 hover:text-blue-400 transition opacity-0 group-hover:opacity-100"
                title="Add to Queue"
              >
                <PlusIcon className="h-4 w-4" />
              </button>
            )}

            <span className="text-gray-400 text-sm tabular-nums">{formatDuration(track.duration)}</span>
          </div>
        </div>
      </div>
    );
  };

  // Calculate estimated row height
  const ROW_HEIGHT = 80;

  if (tracks.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <MusicalNoteIcon className="w-16 h-16 mx-auto mb-4 text-gray-600" />
        <p className="text-lg">No music files found</p>
        <p className="text-sm">Add some MP3, M4A, WAV, FLAC, or OGG files to ~/Downloads</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search tracks, artists, albums..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder-gray-400"
        />
        {searchTerm && (
          <button
            onClick={() => setSearchTerm('')}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
          >
            ✕
          </button>
        )}
      </div>

      {/* Results Count */}
      <div className="flex justify-between items-center text-sm text-gray-400">
        <span>
          {searchTerm 
            ? `${filteredTracks.length} of ${tracks.length} tracks` 
            : `${tracks.length} tracks`
          }
          {djMode && queue.length > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-blue-600 rounded text-xs text-white">
              {queue.length} in queue
            </span>
          )}
        </span>
        {searchTerm && filteredTracks.length === 0 && (
          <span className="text-orange-400">No tracks match your search</span>
        )}
      </div>

      {/* Virtualized List */}
      <div className="h-96 w-full border border-zinc-700/50 rounded-lg overflow-hidden">
        <AutoSizer>
          {({ height, width }) => (
            <List
              height={height}
              rowCount={filteredTracks.length}
              rowHeight={ROW_HEIGHT}
              rowRenderer={rowRenderer}
              width={width}
              overscanRowCount={10}
              style={{ backgroundColor: 'transparent' }}
            />
          )}
        </AutoSizer>
      </div>
    </div>
  );
};

export default VirtualizedTrackList; 
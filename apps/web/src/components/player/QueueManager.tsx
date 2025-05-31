'use client';

import React, { useState } from 'react';
import {
  QueueListIcon,
  XMarkIcon,
  Bars3Icon,
  PlayIcon,
  ChevronUpIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { MusicalNoteIcon } from '@heroicons/react/24/solid';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import { musicService } from '@/services/musicService';
import Image from 'next/image';

const QueueManager: React.FC = () => {
  const {
    queue,
    currentIndex,
    currentTrack,
    isPlaying,
    djMode,
    nextTrack: upcomingTrack,
    playTrack,
    removeFromQueue,
    clearQueue,
    moveTrackInQueue,
  } = useAudioPlayer();

  const [isOpen, setIsOpen] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);

  const formatDuration = (duration: number): string => {
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== dropIndex) {
      moveTrackInQueue(draggedIndex, dropIndex);
    }
    setDraggedIndex(null);
  };

  const handleTrackPlay = (track: any, index: number) => {
    playTrack(track, queue);
  };

  const handleMoveUp = (index: number) => {
    if (index > 0) {
      moveTrackInQueue(index, index - 1);
    }
  };

  const handleMoveDown = (index: number) => {
    if (index < queue.length - 1) {
      moveTrackInQueue(index, index + 1);
    }
  };

  const getTrackStatus = (index: number) => {
    if (index === currentIndex) return 'current';
    if (djMode && upcomingTrack && queue[index]?.filepath === upcomingTrack.filepath) return 'next';
    return 'queued';
  };

  if (queue.length === 0) {
    return null;
  }

  return (
    <>
      {/* Queue Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="relative text-gray-400 hover:text-white transition"
        title="View Queue"
      >
        <QueueListIcon className="h-5 w-5" />
        {queue.length > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-purple-500 rounded-full text-xs text-white flex items-center justify-center">
            {queue.length > 99 ? '99+' : queue.length}
          </span>
        )}
      </button>

      {/* Queue Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg w-full max-w-2xl max-h-[80vh] mx-4 border border-zinc-700">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-zinc-700">
              <div className="flex items-center gap-3">
                <QueueListIcon className="h-6 w-6 text-purple-400" />
                <h2 className="text-lg font-semibold">Queue ({queue.length} tracks)</h2>
                {djMode && (
                  <span className="px-2 py-1 bg-purple-600 rounded text-xs text-white">
                    DJ MODE
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={clearQueue}
                  disabled={queue.length === 0}
                  className="px-3 py-1 text-sm text-red-400 hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Clear All
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-white transition"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
            </div>

            {/* Queue List */}
            <div className="overflow-y-auto max-h-[60vh]">
              {queue.map((track, index) => {
                const status = getTrackStatus(index);
                const isDragging = draggedIndex === index;
                
                return (
                  <div
                    key={`${track.filepath}-${index}`}
                    draggable
                    onDragStart={(e) => handleDragStart(e, index)}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDrop(e, index)}
                    className={`flex items-center gap-4 p-4 border-b border-zinc-800 hover:bg-zinc-800/50 transition-all ${
                      isDragging ? 'opacity-50' : ''
                    } ${
                      status === 'current'
                        ? 'bg-purple-900/30 border-purple-500/30'
                        : status === 'next'
                        ? 'bg-orange-900/30 border-orange-500/30'
                        : ''
                    }`}
                  >
                    {/* Drag Handle */}
                    <div className="cursor-move text-gray-500 hover:text-gray-300">
                      <Bars3Icon className="h-4 w-4" />
                    </div>

                    {/* Track Number/Status */}
                    <div className="w-8 flex justify-center">
                      {status === 'current' && isPlaying ? (
                        <div className="w-3 h-3 bg-purple-500 rounded-full animate-pulse" />
                      ) : status === 'next' ? (
                        <span className="text-xs text-orange-400 font-bold">NEXT</span>
                      ) : (
                        <span className="text-xs text-gray-500">{index + 1}</span>
                      )}
                    </div>

                    {/* Album Artwork */}
                    <div className="w-12 h-12 rounded bg-zinc-800 overflow-hidden relative flex-shrink-0">
                      {track.has_artwork ? (
                        <Image
                          src={musicService.getArtworkUrl(track.filepath)}
                          alt={track.album || 'Album artwork'}
                          fill
                          sizes="48px"
                          className="object-cover"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            const parent = target.parentElement;
                            if (parent) {
                              parent.innerHTML = '<div class="w-full h-full flex items-center justify-center text-gray-400"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg></div>';
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
                    <div className="flex-1 min-w-0">
                      <h3 className={`font-medium truncate ${
                        status === 'current' ? 'text-purple-300' : 'text-white'
                      }`}>
                        {track.title || track.filename}
                      </h3>
                      <p className="text-sm text-gray-400 truncate">
                        {track.artist || 'Unknown Artist'}
                        {track.album && ` • ${track.album}`}
                      </p>
                    </div>

                    {/* Duration */}
                    <span className="text-sm text-gray-400 tabular-nums">
                      {formatDuration(track.duration)}
                    </span>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      {/* Move Up/Down */}
                      <button
                        onClick={() => handleMoveUp(index)}
                        disabled={index === 0}
                        className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Move Up"
                      >
                        <ChevronUpIcon className="h-4 w-4" />
                      </button>
                      
                      <button
                        onClick={() => handleMoveDown(index)}
                        disabled={index === queue.length - 1}
                        className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Move Down"
                      >
                        <ChevronDownIcon className="h-4 w-4" />
                      </button>

                      {/* Play Button */}
                      <button
                        onClick={() => handleTrackPlay(track, index)}
                        className="p-1 text-gray-500 hover:text-white transition"
                        title="Play Track"
                      >
                        <PlayIcon className="h-4 w-4" />
                      </button>

                      {/* Remove Button */}
                      <button
                        onClick={() => removeFromQueue(index)}
                        disabled={status === 'current'}
                        className="p-1 text-gray-500 hover:text-red-400 disabled:opacity-30 disabled:cursor-not-allowed transition"
                        title="Remove from Queue"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-zinc-700">
              <div className="flex items-center justify-between text-sm text-gray-400">
                <span>Drag tracks to reorder • Click play button to jump to track</span>
                <span>Total: {formatDuration(queue.reduce((sum, track) => sum + track.duration, 0))}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default QueueManager; 
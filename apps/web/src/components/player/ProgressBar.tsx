'use client';

import React from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const ProgressBar: React.FC = () => {
  const { isServerStreaming, playbackStatus, djSet, audioRef } = useAudioPlayer();

  const formatTime = (time: number): string => {
    if (!time || isNaN(time)) return '0:00';

    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getProgress = (): number => {
    if (!isServerStreaming || !playbackStatus || !djSet) return 0;
    return ((playbackStatus.elapsed_time || 0) / djSet.total_duration) * 100;
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isServerStreaming || !djSet || !audioRef.current) return;
    
    const progressBar = e.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const clickPercent = x / rect.width;
    const seekTime = clickPercent * djSet.total_duration;
    
    // Seek to the clicked position
    audioRef.current.currentTime = seekTime;
    console.log(`Seeking to ${seekTime}s (${(clickPercent * 100).toFixed(1)}%)`);
  };

  if (!isServerStreaming || !playbackStatus || !djSet) {
    return (
      <div className="flex items-center gap-2 w-full max-w-md">
        <span className="text-xs text-gray-400 w-10 text-right">0:00</span>
        <div className="flex-1 h-1 bg-zinc-700 rounded-full" />
        <span className="text-xs text-gray-400 w-10">0:00</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 w-full max-w-md">
      <span className="text-xs text-gray-400 w-10 text-right">
        {formatTime(playbackStatus.elapsed_time || 0)}
      </span>
      <div 
        className="flex-1 h-1 bg-zinc-700 rounded-full relative cursor-pointer hover:h-2 transition-all"
        onClick={handleProgressClick}
      >
        <div
          className="absolute top-0 left-0 h-full bg-white rounded-full transition-all duration-300 pointer-events-none"
          style={{ width: `${getProgress()}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-10">
        {formatTime(djSet.total_duration)}
      </span>
    </div>
  );
};

export default ProgressBar;
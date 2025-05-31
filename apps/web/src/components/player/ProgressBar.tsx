'use client';

import React, { useState, useRef } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const ProgressBar: React.FC = () => {
  const { currentTime, duration, seekTo } = useAudioPlayer();
  const [isDragging, setIsDragging] = useState(false);
  const [dragTime, setDragTime] = useState(0);
  const progressRef = useRef<HTMLDivElement>(null);

  const formatTime = (time: number): string => {
    if (!time || isNaN(time)) return '0:00';
    
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getProgress = (): number => {
    if (!duration) return 0;
    const time = isDragging ? dragTime : currentTime;
    return (time / duration) * 100;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!progressRef.current || !duration) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const time = percent * duration;
    
    setIsDragging(true);
    setDragTime(time);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !progressRef.current || !duration) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const time = percent * duration;
    
    setDragTime(time);
  };

  const handleMouseUp = () => {
    if (isDragging) {
      seekTo(dragTime);
      setIsDragging(false);
    }
  };

  // Handle mouse events on document when dragging
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragTime, duration]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!duration) return;
    
    const currentDisplayTime = isDragging ? dragTime : currentTime;
    
    switch (e.key) {
      case 'ArrowLeft':
        e.preventDefault();
        seekTo(Math.max(0, currentDisplayTime - 5));
        break;
      case 'ArrowRight':
        e.preventDefault();
        seekTo(Math.min(duration, currentDisplayTime + 5));
        break;
      case 'Home':
        e.preventDefault();
        seekTo(0);
        break;
      case 'End':
        e.preventDefault();
        seekTo(duration);
        break;
    }
  };

  return (
    <div className="w-full max-w-md space-y-1">
      {/* Progress Bar */}
      <div
        ref={progressRef}
        className="relative h-2 bg-zinc-800 rounded-full cursor-pointer group"
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="slider"
        aria-valuemin={0}
        aria-valuemax={duration || 0}
        aria-valuenow={isDragging ? dragTime : currentTime}
        aria-label="Track progress"
        title="Click to seek, use arrow keys to navigate"
      >
        {/* Progress Fill */}
        <div
          className="absolute top-0 left-0 h-full bg-white rounded-full transition-all duration-100"
          style={{ width: `${getProgress()}%` }}
        />
        
        {/* Hover Effect */}
        <div className="absolute inset-0 bg-white/20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
        
        {/* Dragging Thumb */}
        {isDragging && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg"
            style={{ left: `${getProgress()}%`, transform: 'translate(-50%, -50%)' }}
          />
        )}
        
        {/* Hover Thumb */}
        <div 
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ left: `${getProgress()}%`, transform: 'translate(-50%, -50%)' }}
        />
      </div>
      
      {/* Time Display */}
      <div className="flex justify-between text-xs text-gray-400 px-1">
        <span className="tabular-nums">
          {formatTime(isDragging ? dragTime : currentTime)}
        </span>
        <span className="tabular-nums">
          {formatTime(duration)}
        </span>
      </div>
    </div>
  );
};

export default ProgressBar; 
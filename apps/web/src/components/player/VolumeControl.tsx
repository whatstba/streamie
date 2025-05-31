'use client';

import React, { useState, useRef } from 'react';
import {
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
} from '@heroicons/react/24/outline';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const VolumeControl: React.FC = () => {
  const { volume, isMuted, setVolume, toggleMute } = useAudioPlayer();
  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const sliderRef = useRef<HTMLDivElement>(null);

  const displayVolume = isMuted ? 0 : volume;

  const handleVolumeChange = (newVolume: number) => {
    const clampedVolume = Math.max(0, Math.min(1, newVolume));
    setVolume(clampedVolume);
    
    // Auto-unmute when volume is changed
    if (isMuted && clampedVolume > 0) {
      toggleMute();
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!sliderRef.current) return;
    
    const rect = sliderRef.current.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    
    setIsDragging(true);
    handleVolumeChange(percent);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !sliderRef.current) return;
    
    const rect = sliderRef.current.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    
    handleVolumeChange(percent);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
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
  }, [isDragging]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowLeft':
      case 'ArrowDown':
        e.preventDefault();
        handleVolumeChange(volume - 0.1);
        break;
      case 'ArrowRight':
      case 'ArrowUp':
        e.preventDefault();
        handleVolumeChange(volume + 0.1);
        break;
      case 'Home':
        e.preventDefault();
        handleVolumeChange(0);
        break;
      case 'End':
        e.preventDefault();
        handleVolumeChange(1);
        break;
      case ' ':
      case 'Enter':
        e.preventDefault();
        toggleMute();
        break;
    }
  };

  const getVolumeIcon = () => {
    if (isMuted || volume === 0) {
      return <SpeakerXMarkIcon className="h-5 w-5" />;
    }
    return <SpeakerWaveIcon className="h-5 w-5" />;
  };

  return (
    <div 
      className="flex items-center gap-2 group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Mute Button */}
      <button
        onClick={toggleMute}
        className="text-gray-400 hover:text-white transition"
        title={isMuted ? 'Unmute' : 'Mute'}
        aria-label={isMuted ? 'Unmute' : 'Mute'}
      >
        {getVolumeIcon()}
      </button>

      {/* Volume Slider - Shows on hover or when dragging */}
      <div
        className={`overflow-hidden transition-all duration-200 ${
          isHovered || isDragging ? 'w-20 opacity-100' : 'w-0 opacity-0'
        }`}
      >
        <div
          ref={sliderRef}
          className="relative h-1 bg-zinc-800 rounded-full cursor-pointer w-20"
          onMouseDown={handleMouseDown}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="slider"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(displayVolume * 100)}
          aria-label="Volume control"
          title="Volume control"
        >
          {/* Volume Fill */}
          <div
            className="absolute top-0 left-0 h-full bg-white rounded-full transition-all duration-100"
            style={{ width: `${displayVolume * 100}%` }}
          />
          
          {/* Hover Effect */}
          <div className="absolute inset-0 bg-white/20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          
          {/* Volume Thumb */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ left: `${displayVolume * 100}%`, transform: 'translate(-50%, -50%)' }}
          />
        </div>
      </div>

      {/* Volume Percentage (Only show when interacting) */}
      {(isHovered || isDragging) && (
        <span className="text-xs text-gray-400 tabular-nums min-w-[2rem]">
          {Math.round(displayVolume * 100)}%
        </span>
      )}
    </div>
  );
};

export default VolumeControl; 
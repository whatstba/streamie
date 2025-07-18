'use client';

import { useEffect } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

export const useKeyboardShortcuts = () => {
  const {
    isPlaying,
    currentTrack,
    pause,
    play,
    skipToNext,
    skipToPrevious,
    setVolume,
    volume,
    toggleMute,
  } = useAudioPlayer();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target as HTMLElement)?.contentEditable === 'true'
      ) {
        return;
      }

      switch (e.code) {
        case 'Space':
          e.preventDefault();
          if (currentTrack) {
            if (isPlaying) {
              pause();
            } else {
              play();
            }
          }
          break;

        case 'ArrowRight':
          if (e.shiftKey) {
            e.preventDefault();
            skipToNext();
          }
          break;

        case 'ArrowLeft':
          if (e.shiftKey) {
            e.preventDefault();
            skipToPrevious();
          }
          break;

        case 'ArrowUp':
          if (e.shiftKey) {
            e.preventDefault();
            setVolume(Math.min(1, volume + 0.1));
          }
          break;

        case 'ArrowDown':
          if (e.shiftKey) {
            e.preventDefault();
            setVolume(Math.max(0, volume - 0.1));
          }
          break;

        case 'KeyM':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            toggleMute();
          }
          break;

        default:
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    isPlaying,
    currentTrack,
    pause,
    play,
    skipToNext,
    skipToPrevious,
    setVolume,
    volume,
    toggleMute,
  ]);
}; 
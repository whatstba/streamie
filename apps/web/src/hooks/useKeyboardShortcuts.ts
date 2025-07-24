'use client';

import { useEffect } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

export const useKeyboardShortcuts = () => {
  const {
    isPlaying,
    currentTrack,
    isServerStreaming,
    pauseDJSet,
    resumeDJSet,
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
          if (isServerStreaming) {
            if (isPlaying) {
              pauseDJSet();
            } else {
              resumeDJSet();
            }
          }
          break;

        case 'ArrowRight':
          if (e.shiftKey) {
            e.preventDefault();
            // Skip not supported in server streaming
          }
          break;

        case 'ArrowLeft':
          if (e.shiftKey) {
            e.preventDefault();
            // Skip not supported in server streaming
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
    isServerStreaming,
    pauseDJSet,
    resumeDJSet,
    setVolume,
    volume,
    toggleMute,
  ]);
};

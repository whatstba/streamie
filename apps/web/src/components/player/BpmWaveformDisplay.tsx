'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

const BpmWaveformDisplay: React.FC = () => {
  const {
    currentTrack,
    currentTime,
    duration,
    seek,
    hotCues,
    addHotCue,
    djMode,
    sourceBpm,
    isPlaying
  } = useAudioPlayer();

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [canvasWidth, setCanvasWidth] = useState(800);
  const [canvasHeight] = useState(100);
  const [isDragging, setIsDragging] = useState(false);

  // Canvas resize handler
  useEffect(() => {
    const handleResize = () => {
      if (canvasRef.current) {
        const container = canvasRef.current.parentElement;
        if (container) {
          setCanvasWidth(container.clientWidth);
        }
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Draw simplified waveform visualization (no API calls)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !duration) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    // Clear canvas
    ctx.fillStyle = '#0f0f0f';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Draw simplified progress bar background
    ctx.fillStyle = '#374151';
    ctx.fillRect(0, canvasHeight * 0.4, canvasWidth, canvasHeight * 0.2);

    // Draw progress indicator
    const progressX = (currentTime / duration) * canvasWidth;
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(0, canvasHeight * 0.4, progressX, canvasHeight * 0.2);

    // Draw playhead
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(progressX, 0);
    ctx.lineTo(progressX, canvasHeight);
    ctx.stroke();

    // Draw BPM grid if available
    if (sourceBpm && sourceBpm > 0) {
      const beatDuration = 60 / sourceBpm; // seconds per beat
      const beatsToShow = Math.ceil(duration / beatDuration);
      
      ctx.strokeStyle = '#fbbf24';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 4]);
      
      for (let beat = 0; beat < beatsToShow; beat++) {
        const beatTime = beat * beatDuration;
        const beatX = (beatTime / duration) * canvasWidth;
        
        if (beat % 4 === 0) {
          // Stronger line for downbeats
          ctx.lineWidth = 2;
          ctx.strokeStyle = '#f59e0b';
        } else {
          ctx.lineWidth = 1;
          ctx.strokeStyle = '#fbbf24';
        }
        
        ctx.beginPath();
        ctx.moveTo(beatX, 0);
        ctx.lineTo(beatX, canvasHeight);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }

    // Draw hot cues
    if (currentTrack) {
      const trackCues = hotCues[currentTrack.filepath] || [];
      trackCues.forEach((cue) => {
        const cueX = (cue.time / duration) * canvasWidth;
        
        // Draw cue marker
        ctx.fillStyle = cue.color;
        ctx.fillRect(cueX - 2, 0, 4, canvasHeight);
        
        // Draw cue label
        ctx.fillStyle = '#ffffff';
        ctx.font = '10px monospace';
        ctx.fillText(cue.name, cueX + 5, 15);
      });
    }

    // Draw time markers
    ctx.fillStyle = '#6b7280';
    ctx.font = '10px monospace';
    const timeMarkers = [0, duration * 0.25, duration * 0.5, duration * 0.75, duration];
    timeMarkers.forEach((time) => {
      const x = (time / duration) * canvasWidth;
      const minutes = Math.floor(time / 60);
      const seconds = Math.floor(time % 60);
      const timeText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      ctx.fillText(timeText, x - 15, canvasHeight - 5);
    });

  }, [currentTime, duration, canvasWidth, sourceBpm, hotCues, currentTrack]);

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!duration || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const clickTime = (x / canvasWidth) * duration;

    if (event.shiftKey && currentTrack) {
      // Shift+click to add hot cue
      const cueName = prompt('Enter hot cue name:');
      if (cueName) {
        addHotCue(currentTrack.filepath, cueName, clickTime);
      }
    } else {
      // Regular click to seek
      seek(clickTime);
    }
  };

  const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging || !duration || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const seekTime = Math.max(0, Math.min(duration, (x / canvasWidth) * duration));
    
    seek(seekTime);
  };

  if (!djMode || !currentTrack) {
    return null;
  }

  return (
    <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-500/30">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-white">Beat Grid</h3>
        <div className="flex items-center gap-4 text-sm">
          {sourceBpm && (
            <div className="text-blue-400 font-mono">
              {sourceBpm.toFixed(1)} BPM
            </div>
          )}
          <div className="text-gray-500 text-xs">
            Shift+Click for cue
          </div>
        </div>
      </div>

      <div className="relative">
        <canvas
          ref={canvasRef}
          width={canvasWidth}
          height={canvasHeight}
          className="w-full h-auto border border-zinc-700 rounded-lg cursor-pointer"
          onClick={handleCanvasClick}
          onMouseMove={handleMouseMove}
          onMouseDown={() => setIsDragging(true)}
          onMouseUp={() => setIsDragging(false)}
          onMouseLeave={() => setIsDragging(false)}
        />
      </div>

      {/* Compact BPM Info - only show when BPM is available */}
      {sourceBpm && (
        <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
          <div>
            <span className="text-gray-500">Beat Length:</span>{' '}
            <span className="text-white font-mono">{(60 / sourceBpm).toFixed(2)}s</span>
          </div>
          <div>
            <span className="text-gray-500">Total Beats:</span>{' '}
            <span className="text-white font-mono">{Math.floor(duration * sourceBpm / 60)}</span>
          </div>
          <div>
            <span className="text-gray-500">Hot Cues:</span>{' '}
            <span className="text-white font-mono">
              {currentTrack ? (hotCues[currentTrack.filepath] || []).length : 0}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default BpmWaveformDisplay; 
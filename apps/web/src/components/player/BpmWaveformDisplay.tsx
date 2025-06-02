'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import { musicService } from '@/services/musicService';

interface WaveformData {
  waveform: number[];
  sample_rate: number;
  hop_length: number;
}

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
  const [waveformData, setWaveformData] = useState<WaveformData | null>(null);
  const [canvasWidth, setCanvasWidth] = useState(800);
  const [canvasHeight] = useState(100);
  const [isDragging, setIsDragging] = useState(false);

  // Load waveform data when track changes
  useEffect(() => {
    const loadWaveform = async () => {
      if (!currentTrack) {
        setWaveformData(null);
        return;
      }

      try {
        const data = await musicService.getWaveform(currentTrack.filepath);
        setWaveformData(data);
      } catch (error) {
        console.error('Failed to load waveform:', error);
        setWaveformData(null);
      }
    };

    loadWaveform();
  }, [currentTrack]);

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

  // Draw waveform and indicators
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !waveformData || !duration) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    // Clear canvas
    ctx.fillStyle = '#0f0f0f';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Draw waveform
    const waveform = waveformData.waveform;
    const barWidth = canvasWidth / waveform.length;
    const maxAmplitude = Math.max(...waveform);

    ctx.fillStyle = '#3b82f6';
    for (let i = 0; i < waveform.length; i++) {
      const x = i * barWidth;
      const amplitude = waveform[i] / maxAmplitude;
      const barHeight = amplitude * (canvasHeight * 0.8);
      const y = (canvasHeight - barHeight) / 2;
      
      ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
    }

    // Draw progress indicator
    const progressX = (currentTime / duration) * canvasWidth;
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

  }, [waveformData, currentTime, duration, canvasWidth, sourceBpm, hotCues, currentTrack]);

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
        <h3 className="text-lg font-semibold text-white">Waveform</h3>
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
        
        {!waveformData && (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-800/50 rounded-lg">
            <div className="text-gray-400 animate-pulse text-sm">
              Loading waveform...
            </div>
          </div>
        )}
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
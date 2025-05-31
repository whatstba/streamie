'use client';

import React, { useEffect, useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import VirtualizedTrackList from '@/components/VirtualizedTrackList';
import DjModeControls from '@/components/player/DjModeControls';
import AdvancedDjControls from '@/components/player/AdvancedDjControls';
import BpmWaveformDisplay from '@/components/player/BpmWaveformDisplay';
import { SparklesIcon } from '@heroicons/react/24/outline';
import { musicService } from '@/services/musicService';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import Image from 'next/image';

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
  bpm?: number;
}

interface TrackAnalysis {
  bpm: number;
  success: boolean;
}

export default function Home() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<TrackAnalysis | null>(null);
  
  // Use audio player context
  const { 
    currentTrack, 
    playTrack, 
    djMode, 
    addToQueue, 
    queue,
    isTransitioning,
    nextTrack: upcomingTrack 
  } = useAudioPlayer();

  useEffect(() => {
    const fetchTracks = async () => {
      try {
        const trackList = await musicService.listTracks();
        setTracks(trackList);
        setError(null);
      } catch (err) {
        setError('Failed to load tracks. Make sure the Python server is running.');
        console.error('Error fetching tracks:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTracks();
  }, []);

  const formatDuration = (duration: number): string => {
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleTrackSelect = async (track: Track) => {
    setSelectedTrack(track);
    setAnalysis(null); // Clear previous analysis
    
    // Auto-fetch BPM if not available
    if (!track.bpm) {
      try {
        const analysis = await musicService.getTrackAnalysis(track.filepath);
        // Update the track in our tracks array with BPM
        setTracks(prevTracks => 
          prevTracks.map(t => 
            t.filepath === track.filepath ? { ...t, bpm: analysis.bpm } : t
          )
        );
        setAnalysis(analysis);
      } catch (err) {
        console.error('Error analyzing track:', err);
      }
    }
  };

  const handleAnalyzeTrack = async (track: Track) => {
    // Prevent multiple simultaneous analyses
    if (analyzing) return;

    setAnalyzing(true);
    try {
      const trackAnalysis = await musicService.getTrackAnalysis(track.filepath);
      setAnalysis(trackAnalysis);
      
      // Update the track with BPM data
      setTracks(prevTracks => 
        prevTracks.map(t => 
          t.filepath === track.filepath ? { ...t, bpm: trackAnalysis.bpm } : t
        )
      );
    } catch (err) {
      console.error('Error analyzing track:', err);
      // Still select the track even if analysis fails
      setAnalysis(null);
    } finally {
      setAnalyzing(false);
    }
  };

  const handlePlayAll = () => {
    if (tracks.length > 0) {
      playTrack(tracks[0], tracks);
    }
  };

  const handlePlayAllShuffle = () => {
    if (tracks.length > 0) {
      // Create shuffled copy
      const shuffled = [...tracks].sort(() => Math.random() - 0.5);
      playTrack(shuffled[0], shuffled);
    }
  };

  const handleAddToQueue = (track: Track) => {
    addToQueue(track);
  };

  const handleStartDjSet = () => {
    if (tracks.length > 0) {
      // Start with a shuffled playlist for DJ mode
      const shuffled = [...tracks].sort(() => Math.random() - 0.5);
      playTrack(shuffled[0], shuffled);
    }
  };

  // Use current track from audio player context for display
  const displayTrack = currentTrack || selectedTrack;

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">AI DJ Session</h1>
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 bg-purple-500 rounded-full flex items-center gap-2">
              <SparklesIcon className="h-5 w-5" />
              <span>Current Vibe: {djMode ? 'DJ Auto-Mix' : 'Chill Evening'}</span>
            </div>
          </div>
        </div>

        {/* DJ Mode Controls */}
        <DjModeControls />

        {/* Advanced DJ Controls */}
        <AdvancedDjControls />

        {/* Waveform Display */}
        <BpmWaveformDisplay />

        {/* Selected Track Info */}
        {displayTrack && (
          <div className={`border rounded-xl p-6 ${
            currentTrack 
              ? 'bg-purple-900/20 border-purple-500/30' 
              : 'bg-zinc-900/20 border-zinc-500/30'
          }`}>
            <div className="flex gap-6">
              {displayTrack.has_artwork ? (
                <div className="w-32 h-32 rounded-lg overflow-hidden bg-zinc-800 relative">
                  <Image
                    src={musicService.getArtworkUrl(displayTrack.filepath)}
                    alt={displayTrack.album || 'Album artwork'}
                    fill
                    className="object-cover"
                    onError={(e) => {
                      // Hide image on error
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                </div>
              ) : (
                <div className="w-32 h-32 rounded-lg bg-zinc-800 flex items-center justify-center text-4xl text-gray-600">
                  ♪
                </div>
              )}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-xl font-semibold">
                    {currentTrack ? 'Now Playing' : 'Selected Track'}
                  </h2>
                  {djMode && currentTrack && (
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-purple-600 rounded text-xs text-white">
                        DJ MODE
                      </span>
                      {isTransitioning && (
                        <span className="px-2 py-1 bg-orange-600 rounded text-xs text-white animate-pulse">
                          MIXING
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <p className="text-lg font-medium">{displayTrack.title || displayTrack.filename}</p>
                <p className="text-gray-400">
                  {displayTrack.artist || 'Unknown Artist'} 
                  {displayTrack.album && ` • ${displayTrack.album}`}
                  {displayTrack.year && ` • ${displayTrack.year}`}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  {formatDuration(displayTrack.duration)}
                  {displayTrack.genre && ` • ${displayTrack.genre}`}
                </p>
                
                {analyzing && (
                  <div className="mt-4">
                    <p className="text-yellow-400 animate-pulse">🎵 Analyzing beat pattern...</p>
                  </div>
                )}
                
                {analysis && !analyzing && (
                  <div className="mt-4">
                    <p className="text-green-400">✓ Beat analysis complete</p>
                    <p className="text-sm text-gray-400">
                      Tempo: {analysis.bpm.toFixed(2)} BPM 
                    </p>
                  </div>
                )}

                {/* Show next track in DJ mode */}
                {djMode && upcomingTrack && (
                  <div className="mt-4 p-3 bg-orange-900/20 border border-orange-500/30 rounded-lg">
                    <p className="text-xs text-orange-400 font-medium mb-1">NEXT UP:</p>
                    <p className="text-sm font-medium">{upcomingTrack.title || upcomingTrack.filename}</p>
                    <p className="text-xs text-gray-400">{upcomingTrack.artist || 'Unknown Artist'}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Music Library */}
        <div className="bg-zinc-900/50 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Music Library ({tracks.length} tracks)</h2>
            <div className="flex items-center gap-2">
              {djMode && (
                <button
                  onClick={handleStartDjSet}
                  disabled={tracks.length === 0}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
                >
                  🎧 Start DJ Set
                </button>
              )}
              <button
                onClick={handlePlayAllShuffle}
                disabled={tracks.length === 0}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
              >
                🔀 Shuffle All
              </button>
              <button
                onClick={handlePlayAll}
                disabled={tracks.length === 0}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
              >
                ▶️ Play All
              </button>
            </div>
          </div>
          {loading ? (
            <div className="text-center py-8 text-gray-400">Loading tracks...</div>
          ) : error ? (
            <div className="text-center py-8 text-red-400">{error}</div>
          ) : (
            <VirtualizedTrackList
              tracks={tracks}
              selectedTrackPath={selectedTrack?.filepath}
              onTrackSelect={handleTrackSelect}
              onTrackAnalyze={handleAnalyzeTrack}
              onAddToQueue={handleAddToQueue}
              isAnalyzing={analyzing}
            />
          )}
        </div>

        {/* AI DJ Features */}
        <div className="grid grid-cols-3 gap-4">
          <button 
            className="p-4 bg-zinc-900/50 rounded-xl hover:bg-zinc-800/50 transition text-left disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!displayTrack || analyzing}
          >
            <h3 className="font-medium mb-2">
              {analyzing ? 'Analyzing...' : 'Auto-Analysis Active'}
            </h3>
            <p className="text-sm text-gray-400">
              Tracks are automatically analyzed when selected
            </p>
          </button>
          <button 
            className="p-4 bg-zinc-900/50 rounded-xl hover:bg-zinc-800/50 transition text-left"
            disabled={!djMode}
          >
            <h3 className="font-medium mb-2">
              {djMode ? 'DJ Auto-Mix Active' : 'Enable DJ Mode'}
            </h3>
            <p className="text-sm text-gray-400">
              {djMode 
                ? 'Automatic crossfading and track transitions'
                : 'Turn on DJ mode for seamless mixing'
              }
            </p>
          </button>
          <button className="p-4 bg-zinc-900/50 rounded-xl hover:bg-zinc-800/50 transition text-left">
            <h3 className="font-medium mb-2">Queue Management</h3>
            <p className="text-sm text-gray-400">
              {queue.length > 0 
                ? `${queue.length} tracks in queue`
                : 'Add tracks to build your set'
              }
            </p>
          </button>
        </div>
      </div>
    </MainLayout>
  );
}

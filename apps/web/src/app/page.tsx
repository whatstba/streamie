'use client';

import React, { useEffect, useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import VirtualizedTrackList from '@/components/VirtualizedTrackList';
import DjModeControls from '@/components/player/DjModeControls';
import AdvancedDjControls from '@/components/player/AdvancedDjControls';
import BpmWaveformDisplay from '@/components/player/BpmWaveformDisplay';
import { SparklesIcon, PlayIcon } from '@heroicons/react/24/outline';
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
  const [vibeInput, setVibeInput] = useState('');
  const [generatingPlaylist, setGeneratingPlaylist] = useState(false);
  const [generatedPlaylist, setGeneratedPlaylist] = useState<Track[]>([]);
  
  // Use audio player context
  const { 
    currentTrack, 
    playTrack, 
    djMode, 
    addToQueue, 
    queue,
    isTransitioning,
    nextTrack: upcomingTrack,
    toggleDjMode
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

  const handleGenerateVibePlaylist = async () => {
    if (!vibeInput.trim()) return;
    
    setGeneratingPlaylist(true);
    try {
      const response = await fetch('http://localhost:8000/ai/generate-vibe-playlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vibe_description: vibeInput.trim(),
          playlist_length: 10
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate playlist: ${response.statusText}`);
      }

      const data = await response.json();
      setGeneratedPlaylist(data.playlist || []);
    } catch (err) {
      console.error('Error generating playlist:', err);
      setError('Failed to generate playlist. Make sure the AI service is running.');
    } finally {
      setGeneratingPlaylist(false);
    }
  };

  const handlePlayGeneratedPlaylist = () => {
    if (generatedPlaylist.length > 0) {
      playTrack(generatedPlaylist[0], generatedPlaylist);
      toggleDjMode(); // Enable DJ mode for the generated playlist
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
              <span>Current Mode: {djMode ? 'DJ Auto-Mix' : 'Manual Mode'}</span>
            </div>
          </div>
        </div>

        {/* Vibe-Based Playlist Generator */}
        <div className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl p-6 border border-purple-500/30">
          <div className="flex items-center gap-3 mb-4">
            <SparklesIcon className="h-6 w-6 text-purple-400" />
            <h3 className="font-medium text-xl">Generate Playlist by Vibe</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="vibe-input" className="block text-sm font-medium mb-2">
                Describe the vibe you want (e.g., "energetic hip-hop for working out", "chill R&B for late night", "upbeat dance music")
              </label>
              <input
                id="vibe-input"
                type="text"
                value={vibeInput}
                onChange={(e) => setVibeInput(e.target.value)}
                placeholder="Enter your desired vibe..."
                className="w-full px-4 py-3 bg-black/30 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none"
                onKeyPress={(e) => e.key === 'Enter' && handleGenerateVibePlaylist()}
              />
            </div>
            
            <button
              onClick={handleGenerateVibePlaylist}
              disabled={!vibeInput.trim() || generatingPlaylist}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white font-medium transition"
            >
              {generatingPlaylist ? '🤖 Creating Playlist...' : '✨ Generate Playlist'}
            </button>
          </div>

          {/* Generated Playlist */}
          {generatedPlaylist.length > 0 && (
            <div className="mt-6 p-4 bg-black/20 rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-medium text-lg">Generated Playlist ({generatedPlaylist.length} tracks)</h4>
                <button
                  onClick={handlePlayGeneratedPlaylist}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition flex items-center gap-2"
                >
                  <PlayIcon className="h-4 w-4" />
                  Play Playlist
                </button>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {generatedPlaylist.map((track, index) => (
                  <div key={index} className="flex items-center justify-between text-sm p-3 bg-purple-900/20 rounded border border-purple-500/20">
                    <div className="flex-1">
                      <div className="font-medium">{track.title || track.filename}</div>
                      <div className="text-gray-400">{track.artist || 'Unknown Artist'}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleTrackSelect(track)}
                        className="px-2 py-1 bg-purple-600 hover:bg-purple-700 rounded text-xs"
                      >
                        Select
                      </button>
                      <button
                        onClick={() => handleAddToQueue(track)}
                        className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs"
                      >
                        Queue
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Combined DJ Controls and Waveform Display */}
        {djMode && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DjModeControls />
            <BpmWaveformDisplay />
          </div>
        )}

        {/* Advanced DJ Controls - Collapsible */}
        <AdvancedDjControls />

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

        {/* Enable DJ Mode Button - Only show if not in DJ mode */}
        {!djMode && generatedPlaylist.length === 0 && (
          <div className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl p-6 border border-purple-500/30">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-xl mb-2">Enable DJ Mode</h3>
                <p className="text-sm text-gray-400">
                  Turn on DJ mode for automatic mixing, beat matching, and seamless transitions
                </p>
              </div>
              <button
                onClick={() => {
                  toggleDjMode();
                  if (tracks.length > 0 && !currentTrack) {
                    const shuffled = [...tracks].sort(() => Math.random() - 0.5);
                    playTrack(shuffled[0], shuffled);
                  }
                }}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg text-white font-medium transition"
              >
                🎧 Enable DJ Mode
              </button>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}

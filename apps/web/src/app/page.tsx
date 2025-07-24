'use client';

import React, { useEffect, useState, useRef } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import VirtualizedTrackList from '@/components/VirtualizedTrackList';
import DjModeControls from '@/components/player/DjModeControls';
import PlaylistGenerationUI from '@/components/ai/PlaylistGenerationUI';
import MusicFolderSetup from '@/components/music-library/MusicFolderSetup';
import MusicLibrarySettings from '@/components/music-library/MusicLibrarySettings';
import { SparklesIcon, PlayIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { musicService } from '@/services/musicService';
import { musicLibraryService } from '@/services/musicLibraryService';
import { aiService, type DJSet } from '@/services/aiService';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import { useToast } from '@/context/ToastContext';
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
  const [aiThinkingMessages, setAiThinkingMessages] = useState<string[]>([]);
  const [isTracklistCollapsed, setIsTracklistCollapsed] = useState(true);
  const [isDjPanelCollapsed, setIsDjPanelCollapsed] = useState(false);

  // Add ref for request debouncing
  const generateRequestRef = useRef<AbortController | null>(null);

  // New state for enhanced UI
  const [generationStage, setGenerationStage] = useState<
    | 'idle'
    | 'analyzing_vibe'
    | 'searching_library'
    | 'matching_tracks'
    | 'optimizing_order'
    | 'finalizing'
    | 'complete'
  >('idle');
  const [stageNumber, setStageNumber] = useState(0);
  const [stageProgress, setStageProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState('');
  const [foundTracks, setFoundTracks] = useState<any[]>([]);
  const [detectedMood, setDetectedMood] = useState<
    { genres: string[]; energy: number; mood: string } | undefined
  >();
  const [playlistTransitions, setPlaylistTransitions] = useState<any[]>([]);
  const [autoPlayGenerated, setAutoPlayGenerated] = useState(true);
  const [currentDJSet, setCurrentDJSet] = useState<DJSet | null>(null);
  const [djSetPlaying, setDJSetPlaying] = useState(false);

  // Music library state
  const [showFirstRunSetup, setShowFirstRunSetup] = useState(false);
  const [libraryStats, setLibraryStats] = useState<any>(null);
  const [showLibrarySettings, setShowLibrarySettings] = useState(false);

  // Use audio player context
  const {
    currentTrack,
    playTrack,
    djMode,
    addToQueue,
    toggleDjMode,
    playDJSet,
    isServerStreaming,
    djSet,
    playbackStatus,
  } = useAudioPlayer();

  // Use toast context
  const { success: showSuccess, error: showError } = useToast();

  useEffect(() => {
    const initializeLibrary = async () => {
      try {
        // Load tracks directly first - this was working before
        console.log('🎵 Loading tracks...');
        const trackList = await musicService.listTracks();
        console.log(`✅ Loaded ${trackList.length} tracks`);
        setTracks(trackList);

        // Then try to get library stats (non-blocking)
        try {
          console.log('🔍 Checking library stats...');
          const stats = await musicLibraryService.getLibraryStats();
          console.log('📊 Library stats:', stats);
          setLibraryStats(stats);

          // Only show first-run setup if we have 0 tracks AND 0 folders
          if (trackList.length === 0 && stats.active_folders === 0) {
            console.log('⚠️ No tracks and no folders, showing first-run setup');
            setShowFirstRunSetup(true);
          }
        } catch (statsErr) {
          console.warn('❌ Failed to load library stats (non-critical):', statsErr);
          // If we have tracks, continue without stats
          if (trackList.length === 0) {
            setShowFirstRunSetup(true);
          }
        }

        setError(null);
      } catch (err) {
        setError('Failed to load tracks. Make sure the Python server is running.');
        console.error('❌ Error loading tracks:', err);
      } finally {
        setLoading(false);
      }
    };

    initializeLibrary();
  }, []);

  // Track current playback position in DJ set
  useEffect(() => {
    if (isServerStreaming && playbackStatus && djSet) {
      // Update current track based on playback status
      const currentTrackOrder = playbackStatus.current_track_order;
      if (currentTrackOrder !== undefined && currentTrackOrder < djSet.tracks.length) {
        const track = djSet.tracks[currentTrackOrder];
        const newCurrentTrack = {
          filename: track.filepath.split('/').pop() || '',
          filepath: track.filepath,
          duration: track.end_time - track.start_time,
          title: track.title,
          artist: track.artist,
          album: track.album || null,
          genre: track.genre || null,
          year: null,
          has_artwork: false,
          bpm: track.bpm,
        };
        
        // Only update if it's actually different to avoid unnecessary re-renders
        if (!currentTrack || currentTrack.filepath !== newCurrentTrack.filepath) {
          console.log(`🎵 Now playing track ${currentTrackOrder + 1} of ${djSet.tracks.length}`);
        }
      }
    }
  }, [isServerStreaming, playbackStatus, djSet, currentTrack]);

  const formatDuration = (duration: number): string => {
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleTrackSelect = async (track: Track) => {
    setSelectedTrack(track);
    setAnalysis(null); // Clear previous analysis
    // NO automatic analysis - only when explicitly requested
  };

  const handleAnalyzeTrack = async (track: Track) => {
    // Prevent multiple simultaneous analyses
    if (analyzing) return;

    setAnalyzing(true);
    try {
      const trackAnalysis = await musicService.getTrackAnalysis(track.filepath);
      setAnalysis(trackAnalysis);

      // Update the track with BPM data
      setTracks((prevTracks) =>
        prevTracks.map((t) =>
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

    // Cancel any previous request
    if (generateRequestRef.current) {
      generateRequestRef.current.abort();
    }

    // Create new AbortController for this request
    const abortController = new AbortController();
    generateRequestRef.current = abortController;

    setGeneratingPlaylist(true);
    setAiThinkingMessages([]);
    setGeneratedPlaylist([]);
    setGenerationStage('analyzing_vibe');
    setStageNumber(1);
    setStageProgress(0);
    setFoundTracks([]);
    setDetectedMood(undefined);
    setCurrentDJSet(null);

    try {
      // Simulate progress stages for UI feedback
      setStageMessage('Analyzing your vibe description...');
      setStageProgress(0.2);
      
      // Generate the DJ set
      const djSetResponse = await aiService.generateDJSet({
        vibe_description: vibeInput.trim(),
        duration_minutes: 30,
        energy_pattern: 'wave',
      }, abortController.signal);

      if (!djSetResponse.success || !djSetResponse.dj_set) {
        throw new Error(djSetResponse.error || 'Failed to generate DJ set');
      }

      const djSet = djSetResponse.dj_set;
      setCurrentDJSet(djSet);

      // Update UI with results
      setStageMessage('DJ set generated successfully!');
      setStageProgress(1);
      setGenerationStage('complete');
      
      // Convert DJ set tracks to playlist format for compatibility
      const playlist = djSet.tracks.map((track) => ({
        filename: track.filepath.split('/').pop() || track.filepath,
        filepath: track.filepath,
        title: track.title,
        artist: track.artist,
        album: track.album || null,
        genre: track.genre || null,
        year: null,
        has_artwork: false,
        bpm: track.bpm,
        duration: track.end_time - track.start_time,
      }));
      
      setGeneratedPlaylist(playlist);
      setPlaylistTransitions(djSet.transitions);
      
      // Set detected mood based on the vibe
      setDetectedMood({
        genres: [...new Set(djSet.tracks.map(t => t.genre).filter(Boolean))] as string[],
        energy: djSet.tracks.reduce((sum, t) => sum + t.energy_level, 0) / djSet.tracks.length,
        mood: djSet.vibe_description,
      });
      
      setGeneratingPlaylist(false);
      
      // Auto-play the DJ set
      if (autoPlayGenerated) {
        handlePlayDJSet();
      }
    } catch (err) {
      // Check if the error is due to request being aborted
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Generation request was cancelled');
        // Reset state without showing error
        setGeneratingPlaylist(false);
        setGenerationStage('idle');
        return;
      }
      
      console.error('Error generating DJ set:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate DJ set. Make sure the AI service is running.');
      setGeneratingPlaylist(false);
      setGenerationStage('idle');
    } finally {
      // Clear the ref when done
      if (generateRequestRef.current === abortController) {
        generateRequestRef.current = null;
      }
    }
  };

  const handlePlayDJSet = async () => {
    if (!currentDJSet) return;
    
    try {
      setDJSetPlaying(true);
      
      // Use the new playDJSet method from AudioPlayerContext
      await playDJSet(currentDJSet);
      
      showSuccess('DJ set is now playing!');
      
    } catch (err) {
      console.error('Error playing DJ set:', err);
      showError(err instanceof Error ? err.message : 'Failed to play DJ set');
      setDJSetPlaying(false);
    }
  };

  const handlePlayGeneratedPlaylist = async () => {
    // This function is deprecated - handlePlayDJSet is called automatically
    console.warn('handlePlayGeneratedPlaylist is deprecated. Using server-side DJ sets.');
  };

  const handleFirstRunComplete = async () => {
    setShowFirstRunSetup(false);
    setLoading(true);

    try {
      // Reload tracks and library stats
      const [trackList, stats] = await Promise.all([
        musicService.listTracks(),
        musicLibraryService.getLibraryStats(),
      ]);
      setTracks(trackList);
      setLibraryStats(stats);
      showSuccess('Library setup complete', 'Your music is ready to use!');
    } catch (err) {
      setError('Failed to load tracks after setup');
      showError('Setup Error', 'There was an issue loading your music');
    } finally {
      setLoading(false);
    }
  };

  const handleLibraryUpdate = async () => {
    try {
      const [trackList, stats] = await Promise.all([
        musicService.listTracks(),
        musicLibraryService.getLibraryStats(),
      ]);
      setTracks(trackList);
      setLibraryStats(stats);
    } catch (err) {
      console.error('Failed to refresh library:', err);
    }
  };

  // Use current track from audio player context for display
  const displayTrack = currentTrack || selectedTrack;

  // Show first-run setup if no folders are configured
  if (showFirstRunSetup) {
    return <MusicFolderSetup onComplete={handleFirstRunComplete} />;
  }

  return (
    <MainLayout>
      <div className="h-full flex flex-col overflow-hidden">
        {/* Fixed content area */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h1 className="text-3xl font-bold">Current Session</h1>
              <button
                onClick={() => setShowLibrarySettings(true)}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                title="Music Library Settings"
              >
                <Cog6ToothIcon className="h-4 w-4" />
                Library
              </button>
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
                    Describe the vibe you want (e.g., &ldquo;energetic hip-hop for working
                    out&rdquo;, &ldquo;chill R&B for late night&rdquo;, &ldquo;upbeat dance
                    music&rdquo;)
                  </label>
                  <input
                    id="vibe-input"
                    type="text"
                    value={vibeInput}
                    onChange={(e) => setVibeInput(e.target.value)}
                    placeholder="Enter your desired vibe..."
                    className="w-full px-4 py-3 bg-black/30 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none"
                    onKeyPress={(e) => e.key === 'Enter' && handleGenerateVibePlaylist()}
                    disabled={generatingPlaylist}
                  />
                </div>

                {!generatingPlaylist && (
                  <button
                    onClick={handleGenerateVibePlaylist}
                    disabled={!vibeInput.trim()}
                    className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white font-medium transition"
                  >
                    ✨ Generate Playlist
                  </button>
                )}
              </div>

              {/* Enhanced AI Generation UI */}
              {generatingPlaylist && (
                <PlaylistGenerationUI
                  stage={generationStage}
                  stageNumber={stageNumber}
                  totalStages={5}
                  progress={stageProgress}
                  message={stageMessage}
                  foundTracks={foundTracks}
                  targetTrackCount={10}
                  detectedMood={detectedMood}
                />
              )}

              {/* Generated Playlist */}
              {!generatingPlaylist && generatedPlaylist.length > 0 && (
                <div className="mt-6 p-4 bg-black/20 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium text-lg">
                      Generated Playlist ({generatedPlaylist.length} tracks)
                    </h4>
                    <button
                      onClick={handlePlayDJSet}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition flex items-center gap-2"
                    >
                      <PlayIcon className="h-4 w-4" />
                      Play Playlist
                    </button>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {generatedPlaylist.map((track, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between text-sm p-3 bg-purple-900/20 rounded border border-purple-500/20"
                      >
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

            {/* Combined DJ Controls - Collapsible */}
            {djMode && (
              <div className="bg-zinc-900/50 rounded-xl border border-zinc-700 overflow-hidden">
                <button
                  onClick={() => setIsDjPanelCollapsed(!isDjPanelCollapsed)}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-zinc-800/50 transition"
                >
                  <h2 className="text-xl font-semibold">DJ Controls</h2>
                  <span className="text-gray-400">{isDjPanelCollapsed ? '▶' : '▼'}</span>
                </button>
                {!isDjPanelCollapsed && (
                  <div className="p-6 pt-0 space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <DjModeControls />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Music Library - Collapsible with fixed height scrollable list */}
            <div className="bg-zinc-900/50 rounded-xl border border-zinc-700 overflow-hidden">
              <div className="px-6 py-4 flex items-center justify-between hover:bg-zinc-800/50 transition">
                <button
                  onClick={() => setIsTracklistCollapsed(!isTracklistCollapsed)}
                  className="flex items-center gap-2"
                >
                  <h2 className="text-xl font-semibold">Music Library ({tracks.length} tracks)</h2>
                  <span className="text-gray-400">{isTracklistCollapsed ? '▶' : '▼'}</span>
                </button>
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
              {!isTracklistCollapsed && (
                <div className="p-6 pt-0">
                  {loading ? (
                    <div className="text-center py-8 text-gray-400">Loading tracks...</div>
                  ) : error ? (
                    <div className="text-center py-8 text-red-400">{error}</div>
                  ) : (
                    <div className="h-96 overflow-hidden">
                      <VirtualizedTrackList
                        tracks={tracks}
                        selectedTrackPath={selectedTrack?.filepath}
                        onTrackSelect={handleTrackSelect}
                        onTrackAnalyze={handleAnalyzeTrack}
                        onAddToQueue={handleAddToQueue}
                        isAnalyzing={analyzing}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Music Library Settings Modal */}
      <MusicLibrarySettings
        isOpen={showLibrarySettings}
        onClose={() => setShowLibrarySettings(false)}
        onLibraryUpdate={handleLibraryUpdate}
      />
    </MainLayout>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import {
  SparklesIcon,
  PlayIcon,
  QueueListIcon,
  StarIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import { aiService } from '@/services/aiService';
import { useAudioPlayer } from '@/context/AudioPlayerContext';

interface VibeAnalysis {
  track_id: string;
  bpm: number;
  energy_level: number;
  dominant_vibe: string;
  mood_vector: Record<string, number>;
  genre: string;
  recommendations: string[];
}

interface TrackSuggestion {
  track: any;
  confidence: number;
  transition?: any;
  reasoning?: string;
}

interface AiDjPanelProps {
  tracks: any[];
  onTrackSelect: (track: any) => void;
  onAddToQueue: (track: any) => void;
}

export default function AiDjPanel({ tracks, onTrackSelect, onAddToQueue }: AiDjPanelProps) {
  const { currentTrack, playTrack, djMode } = useAudioPlayer();
  const [vibeAnalysis, setVibeAnalysis] = useState<VibeAnalysis | null>(null);
  const [nextSuggestion, setNextSuggestion] = useState<TrackSuggestion | null>(null);
  const [generatedPlaylist, setGeneratedPlaylist] = useState<any[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingPlaylist, setIsGeneratingPlaylist] = useState(false);
  const [isSuggestingNext, setIsSuggestingNext] = useState(false);
  const [playedTracks, setPlayedTracks] = useState<string[]>([]);
  const [rating, setRating] = useState<number>(0);
  const [showRating, setShowRating] = useState(false);

  // Update played tracks when current track changes
  useEffect(() => {
    if (currentTrack && !playedTracks.includes(currentTrack.filepath)) {
      setPlayedTracks((prev) => [...prev, currentTrack.filepath]);
    }
  }, [currentTrack, playedTracks]);

  const analyzeCurrentVibe = async () => {
    if (!currentTrack) return;

    setIsAnalyzing(true);
    try {
      const analysis = await aiService.analyzeVibe({
        current_track_id: currentTrack.filepath,
        context: {
          dj_mode: djMode,
          played_tracks: playedTracks,
        },
      });
      setVibeAnalysis(analysis);
    } catch (error) {
      console.error('Error analyzing vibe:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getNextTrackSuggestion = async () => {
    if (!currentTrack) return;

    setIsSuggestingNext(true);
    try {
      const suggestion = await aiService.suggestNextTrack({
        current_track_id: currentTrack.filepath,
        played_tracks: playedTracks,
        context: {
          dj_mode: djMode,
          energy_level: vibeAnalysis?.energy_level,
        },
      });
      setNextSuggestion(suggestion);
    } catch (error) {
      console.error('Error getting track suggestion:', error);
    } finally {
      setIsSuggestingNext(false);
    }
  };

  const generateAiPlaylist = async (
    energyPattern: 'build_up' | 'peak_time' | 'cool_down' | 'wave' = 'wave'
  ) => {
    if (!currentTrack) return;

    setIsGeneratingPlaylist(true);
    try {
      const playlist = await aiService.generatePlaylist({
        seed_track_id: currentTrack.filepath,
        playlist_length: 8,
        energy_pattern: energyPattern,
        context: {
          dj_mode: djMode,
          played_tracks: playedTracks,
        },
      });
      setGeneratedPlaylist(playlist.playlist);
    } catch (error) {
      console.error('Error generating playlist:', error);
    } finally {
      setIsGeneratingPlaylist(false);
    }
  };

  const rateTransition = async (rating: number) => {
    if (!currentTrack || playedTracks.length < 2) return;

    try {
      const previousTrack = playedTracks[playedTracks.length - 2];
      await aiService.rateTransition({
        from_track_id: previousTrack,
        to_track_id: currentTrack.filepath,
        rating: rating / 5, // Convert 1-5 to 0-1
      });
      setShowRating(false);
      setRating(0);
    } catch (error) {
      console.error('Error rating transition:', error);
    }
  };

  const playAiSuggestion = () => {
    if (nextSuggestion?.track) {
      // Find the full track object in our tracks array
      const fullTrack = tracks.find((t) => t.filepath === nextSuggestion.track.filepath);
      if (fullTrack) {
        playTrack(fullTrack, tracks);
        setNextSuggestion(null); // Clear suggestion after playing
      }
    }
  };

  if (!djMode) {
    return (
      <div className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl p-6 border border-purple-500/30">
        <div className="flex items-center gap-3 mb-4">
          <SparklesIcon className="h-6 w-6 text-purple-400" />
          <h3 className="font-medium text-xl">AI DJ Assistant</h3>
        </div>
        <p className="text-gray-400 mb-4">
          Enable DJ mode to access AI-powered mixing suggestions, vibe analysis, and intelligent
          playlist generation.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl p-6 border border-purple-500/30">
      <div className="flex items-center gap-3 mb-6">
        <SparklesIcon className="h-6 w-6 text-purple-400" />
        <h3 className="font-medium text-xl">AI DJ Assistant</h3>
        {djMode && <span className="px-2 py-1 bg-purple-600 rounded text-xs">ACTIVE</span>}
      </div>

      {/* Current Track Analysis */}
      {currentTrack && (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <button
              onClick={analyzeCurrentVibe}
              disabled={isAnalyzing}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
            >
              {isAnalyzing ? '🧠 Analyzing...' : '🎵 Analyze Vibe'}
            </button>

            {playedTracks.length > 1 && !showRating && (
              <button
                onClick={() => setShowRating(true)}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg font-medium transition"
              >
                ⭐ Rate Last Mix
              </button>
            )}
          </div>

          {/* Transition Rating */}
          {showRating && (
            <div className="p-4 bg-orange-900/20 border border-orange-500/30 rounded-lg">
              <p className="text-sm font-medium mb-2">Rate the last transition:</p>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => setRating(star)}
                    className="text-2xl hover:scale-110 transition"
                  >
                    {star <= rating ? (
                      <StarIconSolid className="h-6 w-6 text-yellow-400" />
                    ) : (
                      <StarIcon className="h-6 w-6 text-gray-400" />
                    )}
                  </button>
                ))}
                <button
                  onClick={() => rateTransition(rating)}
                  disabled={rating === 0}
                  className="ml-4 px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium transition"
                >
                  Submit
                </button>
                <button
                  onClick={() => {
                    setShowRating(false);
                    setRating(0);
                  }}
                  className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm font-medium transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Vibe Analysis Results */}
          {vibeAnalysis && (
            <div className="p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
              <h4 className="font-medium mb-2">🎭 Current Vibe Analysis</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Dominant Vibe:</span>
                  <span className="ml-2 font-medium text-blue-400">
                    {vibeAnalysis.dominant_vibe}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Energy Level:</span>
                  <span className="ml-2 font-medium text-green-400">
                    {(vibeAnalysis.energy_level * 100).toFixed(0)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Genre:</span>
                  <span className="ml-2 font-medium text-purple-400">{vibeAnalysis.genre}</span>
                </div>
                <div>
                  <span className="text-gray-400">BPM:</span>
                  <span className="ml-2 font-medium text-orange-400">
                    {vibeAnalysis.bpm.toFixed(1)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Next Track Suggestion */}
          <div className="flex items-center gap-4">
            <button
              onClick={getNextTrackSuggestion}
              disabled={isSuggestingNext}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition"
            >
              {isSuggestingNext ? '🤖 AI Thinking...' : '🎯 Get Next Track'}
            </button>

            {nextSuggestion && (
              <div className="flex-1 p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">
                      {nextSuggestion.track.title || nextSuggestion.track.filename}
                    </p>
                    <p className="text-xs text-gray-400">
                      {nextSuggestion.track.artist} • {(nextSuggestion.confidence * 100).toFixed(0)}
                      % match
                    </p>
                    {nextSuggestion.reasoning && (
                      <p className="text-xs text-green-400 mt-1">{nextSuggestion.reasoning}</p>
                    )}
                  </div>
                  <button
                    onClick={playAiSuggestion}
                    className="px-3 py-1 bg-green-600 hover:bg-green-700 rounded text-sm font-medium transition"
                  >
                    <PlayIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Playlist Generation */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => generateAiPlaylist('wave')}
                disabled={isGeneratingPlaylist}
                className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
              >
                🌊 Wave Playlist
              </button>
              <button
                onClick={() => generateAiPlaylist('build_up')}
                disabled={isGeneratingPlaylist}
                className="px-3 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
              >
                📈 Build Up
              </button>
              <button
                onClick={() => generateAiPlaylist('peak_time')}
                disabled={isGeneratingPlaylist}
                className="px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
              >
                🔥 Peak Time
              </button>
              <button
                onClick={() => generateAiPlaylist('cool_down')}
                disabled={isGeneratingPlaylist}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
              >
                🌙 Cool Down
              </button>
            </div>

            {isGeneratingPlaylist && (
              <p className="text-yellow-400 animate-pulse text-sm">
                🤖 AI is crafting your perfect playlist...
              </p>
            )}

            {/* Generated Playlist */}
            {generatedPlaylist.length > 0 && (
              <div className="p-4 bg-indigo-900/20 border border-indigo-500/30 rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <QueueListIcon className="h-4 w-4" />
                  AI Generated Playlist ({generatedPlaylist.length} tracks)
                </h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {generatedPlaylist.map((track, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between text-sm p-2 bg-black/20 rounded"
                    >
                      <div>
                        <span className="font-medium">{track.title || track.filename}</span>
                        <span className="text-gray-400 ml-2">{track.artist}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onTrackSelect(track)}
                          className="px-2 py-1 bg-purple-600 hover:bg-purple-700 rounded text-xs"
                        >
                          Select
                        </button>
                        <button
                          onClick={() => onAddToQueue(track)}
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
        </div>
      )}
    </div>
  );
}

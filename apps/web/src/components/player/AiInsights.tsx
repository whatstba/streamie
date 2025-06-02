'use client';

import React, { useState, useEffect } from 'react';
import { ChartBarIcon, TrophyIcon, HeartIcon } from '@heroicons/react/24/outline';
import { aiService } from '@/services/aiService';

interface MixingInsights {
  top_transitions: Array<{
    _id: { from: string; to: string };
    avg_rating: number;
    count: number;
  }>;
  most_mixed_tracks: Array<{
    filepath: string;
    title?: string;
    artist?: string;
    mix_count: number;
  }>;
  total_ratings: number;
}

export default function AiInsights() {
  const [insights, setInsights] = useState<MixingInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const fetchInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await aiService.getMixingInsights();
      setInsights(data);
    } catch (err) {
      setError('Failed to load mixing insights');
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && !insights && !loading) {
      fetchInsights();
    }
  }, [isOpen, insights, loading]);

  if (!isOpen) {
    return (
      <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-700/50">
        <button
          onClick={() => setIsOpen(true)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-3">
            <ChartBarIcon className="h-5 w-5 text-blue-400" />
            <h3 className="font-medium">AI Mixing Insights</h3>
          </div>
          <span className="text-gray-400">Click to view →</span>
        </button>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900/50 rounded-xl p-6 border border-zinc-700/50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <ChartBarIcon className="h-6 w-6 text-blue-400" />
          <h3 className="font-medium text-xl">AI Mixing Insights</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchInsights}
            disabled={loading}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium transition"
          >
            {loading ? '🔄' : '↻'} Refresh
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm font-medium transition"
          >
            ✕ Close
          </button>
        </div>
      </div>

      {loading && (
        <div className="text-center py-8 text-gray-400">
          <div className="animate-pulse">🧠 Analyzing mixing patterns...</div>
        </div>
      )}

      {error && (
        <div className="text-center py-8 text-red-400">
          <div className="mb-2">❌ {error}</div>
          <button
            onClick={fetchInsights}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-medium transition"
          >
            Try Again
          </button>
        </div>
      )}

      {insights && !loading && (
        <div className="space-y-6">
          {/* Stats Overview */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">{insights.total_ratings}</div>
              <div className="text-xs text-gray-400">Total Ratings</div>
            </div>
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{insights.top_transitions.length}</div>
              <div className="text-xs text-gray-400">Top Transitions</div>
            </div>
            <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-400">{insights.most_mixed_tracks.length}</div>
              <div className="text-xs text-gray-400">Popular Tracks</div>
            </div>
          </div>

          {/* Top Transitions */}
          {insights.top_transitions.length > 0 && (
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <TrophyIcon className="h-5 w-5 text-yellow-400" />
                Best Rated Transitions
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {insights.top_transitions.map((transition, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-black/20 rounded">
                    <div className="flex-1">
                      <div className="text-sm font-medium">
                        {transition._id.from.split('/').pop()?.replace(/\.[^/.]+$/, '')}
                      </div>
                      <div className="text-xs text-gray-400">
                        ↓ {transition._id.to.split('/').pop()?.replace(/\.[^/.]+$/, '')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-yellow-400">
                        {(transition.avg_rating * 5).toFixed(1)}/5
                      </div>
                      <div className="text-xs text-gray-400">
                        {transition.count} time{transition.count !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Most Mixed Tracks */}
          {insights.most_mixed_tracks.length > 0 && (
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <HeartIcon className="h-5 w-5 text-red-400" />
                Most Mixed Tracks
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {insights.most_mixed_tracks.map((track, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-black/20 rounded">
                    <div className="flex-1">
                      <div className="text-sm font-medium">
                        {track.title || track.filepath.split('/').pop()?.replace(/\.[^/.]+$/, '')}
                      </div>
                      {track.artist && (
                        <div className="text-xs text-gray-400">{track.artist}</div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-red-400">
                        {track.mix_count} mix{track.mix_count !== 1 ? 'es' : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {insights.total_ratings === 0 && (
            <div className="text-center py-8 text-gray-400">
              <div className="text-4xl mb-2">🎧</div>
              <div className="font-medium mb-1">No mixing data yet</div>
              <div className="text-sm">
                Start mixing tracks and rating transitions to see AI insights!
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
} 
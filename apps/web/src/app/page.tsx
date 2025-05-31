'use client';

import React, { useEffect, useState } from 'react';
import MainLayout from '@/components/layout/MainLayout';
import { SparklesIcon } from '@heroicons/react/24/outline';
import { musicService } from '@/services/musicService';

interface Track {
  filename: string;
  duration: number;
  title: string | null;
  artist: string | null;
}

export default function Home() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">AI DJ Session</h1>
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 bg-purple-500 rounded-full flex items-center gap-2">
              <SparklesIcon className="h-5 w-5" />
              <span>Current Vibe: Chill Evening</span>
            </div>
          </div>
        </div>

        {/* Current Session */}
        <div className="bg-zinc-900/50 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4">Available Tracks</h2>
          {loading ? (
            <div className="text-center py-8 text-gray-400">Loading tracks...</div>
          ) : error ? (
            <div className="text-center py-8 text-red-400">{error}</div>
          ) : (
            <div className="space-y-2">
              {tracks.map((track) => (
                <div
                  key={track.filename}
                  className="flex items-center justify-between p-3 hover:bg-zinc-800/50 rounded-lg transition cursor-pointer"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-zinc-800 rounded flex items-center justify-center text-gray-400">
                      ♪
                    </div>
                    <div>
                      <h3 className="font-medium">{track.title || track.filename}</h3>
                      <p className="text-sm text-gray-400">{track.artist || 'Unknown Artist'}</p>
                    </div>
                  </div>
                  <span className="text-gray-400">{formatDuration(track.duration)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI DJ Suggestions */}
        <div className="grid grid-cols-3 gap-4">
          <button className="p-4 bg-zinc-900/50 rounded-xl hover:bg-zinc-800/50 transition text-left">
            <h3 className="font-medium mb-2">Analyze Current Track</h3>
            <p className="text-sm text-gray-400">
              Get beat analysis and waveform visualization
            </p>
          </button>
          <button className="p-4 bg-zinc-900/50 rounded-xl hover:bg-zinc-800/50 transition text-left">
            <h3 className="font-medium mb-2">Generate Transition</h3>
            <p className="text-sm text-gray-400">
              Find the best way to mix into the next track
            </p>
          </button>
          <button className="p-4 bg-zinc-900/50 rounded-xl hover:bg-zinc-800/50 transition text-left">
            <h3 className="font-medium mb-2">Adjust BPM</h3>
            <p className="text-sm text-gray-400">
              Speed up or slow down to match the desired tempo
            </p>
          </button>
        </div>
      </div>
    </MainLayout>
  );
}

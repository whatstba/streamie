'use client';

import React, { useState } from 'react';
import {
  PlayIcon,
  PauseIcon,
  ForwardIcon,
  BackwardIcon,
  SpeakerWaveIcon,
  SparklesIcon,
} from '@heroicons/react/24/solid';

const Player = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');

  return (
    <div className="h-24 bg-zinc-900 border-t border-zinc-800 px-4">
      <div className="max-w-screen-xl mx-auto h-full flex items-center justify-between">
        {/* Currently Playing */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-zinc-800 rounded-md"></div>
          <div>
            <h3 className="font-medium">Current Track</h3>
            <p className="text-sm text-gray-400">Artist</p>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-4">
            <button className="text-gray-400 hover:text-white transition">
              <BackwardIcon className="h-5 w-5" />
            </button>
            <button 
              className="p-2 bg-white rounded-full hover:scale-105 transition"
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? (
                <PauseIcon className="h-6 w-6 text-black" />
              ) : (
                <PlayIcon className="h-6 w-6 text-black" />
              )}
            </button>
            <button className="text-gray-400 hover:text-white transition">
              <ForwardIcon className="h-5 w-5" />
            </button>
          </div>
          <div className="w-96 h-1 bg-zinc-800 rounded-full">
            <div className="w-1/3 h-full bg-white rounded-full"></div>
          </div>
        </div>

        {/* AI DJ Controls */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Tell AI DJ to change the vibe..."
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              className="w-64 px-4 py-2 rounded-full bg-zinc-800 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <button 
              className="absolute right-2 top-1/2 -translate-y-1/2 text-purple-500 hover:text-purple-400 transition"
            >
              <SparklesIcon className="h-5 w-5" />
            </button>
          </div>
          <button className="text-gray-400 hover:text-white transition">
            <SpeakerWaveIcon className="h-6 w-6" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Player; 
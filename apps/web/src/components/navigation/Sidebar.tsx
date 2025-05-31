'use client';

import React from 'react';
import { HomeIcon, MicrophoneIcon, SparklesIcon, HeartIcon } from '@heroicons/react/24/outline';

const Sidebar = () => {
  return (
    <div className="w-64 bg-zinc-900 p-6 flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <SparklesIcon className="h-8 w-8 text-purple-500" />
        <h1 className="text-xl font-bold">AI DJ</h1>
      </div>
      
      <nav className="space-y-4">
        <a href="#" className="flex items-center gap-3 text-gray-300 hover:text-white transition">
          <HomeIcon className="h-6 w-6" />
          <span>Home</span>
        </a>
        <a href="#" className="flex items-center gap-3 text-gray-300 hover:text-white transition">
          <MicrophoneIcon className="h-6 w-6" />
          <span>AI DJ Mode</span>
        </a>
        <a href="#" className="flex items-center gap-3 text-gray-300 hover:text-white transition">
          <HeartIcon className="h-6 w-6" />
          <span>Liked Songs</span>
        </a>
      </nav>

      <div className="mt-8">
        <h2 className="text-gray-400 text-sm font-semibold mb-4">SAVED VIBES</h2>
        <div className="space-y-2">
          <button className="w-full text-left py-2 px-4 rounded-lg hover:bg-zinc-800 transition">
            Chill Evening
          </button>
          <button className="w-full text-left py-2 px-4 rounded-lg hover:bg-zinc-800 transition">
            Workout Energy
          </button>
          <button className="w-full text-left py-2 px-4 rounded-lg hover:bg-zinc-800 transition">
            Focus Mode
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar; 
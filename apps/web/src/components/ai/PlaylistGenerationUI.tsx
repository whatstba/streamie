'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MusicalNoteIcon } from '@heroicons/react/24/outline';
import AnimatedStageText from './AnimatedStageText';

interface Track {
  title: string;
  artist: string;
  bpm?: number;
  artwork_url?: string;
  match_score?: number;
}

interface PlaylistGenerationUIProps {
  stage: 'idle' | 'analyzing_vibe' | 'searching_library' | 'matching_tracks' | 'optimizing_order' | 'finalizing' | 'complete';
  stageNumber: number;
  totalStages: number;
  progress: number;
  message: string;
  foundTracks: Track[];
  targetTrackCount: number;
  detectedMood?: {
    genres: string[];
    energy: number;
    mood: string;
  };
}

const stageLabels = {
  analyzing_vibe: 'Analyzing Your Vibe',
  searching_library: 'Searching Music Library',
  matching_tracks: 'Matching Tracks to Mood',
  optimizing_order: 'Optimizing Track Order',
  finalizing: 'Finalizing Playlist'
};

export default function PlaylistGenerationUI({
  stage,
  stageNumber,
  totalStages,
  progress,
  message,
  foundTracks,
  targetTrackCount,
  detectedMood
}: PlaylistGenerationUIProps) {
  const overallProgress = (stageNumber - 1 + progress) / totalStages;
  
  return (
    <motion.div 
      className="relative mt-6 p-8 rounded-2xl overflow-hidden"
      animate={{
        boxShadow: [
          '0 0 0 0 rgba(147, 51, 234, 0)',
          '0 0 50px 20px rgba(147, 51, 234, 0.1)',
          '0 0 30px 10px rgba(147, 51, 234, 0.05)',
          '0 0 0 0 rgba(147, 51, 234, 0)'
        ]
      }}
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    >
      {/* Animated background gradient */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-pink-900/20"
        animate={{
          opacity: [0.3, 0.6, 0.3],
          scale: [1, 1.1, 1]
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      <div className="relative space-y-6">
        {/* Progress Bar */}
        <div className="w-full">
          <div className="flex justify-between items-center mb-4">
            <AnimatedStageText 
              text={stageLabels[stage] || 'Processing'} 
              className="text-xl"
            />
            <motion.span 
              className="text-sm text-purple-400 font-mono"
              key={Math.round(overallProgress * 100)}
              initial={{ scale: 1.2, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              {Math.round(overallProgress * 100)}%
            </motion.span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
              initial={{ width: 0 }}
              animate={{ width: `${overallProgress * 100}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            />
          </div>
        </div>

        {/* Message Display */}
        <AnimatePresence mode="wait">
          <motion.div
            key={message}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-center text-gray-400 text-sm"
          >
            {message}
          </motion.div>
        </AnimatePresence>

        {/* Track Preview - Minimal */}
        {foundTracks.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-6"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-500">Finding tracks</span>
              <span className="text-sm text-purple-400">
                {foundTracks.length} / {targetTrackCount}
              </span>
            </div>
            <div className="space-y-2">
              {foundTracks.slice(-3).map((track, index) => (
                <motion.div
                  key={`${track.title}-${index}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-3 text-sm"
                >
                  <div className="w-8 h-8 bg-gray-800 rounded flex items-center justify-center">
                    <MusicalNoteIcon className="w-4 h-4 text-gray-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-white/80 truncate">{track.title}</div>
                    <div className="text-gray-500 text-xs truncate">{track.artist}</div>
                  </div>
                  {track.bpm && (
                    <div className="text-xs text-gray-600">
                      {track.bpm} BPM
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
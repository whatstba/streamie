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
  stage:
    | 'idle'
    | 'analyzing_vibe'
    | 'searching_library'
    | 'matching_tracks'
    | 'optimizing_order'
    | 'finalizing'
    | 'complete';
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

const stageLabels: Record<string, string> = {
  idle: 'Ready',
  analyzing_vibe: 'Analyzing Your Vibe',
  searching_library: 'Searching Music Library',
  matching_tracks: 'Matching Tracks to Mood',
  optimizing_order: 'Optimizing Track Order',
  finalizing: 'Finalizing Playlist',
  complete: 'Complete',
};

export default function PlaylistGenerationUI({
  stage,
  stageNumber,
  totalStages,
  progress,
  message,
  foundTracks,
  targetTrackCount,
  detectedMood,
}: PlaylistGenerationUIProps) {
  const overallProgress = (stageNumber - 1 + progress) / totalStages;

  return (
    <motion.div
      className="relative mt-6 p-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="relative space-y-6">
        {/* Progress Bar */}
        <div className="w-full">
          <div className="flex justify-center mb-6">
            <AnimatedStageText text={stageLabels[stage] || 'Processing'} className="text-xl" />
          </div>
          <motion.div
            className="h-3 bg-gray-800 rounded-full overflow-hidden shadow-lg"
            animate={{
              boxShadow: [
                '0 0 0 0 rgba(147, 51, 234, 0)',
                '0 0 20px 5px rgba(147, 51, 234, 0.3)',
                '0 0 10px 2px rgba(147, 51, 234, 0.1)',
                '0 0 0 0 rgba(147, 51, 234, 0)',
              ],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          >
            <motion.div
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
              initial={{ width: 0 }}
              animate={{ width: `${overallProgress * 100}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}

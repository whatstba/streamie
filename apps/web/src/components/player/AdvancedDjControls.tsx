'use client';

import React, { useState, useRef } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import BpmWaveformDisplay from '@/components/player/BpmWaveformDisplay';
import {
  MusicalNoteIcon,
  AdjustmentsHorizontalIcon,
  SpeakerWaveIcon,
  BoltIcon,
  ArrowsRightLeftIcon,
  SparklesIcon,
  ClockIcon,
  FireIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';

const AdvancedDjControls: React.FC = () => {
  const {
    currentTrack,
    nextTrack,
    bpmSyncEnabled,
    setBpmSync,
    hotCues,
    addHotCue,
    jumpToHotCue,
    currentEffects,
    beatAlignment,
    toggleBeatAlignment,
    pitchShift,
    setPitchShift,
    triggerScratch,
    triggerEcho,
    triggerFilter,
    sourceBpm,
    targetBpm,
    syncRatio,
    currentTime,
    djMode,
    applyTransitionEffect,
    transitionEffectPlan,
  } = useAudioPlayer();

  const [showEffects, setShowEffects] = useState(false);
  const [hotCueName, setHotCueName] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const pitchSliderRef = useRef<HTMLInputElement>(null);

  if (!djMode) {
    return null;
  }

  const handleAddHotCue = () => {
    if (currentTrack && hotCueName.trim()) {
      addHotCue(currentTrack.filepath, hotCueName, currentTime);
      setHotCueName('');
    }
  };

  const currentTrackCues = currentTrack ? hotCues[currentTrack.filepath] || [] : [];

  return (
    <div className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl border border-purple-500/30 overflow-hidden">
      {/* Header - Always visible */}
      <div
        className="flex items-center gap-3 p-6 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <FireIcon className="h-6 w-6 text-orange-500" />
        <h2 className="text-xl font-bold text-white">Advanced DJ Controls</h2>
        <div className="flex-1" />
        {currentEffects.length > 0 && (
          <div className="flex items-center gap-2">
            <BoltIcon className="h-5 w-5 text-yellow-400 animate-pulse" />
            <span className="text-sm text-yellow-400">{currentEffects.length} effects active</span>
          </div>
        )}
        {isExpanded ? (
          <ChevronUpIcon className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronDownIcon className="h-5 w-5 text-gray-400" />
        )}
      </div>

      {/* Collapsed view - Quick stats */}
      {!isExpanded && (
        <div className="px-6 pb-4 flex items-center gap-6 text-sm">
          {currentTrack && (
            <>
              <div className="flex items-center gap-2">
                <MusicalNoteIcon className="h-4 w-4 text-blue-400" />
                <span className="text-gray-300">
                  {sourceBpm?.toFixed(2) || '?'} BPM
                  {bpmSyncEnabled && syncRatio !== 1 && (
                    <span className="text-green-400 ml-1">(synced)</span>
                  )}
                </span>
              </div>
              {beatAlignment && (
                <div className="flex items-center gap-2">
                  <ClockIcon className="h-4 w-4 text-purple-400" />
                  <span className="text-purple-400">Beat aligned</span>
                </div>
              )}
              {currentTrackCues.length > 0 && (
                <div className="flex items-center gap-2">
                  <SparklesIcon className="h-4 w-4 text-yellow-400" />
                  <span className="text-gray-300">{currentTrackCues.length} hot cues</span>
                </div>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsExpanded(true);
                }}
                className="ml-auto px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded text-white text-xs font-medium transition"
              >
                Show Controls
              </button>
            </>
          )}
        </div>
      )}

      {/* Expanded view - Full controls */}
      {isExpanded && (
        <div className="p-6 pt-0">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* BPM Sync Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <MusicalNoteIcon className="h-5 w-5 text-blue-400" />
                BPM Sync
              </h3>

              <div className="bg-black/20 rounded-lg p-4 space-y-3 relative">
                {/* Coming Soon Overlay */}
                <div className="absolute inset-0 bg-black/60 rounded-lg flex items-center justify-center z-10">
                  <div className="text-center">
                    <span className="text-white font-semibold text-sm">Coming Soon</span>
                    <p className="text-gray-400 text-xs mt-1">BPM Sync features in development</p>
                  </div>
                </div>
                
                <div className="flex items-center justify-between opacity-50">
                  <span className="text-sm text-gray-300">Auto BPM Sync</span>
                  <button
                    disabled
                    className="px-3 py-1 rounded-full text-xs font-medium bg-gray-600 text-gray-300 cursor-not-allowed"
                  >
                    OFF
                  </button>
                </div>

                {currentTrack && (
                  <div className="text-sm space-y-1 opacity-50">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Current:</span>
                      <span className="text-white">{sourceBpm?.toFixed(2) || '?'} BPM</span>
                    </div>
                    {nextTrack && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Next:</span>
                        <span className="text-white">{targetBpm?.toFixed(2) || '?'} BPM</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-2 opacity-50">
                  <label className="text-sm text-gray-300 flex items-center gap-2">
                    <AdjustmentsHorizontalIcon className="h-4 w-4" />
                    Pitch Shift: 0 cents
                  </label>
                  <input
                    disabled
                    type="range"
                    min="-50"
                    max="50"
                    value={0}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-not-allowed slider"
                  />
                </div>

                <button
                  disabled
                  className="w-full px-3 py-2 rounded-lg text-sm font-medium bg-gray-600 text-gray-300 cursor-not-allowed"
                >
                  <ClockIcon className="h-4 w-4 inline mr-2" />
                  Beat Alignment OFF
                </button>
              </div>
            </div>

            {/* Hot Cues Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <SparklesIcon className="h-5 w-5 text-yellow-400" />
                Hot Cues
              </h3>

              <div className="bg-black/20 rounded-lg p-4 space-y-3 relative">
                {/* Coming Soon Overlay */}
                <div className="absolute inset-0 bg-black/60 rounded-lg flex items-center justify-center z-10">
                  <div className="text-center">
                    <span className="text-white font-semibold text-sm">Coming Soon</span>
                    <p className="text-gray-400 text-xs mt-1">Hot Cue features in development</p>
                  </div>
                </div>
                
                <div className="flex gap-2 opacity-50">
                  <input
                    disabled
                    type="text"
                    placeholder="Cue name..."
                    className="flex-1 px-3 py-2 bg-gray-800 rounded-lg text-white text-sm cursor-not-allowed"
                  />
                  <button
                    disabled
                    className="px-4 py-2 bg-gray-600 rounded-lg text-white text-sm font-medium cursor-not-allowed"
                  >
                    Add
                  </button>
                </div>

                <div className="space-y-2 max-h-40 overflow-y-auto opacity-50">
                  <p className="text-gray-400 text-sm text-center py-4">
                    No hot cues for this track
                  </p>
                </div>
              </div>
            </div>

            {/* Creative Effects Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <SpeakerWaveIcon className="h-5 w-5 text-green-400" />
                Creative Effects
              </h3>

              <div className="bg-black/20 rounded-lg p-4 space-y-3">
                <button
                  onClick={() => setShowEffects(!showEffects)}
                  className="w-full px-3 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white text-sm font-medium transition"
                >
                  <BoltIcon className="h-4 w-4 inline mr-2" />
                  {showEffects ? 'Hide' : 'Show'} Effect Panel
                </button>

                {showEffects && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => triggerFilter(0.8)}
                        className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-white text-sm font-medium transition"
                      >
                        🔊 Filter Sweep
                      </button>
                      <button
                        onClick={() => triggerEcho(0.6)}
                        className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition"
                      >
                        🔄 Echo
                      </button>
                      <button
                        onClick={() => triggerScratch(0.9)}
                        className="px-3 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-white text-sm font-medium transition"
                      >
                        🎛️ Scratch
                      </button>
                      <button
                        onClick={() => triggerFilter(0.3)}
                        className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white text-sm font-medium transition"
                      >
                        🎚️ Lo-Pass
                      </button>
                    </div>

                    {/* Transition Effect Plan Display */}
                    {transitionEffectPlan && (
                      <div className="border-t border-gray-700 pt-3">
                        <p className="text-xs text-gray-400 mb-2">Planned Transition Effects:</p>
                        <div className="bg-gray-800/50 rounded-lg p-3 space-y-2">
                          <div className="text-xs text-green-400">
                            Profile: {transitionEffectPlan.profile}
                          </div>
                          <div className="text-xs text-gray-300">
                            Curve: {transitionEffectPlan.crossfade_curve}
                          </div>
                          <div className="space-y-1">
                            {transitionEffectPlan.effects.map((effect, index) => (
                              <div
                                key={index}
                                className="text-xs text-yellow-400 flex items-center justify-between"
                              >
                                <span>
                                  {effect.type} ({(effect.intensity * 100).toFixed(0)}%)
                                </span>
                                <span className="text-gray-500">
                                  @{effect.start_at}s for {effect.duration}s
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {currentEffects.length > 0 && (
                  <div className="mt-3 space-y-1">
                    <p className="text-xs text-gray-400">Active Effects:</p>
                    {currentEffects.map((effect, index) => (
                      <div key={index} className="text-xs text-yellow-400 flex items-center gap-2">
                        <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                        {effect.type} ({(effect.intensity * 100).toFixed(0)}%)
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Track Info with BPM */}
          {currentTrack && (
            <div className="mt-6 p-4 bg-black/20 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-white font-medium">
                    {currentTrack.title || currentTrack.filename}
                  </h4>
                  <p className="text-gray-400 text-sm">{currentTrack.artist || 'Unknown Artist'}</p>
                </div>
                <div className="text-right">
                  <p className="text-white font-mono text-lg">{sourceBpm?.toFixed(2) || '?'} BPM</p>
                  {bpmSyncEnabled && syncRatio !== 1 && (
                    <p className="text-green-400 text-sm">
                      Synced to {(sourceBpm! * syncRatio).toFixed(2)} BPM
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Beat Grid Visualization */}
          {currentTrack && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <ArrowsRightLeftIcon className="h-5 w-5 text-blue-400" />
                Beat Grid
              </h3>
              <BpmWaveformDisplay />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdvancedDjControls;

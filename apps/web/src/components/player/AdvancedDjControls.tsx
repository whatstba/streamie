'use client';

import React, { useState, useRef } from 'react';
import { useAudioPlayer } from '@/context/AudioPlayerContext';
import {
  MusicalNoteIcon,
  AdjustmentsHorizontalIcon,
  SpeakerWaveIcon,
  BoltIcon,
  ArrowsRightLeftIcon,
  SparklesIcon,
  ClockIcon,
  FireIcon
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
    djMode
  } = useAudioPlayer();

  const [showEffects, setShowEffects] = useState(false);
  const [hotCueName, setHotCueName] = useState('');
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
    <div className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl p-6 border border-purple-500/30">
      <div className="flex items-center gap-3 mb-6">
        <FireIcon className="h-6 w-6 text-orange-500" />
        <h2 className="text-xl font-bold text-white">Advanced DJ Controls</h2>
        <div className="flex-1" />
        {currentEffects.length > 0 && (
          <div className="flex items-center gap-2">
            <BoltIcon className="h-5 w-5 text-yellow-400 animate-pulse" />
            <span className="text-sm text-yellow-400">{currentEffects.length} effects active</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* BPM Sync Section */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <MusicalNoteIcon className="h-5 w-5 text-blue-400" />
            BPM Sync
          </h3>
          
          <div className="bg-black/20 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Auto BPM Sync</span>
              <button
                onClick={() => setBpmSync(!bpmSyncEnabled)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                  bpmSyncEnabled 
                    ? 'bg-green-600 text-white' 
                    : 'bg-gray-600 text-gray-300'
                }`}
              >
                {bpmSyncEnabled ? 'ON' : 'OFF'}
              </button>
            </div>

            {currentTrack && (
              <div className="text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-gray-400">Current:</span>
                  <span className="text-white">{sourceBpm?.toFixed(1) || '?'} BPM</span>
                </div>
                {nextTrack && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Next:</span>
                    <span className="text-white">{targetBpm?.toFixed(1) || '?'} BPM</span>
                  </div>
                )}
                {bpmSyncEnabled && (
                  <div className="flex justify-between text-green-400">
                    <span>Sync Ratio:</span>
                    <span>{syncRatio.toFixed(3)}x</span>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm text-gray-300 flex items-center gap-2">
                <AdjustmentsHorizontalIcon className="h-4 w-4" />
                Pitch Shift: {pitchShift > 0 ? '+' : ''}{pitchShift} cents
              </label>
              <input
                ref={pitchSliderRef}
                type="range"
                min="-50"
                max="50"
                value={pitchShift}
                onChange={(e) => setPitchShift(Number(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
              />
            </div>

            <button
              onClick={toggleBeatAlignment}
              className={`w-full px-3 py-2 rounded-lg text-sm font-medium transition ${
                beatAlignment 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-600 text-gray-300'
              }`}
            >
              <ClockIcon className="h-4 w-4 inline mr-2" />
              Beat Alignment {beatAlignment ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>

        {/* Hot Cues Section */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <SparklesIcon className="h-5 w-5 text-yellow-400" />
            Hot Cues
          </h3>
          
          <div className="bg-black/20 rounded-lg p-4 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={hotCueName}
                onChange={(e) => setHotCueName(e.target.value)}
                placeholder="Cue name..."
                className="flex-1 px-3 py-2 bg-gray-800 rounded-lg text-white text-sm"
                onKeyPress={(e) => e.key === 'Enter' && handleAddHotCue()}
              />
              <button
                onClick={handleAddHotCue}
                disabled={!currentTrack || !hotCueName.trim()}
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 rounded-lg text-white text-sm font-medium transition"
              >
                Add
              </button>
            </div>

            <div className="space-y-2 max-h-40 overflow-y-auto">
              {currentTrackCues.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-4">
                  No hot cues for this track
                </p>
              ) : (
                currentTrackCues.map((cue) => (
                  <div
                    key={cue.id}
                    className="flex items-center justify-between p-2 bg-gray-800/50 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: cue.color }}
                      />
                      <span className="text-white text-sm font-medium">{cue.name}</span>
                      <span className="text-gray-400 text-xs">
                        {Math.floor(cue.time / 60)}:{(cue.time % 60).toFixed(0).padStart(2, '0')}
                      </span>
                    </div>
                    <button
                      onClick={() => jumpToHotCue(cue)}
                      className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-white text-xs transition"
                    >
                      Jump
                    </button>
                  </div>
                ))
              )}
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
              <p className="text-gray-400 text-sm">
                {currentTrack.artist || 'Unknown Artist'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-white font-mono text-lg">
                {sourceBpm?.toFixed(1) || '?'} BPM
              </p>
              {bpmSyncEnabled && syncRatio !== 1 && (
                <p className="text-green-400 text-sm">
                  Synced to {(sourceBpm! * syncRatio).toFixed(1)} BPM
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdvancedDjControls; 
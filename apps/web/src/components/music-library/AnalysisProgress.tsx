'use client';

import React from 'react';
import {
  MusicalNoteIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

interface AnalysisStatus {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total: number;
  workers: number;
  running: boolean;
}

interface TrackProgress {
  filepath: string;
  status: string;
  worker?: string;
  started_at?: string;
  error?: string;
}

interface AnalysisProgressProps {
  analysisStatus: AnalysisStatus;
  trackProgress: Record<string, TrackProgress>;
  className?: string;
  showDetails?: boolean;
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  analysisStatus,
  trackProgress,
  className = '',
  showDetails = true,
}) => {
  const { pending, processing, completed, failed, total, workers, running } = analysisStatus;

  const progressPercentage = total > 0 ? Math.round(((completed + failed) / total) * 100) : 0;
  const isComplete = total > 0 && completed + failed === total;

  const formatFilename = (filepath: string) => {
    return filepath.split('/').pop() || filepath;
  };

  return (
    <div className={`bg-zinc-800/50 rounded-xl p-4 border border-zinc-700 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <MusicalNoteIcon className="h-5 w-5 text-purple-400" />
          <h3 className="font-medium text-white">Track Analysis</h3>
        </div>

        {running && (
          <div className="flex items-center gap-2 text-sm text-green-400">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            {workers} workers active
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-400 mb-2">
          <span>{isComplete ? 'Analysis Complete' : 'Analyzing tracks...'}</span>
          <span>{progressPercentage}%</span>
        </div>

        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              isComplete ? 'bg-green-500' : 'bg-purple-500'
            }`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-zinc-900/50 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <CheckCircleIcon className="h-4 w-4 text-green-400" />
            <span className="text-xs text-gray-400">Completed</span>
          </div>
          <div className="text-lg font-semibold text-green-400">{completed}</div>
        </div>

        <div className="bg-zinc-900/50 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <ClockIcon className="h-4 w-4 text-blue-400" />
            <span className="text-xs text-gray-400">Processing</span>
          </div>
          <div className="text-lg font-semibold text-blue-400">{processing}</div>
        </div>

        <div className="bg-zinc-900/50 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <ClockIcon className="h-4 w-4 text-yellow-400" />
            <span className="text-xs text-gray-400">Pending</span>
          </div>
          <div className="text-lg font-semibold text-yellow-400">{pending}</div>
        </div>

        <div className="bg-zinc-900/50 rounded-lg p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <ExclamationCircleIcon className="h-4 w-4 text-red-400" />
            <span className="text-xs text-gray-400">Failed</span>
          </div>
          <div className="text-lg font-semibold text-red-400">{failed}</div>
        </div>
      </div>

      {/* Active Tracks */}
      {showDetails && Object.keys(trackProgress).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2 uppercase tracking-wide">
            Currently Processing
          </h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {Object.entries(trackProgress).map(([filepath, progress]) => (
              <div
                key={filepath}
                className="flex items-center justify-between p-2 bg-zinc-900/30 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white truncate" title={filepath}>
                    {formatFilename(filepath)}
                  </p>
                  {progress.worker && <p className="text-xs text-gray-500">{progress.worker}</p>}
                </div>

                <div className="flex items-center gap-2">
                  {progress.status === 'analyzing' && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  )}
                  {progress.status === 'completed' && (
                    <CheckCircleIcon className="h-4 w-4 text-green-400" />
                  )}
                  {progress.status === 'failed' && (
                    <ExclamationCircleIcon className="h-4 w-4 text-red-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Summary */}
      {failed > 0 && (
        <div className="mt-3 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
          <p className="text-sm text-red-400">
            {failed} track{failed !== 1 ? 's' : ''} failed analysis. These may be unsupported
            formats or corrupted files.
          </p>
        </div>
      )}
    </div>
  );
};

export default AnalysisProgress;

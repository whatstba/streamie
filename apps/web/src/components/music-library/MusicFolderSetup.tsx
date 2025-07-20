'use client';

import React, { useState, useEffect } from 'react';
import {
  SparklesIcon,
  FolderIcon,
  MusicalNoteIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import FolderPicker from './FolderPicker';
import AnalysisProgress from './AnalysisProgress';
import { musicLibraryService } from '@/services/musicLibraryService';

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

interface MusicFolderSetupProps {
  onComplete: () => void;
}

const MusicFolderSetup: React.FC<MusicFolderSetupProps> = ({ onComplete }) => {
  const [step, setStep] = useState<'welcome' | 'folder-select' | 'analyzing' | 'complete'>(
    'welcome'
  );
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string>('');
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    total: 0,
    workers: 0,
    running: false,
  });
  const [trackProgress, setTrackProgress] = useState<Record<string, TrackProgress>>({});
  const [webSocket, setWebSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    // Cleanup WebSocket on unmount
    return () => {
      if (webSocket) {
        webSocket.close();
      }
    };
  }, [webSocket]);

  const handleFolderSelect = async (folderPath: string) => {
    setSelectedFolder(folderPath);
    setIsAdding(true);
    setError('');

    try {
      // Add the folder to the backend
      const result = await musicLibraryService.addMusicFolder(folderPath, true);

      if (result.queued_tracks && result.queued_tracks > 0) {
        // Start monitoring analysis progress
        setStep('analyzing');
        startAnalysisMonitoring();
      } else {
        // No tracks found, but folder was added successfully
        setStep('complete');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add music folder');
      setIsAdding(false);
    }
  };

  const startAnalysisMonitoring = () => {
    // Connect to WebSocket for real-time updates
    const ws = musicLibraryService.connectAnalysisWebSocket(
      (data) => {
        if (data.type === 'queue_status') {
          setAnalysisStatus(data.data);

          // Check if analysis is complete
          const { pending, processing, total, completed, failed } = data.data;
          if (total > 0 && pending === 0 && processing === 0) {
            setTimeout(() => {
              setStep('complete');
            }, 1000);
          }
        } else if (data.type === 'track_progress') {
          setTrackProgress((prev) => ({
            ...prev,
            [data.filepath]: data.data,
          }));
        }
      },
      (error) => {
        console.error('WebSocket error:', error);
      },
      () => {
        console.log('WebSocket connection closed');
      }
    );

    setWebSocket(ws);
  };

  const handleComplete = async () => {
    try {
      await musicLibraryService.markFirstRunComplete();
      onComplete();
    } catch (err) {
      console.error('Failed to mark first run complete:', err);
      // Continue anyway
      onComplete();
    }
  };

  const handleRetry = () => {
    setStep('folder-select');
    setError('');
    setIsAdding(false);
    if (webSocket) {
      webSocket.close();
      setWebSocket(null);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        {/* Welcome Step */}
        {step === 'welcome' && (
          <div className="text-center">
            <div className="flex justify-center mb-6">
              <SparklesIcon className="h-16 w-16 text-purple-500" />
            </div>

            <h1 className="text-4xl font-bold text-white mb-4">Welcome to Jamz</h1>

            <p className="text-xl text-gray-400 mb-8 max-w-lg mx-auto">
              Your AI-powered DJ experience starts here. Let&apos;s set up your music library.
            </p>

            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="text-center p-4">
                <FolderIcon className="h-8 w-8 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-gray-300">Connect your music folder</p>
              </div>
              <div className="text-center p-4">
                <MusicalNoteIcon className="h-8 w-8 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-gray-300">Analyze your tracks</p>
              </div>
              <div className="text-center p-4">
                <SparklesIcon className="h-8 w-8 text-purple-400 mx-auto mb-2" />
                <p className="text-sm text-gray-300">Generate AI playlists</p>
              </div>
            </div>

            <button
              onClick={() => setStep('folder-select')}
              className="px-8 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
            >
              Get Started
            </button>
          </div>
        )}

        {/* Folder Selection Step */}
        {step === 'folder-select' && (
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white mb-4">Select Your Music Folder</h2>

            <p className="text-gray-400 mb-8 max-w-md mx-auto">
              Choose the folder where you keep your music files. We&apos;ll analyze them to enable
              smart DJ features.
            </p>

            <FolderPicker
              onFolderSelect={handleFolderSelect}
              disabled={isAdding}
              className="max-w-md mx-auto"
            />

            {error && (
              <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm max-w-md mx-auto">
                {error}
              </div>
            )}

            {selectedFolder && (
              <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg text-blue-400 text-sm max-w-md mx-auto">
                Selected: {selectedFolder}
              </div>
            )}

            <button
              onClick={() => setStep('welcome')}
              className="mt-6 text-gray-400 hover:text-white transition-colors"
            >
              ← Back
            </button>
          </div>
        )}

        {/* Analysis Step */}
        {step === 'analyzing' && (
          <div>
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-4">Analyzing Your Music</h2>

              <p className="text-gray-400 max-w-md mx-auto">
                We&apos;re analyzing your tracks to extract BPM, key signatures, and energy levels
                for intelligent mixing.
              </p>
            </div>

            <AnalysisProgress
              analysisStatus={analysisStatus}
              trackProgress={trackProgress}
              showDetails={true}
            />

            <div className="text-center mt-6">
              <button
                onClick={handleRetry}
                className="text-gray-400 hover:text-white transition-colors"
              >
                Cancel and try different folder
              </button>
            </div>
          </div>
        )}

        {/* Complete Step */}
        {step === 'complete' && (
          <div className="text-center">
            <div className="flex justify-center mb-6">
              <CheckCircleIcon className="h-16 w-16 text-green-500" />
            </div>

            <h2 className="text-2xl font-bold text-white mb-4">Setup Complete!</h2>

            <p className="text-gray-400 mb-8 max-w-md mx-auto">
              Your music library is ready. You can now generate AI playlists and use advanced DJ
              features.
            </p>

            <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700 mb-8 max-w-md mx-auto">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-lg font-semibold text-green-400">
                    {analysisStatus.completed}
                  </div>
                  <div className="text-gray-400">Tracks analyzed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-purple-400">1</div>
                  <div className="text-gray-400">Folder connected</div>
                </div>
              </div>
            </div>

            <button
              onClick={handleComplete}
              className="px-8 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
            >
              Start Using Jamz
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MusicFolderSetup;

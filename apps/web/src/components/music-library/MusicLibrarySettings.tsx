'use client';

import React, { useState, useEffect } from 'react';
import {
  PlusIcon,
  Cog6ToothIcon,
  ChartBarIcon,
  ArrowPathIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import Modal from '../ui/Modal';
import FolderPicker from './FolderPicker';
import FolderList from './FolderList';
import AnalysisProgress from './AnalysisProgress';
import { musicLibraryService } from '@/services/musicLibraryService';

interface MusicFolder {
  id: number;
  path: string;
  enabled: boolean;
  auto_scan: boolean;
  last_scan: string | null;
  created_at: string;
  exists: boolean;
  accessible: boolean;
}

interface LibraryStats {
  total_tracks: number;
  analyzed_tracks: number;
  pending_analysis: number;
  failed_analysis: number;
  active_folders: number;
  total_size_mb: number;
}

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

interface LibrarySettings {
  auto_analyze: string;
  watch_folders: string;
  [key: string]: string;
}

interface MusicLibrarySettingsProps {
  isOpen: boolean;
  onClose: () => void;
  onLibraryUpdate?: () => void;
}

const MusicLibrarySettings: React.FC<MusicLibrarySettingsProps> = ({
  isOpen,
  onClose,
  onLibraryUpdate,
}) => {
  const [activeTab, setActiveTab] = useState<'folders' | 'analysis' | 'settings'>('folders');
  const [folders, setFolders] = useState<MusicFolder[]>([]);
  const [stats, setStats] = useState<LibraryStats | null>(null);
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
  const [settings, setSettings] = useState<LibrarySettings>({
    auto_analyze: 'true',
    watch_folders: 'true',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isAddingFolder, setIsAddingFolder] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    setIsLoading(true);
    setError('');

    try {
      const [foldersData, statsData, analysisData, settingsData] = await Promise.all([
        musicLibraryService.getMusicFolders(),
        musicLibraryService.getLibraryStats(),
        musicLibraryService.getAnalysisStatus(),
        musicLibraryService.getSettings(),
      ]);

      setFolders(foldersData);
      setStats(statsData);
      setAnalysisStatus(analysisData);
      setSettings(settingsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load library data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddFolder = async (folderPath: string) => {
    setIsAddingFolder(true);
    setError('');

    try {
      await musicLibraryService.addMusicFolder(folderPath, settings.auto_analyze === 'true');
      await loadData();
      onLibraryUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add folder');
    } finally {
      setIsAddingFolder(false);
    }
  };

  const handleRemoveFolder = async (path: string) => {
    setError('');

    try {
      await musicLibraryService.removeMusicFolder(path);
      await loadData();
      onLibraryUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove folder');
    }
  };

  const handleScanFolder = async (folderId: number) => {
    setError('');

    try {
      await musicLibraryService.scanMusicFolder(folderId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to scan folder');
    }
  };

  const handleRetryFailed = async () => {
    setError('');

    try {
      await musicLibraryService.retryFailedAnalysis();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry analysis');
    }
  };

  const handleReprocessTracks = async (forceReanalyze: boolean, metadataOnly: boolean = false) => {
    setError('');
    setIsLoading(true);

    try {
      const result = await musicLibraryService.reprocessAllTracks(forceReanalyze, metadataOnly);
      await loadData();

      // You might want to show a success message using toast
      // For now, we'll just refresh the data
      console.log(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reprocess tracks');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFastMetadataScan = async () => {
    setError('');
    setIsLoading(true);

    try {
      const result = await musicLibraryService.fastMetadataScan();
      await loadData();
      console.log(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start metadata scan');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSettingChange = async (key: string, value: string) => {
    try {
      await musicLibraryService.updateSettings({ [key]: value });
      setSettings((prev) => ({ ...prev, [key]: value }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    }
  };

  const tabs = [
    { id: 'folders', label: 'Music Folders', icon: PlusIcon },
    { id: 'analysis', label: 'Analysis', icon: ChartBarIcon },
    { id: 'settings', label: 'Settings', icon: Cog6ToothIcon },
  ] as const;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Music Library Settings" size="lg">
      <div className="flex border-b border-zinc-700">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-3 font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-purple-400 border-b-2 border-purple-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center gap-2">
            <ExclamationCircleIcon className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Library Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-semibold text-white">{stats.total_tracks}</div>
              <div className="text-xs text-gray-400">Total Tracks</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-semibold text-green-400">{stats.analyzed_tracks}</div>
              <div className="text-xs text-gray-400">Analyzed</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-semibold text-purple-400">{stats.active_folders}</div>
              <div className="text-xs text-gray-400">Folders</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-semibold text-blue-400">
                {stats.total_size_mb.toFixed(1)}MB
              </div>
              <div className="text-xs text-gray-400">Library Size</div>
            </div>
          </div>
        )}

        {/* Folders Tab */}
        {activeTab === 'folders' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Add Music Folder</h3>
              <FolderPicker
                onFolderSelect={handleAddFolder}
                disabled={isAddingFolder || isLoading}
              />
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Connected Folders</h3>
              <FolderList
                folders={folders}
                onRemoveFolder={handleRemoveFolder}
                onScanFolder={handleScanFolder}
                isLoading={isLoading}
              />
            </div>
          </div>
        )}

        {/* Analysis Tab */}
        {activeTab === 'analysis' && (
          <div className="space-y-6">
            <AnalysisProgress
              analysisStatus={analysisStatus}
              trackProgress={trackProgress}
              showDetails={true}
            />

            {analysisStatus.failed > 0 && (
              <div className="flex items-center justify-between p-4 bg-red-900/20 border border-red-500/30 rounded-lg">
                <div>
                  <p className="text-red-400 font-medium">Failed Analyses</p>
                  <p className="text-sm text-gray-400">
                    {analysisStatus.failed} tracks failed to analyze
                  </p>
                </div>
                <button
                  onClick={handleRetryFailed}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  <ArrowPathIcon className="h-4 w-4" />
                  Retry Failed
                </button>
              </div>
            )}

            {/* Reprocess Controls */}
            <div className="space-y-4">
              {/* Fast Metadata Scan */}
              <div className="p-4 bg-green-900/20 border border-green-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-green-400 font-medium">Fast Metadata Scan</p>
                    <p className="text-sm text-gray-400">
                      Quickly scan tracks for missing basic metadata (title, artist, album, BPM)
                      without full audio analysis
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleFastMetadataScan}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
                >
                  <ArrowPathIcon className="h-4 w-4" />
                  Fast Metadata Scan
                </button>
              </div>

              {/* Enhanced Analysis */}
              <div className="p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-blue-400 font-medium">Enhanced Analysis</p>
                    <p className="text-sm text-gray-400">
                      Full audio analysis including key detection, structure analysis, and energy
                      profiling
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleReprocessTracks(false, false)}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
                  >
                    <ArrowPathIcon className="h-4 w-4" />
                    Analyze Unprocessed
                  </button>
                  <button
                    onClick={() => handleReprocessTracks(true, false)}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
                  >
                    <ArrowPathIcon className="h-4 w-4" />
                    Force Reanalyze All
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg">
                <div>
                  <p className="font-medium text-white">Auto-analyze new tracks</p>
                  <p className="text-sm text-gray-400">
                    Automatically analyze tracks when they&apos;re added
                  </p>
                </div>
                <button
                  onClick={() =>
                    handleSettingChange(
                      'auto_analyze',
                      settings.auto_analyze === 'true' ? 'false' : 'true'
                    )
                  }
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    settings.auto_analyze === 'true'
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-600 text-gray-300'
                  }`}
                >
                  {settings.auto_analyze === 'true' ? 'Enabled' : 'Disabled'}
                </button>
              </div>

              <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg">
                <div>
                  <p className="font-medium text-white">Watch folders</p>
                  <p className="text-sm text-gray-400">Monitor folders for new music files</p>
                </div>
                <button
                  onClick={() =>
                    handleSettingChange(
                      'watch_folders',
                      settings.watch_folders === 'true' ? 'false' : 'true'
                    )
                  }
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    settings.watch_folders === 'true'
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-600 text-gray-300'
                  }`}
                >
                  {settings.watch_folders === 'true' ? 'Enabled' : 'Disabled'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default MusicLibrarySettings;

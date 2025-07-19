'use client';

import React, { useState } from 'react';
import {
  FolderIcon,
  TrashIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

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

interface FolderListProps {
  folders: MusicFolder[];
  onRemoveFolder: (path: string) => void;
  onScanFolder: (folderId: number) => void;
  isLoading?: boolean;
}

const FolderList: React.FC<FolderListProps> = ({
  folders,
  onRemoveFolder,
  onScanFolder,
  isLoading = false,
}) => {
  const [scanningFolders, setScanningFolders] = useState<Set<number>>(new Set());
  const [removingFolders, setRemovingFolders] = useState<Set<string>>(new Set());

  const handleScanFolder = async (folderId: number) => {
    setScanningFolders((prev) => new Set(prev).add(folderId));
    try {
      await onScanFolder(folderId);
    } finally {
      setScanningFolders((prev) => {
        const newSet = new Set(prev);
        newSet.delete(folderId);
        return newSet;
      });
    }
  };

  const handleRemoveFolder = async (path: string) => {
    if (
      !confirm(
        'Are you sure you want to remove this folder? This will not delete your music files.'
      )
    ) {
      return;
    }

    setRemovingFolders((prev) => new Set(prev).add(path));
    try {
      await onRemoveFolder(path);
    } finally {
      setRemovingFolders((prev) => {
        const newSet = new Set(prev);
        newSet.delete(path);
        return newSet;
      });
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getFolderStatus = (folder: MusicFolder) => {
    if (!folder.exists) {
      return { icon: XCircleIcon, text: 'Folder not found', color: 'text-red-400' };
    }
    if (!folder.accessible) {
      return { icon: ExclamationTriangleIcon, text: 'No access', color: 'text-yellow-400' };
    }
    if (!folder.enabled) {
      return { icon: XCircleIcon, text: 'Disabled', color: 'text-gray-400' };
    }
    return { icon: CheckCircleIcon, text: 'Active', color: 'text-green-400' };
  };

  if (folders.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <FolderIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>No music folders connected</p>
        <p className="text-sm mt-1">Add a folder to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {folders.map((folder) => {
        const status = getFolderStatus(folder);
        const isScanning = scanningFolders.has(folder.id);
        const isRemoving = removingFolders.has(folder.path);
        const StatusIcon = status.icon;

        return (
          <div
            key={folder.id}
            className={`p-4 rounded-lg border transition-all ${
              folder.exists && folder.accessible
                ? 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                : 'bg-red-900/10 border-red-500/30'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <FolderIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <span className="font-medium text-white truncate" title={folder.path}>
                    {folder.path}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <div className="flex items-center gap-1">
                    <StatusIcon className={`h-4 w-4 ${status.color}`} />
                    <span className={status.color}>{status.text}</span>
                  </div>

                  <div>Last scan: {formatDate(folder.last_scan)}</div>

                  {folder.auto_scan && (
                    <div className="text-xs bg-blue-900/30 text-blue-400 px-2 py-1 rounded">
                      Auto-scan
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 ml-4">
                {folder.exists && folder.accessible && (
                  <button
                    onClick={() => handleScanFolder(folder.id)}
                    disabled={isScanning || isLoading}
                    className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-zinc-700 transition-colors disabled:opacity-50"
                    title="Scan for new tracks"
                  >
                    <ArrowPathIcon className={`h-4 w-4 ${isScanning ? 'animate-spin' : ''}`} />
                  </button>
                )}

                <button
                  onClick={() => handleRemoveFolder(folder.path)}
                  disabled={isRemoving || isLoading}
                  className="p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-900/20 transition-colors disabled:opacity-50"
                  title="Remove folder"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>

            {!folder.exists && (
              <div className="mt-3 p-2 bg-red-900/20 border border-red-500/30 rounded text-sm text-red-400">
                This folder no longer exists. You may want to remove it from your library.
              </div>
            )}

            {folder.exists && !folder.accessible && (
              <div className="mt-3 p-2 bg-yellow-900/20 border border-yellow-500/30 rounded text-sm text-yellow-400">
                Cannot access this folder. Please check permissions.
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default FolderList;

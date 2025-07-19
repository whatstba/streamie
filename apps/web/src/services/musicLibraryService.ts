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

interface LibrarySettings {
  auto_analyze: string;
  watch_folders: string;
  [key: string]: string;
}

const API_BASE_URL = 'http://localhost:8000';

export const musicLibraryService = {
  async getMusicFolders(): Promise<MusicFolder[]> {
    const response = await fetch(`${API_BASE_URL}/api/library/folders`);
    if (!response.ok) {
      throw new Error('Failed to fetch music folders');
    }
    const data = await response.json();
    return data.folders;
  },

  async addMusicFolder(
    path: string,
    autoScan: boolean = true
  ): Promise<MusicFolder & { queued_tracks?: number }> {
    const response = await fetch(`${API_BASE_URL}/api/library/folders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ path, auto_scan: autoScan }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add music folder');
    }

    return response.json();
  },

  async removeMusicFolder(path: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/api/library/folders/${encodeURIComponent(path)}`,
      {
        method: 'DELETE',
      }
    );

    if (!response.ok) {
      throw new Error('Failed to remove music folder');
    }
  },

  async scanMusicFolder(
    folderId: number,
    fullScan: boolean = false
  ): Promise<{ folder: string; new_tracks: number; queued: number }> {
    const response = await fetch(`${API_BASE_URL}/api/library/scan/${folderId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ full_scan: fullScan }),
    });

    if (!response.ok) {
      throw new Error('Failed to scan music folder');
    }

    return response.json();
  },

  async getLibraryStats(): Promise<LibraryStats> {
    const response = await fetch(`${API_BASE_URL}/api/library/stats`);
    if (!response.ok) {
      throw new Error('Failed to fetch library stats');
    }
    return response.json();
  },

  async getAnalysisStatus(): Promise<AnalysisStatus> {
    const response = await fetch(`${API_BASE_URL}/api/library/analysis/status`);
    if (!response.ok) {
      throw new Error('Failed to fetch analysis status');
    }
    return response.json();
  },

  async getSettings(): Promise<LibrarySettings> {
    const response = await fetch(`${API_BASE_URL}/api/library/settings`);
    if (!response.ok) {
      throw new Error('Failed to fetch library settings');
    }
    return response.json();
  },

  async updateSettings(settings: Partial<LibrarySettings>): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/library/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });

    if (!response.ok) {
      throw new Error('Failed to update settings');
    }
  },

  async markFirstRunComplete(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/library/first-run-complete`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to mark first run complete');
    }
  },

  async reprocessAllTracks(
    forceReanalyze: boolean = false,
    metadataOnly: boolean = false
  ): Promise<{ status: string; queued_tracks: number; message: string }> {
    const response = await fetch(
      `${API_BASE_URL}/api/library/analysis/reprocess-all?force_reanalyze=${forceReanalyze}&metadata_only=${metadataOnly}`,
      {
        method: 'POST',
      }
    );
    if (!response.ok) {
      throw new Error('Failed to reprocess tracks');
    }
    return response.json();
  },

  async fastMetadataScan(): Promise<{ status: string; message: string; tracks_to_scan?: number }> {
    const response = await fetch(`${API_BASE_URL}/api/library/analysis/metadata-scan`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to start metadata scan');
    }
    return response.json();
  },

  async retryFailedAnalysis(maxRetries: number = 3): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/api/library/analysis/retry-failed?max_retries=${maxRetries}`,
      {
        method: 'POST',
      }
    );

    if (!response.ok) {
      throw new Error('Failed to retry failed analysis');
    }
  },

  // WebSocket connection for real-time analysis progress
  connectAnalysisWebSocket(
    onMessage: (data: any) => void,
    onError?: (error: Event) => void,
    onClose?: () => void
  ): WebSocket {
    const ws = new WebSocket(`ws://localhost:8000/ws/analysis-progress`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    ws.onerror = onError || (() => {});
    ws.onclose = onClose || (() => {});

    return ws;
  },
};

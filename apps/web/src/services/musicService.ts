interface TrackInfo {
  filename: string;
  filepath: string;
  duration: number;
  title: string | null;
  artist: string | null;
  album: string | null;
  genre: string | null;
  year: string | null;
  has_artwork: boolean;
  bpm?: number;
}

interface SeratoHotCue {
  name: string;
  time: number;
  color: string;
  type: 'cue' | 'loop' | 'phrase';
  index: number;
}

interface TrackAnalysis {
  bpm: number;
  success: boolean;
  confidence?: number;
  analysis_time?: string;
  suggested_transitions?: {
    filter_sweep?: boolean;
    echo_effect?: boolean;
    scratch_compatible?: boolean;
    has_serato_cues?: boolean;
    loop_ready?: boolean;
  };
  serato_data?: {
    hot_cues: SeratoHotCue[];
    bpm?: number;
    key?: string;
    energy?: number;
    beatgrid?: any;
    serato_available: boolean;
  };
  hot_cues?: SeratoHotCue[];
}

const API_BASE_URL = 'http://localhost:8000';

export const musicService = {
  async listTracks(): Promise<TrackInfo[]> {
    const response = await fetch(`${API_BASE_URL}/tracks`);
    if (!response.ok) {
      throw new Error('Failed to fetch tracks');
    }
    return response.json();
  },

  async getTrackAnalysis(filepath: string): Promise<TrackAnalysis> {
    const response = await fetch(`${API_BASE_URL}/track/${encodeURIComponent(filepath)}/analysis`);
    if (!response.ok) {
      throw new Error('Failed to analyze track');
    }
    return response.json();
  },

  async getSeratoData(filepath: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/track/${encodeURIComponent(filepath)}/serato`);
    if (!response.ok) {
      throw new Error('Failed to fetch Serato data');
    }
    return response.json();
  },

  async getTrackWithBpm(filepath: string): Promise<TrackInfo & { bpm: number }> {
    try {
      const [trackResponse, analysisResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/track/${encodeURIComponent(filepath)}`),
        fetch(`${API_BASE_URL}/track/${encodeURIComponent(filepath)}/analysis`),
      ]);

      if (!trackResponse.ok || !analysisResponse.ok) {
        throw new Error('Failed to fetch track or analysis');
      }

      const track = await trackResponse.json();
      const analysis = await analysisResponse.json();

      return {
        ...track,
        bpm: analysis.bpm,
      };
    } catch (error) {
      console.error('Error fetching track with BPM:', error);
      throw error;
    }
  },

  async enrichTracksWithBpm(tracks: TrackInfo[]): Promise<TrackInfo[]> {
    const enrichedTracks = await Promise.allSettled(
      tracks.map(async (track) => {
        try {
          const analysis = await this.getTrackAnalysis(track.filepath);
          return { ...track, bpm: analysis.bpm };
        } catch (error) {
          console.warn(`Failed to get BPM for ${track.filename}:`, error);
          return track;
        }
      })
    );

    return enrichedTracks.map((result, index) =>
      result.status === 'fulfilled' ? result.value : tracks[index]
    );
  },

  getArtworkUrl(filepath: string): string {
    return `${API_BASE_URL}/track/${encodeURIComponent(filepath)}/artwork`;
  },

  getStreamUrl(filepath: string): string {
    return `${API_BASE_URL}/track/${encodeURIComponent(filepath)}/stream`;
  },

  getDJSetStreamUrl(setId?: string): string {
    // CRITICAL: Pre-rendered streaming is REQUIRED - no fallbacks allowed
    if (!setId) {
      const errorMsg = 'CRITICAL ERROR: DJ set ID is required for streaming. Pre-rendering may have failed!';
      console.error(errorMsg);
      throw new Error(errorMsg);
    }
    
    // Use pre-rendered streaming endpoint - this is the ONLY valid path
    const url = `${API_BASE_URL}/api/audio/stream/prerendered/${encodeURIComponent(setId)}`;
    console.log('Using pre-rendered stream URL:', url);
    return url;
  },
  
  getDJSetChunkedStreamUrl(setId: string): string {
    // Chunked streaming endpoint for reliable playback
    return `${API_BASE_URL}/api/audio/stream/chunked/${encodeURIComponent(setId)}`;
  },
  
  
  getDJSetFileUrl(setId: string): string {
    // Pre-rendered file endpoint
    return `${API_BASE_URL}/api/audio/stream/file/${encodeURIComponent(setId)}`;
  },
  
  async checkStreamStatus(setId: string): Promise<{
    is_rendered: boolean;
    render_progress_seconds: number;
    file_ready: boolean;
    file_url: string | null;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/audio/stream/status/${encodeURIComponent(setId)}`);
    if (!response.ok) {
      throw new Error('Failed to check stream status');
    }
    return response.json();
  },
  
  getTestSineWaveUrl(): string {
    // Test sine wave endpoint
    return `${API_BASE_URL}/api/audio/test-sine-wave`;
  },
};

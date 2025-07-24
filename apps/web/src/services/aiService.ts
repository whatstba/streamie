interface VibeAnalysisRequest {
  current_track_id: string;
  context?: Record<string, any>;
}

interface PlaylistGenerationRequest {
  seed_track_id: string;
  playlist_length?: number;
  energy_pattern?: 'build_up' | 'peak_time' | 'cool_down' | 'wave';
  context?: Record<string, any>;
}

interface NextTrackRequest {
  current_track_id: string;
  played_tracks?: string[];
  desired_vibe?: string;
  context?: Record<string, any>;
}

interface TransitionRatingRequest {
  from_track_id: string;
  to_track_id: string;
  rating: number; // 0-1
  notes?: string;
}

interface VibeAnalysisResponse {
  track_id: string;
  bpm: number;
  energy_level: number;
  dominant_vibe: string;
  mood_vector: Record<string, number>;
  genre: string;
  recommendations: string[];
}

interface TrackSuggestion {
  track: Record<string, any>;
  confidence: number;
  transition?: Record<string, any>;
  reasoning?: string;
}

interface PlaylistResponse {
  playlist: Record<string, any>[];
  transitions: Record<string, any>[];
  energy_flow: number[];
  vibe_analysis: Record<string, any>;
}

interface MixingInsights {
  top_transitions: Array<{
    _id: { from: string; to: string };
    avg_rating: number;
    count: number;
  }>;
  most_mixed_tracks: Array<{
    filepath: string;
    title?: string;
    artist?: string;
    mix_count: number;
  }>;
  total_ratings: number;
}

// DJ Set interfaces
interface DJSetGenerateRequest {
  vibe_description: string;
  duration_minutes?: number;
  energy_pattern?: 'steady' | 'building' | 'cooling' | 'wave';
  name?: string;
}

interface DJSetTrack {
  order: number;
  filepath: string;
  title: string;
  artist: string;
  album?: string;
  genre?: string;
  bpm: number;
  key?: string;
  energy_level: number;
  start_time: number;
  end_time: number;
  deck: string;
  gain_adjust: number;
  tempo_adjust: number;
  eq_low: number;
  eq_mid: number;
  eq_high: number;
}

interface DJSetTransition {
  from_track_order: number;
  to_track_order: number;
  start_time: number;
  duration: number;
  type: 'smooth' | 'cut' | 'scratch' | 'echo';
  effects: Array<{
    type: string;
    start_at: number;
    duration: number;
    intensity: number;
  }>;
}

interface DJSet {
  id: string;
  name: string;
  created_at: string;
  vibe_description: string;
  energy_pattern: string;
  track_count: number;
  total_duration: number;
  tracks: DJSetTrack[];
  transitions: DJSetTransition[];
}

interface DJSetGenerateResponse {
  set_id: string;
  name: string;
  track_count: number;
  total_duration: number;
  tracks: any[];
  transitions: any[];
}

interface DJSetPlaybackStatus {
  is_playing: boolean;
  is_paused?: boolean;
  set_id?: string;
  set_name?: string;
  current_track_order?: number;
  total_tracks?: number;
  elapsed_time?: number;
  total_duration?: number;
  primary_deck?: string;
  active_decks?: string[];
  in_transition?: boolean;
  transition_progress?: number;
  next_transition_in?: number;
  message?: string;
}

const AI_API_BASE_URL = 'http://localhost:8000/ai';
const API_BASE_URL = 'http://localhost:8000';

// Export types for use in components
export type {
  DJSetGenerateRequest,
  DJSetTrack,
  DJSetTransition,
  DJSet,
  DJSetGenerateResponse,
  DJSetPlaybackStatus,
};

export const aiService = {
  /**
   * Analyze the vibe of a track and get AI recommendations
   */
  async analyzeVibe(request: VibeAnalysisRequest): Promise<VibeAnalysisResponse> {
    const response = await fetch(`${AI_API_BASE_URL}/analyze-vibe`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to analyze vibe: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Generate an intelligent playlist using AI
   */
  async generatePlaylist(request: PlaylistGenerationRequest): Promise<PlaylistResponse> {
    const response = await fetch(`${AI_API_BASE_URL}/generate-playlist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        playlist_length: 10,
        energy_pattern: 'wave',
        ...request,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to generate playlist: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Get AI suggestion for the next track
   */
  async suggestNextTrack(request: NextTrackRequest): Promise<TrackSuggestion> {
    const response = await fetch(`${AI_API_BASE_URL}/suggest-next-track`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to get track suggestion: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Rate a transition to improve future AI suggestions
   */
  async rateTransition(
    request: TransitionRatingRequest
  ): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${AI_API_BASE_URL}/rate-transition`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to rate transition: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Get mixing insights and patterns from AI learning
   */
  async getMixingInsights(): Promise<MixingInsights> {
    const response = await fetch(`${AI_API_BASE_URL}/mixing-insights`);

    if (!response.ok) {
      throw new Error(`Failed to get mixing insights: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Generate a DJ set with pre-planned transitions
   */
  async generateDJSet(request: DJSetGenerateRequest, signal?: AbortSignal): Promise<{ success: boolean; dj_set?: DJSet; error?: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dj-set/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          duration_minutes: 30,
          energy_pattern: 'wave',
          ...request,
        }),
        signal,
      });

      if (!response.ok) {
        const error = await response.text();
        return { success: false, error: `Failed to generate DJ set: ${error}` };
      }

      const data: DJSetGenerateResponse = await response.json();
      
      // Transform the response into DJSet format
      const djSet: DJSet = {
        id: data.set_id,
        name: data.name,
        created_at: new Date().toISOString(),
        vibe_description: request.vibe_description,
        energy_pattern: request.energy_pattern || 'wave',
        track_count: data.track_count,
        total_duration: data.total_duration,
        tracks: data.tracks,
        transitions: data.transitions,
      };

      return { success: true, dj_set: djSet };
    } catch (error) {
      // Re-throw AbortError so it can be handled by the caller
      if (error instanceof Error && error.name === 'AbortError') {
        throw error;
      }
      
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  },

  /**
   * Play an existing DJ set by ID
   */
  async playDJSet(setId: string): Promise<{
    status: string;
    set_id: string;
    session_id?: string;
    name?: string;
    track_count?: number;
    total_duration?: number;
    message?: string;
    error?: string;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dj-set/${setId}/play`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const error = await response.text();
        return { status: 'error', set_id: setId, error: `Failed to play DJ set: ${error}` };
      }

      return await response.json();
    } catch (error) {
      return { status: 'error', set_id: setId, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  },

  /**
   * Generate and immediately play a DJ set
   */
  async playDJSetImmediately(request: DJSetGenerateRequest): Promise<{
    success: boolean;
    set_id?: string;
    audio_url?: string;
    message?: string;
    error?: string;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dj-set/play-immediately`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          duration_minutes: 30,
          energy_pattern: 'wave',
          ...request,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        return { success: false, error: `Failed to play DJ set: ${error}` };
      }

      const data = await response.json();
      
      // Backend returns {status: "playing", ...}, wrap it with success field
      if (data.status === 'playing') {
        return {
          success: true,
          set_id: data.set_id,
          audio_url: `/api/audio/stream/prerendered/${data.set_id}`,
          message: data.message,
        };
      } else {
        return { success: false, error: 'Unexpected response from server' };
      }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  },

  /**
   * Get DJ set playback status
   */
  async getDJSetPlaybackStatus(): Promise<DJSetPlaybackStatus> {
    const response = await fetch(`${API_BASE_URL}/api/dj-set/playback/status`);

    if (!response.ok) {
      throw new Error(`Failed to get playback status: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Stop DJ set playback
   */
  async stopDJSetPlayback(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/dj-set/playback/stop`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to stop playback: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Pause DJ set playback
   */
  async pauseDJSetPlayback(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/dj-set/playback/pause`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to pause playback: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Resume DJ set playback
   */
  async resumeDJSetPlayback(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/dj-set/playback/resume`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to resume playback: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Play single track or queue directly without AI generation
   */
  async playTracksDirectly(tracks: any[]): Promise<{
    status: string;
    set_id?: string;
    session_id?: string;
    track_count?: number;
    total_duration?: number;
    message?: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/track/play`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tracks }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to play tracks: ${error}`);
    }

    return response.json();
  },
};

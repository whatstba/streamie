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

const AI_API_BASE_URL = 'http://localhost:8000/ai';

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
};

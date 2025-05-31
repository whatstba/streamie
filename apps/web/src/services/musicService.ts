interface TrackInfo {
  filename: string;
  duration: number;
  title: string | null;
  artist: string | null;
}

interface TrackAnalysis {
  beat_times: number[];
  success: boolean;
}

interface WaveformData {
  waveform: number[];
  sample_rate: number;
  hop_length: number;
}

const API_BASE_URL = 'http://localhost:8001';

export const musicService = {
  async listTracks(): Promise<TrackInfo[]> {
    const response = await fetch(`${API_BASE_URL}/tracks`);
    if (!response.ok) {
      throw new Error('Failed to fetch tracks');
    }
    return response.json();
  },

  async getTrackAnalysis(filename: string): Promise<TrackAnalysis> {
    const response = await fetch(`${API_BASE_URL}/track/${encodeURIComponent(filename)}/analysis`);
    if (!response.ok) {
      throw new Error('Failed to analyze track');
    }
    return response.json();
  },

  async getWaveform(filename: string): Promise<WaveformData> {
    const response = await fetch(`${API_BASE_URL}/track/${encodeURIComponent(filename)}/waveform`);
    if (!response.ok) {
      throw new Error('Failed to fetch waveform');
    }
    return response.json();
  }
}; 
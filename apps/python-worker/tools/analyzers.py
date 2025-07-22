"""Track analysis tools using librosa"""

import librosa
import numpy as np
import json
from typing import Dict, List, Tuple, Optional
import soundfile as sf
import logging

logger = logging.getLogger(__name__)


class TrackAnalyzer:
    """Analyzes audio tracks for DJ-relevant features"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    async def analyze_track(self, filepath: str) -> Dict:
        """Comprehensive track analysis"""
        try:
            # Load audio with librosa
            y, sr = librosa.load(filepath, sr=self.sample_rate, mono=False)

            # Convert to mono for analysis if stereo
            if y.ndim > 1:
                y_mono = librosa.to_mono(y)
            else:
                y_mono = y

            # Get file info
            info = sf.info(filepath)
            duration = info.duration

            # Run all analyses
            bpm_data = self._analyze_bpm(y_mono, sr)
            key_data = self._analyze_key(y_mono, sr)
            energy_data = self._analyze_energy(y_mono, sr)

            return {
                "filepath": filepath,
                "duration": duration,
                "sample_rate": sr,
                "channels": info.channels,
                **bpm_data,
                **key_data,
                **energy_data,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Error analyzing track {filepath}: {e}")
            return {"filepath": filepath, "analyzed": False, "error": str(e)}

    def _analyze_bpm(self, y: np.ndarray, sr: int) -> Dict:
        """Detect BPM and beat positions"""
        # Get tempo and beat frames
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        # Convert beat frames to time
        beat_times = librosa.frames_to_time(beats, sr=sr)

        # Calculate tempo stability
        if len(beats) > 1:
            beat_intervals = np.diff(beat_times)
            tempo_stability = 1.0 - (np.std(beat_intervals) / np.mean(beat_intervals))
        else:
            tempo_stability = 0.0

        # Get more detailed tempo analysis
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        pulse = librosa.beat.plp(onset_envelope=onset_env, sr=sr)

        return {
            "bpm": float(tempo),
            "beat_times": beat_times.tolist(),
            "beat_count": len(beats),
            "tempo_stability": float(tempo_stability),
            "first_beat": float(beat_times[0]) if len(beat_times) > 0 else 0.0,
            "pulse_strength": float(np.mean(pulse)),
        }

    def _analyze_key(self, y: np.ndarray, sr: int) -> Dict:
        """Detect musical key using chroma features"""
        # Compute chroma features
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

        # Average chroma across time
        chroma_mean = np.mean(chroma, axis=1)

        # Key profiles for major and minor keys (Krumhansl-Kessler)
        major_profile = np.array(
            [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        )
        minor_profile = np.array(
            [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        )

        # Compute correlation with each key
        key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        correlations = []

        for shift in range(12):
            # Rotate chroma to match key
            rotated_chroma = np.roll(chroma_mean, shift)

            # Correlate with major and minor profiles
            major_corr = np.corrcoef(rotated_chroma, major_profile)[0, 1]
            minor_corr = np.corrcoef(rotated_chroma, minor_profile)[0, 1]

            correlations.append(
                {
                    "key": key_names[shift],
                    "major_corr": major_corr,
                    "minor_corr": minor_corr,
                    "is_major": major_corr > minor_corr,
                    "confidence": max(major_corr, minor_corr),
                }
            )

        # Find best matching key
        best_key = max(correlations, key=lambda x: x["confidence"])
        key_str = f"{best_key['key']}{'maj' if best_key['is_major'] else 'min'}"

        # Convert to Camelot notation for harmonic mixing
        camelot_wheel = {
            "Cmaj": "8B",
            "Amin": "8A",
            "Gmaj": "9B",
            "Emin": "9A",
            "Dmaj": "10B",
            "Bmin": "10A",
            "Amaj": "11B",
            "F#min": "11A",
            "Emaj": "12B",
            "C#min": "12A",
            "Bmaj": "1B",
            "G#min": "1A",
            "F#maj": "2B",
            "D#min": "2A",
            "C#maj": "3B",
            "A#min": "3A",
            "G#maj": "4B",
            "Fmin": "4A",
            "D#maj": "5B",
            "Cmin": "5A",
            "A#maj": "6B",
            "Gmin": "6A",
            "Fmaj": "7B",
            "Dmin": "7A",
        }

        camelot_key = camelot_wheel.get(key_str, "Unknown")

        return {
            "key": key_str,
            "key_confidence": float(best_key["confidence"]),
            "camelot_key": camelot_key,
            "key_data": correlations,
        }

    def _analyze_energy(self, y: np.ndarray, sr: int) -> Dict:
        """Analyze energy and intensity features"""
        # RMS energy
        rms = librosa.feature.rms(y=y)[0]

        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]

        # Zero crossing rate (indicates percussiveness)
        zcr = librosa.feature.zero_crossing_rate(y)[0]

        # Dynamic range
        db = librosa.amplitude_to_db(rms, ref=np.max)
        dynamic_range = float(np.max(db) - np.min(db))

        # Overall energy (0-1 scale)
        energy = float(np.mean(rms))
        normalized_energy = np.clip(energy / 0.1, 0, 1)  # Normalize to typical range

        # Energy variance (indicates dynamics)
        energy_variance = float(np.std(rms))

        # Calculate energy over time for automation
        hop_length = 512
        frame_length = 2048

        # Segment into 8-bar sections (assuming 4/4 time)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bars_per_section = 8
        beats_per_bar = 4
        section_duration = (60.0 / tempo) * beats_per_bar * bars_per_section

        # Calculate energy per section
        section_energies = []
        for i in range(0, len(y), int(section_duration * sr)):
            section = y[i : i + int(section_duration * sr)]
            if len(section) > 0:
                section_rms = float(np.sqrt(np.mean(section**2)))
                section_energies.append(section_rms)

        return {
            "energy": normalized_energy,
            "energy_variance": energy_variance,
            "dynamic_range_db": dynamic_range,
            "spectral_centroid_mean": float(np.mean(spectral_centroids)),
            "spectral_rolloff_mean": float(np.mean(spectral_rolloff)),
            "zero_crossing_rate": float(np.mean(zcr)),
            "section_energies": section_energies,
            "percussiveness": float(np.mean(zcr) * 1000),  # Scaled ZCR
        }


class WaveformAnalyzer:
    """Generate waveform data for visualization"""

    def __init__(self, sample_rate: int = 44100, visual_rate: int = 60):
        self.sample_rate = sample_rate
        self.visual_rate = visual_rate  # Samples per second for visualization

    async def generate_waveform(self, filepath: str) -> Dict:
        """Generate downsampled waveform data"""
        try:
            # Load audio
            y, sr = librosa.load(filepath, sr=self.sample_rate, mono=False)

            # Convert to mono for waveform
            if y.ndim > 1:
                y_mono = librosa.to_mono(y)
            else:
                y_mono = y

            # Calculate downsample factor
            downsample_factor = int(sr / self.visual_rate)

            # Process in chunks to get peak values
            waveform_data = []
            for i in range(0, len(y_mono), downsample_factor):
                chunk = y_mono[i : i + downsample_factor]
                if len(chunk) > 0:
                    # Get both positive and negative peaks
                    peak_pos = float(np.max(chunk))
                    peak_neg = float(np.min(chunk))
                    rms = float(np.sqrt(np.mean(chunk**2)))
                    waveform_data.append(
                        {"peak_pos": peak_pos, "peak_neg": peak_neg, "rms": rms}
                    )

            return {
                "waveform": waveform_data,
                "sample_rate": self.visual_rate,
                "duration": len(y_mono) / sr,
            }

        except Exception as e:
            logger.error(f"Error generating waveform for {filepath}: {e}")
            return {"waveform": [], "error": str(e)}

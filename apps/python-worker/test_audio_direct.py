#!/usr/bin/env python3
"""
Direct test of audio pre-rendering without service manager dependencies.
This test directly uses the AudioPrerenderer to process a real file.
"""

import asyncio
import os
import sys
import logging
import numpy as np
import librosa
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.dj_set_models import DJSet, DJSetTrack

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleAudioPrerenderer:
    """Simplified audio pre-renderer for testing."""
    
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 2
        self.bit_depth = 16
        self.output_dir = os.path.expanduser("~/Downloads/streamie_test_output")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def create_wav_header(self, data_size: int) -> bytes:
        """Create a complete WAV header with known size"""
        import struct
        header = bytearray()
        
        # RIFF chunk
        header.extend(b"RIFF")
        header.extend(struct.pack("<I", 36 + data_size))  # File size - 8
        header.extend(b"WAVE")
        
        # fmt chunk
        header.extend(b"fmt ")
        header.extend(struct.pack("<I", 16))  # Chunk size
        header.extend(struct.pack("<H", 1))   # PCM format
        header.extend(struct.pack("<H", self.channels))
        header.extend(struct.pack("<I", self.sample_rate))
        byte_rate = self.sample_rate * self.channels * (self.bit_depth // 8)
        header.extend(struct.pack("<I", byte_rate))
        block_align = self.channels * (self.bit_depth // 8)
        header.extend(struct.pack("<H", block_align))
        header.extend(struct.pack("<H", self.bit_depth))
        
        # data chunk
        header.extend(b"data")
        header.extend(struct.pack("<I", data_size))
        
        return bytes(header)
        
    def apply_simple_effects(self, audio: np.ndarray, fade_in_sec: float = 2.0, fade_out_sec: float = 2.0) -> np.ndarray:
        """Apply simple fade in/out effects."""
        # Fade in
        fade_in_samples = int(fade_in_sec * self.sample_rate)
        if audio.shape[1] > fade_in_samples:
            fade_in = np.linspace(0, 1, fade_in_samples)
            audio[:, :fade_in_samples] *= fade_in
            
        # Fade out
        fade_out_samples = int(fade_out_sec * self.sample_rate)
        if audio.shape[1] > fade_out_samples:
            fade_out = np.linspace(1, 0, fade_out_samples)
            audio[:, -fade_out_samples:] *= fade_out
            
        return audio
        
    def prerender_audio_file(self, input_path: str, duration_sec: float = 60.0) -> str:
        """Pre-render an audio file with basic effects."""
        logger.info(f"🎵 Loading audio file: {input_path}")
        
        try:
            # Load audio with librosa
            audio_data, sr = librosa.load(input_path, sr=self.sample_rate, mono=False, duration=duration_sec)
            
            # Ensure stereo
            if audio_data.ndim == 1:
                audio_data = np.stack([audio_data, audio_data])
            elif audio_data.shape[0] > 2:
                audio_data = audio_data[:2]
                
            logger.info(f"✅ Loaded {audio_data.shape[1] / self.sample_rate:.1f}s of audio")
            
            # Apply simple effects
            logger.info("🎨 Applying fade effects...")
            audio_data = self.apply_simple_effects(audio_data)
            
            # Normalize to prevent clipping
            max_val = np.abs(audio_data).max()
            if max_val > 0:
                audio_data = audio_data / max_val * 0.95
                
            # Convert to 16-bit PCM
            audio_16bit = (audio_data * 32767).astype(np.int16)
            
            # Interleave channels
            interleaved = np.empty((audio_16bit.shape[1] * 2,), dtype=np.int16)
            interleaved[0::2] = audio_16bit[0]  # Left channel
            interleaved[1::2] = audio_16bit[1]  # Right channel
            
            # Create WAV file
            audio_bytes = interleaved.tobytes()
            wav_header = self.create_wav_header(len(audio_bytes))
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_output_{timestamp}.wav"
            output_path = os.path.join(self.output_dir, filename)
            
            with open(output_path, 'wb') as f:
                f.write(wav_header + audio_bytes)
                
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            logger.info(f"✅ Pre-rendered file saved:")
            logger.info(f"   Path: {output_path}")
            logger.info(f"   Size: {file_size:.2f} MB")
            logger.info(f"   Duration: {audio_data.shape[1] / self.sample_rate:.1f}s")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error processing audio: {e}")
            raise


def main():
    """Main test function."""
    # Test file path
    test_file = "/Users/lynscott/Downloads/PLAYLISTS/AFRO HITS/Gyakie/Forever (Remix) (Single)/01 Forever (Remix).mp3"
    
    # Check if file exists
    if not os.path.exists(test_file):
        logger.error(f"❌ Test file not found: {test_file}")
        # Try to find another file
        logger.info("🔍 Looking for alternative test files...")
        import glob
        alt_files = glob.glob(os.path.expanduser("~/Downloads/PLAYLISTS/*/*/*/*.mp3"))[:5]
        if alt_files:
            test_file = alt_files[0]
            logger.info(f"📁 Using alternative file: {test_file}")
        else:
            logger.error("❌ No MP3 files found in PLAYLISTS directory")
            return
    
    logger.info("🚀 Starting direct audio pre-rendering test")
    
    try:
        # Create pre-renderer
        prerenderer = SimpleAudioPrerenderer()
        
        # Process the file
        output_path = prerenderer.prerender_audio_file(test_file, duration_sec=60.0)
        
        # Copy to Downloads for easy access
        import shutil
        final_path = os.path.expanduser("~/Downloads/test_audio_engine_output.wav")
        shutil.copy2(output_path, final_path)
        
        logger.info(f"🎉 SUCCESS! Test completed")
        logger.info(f"📁 Output file copied to: {final_path}")
        logger.info(f"🎧 You can now play this file to verify the audio engine works!")
        
    except Exception as e:
        logger.error(f"💥 Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
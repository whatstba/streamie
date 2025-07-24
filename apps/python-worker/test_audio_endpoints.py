#!/usr/bin/env python3
"""
Test audio streaming endpoints to diagnose browser playback issues
"""

import requests
import time
import sys
import os
import subprocess
import tempfile

API_BASE = "http://localhost:8000"

def test_endpoint(endpoint_name: str, url: str):
    """Test a single streaming endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {endpoint_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        # Test 1: Basic connectivity
        print("1. Testing connectivity...")
        response = requests.get(url, stream=True, timeout=5)
        print(f"   ✅ Status code: {response.status_code}")
        print(f"   ✅ Content-Type: {response.headers.get('Content-Type', 'Not set')}")
        
        # Test 2: Download first chunk
        print("\n2. Downloading first chunk...")
        chunk_count = 0
        total_bytes = 0
        
        # Create temp file to save audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    chunk_count += 1
                    total_bytes += len(chunk)
                    
                    if chunk_count >= 50:  # Get ~400KB
                        break
            
        print(f"   ✅ Downloaded {chunk_count} chunks ({total_bytes / 1024:.1f} KB)")
        
        # Test 3: Verify WAV header
        print("\n3. Verifying WAV header...")
        with open(temp_filename, 'rb') as f:
            header = f.read(44)
            
            if header[:4] == b'RIFF':
                print("   ✅ Valid RIFF header")
                file_size = int.from_bytes(header[4:8], 'little')
                print(f"   ℹ️  Declared file size: {file_size:,} bytes")
                
                if header[8:12] == b'WAVE':
                    print("   ✅ Valid WAVE format")
                    
                    # Check fmt chunk
                    if header[12:16] == b'fmt ':
                        fmt_size = int.from_bytes(header[16:20], 'little')
                        audio_format = int.from_bytes(header[20:22], 'little')
                        channels = int.from_bytes(header[22:24], 'little')
                        sample_rate = int.from_bytes(header[24:28], 'little')
                        byte_rate = int.from_bytes(header[28:32], 'little')
                        bits_per_sample = int.from_bytes(header[34:36], 'little')
                        
                        print(f"   ✅ Valid fmt chunk")
                        print(f"   ℹ️  Format: PCM ({audio_format})")
                        print(f"   ℹ️  Channels: {channels}")
                        print(f"   ℹ️  Sample rate: {sample_rate} Hz")
                        print(f"   ℹ️  Bits/sample: {bits_per_sample}")
                        
                        # Check data chunk
                        if header[36:40] == b'data':
                            data_size = int.from_bytes(header[40:44], 'little')
                            print(f"   ✅ Valid data chunk")
                            print(f"   ℹ️  Data size: {data_size:,} bytes")
                        else:
                            print(f"   ❌ Invalid data chunk: {header[36:40]}")
                    else:
                        print(f"   ❌ Invalid fmt chunk: {header[12:16]}")
                else:
                    print(f"   ❌ Not WAVE format: {header[8:12]}")
            else:
                print(f"   ❌ Not RIFF format: {header[:4]}")
        
        # Test 4: Try to play with ffplay
        print("\n4. Testing playback with ffplay...")
        if os.path.exists(temp_filename):
            try:
                # Use ffplay to test playback (will play for 2 seconds)
                result = subprocess.run(
                    ['ffplay', '-nodisp', '-autoexit', '-t', '2', temp_filename],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    print("   ✅ ffplay playback successful")
                else:
                    print(f"   ❌ ffplay error: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("   ⚠️  ffplay timed out")
            except FileNotFoundError:
                print("   ⚠️  ffplay not installed - skipping playback test")
            
            # Clean up
            os.unlink(temp_filename)
        
        print(f"\n✅ {endpoint_name} test completed successfully")
        
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error - is the server running?")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Test all audio streaming endpoints"""
    print("🎵 Audio Streaming Endpoint Test Suite")
    print("=====================================")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE}/")
        print(f"✅ Server is running at {API_BASE}")
    except:
        print(f"❌ Server is not running at {API_BASE}")
        print("Please start the server with: python main.py")
        return
    
    # Test endpoints
    endpoints = [
        ("Instant Test Tone", f"{API_BASE}/api/test/instant-tone"),
        ("Chunked Test Tone", f"{API_BASE}/api/test/chunked-tone"),
        ("Instant File Stream", f"{API_BASE}/api/test/instant-file"),
    ]
    
    for name, url in endpoints:
        test_endpoint(name, url)
        
        # Ask to continue
        print("\nPress Enter to continue to next test, or Ctrl+C to exit...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nTest suite interrupted by user")
            break
    
    print("\n" + "="*60)
    print("Test suite completed!")
    print("="*60)
    
    # Provide browser test URLs
    print("\n🌐 Browser Test URLs:")
    print("Try these URLs directly in your browser:")
    for name, url in endpoints:
        print(f"  - {name}: {url}")
    
    print("\n💡 To test in HTML:")
    print("""
<audio controls>
  <source src="http://localhost:8000/api/test/instant-tone" type="audio/wav">
  Your browser does not support the audio element.
</audio>
""")


if __name__ == "__main__":
    main()
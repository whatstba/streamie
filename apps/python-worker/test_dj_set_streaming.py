#!/usr/bin/env python3
"""
Test DJ set generation and streaming
"""

import requests
import asyncio
import time

API_BASE = "http://localhost:8000"

async def test_dj_set_streaming():
    print("🎵 Testing DJ set streaming...")
    
    try:
        # Step 1: Generate a DJ set
        print("\n1. Generating DJ set...")
        response = requests.post(f"{API_BASE}/api/dj-set/generate", json={
            "vibe_description": "upbeat house music for testing",
            "duration_minutes": 5,
            "energy_pattern": "wave"
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to generate DJ set: {response.text}")
            return
        
        dj_set = response.json()
        set_id = dj_set["set_id"]
        print(f"✅ DJ set generated: {set_id}")
        print(f"   - Tracks: {dj_set['track_count']}")
        print(f"   - Duration: {dj_set['total_duration']:.1f}s")
        
        # Step 2: Start playback
        print("\n2. Starting playback...")
        response = requests.post(f"{API_BASE}/api/dj-set/{set_id}/play")
        
        if response.status_code != 200:
            print(f"❌ Failed to start playback: {response.text}")
            return
            
        print("✅ Playback started")
        
        # Step 3: Check playback status
        print("\n3. Checking playback status...")
        response = requests.get(f"{API_BASE}/api/dj-set/playback/status")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Status: {'Playing' if status['is_playing'] else 'Not playing'}")
            if status.get('current_track'):
                print(f"   - Current track: {status['current_track']}")
        
        # Step 4: Test chunked streaming
        print("\n4. Testing chunked stream...")
        stream_url = f"{API_BASE}/api/audio/stream/chunked/{set_id}"
        response = requests.get(stream_url, stream=True, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Stream failed: {response.status_code} - {response.text}")
            return
        
        # Download first few chunks
        chunk_count = 0
        total_bytes = 0
        start_time = time.time()
        
        with open("dj_set_test.wav", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    chunk_count += 1
                    total_bytes += len(chunk)
                    
                    if chunk_count % 100 == 0:
                        elapsed = time.time() - start_time
                        print(f"   Downloaded: {total_bytes / 1024 / 1024:.1f} MB in {elapsed:.1f}s")
                    
                    # Get about 10 seconds of audio
                    if total_bytes > 44100 * 2 * 2 * 10:  # 10 seconds at 44.1kHz stereo 16-bit
                        break
        
        print(f"✅ Downloaded {chunk_count} chunks ({total_bytes / 1024 / 1024:.1f} MB)")
        
        # Step 5: Stop playback
        print("\n5. Stopping playback...")
        response = requests.post(f"{API_BASE}/api/dj-set/playback/stop")
        print("✅ Playback stopped")
        
        # Test the downloaded file
        print("\n6. Testing downloaded audio...")
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-i', 'dj_set_test.wav', '-show_streams', '-v', 'quiet'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Audio file is valid")
            # Play first 3 seconds
            print("   Playing first 3 seconds...")
            subprocess.run(['ffplay', '-nodisp', '-autoexit', '-t', '3', 'dj_set_test.wav'])
        else:
            print("❌ Audio file validation failed")
        
        print("\n🎉 DJ set streaming test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_dj_set_streaming())
#!/usr/bin/env python3
"""
Test the complete DJ set streaming flow
"""

import asyncio
import requests
import time

API_BASE = "http://localhost:8000"

async def test_complete_flow():
    print("🎵 Testing complete DJ set streaming flow...")
    
    try:
        # Step 1: Generate a DJ set
        print("1. Generating DJ set...")
        response = requests.post(f"{API_BASE}/api/dj-set/generate", json={
            "vibe_description": "test streaming",
            "duration_minutes": 3,
            "energy_level": "medium"
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to generate DJ set: {response.text}")
            return
        
        dj_set = response.json()
        set_id = dj_set["id"]
        print(f"✅ DJ set generated: {set_id}")
        
        # Step 2: Start playback
        print("2. Starting playback...")
        response = requests.post(f"{API_BASE}/api/dj-set/{set_id}/play")
        
        if response.status_code != 200:
            print(f"❌ Failed to start playback: {response.text}")
            return
            
        print("✅ Playback started")
        
        # Step 3: Wait for audio engine to sync
        print("3. Waiting for audio engine sync...")
        await asyncio.sleep(2)
        
        # Step 4: Test chunked streaming
        print("4. Testing chunked stream...")
        response = requests.get(f"{API_BASE}/api/audio/stream/chunked/{set_id}", 
                              stream=True, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Chunked stream failed: {response.status_code} - {response.text}")
            return
        
        # Read first few chunks
        chunk_count = 0
        total_bytes = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                chunk_count += 1
                total_bytes += len(chunk)
                if chunk_count >= 10:  # Get first 10 chunks
                    break
        
        print(f"✅ Received {chunk_count} chunks ({total_bytes} bytes)")
        
        # Step 5: Check stream status
        print("5. Checking stream status...")
        response = requests.get(f"{API_BASE}/api/audio/stream/status/{set_id}")
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Stream status: rendered={status['is_rendered']}")
        
        print("🎉 Complete flow test successful!")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())
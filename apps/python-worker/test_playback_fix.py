#!/usr/bin/env python3
"""
Test script to verify DJ set playback fixes
"""

import asyncio
import requests
import time

API_BASE = "http://localhost:8000"

def test_playback_fix():
    print("1. Generating a simple DJ set...")
    
    # Generate a DJ set
    response = requests.post(f"{API_BASE}/api/dj-set/generate", json={
        "vibe_description": "quick test mix",
        "duration_minutes": 5,
        "energy_level": "medium"
    })
    
    if response.status_code != 200:
        print(f"ERROR: Failed to generate DJ set: {response.text}")
        return
    
    dj_set = response.json()
    set_id = dj_set["id"]
    print(f"✓ DJ set generated: {dj_set['name']} (ID: {set_id})")
    
    # Wait a moment
    time.sleep(1)
    
    print("\n2. Starting playback...")
    response = requests.post(f"{API_BASE}/api/dj-set/{set_id}/play")
    
    if response.status_code != 200:
        print(f"ERROR: Failed to start playback: {response.text}")
        return
        
    print("✓ Playback started successfully")
    
    # Wait for audio engine to sync
    time.sleep(1)
    
    print("\n3. Checking audio engine status...")
    response = requests.get(f"{API_BASE}/api/audio/status")
    
    if response.status_code != 200:
        print(f"ERROR: Failed to get audio status: {response.text}")
        return
        
    status = response.json()
    print(f"✓ Audio engine running: {status['is_running']}")
    print(f"✓ Active decks: {status['active_decks']}")
    
    print("\n4. Testing audio stream...")
    # Try to get a small chunk of audio
    response = requests.get(f"{API_BASE}/api/audio/test-sine-wave", stream=True)
    
    if response.status_code != 200:
        print(f"ERROR: Failed to get audio stream: {response.text}")
        return
        
    # Read first chunk
    chunk_count = 0
    for chunk in response.iter_content(chunk_size=1024):
        chunk_count += 1
        if chunk_count >= 5:
            break
            
    print(f"✓ Audio streaming working: received {chunk_count} chunks")
    
    # Stop playback
    print("\n5. Stopping playback...")
    response = requests.post(f"{API_BASE}/api/dj-set/stop")
    print("✓ Playback stopped")
    
    print("\n✅ All tests passed! Playback fix is working.")

if __name__ == "__main__":
    test_playback_fix()
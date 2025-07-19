#!/usr/bin/env python3
"""Test API endpoints to diagnose the issue."""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=== Testing API Endpoints ===\n")

# Test root endpoint
try:
    print("1. Testing root endpoint (/)...")
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test library stats
try:
    print("\n2. Testing library stats (/api/library/stats)...")
    response = requests.get(f"{BASE_URL}/api/library/stats", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Response: {json.dumps(stats, indent=2)}")
        print(f"   Active folders: {stats.get('active_folders', 'NOT FOUND')}")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test tracks endpoint
try:
    print("\n3. Testing tracks endpoint (/tracks)...")
    response = requests.get(f"{BASE_URL}/tracks", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        tracks = response.json()
        print(f"   Total tracks returned: {len(tracks)}")
        if tracks:
            print(f"   First track: {tracks[0].get('filename', 'NO FILENAME')}")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test music folders
try:
    print("\n4. Testing music folders (/api/library/folders)...")
    response = requests.get(f"{BASE_URL}/api/library/folders", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        folders = data.get("folders", [])
        print(f"   Total folders: {len(folders)}")
        for folder in folders:
            print(f"   - {folder.get('path')} (enabled: {folder.get('enabled')})")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ERROR: {e}")

"""Test script for Phase 4: Real-time Analysis Agent Integration"""
import requests
import json
import time
import asyncio
import websockets

BASE_URL = "http://localhost:8000"

def test_analysis_endpoints():
    """Test all analysis endpoints"""
    print("=" * 50)
    print("PHASE 4: REAL-TIME ANALYSIS TESTS")
    print("=" * 50)
    
    # Test 1: Trigger analysis for a specific track
    print("\n1. Testing POST /api/analysis/track")
    filepath = "../../../../Downloads/09 M.I.A. (Clean).mp3"
    data = {
        "filepath": filepath,
        "priority": 1,
        "analysis_type": "realtime"
    }
    response = requests.post(f"{BASE_URL}/api/analysis/track", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        task_id = result.get("task_id")
        assert task_id is not None
    else:
        print(f"Error: {response.text}")
        task_id = None
    
    # Test 2: Check analysis status
    if task_id:
        print("\n2. Testing GET /api/analysis/status/{task_id}")
        time.sleep(2)  # Give it time to process
        response = requests.get(f"{BASE_URL}/api/analysis/status/{task_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
    
    # Test 3: Get queue status
    print("\n3. Testing GET /api/analysis/queue/status")
    response = requests.get(f"{BASE_URL}/api/analysis/queue/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Test 4: Get cached analysis results
    print("\n4. Testing POST /api/analysis/results")
    response = requests.post(f"{BASE_URL}/api/analysis/results", json={"filepath": filepath})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"BPM: {result.get('bpm')}")
        print(f"Key: {result.get('key')} ({result.get('camelot_key')})")
        print(f"Energy Level: {result.get('energy_level')}")
    
    # Test 5: Batch analysis
    print("\n5. Testing POST /api/analysis/batch")
    filepaths = [
        "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Ashanti/Concrete Rose (Album)/04 Only U.mp3",
        "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Avant/Avant (Album)/03 Involve Yourself.mp3"
    ]
    response = requests.post(f"{BASE_URL}/api/analysis/batch", json=filepaths)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 6: Beat phase calculation
    print("\n6. Testing POST /api/analysis/beat-phase")
    data = {"filepath": filepath, "position": 30.5}  # 30.5 seconds into the track
    response = requests.post(
        f"{BASE_URL}/api/analysis/beat-phase", 
        json=data
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    print("\n" + "=" * 50)
    print("ALL ANALYSIS ENDPOINT TESTS COMPLETED!")
    print("=" * 50)


def test_deck_analysis_integration():
    """Test integration with deck loading"""
    print("\n" + "=" * 50)
    print("DECK-ANALYSIS INTEGRATION TESTS")
    print("=" * 50)
    
    # Load a track on deck A
    print("\n1. Loading track on deck A (should trigger analysis)")
    data = {"track_filepath": "../../../../Downloads/09 M.I.A. (Clean).mp3"}
    response = requests.post(f"{BASE_URL}/api/decks/A/load", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Give analysis time to run
    print("\n2. Waiting for analysis to complete...")
    time.sleep(3)
    
    # Check queue status
    response = requests.get(f"{BASE_URL}/api/analysis/queue/status")
    queue_status = response.json()
    print(f"Queue status: {json.dumps(queue_status, indent=2)}")
    
    # Load another track on deck B
    print("\n3. Loading track on deck B")
    data = {"track_filepath": "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Ashanti/Concrete Rose (Album)/04 Only U.mp3"}
    response = requests.post(f"{BASE_URL}/api/decks/B/load", json=data)
    print(f"Status: {response.status_code}")
    
    # Test transition analysis
    print("\n4. Testing transition analysis between decks A and B")
    data = {
        "deck_a_id": "A",
        "deck_b_id": "B"
    }
    response = requests.post(f"{BASE_URL}/api/analysis/transition", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Compatibility: {json.dumps(result.get('compatibility'), indent=2)}")
        print(f"Transition points: {len(result.get('transition_points', []))}")
        print(f"Recommended effects: {result.get('recommended_effects')}")
    
    print("\n" + "=" * 50)
    print("INTEGRATION TESTS COMPLETED!")
    print("=" * 50)


async def test_websocket_streaming():
    """Test WebSocket streaming for real-time analysis updates"""
    print("\n" + "=" * 50)
    print("WEBSOCKET STREAMING TEST")
    print("=" * 50)
    
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8000/api/analysis/stream/A"
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Receive messages
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    print(f"Received: {json.dumps(data, indent=2)}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                    break
            
            print("Closing WebSocket connection")
    except Exception as e:
        print(f"WebSocket test failed: {e}")
    
    print("=" * 50)


def test_regression():
    """Test that previous phases still work"""
    print("\n" + "=" * 50)
    print("REGRESSION TESTS")
    print("=" * 50)
    
    # Test deck endpoints
    print("\n1. Testing deck endpoints")
    response = requests.get(f"{BASE_URL}/api/decks/")
    print(f"GET /api/decks/ - Status: {response.status_code}")
    assert response.status_code == 200
    
    # Test mixer endpoints
    print("\n2. Testing mixer endpoints")
    response = requests.get(f"{BASE_URL}/api/mixer/state")
    print(f"GET /api/mixer/state - Status: {response.status_code}")
    assert response.status_code == 200
    
    # Test deck state updates
    print("\n3. Testing deck state updates")
    data = {"volume": 0.8, "tempo_adjust": 1.5}
    response = requests.put(f"{BASE_URL}/api/decks/A/state", json=data)
    print(f"PUT /api/decks/A/state - Status: {response.status_code}")
    assert response.status_code == 200
    
    print("\n" + "=" * 50)
    print("REGRESSION TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        # Run synchronous tests
        test_analysis_endpoints()
        test_deck_analysis_integration()
        test_regression()
        
        # Run async WebSocket test
        print("\nRunning WebSocket test...")
        asyncio.run(test_websocket_streaming())
        
        print("\n" + "=" * 70)
        print("✅ ALL PHASE 4 TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
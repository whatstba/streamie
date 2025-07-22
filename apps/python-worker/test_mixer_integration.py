"""Test script for Phase 3: Mixer Integration"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_mixer_endpoints():
    """Test all mixer endpoints"""
    print("=" * 50)
    print("PHASE 3: MIXER INTEGRATION TESTS")
    print("=" * 50)
    
    # Test 1: Get mixer state
    print("\n1. Testing GET /api/mixer/state")
    response = requests.get(f"{BASE_URL}/api/mixer/state")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Test 2: Update crossfader
    print("\n2. Testing PUT /api/mixer/crossfader")
    data = {"position": 0.3, "apply_to_decks": True}
    response = requests.put(f"{BASE_URL}/api/mixer/crossfader", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    assert response.status_code == 200
    assert result['position'] == 0.3
    
    # Test 3: Change crossfader curve
    print("\n3. Testing PUT /api/mixer/crossfader/curve")
    data = {"curve": "scratch"}
    response = requests.put(f"{BASE_URL}/api/mixer/crossfader/curve", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    assert response.status_code == 200
    assert result['curve'] == 'scratch'
    
    # Test 4: Update master output
    print("\n4. Testing PUT /api/mixer/master")
    data = {"volume": 0.9, "gain": 1.2}
    response = requests.put(f"{BASE_URL}/api/mixer/master", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Test 5: Update monitor settings
    print("\n5. Testing PUT /api/mixer/monitor")
    data = {"volume": 0.6, "cue_mix": 0.3}
    response = requests.put(f"{BASE_URL}/api/mixer/monitor", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Test 6: Get channel levels
    print("\n6. Testing GET /api/mixer/levels")
    response = requests.get(f"{BASE_URL}/api/mixer/levels")
    print(f"Status: {response.status_code}")
    levels = response.json()
    print(f"Response: {json.dumps(levels, indent=2)}")
    assert response.status_code == 200
    assert 'master' in levels
    
    # Test 7: Load a track (for auto-gain test)
    print("\n7. Loading track on deck B")
    data = {"track_filepath": "PLAYLISTS/NEW JACK SWING/112/112 (Album)/05 Cupid.mp3"}
    response = requests.post(f"{BASE_URL}/api/decks/B/load", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 8: Auto-gain
    print("\n8. Testing POST /api/mixer/auto-gain/B")
    response = requests.post(f"{BASE_URL}/api/mixer/auto-gain/B")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    assert response.status_code == 200
    if result['success']:
        assert 'suggested_gain' in result
    
    # Test 9: Toggle cue
    print("\n9. Testing POST /api/mixer/channels/B/cue")
    response = requests.post(f"{BASE_URL}/api/mixer/channels/B/cue")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Test 10: Get specific channel level
    print("\n10. Testing GET /api/mixer/channel/B/level")
    response = requests.get(f"{BASE_URL}/api/mixer/channel/B/level")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    
    # Test 11: Recording control
    print("\n11. Testing recording start/stop")
    data = {"filepath": "/tmp/test_recording.wav"}
    response = requests.post(f"{BASE_URL}/api/mixer/recording/start", json=data)
    print(f"Start recording - Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    time.sleep(1)  # Record for 1 second
    
    response = requests.post(f"{BASE_URL}/api/mixer/recording/stop")
    print(f"Stop recording - Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    print("\n" + "=" * 50)
    print("ALL MIXER INTEGRATION TESTS PASSED!")
    print("=" * 50)

def test_deck_mixer_integration():
    """Test deck and mixer integration"""
    print("\n" + "=" * 50)
    print("DECK-MIXER INTEGRATION TESTS")
    print("=" * 50)
    
    # Load tracks on A and B
    print("\n1. Loading tracks on decks A and B")
    tracks = [
        ("A", "PLAYLISTS/THRWBYKES/112/112 (Album)/07 Come See Me.mp3"),
        ("B", "PLAYLISTS/NEW JACK SWING/112/112 (Album)/05 Cupid.mp3")
    ]
    
    for deck_id, filepath in tracks:
        data = {"track_filepath": filepath}
        response = requests.post(f"{BASE_URL}/api/decks/{deck_id}/load", json=data)
        print(f"Deck {deck_id} - Status: {response.status_code}")
    
    # Test crossfader affects output levels
    print("\n2. Testing crossfader effect on levels")
    positions = [-1.0, -0.5, 0.0, 0.5, 1.0]
    
    for pos in positions:
        data = {"position": pos}
        requests.put(f"{BASE_URL}/api/mixer/crossfader", json=data)
        
        response = requests.get(f"{BASE_URL}/api/mixer/levels")
        levels = response.json()
        
        print(f"\nCrossfader at {pos}:")
        print(f"  Deck A level: {levels['A']['level']:.3f}")
        print(f"  Deck B level: {levels['B']['level']:.3f}")
    
    # Test EQ changes
    print("\n3. Testing EQ changes on deck A")
    eq_settings = [
        {"eq_low": 0.5, "eq_mid": 0.0, "eq_high": -0.3}
    ]
    
    for settings in eq_settings:
        response = requests.put(f"{BASE_URL}/api/decks/A/state", json=settings)
        print(f"Applied EQ - Status: {response.status_code}")
        
        response = requests.get(f"{BASE_URL}/api/mixer/channel/A/level")
        level_info = response.json()
        print(f"New level with EQ: {level_info['level']:.3f}")
    
    print("\n" + "=" * 50)
    print("INTEGRATION TESTS COMPLETED!")
    print("=" * 50)

def test_regression():
    """Test that Phase 2 functionality still works"""
    print("\n" + "=" * 50)
    print("REGRESSION TESTS")
    print("=" * 50)
    
    # Test deck endpoints still work
    print("\n1. Testing deck endpoints")
    response = requests.get(f"{BASE_URL}/api/decks/")
    print(f"GET /api/decks/ - Status: {response.status_code}")
    assert response.status_code == 200
    
    response = requests.get(f"{BASE_URL}/api/decks/A")
    print(f"GET /api/decks/A - Status: {response.status_code}")
    assert response.status_code == 200
    
    # Test deck state updates
    print("\n2. Testing deck state updates")
    data = {"volume": 0.7, "tempo_adjust": 2.5}
    response = requests.put(f"{BASE_URL}/api/decks/A/state", json=data)
    print(f"PUT /api/decks/A/state - Status: {response.status_code}")
    assert response.status_code == 200
    
    print("\n" + "=" * 50)
    print("REGRESSION TESTS PASSED!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        test_mixer_endpoints()
        test_deck_mixer_integration()
        test_regression()
        
        print("\n" + "=" * 70)
        print("✅ ALL PHASE 3 TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
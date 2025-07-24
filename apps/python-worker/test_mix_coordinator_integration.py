"""Test script for Phase 5: Mix Coordinator Agent Integration"""

import requests
import json
import time
import asyncio
import websockets
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"


def test_mix_endpoints():
    """Test all mix coordination endpoints"""
    print("=" * 50)
    print("PHASE 5: MIX COORDINATOR TESTS")
    print("=" * 50)

    # Test 1: Coordinate mix without active decks
    print("\n1. Testing POST /api/mix/coordinate (no active decks)")
    response = requests.post(f"{BASE_URL}/api/mix/coordinate", json={})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"Error: {response.text}")

    # Test 2: Get current plan (should be None)
    print("\n2. Testing GET /api/mix/current-plan")
    response = requests.get(f"{BASE_URL}/api/mix/current-plan")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200

    # Test 3: Get mix history
    print("\n3. Testing GET /api/mix/history")
    response = requests.get(f"{BASE_URL}/api/mix/history")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200

    # Test 4: Get transition status (no active transition)
    print("\n4. Testing GET /api/mix/transition/status")
    response = requests.get(f"{BASE_URL}/api/mix/transition/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200

    print("\n" + "=" * 50)
    print("MIX ENDPOINT TESTS COMPLETED!")
    print("=" * 50)


def test_mix_coordination_with_decks():
    """Test mix coordination with loaded decks"""
    print("\n" + "=" * 50)
    print("MIX COORDINATION WITH DECKS TEST")
    print("=" * 50)

    # Load tracks on decks
    print("\n1. Loading tracks on decks A and B")

    # Load track on deck A
    track_a = "../../../../Downloads/09 M.I.A. (Clean).mp3"
    response = requests.post(
        f"{BASE_URL}/api/decks/A/load", json={"track_filepath": track_a}
    )
    print(f"Deck A load status: {response.status_code}")

    # Load track on deck B
    track_b = "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Ashanti/Concrete Rose (Album)/04 Only U.mp3"
    response = requests.post(
        f"{BASE_URL}/api/decks/B/load", json={"track_filepath": track_b}
    )
    print(f"Deck B load status: {response.status_code}")

    # Start playing deck A
    print("\n2. Starting playback on deck A")
    response = requests.put(f"{BASE_URL}/api/decks/A/state", json={"is_playing": True})
    print(f"Play status: {response.status_code}")

    # Wait for analysis to complete
    print("\n3. Waiting for track analysis...")
    time.sleep(3)

    # Coordinate mix
    print("\n4. Coordinating mix transition")
    response = requests.post(f"{BASE_URL}/api/mix/coordinate", json={})
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        mix_decision = result.get("mix_decision")

        if mix_decision:
            print("\nMix Decision:")
            print(f"  Action: {mix_decision.get('action')}")
            print(f"  Source: Deck {mix_decision.get('source_deck')}")
            print(f"  Target: Deck {mix_decision.get('target_deck')}")
            print(f"  Duration: {mix_decision.get('duration')}s")
            print(f"  Confidence: {mix_decision.get('decision_confidence'):.2f}")
            print(f"  Reasoning: {mix_decision.get('reasoning')}")

            # Show effects
            effects = mix_decision.get("effects", [])
            if effects:
                print(f"\n  Effects ({len(effects)}):")
                for effect in effects:
                    print(f"    - {effect['type']} (intensity: {effect['intensity']})")

            # Show EQ adjustments
            eq_adjustments = mix_decision.get("eq_adjustments", {})
            if eq_adjustments:
                print("\n  EQ Adjustments:")
                for deck, eq in eq_adjustments.items():
                    print(
                        f"    Deck {deck}: Low={eq['low']:.2f}, Mid={eq['mid']:.2f}, High={eq['high']:.2f}"
                    )

            # Show compatibility
            compatibility = result.get("compatibility", {})
            print("\n  Compatibility:")
            print(f"    Overall: {compatibility.get('overall', 0):.2f}")
            print(f"    BPM: {compatibility.get('bpm', 0):.2f}")
            print(f"    Key: {compatibility.get('key', 0):.2f}")
            print(f"    Energy: {compatibility.get('energy', 0):.2f}")
        else:
            print("No mix decision generated")
    else:
        print(f"Error: {response.text}")

    # Get current plan
    print("\n5. Getting current mix plan")
    response = requests.get(f"{BASE_URL}/api/mix/current-plan")
    if response.status_code == 200:
        result = response.json()
        if result.get("current_plan"):
            print("Current plan is active")
        else:
            print("No current plan")

    print("\n" + "=" * 50)
    print("MIX COORDINATION TEST COMPLETED!")
    print("=" * 50)


def test_transition_execution():
    """Test transition execution"""
    print("\n" + "=" * 50)
    print("TRANSITION EXECUTION TEST")
    print("=" * 50)

    # First, get a mix plan
    print("\n1. Getting mix plan...")
    response = requests.post(f"{BASE_URL}/api/mix/coordinate", json={})

    if response.status_code == 200:
        result = response.json()
        mix_decision = result.get("mix_decision")

        if mix_decision:
            print(f"Got mix plan: {mix_decision['action']}")

            # Execute the transition
            print("\n2. Executing transition...")
            response = requests.post(
                f"{BASE_URL}/api/mix/execute-transition",
                json={"mix_decision": mix_decision},
            )

            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("Transition started!")

                # Monitor transition progress
                print("\n3. Monitoring transition progress...")
                for i in range(5):
                    time.sleep(2)
                    response = requests.get(f"{BASE_URL}/api/mix/transition/status")
                    if response.status_code == 200:
                        status = response.json()
                        if status["active"]:
                            state = status["state"]
                            print(
                                f"  Progress: {state['progress'] * 100:.1f}% - Phase: {state['current_phase']}"
                            )
                        else:
                            print("  Transition completed!")
                            break
            else:
                print(f"Failed to start transition: {response.text}")
        else:
            print("No mix decision available")
    else:
        print(f"Failed to get mix plan: {response.text}")

    print("\n" + "=" * 50)
    print("TRANSITION EXECUTION TEST COMPLETED!")
    print("=" * 50)


@pytest.mark.asyncio
async def test_websocket_streaming():
    """Test WebSocket streaming for mix updates"""
    print("\n" + "=" * 50)
    print("WEBSOCKET STREAMING TEST")
    print("=" * 50)

    try:
        # Connect to WebSocket
        uri = "ws://localhost:8000/api/mix/stream?session_id=test"
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")

            # Receive initial connection message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Initial message: {data}")

            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))

            # Receive messages for a bit
            for i in range(3):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    print(f"Received: {data['type']}")
                    if data["type"] == "transition_update":
                        print(f"  Progress: {data['data']['progress'] * 100:.1f}%")
                        print(f"  Phase: {data['data']['phase']}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                    break

            print("Closing WebSocket connection")
    except Exception as e:
        print(f"WebSocket test error: {e}")

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

    # Test analysis endpoints
    print("\n3. Testing analysis endpoints")
    response = requests.get(f"{BASE_URL}/api/analysis/queue/status")
    print(f"GET /api/analysis/queue/status - Status: {response.status_code}")
    assert response.status_code == 200

    print("\n" + "=" * 50)
    print("REGRESSION TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        # Run synchronous tests
        test_mix_endpoints()
        test_mix_coordination_with_decks()
        test_transition_execution()
        test_regression()

        # Run async WebSocket test
        print("\nRunning WebSocket test...")
        asyncio.run(test_websocket_streaming())

        print("\n" + "=" * 70)
        print("✅ ALL PHASE 5 TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

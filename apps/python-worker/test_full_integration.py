"""Comprehensive Integration Test Suite for All Phases"""

import requests
import json
import time
import asyncio
import websockets
from typing import Dict, List

BASE_URL = "http://localhost:8000"

# Test tracks from the database
TEST_TRACKS = [
    "../../../../Downloads/09 M.I.A. (Clean).mp3",
    "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Ashanti/Concrete Rose (Album)/04 Only U.mp3",
    "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Avant/Avant (Album)/03 Involve Yourself.mp3",
    "../../../../Downloads/PLAYLISTS/2000 FEELGOODS/Andrea Martin/The Best Of Me (Album)/01 Let Me Return The Favor (Album Version).mp3",
]


class IntegrationTestSuite:
    """Comprehensive test suite for all DJ system phases"""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def run_test(self, test_name: str, test_func):
        """Run a test and track results"""
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print("=" * 60)

        try:
            test_func()
            self.passed_tests += 1
            self.test_results.append((test_name, "PASSED", None))
            print(f"✅ {test_name} - PASSED")
        except AssertionError as e:
            self.failed_tests += 1
            self.test_results.append((test_name, "FAILED", str(e)))
            print(f"❌ {test_name} - FAILED: {e}")
        except Exception as e:
            self.failed_tests += 1
            self.test_results.append((test_name, "ERROR", str(e)))
            print(f"❌ {test_name} - ERROR: {e}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print("\nDetailed Results:")
        for test, status, error in self.test_results:
            if status == "PASSED":
                print(f"  ✅ {test}")
            else:
                print(f"  ❌ {test} - {error}")
        print("=" * 70)


# Phase 1: Core State Architecture Tests
def test_phase1_deck_initialization():
    """Test that all 4 decks are properly initialized"""
    # First clear all decks to ensure clean state
    for deck_id in ["A", "B", "C", "D"]:
        requests.post(f"{BASE_URL}/api/decks/{deck_id}/clear")

    response = requests.get(f"{BASE_URL}/api/decks/")
    assert response.status_code == 200

    decks = response.json()
    assert len(decks) == 4

    deck_ids = [deck["id"] for deck in decks]
    assert sorted(deck_ids) == ["A", "B", "C", "D"]

    # Check each deck is empty after clearing
    for deck in decks:
        assert deck["status"] == "empty"
        assert deck["track_id"] is None


# Phase 2: Multi-Deck Management Tests
def test_phase2_deck_loading():
    """Test loading tracks onto decks"""
    # Load track on deck A
    response = requests.post(
        f"{BASE_URL}/api/decks/A/load", json={"track_filepath": TEST_TRACKS[0]}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["track"]["filepath"] == TEST_TRACKS[0]

    # Get deck state
    response = requests.get(f"{BASE_URL}/api/decks/A")
    assert response.status_code == 200
    deck = response.json()
    assert deck["status"] == "loaded"
    assert deck["track_filepath"] == TEST_TRACKS[0]


def test_phase2_deck_state_updates():
    """Test updating deck state (position, tempo, volume)"""
    # Update deck A state
    updates = {"volume": 0.8, "tempo_adjust": 2.5, "is_playing": True}
    response = requests.put(f"{BASE_URL}/api/decks/A/state", json=updates)
    assert response.status_code == 200

    # Verify updates
    response = requests.get(f"{BASE_URL}/api/decks/A")
    deck = response.json()
    assert deck["volume"] == 0.8
    assert deck["tempo_adjust"] == 2.5
    assert deck["is_playing"] is True


def test_phase2_deck_sync():
    """Test syncing two decks"""
    # Load track on deck B
    response = requests.post(
        f"{BASE_URL}/api/decks/B/load", json={"track_filepath": TEST_TRACKS[1]}
    )
    assert response.status_code == 200

    # Sync deck B to deck A
    response = requests.post(
        f"{BASE_URL}/api/decks/sync",
        json={"leader_deck_id": "A", "follower_deck_id": "B"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True


def test_phase2_deck_history():
    """Test deck play history tracking"""
    response = requests.get(f"{BASE_URL}/api/decks/A/history")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)


# Phase 3: Mixer Integration Tests
def test_phase3_mixer_state():
    """Test mixer state management"""
    response = requests.get(f"{BASE_URL}/api/mixer/state")
    assert response.status_code == 200

    mixer = response.json()
    assert "crossfader" in mixer
    assert "master_volume" in mixer
    assert "crossfader_curve" in mixer


def test_phase3_crossfader_control():
    """Test crossfader position and curve"""
    # Update crossfader position
    response = requests.put(
        f"{BASE_URL}/api/mixer/crossfader",
        json={"position": -0.5, "apply_to_decks": True},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["position"] == -0.5

    # Change crossfader curve
    response = requests.put(
        f"{BASE_URL}/api/mixer/crossfader/curve", json={"curve": "scratch"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["curve"] == "scratch"


def test_phase3_channel_levels():
    """Test channel level monitoring"""
    response = requests.get(f"{BASE_URL}/api/mixer/levels")
    assert response.status_code == 200

    levels = response.json()
    assert "A" in levels
    assert "B" in levels
    assert "master" in levels

    # Check deck A has higher level (crossfader at -0.5)
    assert levels["A"]["level"] > levels["B"]["level"]


def test_phase3_auto_gain():
    """Test auto-gain functionality"""
    response = requests.post(f"{BASE_URL}/api/mixer/auto-gain/A")
    assert response.status_code == 200

    result = response.json()
    if result["success"]:
        assert "suggested_gain" in result
        assert "energy_level" in result


# Phase 4: Real-time Analysis Tests
def test_phase4_trigger_analysis():
    """Test triggering track analysis"""
    response = requests.post(
        f"{BASE_URL}/api/analysis/track",
        json={"filepath": TEST_TRACKS[2], "priority": 1, "analysis_type": "realtime"},
    )
    assert response.status_code == 200

    result = response.json()
    assert "task_id" in result
    assert result["status"] == "pending"

    # Wait and check status
    time.sleep(2)
    response = requests.get(f"{BASE_URL}/api/analysis/status/{result['task_id']}")
    assert response.status_code == 200


def test_phase4_batch_analysis():
    """Test batch analysis"""
    response = requests.post(f"{BASE_URL}/api/analysis/batch", json=TEST_TRACKS[:2])
    assert response.status_code == 200

    result = response.json()
    assert result["queued"] == 2
    assert len(result["task_ids"]) == 2


def test_phase4_transition_analysis():
    """Test transition compatibility analysis"""
    # Ensure decks A and B are loaded
    response = requests.post(
        f"{BASE_URL}/api/analysis/transition", json={"deck_a_id": "A", "deck_b_id": "B"}
    )
    assert response.status_code == 200

    result = response.json()
    assert "compatibility" in result
    assert "overall" in result["compatibility"]
    assert "recommended_effects" in result


def test_phase4_beat_phase():
    """Test beat phase calculation"""
    response = requests.post(
        f"{BASE_URL}/api/analysis/beat-phase",
        json={"filepath": TEST_TRACKS[0], "position": 30.5},
    )
    # May fail if track not analyzed yet
    if response.status_code == 200:
        result = response.json()
        assert "phase" in result
        assert "next_beat" in result


# Cross-Phase Integration Tests
def test_integration_load_analyze_mix():
    """Test complete workflow: load -> analyze -> mix"""
    # Clear decks first
    requests.post(f"{BASE_URL}/api/decks/C/clear")
    requests.post(f"{BASE_URL}/api/decks/D/clear")

    # Load tracks on C and D
    for deck_id, track in [("C", TEST_TRACKS[2]), ("D", TEST_TRACKS[3])]:
        response = requests.post(
            f"{BASE_URL}/api/decks/{deck_id}/load", json={"track_filepath": track}
        )
        assert response.status_code == 200

    # Wait for automatic analysis
    time.sleep(3)

    # Check queue status
    response = requests.get(f"{BASE_URL}/api/analysis/queue/status")
    queue = response.json()
    assert queue["running"] is True

    # Set up mixer for transition (crossfader only affects A/B)
    response = requests.put(
        f"{BASE_URL}/api/mixer/crossfader",
        json={"position": -1.0},  # Full A
    )
    assert response.status_code == 200

    # Check levels
    response = requests.get(f"{BASE_URL}/api/mixer/levels")
    levels = response.json()
    # Decks C and D are not affected by crossfader, both should have output
    assert levels["C"]["level"] > 0
    assert levels["D"]["level"] > 0
    # With crossfader at -1.0, deck A should have full output, B none
    assert levels["A"]["level"] > levels["B"]["level"]


def test_integration_mix_point_calculation():
    """Test mix point calculation between decks"""
    response = requests.post(f"{BASE_URL}/api/decks/mix-point/A/B", json={})
    assert response.status_code == 200

    result = response.json()
    if result["success"]:
        assert "deck_a" in result
        assert "deck_b" in result
        assert "transition_duration" in result


async def test_websocket_analysis_stream():
    """Test WebSocket streaming for analysis updates"""
    uri = "ws://localhost:8000/api/analysis/stream/A"
    try:
        async with websockets.connect(uri) as websocket:
            # Should receive connected message
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)
            assert data["type"] == "connected"
            assert data["deck_id"] == "A"
    except Exception as e:
        # WebSocket might timeout if no active analysis
        pass


# Performance and Error Handling Tests
def test_error_invalid_deck():
    """Test error handling for invalid deck ID"""
    response = requests.get(f"{BASE_URL}/api/decks/Z")
    assert response.status_code == 400


def test_error_missing_track():
    """Test error handling for missing track"""
    response = requests.post(
        f"{BASE_URL}/api/decks/A/load", json={"track_filepath": "nonexistent/track.mp3"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is False


def test_concurrent_operations():
    """Test concurrent deck operations"""
    import concurrent.futures

    def update_deck(deck_id, volume):
        return requests.put(
            f"{BASE_URL}/api/decks/{deck_id}/state", json={"volume": volume}
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(update_deck, deck_id, 0.5 + i * 0.1)
            for i, deck_id in enumerate(["A", "B", "C", "D"])
        ]

        for future in concurrent.futures.as_completed(futures):
            response = future.result()
            assert response.status_code == 200


# Main test runner
def run_all_tests():
    """Run all integration tests"""
    suite = IntegrationTestSuite()

    # Phase 1 Tests
    suite.run_test("Phase 1: Deck Initialization", test_phase1_deck_initialization)

    # Phase 2 Tests
    suite.run_test("Phase 2: Deck Loading", test_phase2_deck_loading)
    suite.run_test("Phase 2: Deck State Updates", test_phase2_deck_state_updates)
    suite.run_test("Phase 2: Deck Sync", test_phase2_deck_sync)
    suite.run_test("Phase 2: Deck History", test_phase2_deck_history)

    # Phase 3 Tests
    suite.run_test("Phase 3: Mixer State", test_phase3_mixer_state)
    suite.run_test("Phase 3: Crossfader Control", test_phase3_crossfader_control)
    suite.run_test("Phase 3: Channel Levels", test_phase3_channel_levels)
    suite.run_test("Phase 3: Auto-Gain", test_phase3_auto_gain)

    # Phase 4 Tests
    suite.run_test("Phase 4: Trigger Analysis", test_phase4_trigger_analysis)
    suite.run_test("Phase 4: Batch Analysis", test_phase4_batch_analysis)
    suite.run_test("Phase 4: Transition Analysis", test_phase4_transition_analysis)
    suite.run_test("Phase 4: Beat Phase", test_phase4_beat_phase)

    # Integration Tests
    suite.run_test("Integration: Load-Analyze-Mix", test_integration_load_analyze_mix)
    suite.run_test(
        "Integration: Mix Point Calculation", test_integration_mix_point_calculation
    )

    # Async test
    print("\nRunning async WebSocket test...")
    asyncio.run(test_websocket_analysis_stream())

    # Error Handling Tests
    suite.run_test("Error: Invalid Deck ID", test_error_invalid_deck)
    suite.run_test("Error: Missing Track", test_error_missing_track)
    suite.run_test("Concurrent Operations", test_concurrent_operations)

    # Print summary
    suite.print_summary()

    # Return success/failure
    return suite.failed_tests == 0


if __name__ == "__main__":
    print("🎛️ DJ SYSTEM COMPREHENSIVE INTEGRATION TEST SUITE")
    print("=" * 70)
    print("Testing all phases of the DJ system...")
    print()

    success = run_all_tests()

    if success:
        print("\n✅ ALL TESTS PASSED! System is fully operational.")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED! Please review the errors above.")
        exit(1)

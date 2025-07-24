"""
Test Effect Manager - Comprehensive tests for the effects system.
"""

import pytest
import pytest_asyncio
import asyncio

from models.effect_models import (
    AutomationCurve,
)
from models.mix_models import TransitionEffect, EffectType
from services.effect_manager import EffectManager
from services.effect_simulators import (
    FilterSweepSimulator,
    EchoSimulator,
    create_simulator,
)


@pytest_asyncio.fixture
async def effect_manager():
    """Create a test EffectManager instance"""
    manager = EffectManager()
    yield manager
    await manager.shutdown()


@pytest.mark.asyncio
async def test_apply_effect(effect_manager):
    """Test applying an effect to a deck"""
    # Create test effect
    effect = TransitionEffect(
        type=EffectType.FILTER_SWEEP, intensity=0.7, duration=10.0
    )

    # Apply effect to deck A
    effect_id = await effect_manager.apply_effect("A", effect)

    # Verify effect was applied
    assert effect_id is not None
    assert len(effect_id) == 36  # UUID format

    # Check effect is in active effects
    active_effects = effect_manager.get_all_active_effects()
    assert len(active_effects) == 1
    assert active_effects[0].effect_id == effect_id

    # Check deck has the effect
    deck_effects = effect_manager.get_deck_effects("A")
    assert len(deck_effects) == 1
    assert deck_effects[0].effect_type == EffectType.FILTER_SWEEP


@pytest.mark.asyncio
async def test_stop_effect(effect_manager):
    """Test stopping an effect"""
    # Apply effect
    effect = TransitionEffect(type=EffectType.ECHO, intensity=0.5)
    effect_id = await effect_manager.apply_effect("B", effect)

    # Stop effect
    success = await effect_manager.stop_effect(effect_id)
    assert success is True

    # Verify effect is removed
    active_effects = effect_manager.get_all_active_effects()
    assert len(active_effects) == 0

    # Try stopping non-existent effect
    success = await effect_manager.stop_effect("non-existent")
    assert success is False


@pytest.mark.asyncio
async def test_update_effect_parameters(effect_manager):
    """Test updating effect parameters"""
    # Apply effect
    effect = TransitionEffect(type=EffectType.REVERB, intensity=0.3)
    effect_id = await effect_manager.apply_effect("C", effect)

    # Update parameters
    new_params = {"room_size": 0.8, "wet_level": 0.5}
    success = await effect_manager.update_effect(effect_id, parameters=new_params)
    assert success is True

    # Verify parameters updated
    state = effect_manager.get_effect_state(effect_id)
    assert state.current_parameters["room_size"] == 0.8
    assert state.current_parameters["wet_level"] == 0.5


@pytest.mark.asyncio
async def test_bypass_effect(effect_manager):
    """Test bypassing and resuming effects"""
    # Apply effect
    effect = TransitionEffect(type=EffectType.DELAY, intensity=0.4)
    effect_id = await effect_manager.apply_effect("D", effect)

    # Bypass effect
    success = await effect_manager.bypass_effect(effect_id, bypassed=True)
    assert success is True

    # Check state
    state = effect_manager.get_effect_state(effect_id)
    assert state.is_bypassed is True

    # Resume effect
    success = await effect_manager.bypass_effect(effect_id, bypassed=False)
    assert success is True

    state = effect_manager.get_effect_state(effect_id)
    assert state.is_bypassed is False


@pytest.mark.asyncio
async def test_multiple_effects_per_deck(effect_manager):
    """Test applying multiple effects to the same deck"""
    # Apply multiple effects to deck A
    effect1 = TransitionEffect(type=EffectType.FILTER_SWEEP, intensity=0.5)
    effect2 = TransitionEffect(type=EffectType.ECHO, intensity=0.3)

    id1 = await effect_manager.apply_effect("A", effect1)
    id2 = await effect_manager.apply_effect("A", effect2)

    # Check deck has both effects
    deck_effects = effect_manager.get_deck_effects("A")
    assert len(deck_effects) == 2

    effect_types = [e.effect_type for e in deck_effects]
    assert EffectType.FILTER_SWEEP in effect_types
    assert EffectType.ECHO in effect_types


@pytest.mark.asyncio
async def test_clear_deck_effects(effect_manager):
    """Test clearing all effects from a deck"""
    # Apply multiple effects
    for effect_type in [EffectType.REVERB, EffectType.DELAY, EffectType.FLANGER]:
        effect = TransitionEffect(type=effect_type, intensity=0.5)
        await effect_manager.apply_effect("B", effect)

    # Clear deck effects
    count = await effect_manager.clear_deck_effects("B")
    assert count == 3

    # Verify deck has no effects
    deck_effects = effect_manager.get_deck_effects("B")
    assert len(deck_effects) == 0


@pytest.mark.asyncio
async def test_effect_with_duration(effect_manager):
    """Test effect with duration and automatic cleanup"""
    # Apply effect with short duration
    effect = TransitionEffect(
        type=EffectType.GATE,
        intensity=0.6,
        duration=0.5,  # 500ms
    )
    effect_id = await effect_manager.apply_effect("C", effect)

    # Check effect is active
    state = effect_manager.get_effect_state(effect_id)
    assert state.is_active is True

    # Wait for effect to expire
    await asyncio.sleep(0.6)

    # Check effect is removed
    state = effect_manager.get_effect_state(effect_id)
    assert state is None


@pytest.mark.asyncio
async def test_transition_effects_cleanup(effect_manager):
    """Test clearing effects associated with a transition"""
    transition_id = "test_transition_123"

    # Apply effects with transition ID
    for deck in ["A", "B"]:
        effect = TransitionEffect(type=EffectType.EQ_SWEEP, intensity=0.4)
        await effect_manager.apply_effect(deck, effect, transition_id=transition_id)

    # Clear transition effects
    count = await effect_manager.clear_transition_effects(transition_id)
    assert count == 2

    # Verify effects are removed
    all_effects = effect_manager.get_all_active_effects()
    assert len(all_effects) == 0


@pytest.mark.asyncio
async def test_effect_event_log(effect_manager):
    """Test effect event logging"""
    # Apply and modify effect
    effect = TransitionEffect(type=EffectType.SCRATCH, intensity=0.7)
    effect_id = await effect_manager.apply_effect("D", effect)

    # Update effect
    await effect_manager.update_effect(effect_id, parameters={"speed": 1.5})

    # Stop effect
    await effect_manager.stop_effect(effect_id)

    # Check event log
    events = effect_manager.get_event_log(effect_id=effect_id)
    assert len(events) == 3

    event_types = [e.event_type for e in events]
    assert "started" in event_types
    assert "updated" in event_types
    assert "stopped" in event_types


def test_filter_sweep_simulator():
    """Test filter sweep effect simulation"""
    simulator = FilterSweepSimulator()

    # Test initial parameters
    params = simulator.get_initial_parameters(intensity=0.5)
    assert params["frequency"] == 100.0
    assert params["resonance"] == 0.5  # 0.3 + (0.5 * 0.4)
    assert params["mix"] == 0.5

    # Test parameter automation over time
    params_at_0 = simulator.calculate_parameters_at_time(
        elapsed=0, duration=10, intensity=0.5
    )
    params_at_5 = simulator.calculate_parameters_at_time(
        elapsed=5, duration=10, intensity=0.5
    )
    params_at_10 = simulator.calculate_parameters_at_time(
        elapsed=10, duration=10, intensity=0.5
    )

    # Frequency should increase over time
    assert params_at_0["frequency"] < params_at_5["frequency"]
    assert params_at_5["frequency"] < params_at_10["frequency"]
    assert (
        abs(params_at_10["frequency"] - 8000.0) < 0.1
    )  # Target frequency (allow small float precision difference)


def test_echo_simulator():
    """Test echo effect simulation"""
    simulator = EchoSimulator()

    # Test initial parameters
    params = simulator.get_initial_parameters(intensity=0.8)
    assert params["delay_time"] == 250.0  # ms
    assert abs(params["feedback"] - 0.62) < 0.01  # 0.3 + (0.8 * 0.4)
    assert params["mix"] == 0.4  # 0.8 * 0.5

    # Test with custom target parameters
    initial = simulator.get_initial_parameters(intensity=0.5)
    target = initial.copy()
    target["feedback"] = 0.8

    params_end = simulator.calculate_parameters_at_time(
        elapsed=10,
        duration=10,
        intensity=0.5,
        initial_params=initial,
        target_params=target,
    )
    assert params_end["feedback"] == 0.8


def test_effect_simulator_factory():
    """Test creating simulators for all effect types"""
    for effect_type in EffectType:
        simulator = create_simulator(effect_type)
        assert simulator is not None
        assert simulator.effect_type == effect_type

        # Test each simulator can generate parameters
        params = simulator.get_initial_parameters(intensity=0.5)
        assert isinstance(params, dict)
        assert len(params) > 0


@pytest.mark.asyncio
async def test_process_tick(effect_manager):
    """Test manual tick processing for parameter updates"""
    # Apply multiple effects with automation
    effects = [
        (
            "A",
            TransitionEffect(type=EffectType.FILTER_SWEEP, intensity=0.6, duration=20),
        ),
        ("B", TransitionEffect(type=EffectType.FLANGER, intensity=0.4)),
        ("C", TransitionEffect(type=EffectType.EQ_SWEEP, intensity=0.5, duration=30)),
    ]

    for deck_id, effect in effects:
        await effect_manager.apply_effect(deck_id, effect)

    # Process tick at different times
    initial_params = effect_manager.process_tick(0)
    assert len(initial_params) == 3  # 3 decks with effects

    # Process tick after 5 seconds
    later_params = effect_manager.process_tick(5)

    # Verify parameters changed for effects with duration
    # Filter sweep on deck A should have higher frequency
    deck_a_params = next(
        p for p in later_params["A"] if p["effect_type"] == EffectType.FILTER_SWEEP
    )
    assert deck_a_params["parameters"]["frequency"] > 100.0  # Initial was 100

    # Flanger should have oscillating delay
    deck_b_params = next(
        p for p in later_params["B"] if p["effect_type"] == EffectType.FLANGER
    )
    assert "current_delay" in deck_b_params["parameters"]


@pytest.mark.asyncio
async def test_automation_curves(effect_manager):
    """Test different automation curve types"""
    # Apply effect with S-curve automation
    effect = TransitionEffect(type=EffectType.FILTER_SWEEP, intensity=0.5, duration=10)
    effect_id = await effect_manager.apply_effect("A", effect)

    # Update to use exponential curve
    await effect_manager.update_effect(
        effect_id, automation_curve=AutomationCurve.EXPONENTIAL
    )

    # Get the active effect
    active_effect = effect_manager._active_effects[effect_id]
    assert active_effect.automation_curve == AutomationCurve.EXPONENTIAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Effect Simulators - Simulate effect behavior without actual audio processing.
Each simulator calculates parameter values over time for testing and visualization.
"""

import math
from abc import ABC, abstractmethod
from typing import Dict, Optional
import numpy as np

from models.mix_models import EffectType
from models.effect_models import AutomationCurve


class EffectSimulator(ABC):
    """Base class for effect simulators"""

    def __init__(self, effect_type: EffectType):
        self.effect_type = effect_type

    @abstractmethod
    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Get initial parameter values based on intensity"""
        pass

    @abstractmethod
    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Calculate parameter values at a specific time"""
        pass

    def apply_automation_curve(self, progress: float, curve: AutomationCurve) -> float:
        """Apply automation curve to progress value (0-1)"""
        if curve == AutomationCurve.LINEAR:
            return progress
        elif curve == AutomationCurve.EXPONENTIAL:
            return progress**2
        elif curve == AutomationCurve.S_CURVE:
            # Smooth S-curve using cosine
            return 0.5 * (1 - math.cos(math.pi * progress))
        elif curve == AutomationCurve.LOGARITHMIC:
            # Logarithmic curve (fast start, slow end)
            return 1 - (1 - progress) ** 2
        return progress


class FilterSweepSimulator(EffectSimulator):
    """Simulates filter sweep effect (low/high-pass filter automation)"""

    def __init__(self):
        super().__init__(EffectType.FILTER_SWEEP)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Start with low frequency for sweep up"""
        return {
            "frequency": 100.0,  # Hz
            "resonance": 0.3 + (intensity * 0.4),  # 0.3-0.7 based on intensity
            "filter_type": 0.0,  # 0=low-pass, 1=high-pass
            "mix": intensity,  # Dry/wet mix
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.S_CURVE,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Sweep filter frequency over time"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        # Default target is high frequency
        if target_params is None:
            target_params = {
                "frequency": 8000.0,  # Sweep up to 8kHz
                "resonance": initial_params["resonance"],
                "filter_type": initial_params["filter_type"],
                "mix": initial_params["mix"],
            }

        # Calculate progress
        if duration:
            progress = min(1.0, elapsed / duration)
        else:
            # For infinite effects, use a slower sweep (30 second cycle)
            progress = (elapsed % 30) / 30

        # Apply automation curve
        curve_progress = self.apply_automation_curve(progress, automation_curve)

        # Interpolate frequency logarithmically for natural sound
        start_freq = initial_params["frequency"]
        end_freq = target_params["frequency"]
        log_start = math.log10(start_freq)
        log_end = math.log10(end_freq)
        log_current = log_start + (log_end - log_start) * curve_progress
        current_freq = 10**log_current

        return {
            "frequency": current_freq,
            "resonance": initial_params["resonance"],
            "filter_type": initial_params["filter_type"],
            "mix": initial_params["mix"],
        }


class EchoSimulator(EffectSimulator):
    """Simulates echo/delay effect"""

    def __init__(self):
        super().__init__(EffectType.ECHO)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Echo parameters based on intensity"""
        return {
            "delay_time": 250.0,  # ms (1/4 note at 120 BPM)
            "feedback": 0.3 + (intensity * 0.4),  # 0.3-0.7
            "mix": intensity * 0.5,  # Keep echo subtle
            "filter_freq": 4000.0,  # High-cut filter
            "sync": 1.0,  # Beat sync enabled
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Echo can increase feedback/mix over time"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        if target_params is None:
            # Default: increase feedback and mix slightly
            target_params = initial_params.copy()
            target_params["feedback"] = min(0.8, initial_params["feedback"] + 0.2)
            target_params["mix"] = min(0.7, initial_params["mix"] + 0.2)

        if duration:
            progress = min(1.0, elapsed / duration)
        else:
            # Static effect
            return initial_params

        curve_progress = self.apply_automation_curve(progress, automation_curve)

        # Interpolate parameters
        current_params = {}
        for key in initial_params:
            start_val = initial_params[key]
            end_val = target_params.get(key, start_val)
            current_params[key] = start_val + (end_val - start_val) * curve_progress

        return current_params


class ReverbSimulator(EffectSimulator):
    """Simulates reverb effect"""

    def __init__(self):
        super().__init__(EffectType.REVERB)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Reverb room size and mix based on intensity"""
        return {
            "room_size": 0.3 + (intensity * 0.5),  # 0.3-0.8
            "damping": 0.5,
            "wet_level": intensity * 0.4,  # Keep reverb subtle
            "dry_level": 1.0,
            "pre_delay": 20.0,  # ms
            "width": 0.8,
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Reverb can increase room size/wet level over time"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        if duration and target_params:
            progress = min(1.0, elapsed / duration)
            curve_progress = self.apply_automation_curve(progress, automation_curve)

            current_params = {}
            for key in initial_params:
                start_val = initial_params[key]
                end_val = target_params.get(key, start_val)
                current_params[key] = start_val + (end_val - start_val) * curve_progress
            return current_params

        return initial_params


class DelaySimulator(EffectSimulator):
    """Simulates delay effect (longer than echo)"""

    def __init__(self):
        super().__init__(EffectType.DELAY)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Delay with longer times than echo"""
        return {
            "delay_time": 500.0,  # ms (1/2 note at 120 BPM)
            "feedback": 0.4 + (intensity * 0.3),  # 0.4-0.7
            "mix": intensity * 0.4,
            "ping_pong": 1.0
            if intensity > 0.6
            else 0.0,  # Stereo delay for higher intensity
            "filter_freq": 3000.0,
            "sync": 1.0,
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Similar to echo but with different timing"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        if duration and target_params:
            progress = min(1.0, elapsed / duration)
            curve_progress = self.apply_automation_curve(progress, automation_curve)

            current_params = {}
            for key in initial_params:
                start_val = initial_params[key]
                end_val = target_params.get(key, start_val)
                current_params[key] = start_val + (end_val - start_val) * curve_progress
            return current_params

        return initial_params


class GateSimulator(EffectSimulator):
    """Simulates gate effect (rhythmic volume cuts)"""

    def __init__(self):
        super().__init__(EffectType.GATE)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Gate pattern and depth based on intensity"""
        return {
            "pattern": 1.0,  # Pattern index (1-8)
            "depth": intensity,  # How much to cut volume
            "rate": 16.0,  # 16th notes
            "smooth": 0.1,  # Attack/release smoothing
            "sync": 1.0,  # Beat sync
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Gate pattern can change over time"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        # Gate is typically static, but pattern could change
        current_params = initial_params.copy()

        # Add rhythmic variation to gate state
        rate = current_params["rate"]
        beat_time = 60.0 / 120.0 / (rate / 4.0)  # Assuming 120 BPM
        gate_position = (elapsed % beat_time) / beat_time
        current_params["gate_open"] = 1.0 if gate_position < 0.5 else 0.0

        return current_params


class FlangerSimulator(EffectSimulator):
    """Simulates flanger effect (short modulated delay)"""

    def __init__(self):
        super().__init__(EffectType.FLANGER)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Flanger with LFO modulation"""
        return {
            "delay": 5.0,  # ms (base delay)
            "depth": intensity * 3.0,  # Modulation depth in ms
            "rate": 0.5,  # Hz (LFO rate)
            "feedback": 0.3 + (intensity * 0.4),
            "mix": intensity * 0.6,
            "phase": 0.0,  # Starting phase
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Flanger with LFO modulation of delay time"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        current_params = initial_params.copy()

        # Calculate LFO position
        lfo_phase = (elapsed * current_params["rate"] * 2 * math.pi) % (2 * math.pi)
        lfo_value = math.sin(lfo_phase)

        # Modulate delay time
        base_delay = current_params["delay"]
        depth = current_params["depth"]
        current_params["current_delay"] = base_delay + (depth * lfo_value)
        current_params["lfo_position"] = lfo_value

        return current_params


class EQSweepSimulator(EffectSimulator):
    """Simulates parametric EQ sweep"""

    def __init__(self):
        super().__init__(EffectType.EQ_SWEEP)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Parametric EQ starting position"""
        return {
            "frequency": 200.0,  # Hz
            "gain": intensity * 12.0,  # dB (0-12)
            "q_factor": 2.0,  # Bandwidth
            "type": 0.0,  # 0=bell, 1=shelf
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.S_CURVE,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Sweep EQ frequency across spectrum"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        if target_params is None:
            target_params = initial_params.copy()
            target_params["frequency"] = 4000.0  # Sweep to 4kHz

        if duration:
            progress = min(1.0, elapsed / duration)
        else:
            # Continuous sweep over 20 seconds
            progress = (elapsed % 20) / 20

        curve_progress = self.apply_automation_curve(progress, automation_curve)

        # Logarithmic frequency sweep
        start_freq = initial_params["frequency"]
        end_freq = target_params["frequency"]
        log_start = math.log10(start_freq)
        log_end = math.log10(end_freq)
        log_current = log_start + (log_end - log_start) * curve_progress

        current_params = initial_params.copy()
        current_params["frequency"] = 10**log_current

        return current_params


class ScratchSimulator(EffectSimulator):
    """Simulates vinyl scratch effect"""

    def __init__(self):
        super().__init__(EffectType.SCRATCH)

    def get_initial_parameters(self, intensity: float) -> Dict[str, float]:
        """Scratch pattern parameters"""
        return {
            "speed": 0.0,  # Playback speed multiplier
            "pattern": 1.0,  # Scratch pattern type
            "depth": intensity,  # How extreme the scratches
            "crossfader": 1.0,  # Simulated fader position
            "momentum": 0.5,  # Vinyl momentum simulation
        }

    def calculate_parameters_at_time(
        self,
        elapsed: float,
        duration: Optional[float],
        intensity: float,
        automation_curve: AutomationCurve = AutomationCurve.LINEAR,
        initial_params: Optional[Dict[str, float]] = None,
        target_params: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Simulate scratch movements"""
        if initial_params is None:
            initial_params = self.get_initial_parameters(intensity)

        current_params = initial_params.copy()

        # Simulate different scratch patterns
        pattern = int(current_params["pattern"])

        if pattern == 1:  # Baby scratch
            # Simple back and forth
            scratch_pos = math.sin(elapsed * 8) * current_params["depth"]
            current_params["speed"] = 1.0 + scratch_pos
            current_params["crossfader"] = 1.0

        elif pattern == 2:  # Transform scratch
            # With crossfader cuts
            scratch_pos = math.sin(elapsed * 6) * current_params["depth"]
            current_params["speed"] = 1.0 + scratch_pos
            # Cut on the backward motion
            current_params["crossfader"] = 1.0 if scratch_pos > 0 else 0.0

        elif pattern == 3:  # Chirp scratch
            # Fast forward, slow back
            phase = (elapsed * 4) % (2 * math.pi)
            if phase < math.pi:
                # Forward (fast)
                scratch_pos = math.sin(phase * 2) * current_params["depth"]
            else:
                # Back (slow)
                scratch_pos = (
                    -math.sin((phase - math.pi) * 0.5) * current_params["depth"]
                )
            current_params["speed"] = 1.0 + scratch_pos
            current_params["crossfader"] = 1.0

        return current_params


# Factory to create simulators
def create_simulator(effect_type: EffectType) -> EffectSimulator:
    """Create appropriate simulator for effect type"""
    simulators = {
        EffectType.FILTER_SWEEP: FilterSweepSimulator,
        EffectType.ECHO: EchoSimulator,
        EffectType.REVERB: ReverbSimulator,
        EffectType.DELAY: DelaySimulator,
        EffectType.GATE: GateSimulator,
        EffectType.FLANGER: FlangerSimulator,
        EffectType.EQ_SWEEP: EQSweepSimulator,
        EffectType.SCRATCH: ScratchSimulator,
    }

    simulator_class = simulators.get(effect_type)
    if not simulator_class:
        raise ValueError(f"No simulator for effect type: {effect_type}")

    return simulator_class()

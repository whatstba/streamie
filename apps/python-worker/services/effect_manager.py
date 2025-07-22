"""
Effect Manager - Manages effect lifecycle and state for all decks.
Simulates effect execution without actual audio processing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
import uuid

from models.effect_models import (
    ActiveEffect,
    EffectState,
    DeckEffectChain,
    EffectEvent,
    AutomationCurve,
)
from models.mix_models import TransitionEffect, EffectType
from services.effect_simulators import create_simulator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🎨 [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class EffectManager:
    """Manages effects across all decks with simulation capabilities"""

    def __init__(self):
        # Effect chains per deck
        self._deck_chains: Dict[str, DeckEffectChain] = {
            "A": DeckEffectChain(deck_id="A"),
            "B": DeckEffectChain(deck_id="B"),
            "C": DeckEffectChain(deck_id="C"),
            "D": DeckEffectChain(deck_id="D"),
        }

        # Active effects by ID for quick lookup
        self._active_effects: Dict[str, ActiveEffect] = {}

        # Effect simulators
        self._simulators = {}

        # Background tasks for automation
        self._automation_tasks: Dict[str, asyncio.Task] = {}

        # Event log for testing/debugging
        self._event_log: List[EffectEvent] = []

        # Update interval for automation
        self._update_interval = 0.1  # 100ms

        logger.info("🎨 EffectManager initialized")

    async def apply_effect(
        self,
        deck_id: str,
        effect: TransitionEffect,
        transition_id: Optional[str] = None,
    ) -> str:
        """Apply an effect to a deck and return effect ID"""
        if deck_id not in self._deck_chains:
            raise ValueError(f"Invalid deck ID: {deck_id}")

        # Create active effect instance
        active_effect = ActiveEffect(
            deck_id=deck_id,
            effect_type=effect.type,
            intensity=effect.intensity,
            duration=effect.duration,
            transition_id=transition_id,
        )

        # Get simulator and initial parameters
        simulator = create_simulator(effect.type)
        initial_params = simulator.get_initial_parameters(effect.intensity)

        # Override with any custom parameters
        if effect.parameters:
            initial_params.update(effect.parameters)

        active_effect.parameters = initial_params
        active_effect.initial_parameters = initial_params.copy()

        # Add to deck chain and active effects
        self._deck_chains[deck_id].add_effect(active_effect)
        self._active_effects[active_effect.id] = active_effect

        # Log event
        self._log_event(
            EffectEvent(
                effect_id=active_effect.id,
                deck_id=deck_id,
                event_type="started",
                parameters=initial_params,
                metadata={
                    "effect_type": effect.type,
                    "intensity": effect.intensity,
                    "duration": effect.duration,
                },
            )
        )

        logger.info(
            f"🎨 Applied {effect.type} to deck {deck_id} "
            f"(ID: {active_effect.id[:8]}..., intensity: {effect.intensity})"
        )

        # Start automation task if effect has duration
        if effect.duration:
            task = asyncio.create_task(self._run_effect_automation(active_effect.id))
            self._automation_tasks[active_effect.id] = task

        return active_effect.id

    async def update_effect(
        self,
        effect_id: str,
        parameters: Optional[Dict[str, float]] = None,
        target_parameters: Optional[Dict[str, float]] = None,
        automation_curve: Optional[AutomationCurve] = None,
    ) -> bool:
        """Update effect parameters or automation settings"""
        effect = self._active_effects.get(effect_id)
        if not effect or not effect.is_active:
            return False

        # Update current parameters
        if parameters:
            effect.parameters.update(parameters)
            self._log_event(
                EffectEvent(
                    effect_id=effect_id,
                    deck_id=effect.deck_id,
                    event_type="updated",
                    parameters=parameters,
                )
            )

        # Update automation target
        if target_parameters:
            effect.target_parameters = target_parameters

        # Update automation curve
        if automation_curve:
            effect.automation_curve = automation_curve

        logger.info(f"🎨 Updated effect {effect_id[:8]}...")
        return True

    async def stop_effect(self, effect_id: str) -> bool:
        """Stop and remove an effect"""
        effect = self._active_effects.get(effect_id)
        if not effect:
            return False

        # Mark as inactive
        effect.is_active = False
        effect.end_time = datetime.utcnow()

        # Cancel automation task
        if effect_id in self._automation_tasks:
            self._automation_tasks[effect_id].cancel()
            del self._automation_tasks[effect_id]

        # Remove from deck chain
        self._deck_chains[effect.deck_id].remove_effect(effect_id)

        # Remove from active effects
        del self._active_effects[effect_id]

        # Log event
        self._log_event(
            EffectEvent(
                effect_id=effect_id,
                deck_id=effect.deck_id,
                event_type="stopped",
                metadata={"duration": effect.get_elapsed_time()},
            )
        )

        logger.info(
            f"🎨 Stopped {effect.effect_type} on deck {effect.deck_id} "
            f"(ID: {effect_id[:8]}...)"
        )

        return True

    async def bypass_effect(self, effect_id: str, bypassed: bool = True) -> bool:
        """Bypass or un-bypass an effect"""
        effect = self._active_effects.get(effect_id)
        if not effect:
            return False

        effect.is_bypassed = bypassed

        self._log_event(
            EffectEvent(
                effect_id=effect_id,
                deck_id=effect.deck_id,
                event_type="bypassed" if bypassed else "resumed",
            )
        )

        logger.info(
            f"🎨 {'Bypassed' if bypassed else 'Resumed'} effect {effect_id[:8]}..."
        )

        return True

    def get_deck_effects(self, deck_id: str) -> List[ActiveEffect]:
        """Get all active effects for a deck"""
        if deck_id not in self._deck_chains:
            return []

        return self._deck_chains[deck_id].get_active_effects()

    def get_effect_state(self, effect_id: str) -> Optional[EffectState]:
        """Get current state of an effect"""
        effect = self._active_effects.get(effect_id)
        if not effect:
            return None

        return EffectState.from_active_effect(effect)

    def get_all_active_effects(self) -> List[EffectState]:
        """Get all active effects across all decks"""
        states = []
        for effect in self._active_effects.values():
            if effect.is_active:
                states.append(EffectState.from_active_effect(effect))
        return states

    async def clear_deck_effects(self, deck_id: str) -> int:
        """Clear all effects from a deck"""
        if deck_id not in self._deck_chains:
            return 0

        chain = self._deck_chains[deck_id]
        effect_ids = [e.id for e in chain.effects]

        count = 0
        for effect_id in effect_ids:
            if await self.stop_effect(effect_id):
                count += 1

        logger.info(f"🎨 Cleared {count} effects from deck {deck_id}")
        return count

    async def clear_transition_effects(self, transition_id: str) -> int:
        """Clear all effects associated with a transition"""
        effects_to_stop = [
            effect_id
            for effect_id, effect in self._active_effects.items()
            if effect.transition_id == transition_id
        ]

        count = 0
        for effect_id in effects_to_stop:
            if await self.stop_effect(effect_id):
                count += 1

        logger.info(f"🎨 Cleared {count} effects from transition {transition_id}")
        return count

    def process_tick(self, current_time: float) -> Dict[str, List[Dict[str, float]]]:
        """Simulate parameter updates for all active effects (called externally)"""
        deck_parameters = {}

        for deck_id, chain in self._deck_chains.items():
            deck_params = []

            for effect in chain.get_active_effects():
                # Get simulator
                simulator = create_simulator(effect.effect_type)

                # Calculate current parameters
                elapsed = effect.get_elapsed_time()
                params = simulator.calculate_parameters_at_time(
                    elapsed=elapsed,
                    duration=effect.duration,
                    intensity=effect.intensity,
                    automation_curve=effect.automation_curve,
                    initial_params=effect.initial_parameters,
                    target_params=effect.target_parameters,
                )

                # Update effect parameters
                effect.parameters = params

                deck_params.append(
                    {
                        "effect_id": effect.id,
                        "effect_type": effect.effect_type,
                        "parameters": params,
                    }
                )

            if deck_params:
                deck_parameters[deck_id] = deck_params

        return deck_parameters

    async def _run_effect_automation(self, effect_id: str):
        """Background task to automate effect parameters"""
        try:
            while effect_id in self._active_effects:
                effect = self._active_effects.get(effect_id)
                if not effect or not effect.is_active:
                    break

                # Check if effect duration expired
                if effect.duration and effect.get_elapsed_time() >= effect.duration:
                    await self.stop_effect(effect_id)
                    break

                # Get simulator and update parameters
                simulator = create_simulator(effect.effect_type)
                params = simulator.calculate_parameters_at_time(
                    elapsed=effect.get_elapsed_time(),
                    duration=effect.duration,
                    intensity=effect.intensity,
                    automation_curve=effect.automation_curve,
                    initial_params=effect.initial_parameters,
                    target_params=effect.target_parameters,
                )

                # Update effect parameters
                effect.parameters = params

                # Wait for next update
                await asyncio.sleep(self._update_interval)

        except asyncio.CancelledError:
            logger.info(f"🎨 Automation cancelled for effect {effect_id[:8]}...")
        except Exception as e:
            logger.error(f"🎨 Error in effect automation: {e}")

    def _log_event(self, event: EffectEvent):
        """Log an effect event"""
        self._event_log.append(event)

        # Keep only last 1000 events
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]

    def get_event_log(
        self,
        deck_id: Optional[str] = None,
        effect_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EffectEvent]:
        """Get filtered event log"""
        events = self._event_log

        if deck_id:
            events = [e for e in events if e.deck_id == deck_id]

        if effect_id:
            events = [e for e in events if e.effect_id == effect_id]

        return events[-limit:]

    async def shutdown(self):
        """Clean shutdown of all effects"""
        logger.info("🎨 Shutting down EffectManager...")

        # Cancel all automation tasks
        for task in self._automation_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._automation_tasks:
            await asyncio.gather(
                *self._automation_tasks.values(), return_exceptions=True
            )

        # Clear all effects
        for deck_id in self._deck_chains:
            await self.clear_deck_effects(deck_id)

        logger.info("🎨 EffectManager shutdown complete")

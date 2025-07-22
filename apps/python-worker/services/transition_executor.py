"""
Transition Executor Service - Executes mix plans with precise timing and coordination.
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any, Set
from datetime import datetime, timedelta
import numpy as np

from models.mix_models import (
    MixDecision,
    TransitionState,
    TransitionEffect,
    EQAdjustment,
)
from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "🎚️ [%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class TransitionExecutor:
    """Executes mix transitions with precise timing and smooth parameter changes."""

    def __init__(
        self,
        deck_manager: DeckManager,
        mixer_manager: MixerManager,
        effect_manager=None,
    ):
        self.deck_manager = deck_manager
        self.mixer_manager = mixer_manager
        self.effect_manager = effect_manager
        self.active_transition: Optional[TransitionState] = None
        self._transition_task: Optional[asyncio.Task] = None
        self._update_callbacks: list[Callable] = []
        self._active_effect_ids: Set[str] = set()

    def add_update_callback(self, callback: Callable[[TransitionState], None]):
        """Add a callback for transition state updates."""
        self._update_callbacks.append(callback)

    def remove_update_callback(self, callback: Callable[[TransitionState], None]):
        """Remove a callback."""
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    async def execute_transition(self, mix_decision: MixDecision) -> bool:
        """Execute a mix transition plan."""
        if self.active_transition and self.active_transition.is_active:
            logger.warning("🎚️ Transition already in progress, cannot start new one")
            return False

        logger.info(
            f"🎚️ Starting {mix_decision.action} transition from "
            f"deck {mix_decision.source_deck} to {mix_decision.target_deck}"
        )

        # Create transition state
        self.active_transition = TransitionState(
            mix_decision=mix_decision,
            started_at=datetime.utcnow(),
            progress=0.0,
            is_active=True,
            current_phase="preparing",
        )

        # Start transition task
        self._transition_task = asyncio.create_task(
            self._execute_transition_async(mix_decision)
        )

        return True

    async def _execute_transition_async(self, mix_decision: MixDecision):
        """Async execution of transition."""
        try:
            # Phase 1: Preparation
            await self._prepare_transition(mix_decision)

            # Phase 2: Execute main transition
            await self._execute_main_transition(mix_decision)

            # Phase 3: Complete transition
            await self._complete_transition(mix_decision)

        except asyncio.CancelledError:
            logger.info("🎚️ Transition cancelled")
            if self.active_transition:
                self.active_transition.is_active = False
        except Exception as e:
            logger.error(f"🎚️ Transition failed: {e}")
            if self.active_transition:
                self.active_transition.is_active = False
        finally:
            # Cleanup
            if self.active_transition:
                self.active_transition.is_active = False
                await self._notify_update()

    async def _prepare_transition(self, mix_decision: MixDecision):
        """Prepare decks for transition."""
        logger.info("🎚️ Phase 1: Preparing transition")

        if self.active_transition:
            self.active_transition.current_phase = "preparing"
            await self._notify_update()

        # Ensure target deck is cued to the right position
        if mix_decision.transition_point:
            target_position = mix_decision.transition_point.deck_b_time
            await self.deck_manager.set_position(
                mix_decision.target_deck, target_position
            )

        # Start target deck if not playing
        target_state = await self.deck_manager.get_deck_state(mix_decision.target_deck)
        if target_state and not target_state.get("is_playing"):
            await self.deck_manager.play_pause(mix_decision.target_deck)

        # Apply initial EQ adjustments
        for deck_id, eq_adj in mix_decision.eq_adjustments.items():
            if deck_id == mix_decision.target_deck:
                # Start with reduced highs/lows for incoming track
                await self.deck_manager.set_eq(
                    deck_id,
                    low=eq_adj.low * 0.5,
                    mid=eq_adj.mid,
                    high=eq_adj.high * 0.5,
                )

    async def _execute_main_transition(self, mix_decision: MixDecision):
        """Execute the main transition with smooth parameter changes."""
        logger.info(f"🎚️ Phase 2: Executing {mix_decision.duration}s transition")

        if self.active_transition:
            self.active_transition.current_phase = "executing"

        start_time = datetime.utcnow()
        duration = mix_decision.duration
        update_interval = 0.1  # Update every 100ms for smooth transitions

        # Get initial crossfader position
        mixer_state = await self.mixer_manager.get_mixer_state()
        initial_crossfader = mixer_state.get("crossfader", 0.0)

        # Determine target crossfader position
        if mix_decision.source_deck in ["A", "C"]:
            target_crossfader = 1.0 if mix_decision.target_deck in ["B", "D"] else 0.0
        else:
            target_crossfader = -1.0 if mix_decision.target_deck in ["A", "C"] else 0.0

        # Effect scheduling
        effects_started = set()

        while True:
            # Calculate progress
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            progress = min(elapsed / duration, 1.0)

            if self.active_transition:
                self.active_transition.progress = progress

            # Update crossfader with curve
            if mix_decision.action in ["smooth_blend", "beatmatch_blend"]:
                # S-curve for smooth transitions
                curve_progress = self._apply_s_curve(progress)
                crossfader_pos = (
                    initial_crossfader
                    + (target_crossfader - initial_crossfader) * curve_progress
                )
                await self.mixer_manager.set_crossfader(crossfader_pos)
            elif mix_decision.action == "quick_cut":
                # Quick cut at 50% progress
                if progress >= 0.5 and initial_crossfader != target_crossfader:
                    await self.mixer_manager.set_crossfader(target_crossfader)
                    initial_crossfader = target_crossfader  # Prevent multiple cuts

            # Apply EQ curves
            await self._apply_eq_curves(mix_decision, progress)

            # Start effects at scheduled times
            for effect in mix_decision.effects:
                effect_key = f"{effect.type}_{effect.start_at}"
                if effect_key not in effects_started and elapsed >= effect.start_at:
                    await self._start_effect(effect, mix_decision)
                    effects_started.add(effect_key)
                    if self.active_transition:
                        self.active_transition.effects_applied.append(effect.type)

            # Update state
            await self._notify_update()

            # Check if complete
            if progress >= 1.0:
                break

            # Wait for next update
            await asyncio.sleep(update_interval)

    async def _complete_transition(self, mix_decision: MixDecision):
        """Complete the transition and clean up."""
        logger.info("🎚️ Phase 3: Completing transition")

        if self.active_transition:
            self.active_transition.current_phase = "completing"
            self.active_transition.progress = 1.0
            await self._notify_update()

        # Stop source deck
        await self.deck_manager.stop(mix_decision.source_deck)

        # Reset EQ on target deck to neutral
        await self.deck_manager.set_eq(
            mix_decision.target_deck, low=0.0, mid=0.0, high=0.0
        )

        # Clear any effects
        if self.effect_manager and self._active_effect_ids:
            logger.info(f"🎚️ Cleaning up {len(self._active_effect_ids)} effects")
            for effect_id in list(self._active_effect_ids):
                await self.effect_manager.stop_effect(effect_id)
            self._active_effect_ids.clear()

        logger.info(
            f"🎚️ Transition complete: {mix_decision.source_deck} → {mix_decision.target_deck}"
        )

    def _apply_s_curve(self, x: float) -> float:
        """Apply S-curve for smooth transitions."""
        # Smooth S-curve using cosine
        return 0.5 * (1 - np.cos(np.pi * x))

    async def _apply_eq_curves(self, mix_decision: MixDecision, progress: float):
        """Apply EQ adjustments over time."""
        for deck_id, eq_adj in mix_decision.eq_adjustments.items():
            if deck_id == mix_decision.source_deck:
                # Fade out source
                factor = 1.0 - progress
                await self.deck_manager.set_eq(
                    deck_id,
                    low=eq_adj.low * factor,
                    mid=eq_adj.mid,
                    high=eq_adj.high * factor,
                )
            elif deck_id == mix_decision.target_deck:
                # Fade in target with S-curve
                factor = self._apply_s_curve(progress)
                await self.deck_manager.set_eq(
                    deck_id,
                    low=eq_adj.low * factor,
                    mid=eq_adj.mid,
                    high=eq_adj.high * factor,
                )

    async def _start_effect(self, effect: TransitionEffect, mix_decision: MixDecision):
        """Start an effect using the EffectManager."""
        logger.info(f"🎚️ Starting effect: {effect.type} at intensity {effect.intensity}")

        if self.effect_manager:
            # Determine which deck(s) to apply effect to
            # For most transitions, effects are applied to the source deck
            deck_id = mix_decision.source_deck

            # Some effects might be applied to the target deck
            if (
                effect.type in ["reverb", "delay"]
                and effect.start_at > mix_decision.duration * 0.5
            ):
                deck_id = mix_decision.target_deck

            try:
                # Apply effect via EffectManager
                effect_id = await self.effect_manager.apply_effect(
                    deck_id=deck_id,
                    effect=effect,
                    transition_id=self.active_transition.mix_decision.source_deck
                    + "_to_"
                    + self.active_transition.mix_decision.target_deck,
                )

                # Track effect ID for cleanup
                self._active_effect_ids.add(effect_id)

                logger.info(
                    f"🎚️ Effect {effect.type} started on deck {deck_id} (ID: {effect_id[:8]}...)"
                )
            except Exception as e:
                logger.error(f"🎚️ Failed to start effect {effect.type}: {e}")
        else:
            logger.warning("🎚️ EffectManager not available, effect not started")

    async def _notify_update(self):
        """Notify callbacks of state update."""
        if self.active_transition:
            for callback in self._update_callbacks:
                try:
                    await asyncio.create_task(
                        asyncio.coroutine(callback)(self.active_transition)
                    ) if asyncio.iscoroutinefunction(callback) else callback(
                        self.active_transition
                    )
                except Exception as e:
                    logger.error(f"Callback error: {e}")

    async def cancel_transition(self):
        """Cancel the active transition."""
        if self._transition_task and not self._transition_task.done():
            logger.info("🎚️ Cancelling active transition")
            self._transition_task.cancel()
            await asyncio.gather(self._transition_task, return_exceptions=True)

    def get_transition_state(self) -> Optional[TransitionState]:
        """Get current transition state."""
        return (
            self.active_transition
            if self.active_transition and self.active_transition.is_active
            else None
        )

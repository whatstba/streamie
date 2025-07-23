"""
Service Manager - Singleton management for background services
"""

import asyncio
import logging
from typing import Optional
import os

from services.analysis_service import AnalysisService
from services.deck_manager import DeckManager
from services.mixer_manager import MixerManager
from services.transition_executor import TransitionExecutor
from services.effect_manager import EffectManager
from services.audio_engine import AudioEngine
from agents.mix_coordinator_agent import MixCoordinatorAgent
from models.database import init_db

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages singleton instances of background services"""

    _instance = None
    _analysis_service: Optional[AnalysisService] = None
    _deck_manager: Optional[DeckManager] = None
    _mixer_manager: Optional[MixerManager] = None
    _effect_manager: Optional[EffectManager] = None
    _audio_engine: Optional[AudioEngine] = None
    _mix_coordinator: Optional[MixCoordinatorAgent] = None
    _transition_executor: Optional[TransitionExecutor] = None
    _engine = None
    _initialization_started = False
    _initialization_complete = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
        return cls._instance

    async def _get_engine(self):
        """Get or create database engine"""
        if self._engine is None:
            self._engine = await init_db()
        return self._engine

    async def initialize_all_services(self):
        """Initialize all services in the correct order to avoid circular dependencies"""
        if self._initialization_complete:
            return

        if self._initialization_started:
            # Wait for initialization to complete
            while not self._initialization_complete:
                await asyncio.sleep(0.1)
            return

        self._initialization_started = True
        logger.info("🔍 Starting service initialization...")

        try:
            # 1. Initialize database engine
            self._engine = await init_db()
            logger.info("✅ Database engine initialized")

            # 2. Initialize analysis service
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "tracks.db"
            )
            self._analysis_service = AnalysisService(db_path)
            await self._analysis_service.start()
            logger.info("✅ Analysis service started")

            # 3. Initialize deck and mixer managers
            self._deck_manager = DeckManager(self._engine)
            self._mixer_manager = MixerManager(self._engine)

            # 4. Set cross-references
            self._deck_manager.mixer_manager = self._mixer_manager
            self._deck_manager.analysis_service = self._analysis_service
            logger.info("✅ Deck and mixer managers initialized")

            # 5. Initialize effect manager
            self._effect_manager = EffectManager()
            logger.info("✅ Effect manager initialized")

            # 6. Initialize audio engine
            try:
                self._audio_engine = AudioEngine(
                    deck_manager=self._deck_manager,
                    mixer_manager=self._mixer_manager,
                    effect_manager=self._effect_manager,
                )
                await asyncio.wait_for(self._audio_engine.start(), timeout=5.0)
                logger.info("✅ Audio engine initialized and started")
            except asyncio.TimeoutError:
                logger.error(
                    "⚠️ Audio engine start timed out - continuing without audio"
                )
                self._audio_engine = None
            except Exception as e:
                logger.error(f"⚠️ Failed to start audio engine: {e}")
                self._audio_engine = None

            # 7. Set audio engine reference in deck manager
            self._deck_manager.set_audio_engine(self._audio_engine)

            # 8. Initialize mix coordinator
            self._mix_coordinator = MixCoordinatorAgent(
                deck_manager=self._deck_manager,
                mixer_manager=self._mixer_manager,
                analysis_service=self._analysis_service,
            )
            logger.info("✅ Mix coordinator initialized")

            # 9. Initialize transition executor with effect manager
            self._transition_executor = TransitionExecutor(
                deck_manager=self._deck_manager,
                mixer_manager=self._mixer_manager,
                effect_manager=self._effect_manager,
            )
            logger.info("✅ Transition executor initialized")

            self._initialization_complete = True
            logger.info("✅ All services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            self._initialization_started = False
            raise

    async def get_analysis_service(self) -> AnalysisService:
        """Get or create the singleton AnalysisService instance"""
        await self.initialize_all_services()
        return self._analysis_service

    async def get_deck_manager(self) -> DeckManager:
        """Get or create the singleton DeckManager instance"""
        await self.initialize_all_services()
        return self._deck_manager

    async def get_mixer_manager(self) -> MixerManager:
        """Get or create the singleton MixerManager instance"""
        await self.initialize_all_services()
        return self._mixer_manager

    async def get_mix_coordinator(self) -> MixCoordinatorAgent:
        """Get or create the singleton MixCoordinatorAgent instance"""
        await self.initialize_all_services()
        return self._mix_coordinator

    async def get_transition_executor(self) -> TransitionExecutor:
        """Get or create the singleton TransitionExecutor instance"""
        await self.initialize_all_services()
        return self._transition_executor

    async def get_effect_manager(self) -> EffectManager:
        """Get or create the singleton EffectManager instance"""
        await self.initialize_all_services()
        return self._effect_manager

    async def get_audio_engine(self) -> AudioEngine:
        """Get or create the singleton AudioEngine instance"""
        await self.initialize_all_services()
        return self._audio_engine

    async def shutdown(self):
        """Shutdown all managed services"""
        logger.info("🛑 Shutting down services...")

        # Cancel any active transitions first
        if self._transition_executor is not None:
            await self._transition_executor.cancel_transition()

        # Shutdown audio engine first (it uses other services)
        if self._audio_engine is not None:
            await self._audio_engine.stop()
            self._audio_engine = None
            logger.info("✅ Audio engine stopped")

        # Shutdown effect manager
        if self._effect_manager is not None:
            await self._effect_manager.shutdown()
            self._effect_manager = None
            logger.info("✅ Effect manager stopped")

        if self._analysis_service is not None:
            await self._analysis_service.stop()
            self._analysis_service = None
            logger.info("✅ Analysis service stopped")

        # Reset other services
        self._deck_manager = None
        self._mixer_manager = None
        self._mix_coordinator = None
        self._transition_executor = None
        self._initialization_complete = False
        self._initialization_started = False

        logger.info("✅ All services shut down")


# Global instance
service_manager = ServiceManager()

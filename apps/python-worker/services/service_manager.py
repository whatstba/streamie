"""
Service Manager - Singleton management for background services
"""

import asyncio
import logging
from typing import Optional
import os

from services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages singleton instances of background services"""
    
    _instance = None
    _analysis_service: Optional[AnalysisService] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
        return cls._instance
    
    async def get_analysis_service(self) -> AnalysisService:
        """Get or create the singleton AnalysisService instance"""
        async with self._lock:
            if self._analysis_service is None:
                db_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    "tracks.db"
                )
                self._analysis_service = AnalysisService(db_path)
                await self._analysis_service.start()
                logger.info("✅ Analysis service started")
            
            return self._analysis_service
    
    async def shutdown(self):
        """Shutdown all managed services"""
        logger.info("🛑 Shutting down services...")
        
        async with self._lock:
            if self._analysis_service is not None:
                await self._analysis_service.stop()
                self._analysis_service = None
                logger.info("✅ Analysis service stopped")
        
        logger.info("✅ All services shut down")


# Global instance
service_manager = ServiceManager()
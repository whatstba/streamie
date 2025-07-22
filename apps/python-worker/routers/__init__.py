# Routers module for FastAPI
from .ai_router import router as ai_router
from .deck_router import router as deck_router

__all__ = ["ai_router", "deck_router"]

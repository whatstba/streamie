"""Test deck database setup"""
import asyncio
from models import init_db, get_session
from models.deck import Deck

async def test_deck_db():
    engine = await init_db()
    
    async with get_session(engine) as session:
        # Check if deck A exists
        deck_a = await session.get(Deck, 'A')
        print(f"Deck A exists: {deck_a is not None}")
        
        if deck_a:
            print(f"Deck A status: {deck_a.status}")
            print(f"Deck A id: {deck_a.id}")
            print(f"Deck A volume: {deck_a.volume}")
        else:
            print("Deck A not found in database!")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_deck_db())
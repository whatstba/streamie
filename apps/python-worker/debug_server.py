"""Debug server to test deck endpoints directly"""

import asyncio
from models import init_db
from services.deck_manager import DeckManager


async def debug_deck_manager():
    engine = await init_db()
    deck_manager = DeckManager(engine)

    print("Testing DeckManager directly...")
    print("=" * 50)

    # Test get_all_decks
    print("\n1. Testing get_all_decks()")
    try:
        decks = await deck_manager.get_all_decks()
        print(f"Success! Found {len(decks)} decks")
        for deck in decks:
            print(f"\nDeck {deck['id']}:")
            for key, value in deck.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    await engine.dispose()
    print("\n" + "=" * 50)
    print("Debug complete!")


if __name__ == "__main__":
    asyncio.run(debug_deck_manager())

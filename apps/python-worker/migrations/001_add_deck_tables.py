"""
Migration: Add deck tables for DJ mixing functionality
Date: 2025-01-22
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import init_db, get_session
from models.deck import Deck, DeckHistory, MixerState, DeckStatus


async def upgrade():
    """Create deck-related tables"""
    print("Creating deck tables...")

    # Initialize database connection
    engine = await init_db()

    # Create tables using SQLAlchemy models
    # The init_db function already calls create_all, which will create new tables
    # without affecting existing ones

    # Initialize default deck states
    async with get_session(engine) as session:
        # Check if decks already exist
        result = await session.execute(text("SELECT COUNT(*) FROM decks"))
        deck_count = result.scalar()

        if deck_count == 0:
            # Create default decks A, B, C, D
            for deck_id in ["A", "B", "C", "D"]:
                deck = Deck(
                    id=deck_id,
                    status=DeckStatus.EMPTY,
                    volume=1.0,
                    gain=1.0,
                    eq_low=0.0,
                    eq_mid=0.0,
                    eq_high=0.0,
                    tempo_adjust=0.0,
                )
                session.add(deck)

            # Create default mixer state
            mixer = MixerState(
                id=1, crossfader=0.0, master_volume=0.8, monitor_volume=0.7
            )
            session.add(mixer)

            await session.commit()
            print("✓ Created default decks A, B, C, D")
            print("✓ Created default mixer state")
        else:
            print("✓ Decks already exist, skipping initialization")

    await engine.dispose()
    print("✓ Migration complete!")


async def downgrade():
    """Drop deck-related tables"""
    print("Dropping deck tables...")

    engine = await init_db()

    async with engine.begin() as conn:
        # Drop tables in reverse order due to foreign keys
        await conn.execute(text("DROP TABLE IF EXISTS deck_history"))
        await conn.execute(text("DROP TABLE IF EXISTS mixer_state"))
        await conn.execute(text("DROP TABLE IF EXISTS decks"))

    await engine.dispose()
    print("✓ Deck tables dropped")


if __name__ == "__main__":
    # Run upgrade when executed directly
    asyncio.run(upgrade())

"""Add mixer integration fields to decks and mixer_state tables"""

import asyncio
import sys

sys.path.append("/Users/lynscott/Projects/streamie/apps/python-worker")

from sqlalchemy import text
from models import init_db


async def run_migration():
    """Add mixer-related columns to tables"""
    engine = await init_db()

    async with engine.begin() as conn:
        # Add columns to decks table
        await conn.execute(
            text("""
            ALTER TABLE decks 
            ADD COLUMN crossfader_gain REAL DEFAULT 1.0
        """)
        )

        await conn.execute(
            text("""
            ALTER TABLE decks 
            ADD COLUMN auto_gain_applied BOOLEAN DEFAULT FALSE
        """)
        )

        await conn.execute(
            text("""
            ALTER TABLE decks 
            ADD COLUMN cue_active BOOLEAN DEFAULT FALSE
        """)
        )

        await conn.execute(
            text("""
            ALTER TABLE decks 
            ADD COLUMN peak_level REAL DEFAULT 0.0
        """)
        )

        await conn.execute(
            text("""
            ALTER TABLE decks 
            ADD COLUMN rms_level REAL DEFAULT 0.0
        """)
        )

        # Add column to mixer_state table
        await conn.execute(
            text("""
            ALTER TABLE mixer_state 
            ADD COLUMN recording_started_at TIMESTAMP
        """)
        )

        print("✅ Added mixer integration fields to database")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())

"""Add started_playing_at column to decks table"""
import asyncio
import sys
sys.path.append('/Users/lynscott/Projects/streamie/apps/python-worker')

from sqlalchemy import text
from models import init_db

async def run_migration():
    """Add started_playing_at column to decks table"""
    engine = await init_db()
    
    async with engine.begin() as conn:
        # Add started_playing_at column
        await conn.execute(text("""
            ALTER TABLE decks 
            ADD COLUMN started_playing_at TIMESTAMP
        """))
        
        print("✅ Added started_playing_at column to decks table")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
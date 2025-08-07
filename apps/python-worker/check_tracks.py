"""Check what tracks are in database"""

import asyncio
from sqlalchemy import select
from models import init_db, get_session, Track


async def check_tracks():
    engine = await init_db()

    async with get_session(engine) as session:
        # Get first 5 tracks
        stmt = select(Track).limit(5)
        result = await session.execute(stmt)
        tracks = result.scalars().all()

        print(f"Found {len(tracks)} tracks")
        for track in tracks:
            print(f"\nTrack ID: {track.id}")
            print(f"  Title: {track.title}")
            print(f"  Artist: {track.artist}")
            print(f"  Filepath: {track.filepath}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_tracks())

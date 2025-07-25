"""Check tracks table structure"""

import asyncio
from sqlalchemy import select
from models import init_db, get_session, Track
from sqlalchemy import text


async def check_track_structure():
    engine = await init_db()

    async with get_session(engine) as session:
        # Check for a specific filepath
        filepath = "PLAYLISTS/THRWBYKES/112/112 (Album)/07 Come See Me.mp3"

        # Count all tracks
        stmt = select(Track).limit(5)
        result = await session.execute(stmt)
        tracks = result.scalars().all()

        print(f"Found {len(tracks)} tracks")

        for track in tracks[:2]:
            print(f"\nTrack: {track.title}")
            print(f"  Artist: {track.artist}")
            print(f"  Filepath: {track.filepath}")
            print(f"  Filepath type: {type(track.filepath)}")

        # Check for specific track
        stmt = select(Track).where(Track.filepath == filepath)
        result = await session.execute(stmt)
        specific_track = result.scalar_one_or_none()

        print(f"\nSearching for: {filepath}")
        print(f"Found: {specific_track is not None}")

        # Check how many tracks start with PLAYLISTS
        stmt = text("SELECT COUNT(*) FROM tracks WHERE filepath LIKE 'PLAYLISTS%'")
        result = await session.execute(stmt)
        count = result.scalar()
        print(f"\nTracks starting with 'PLAYLISTS': {count}")

        # Get example filepaths
        stmt = text("SELECT filepath FROM tracks LIMIT 5")
        result = await session.execute(stmt)
        rows = result.all()
        print("\nExample filepaths:")
        for row in rows:
            print(f"  {row[0]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_track_structure())

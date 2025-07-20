# SQLite Track Analysis Migration

This document explains the new SQLite-based track analysis system that replaces MongoDB.

## Why SQLite?

- **Local**: No external database server required
- **Fast**: Better performance for local queries
- **Reliable**: No network dependencies or connection issues
- **Portable**: Single file database that's easy to backup/move
- **SQL**: Standard SQL queries for complex data analysis

## New Scripts

### 1. `analyze_and_enhance_tracks_sql.py`
**Main script** - Analyzes and enhances all your tracks in one go.

```bash
# Analyze all tracks (creates SQLite database)
python scripts/analyze_and_enhance_tracks_sql.py

# The script will:
# - Create a SQLite database at ../tracks.db
# - Scan your music directory
# - Only process new/changed files (incremental updates)
# - Extract metadata (title, artist, album, etc.)
# - Analyze audio (BPM, beats, mood)
# - Calculate enhanced features (energy, danceability, etc.)
# - Store everything in the local SQLite database
```

### 2. `query_tracks_db.py`
**Query tool** - Search and analyze your track database.

```bash
# Show database statistics
python scripts/query_tracks_db.py --stats

# Search for tracks
python scripts/query_tracks_db.py --search "artist name"
python scripts/query_tracks_db.py --search "song title"

# Find tracks by BPM range
python scripts/query_tracks_db.py --bpm-range 120 130

# Find high energy tracks
python scripts/query_tracks_db.py --high-energy

# Find danceable tracks
python scripts/query_tracks_db.py --danceable

# Find tracks by mood
python scripts/query_tracks_db.py --mood "mood_happy"

# Find similar tracks to a specific track
python scripts/query_tracks_db.py --similar 123

# Export all data to JSON
python scripts/query_tracks_db.py --export my_tracks.json

# Limit results
python scripts/query_tracks_db.py --high-energy --limit 10
```

### 3. `migrate_mongo_to_sql.py`
**Migration tool** - Migrate existing MongoDB data to SQLite.

```bash
# Migrate existing MongoDB data (one-time operation)
python scripts/migrate_mongo_to_sql.py
```

## Database Schema

The SQLite database includes all fields from your previous MongoDB setup plus improvements:

### Basic Metadata
- `title`, `artist`, `album`, `genre`, `year`, `track`, `albumartist`
- `duration`, `has_artwork`, `filename`, `filepath`

### Audio Analysis
- `bpm` - Beats per minute
- `beat_times` - JSON array of beat timestamps

### Mood Analysis (Essentia)
- `mood_acoustic`, `mood_aggressive`, `mood_electronic`
- `mood_happy`, `mood_party`, `mood_relaxed`, `mood_sad`
- `mood_label` - Primary mood

### Enhanced Features
- `energy_level` - Overall energy (0-1)
- `danceability` - How danceable (0-1)
- `tempo_stability` - Tempo consistency (0-1)
- `vocal_presence` - Vocal content detection (0-1)
- `valence` - Musical positivity (0-1)

### File Management
- `file_hash` - For change detection
- `file_size`, `last_modified` - File metadata
- `analyzed_at`, `enhanced_at` - Processing timestamps

## Usage Examples

### Complete Fresh Analysis
```bash
# Start fresh - analyze all your music
python scripts/analyze_and_enhance_tracks_sql.py
```

### Incremental Updates
```bash
# Only processes new/changed files
python scripts/analyze_and_enhance_tracks_sql.py
```

### Query Examples
```bash
# Find all house music around 128 BPM
python scripts/query_tracks_db.py --bpm-range 125 130 --search "house"

# Get your most energetic tracks
python scripts/query_tracks_db.py --high-energy --limit 20

# Find tracks similar to your favorite song
python scripts/query_tracks_db.py --similar 42

# Export data for other tools
python scripts/query_tracks_db.py --export tracks_backup.json
```

## Migration Steps

1. **Backup your existing data** (optional but recommended):
   ```bash
   python scripts/query_tracks_db.py --export mongo_backup.json
   ```

2. **Migrate existing MongoDB data** (if you have any):
   ```bash
   python scripts/migrate_mongo_to_sql.py
   ```

3. **Run the new analyzer** to fill in any missing data:
   ```bash
   python scripts/analyze_and_enhance_tracks_sql.py
   ```

4. **Verify migration** worked:
   ```bash
   python scripts/query_tracks_db.py --stats
   ```

## Performance

- **Initial analysis**: Same time as before (depends on library size)
- **Incremental updates**: Much faster (only processes changed files)
- **Queries**: Nearly instant for most operations
- **Database size**: ~1-2KB per track (much smaller than MongoDB)

## File Location

- **Database**: `apps/python-worker/tracks.db`
- **Backup**: Copy this single file to backup your entire database
- **Portable**: Can be moved between machines easily

## Benefits Over MongoDB

1. **No external dependencies** - Works without MongoDB server
2. **Better performance** - Faster queries and startup
3. **Incremental updates** - Only processes changed files
4. **File change detection** - Automatically detects modified tracks
5. **SQL queries** - Use standard SQL for complex analysis
6. **Smaller footprint** - More efficient storage
7. **Easy backup** - Single file to backup/restore

## Custom SQL Queries

You can also run custom SQL queries directly:

```python
import sqlite3
conn = sqlite3.connect('tracks.db')
cursor = conn.cursor()

# Find tracks with specific characteristics
cursor.execute('''
    SELECT title, artist, bpm, energy_level 
    FROM tracks 
    WHERE bpm BETWEEN 120 AND 130 
    AND energy_level > 0.7 
    ORDER BY energy_level DESC
''')

for row in cursor.fetchall():
    print(row)
```

## Next Steps

After migration, you can:
1. Remove the old MongoDB scripts
2. Update your main application to use SQLite
3. Set up regular incremental analysis
4. Build custom queries for your DJ workflow

The new system is designed to be faster, more reliable, and easier to maintain than the MongoDB setup. 
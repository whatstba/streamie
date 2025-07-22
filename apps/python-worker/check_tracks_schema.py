"""Check tracks database schema"""
import sqlite3

db_path = "tracks.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(tracks)")
columns = cursor.fetchall()

print("Tracks table columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()